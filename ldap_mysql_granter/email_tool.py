#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
email_tool automate sending emails through gmail
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
import argparse
import boto
import email
import logging
import pprint
import requests
import smtplib
import sys
import util

_connection = None
logger = logging.getLogger(__name__)


class EmailConfigException(Exception):
    pass


class EmailTool(object):
    def __init__(self, email, password=None, awsKey=None, awsSecret=None, hastebinUrl=None):
        self._email = email
        self._password = password
        self._awsKey = awsKey
        self._awsSecret = awsSecret
        self._hastebinUrl = hastebinUrl

    def sendMail(self, receipients, subject, message, attachPayloads={}, messageFormat='text'):
        if self._awsKey is not None and self._awsSecret is not None:
            if 0 < len(attachPayloads.keys()):
                logger.warn("sending through AWS does NOT support attachments at this time consider setting up a local hastebin server")
            self.sendAWSMail(receipients, subject, message, messageFormat)
        else:
            if self._email is None:
                raise EmailConfigException("missing email")
            if self._password is None:
                raise EmailConfigException("missing password")
            if receipients is None or receipients[0] is None:
                receipients = [self._email]
            self.sendGmail(receipients, subject, message, attachPayloads)

    def sendGmail(self, receipients, subject, message, attachPayloads):
        logger.info("sending through Gmail")
        msg = email.mime.Multipart.MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self._email
        msg['To'] = ", ".join(receipients)
        body = email.mime.Text.MIMEText(message)
        msg.attach(body)
        for f in attachPayloads:
            if attachPayloads[f] is not None:
                att = email.mime.Text.MIMEText(attachPayloads[f])
                att.add_header('Content-Disposition', 'attachment', filename=f)
                msg.attach(att)
            else:
                logger.warn("skipping empty attachment %s", f)
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo()
        server.starttls()
        server.login(self._email, self._password)
        server.sendmail(self._email, receipients, msg.as_string())
        server.quit()

    def sendAWSMail(self, receipients, subject, message,
                    messageFormat='text'):
        logger.info("sending through AWS")
        ses = boto.connect_ses(self._awsKey, self._awsSecret)
        ses.send_email(source=self._email,
                       subject=subject,
                       body=message,
                       to_addresses=receipients,
                       format=messageFormat,
                       reply_addresses=self._email)

    def getPasswordChangeScript(self, mysqlClusters, mysqlUser, mysqlHost, mysqlPass, raw=True):
        templateArgDict = {'mysqlUser': mysqlUser,
                           'mysqlHost': mysqlHost,
                           'mysqlPass': mysqlPass,
                           'mysqlClusters': mysqlClusters}
        payload = util.renderTemplate("password_change.py.tmpl",
                                      templateArgDict)
        return payload

    def getHasteBinUrl(self, payload, raw=True):
        uniqHastebinUrl = None
        if self._hastebinUrl is not None:
            try:
                hbRes = requests.post(self._hastebinUrl + 'documents', data=payload)
                hbUrl = self._hastebinUrl.rstrip('/')
                split = "/"
                if raw:
                    split = "/raw/"
                uniqHastebinUrl = hbUrl + split + hbRes.json()['key']
            except requests.exceptions.ConnectionError as e:
                logger.error("aborting hastebin is unavailable either remove from config or try again")
                raise e
        return uniqHastebinUrl

    def sendChangePasswordInvite(self, mysqlClusters, mysqlUserAtHost,
                                 mysqlPass, toList=None):
        attachPayloads = {}
        mysqlUser, mysqlHost = (x.strip("'") for x in mysqlUserAtHost.split('@'))
        passwordChangeScript = self.getPasswordChangeScript(mysqlClusters, mysqlUser, mysqlHost,
                                                            mysqlPass)
        rawHasteBinUrl = self.getHasteBinUrl(passwordChangeScript)
        if rawHasteBinUrl is not None:
            passwordChangeInst = "curl -fsSL " + rawHasteBinUrl + " | python"
        else:
            attachPayloads['password_change_invite.py'] = passwordChangeScript
            passwordChangeInst = "Download the password_change_invite.py script\nRun python password_change_invite.py from a command prompt\nFollow the on screen instructions"
        receipients = toList
        if receipients is None:
            emailDomain = self._email.split('@')[1]
            receipients = [mysqlUser + '@' + emailDomain]
        subject = "MySQL Password Change Invite"
        templateArgDict = {'mysqlUser': mysqlUser,
                           'mysqlHost': mysqlHost,
                           'mysqlPass': mysqlPass,
                           'email': self._email,
                           'passwordChangeInst': passwordChangeInst}
        message = util.renderTemplate("password_change_invite.tmpl",
                                      templateArgDict)
        logger.info("Sent ChangePassInvite to [%s] for %s on %s with password %s",
                    ', '.join(receipients), mysqlUser, ",".join(mysqlClusters), mysqlPass)
        self.sendMail(receipients, subject, message, attachPayloads)

    def sendAccessNotification(self, mysqlClusters, mysqlUserAtHost,
                               mysqlPass, defaultCluster, toList=None):
        mysqlUser, mysqlHost = (x.strip("'")
                                for x in mysqlUserAtHost.split('@'))
        receipients = toList
        if receipients is None:
            emailDomain = self._email.split('@')[1]
            receipients = [mysqlUser + '@' + emailDomain]
        subject = "MySQL Access Notification"
        templateArgDict = {'mysqlUser': mysqlUser,
                           'mysqlHost': mysqlHost,
                           'mysqlClusters': ",".join(mysqlClusters),
                           'defaultCluster': defaultCluster,
                           'email': self._email}
        message = util.renderTemplate("password_change_access.tmpl",
                                      templateArgDict)
        logger.info("Sent Access Notification to [%s] for %s on %s with password %s",
                    ", ".join(receipients), mysqlUser, ",".join(mysqlClusters), mysqlPass)
        self.sendMail(receipients, subject, message)


def main(args=None):
    """Arg parsing and logger setup"""
    retCode = 0
    toList = None
    clusterList = None
    logLevels = {"DEBUG": logging.DEBUG,
                 "INFO": logging.INFO,
                 "WARN": logging.WARNING,
                 "ERROR": logging.ERROR,
                 "CRITICAL": logging.CRITICAL}
    parser = argparse.ArgumentParser(
        description='A tool to automate the sending of emails')
    parser.add_argument('-l', '--log-level', type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
                        help="the log level")
    parser.add_argument('-e', '--email', type=str,
                        help="the email to send from")
    parser.add_argument('-p', '--password', type=str,
                        help="the password for the email")
    parser.add_argument('-k', '--aws-key', type=str,
                        help="the aws key if sending email through aws")
    parser.add_argument('-S', '--aws-secret', type=str,
                        help="the aws secret if sending email through aws")
    parser.add_argument('-T', '--to-list', type=str,
                        help="the list of receipients to send the mail to")
    parser.add_argument('-s', '--subject', type=str, default="",
                        help="the subject of the email")
    parser.add_argument('-m', '--message', type=str, default="",
                        help="the message body")
    parser.add_argument('-f', '--format', type=str, default="text",
                        help="the message format")
    # only used for sendChangePasswordInvite
    parser.add_argument('-C', '--clusters', type=str,
                        help="the list of clusters to filter by")
    # only used for sendChangePasswordInvite
    parser.add_argument('-P', '--new-password', type=str,
                        help="the new password for the user")
    # only used for sendChangePasswordInvite
    parser.add_argument('-N', '--new-user-at-host', type=str,
                        help="the new host for the user")
    parsedArgs = parser.parse_args(args)
    if parsedArgs.log_level.upper() in logLevels.keys():
        logging.basicConfig(level=logLevels[parsedArgs.log_level.upper()])
    else:
        logging.basicConfig(level=logging.INFO)
        logger.warn("Unknown logLevel=%s retaining level at INFO",
                    parsedArgs.log_level)
    logger.info(pprint.pformat(parsedArgs))
    # just for the email_tool
    if (parsedArgs.awsKey is None or parsedArgs.awsSecret is not None):
        if parsedArgs.email is None:
            parsedArgs.email = util.askQuestion("Gmail address: ")
        if parsedArgs.password is None:
            parsedArgs.password = util.askPassword("Gmail Password: ")
    if parsedArgs.to_list is not None:
        toList = parsedArgs.to_list.split(',')
    # run
    emailTool = EmailTool(parsedArgs.email, parsedArgs.password, parsedArgs.aws_key,
                          parsedArgs.aws_secret)
    if parsedArgs.new_password is not None and parsedArgs.clusters is not None:
        clusterList = parsedArgs.clusters.split(',')
        emailTool.sendChangePasswordInvite(clusterList, parsedArgs.new_user_at_host,
                                           parsedArgs.new_password, toList)
    else:
        emailTool.sendMail(toList, parsedArgs.subject, parsedArgs.message, parsedArgs.format)
    logger.info("Done!")
    return retCode

if __name__ == "__main__":
    """Entry point if being run as a script"""
    main(main(sys.argv[1:]))

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
mysql_grants_generator is a program to automate the generation of mysql grants
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""

import argparse
import datetime
import logging
import os
import pprint
import email_tool
import random
import string
import sys
import auto_grant_config
import ldap_query_tool
import mysql_backup_tool
import mysql_query_tool
import util
logger = logging.getLogger(__name__)

PASSWORD_KEY = 'password'
CLUSTERS_KEY = 'clusters'
TEMPLATE_KEY = 'template'
TEMPLATE_ACCESS = 'access'
TEMPLATE_INVITE = 'invite'
RET_MUTEX_ARGS = 10


class GrantException(Exception):
    """
    Generic GranException
    """
    def __init__(self, message):
        super(GrantException, self).__init__(message)


def makeGroupDict(autoGrantConfig, ldapGroupDict):
    """
    this is the ldap group processing
    :param autoGrantConfig: an instance of AutoGrantConfig
    :param ldapGroupDict: a dict with the form:
    {'cn=int_test_group,ou=groups,dc=nodomain': {'cn': ['int_test_group'],
                                                 'gidNumber': ['20000'],
                                                 'memberUid': ['int_test_user'],
                                                 'objectClass': ['top',
                                                                 'posixGroup']},
     'ou=groups,dc=nodomain': {'objectClass': ['organizationalUnit'],
                           'ou': ['groups']}}
    :returns: a dict of the form: {'int_test_group': ['int_test_user']}
    """
    groupDict = {}
    ldapMinGid = autoGrantConfig.getLdapMinGid()
    # add groups from ldap
    for key in ldapGroupDict.keys():
        if 'gidNumber' in ldapGroupDict[key]:
            for gid in ldapGroupDict[key]['gidNumber']:
                if ldapMinGid <= int(gid):
                    cnList = ldapGroupDict[key]['cn']
                    for cn in cnList:
                        if cn not in groupDict and 'memberUid' in ldapGroupDict[key]:
                            groupDict[cn] = ldapGroupDict[key]['memberUid']
    # add custom mysql groups from config
    customMysqlGroups = autoGrantConfig.getCustomMysqlGroups()
    if customMysqlGroups is not None:
        for group in customMysqlGroups.keys():
            if group not in groupDict:
                groupDict[group] = customMysqlGroups[group]
            else:
                for user in customMysqlGroups[group]:
                    if user not in groupDict[group]:
                        groupDict[group].append(user)
    logger.debug(pprint.pformat(groupDict))
    return groupDict


def makeUserDict(autoGrantConfig, groupDict, userList=None):
    """
    this breaks out the groups by user
    :param autoGrantConfig: an instance of AutoGrantConfig
    :param groupDict: a dict with the form: {'int_test_group': ['int_test_user']}
    :returns: a dict with the form: {'int_test_user@%': set(['int_test_group'])}
    """
    userDict = {}
    reverseDict = {}
    # first pass to just reverse the groupDict
    for group in groupDict.keys():
        for user in groupDict[group]:
            if userList is None or user in userList:
                if user not in reverseDict:
                    reverseDict[user] = set()
                reverseDict[user] |= set([group])
    # second pass to expand users with their @'hosts'
    for user in reverseDict.keys():
        for group in reverseDict[user]:
            hosts = autoGrantConfig.getHostsForGroup(group)
            for host in hosts:
                userKey = user + "@" + host
                if userKey not in userDict:
                    if not autoGrantConfig.getMysqlUserFiltered(userKey):
                        userDict[userKey] = reverseDict[user]
                    else:
                        logger.debug("filtering out user:"+userKey)
    return userDict


def makeGrantDict(autoGrantConfig, userDict, clusterList=None):
    """
    this breaks out the grants by user
    :param autoGrantConfig: an instance of AutoGrantConfig
    :param userDict: a dict with the form: {'int_test_user@%': set(['int_test_group'])}
    :returns: a dict with the form:
        {'192.168.33.10': {'int_test_user@%':
            [{'db_table': '*.*',
              'privileges': ['SELECT', 'FOOEY']},
             {'db_table': 'test_db.test_table',
              'privileges': ['select',
                             'INSERT',
                             'update',
                             'delete']}]}}
    """
    grantDict = {}
    dbClusters = autoGrantConfig.getDbClusters()
    # add the user dicts and get grants per cluster
    for cluster in dbClusters:
        if clusterList is not None and cluster not in clusterList:
            continue
        for user in userDict.keys():
            for group in userDict[user]:
                grantList = autoGrantConfig.getGrantList(user, cluster, group)
                for grant in grantList:
                    if cluster not in grantDict:
                        grantDict[cluster] = {}
                    if user not in grantDict[cluster]:
                        grantDict[cluster][user] = []
                    for userGrant in grantDict[cluster][user]:
                        if userGrant['db_table'] == grant['db_table']:
                            grantDict[cluster][user].remove(userGrant)
                            grant['privileges'] = list(set(userGrant['privileges'] + grant['privileges']))
                            break
                    grantDict[cluster][user].append(grant)
    return grantDict


def grantAccess(autoGrantConfig, grantDict, echoOnly, destructive, passwordReset):
    """ This is the function that grants revokes and drops users
        Before adding any additional logica we should consider splitting
        this function to avoid it getting too unweildy
        NOTE: if destructive is False Revokes and Drop Users will be omitted
    """
    newUserDict = {}
    mysqlBackupTool = mysql_backup_tool.MysqlBackupTool(echoOnly)
    backupName = mysqlBackupTool.getCurrentTimeBackup()
    grantUser = autoGrantConfig.getMysqlGrantsUsername()
    grantPass = autoGrantConfig.getMysqlGrantsPassword()
    # determine access levels from echoOnly and destructive
    echoAccessLevel = mysql_query_tool.QAL_READ_WRITE
    if destructive or passwordReset:
        echoAccessLevel = mysql_query_tool.QAL_READ_WRITE_DELETE
    queryAccessLevel = echoAccessLevel
    if echoOnly:
        queryAccessLevel = mysql_query_tool.QAL_READ
    defaultCluster = grantDict.keys()[0]
    for cluster in grantDict.keys():
        mysqlBackupTool.performMySQLDumpList(cluster, grantUser, grantPass, backupName, [("mysql", "user")])
        logger.debug("backup saved")
        mysqlConn = mysql_query_tool.MysqlQueryTool(cluster, grantUser,
                                                    grantPass, echoAccessLevel,
                                                    queryAccessLevel)
        logger.debug("connection created")
        for userAtHost in grantDict[cluster].keys():
            logger.debug("working on %s", userAtHost)
            userPart, hostPart = (x.strip("'") for x in userAtHost.split('@'))
            mysqlConn.beginTransaction()
            passwordHash = mysqlConn.getPasswordHash(userPart, hostPart)
            userExists = (passwordHash is not None)
            if passwordReset and userExists:
                mysqlConn.dropUser(userAtHost)
                userExists = False
                passwordHash = None
            if userExists:
                logger.debug("CACHING PASSWORD HASH %s FOR %s ACCOUNT ON %s" % (passwordHash, userAtHost, cluster))
                updateMysqlUser(newUserDict, userAtHost, mysqlConn, passwordHash, None)
            else:
                logger.debug("NEED TO CREATE USER: %s", userAtHost)
                updateMysqlUser(newUserDict, userAtHost, mysqlConn, generateRandomPassword(), cluster)
            grantDeltaDict = {}
            try:
                for grant in grantDict[cluster][userAtHost]:
                    dbTable = grant['db_table']
                    privileges = grant['privileges']
                    grantDeltaDict = mysqlConn.getGrantDeltaDict(userAtHost, dbTable, privileges)
                    if 0 < len(grantDeltaDict['grants']):
                        mysqlConn.queryGrant(userAtHost,
                                             grantDeltaDict['grants'],
                                             dbTable)
                    if 0 < len(grantDeltaDict['revokes']):
                        mysqlConn.queryRevoke(userAtHost,
                                              grantDeltaDict['revokes'],
                                              dbTable)
                        mysqlConn.queryFlushPrivileges()
                mysqlConn.commitTransaction()
            except Exception as e:
                mysqlConn.rollbackTransaction()
                message = e.message + ": An exception occured when trying to grant:[%s] and revoke:[%s] to %s on %s" % (",".join(grantDeltaDict['grants']), ",".join(grantDeltaDict['revokes']), userAtHost, cluster)
                raise GrantException(message)
        if destructive and not passwordReset:
            # remove non defined users
            allMysqlUsers = mysqlConn.findAllUsers()
            usersToDrop = findUsersToDrop(autoGrantConfig, allMysqlUsers,
                                          grantDict[cluster].keys())
            for userToDropWithHost in usersToDrop:
                mysqlConn.dropUser(userToDropWithHost)
        mysqlConn.closeConnection()
    if echoOnly is False:
        sendEmailNotifications(autoGrantConfig, newUserDict, defaultCluster)


def findUsersToDrop(autoGrantConfig, allMysqlUsers, usersWithGrants):
    usersToDrop = []
    for mysqlUser in allMysqlUsers:
        if mysqlUser in usersWithGrants:
            continue
        if not autoGrantConfig.getMysqlUserFiltered(mysqlUser):
            usersToDrop.append(mysqlUser)
    return usersToDrop


def updateMysqlUser(newUserDict, newUserWithHost, mysqlConn, password, cluster=None):
    if newUserWithHost not in newUserDict:
        newUserDict[newUserWithHost] = {CLUSTERS_KEY: set([]),
                                        PASSWORD_KEY: password,
                                        TEMPLATE_KEY: TEMPLATE_INVITE}
        if cluster is None:
            newUserDict[newUserWithHost][TEMPLATE_KEY] = TEMPLATE_ACCESS
        else:
            logger.info("New password invite for %s with password %s",
                        newUserWithHost, password)
    if cluster is not None:
        newUserDict[newUserWithHost][CLUSTERS_KEY] |= set([cluster])
        useHash = newUserDict[newUserWithHost][TEMPLATE_KEY] == TEMPLATE_ACCESS
        newPassword = newUserDict[newUserWithHost][PASSWORD_KEY]
        mysqlConn.createUser(newUserWithHost, newPassword, useHash)


def sendEmailNotifications(autoGrantConfig, newUserDict, defaultCluster):
    email = autoGrantConfig.getEmail()
    emailPass = autoGrantConfig.getEmailPass()
    awsKey = autoGrantConfig.getAWSKey()
    awsSecret = autoGrantConfig.getAWSSecret()
    hastebinUrl = autoGrantConfig.getHasteBinUrl()
    emailTool = email_tool.EmailTool(email, emailPass, awsKey, awsSecret, hastebinUrl)
    ldapEmailMap = autoGrantConfig.getUserToEmailMap()
    for userAtHost in newUserDict.keys():
        clusters = newUserDict[userAtHost][CLUSTERS_KEY]
        if 0 < len(clusters):
            newPassword = newUserDict[userAtHost][PASSWORD_KEY]
            template = newUserDict[userAtHost][TEMPLATE_KEY]
            mysqlUser = userAtHost.split('@')[0].strip("'")
            # If None this will generate the email from [mysqlUser]@[domain of gmail_auth.username in yaml]
            toList = None
            if mysqlUser in ldapEmailMap:
                emailOverride = ldapEmailMap[mysqlUser]
                toList = [emailOverride]
            if template == TEMPLATE_INVITE:
                emailTool.sendChangePasswordInvite(clusters, userAtHost, newPassword, toList)
            else:
                emailTool.sendAccessNotification(clusters, userAtHost, newPassword, defaultCluster, toList)


def generateRandomPassword():
    length = 32
    chars = string.ascii_letters + string.digits
    random.seed = (os.urandom(1024))
    randomPassword = ''.join(random.choice(chars) for i in range(length))
    logger.debug("generateRandomPassword="+randomPassword)
    return randomPassword


def start(autoGrantConfig, echoOnly, destructive, passwordReset, revert, userList, groupList,
          clusterList):
    restoreName = ''
    restorePath = ''
    mysqlBackupTool = mysql_backup_tool.MysqlBackupTool(echoOnly)
    pruneBeforeDate = mysqlBackupTool.getPruneBeforeFromTimeDelta(
        datetime.timedelta(days=30))
    mysqlBackupTool.pruneBefore(pruneBeforeDate)
    if revert is not False:
        if revert is None:
            # default we use the last backup
            restoreName = mysqlBackupTool.getLastBackup()
        else:
            # default we use the last backup
            restoreName = revert
        backupDir = mysql_backup_tool.DEFAULT_BACKUP_DIR
        if restoreName is not None and 0 < len(restoreName):
            restorePath = os.path.join(backupDir, restoreName)
        if os.path.isdir(restorePath):
            revertUser = autoGrantConfig.getMysqlRevertUsername()
            revertPass = autoGrantConfig.getMysqlRevertPassword()
            mysqlBackupTool = mysql_backup_tool.MysqlBackupTool(echoOnly)
            for cluster in autoGrantConfig.getDbClusters():
                logger.info("reverting %s", cluster)
                echoAccessLevel = mysql_query_tool.QAL_ALL
                queryAccessLevel = mysql_query_tool.QAL_ALL
                if echoOnly:
                    queryAccessLevel = mysql_query_tool.QAL_NONE
                mysqlConn = mysql_query_tool.MysqlQueryTool(cluster, revertUser,
                                                            revertPass,
                                                            echoAccessLevel,
                                                            queryAccessLevel)
                mysqlBackupTool.restoreFromMySQLDumpList(cluster, revertUser,
                                                         revertPass, restoreName,
                                                         [("mysql", "user")])
                mysqlConn.queryFlushPrivileges()
        else:
            logger.error("No backup was found under %s", backupDir)
    else:
        ldapUrl = autoGrantConfig.getLdapURL()
        ldapUsernameBase = autoGrantConfig.getLdapUsernameBase()
        ldapPassword = autoGrantConfig.getLdapPassword()
        ldapGroupDict = {}
        if ldapUrl is None or ldapUsernameBase is None or ldapPassword is None:
            logger.warning("missing one of ldapUrl:%s ldapUsernameBase:%s or ldapPassword:%s [%s]",
                           str(ldapUrl), str(ldapUsernameBase), str(ldapPassword),
                           "this will disable ldap integration")
        else:
            ldapQueryTool = ldap_query_tool.LdapQueryTool(ldapUrl,
                                                          ldapUsernameBase,
                                                          ldapPassword)
            ldapGroupDesc = autoGrantConfig.getLdapGroupDesc()
            ldapGroupDict = ldapQueryTool.queryLDAP(ldapGroupDesc)
        groupDict = makeGroupDict(autoGrantConfig, ldapGroupDict)
        if userList is not None:
            userList = userList.split(",")
        if groupList is not None:
            for group in groupList.split(","):
                if userList is None:
                    userList = []
                userList += groupDict[group]
        logger.debug("groupDict:\n"+pprint.pformat(groupDict))
        userDict = makeUserDict(autoGrantConfig, groupDict, userList)
        logger.debug("userDict:\n"+pprint.pformat(userDict))
        grantDict = makeGrantDict(autoGrantConfig, userDict, clusterList)
        logger.debug("grantDict:\n"+pprint.pformat(grantDict))
        grantAccess(autoGrantConfig, grantDict, echoOnly, destructive, passwordReset)


def init_config(nonInteractive):
    configFile = os.path.join(os.getcwd(), 'auto_grant.yaml')
    if os.path.exists(configFile):
        raise Exception("could not generate auto_grant.yaml file already exists")
    else:
        if nonInteractive:
            mysqlUser = "<%= ENV['AG_MYSQL_USER'] %>"
            mysqlPass = "<%= ENV['AG_MYSQL_PASS'] %>"
            gmailUser = "<%= ENV['AG_GMAIL_USER'] %>"
            gmailPass = "<%= ENV['AG_GMAIL_PASS'] %>"
        else:
            mysqlUser = util.askQuestion("Please enter your mysql user", "grant_user")
            mysqlPass = util.askPassword("Please enter your mysql password", "grant_pass")
            gmailUser = util.askQuestion("Please enter your gmail user")
            gmailPass = util.askPassword("Please enter your gmail password")
        templateArgDict = {'mysqlUser': mysqlUser,
                           'mysqlPass': mysqlPass,
                           'gmailUser': gmailUser,
                           'gmailPass': gmailPass}
        payload = util.renderTemplate("auto_grant.yaml.tmpl",
                                      templateArgDict)
        with open(configFile, 'w') as f:
            f.write(payload)


def main(args=None):
    """Arg parsing and logger setup"""
    retCode = 0
    logLevels = {"DEBUG": logging.DEBUG,
                 "INFO": logging.INFO,
                 "WARN": logging.WARNING,
                 "ERROR": logging.ERROR,
                 "CRITICAL": logging.CRITICAL}
    parser = argparse.ArgumentParser(
        description='A tool to apply grants using ldap groups')
    reqGrp = parser.add_argument_group("required arguments")
    usrGrp = parser.add_argument_group("user arguments")
    dstGrp = parser.add_argument_group("destructive arguments")
    parser.add_argument('-l', '--log-level', type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
                        help="the log level")
    parser.add_argument('-e', '--echo-only', action='store_true',
                        help="just print out the queries to run")
    parser.add_argument('--non-interactive', action='store_true', default=False,
                        help="just run without any prompting")
    parser.add_argument('-C', '--cluster-list', type=str,
                        help="a comma delimited list of clusters to filter by")
    usrGrp.add_argument('-U', '--user-list', type=str,
                        help="a comma delimited list of users to filter by")
    usrGrp.add_argument('-G', '--group-list', type=str,
                        help="a comma delimited list of groups to filter by")
    dstGrp.add_argument('-r', '--revert', nargs='?', type=str,
                        required=False, default=False,
                        help="restore using the latest backup")
    dstGrp.add_argument('--destructive', action='store_true',
                        required=False, default=False,
                        help="drop users and revoke privileges")
    parser.add_argument('--password-reset', action='store_true',
                        required=False, default=False,
                        help="drop and re-add the user to reset password")
    reqGrp.add_argument('-y', '--yaml-conf', type=str, required=False,
                        default=os.path.join(os.getcwd(), 'auto_grant.yaml'),
                        help="the yaml configuration path")
    reqGrp.add_argument('-i', '--init', action='store_true',
                        required=False, default=False,
                        help="create an auto_grant.yaml conf in the current working dir")
    parsedArgs = parser.parse_args(args)
    if parsedArgs.log_level.upper() in logLevels.keys():
        logging.basicConfig(level=logLevels[parsedArgs.log_level.upper()])
    else:
        logging.basicConfig(level=logging.INFO)
        logger.warn("Unknown logLevel=%s retaining level at INFO",
                    parsedArgs.log_level)
    logger.debug(pprint.pformat(parsedArgs))
    if ((parsedArgs.destructive is True or parsedArgs.revert is not False) and
            (parsedArgs.user_list is not None or parsedArgs.group_list is not None)):
        print ("Can not use user arguments in combination with " +
               "destructive arguments")
        retCode = RET_MUTEX_ARGS
    else:
        if parsedArgs.init:
            init_config(parsedArgs.non_interactive)
        else:
            autoGrantConfig = auto_grant_config.AutoGrantConfig(parsedArgs.yaml_conf)
            start(autoGrantConfig, True, parsedArgs.destructive, parsedArgs.password_reset, parsedArgs.revert,
                  parsedArgs.user_list, parsedArgs.group_list, parsedArgs.cluster_list)
            if(parsedArgs.echo_only is False):
                userInput = "No"
                if parsedArgs.non_interactive is True:
                    logger.info("The above commands will be run %s...",
                                "non-interactively")
                    userInput = "Yes"
                else:
                    userInput = util.askQuestion("Are you sure you would like to run the above commands:\n" +
                                                 "Type %s to continue %s to skip" %
                                                 ("[Yes]", "[Enter]"))
                if userInput == "Yes":
                    start(autoGrantConfig, parsedArgs.echo_only, parsedArgs.destructive, parsedArgs.password_reset,
                          parsedArgs.revert, parsedArgs.user_list, parsedArgs.group_list,
                          parsedArgs.cluster_list)
                else:
                    logger.info("skipping...")
    logger.info("done.")
    return retCode

if __name__ == "__main__":
    """Entry point if being run as a script"""
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_email_tool is used to test the gmail tool
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
#  This script requires the following packages to be installed:
#   mock==1.0.1

import logging
import mock
import email_tool
import unittest
import util
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)


class TestEmailTool(unittest.TestCase):
    def test_sendChangePasswordInvite(self):
        awsMailTool = email_tool.EmailTool("username@domain.com", "password",
                                           "an_aws_key", "an_aws_secret")
        awsMailTool.getHasteBinUrl = mock.MagicMock(
            return_value="http://internal-hastebin.example.com/random_abc")
        awsMailTool.sendAWSMail = mock.MagicMock(return_value=None)
        awsMailTool.sendChangePasswordInvite("mysqlCluster",
                                             "'mysqlUser'@'mysqlHost'",
                                             "mysqlPass")
        self.assertEquals(1, len(awsMailTool.sendAWSMail.mock_calls))
        gmailTool = email_tool.EmailTool("username@domain.com", "password")
        gmailTool.getHasteBinUrl = mock.MagicMock(
            return_value="http://internal-hastebin.example.com/random_abc")
        gmailTool.sendGmail = mock.MagicMock(return_value=None)
        gmailTool.sendChangePasswordInvite("mysqlCluster",
                                           "'mysqlUser'@'mysqlHost'",
                                           "mysqlPass")
        self.assertEquals(1, len(gmailTool.sendGmail.mock_calls))

    def test_sendsendAccessNotification(self):
        awsMailTool = email_tool.EmailTool("username@domain.com", "password",
                                           "an_aws_key", "an_aws_secret")
        awsMailTool.sendAWSMail = mock.MagicMock(return_value=None)
        awsMailTool.sendAccessNotification("mysqlCluster",
                                           "'mysqlUser'@'mysqlHost'",
                                           "defaultCluster",
                                           "mysqlPass")
        self.assertEquals(1, len(awsMailTool.sendAWSMail.mock_calls))
        gmailTool = email_tool.EmailTool("username@domain.com", "password")
        gmailTool.sendGmail = mock.MagicMock(return_value=None)
        gmailTool.sendAccessNotification("mysqlCluster",
                                         "'mysqlUser'@'mysqlHost'",
                                         "defaultCluster",
                                         "mysqlPass")
        self.assertEquals(1, len(gmailTool.sendGmail.mock_calls))

    def test_getEmailTemplate(self):
        self.maxDiff = None
        templateContents = """
Hello {{ u }},

You are now the proud owner of your very own MySQL user:
'{{ u }}'@'{{ h }}'
The first thing you should do is change your password.
This can be done easily but first setting an by running the following commands:
First set an environment variable with your password
$ export NMP="INSERT_YOUR_FAVORITE_PASSWORD_HERE"
Then you can just copy paste these lines to set your password:
{% for cl in c %}
# after being connected to {{ h }}:
$ mysql -h {{ cl }} -u '{{ u }}' -p{{ p }} -e "SET PASSWORD = PASSWORD($NMP)"
{% endfor %}
Please feel free to reply to this email with any questions you may have.

Happy Querying,
Bob T. Builder <{{ e }}>
http://i.imgur.com/IaqNsAd.jpg"""
        templateArgDict = {'u': "user",
                           'h': "fromHost",
                           'p': "password",
                           'e': "email@domain.com",
                           'c': set(["cluster1", "cluster2"])}
        renderedTemplate = util.renderTemplate(templateContents,
                                               templateArgDict)
        expectedRenderedTemplate = u"""
Hello user,

You are now the proud owner of your very own MySQL user:
'user'@'fromHost'
The first thing you should do is change your password.
This can be done easily but first setting an by running the following commands:
First set an environment variable with your password
$ export NMP="INSERT_YOUR_FAVORITE_PASSWORD_HERE"
Then you can just copy paste these lines to set your password:

# after being connected to fromHost:
$ mysql -h cluster2 -u 'user' -ppassword -e "SET PASSWORD = PASSWORD($NMP)"

# after being connected to fromHost:
$ mysql -h cluster1 -u 'user' -ppassword -e "SET PASSWORD = PASSWORD($NMP)"

Please feel free to reply to this email with any questions you may have.

Happy Querying,
Bob T. Builder <email@domain.com>
http://i.imgur.com/IaqNsAd.jpg"""
        self.assertEquals(expectedRenderedTemplate, renderedTemplate)


# IMPLEMENT THESE TESTS IF TIME
# def test_main(self):

if __name__ == '__main__':
    unittest.main()

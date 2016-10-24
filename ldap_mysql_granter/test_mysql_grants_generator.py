#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_mysql_grants_generator is used to test the mysql grants generator
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
#  This script requires the following packages to be installed:
#   mock==1.0.1
#   PyYAML==3.11
#   python-ldap==2.4.19

from contextlib import contextmanager
from StringIO import StringIO
import logging
import mock
import sys
import mysql_grants_generator
import unittest
import auto_grant_config
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class TestMysqlGrantsGenerator(unittest.TestCase):
    yamlDict = None
    ldapUrl = "ldaps://ldap.example.com"

    def setUp(self):
        """use a custom yaml file
           NOTE: the overrideYamlDictForTests should only be called from tests
        """
        self.maxDiff = None
        self.yamlDict = {'ldap_server_url': self.ldapUrl,
                         'mysql_auth': {'grants': {'username': "grantUser",
                                                   'password': "grantPass"},
                                        'revert': {'username': "revertUser",
                                                   'password': "revertPass"}},
                         'gmail_auth': {'username': "user@gmail.com",
                                        'password': "gmailPass"},
                         'aws_auth': {'key': "an_aws_key",
                                      'secret': "an_aws_secret"},
                         'override_groups': {'group1': ["user1", "user2"],
                                             'group2': ["user2", "user3"]},
                         'user_to_email_map': {'aNewUser':
                                               'aNewEmail@domain.com'},
                         'group_to_grants_map': {
                             # db cluster
                             'cluster1': {
                                 # ldap group to expand per user
                                 'group1': {
                                     # @host component of username
                                     'host1': {
                                         # database.table: Permissions to GRANT
                                         '*.*': ['SELECT', 'INSERT',
                                                 'UPDATE', 'DELETE']
                                     },
                                     'host2': {
                                         # database.table: Permissions to GRANT
                                         'aDB.aTable': ['ALTER', 'DROP'],
                                         'bDB.bTable': ['SUPER']
                                     }
                                 },
                                 'group2': {'%': {'*.*': ["SELECT"]}},
                                 'group3': {'%': {'*.*': ["SELECT"]}},
                                 'group4': {'%': {'*.*': ["SELECT", "INSERT", "UPDATE", "DELETE"]}}
                             },
                             'cluster2': {
                                 'group2': {'%': {'*.*': ["SELECT"]}}
                             }
                         }}
        self.autoGrantConfig = auto_grant_config.AutoGrantConfig('integration_test.yaml')
        self.autoGrantConfig.overrideYamlDictForTests(self.yamlDict)
        # Cache unmocked
        self._unmockedQueryToolInit = mysql_grants_generator.mysql_query_tool.MysqlQueryTool.__init__
        self._unmockedQueryToolQueryMySql = mysql_grants_generator.mysql_query_tool.MysqlQueryTool.queryMySQL
        self._unmockedQueryToolQueryGrant = mysql_grants_generator.mysql_query_tool.MysqlQueryTool.queryGrant
        self._unmockedQueryToolBeginTrans = mysql_grants_generator.mysql_query_tool.MysqlQueryTool.beginTransaction
        self._unmockedQueryToolCommitTrans = mysql_grants_generator.mysql_query_tool.MysqlQueryTool.commitTransaction
        self._unmockedQueryToolCloseConn = mysql_grants_generator.mysql_query_tool.MysqlQueryTool.closeConnection
        self._unmockedQueryToolCreateUser = mysql_grants_generator.mysql_query_tool.MysqlQueryTool.createUser
        self._unmockedBackupToolDump = mysql_grants_generator.mysql_backup_tool.MysqlBackupTool.performMySQLDumpList
        self._unmockedEmailToolSendMail = mysql_grants_generator.email_tool.EmailTool.sendMail
        self._unmockedEmailToolSendInvite = mysql_grants_generator.email_tool.EmailTool.sendChangePasswordInvite
        # Mock
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.__init__ = mock.MagicMock(return_value=None)
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.queryMySQL = mock.MagicMock(return_value={})
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.queryGrant = mock.MagicMock(return_value={})
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.beginTransaction = mock.MagicMock(return_value=None)
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.commitTransaction = mock.MagicMock(return_value=None)
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.closeConnection = mock.MagicMock(return_value=None)
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.createUser = mock.MagicMock(return_value=None)
        mysql_grants_generator.mysql_backup_tool.MysqlBackupTool.performMySQLDumpList = mock.MagicMock(return_value=None)
        mysql_grants_generator.email_tool.EmailTool.sendMail = mock.MagicMock(return_value=None)
        mysql_grants_generator.email_tool.EmailTool.sendChangePasswordInvite = mock.MagicMock(return_value=None)

    def tearDown(self):
        # Restore from unmocked
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.__init__ = self._unmockedQueryToolInit
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.queryMySQL = self._unmockedQueryToolQueryMySql
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.queryGrant = self._unmockedQueryToolQueryGrant
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.beginTransaction = self._unmockedQueryToolBeginTrans
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.commitTransaction = self._unmockedQueryToolCommitTrans
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.closeConnection = self._unmockedQueryToolCloseConn
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.createUser = self._unmockedQueryToolCreateUser
        mysql_grants_generator.mysql_backup_tool.MysqlBackupTool.performMySQLDumpList = self._unmockedBackupToolDump
        mysql_grants_generator.email_tool.EmailTool.sendMail = self._unmockedEmailToolSendMail
        mysql_grants_generator.email_tool.EmailTool.sendChangePasswordInvite = self._unmockedEmailToolSendInvite

    def test_makeGroupDict(self):
        ldapDict = {'cn=agroup,ou=Groups,dc=example,dc=com': {
                    'cn': ['agroup'],
                    'gidNumber': ['20001'],
                    'memberUid': ['user1',
                                  'user2',
                                  'user3'],
                    'objectClass': ['top',
                                    'posixGroup']},
                    'cn=empty,ou=Groups,dc=example,dc=com': {
                    'cn': ['agroup'],
                    'gidNumber': ['20002'],
                    'objectClass': ['top',
                                    'posixGroup']}}
        groupDict = mysql_grants_generator.makeGroupDict(self.autoGrantConfig,
                                                         ldapDict)
        expectedGroupDict = {'agroup': ['user1', 'user2', 'user3'],
                             'group1': ['user1', 'user2'],
                             'group2': ['user2', 'user3']}
        self.assertItemsEqual(expectedGroupDict, groupDict)

    def test_makeUserDict(self):
        groupDict = {'agroup': ['user1', 'user2', 'user3'],
                     'group1': ['user1', 'user2'],
                     'group2': ['user2', 'user3']}
        userDict = mysql_grants_generator.makeUserDict(self.autoGrantConfig,
                                                       groupDict)
        expectedUserDict = {"user1@host1": set(['group1', 'agroup']),
                            "user1@host2": set(['group1', 'agroup']),
                            "user2@host1": set(['group1',
                                                'group2', 'agroup']),
                            "user2@host2": set(['group1',
                                                'group2', 'agroup']),
                            "user2@%": set(['group1',
                                            'group2', 'agroup']),
                            "user3@%": set(['group2', 'agroup'])}
        self.assertDictEqual(expectedUserDict, userDict)

    def test_makeGrantDict(self):
        userDict = {"user1@host1": set(['group1', 'agroup']),
                    "user1@host2": set(['group1', 'agroup']),
                    "user2@host1": set(['group1', 'group2', 'agroup']),
                    "user2@host2": set(['group1', 'group2', 'agroup']),
                    "user2@%": set(['group1', 'group2', 'agroup']),
                    "user3@%": set(['group2', 'agroup']),
                    "user4@%": set(['group3', 'group4'])}
        grantDict = mysql_grants_generator.makeGrantDict(self.autoGrantConfig,
                                                         userDict)
        expectedGrantDict = {'cluster1':
                             {"user1@host1": [{'db_table': '*.*',
                                               'privileges': ['SELECT',
                                                              'INSERT',
                                                              'UPDATE',
                                                              'DELETE']}],
                              "user1@host2": [{'db_table': 'bDB.bTable',
                                               'privileges':
                                               ['SUPER']},
                                              {'db_table': 'aDB.aTable',
                                               'privileges': ['ALTER',
                                                              'DROP']}],
                              "user2@%": [{'db_table': '*.*',
                                           'privileges': ['SELECT']}],
                              "user2@host1": [{'db_table': '*.*',
                                               'privileges': ['SELECT',
                                                              'INSERT',
                                                              'UPDATE',
                                                              'DELETE']}],
                              "user2@host2": [{'db_table': 'bDB.bTable',
                                               'privileges':
                                               ['SUPER']},
                                              {'db_table': 'aDB.aTable',
                                               'privileges': ['ALTER',
                                                              'DROP']}],
                              "user3@%": [{'db_table': '*.*',
                                           'privileges': ['SELECT']}],
                              "user4@%": [{'db_table': '*.*',
                                           'privileges': ['INSERT',
                                                          'UPDATE',
                                                          'SELECT',
                                                          'DELETE']}]},
                             'cluster2':
                             {"user2@%": [{'db_table': '*.*',
                                           'privileges': ['SELECT']}],
                              "user3@%": [{'db_table': '*.*',
                                           'privileges': ['SELECT']}]}}
        self.assertDictEqual(expectedGrantDict, grantDict)

    def test_grantAccess(self):
        grantDict = {'cluster1':
                     {"user1@host1": [{'db_table': '*.*',
                                       'privileges': ['SELECT',
                                                      'INSERT',
                                                      'UPDATE',
                                                      'DELETE']}],
                      "user1@host2": [{'db_table': 'bDB.bTable',
                                       'privileges':
                                       ['SUPER']},
                                      {'db_table': 'aDB.aTable',
                                       'privileges':
                                       ['ALTER', 'DROP']}],
                      "user2@%": [{'db_table': '*.*',
                                   'privileges': ['SELECT']}],
                      "user2@host1": [{'db_table': '*.*',
                                       'privileges': ['SELECT',
                                                      'INSERT',
                                                      'UPDATE',
                                                      'DELETE']}],
                      "user2@host2": [{'db_table': 'bDB.bTable',
                                       'privileges':
                                       ['SUPER']},
                                      {'db_table': 'aDB.aTable',
                                       'privileges':
                                       ['ALTER', 'DROP']}],
                      "user3@%": [{'db_table': '*.*',
                                   'privileges': ['SELECT']}]},
                     'cluster2':
                     {"user2@%": [{'db_table': '*.*',
                                   'privileges': ['SELECT']}],
                      "user3@%": [{'db_table': '*.*',
                                   'privileges': ['SELECT']}]}}
        expectedCalls = [mock.call('user3@%', set(['SELECT']), '*.*'),
                         mock.call('user2@%', set(['SELECT']), '*.*'),
                         mock.call('user3@%', set(['SELECT']), '*.*'),
                         mock.call('user2@host1',
                                   set(['INSERT', 'UPDATE', 'SELECT',
                                        'DELETE']), '*.*'),
                         mock.call('user2@host2', set(['SUPER']),
                                   'bDB.bTable'),
                         mock.call('user2@host2', set(['DROP', 'ALTER']),
                                   'aDB.aTable'),
                         mock.call('user2@%', set(['SELECT']), '*.*'),
                         mock.call('user1@host2', set(['SUPER']),
                                   'bDB.bTable'),
                         mock.call('user1@host2', set(['DROP', 'ALTER']),
                                   'aDB.aTable'),
                         mock.call('user1@host1',
                                   set(['INSERT', 'UPDATE', 'SELECT',
                                        'DELETE']), '*.*')]
        echoOnly = False
        destructive = False
        passwordReset = False
        mysql_grants_generator.grantAccess(self.autoGrantConfig, grantDict,
                                           echoOnly, destructive, passwordReset)
        mysql_grants_generator.mysql_query_tool.MysqlQueryTool.queryGrant.assert_has_calls(expectedCalls)

    def test_updateMysqlUser(self):
        qal = mysql_grants_generator.mysql_query_tool.QAL_NONE
        mysqlConn = mysql_grants_generator.mysql_query_tool.MysqlQueryTool("cluster", "user", "pass", qal, qal)
        newUserDict = {}
        # Check adding a user
        expectedNewUserDict = {"aNewUser@Host":
                               {mysql_grants_generator.CLUSTERS_KEY: set(['aCluster']),
                                mysql_grants_generator.PASSWORD_KEY: 'aRandPass',
                                mysql_grants_generator.TEMPLATE_KEY: mysql_grants_generator.TEMPLATE_INVITE}
                               }
        mysql_grants_generator.updateMysqlUser(newUserDict, "aNewUser@Host", mysqlConn, 'aRandPass', 'aCluster')
        expectedMySQLCalls = [mock.call('aNewUser@Host', 'aRandPass', False)]
        mysqlConn.createUser.assert_has_calls(expectedMySQLCalls)
        self.assertDictEqual(expectedNewUserDict, newUserDict)
        newUserDict = expectedNewUserDict
        # Check caching a password
        expectedNewUserDict['bNewUser@Host'] = {
            mysql_grants_generator.CLUSTERS_KEY: set([]),
            mysql_grants_generator.PASSWORD_KEY: 'bSavedPass',
            mysql_grants_generator.TEMPLATE_KEY: mysql_grants_generator.TEMPLATE_ACCESS}
        mysql_grants_generator.updateMysqlUser(newUserDict, "bNewUser@Host", mysqlConn, 'bSavedPass', None)
        newUserDict = expectedNewUserDict
        # Check notifying about a new cluster
        expectedNewUserDict['bNewUser@Host'][mysql_grants_generator.CLUSTERS_KEY] = set(['bCluster'])
        mysql_grants_generator.updateMysqlUser(newUserDict, "bNewUser@Host", mysqlConn, 'bRandomPass', 'bCluster')
        self.assertDictEqual(expectedNewUserDict, newUserDict)

    def test_sendEmailNotifications(self):
        emailTool = mysql_grants_generator.email_tool.EmailTool
        emailTool.sendMail = mock.MagicMock(return_value=None)
        emailTool.sendEmailNotifications = mock.MagicMock(return_value=None)
        emailTool.sendAccessNotification = mock.MagicMock(return_value=None)

        newUserDict = {"aNewUser@Host": {mysql_grants_generator.CLUSTERS_KEY: set(['aCluster']),
                                         mysql_grants_generator.PASSWORD_KEY: 'aRandPass',
                                         mysql_grants_generator.TEMPLATE_KEY: mysql_grants_generator.TEMPLATE_INVITE},
                       "bNewUser@Host": {mysql_grants_generator.CLUSTERS_KEY: set(['bCluster']),
                                         mysql_grants_generator.PASSWORD_KEY: 'bSavedPass',
                                         mysql_grants_generator.TEMPLATE_KEY: mysql_grants_generator.TEMPLATE_ACCESS}
                       }
        expectedPasswordInvites = [mock.call(set(['aCluster']), "aNewUser@Host",
                                             'aRandPass', ['aNewEmail@domain.com'])]
        expectedAccessNotifications = [mock.call(set(['bCluster']), "bNewUser@Host",
                                                 'bSavedPass', 'defaultCluster', None)]
        mysql_grants_generator.sendEmailNotifications(self.autoGrantConfig,
                                                      newUserDict, 'defaultCluster')
        emailTool.sendChangePasswordInvite.assert_has_calls(expectedPasswordInvites)
        emailTool.sendAccessNotification.assert_has_calls(expectedAccessNotifications)

# IMPLEMENT THESE TESTS IF TIME
# def test_main(self):

if __name__ == '__main__':
    unittest.main()

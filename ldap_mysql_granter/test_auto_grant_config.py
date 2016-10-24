#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_auto_grant_config tests the nagios config formatter
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
#  This script requires the following packages to be installed:
#   mock==1.0.1
#   PyYAML==3.11

import unittest
import urlparse
import auto_grant_config
import logging
import sys
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)


class TestLdapGrantMapper(unittest.TestCase):
    yamlDict = None
    ldapUrl = "ldaps://ldap.example.com"
    productManagersList = ["tom", "dick", "harry"]

    def setUp(self):
        """use a custom yaml file
           NOTE: the overrideYamlDictForTests should only be called from tests
        """
        self.yamlDict = {'ldap_server_url': self.ldapUrl,
                         'override_groups': {
                             'product_managers': self.productManagersList},
                         'group_to_grants_map': {
                             # db cluster
                             'cluster1': {
                                 # ldap group to expand per user
                                 'group1': {
                                     # @host component of username
                                     'host1': {
                                         # database.table: Permissions to GRANT
                                         '*.*': ["SELECT", "INSERT", "UPDATE",
                                                 "DELETE"]
                                     },
                                     'host2': {
                                         # database.table: Permissions to GRANT
                                         'aDB.aTable': ["DROP"],
                                         'bDB.bTable': ["ALL PRIVILEGES"]
                                     }
                                 },
                                 'group2': {'%': {'*.*': ["SELECT"]}}
                             },
                             'cluster2': {
                                 'group2': {'%': {'*.*': ["SELECT"]}}
                             }
                         }}
        self.autoGrantConfig = auto_grant_config.AutoGrantConfig('integration_test.yaml')
        self.autoGrantConfig.overrideYamlDictForTests(self.yamlDict)

    def test_getDbClusters(self):
        """tests the getDbClusters function
           returns a valid list of server strings
        """
        clusters = self.autoGrantConfig.getDbClusters()
        self.assertItemsEqual(self.yamlDict['group_to_grants_map'].keys(),
                              clusters)

    def test_getHosts(self):
        """tests the getDbClusters function
            returns a valid list of server strings
        """
        hosts = self.autoGrantConfig.getHostsForGroup('group1')
        self.assertItemsEqual(['host1', 'host2'], hosts)
        hosts = self.autoGrantConfig.getHostsForGroup('group2')
        self.assertItemsEqual(['%'], hosts)

    def test_getGrantList(self):
        """tests the getGrant function returns a valid list of GRANT strings
        """
        streamHandler = logging.StreamHandler(sys.stdout)
        logger = logging.getLogger('auto_grant_config')
        loggerLevel = logger.level  # Save level
        logger.addHandler(streamHandler)
        # test on cluster1 for group1 at host1
        grantList = self.autoGrantConfig.getGrantList("'somebody'@'host1'",
                                                      "cluster1",
                                                      "group1")
        expectedGrantList = [{'db_table': '*.*',
                              'privileges': ["SELECT", "INSERT", "UPDATE",
                                             "DELETE"]}]
        self.assertDictEqual(expectedGrantList[0], grantList[0])
        # test on cluster1 for group1 at host2
        grantList = self.autoGrantConfig.getGrantList("'somebody'@'host2'",
                                                      "cluster1", "group1")
        expectedGrantList = [{'db_table': 'bDB.bTable',
                              'privileges': ['ALL PRIVILEGES']},
                             {'db_table': 'aDB.aTable',
                              'privileges': ['DROP']}]
        self.assertDictEqual(expectedGrantList[0], grantList[0])
        self.assertDictEqual(expectedGrantList[1], grantList[1])
        # test on cluster1 for group2 at %
        grantList = self.autoGrantConfig.getGrantList("'somebody'@'%'",
                                                      "cluster1", "group2")
        expectedGrantList = [{'db_table': '*.*', 'privileges': ['SELECT']}]
        self.assertDictEqual(expectedGrantList[0], grantList[0])
        # test on cluster2 for group2 at %
        grantList = self.autoGrantConfig.getGrantList("'somebody'@'%'",
                                                      "cluster2",
                                                      "group2")
        expectedGrantList = [{'db_table': '*.*', 'privileges': ['SELECT']}]
        self.assertDictEqual(expectedGrantList[0], grantList[0])
        # These should NOT exist so hide our expected warning for nicer output
        logger.level = logging.CRITICAL
        # test on for non existing cluster group and host
        expectedGrantList = []
        logger.level = loggerLevel  # Renable level
        self.assertItemsEqual([], expectedGrantList)

    def test_getCustomMysqlGroups(self):
        """tests the getCustomMysqlGroups function returns a valid list
        """
        customGroups = self.autoGrantConfig.getCustomMysqlGroups()
        self.assertTrue(isinstance(customGroups, dict))
        self.assertEquals(self.productManagersList,
                          customGroups['product_managers'])

    def test_getLdapURL(self):
        """tests the getLdapURL function returns a valid url
        """
        url = self.autoGrantConfig.getLdapURL()
        self.assertTrue(isinstance(url, str))
        parsedUrl = urlparse.urlparse(url)
        self.assertTrue(0 < len(parsedUrl.scheme))
        self.assertTrue(0 < len(parsedUrl.netloc))
        self.assertEquals(self.ldapUrl, url)

if __name__ == '__main__':
    unittest.main()

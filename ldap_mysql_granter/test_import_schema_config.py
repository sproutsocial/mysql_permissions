#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_import_schema_config tests the nagios config formatter
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
#  This script requires the following packages to be installed:
#   mock==1.0.1
#   PyYAML==3.11

import import_schema_config
import logging
import os
import unittest
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)


class TestImportSchemaConfig(unittest.TestCase):
    yamlDict = None
    ldapUrl = "ldaps://ldap.example.com"
    productManagersList = ["tom", "dick", "harry"]

    def setUp(self):
        """use a custom yaml file
           NOTE: the overrideYamlDictForTests should only be called from tests
        """
        self.yamlDict = {
            'mysql_users': {
                'amysql.ip.example.com':
                    ["'adeveloper'@'%'"]},
            'mysql_schemas': {
                'amysql.ip.example.com':
                    ["bdb", "adb"],
                'bmysql.ip.example.com':
                    ["cdb"]},
            }
        yamlFile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "import_schema.yaml")
        self.importSchemaConfig = import_schema_config.ImportSchemaConfig(yamlFile)
        self.importSchemaConfig.overrideYamlDictForTests(self.yamlDict)
        self.importEmptySchemaConfig = import_schema_config.ImportSchemaConfig(yamlFile)
        self.importEmptySchemaConfig.overrideYamlDictForTests("{}")

    def test_getMysqlUsers(self):
        """tests the getMysqlUsers function
           returns a valid dict of servers => users
        """
        users = self.importSchemaConfig.getMysqlUsers()
        self.assertItemsEqual(users, ["amysql.ip.example.com"])
        self.assertItemsEqual(self.yamlDict['mysql_users'].keys(),
                              ["amysql.ip.example.com"])
        self.assertItemsEqual(self.yamlDict['mysql_users']['amysql.ip.example.com'],
                              ["'adeveloper'@'%'"])

    def test_getMysqlSchemas(self):
        """tests the getMysqlSchemas function
            returns a valid dict of servers => dbs
        """
        schemas = self.importSchemaConfig.getMysqlSchemas()
        self.assertItemsEqual(schemas, ["amysql.ip.example.com", "bmysql.ip.example.com"])
        self.assertItemsEqual(self.yamlDict['mysql_schemas'].keys(),
                              ["amysql.ip.example.com", "bmysql.ip.example.com"])
        self.assertItemsEqual(self.yamlDict['mysql_schemas']['amysql.ip.example.com'],
                              ["bdb", "adb"])
        self.assertItemsEqual(self.yamlDict['mysql_schemas']['bmysql.ip.example.com'],
                              ["cdb"])


if __name__ == '__main__':
    unittest.main()

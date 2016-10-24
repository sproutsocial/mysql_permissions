#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_import_schema is used to test the mysql grants generator
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
import import_schema_tool
import import_schema_config
import unittest
import test_mysql_query_tool
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


class TestImportSchema(unittest.TestCase):

    def setUp(self):
        """use a custom yaml file
           NOTE: the overrideYamlDictForTests should only be called from tests
        """
        self.echoOnly = True
        self.username = "localUsername"
        self.password = "localPassword"
        self.backupPath = "backuppath"
        self.yamlConf = "path/to/conf.yaml"
        self.mockedSchemaImportTool = import_schema_tool.SchemaImportTool(self.echoOnly, self.backupPath, self.username, self.password)
        # Save SchemaImportTool unmocked
        self._unmockedSchemaImportToolImportUsers = self.mockedSchemaImportTool.importUsers
        self._unmockedSchemaImportToolImportSchema = self.mockedSchemaImportTool.importSchema
        # Save MysqlQueryTool unmocked
        self._unmockedMysqlQueryToolUserExists = import_schema_tool.mysql_query_tool.MysqlQueryTool.userExists
        self._unmockedMysqlQueryToolQueryUserGrants = import_schema_tool.mysql_query_tool.MysqlQueryTool.queryUserGrants
        self._unmockedMysqlQueryToolGetPasswordHash = import_schema_tool.mysql_query_tool.MysqlQueryTool.getPasswordHash
        self._unmockedMysqlQueryToolGetCursor = import_schema_tool.mysql_query_tool.MysqlQueryTool.getCursor

        # Mock SchemaImportTool out
        self.mockedSchemaImportTool.importUsers = mock.MagicMock(return_value=None)
        self.mockedSchemaImportTool.importSchema = mock.MagicMock(return_value=None)
        # Mock MysqlQueryTool out
        import_schema_tool.mysql_query_tool.MysqlQueryTool.userExists = mock.MagicMock(return_value=True)
        import_schema_tool.mysql_query_tool.MysqlQueryTool.queryUserGrants = mock.MagicMock(return_value={'aDB': ["SELECT"]})
        import_schema_tool.mysql_query_tool.MysqlQueryTool.getPasswordHash = mock.MagicMock(return_value="passhash")
        import_schema_tool.mysql_query_tool.MysqlQueryTool.userGrants = mock.MagicMock(return_value={'aDB': ["SELECT"]})
        import_schema_tool.mysql_query_tool.MysqlQueryTool.getCursor = mock.MagicMock(return_value=test_mysql_query_tool.FakeMysqlCursor())

    def tearDown(self):
        # Restore SchemaImportTool from unmocked
        import_schema_tool.SchemaImportTool.importUsers = self._unmockedSchemaImportToolImportUsers
        import_schema_tool.SchemaImportTool.importSchema = self._unmockedSchemaImportToolImportSchema
        # Restore MySQLQueryTool from unmocked
        import_schema_tool.mysql_query_tool.MysqlQueryTool.userExists = self._unmockedMysqlQueryToolUserExists
        import_schema_tool.mysql_query_tool.MysqlQueryTool.queryUserGrants = self._unmockedMysqlQueryToolQueryUserGrants
        import_schema_tool.mysql_query_tool.MysqlQueryTool.getPasswordHash = self._unmockedMysqlQueryToolGetPasswordHash
        import_schema_tool.mysql_query_tool.MysqlQueryTool.getCursor = self._unmockedMysqlQueryToolGetCursor

    # @unittest.skip("wip")
    @mock.patch.object(import_schema_tool.mysql_query_tool.MySQLdb, "connect")
    def test_importUsers(self, mysqlConnMock):
        mysqlConnMock.return_value = test_mysql_query_tool.FakeMysqlConnection()
        yamlConf = {'mysql_users': {'host2': ["'user'@'origin'"]}}
        importSchemaConfig = import_schema_config.ImportSchemaConfig()
        importSchemaConfig.overrideYamlDictForTests(yamlConf)
        # unmock
        schemaImportTool = import_schema_tool.SchemaImportTool(self.echoOnly, self.backupPath, self.username, self.password)
        schemaImportTool.remoteMysqlUser = "remoteMysqlUser"
        schemaImportTool.remoteMysqlPass = "remoteMysqlPass"
        with captured_output() as (out, err):
            schemaImportTool.importUsers(importSchemaConfig)
            outStr = out.getvalue().strip()
            outLines = outStr.splitlines()
            expectedLines = [
                "mysql -h localhost -u localUsername -plocalPassword mysql -e \"DROP USER 'user'@'origin'\"",
                "mysql -h localhost -u localUsername -plocalPassword mysql -e \"CREATE USER 'user'@'origin' IDENTIFIED BY PASSWORD 'passhash'\"",
                "mysql -h localhost -u localUsername -plocalPassword mysql -e \"GRANT SELECT ON aDB TO 'user'@'origin'\"",
                ]
            self.assertEquals(expectedLines[0], outLines[0])
            self.assertEquals(expectedLines[1], outLines[1])
            self.assertEquals(expectedLines[2], outLines[2])

    @mock.patch.object(import_schema_tool.mysql_backup_tool.MysqlBackupTool, "getCurrentTimeBackup")
    @mock.patch.object(import_schema_tool.mysql_query_tool.MySQLdb, "connect")
    @mock.patch("os.path.exists")
    def test_importSchema(self, pathExistsMock, mysqlConnMock, getCurrentTimeBackupMock):
        pathExistsMock.return_value = True
        getCurrentTimeBackupMock.return_value = "20150904-150131"
        mysqlConnMock.return_value = test_mysql_query_tool.FakeMysqlConnection()
        yamlConf = {'mysql_schemas': [{'host1': [{'bDB': 'dDB'}, {'aDB': 'dDB'}]}]}
        importSchemaConfig = import_schema_config.ImportSchemaConfig()
        importSchemaConfig.overrideYamlDictForTests(yamlConf)
        # unmock
        self.mockedSchemaImportTool.importSchema = self._unmockedSchemaImportToolImportSchema
        self.mockedSchemaImportTool.remoteMysqlUser = "remoteMysqlUser"
        self.mockedSchemaImportTool.remoteMysqlPass = "remoteMysqlPass"
        with captured_output() as (out, err):
            self.mockedSchemaImportTool.importSchema(importSchemaConfig)
            outStr = out.getvalue().strip()
            outLines = outStr.splitlines()
            expectedLines = [
                "mysql -h localhost -u localUsername -plocalPassword mysql -e \"CREATE DATABASE IF NOT EXISTS dDB\"",
                "mysqldump --single-transaction --no-data --host=host1 --user=remoteMysqlUser --password=remoteMysqlPass bDB > backuppath/20150904-150131/host1/bDB.sql",
                "mysql --host=localhost --user=localUsername --password=localPassword dDB < backuppath/20150904-150131/host1/bDB.sql",
                "mysql -h localhost -u localUsername -plocalPassword mysql -e \"CREATE DATABASE IF NOT EXISTS dDB\"",
                "mysqldump --single-transaction --no-data --host=host1 --user=remoteMysqlUser --password=remoteMysqlPass aDB > backuppath/20150904-150131/host1/aDB.sql",
                "mysql --host=localhost --user=localUsername --password=localPassword dDB < backuppath/20150904-150131/host1/aDB.sql",
            ]
            self.assertEquals(expectedLines[0], outLines[0])
            self.assertEquals(expectedLines[1], outLines[1])
            self.assertEquals(expectedLines[2], outLines[2])
            self.assertEquals(expectedLines[3], outLines[3])
            self.assertEquals(expectedLines[4], outLines[4])
            self.assertEquals(expectedLines[5], outLines[5])
        # remock
        self.mockedSchemaImportTool.importSchema = mock.MagicMock(return_value=None)

    @mock.patch.object(import_schema_config.ImportSchemaConfig, "__new__", create=False)
    def test_start(self, schemaConfig):
        yamlConfFile = None
        yamlConf = {'mysql_users': {'host': "'user'@'host'"}}
        importSchemaConfig = import_schema_config.ImportSchemaConfig()
        importSchemaConfig.overrideYamlDictForTests(yamlConf)
        schemaConfig.return_value = importSchemaConfig
        self.mockedSchemaImportTool.start(yamlConfFile)
        self.mockedSchemaImportTool.importUsers.assert_called_once_with(importSchemaConfig)
        self.mockedSchemaImportTool.importSchema.assert_called_once_with(importSchemaConfig)


class TestSchemaImportMain(unittest.TestCase):
    def setUp(self):
        """use a custom yaml file
           NOTE: the overrideYamlDictForTests should only be called from tests
        """
        self._echoOnly = True
        self._username = "username"
        self._password = "password"
        self._backupPath = "backuppath"
        self._yamlConf = "path/to/conf.yaml"
        self._unmockedSchemaImportToolStart = import_schema_tool.SchemaImportTool.start
        import_schema_tool.SchemaImportTool.start = mock.MagicMock(return_value=None)

    def tearDown(self):
        # Restore from unmocked
        import_schema_tool.SchemaImportTool.start = self._unmockedSchemaImportToolStart
        pass

    def test_main(self):
        import_schema_tool.main(["-u", self._username, "-p", self._password, "-b", self._backupPath, "-e", "-y", self._yamlConf])
        startCall = [mock.call(self._yamlConf)]
        import_schema_tool.SchemaImportTool.start.assert_has_calls(startCall)


if __name__ == '__main__':
    unittest.main()

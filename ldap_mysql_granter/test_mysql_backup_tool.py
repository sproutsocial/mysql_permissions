#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_mysql_backup_tool are the tests associated with the mysql_backup_tool
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""

from contextlib import contextmanager
from StringIO import StringIO
import datetime
import logging
import mock
import mysql_backup_tool
import os
import shutil
import sys
import unittest
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


class TestMysqlBackupTool(unittest.TestCase):
    def setUp(self):
        echoOnly = True
        self._cluster = "cluster"
        self._username = "username"
        self._password = "password"
        self._fakeBackupPath = "./testMysqlBackup"
        self._mysqlBackupTool = mysql_backup_tool.MysqlBackupTool(echoOnly, self._fakeBackupPath)
        self._backupName = self._mysqlBackupTool.getCurrentTimeBackup()
        self._backupPath = os.path.join(self._fakeBackupPath, self._backupName, self._cluster)
        if not os.path.exists(self._backupPath):
            os.makedirs(self._backupPath)
        open(os.path.join(self._backupPath, "aDB.sql"), 'a').close()
        open(os.path.join(self._backupPath, "bDB.bTable.sql"), 'a').close()

    def tearDown(self):
        sys.stdout.write(self._fakeBackupPath)
        shutil.rmtree(self._fakeBackupPath)

    def test_performMySQLDump(self):
        with captured_output() as (out, err):
            dumpFile = "path/to/dump.sql"
            self._mysqlBackupTool.performMySQLDump("theCluster", self._username, self._password, "theDB theTable", dumpFile, ["--single-transaction", "--no-data"])
            outStr = out.getvalue().strip()
            self.assertEquals(outStr, "mysqldump --single-transaction --no-data --host=%s --user=%s --password=%s theDB theTable > %s" % ("theCluster", self._username, self._password, dumpFile))

    @mock.patch("os.path.exists")
    def test_restoreFromMySQLDump(self, pathExistsMock):
        pathExistsMock.return_value = True
        with captured_output() as (out, err):
            dumpFile = "path/to/dump.sql"
            self._mysqlBackupTool.restoreFromMySQLDump("theCluster", self._username, self._password, "theDB", dumpFile)
            outStr = out.getvalue().strip()
            self.assertEquals(outStr, "mysql --host=%s --user=%s --password=%s theDB < %s" % ("theCluster", self._username, self._password, dumpFile))

    def test_performMySQLDumpList(self):
        aDBList = ["aDB"]
        with captured_output() as (out, err):
            self._mysqlBackupTool.performMySQLDumpList(self._cluster, self._username, self._password, self._backupName, aDBList)
            outStr = out.getvalue().strip()
            self.assertEquals(outStr, "mysqldump --single-transaction --host=%s --user=%s --password=%s aDB > %s" % (self._cluster, self._username, self._password, os.path.join(self._backupPath, "aDB.sql")))
        bDBList = [("bDB", "bTable")]
        with captured_output() as (out, err):
            self._mysqlBackupTool.performMySQLDumpList(self._cluster, self._username, self._password, self._backupName, bDBList)
            outStr = out.getvalue().strip()
            self.assertEquals(outStr, "mysqldump --single-transaction --host=%s --user=%s --password=%s bDB bTable > %s" % (self._cluster, self._username, self._password, os.path.join(self._backupPath, "bDB.bTable.sql")))

    def test_restoreFromMySQLDumpList(self):
        aDBList = ["aDB"]
        with captured_output() as (out, err):
            self._mysqlBackupTool.restoreFromMySQLDumpList(self._cluster, self._username, self._password, self._backupName, aDBList)
            outStr = out.getvalue().strip()
            self.assertEquals(outStr, "mysql --host=%s --user=%s --password=%s aDB < %s" % (self._cluster, self._username, self._password, os.path.join(self._backupPath, "aDB.sql")))
        bDBList = [("bDB", "bTable")]
        with captured_output() as (out, err):
            self._mysqlBackupTool.restoreFromMySQLDumpList(self._cluster, self._username, self._password, self._backupName, bDBList)
            outStr = out.getvalue().strip()
            self.assertEquals(outStr, "mysql --host=%s --user=%s --password=%s bDB < %s" % (self._cluster, self._username, self._password, os.path.join(self._backupPath, "bDB.bTable.sql")))

    def test_pruneing(self):
        now = datetime.timedelta(days=0)
        yesterday = datetime.timedelta(days=1)
        currentTime = self._mysqlBackupTool.getCurrentTimeBackup()
        pruneNow = self._mysqlBackupTool.getPruneBeforeFromTimeDelta(now)
        pruneYesterday = self._mysqlBackupTool.getPruneBeforeFromTimeDelta(yesterday)
        self._mysqlBackupTool.pruneBefore(pruneYesterday)
        self.assertEquals(currentTime, pruneNow)


class TestMysqlBackupToolMain(unittest.TestCase):
    def setUp(self):
        self._backupPath = "./testMysqlBackup"
        self._echoOnly = True
        self._unmockedPerformMySQLDumpList = mysql_backup_tool.MysqlBackupTool.performMySQLDumpList
        self._mysqlBackupTool = mysql_backup_tool.MysqlBackupTool(self._echoOnly, self._backupPath)
        mysql_backup_tool.MysqlBackupTool.performMySQLDumpList = mock.MagicMock(
            return_value=None)

    def tearDown(self):
        mysql_backup_tool.MysqlBackupTool.performMySQLDumpList = self._unmockedPerformMySQLDumpList

    def test_main(self):
        cluster = "cluster"
        username = "username"
        password = "password"
        backupName = self._mysqlBackupTool.getCurrentTimeBackup()
        dbName = "db"
        backupList = [dbName]
        # test without a filter
        mysql_backup_tool.main(["-c", cluster, "-u", username, "-p", password, "-b",
                                self._backupPath, "-D", dbName, "-e"])
        expectedCalls = [mock.call(cluster, username, password, backupName, backupList)]
        mysql_backup_tool.MysqlBackupTool.performMySQLDumpList.assert_has_calls(
            expectedCalls)


if __name__ == '__main__':
    unittest.main()

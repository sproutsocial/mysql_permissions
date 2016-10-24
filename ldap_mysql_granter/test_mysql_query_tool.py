#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_mysql_query_tool are the test associated with the mysql_query_tool
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""

import logging
import mock
import mysql_query_tool
import unittest
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)
ALL_PRIVS_USER = "allprivs"


class FakeMysqlCursor(object):
    def __init__(self):
        self._lastQuery = None
        self._lastQArgs = None
        self._closed = False

    def close(self):
        self._closed = True

    def execute(self, query, qArgs):
        self._lastQuery = query
        self._lastQArgs = qArgs

    def fetchall(self):
        callDict = {self._lastQuery: self._lastQArgs}
        results = tuple([callDict])
        if self._lastQuery == "SELECT User, Host FROM mysql.user":
                results = tuple([{'Host': '%', 'User': 'grant_bot'},
                                 {'Host': '%', 'User': 'revert_bot'}])
        elif self._lastQuery.startswith("SHOW GRANTS FOR"):
            user, host = self._lastQArgs
            userAtHost = user+"@"+host
            if user == ALL_PRIVS_USER:
                results = tuple([{"Grants for "+userAtHost: "GRANT ALL PRIVILEGES ON *.* TO '"+user+"'@'"+host+"' IDENTIFIED BY PASSWORD '*DEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF' WITH GRANT OPTION"}])
        return results


class FakeMysqlConnection(object):
    def __init__(self):
        self._autocommit = True
        self._commits = 0
        self._rollbacks = 0

    def close(self):
        pass

    def autocommit(self, val):
        self._autocommit = val

    def commit(self):
        self._commits += 1

    def rollback(self):
        self._rollbacks += 1

    def cursor(self, curType):
        return FakeMysqlCursor()


class TestMysqlQueryTool(unittest.TestCase):

    def setUp(self):
        self._cluster = "cluster"
        self._username = "username"
        self._password = "password"
        self._fakeConnection = FakeMysqlConnection()
        self._fakeCursor = FakeMysqlCursor()
        echoAccessLevel = mysql_query_tool.QAL_ALL
        queryAccessLevel = mysql_query_tool.QAL_ALL
        mysql_query_tool.MySQLdb.connect = mock.MagicMock(
            return_value=self._fakeConnection)
        self._mysqlQueryTool = mysql_query_tool.MysqlQueryTool(self._cluster, self._username, self._password, echoAccessLevel, queryAccessLevel)
        self._mysqlQueryTool.getCursor = mock.MagicMock(
            return_value=self._fakeCursor)

    def test_closeConnection(self):
        self._mysqlQueryTool.closeConnection()
        self.assertEquals(None, self._mysqlQueryTool._connection)

    def test_getCmdLineQuery(self):
        user = "test"
        host = "%"
        cmdLineQuery = self._mysqlQueryTool.getCmdLineQuery("SHOW GRANTS FOR %s@%s", (user, host))
        expectedQuery = "mysql -h "+self._cluster+" -u "+self._username+" -p"+self._password+' -e "SHOW GRANTS FOR \'test\'@\'%\'"'
        self.assertEquals(expectedQuery, cmdLineQuery)

    def test_transactions(self):
        # test successful transaction
        self.assertEquals(0, self._fakeConnection._commits)
        self.assertEquals(True, self._fakeConnection._autocommit)
        self._mysqlQueryTool.beginTransaction()
        self.assertEquals(False, self._fakeConnection._autocommit)
        self._mysqlQueryTool.commitTransaction()
        self.assertEquals(1, self._fakeConnection._commits)
        self.assertEquals(True, self._fakeConnection._autocommit)
        # test failed transaction
        self.assertEquals(0, self._fakeConnection._rollbacks)
        self.assertEquals(True, self._fakeConnection._autocommit)
        self._mysqlQueryTool.beginTransaction()
        self.assertEquals(False, self._fakeConnection._autocommit)
        self._mysqlQueryTool.rollbackTransaction()
        self.assertEquals(True, self._fakeConnection._autocommit)
        self.assertEquals(1, self._fakeConnection._rollbacks)

    def test_queryVersion(self):
        result = self._mysqlQueryTool.queryVersion()
        self.assertEquals(1, len(result))
        self.assertDictEqual({'SELECT VERSION()': None}, result[0])

    def test_queryFlushPrivileges(self):
        result = self._mysqlQueryTool.queryFlushPrivileges()
        self.assertEquals(1, len(result))
        self.assertDictEqual({'FLUSH PRIVILEGES': None}, result[0])

    def test_queryGrant(self):
        allPrivsUserAtHost = ALL_PRIVS_USER+"@localhost"
        result = self._mysqlQueryTool.queryGrant(allPrivsUserAtHost, ["SELECT", "insert", "blah"], "db.table")
        self.assertEquals(1, len(result))
        self.assertDictEqual({'GRANT INSERT, SELECT ON db.table TO %s@%s': (ALL_PRIVS_USER, 'localhost')}, result[0])

    def test_queryUserGrants(self):
        result = self._mysqlQueryTool.queryUserGrants(ALL_PRIVS_USER+"@localhost")
        self.assertDictEqual({'*.*': set(['ALL PRIVILEGES'])}, result)

    def test_queryRevoke(self):
        allPrivsUserAtHost = ALL_PRIVS_USER+"@localhost"
        result = self._mysqlQueryTool.queryRevoke(allPrivsUserAtHost, ["SELECT"], "db.table")
        self.assertEquals(1, len(result))
        self.assertDictEqual({'REVOKE SELECT ON db.table FROM %s@%s': (ALL_PRIVS_USER, 'localhost')}, result[0])

    def test_getGrantDeltaDict(self):
        userAtHost = ALL_PRIVS_USER+'@localhost'
        dbTable = "*.*"
        privileges = ["SELECT"]
        grantDeltaDict = self._mysqlQueryTool.getGrantDeltaDict(userAtHost, dbTable, privileges)
        expectedGrantDeltaDict = {'grants': set([]),
                                  'revokes': self._mysqlQueryTool.getAllPrivileges() - set(privileges)}
        self.assertDictEqual(expectedGrantDeltaDict, grantDeltaDict)

    def test_findAllUsers(self):
        allUserDict = self._mysqlQueryTool.findAllUsers()
        expectedDict = set(['revert_bot@%', 'grant_bot@%'])
        self.assertEquals(expectedDict, allUserDict)

    def test_userExists(self):
        exists = self._mysqlQueryTool.userExists("grant_bot", "%")
        self.assertTrue(exists)

    def test_createUser(self):
        newUserAtHost = "user@host"
        newPassword = "password"
        self._mysqlQueryTool.createUser(newUserAtHost, newPassword)
        self.assertEquals("CREATE USER %s@%s IDENTIFIED BY %s", self._fakeCursor._lastQuery)
        self.assertItemsEqual(("user", "host", "password"), self._fakeCursor._lastQArgs)

    def test_dropUser(self):
        newUserAtHost = "user@host"
        self._mysqlQueryTool.dropUser(newUserAtHost)
        self.assertEquals("DROP USER %s@%s", self._fakeCursor._lastQuery)
        self.assertItemsEqual(("user", "host"), self._fakeCursor._lastQArgs)


class TestMysqlQueryToolMain(unittest.TestCase):
    def setUp(self):
        self._backupPath = "./testMysqlBackup"
        self._echoOnly = True
        self._unmockedConnect = mysql_query_tool.MysqlQueryTool.connect
        self._unmockedQueryMySQL = mysql_query_tool.MysqlQueryTool.queryMySQL
        mysql_query_tool.MysqlQueryTool.connect = mock.MagicMock(
            return_value=None)
        mysql_query_tool.MysqlQueryTool.queryMySQL = mock.MagicMock(
            return_value=None)

    def tearDown(self):
        mysql_query_tool.MysqlQueryTool.connect = self._unmockedQueryMySQL
        mysql_query_tool.MysqlQueryTool.queryMySQL = self._unmockedQueryMySQL

    def test_main(self):
        cluster = "cluster"
        username = "username"
        password = "password"
        dbName = "db"
        query = "SELECT VERSION()"
        qArgs = None
        mysql_query_tool.main(["-c", cluster, "-u", username, "-p", password, "-d", dbName, "-q", query])
        expectedCalls = [mock.call(mysql_query_tool.QAL_ALL, query, qArgs)]
        mysql_query_tool.MysqlQueryTool.queryMySQL.assert_has_calls(
            expectedCalls)


if __name__ == '__main__':
    logging.basicConfig(level=logging.CRITICAL)
    unittest.main()

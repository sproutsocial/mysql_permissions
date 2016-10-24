#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
mysql_query_tool tool to perform mysql queries
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
import argparse
import contextlib
import logging
import MySQLdb
import pprint
import re
import sys

logger = logging.getLogger(__name__)

# Query Access Levels
QAL_NONE = 0
QAL_READ = 1
QAL_READ_WRITE = 2
QAL_READ_WRITE_DELETE = 3
QAL_ALL = 4
HIDE_PASS = True


class MysqlQueryTool(object):

    def __init__(self, cluster, mysqlUser, mysqlPass, echoAccessLevel,
                 queryAccessLevel, database=''):
        self._cluster = cluster
        self._mysqlUser = mysqlUser
        self._mysqlPass = mysqlPass
        self._echoAccessLevel = echoAccessLevel
        self._queryAccessLevel = queryAccessLevel
        self._database = database
        self._connection = None
        self.connect()

    def connect(self):
        if self._connection is None:
            self._connection = MySQLdb.connect(self._cluster, self._mysqlUser, self._mysqlPass,
                                               self._database)

    def closeConnection(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def getCmdLineQuery(self, query, qArgs):
        clusterArg = ""
        usernameArg = ""
        passwordArg = ""
        databaseArg = ""
        if self._cluster is not None and 0 < len(self._cluster):
            clusterArg = " -h %s" % self._cluster
        if self._mysqlUser is not None and 0 < len(self._mysqlUser):
            usernameArg = " -u %s" % self._mysqlUser
        if self._mysqlPass is not None and 0 < len(self._mysqlPass):
            passwordArg = " -p%s" % self._mysqlPass
        if self._database is not None and 0 < len(self._database):
            databaseArg = " %s" % self._database
        sql = query
        if qArgs is not None:
            literalQuery = query.replace("%s", "'%s'")
            sql = literalQuery % qArgs
        cmdLineQuery = ('mysql%s%s%s%s -e "%s"' %
                        (clusterArg, usernameArg, passwordArg, databaseArg,
                         sql))
        return cmdLineQuery

    def beginTransaction(self):
        self._connection.autocommit(False)

    def rollbackTransaction(self):
        self._connection.rollback()
        self._connection.autocommit(True)

    def commitTransaction(self):
        self._connection.commit()
        self._connection.autocommit(True)

    def getCursor(self):
        cursor = None
        if self._connection is not None:
            cursor = self._connection.cursor(MySQLdb.cursors.DictCursor)
        return cursor

    def queryMySQL(self, accessLevel, query, qArgs):
        result = None
        if self._queryAccessLevel < accessLevel:
            if self._echoAccessLevel < accessLevel:
                logger.debug("skipping destructive query: %s, ",
                             self.getCmdLineQuery(query, qArgs))
            else:
                print self.getCmdLineQuery(query, qArgs)
        else:
            printableQuery = query
            if qArgs is not None:
                printableQuery = (query % qArgs)
            logger.debug(printableQuery)
            with contextlib.closing(
                    self.getCursor()) as cursor:
                try:
                    cursor.execute(query, qArgs)
                    result = cursor.fetchall()
                    logger.debug("raw data:%s", pprint.pformat(result))
                except Exception as e:
                    logger.error("query[%s] failed with exception:%s", printableQuery, pprint.pformat(e))
                    raise e

        return result

    def queryVersion(self):
        qArgs = None
        return self.queryMySQL(QAL_READ, "SELECT VERSION()", qArgs)

    def queryFlushPrivileges(self):
        qArgs = None
        return self.queryMySQL(QAL_READ_WRITE, "FLUSH PRIVILEGES", qArgs)

    def queryGrant(self, userAtHost, privileges,
                   db_table):
        ret = None
        userPart, hostPart = (x.strip("'") for x in userAtHost.rsplit('@', 1))
        privilegeStr = self.getVerifiedPrivilegeString(privileges)
        query = "GRANT " + privilegeStr + " ON " + db_table + " TO %s@%s"
        qArgs = (userPart, hostPart)
        ret = self.queryMySQL(QAL_READ_WRITE, query, qArgs)
        return ret

    def queryUserGrants(self, userAtHost):
        query = "SHOW GRANTS FOR %s@%s"
        userPart, hostPart = (x.strip("'") for x in userAtHost.rsplit('@', 1))
        qArgs = (userPart, hostPart)
        result = self.queryMySQL(QAL_READ, query, qArgs)
        userGrantDict = {}
        if result is not None:
            for row in result:
                for value in row.values():
                    matches = re.search(r"^GRANT (.*) ON (.*) TO ", value)
                    db_table = matches.group(2).strip().replace("`", "")
                    grants = set(matches.group(1).split(", "))
                    if db_table not in userGrantDict:
                        userGrantDict[db_table] = grants
                    else:
                        userGrantDict[db_table] |= grants
        return userGrantDict

    def queryRevoke(self, userAtHost, privileges,
                    db_table):
        ret = None
        userPart, hostPart = (x.strip("'") for x in userAtHost.rsplit('@', 1))
        privilegeStr = self.getVerifiedPrivilegeString(privileges)
        query = "REVOKE " + privilegeStr + " ON " + db_table + " FROM %s@%s"
        qArgs = (userPart, hostPart)
        ret = self.queryMySQL(QAL_READ_WRITE_DELETE, query, qArgs)
        return ret

    def getGrantDeltaDict(self, userAtHost, dbTable, privileges):
        userPart, hostPart = (x.strip("'") for x in userAtHost.rsplit('@', 1))
        correctGrants = set(self.getVerifiedPrivilegeString(privileges).split(", "))
        grantDeltaDict = {'grants': correctGrants, 'revokes': set([])}
        userGrantDict = {}
        userExists = self.userExists(userPart, hostPart)
        if userExists:
            userGrantDict = self.queryUserGrants(userAtHost)
        if dbTable in userGrantDict:
            currentGrants = set(self.getVerifiedPrivilegeString(userGrantDict[dbTable]).split(", "))
            grantDeltaDict['grants'] = correctGrants - currentGrants
            grantDeltaDict['revokes'] = currentGrants - correctGrants
        return grantDeltaDict

    def findAllUsers(self):
        query = "SELECT User, Host FROM mysql.user"
        qArgs = None
        result = self.queryMySQL(QAL_READ, query, qArgs)
        users = set()
        for row in result:
            users |= set([row["User"] + '@' + row["Host"]])
        return users

    def userExists(self, userPart, hostPart):
        query = "SELECT User, Host FROM mysql.user WHERE User = %s AND Host = %s"
        qArgs = (userPart, hostPart)
        result = self.queryMySQL(QAL_READ, query, qArgs)
        userExists = True
        if result is None or len(result) == 0:
            userExists = False
        return userExists

    def getPasswordHash(self, userPart, hostPart):
        query = "SELECT Password FROM mysql.user WHERE User = %s AND Host = %s"
        qArgs = (userPart, hostPart)
        result = self.queryMySQL(QAL_READ, query, qArgs)
        passwordHash = None
        if result is not None and len(result) == 1:
            passwordHash = result[0]['Password']
        return passwordHash

    def createUser(self, newUserAtHost, newPassword, useHash=False):
        for i in xrange(2):
            try:
                userPart, hostPart = newUserAtHost.rsplit('@', 1)
                newUser = userPart.strip("'")
                newHost = hostPart.strip("'")
                query = "CREATE USER %s@%s IDENTIFIED BY %s"
                if useHash:
                    query = "CREATE USER %s@%s IDENTIFIED BY PASSWORD %s"
                qArgs = (newUser, newHost, newPassword)
                return self.queryMySQL(QAL_READ_WRITE, query, qArgs)
            except Exception:
                # try and drop the user first if the create fails
                # this can sometimes happen after a restore
                self.dropUser(newUserAtHost)

    def dropUser(self, newUserAtHost):
        userPart, hostPart = newUserAtHost.rsplit('@', 1)
        newUser = userPart.strip("'")
        newHost = hostPart.strip("'")
        query = "DROP USER %s@%s"
        qArgs = (newUser, newHost)
        return self.queryMySQL(QAL_READ_WRITE_DELETE, query, qArgs)

    def createDatabase(self, database):
        query = "CREATE DATABASE IF NOT EXISTS %s" % (database)
        qArgs = None
        return self.queryMySQL(QAL_READ_WRITE, query, qArgs)

    def getAllPrivileges(self):
        return set(["ALL PRIVILEGES",
                    "ALTER",
                    "ALTER ROUTINE",
                    "CREATE",
                    "CREATE ROUTINE",
                    "CREATE TEMPORARY TABLES",
                    "CREATE VIEW",
                    "CREATE USER",
                    "DELETE",
                    "DROP",
                    "EVENT",
                    "EXECUTE",
                    "FILE",
                    "GRANT OPTION",
                    "INDEX",
                    "INSERT",
                    "LOCK TABLES",
                    "PROCESS",
                    "PROXY",
                    "REFERENCES",
                    "RELOAD",
                    "REPLICATION CLIENT",
                    "REPLICATION SLAVE",
                    "SELECT",
                    "SHOW DATABASES",
                    "SHOW VIEW",
                    "SHUTDOWN",
                    "SUPER",
                    "TRIGGER",
                    "CREATE TABLESPACE",
                    "UPDATE",
                    "USAGE"])

    def getVerifiedPrivilegeString(self, privileges):
        """This list comes from show privileges to remove a privilege
           simply comment it out
        """
        allPrivileges = self.getAllPrivileges()
        privilegeStr = ""
        if "ALL PRIVILEGES" in privileges:
            privilegeStr = ", ".join(allPrivileges)
        else:
            upperPrivileges = set([x.upper() for x in privileges])
            badPrivileges = set(upperPrivileges) - allPrivileges
            for badPrivilege in badPrivileges:
                logger.error("Stripping out %s", badPrivilege)
            goodPrivileges = upperPrivileges & allPrivileges
            privilegeStr = ", ".join(goodPrivileges)
        return privilegeStr


def main(args=None):
    retCode = 0
    logLevels = {"DEBUG": logging.DEBUG,
                 "INFO": logging.INFO,
                 "WARN": logging.WARNING,
                 "ERROR": logging.ERROR,
                 "CRITICAL": logging.CRITICAL}
    parser = argparse.ArgumentParser(
        description='A tool to perform mysql queries')
    parser.add_argument('-l', '--log-level', type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
                        help="the log level")
    parser.add_argument('-c', '--cluster', type=str, default="localhost",
                        help="the mysql cluster")
    parser.add_argument('-u', '--username', type=str, default="root",
                        help="the mysql username")
    parser.add_argument('-p', '--password', type=str, default="",
                        help="the mysql password omitted for none")
    parser.add_argument('-d', '--database', type=str, default="",
                        help="the database to connect to")
    parser.add_argument('-q', '--query', type=str, default="",
                        help="the mysql query to execute")
    parsedArgs = parser.parse_args(args)
    if parsedArgs.log_level.upper() in logLevels.keys():
        logging.basicConfig(level=logLevels[parsedArgs.log_level.upper()])
    else:
        logging.basicConfig(level=logging.INFO)
        logger.warn("Unknown logLevel=%s retaining level at INFO",
                    parsedArgs.log_level)
    logger.info(pprint.pformat(parsedArgs))
    thisClass = MysqlQueryTool(parsedArgs.cluster, parsedArgs.username, parsedArgs.password,
                               QAL_ALL, QAL_ALL, parsedArgs.database)
    qArgs = None
    resultDict = thisClass.queryMySQL(QAL_ALL, parsedArgs.query, qArgs)
    logger.info(resultDict)
    logger.info("Done!")
    return retCode

if __name__ == "__main__":
    """Entry point if being run as a script"""
    sys.exit(main(sys.argv[1:]))

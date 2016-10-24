#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
mysql_grants_generator is a program to automate the generation of mysql grants
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
import argparse
import getpass
import import_schema_config
import logging
import my_dot_cnf
import mysql_backup_tool
import mysql_query_tool
import os
import pprint
import sys
logger = logging.getLogger(__name__)
DEFAULT_SCHEMA_DIR = os.path.join(os.path.expanduser("~"), 'mysqlschemas')
BACKUP_DIR_FMT = '%Y%m%d-%H%M%S'


class SchemaImportTool(object):

    def __init__(self, echoOnly, backupPath, localMysqlUser, localMysqlPass):
        self.backupPath = backupPath
        self.echoOnly = echoOnly
        self.localMysqlCluster = "localhost"
        self.localMysqlUser = localMysqlUser
        self.localMysqlPass = localMysqlPass
        self.myDotCnf = my_dot_cnf.MyDotCnf()
        self.mysqlBackupTool = mysql_backup_tool.MysqlBackupTool(self.echoOnly, self.backupPath)

    def importUsers(self, importSchemaConfig):
        mysqlUsersToImport = importSchemaConfig.getMysqlUsers()
        if mysqlUsersToImport:
            logger.info("import users", mysqlUsersToImport)
            localMysql = mysql_query_tool.MysqlQueryTool(self.localMysqlCluster,
                                                         self.localMysqlUser,
                                                         self.localMysqlPass,
                                                         mysql_query_tool.QAL_ALL,
                                                         mysql_query_tool.QAL_READ if self.echoOnly else mysql_query_tool.QAL_ALL,
                                                         "mysql")
            for cluster in mysqlUsersToImport.keys():
                remoteMysql = mysql_query_tool.MysqlQueryTool(cluster,
                                                              self.remoteMysqlUser,
                                                              self.remoteMysqlPass,
                                                              mysql_query_tool.QAL_ALL,
                                                              mysql_query_tool.QAL_READ if self.echoOnly else mysql_query_tool.QAL_ALL,
                                                              "mysql")
                for userAtHost in mysqlUsersToImport[cluster]:
                    useHash = True
                    userPart, hostPart = (x.strip("'") for x in userAtHost.split('@'))
                    passwordHash = remoteMysql.getPasswordHash(userPart, hostPart)
                    if localMysql.userExists(userPart, hostPart):
                        localMysql.dropUser(userAtHost)
                    localMysql.createUser(userAtHost, passwordHash, useHash)
                    userGrantDict = remoteMysql.queryUserGrants(userAtHost)
                    logger.info("userGrantDict=", userGrantDict)
                    for dbTable in userGrantDict.keys():
                        localMysql.queryGrant(userAtHost,
                                              userGrantDict[dbTable],
                                              dbTable)

    def importSchema(self, importSchemaConfig):
        extraArgs = ["--single-transaction", "--no-data"]
        backupName = self.mysqlBackupTool.getCurrentTimeBackup()
        mysqlSchemasToImport = importSchemaConfig.getMysqlSchemas()
        localMysql = mysql_query_tool.MysqlQueryTool(self.localMysqlCluster,
                                                     self.localMysqlUser,
                                                     self.localMysqlPass,
                                                     mysql_query_tool.QAL_ALL,
                                                     mysql_query_tool.QAL_READ if self.echoOnly else mysql_query_tool.QAL_ALL,
                                                     "mysql")
        for entry in mysqlSchemasToImport:
            cluster = entry.keys()[0]
            dbTableList = entry[cluster]
            for dbTableEntry in dbTableList:
                dbTableSrc = dbTableEntry.keys()[0]
                dbTableDst = dbTableEntry[dbTableSrc]
                dbSrc = dbTableSrc
                tableSrc = None
                if '.' in dbTableSrc:
                    dbSrc, tableSrc = dbTableSrc.split(".")
                localMysql.createDatabase(dbTableDst)
                dumpFile = self.mysqlBackupTool.getBackupSQLFile(backupName, cluster, dbSrc, tableSrc)
                self.mysqlBackupTool.performMySQLDump(cluster, self.remoteMysqlUser, self.remoteMysqlPass, dbTableSrc, dumpFile, extraArgs)
                self.mysqlBackupTool.restoreFromMySQLDump(self.localMysqlCluster, self.localMysqlUser, self.localMysqlPass, dbTableDst, dumpFile)

    def start(self, yamlConf):
        importSchemaConfig = import_schema_config.ImportSchemaConfig(yamlConf)
        self.remoteMysqlUser = self.myDotCnf.getDefaultMysqlUser()
        self.remoteMysqlPass = self.myDotCnf.getDefaultMysqlPassword()
        if self.localMysqlUser is None:
            self.localMysqlUser = raw_input("Local Username Enter for [root]: ")
            if self.localMysqlUser is "":
                self.localMysqlUser = "root"
        if self.localMysqlPass is None:
            self.localMysqlPass = getpass.getpass("Local Password: ")
        self.importUsers(importSchemaConfig)
        self.importSchema(importSchemaConfig)


def main(args=None):
    """Arg parsing and logger setup"""
    retCode = 0
    logLevels = {"DEBUG": logging.DEBUG,
                 "INFO": logging.INFO,
                 "WARN": logging.WARNING,
                 "ERROR": logging.ERROR,
                 "CRITICAL": logging.CRITICAL}
    retCode = 0
    parser = argparse.ArgumentParser(
        description='A tool to import mysql schemas it is recommended to use a ~/.my.cnf')
    parser.add_argument('-l', '--log-level', type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
                        help="the log level")
    parser.add_argument('-u', '--username', type=str, default="root",
                        help="the local mysql username")
    parser.add_argument('-p', '--password', type=str, default="",
                        help="the local mysql password")
    parser.add_argument('-b', '--backup-path', type=str,
                        default=DEFAULT_SCHEMA_DIR,
                        help="the mysql query to execute")
    parser.add_argument('-e', '--echo-only', action='store_true',
                        help="just print out the queries to run")
    parser.add_argument('-y', '--yaml-conf', type=str, default=None,
                        help="the yaml configuration path")
    parsedArgs = parser.parse_args(args)
    assert (parsedArgs.backup_path is not '/'), "must not be the root directory"
    logger.info(pprint.pformat(parsedArgs))
    if parsedArgs.log_level.upper() in logLevels.keys():
        logging.basicConfig(level=logLevels[parsedArgs.log_level.upper()])
    else:
        logging.basicConfig(level=logging.INFO)
        logger.warn("Unknown logLevel=%s retaining level at INFO",
                    parsedArgs.log_level)
    logger.info(pprint.pformat(parsedArgs))
    schemaImportTool = SchemaImportTool(parsedArgs.echo_only, parsedArgs.backup_path, parsedArgs.username, parsedArgs.password)
    schemaImportTool.start(parsedArgs.yaml_conf)
    logger.info("Done!")
    return retCode

if __name__ == "__main__":
    """Entry point if being run as a script"""
    sys.exit(main(sys.argv[1:]))

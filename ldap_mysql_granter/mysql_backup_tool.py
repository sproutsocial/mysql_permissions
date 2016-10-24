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
import shutil
import subprocess
import sys
logger = logging.getLogger(__name__)
DEFAULT_BACKUP_DIR = os.path.join(os.path.expanduser("~"), 'mysqlbackup')
BACKUP_DIR_FMT = '%Y%m%d-%H%M%S'


class MysqlDumpException(Exception):
    pass


class MysqlRestoreException(Exception):
    pass


class MysqlBackupTool(object):

    def __init__(self, echoOnly, backupPath=DEFAULT_BACKUP_DIR):
        self._echoOnly = echoOnly
        self._backupPath = backupPath

    def getBackupSQLFile(self, backupName, cluster, database, table=None):
        backupPath = os.path.join(self._backupPath, backupName, cluster)
        archive = os.path.join(backupPath, database + ".sql")
        if table is not None:
            archive = os.path.join(backupPath, database + "." + table + ".sql")
        return archive

    def performMySQLDump(self, host, username, password, dbTable, dumpFile, extraArgList=[]):
        backupPath = os.path.dirname(dumpFile)
        if backupPath is not None:
            if not os.path.exists(backupPath):
                os.makedirs(backupPath)
        extraArgs = ' '
        if 0 < len(extraArgList):
            extraArgs += " ".join(extraArgList) + ' '
        dumpCmd = ("mysqldump%s--host=%s --user=%s --password=%s %s > %s"
                   % (extraArgs, host, username, password, dbTable, dumpFile))
        if self._echoOnly is True:
            print(dumpCmd)
        else:
            logger.info("running dump: %s", dumpCmd)
            if subprocess.call(dumpCmd, shell=True) != 0:
                raise MysqlDumpException("could not perform %s" % dumpCmd)

    def restoreFromMySQLDump(self, host, username, password, database, dumpFile):
        """http://serverfault.com/questions/172950/
        backup-mysql-users-and-permissions"""
        if self._echoOnly is True or os.path.exists(dumpFile):
            restoreCmd = ("mysql --host=%s --user=%s --password=%s %s < %s"
                          % (host, username, password, database, dumpFile))
            if self._echoOnly is True:
                print(restoreCmd)
            else:
                logger.info("running restore: %s", restoreCmd)
                if subprocess.call(restoreCmd, shell=True) != 0:
                    raise MysqlRestoreException(
                        "could not perform %s" % (restoreCmd))
        else:
            logger.error("cant restore from: %s no file exists", dumpFile)

    def performMySQLDumpList(self, cluster, username, password, backupName,
                             backupList, singleTransaction=True, schemaOnly=False):
        for item in backupList:
            extraArgs = []
            if singleTransaction:
                extraArgs.append("--single-transaction")
            if schemaOnly:
                extraArgs.append("--no-data")
            table = None
            db = item
            dbTable = db
            if isinstance(item, (list, tuple)):
                db, table = item
                dbTable = db + ' ' + table
            dumpFile = self.getBackupSQLFile(backupName, cluster, db, table)
            self.performMySQLDump(cluster, username, password, dbTable, dumpFile, extraArgs)

    def restoreFromMySQLDumpList(self, cluster, username, password, restoreName, restoreList):
        for item in restoreList:
            table = None
            db = item
            if isinstance(item, (list, tuple)):
                db, table = item
            dumpFile = self.getBackupSQLFile(restoreName, cluster, db, table)
            self.restoreFromMySQLDump(cluster, username, password, db, dumpFile)

    def getPruneBeforeFromTimeDelta(self, timeDelta):
        currentTime = datetime.datetime.now()
        aWeekAgo = currentTime - timeDelta
        pruneBefore = aWeekAgo.strftime(BACKUP_DIR_FMT)
        return pruneBefore

    def getLastBackup(self):
        lastBackupDir = None
        if os.path.exists(self._backupPath):
            backupDirs = sorted(os.listdir(self._backupPath))
            if 0 < len(backupDirs):
                lastBackupDir = backupDirs[-1]
        else:
            logger.error("%s does not exist", self._backupPath)
        return lastBackupDir

    def getCurrentTimeBackup(self):
        currentTime = datetime.datetime.now()
        currentTimeDir = currentTime.strftime(BACKUP_DIR_FMT)
        return currentTimeDir

    def pruneBefore(self, pruneDate):
        while True:
            dirsToPrune = []
            for root, dirs, files in os.walk(self._backupPath):
                if len(dirs) == 0 and len(files) == 0:
                    dirsToPrune.append(root)
                elif root == self._backupPath:
                    for timeDir in dirs:
                        try:
                            datetime.datetime.strptime(timeDir, BACKUP_DIR_FMT)
                            # convertable
                            if timeDir < pruneDate:
                                dirsToPrune.append(os.path.join(root, timeDir))
                        except ValueError:
                            # malformed directory name
                            dirsToPrune.append(os.path.join(root, timeDir))
            if len(dirsToPrune) == 0:
                break
            else:
                for delDir in sorted(dirsToPrune, reverse=True):
                    shutil.rmtree(delDir)


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
    parser.add_argument('-D', '--db-list', type=str,
                        default=["--all-databases"],
                        help="the database to connect to")
    parser.add_argument('-b', '--backup-path', type=str,
                        default=DEFAULT_BACKUP_DIR,
                        help="the mysql query to execute")
    parser.add_argument('-P', '--prune-date', type=str,
                        help="prune before date in the form YYYYMMDD-hhmmss")
    parser.add_argument('-e', '--echo-only', action='store_true',
                        help="just print out the queries to run")
    parsedArgs = parser.parse_args(args)
    assert (parsedArgs.backup_path is not '/'), "must not be the root directory"
    if parsedArgs.log_level.upper() in logLevels.keys():
        logging.basicConfig(level=logLevels[parsedArgs.log_level.upper()])
    else:
        logging.basicConfig(level=logging.INFO)
        logger.warn("Unknown logLevel=%s retaining level at INFO",
                    parsedArgs.log_level)
    logger.info(pprint.pformat(parsedArgs))
    mysqlBackupTool = MysqlBackupTool(parsedArgs.echo_only, parsedArgs.backup_path)
    if parsedArgs.prune_date is not None:
        mysqlBackupTool.pruneBefore(parsedArgs.prune_date)
    else:
        backupName = mysqlBackupTool.getCurrentTimeBackup()
        mysqlBackupTool.performMySQLDumpList(parsedArgs.cluster, parsedArgs.username,
                                             parsedArgs.password, backupName,
                                             parsedArgs.db_list.split(','))
    logger.info("Done!")
    return retCode

if __name__ == "__main__":
    """Entry point if being run as a script"""
    sys.exit(main(sys.argv[1:]))

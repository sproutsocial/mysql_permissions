#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
integration_test.py used to to run a full test going through the whole process
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
from ldap_mysql_granter import mysql_query_tool
import argparse
import logging
import pprint
import os
logger = logging.getLogger(__name__)
LOG_PASSWORDS = True


def checkDbClean(cluster, mysqlUser, mysqlPass, userPart, hostPart,
                 echoOnly=False, destructive=False):
    # determine access levels from echoOnly and destructive
    echoAccessLevel = mysql_query_tool.QAL_READ_WRITE
    if destructive:
        echoAccessLevel = mysql_query_tool.QAL_READ_WRITE_DELETE
    queryAccessLevel = echoAccessLevel
    queryTool = mysql_query_tool.MysqlQueryTool(cluster, mysqlUser, mysqlPass,
                                                echoAccessLevel,
                                                queryAccessLevel,
                                                LOG_PASSWORDS)
    userExists = queryTool.userExists(userPart, hostPart)
    # verify db is clean
    assert (userExists is False), "db not clean run vagrant ssh -c 'sudo /auto_grant/provision/cleanup_db.sh'"


def checkUserHasGrants(cluster, mysqlUser, mysqlPass, userPart, hostPart,
                       echoOnly=False, destructive=False):
    # determine access levels from echoOnly and destructive
    echoAccessLevel = mysql_query_tool.QAL_READ_WRITE
    if destructive:
        echoAccessLevel = mysql_query_tool.QAL_READ_WRITE_DELETE
    queryAccessLevel = echoAccessLevel
    queryTool = mysql_query_tool.MysqlQueryTool(cluster, mysqlUser, mysqlPass,
                                                echoAccessLevel,
                                                queryAccessLevel,
                                                LOG_PASSWORDS)
    # create user and verify user exists
    userExists = queryTool.userExists(userPart, hostPart)
    assert (userExists is True), "user was NOT added"
    userGrantDict = queryTool.queryUserGrants(userPart + '@' + hostPart)
    wildcardGrants = userGrantDict['*.*']
    testGrants = userGrantDict['test_db.test_table']
    expectedWildcardGrants = set(["SELECT"])
    expectedTestGrants = set(["SELECT", "INSERT", "UPDATE", "DELETE"])
    assert wildcardGrants == expectedWildcardGrants, \
        "user has incorrect grants: %r should be %r" % \
        (" ".join(wildcardGrants), " ".join(expectedWildcardGrants))
    assert testGrants == expectedTestGrants, \
        "user has incorrect grants: %r should be %r" % \
        (" ".join(testGrants), " ".join(expectedTestGrants))


def checkUserHasEnv():
    missingUserMessage = "missing required\nexport AG_GMAIL_USER='example@gmail.com'\nto run non-interactive"
    missingPassMessage = "missing required\nexport AG_GMAIL_PASS='secret'\nto run non-interactive"
    try:
        if os.environ['AG_GMAIL_USER'] == '':
            assert False, missingUserMessage
    except KeyError:
        assert False, missingUserMessage
    try:
        if os.environ['AG_GMAIL_PASS'] == '':
            assert False, missingPassMessage
    except KeyError:
        assert False, missingPassMessage


def main():
    """Arg parsing and logger setup"""
    retCode = 0
    logLevels = {"DEBUG": logging.DEBUG,
                 "INFO": logging.INFO,
                 "WARN": logging.WARNING,
                 "ERROR": logging.ERROR,
                 "CRITICAL": logging.CRITICAL}
    parser = argparse.ArgumentParser(
        description='A tool to check correctness')
    parser.add_argument('-l', '--log-level', type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
                        help="the log level")
    parser.add_argument('-t', '--test', type=str, required=True,
                        choices=["IS_CLEAN", "HAS_GRANTS", "HAS_ENV"],
                        help="the test to perform")
    args = parser.parse_args()
    if args.log_level.upper() in logLevels.keys():
        logging.basicConfig(level=logLevels[args.log_level.upper()])
    else:
        logging.basicConfig(level=logging.INFO)
        logger.warn("Unknown logLevel=%s retaining level at INFO",
                    args.log_level)
    logger.info(pprint.pformat(args))
    # variables
    hostPart = "%"
    userPart = "int_test_user"
    mysqlUser = "grant_bot"
    mysqlPass = "hat"
    cluster = "192.168.33.10"
    echoOnly = False
    destructive = False
    if args.test == "IS_CLEAN":
        checkDbClean(cluster, mysqlUser, mysqlPass, userPart, hostPart,
                     echoOnly, destructive)
    elif args.test == "HAS_GRANTS":
        checkUserHasGrants(cluster, mysqlUser, mysqlPass, userPart, hostPart,
                           echoOnly, destructive)
    elif args.test == "HAS_ENV":
        checkUserHasEnv()
    logger.info("done.")
    return retCode

if __name__ == "__main__":
    """Entry point if being run as a script"""
    main()

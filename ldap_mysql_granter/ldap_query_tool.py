#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ldap_query_tool tool to do ldap search queries
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
import argparse
import logging
import ldap
import pprint
import sys

logger = logging.getLogger(__name__)


class InvalidConfigException(Exception):
    pass


class LdapQueryTool(object):

    def __init__(self, ldapUrl, usernameBase, password):
        self._timeout = 100
        self._connection = ldap.initialize(ldapUrl)
        self._connection.protocol_version = ldap.VERSION3
        self._connection.simple_bind_s(usernameBase, password)

    def queryLDAP(self, base, searchFilter=None):
        baseDN = base
        searchScope = ldap.SCOPE_SUBTREE
        rawResult = None
        resultDict = {}
        if searchFilter is not None:
            rawResult = self._connection.search_st(baseDN, searchScope,
                                                   searchFilter,
                                                   timeout=self._timeout)
        else:
            rawResult = self._connection.search_st(baseDN, searchScope,
                                                   timeout=self._timeout)
        for resultTuple in rawResult:
            resultType, resultData = resultTuple
            resultDict[resultType] = resultData
        return resultDict


def main(args=None):
    """Arg parsing and logger setup"""
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
    parser.add_argument('-e', '--endpoint', type=str,
                        help="the ldap server to query")
    parser.add_argument('-u', '--username', type=str,
                        help="your ldap username")
    parser.add_argument('-p', '--password', type=str,
                        help="your ldap password")
    parser.add_argument('-b', '--base', type=str,
                        help="the base of the ldap query")
    parser.add_argument('-f', '--filter', type=str,
                        help="a string to filter results")
    parsedArgs = parser.parse_args(args)
    if parsedArgs.log_level.upper() in logLevels.keys():
        logging.basicConfig(level=logLevels[parsedArgs.log_level.upper()])
    else:
        logging.basicConfig(level=logging.INFO)
        logger.warn("Unknown logLevel=%s retaining level at INFO",
                    parsedArgs.log_level)
    logger.info(pprint.pformat(parsedArgs))
    ldapQueryTool = LdapQueryTool(parsedArgs.endpoint, parsedArgs.username, parsedArgs.password)
    ldapQueryDict = ldapQueryTool.queryLDAP(parsedArgs.base, parsedArgs.filter)
    pprint.pprint(ldapQueryDict)
    logger.info("Done!")
    return retCode

if __name__ == "__main__":
    """Entry point if being run as a script"""
    sys.exit(main(sys.argv[1:]))

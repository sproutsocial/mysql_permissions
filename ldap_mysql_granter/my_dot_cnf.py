# -*- coding: utf-8 -*-
"""
my_dot_cnf.py is a module to read the .my.cnf file
if found in the users home directory
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
#  This script requires the following packages to be installed:
#   PyYAML==3.11
import ConfigParser
import logging
import os
import getpass
logger = logging.getLogger(__name__)


class MyDotCnf(object):

    def __init__(self, myCnfFile="~/.my.cnf"):
        """
        This reads the ~/.my.cnf
        then it stores data into the global variables
        """
        self._myCnfFile = myCnfFile
        self._cfgParser = ConfigParser.ConfigParser()
        self.defaultMysqlUser = None
        self.defaultMysqlPassword = None
        try:
            self._cfgParser.readfp(open(os.path.expanduser(myCnfFile)))
        except IOError:
            logger.warn("option file %s not found creating one will save time" % self._myCnfFile)
        else:
            try:
                self.defaultMysqlUser = self._cfgParser.get("client", "user")
            except ConfigParser.NoOptionError:
                logger.warn("No user defined in [client] section of ", self._myCnfFile)
            try:
                self.defaultMysqlPassword = self._cfgParser.get("client", "password")
            except ConfigParser.NoOptionError:
                logger.warn("No password defined in [client] section of ", self._myCnfFile)

    def getDefaultMysqlUser(self):
        """returns the mysql user defined in the .my.cnf file or a user entered value if none exists"""
        if self.defaultMysqlUser is None:
            self.defaultMysqlUser = raw_input("Username: ")
        return self.defaultMysqlUser

    def getDefaultMysqlPassword(self):
        """returns the mysql password defined in the .my.cnf file or a user entered value if none exists"""
        if self.defaultMysqlPassword is None:
            self.defaultMysqlPassword = getpass.getpass()
        return self.defaultMysqlPassword

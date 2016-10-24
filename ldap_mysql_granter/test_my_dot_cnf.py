#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_my_dot_cnf tests the nagios config formatter
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
#  This script requires the following packages to be installed:
#   mock==1.0.1
#   PyYAML==3.11

import my_dot_cnf
import logging
import os
import unittest
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)


class TestMyDotCnf(unittest.TestCase):

    def setUp(self):
        """use a custom yaml file
           NOTE: the overrideYamlDictForTests should only be called from tests
        """
        myCnfFile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures", "my.cnf")
        self.myDotCnf = my_dot_cnf.MyDotCnf(myCnfFile)

    def test_getDefaultMysqlUser(self):
        """tests the getDefaultMysqlUser function
           returns an exampleuser
        """
        fixtureUser = self.myDotCnf.getDefaultMysqlUser()
        self.assertEquals(fixtureUser, "exampleuser")

    def test_getMysqlSchemas(self):
        """tests the getDefaultMysqlPassword function
           returns an examplepass
        """
        fixturePass = self.myDotCnf.getDefaultMysqlPassword()
        self.assertEquals(fixturePass, "examplepass")


if __name__ == '__main__':
    unittest.main()

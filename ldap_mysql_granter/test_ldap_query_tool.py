#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_ldap_query_tool are the tests associated with the ldap_query_tool
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
#  This script requires the following packages to be installed:
#   mock==1.0.1

from contextlib import contextmanager
from StringIO import StringIO
import ldap_query_tool
import logging
import mock
import pprint
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


class FakeLdapConnection(object):
    protocol_version = None

    def simple_bind_s(self, usernameBase, password):
        pass


class TestLdapQueryTool(unittest.TestCase):

    def test_queryLdap(self):
        fakeConnection = FakeLdapConnection()
        fakeResData = [('cn=agroup,ou=Groups,dc=example,dc=com', {
            'cn': ['agroup'],
            'gidNumber': ['20001'],
            'memberUid': ['user1',
                          'user2',
                          'user3'],
            'objectClass': ['top',
                            'posixGroup']})]
        fakeConnection.search_st = mock.MagicMock(return_value=fakeResData)
        ldap_query_tool.ldap.initialize = mock.MagicMock(
            return_value=fakeConnection)
        fakeEndpoint = "not_an_endpoint"
        fakeUser = "not_a_username"
        fakePass = "not_a_password"
        fakeBase = "not_a_base"
        fakeFilter = "not_a_filter"
        ldapQueryTool = ldap_query_tool.LdapQueryTool(fakeEndpoint, fakeUser, fakePass)
        expectedLdapDict = {'cn=agroup,ou=Groups,dc=example,dc=com': {
                            'cn': ['agroup'],
                            'gidNumber': ['20001'],
                            'memberUid': ['user1',
                                          'user2',
                                          'user3'],
                            'objectClass': ['top',
                                            'posixGroup']}}
        ldapQueryDict = ldapQueryTool.queryLDAP(fakeBase, fakeFilter)
        self.assertDictEqual(expectedLdapDict, ldapQueryDict)


class TestLdapQueryToolMain(unittest.TestCase):
    def setUp(self):
        self._unmockedQueryLDAP = ldap_query_tool.LdapQueryTool.queryLDAP
        ldap_query_tool.LdapQueryTool.queryLDAP = mock.MagicMock(
            return_value={})

    def tearDown(self):
        ldap_query_tool.LdapQueryTool.queryLDAP = self._unmockedQueryLDAP

    def test_main(self):
        fakeEndpoint = "not_an_endpoint"
        fakeUser = "not_a_username"
        fakePass = "not_a_password"
        fakeBase = "not_a_base"
        fakeFilter = "not_a_filter"
        testDict = {'test dicts': "are fun"}
        ldap_query_tool.LdapQueryTool.queryLDAP = mock.MagicMock(
            return_value=testDict)
        with captured_output() as (out, err):
            # test without a filter
            ldap_query_tool.main(["-e", fakeEndpoint,
                                  "-u", fakeUser, "-p", fakePass, "-b",
                                  fakeBase])
            outStr = out.getvalue().strip()
            self.assertEquals(outStr, pprint.pformat(testDict))
            expectedCalls = [mock.call(fakeBase, None)]
            ldap_query_tool.LdapQueryTool.queryLDAP.assert_has_calls(
                expectedCalls)
            # test with a filter
            ldap_query_tool.main(["-e", fakeEndpoint,
                                  "-u", fakeUser, "-p", fakePass, "-b",
                                  fakeBase, '-f', fakeFilter])
            expectedCalls = [mock.call(fakeBase, fakeFilter)]
            ldap_query_tool.LdapQueryTool.queryLDAP.assert_has_calls(
                expectedCalls)


if __name__ == '__main__':
    unittest.main()

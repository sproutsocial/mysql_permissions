# -*- coding: utf-8 -*-
"""
auto_grant_config is a module to read the integration_test.yaml file
 and provide mappings
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
#  This script requires the following packages to be installed:
#   PyYAML==3.11

import getpass
import logging
import re
import yaml_config
logger = logging.getLogger(__name__)


class InvalidConfigException(Exception):
    pass


class MissingConfigException(Exception):
    pass


class AutoGrantConfig(yaml_config.YamlConfig):

    def __init__(self, yamlFile):
        """
        This reads the integration_test.yaml file
        """
        super(AutoGrantConfig, self).__init__(yamlFile)
        if self._yamlDict is None:
            raise MissingConfigException("Missing config\nYou can run mysql_grants_generator --init to generate one")

    def getDbClusters(self):
        """returns all the keys of the group_to_grants_map"""
        dbClusters = sorted(self._yamlDict['group_to_grants_map'].keys())
        return dbClusters

    def getHostsForGroup(self, group):
        hosts = []
        clusters = self._yamlDict['group_to_grants_map'].keys()
        for cluster in clusters:
            clusterValue = self._yamlDict['group_to_grants_map'][cluster]
            if group in clusterValue:
                hosts += clusterValue[group].keys()
        return set(hosts)

    def getGrantList(self, user, cluster, group):
        """returns all the unique mappings for group on the given cluster"""
        grantList = []
        try:
            host = user.split('@')[1].strip("'")
            mappingValue = self._yamlDict['group_to_grants_map']
            clusterValue = mappingValue[cluster]
            groupValue = clusterValue[group]
            hostValue = groupValue[host]
            for db_table in hostValue:
                privileges = hostValue[db_table]
                grantList += [{'db_table': db_table,
                               'privileges': privileges}]
        except KeyError:
            logger.debug("config missing for user=%s cluster=%s group=%s",
                         user, cluster, group)
        return grantList

    def getCustomMysqlGroups(self):
        """returns all of the groups in override_groups"""
        customGroups = None
        try:
            customGroups = self._yamlDict['override_groups']
        except KeyError:
            logger.debug("config missing for override_groups")
        return customGroups

    def getMysqlUserFiltered(self, user):
        """returns whether a user matches filtered regex
           in mysql_user_filter"""
        userFiltered = False
        if 'mysql_user_filter' in self._yamlDict:
            userFilter = self._yamlDict['mysql_user_filter']
            if userFilter is not None:
                for userPattern in userFilter:
                    matches = re.search(userPattern, user)
                    if matches is not None and user in matches.group():
                        logger.debug("FILTER %s", user)
                        userFiltered = True
                        break
        return userFiltered

    def getUserToEmailMap(self):
        """returns all of the user to email conversions"""
        ldapToEmailMap = {}
        try:
            ldapToEmailMap = self._yamlDict['user_to_email_map']
            if ldapToEmailMap is None:
                ldapToEmailMap = {}
        except KeyError:
            logger.warning("config missing user_to_email_map")
        return ldapToEmailMap

    def getLdapURL(self):
        """returns the ldap_server_url listed in the yaml file"""
        ldapServerUrl = None
        try:
            ldapServerUrl = self._yamlDict['ldap_server_url']
        except KeyError:
            logger.debug("ldapServerUrl not found this will disable ldap search")
        return ldapServerUrl

    def getLdapGroupDesc(self):
        """returns the ldap_group_desc listed in the yaml file"""
        return self._yamlDict['ldap_group_desc']

    def getLdapUsernameBase(self):
        username = None
        try:
            username = self._yamlDict['ldap_auth']['username_base']
        except KeyError:
            logger.debug("ldap_auth.username_base not found this will disable ldap search")
        return username

    def getLdapPassword(self):
        password = None
        try:
            password = self._yamlDict['ldap_auth']['password']
        except KeyError:
            logger.debug("ldap_auth.password not found this will disable ldap search")
        return password

    def getLdapMinGid(self):
        minGid = 0
        try:
            minGid = int(self._yamlDict['ldap_min_gid'])
        except KeyError:
            logger.debug("ldap_min_gid not found defaulting to %s", minGid)
        except ValueError:
            logger.warning("ldap_min_gid not numeric defaulting to %s", minGid)
        return minGid

    def getEmail(self):
        return self._yamlDict['gmail_auth']['username']

    def getEmailPass(self):
        return self._yamlDict['gmail_auth']['password']

    def getAWSKey(self):
        awsKey = None
        try:
            awsKey = self._yamlDict['aws_auth']['key']
        except KeyError:
            logger.debug("no aws key returning %s", awsKey)
        return awsKey

    def getAWSSecret(self):
        awsSecret = None
        try:
            awsSecret = self._yamlDict['aws_auth']['secret']
        except KeyError:
            logger.debug("no aws secret returning %s", awsSecret)
        return awsSecret

    def getMysqlGrantsUsername(self):
        mysqlUser = None
        try:
            mysqlUser = self._yamlDict['mysql_auth']['grants']['username']
        except KeyError:
            raise InvalidConfigException(
                "yaml file is missing mysql_auth for grants")
        return mysqlUser

    def getMysqlGrantsPassword(self):
        mysqlPass = None
        try:
            mysqlPass = self._yamlDict['mysql_auth']['grants']['password']
            if mysqlPass is None:
                mysqlPass = ""
        except KeyError:
            print "MysqlGrantsUser:"
            mysqlPass = getpass.getpass()
        if mysqlPass is None:
            raise InvalidConfigException(
                "yaml file is missing mysql_auth for grants")
        return mysqlPass

    def getMysqlRevertUsername(self):
        mysqlUser = None
        try:
            mysqlUser = self._yamlDict['mysql_auth']['revert']['username']
        except KeyError:
            raise InvalidConfigException(
                "yaml file is missing mysql_auth for revert")
        return mysqlUser

    def getMysqlRevertPassword(self):
        mysqlPass = None
        try:
            mysqlPass = self._yamlDict['mysql_auth']['revert']['password']
        except KeyError:
            raise InvalidConfigException(
                "yaml file is missing mysql_auth for revert")
        return mysqlPass

    def getHasteBinUrl(self):
        hastebinUrl = None
        try:
            hastebinUrl = self._yamlDict['hastebin_url']
        except KeyError:
            logger.debug("yaml file is missing hastebin_url\n for added security setup a local haste server by following the instructions here:\nhttps://github.com/seejohnrun/haste-server/wiki/Installation")
        return hastebinUrl

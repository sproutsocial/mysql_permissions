# -*- coding: utf-8 -*-
"""
import_schema_config is a module to read the integration_test.yaml file
 and provide mappings
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
#  This script requires the following packages to be installed:
#   PyYAML==3.11

import logging
import os
import yaml_config
logger = logging.getLogger(__name__)


class InvalidConfigException(Exception):
    pass


class ImportSchemaConfig(yaml_config.YamlConfig):

    def __init__(self, yamlFile=None):
        """
        This reads the integration_test.yaml file
        """
        if yamlFile is None:
            # TODO(nicholas): fix me as this breaks if not installed via source control
            yamlFile = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "import_schema.yaml")
        print yamlFile
        super(ImportSchemaConfig, self).__init__(yamlFile)

    def getMysqlUsers(self):
        """returns all the keys of the mysql_users"""
        mysqlUsers = None
        try:
            mysqlUsers = self._yamlDict['mysql_users']
        except KeyError:
            logger.info("no mysql_users found to import")
        return mysqlUsers

    def getMysqlSchemas(self):
        """returns all the keys of the mysql_schemas"""
        mysqlSchemas = None
        try:
            mysqlSchemas = self._yamlDict['mysql_schemas']
        except KeyError:
            raise InvalidConfigException("yaml file is missing mysql_schemas")
        return mysqlSchemas

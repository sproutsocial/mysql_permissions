"""
config_env a module to share env reading code for yaml configs
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""
import os
import re
import yaml
import logging
ENV_REGEX = r'^(.*)\<%= ENV\[\'(.*)\'\] %\>(.*)$'
logger = logging.getLogger(__name__)


def envvar_constructor(loader, node):
    value = loader.construct_scalar(node)
    envPattern = re.compile(ENV_REGEX)
    preceding, envVar, remaining = envPattern.match(value).groups()
    result = None
    try:
        result = preceding + os.environ[envVar] + remaining
    except KeyError:
        if 0 < len(preceding) and 0 < len(remaining):
            result = preceding + remaining
    return result


class YamlConfig(object):
    def __init__(self, yamlFile):
        """
        This reads the yamlFile
        then it stores data into the global variables
        NOTE: this should only be called internally
        NOTE: this ENV_REGEX only allows for
              ONE ENV mapping in each value
        """
        self._yamlFile = yamlFile
        envPattern = re.compile(ENV_REGEX)
        yaml.add_implicit_resolver("!envvar", envPattern)
        yaml.add_constructor('!envvar', envvar_constructor)
        yamlContents = ""
        try:
            yamlContents = open(self._yamlFile).read()
        except IOError:
            logger.error("could not open ", self._yamlFile)
        self._yamlDict = yaml.load(yamlContents)

    def overrideYamlDictForTests(self, _yamlDict):
        """
        This allows you to override the default integration_test.yaml file
        by either passing a dict used exclusively by tests
        """
        self._yamlDict = _yamlDict

    def getYamlFile(self):
        """returns the current saved _yamlFile only used for logging"""
        return self._yamlFile

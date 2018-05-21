import ldap_mysql_granter

from setuptools import setup  # Always prefer setuptools over distutils
from setuptools import find_packages
from os import path


def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]


here = path.abspath(path.dirname(__file__))
reqFile = path.join(here, "ldap_mysql_granter", "prod_requirements.txt")
reqs = parse_requirements(reqFile)

epList = ['email_tool=ldap_mysql_granter.email_tool:main',
          'ldap_query_tool=ldap_mysql_granter.ldap_query_tool:main',
          'mysql_backup_tool=ldap_mysql_granter.mysql_backup_tool:main',
          'mysql_grants_generator=ldap_mysql_granter.mysql_grants_generator:main',
          'mysql_query_tool=ldap_mysql_granter.mysql_query_tool:main',
          'import_schema_tool=ldap_mysql_granter.import_schema_tool:main']
packageDataList = ['prod_requirements.txt',
                   path.join('templates', 'password_change.py.tmpl'),
                   path.join('templates', 'password_change_access.tmpl'),
                   path.join('templates', 'password_change_invite.tmpl')]

setup(
    name='ldap_mysql_granter',
    version=ldap_mysql_granter.__version__,
    url='https://github.com/sproutsocial/mysql_permissions',
    keywords=['mysql', 'permissions', 'ldap'],
    description='a configurable ldap group to mysql cluster granter of privileges',
    author='Nicholas Flink',
    author_email='nicholas@sproutsocial.com',
    packages=find_packages(),
    package_data={'': packageDataList},
    install_requires=reqs,
    entry_points={
        'console_scripts': epList,
    },
)

import ldap_mysql_granter

from pip.req import parse_requirements
from setuptools import setup  # Always prefer setuptools over distutils
from setuptools import find_packages
from os import path

here = path.abspath(path.dirname(__file__))
reqFile = path.join(here, "ldap_mysql_granter", "prod_requirements.txt")
install_reqs = parse_requirements(reqFile, session=False)
reqs = [str(ir.req) for ir in install_reqs]

desc = 'a configurable ldap group to mysql cluster granter of privileges',
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
    description=desc,
    author='Nicholas Flink',
    author_email='nicholas@sproutsocial.com',
    packages=find_packages(),
    package_data={'': packageDataList},
    install_requires=reqs,
    entry_points={
        'console_scripts': epList,
    },
)

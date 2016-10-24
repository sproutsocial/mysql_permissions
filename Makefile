.PHONY: flake_lint vagrant integration_test_echo_only integration_test_non_interactive integration_test_interactive integration_tests unit_tests install_test import_schema_test tests dist

CURRENT_VERSION := $(shell cat setup.cfg|grep -o -E "[0-9]*\.[0-9]*\.[0-9]*")

flake_lint :
	flake8

vagrant :
	vagrant up

integration_test_echo_only : vagrant
	python integration_test.py --log-level=CRITICAL --test=IS_CLEAN
	python ldap_mysql_granter/mysql_grants_generator.py --log-level=CRITICAL --yaml-conf=./integration_test.yaml --echo-only 
	python integration_test.py --log-level=CRITICAL --test=IS_CLEAN
	python ldap_mysql_granter/mysql_grants_generator.py --log-level=CRITICAL --yaml-conf=./integration_test.yaml --revert --echo-only 
	python integration_test.py --log-level=CRITICAL --test=IS_CLEAN
	python ldap_mysql_granter/mysql_grants_generator.py --log-level=CRITICAL --yaml-conf=./integration_test.yaml --echo-only | bash -x
	python integration_test.py --log-level=CRITICAL --test=HAS_GRANTS
	python ldap_mysql_granter/mysql_grants_generator.py --log-level=CRITICAL --yaml-conf=./integration_test.yaml --revert --echo-only | bash -x
	python integration_test.py --log-level=CRITICAL --test=IS_CLEAN

integration_test_non_interactive: vagrant
	python integration_test.py --log-level=CRITICAL --test=HAS_ENV
	python integration_test.py --log-level=CRITICAL --test=IS_CLEAN
	python ldap_mysql_granter/mysql_grants_generator.py --log-level=CRITICAL --yaml-conf=./integration_test.yaml --non-interactive
	python integration_test.py --log-level=CRITICAL --test=HAS_GRANTS
	python ldap_mysql_granter/mysql_grants_generator.py --log-level=CRITICAL --yaml-conf=./integration_test.yaml --non-interactive --revert
	python integration_test.py --log-level=CRITICAL --test=IS_CLEAN

integration_test_interactive : vagrant
	python integration_test.py --log-level=CRITICAL --test=IS_CLEAN
	python ldap_mysql_granter/mysql_grants_generator.py --log-level=CRITICAL --yaml-conf=./integration_test.yaml
	python integration_test.py --log-level=CRITICAL --test=HAS_GRANTS
	python ldap_mysql_granter/mysql_grants_generator.py --log-level=CRITICAL --yaml-conf=./integration_test.yaml --revert
	python integration_test.py --log-level=CRITICAL --test=IS_CLEAN

integration_tests : vagrant integration_test_echo_only integration_test_non_interactive integration_test_interactive

unit_tests :
	coverage erase
	nosetests --cover-package=ldap_mysql_granter --with-coverage
	coverage report

install_test: vagrant
	#vagrant ssh -c 'sudo pip install -e hg+/auto_grant/@tip#egg=ldap_mysql_granter-'$(CURRENT_VERSION)';echo "Install returned: $$?"' | tee .ssh.txt
	vagrant ssh -c 'cd /auto_grant;sudo python setup.py install;echo "Install returned: $$?"' > .ssh.txt
	cat .ssh.txt | grep "Install returned: 0"
	vagrant ssh -c 'sudo mysql_grants_generator -h;echo "Help returned: $$?"' > .ssh.txt
	cat .ssh.txt | grep "Help returned: 0"

import_schema_test: install_test
	vagrant ssh -c 'import_schema_tool -h'

tests: flake_lint unit_tests integration_tests install_test

dist:
	python setup.py sdist


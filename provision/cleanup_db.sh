#!/usr/bin/env bash

set -ex

mysql -f -u root -pass -e "DROP USER 'int_test_user'@'%';"

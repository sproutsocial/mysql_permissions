#!/bin/bash
set -ex
export LANGUAGE=en_US.UTF-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
locale-gen en_US.UTF-8
dpkg-reconfigure locales
apt-get update -y > /dev/null
apt-get install vim -y > /dev/null
apt-get install debconf-utils -y > /dev/null
apt-get install mercurial -y > /dev/null
apt-get install git -y > /dev/null
apt-get install maven -y > /dev/null
debconf-set-selections <<< "mysql-server mysql-server/root_password password ass"
debconf-set-selections <<< "mysql-server mysql-server/root_password_again password ass"
apt-get install mysql-server -y > /dev/null
mysql -f -u root -pass < /auto_grant/provision/bootstrap.sql
sed -i "s/bind-address\t\t= 127.0.0.1/bind-address\t\t= 0.0.0.0/g" /etc/mysql/my.cnf
service mysql restart
# packages needed to install ldap_mysql_granter package
apt-get install build-essential -y > /dev/null
apt-get install libmysqlclient-dev -y > /dev/null
apt-get install python-dev -y > /dev/null
apt-get install libldap2-dev -y > /dev/null
apt-get install python-mysqldb -y > /dev/null
apt-get install libsasl2-dev -y > /dev/null
apt-get install python-pip -y > /dev/null
pip install --upgrade pip > /dev/null 
# install java8
apt-get install software-properties-common python-software-properties -y > /dev/null # for add-apt-repository
add-apt-repository ppa:webupd8team/java -y > /dev/null
apt-get update > /dev/null
debconf-set-selections <<< "debconf shared/accepted-oracle-license-v1-1 select true"
debconf-set-selections <<< "debconf shared/accepted-oracle-license-v1-1 seen true"
# apt-get install oracle-java8-installer -y > /dev/null
#ldap
export DEBIAN_FRONTEND=noninteractive
echo -e " \
slapd    slapd/domain string nodomain
slapd    slapd/internal/generated_adminpw    password   openstack
slapd    slapd/password2    password    openstack
slapd    slapd/internal/adminpw    password openstack
slapd    slapd/password1    password    openstack
" | debconf-set-selections
apt-get install -y slapd ldap-utils
service slapd stop
slapadd -l /auto_grant/provision/base.ldif
slapadd -l /auto_grant/provision/int_test_user.ldif
slapadd -l /auto_grant/provision/int_test_group.ldif
service slapd start

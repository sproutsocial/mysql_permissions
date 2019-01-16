# mysql_permissions #

### What is this repository for? ###
* mysql_permissions is a way to manage authentication and permissions across mysql clusters and servers from a configuration management system or LDAP tree.
* Automatically adds, removes and updates GRANTS for all user in a group
* Integrates with a hastebin server so you can safely store emails only on internal servers
* Integrates with gmail or amazon's boto to send users notifications
* Command line program is easily cronable with --non-interactive argument
* Easily perform dry runs by passing the --echo-only argument
* Ensure old users are cleaned up by passing the --destructive argument
* Backs up mysql schemas to ~/mysqlbackup/YYYYMMDD-HHMMSS/cluster_name_or_ip/db.sql
* if the user@host doesn't exist
    * connects and does a CREATE USER 'user'@'host' with a randomly generated password
    * sends an instructional email to the user asking them to change their password

### Quick Start ###
Ensure you have Mysql installed
```
git clone git@github.com:sproutsocial/mysql_permissions.git
cd mysql_permissions
# You may need to change the from the root user or omit the --password flag depending on your mysql setup
mysql --user=root --password < provision/quick_start.sql
# Install necessary requirements
# When installing requirements I highly recommend using https://virtualenv.pypa.io
# without a virtualenv sudo may be required
pip install -r requirements.txt
# Generate an auto_grant.yaml file with mysql/gmail users/passwords
# Choose the defaults for the mysql user and mysql password grant_user and grant_pass respectively
python ldap_mysql_granter/mysql_grants_generator.py -i
# Run the actual tool and follow online prompts, check your email, download the attachment
python ldap_mysql_granter/mysql_grants_generator.py
# Download password_change_invite.py to CWD Reset the autogenerated to a new one of the users choosing
python password_change_invite.py
# Read the generated file auto_grant.yaml
```

### Ldap Integration Testing ###
Download VirtualBox: https://www.virtualbox.org/wiki/Downloads
Download vagrant: https://www.vagrantup.com/downloads.html

```
git clone git@github.com:sproutsocial/mysql_permissions.git
cd mysql_permissions
pip install -r requirements.txt
export AG_GMAIL_USER=example@gmail.com
export AG_GMAIL_PASS=mail_password
make integration_test_interactive
```
-- Follow online prompts, check your email, download the attachment --
python password_change_invite.py

### Configuration ###
* you can configure the way the script runs:
* check out the documentation about [auto_grant.yaml](ldap_mysql_granter/templates/auto_grant.yaml.tmpl)

### Limitations ###
* Sending through gmail will not work if you have 2 factor authorization setup

### Assumptions ###
* New grant mysqlUser emails will be composed from mysqlUser @ gmail_auth['username'] domain
* If a user already exists on one machine a Notification email will be sent of access the password will be the same

### Enterprise installation ###
* Install a local haste server that is only accessable from your enterprise's ips https://github.com/seejohnrun/haste-server/wiki/Installation
* Use amazon simple email service to send to your enterprises domain.  You will need to create an amazon account then obtain an application key and secret https://aws.amazon.com/ses/getting-started/
* Generate the auto_grant.yaml using: mysql_grants_generator --init --non-interactive
* Uncomment the sections for Ldap, AWS, and Hastebin changing the hastebin to your internal one
* Create an env.sh file:
* It should follow the below format replacing these values with your own
```
export AG_LDAP_USER='ldap_user'
export AG_LDAP_PASS='ldap_pass'
export AG_GMAIL_USER='user@domain.com'
export AG_GMAIL_PASS='gmail_pass'
export AG_MYSQL_USER='mysql_user_with_create_user_permission'
export AG_MYSQL_PASS='mysql_pass'
export AG_AWS_KEY='aws_key'
export AG_AWS_SECRET='aws_secret'
```
* Source it you can check using env that everything is ok
```
source env.sh
env|grep AG_
```
* clone repo and change your directory to there
```
git clone git@github.com:sproutsocial/mysql_permissions.git
cd mysql_permissions
```
* OPTIONAL: set up any virtual environment I use https://virtualenvwrapper.readthedocs.org/en/latest/install.html
```
mkvirtualenv auto_grant
```
* install requirements into your virtual environment
```
pip install -r requirements.txt
```
* you are ready to run the script and the global expected command is
    * see contribution to view how to develop and run locally
    * make sure to look at the commands before typing Yes you can always Ctrl-C to quit
    * generate grants for a user-list RECOMMENDED
```
python ldap_mysql_granter/mysql_grants_generator.py --yaml-conf=./integration_test.yaml -U user1,user2
```
    * Globally this will update everyone in ldap take care with this one
```
python ldap_mysql_granter/mysql_grants_generator.py --yaml-conf=./integration_test.yaml
```

### Contributing ###
* Please run tests before commiting any python changes.
```
make tests
```
* Pull requests to https://github.com/sproutsocial/mysql_permissions

### Distribution ###
* To distribute a new version
    * you need to update the version and tag the repo
    * then follow the instruction to build a dist
    * take care to replace "#.#.#" with your actual version
```
bumpversion --tag --commit {patch,minor,major} ldap_mysql_granter/__init__.py
```
* to build a dist simply make sure there isn't an old one
* then just make it
```
    rm -r dist
    make dist
```
* to add the latest distribution to your_other_project/requirements.txt
    * this should be run from the clone of auto_grant
    * but the output can be directed to whichever requirements file you would like
```
LATEST_TAG=`git describe --tags $(git rev-list --tags --max-count=1)`
LATEST_TAG_REV=`git rev-list --tags --max-count=1`
echo "-e git://github.com/sproutsocial/mysql_permissions.git@${LATEST_TAG}#egg=ldap_mysql_granter=${LATEST_TAG_REV}" >> your_other_project/requirements.txt
```

### Script entry points ###
* This is the main entry point
* ldap_mysql_granter/mysql_grants_generator.py
* ldap_mysql_granter/email_tool.py
* ldap_mysql_granter/ldap_query_tool.py
* ldap_mysql_granter/mysql_backup_tool.py
* ldap_mysql_granter/mysql_query_tool.py
* ldap_mysql_granter/import_schema_tool.py

### How to I post an issue? ###
https://github.com/sproutsocial/mysql_permissions/issues

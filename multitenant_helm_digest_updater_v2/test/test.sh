#! /bin/bash

BASE_DIRECTORY=$(pwd)

# Absolute path to this script. /home/user/bin/foo.sh
SCRIPT=$(readlink -f $0)
# Absolute path this script is in. /home/user/bin
SCRIPTPATH=`dirname $SCRIPT`

export BRANCH_CONFIGURATION=$(cat $SCRIPTPATH/test.yaml)
export GITHUB_BRANCH=development
export GITOPS_BRANCH=test
export GITOPS_REPOSITORY=test
export GITOPS_USERNAME=test
export GITOPS_EMAIL=test
export GITHUB_ACTION_RUN_URL=test

cd $SCRIPTPATH

# CAREFUL THIS WILL DO COMMITS TO THE BRANCHHHHH

$SCRIPTPATH/../scripts/deploy_tenants.sh

cd $BASE_DIRECTORY
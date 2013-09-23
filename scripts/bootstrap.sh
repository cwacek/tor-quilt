#!/bin/sh

# steps required to build/deploy safest-tor
exp=$1

if [[ -z $exp ]]; then
  echo "Please give experiment to run"
  exit 1
fi

sudo apt-get install fabric python-yaml

fab update_apt
fab setup_clients setup_servers
fab deploy_tor:config_file=$exp
fab setup_tor:force=true
fab configure_dirservers
fab configure_torrc:config_file=$exp


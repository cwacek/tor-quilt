#!/bin/sh

# steps required to build/deploy safest-tor
exp=rapidtor-fc-prot-ratelimited

sudo apt-get install fabric python-yaml

fab update_apt
fab setup_clients setup_servers
fab deploy_tor:config_file=experiments/$exp
fab setup_tor:force=true
fab configure_dirservers
fab configure_torrc:config_file=experiments/$exp


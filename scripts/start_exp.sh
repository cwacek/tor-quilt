#!/bin/bash

config=$1

if [[ -z $config ]]; then
  echo " usage: start_exp.sh <config file> <savedir>"
  exit 1
fi

savedir=$2
if [[ -z $savedir ]]; then
  echo " usage: start_exp.sh <config file> <savedir>"
  exit 1
fi

fab=/usr/bin/fab

$fab deploy_tor:config_file=$config

if [[ "$?" != "0" ]]; then echo "Failed to deploy Tor"; exit 1; fi
$fab setup_tor:force=True
if [[ "$?" != "0" ]]; then echo "Failed to compile"; exit 1; fi

$fab kill_tor

$fab configure_dirservers
if [[ "$?" != "0" ]]; then echo "Failed to configure directory servers"; exit 1; fi

$fab configure_torrc:config_file=$config
if [[ "$?" != "0" ]]; then echo "Failed to configure torrc files"; exit 1; fi


echo "Starting Directories"
$fab run_tor:roles=directory
if [[ "$?" != "0" ]]; then echo "Failed to run directories"; exit 1; fi

sleep 60
echo "Starting Routers"
$fab run_tor:roles=router
if [[ "$?" != "0" ]]; then echo "Failed to run routers"; exit 1; fi

sleep 400
$fab run_tor:roles=client
if [[ "$?" != "0" ]]; then echo "Failed to run clients"; exit 1; fi
sleep 60

$fab run_clients:config_file=$config
if [[ "$?" != "0" ]]; then echo "Failed to run curl"; exit 1; fi

for i in $(seq 0 9); do
  echo "Experiment Running. $(expr 9000 - $(expr $i \* 900)) seconds remain."
  sleep 900
done

echo "Stopping clients/Tor"
$fab stop_clients
$fab kill_tor

$fab save_data:save_base=$savedir

#!/bin/sh

# starts up Tor on all the experiment nodes
# uses a staggered start for various roles

fab run_tor:roles=directory
sleep 60
fab run_tor:roles=router
sleep 60
fab run_tor:roles=client


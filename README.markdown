Title: DETER Control Scripts README
Author: Chris Wacek
Date: September 26, 2012

DETER Control Scripts
=====================

The contents of this directory together comprise a series of
scripts and configuration files that can be used to run
SAFEST experiments on DETER.

Requirements
------------

### Applications and Libraries 
The control scripts are based on [Fabric][1], a Python library
that streamlines the use of SSH for application deployment
and system administration. They also rely heavily on
[YAML][2] as a configuration file format.

This means that the machine running them must have the
following packages installed (this is Ubuntu 12.04 specific.
You'll have to translate if you're running something else):

- python-yaml
- fabric


**Note:** `users.isi.deterlab.net` doesn't play nicely with
Fabric because it runs FreeBSD. Don't try and run these on
it. There's one caveat to this described [later](#howtorun).

### DETER Topologies
Very different activities need to be performed for routers,
clients, directories, and servers whe starting up SAFEST.
These control scripts are designed to avoid having to
identify what type of action should be performed on each
node by using the node hostname to inform the action.

Nodes are assigned to Fabric roles by the contents of the 
second match in this regular expression when applied to
their fully qualified domain name (e.g.
*router4.inbuild2.safer* results in a second group match of
*router*):

    (([a-zA-Z]+)[^\.]*\.(?:[a-zA-Z0-9]+)\.(?:[a-zA-Z0-9]+))

The control scripts understand four different kinds of
roles, and apply different actions to them as follows:

- *router*: Actions that affect Tor relays.
- *directory*: Actions that affect Tor directory
  servers. In most cases, *router* actions are also applied
  to *directory* nodes.
- *client*: Actions that affect client hosts.
- *server*: Actions that affect server hosts.

Any other node hostname is simply ignored.

**NB:** To see the roles assigned to actions, look
inside `fabfile.py` and note the `@roles` designator above
each function.


How to Run <a id="howtorun">
----------

### Required Step / Where to Run

Think of `users.isi.deterlab.net` as a node that oversees the experiment, but
*does not participate in it*. The other nodes in the experiment (such as
`router1.<exp_name>.safer` ) are actual participants in the experiment. Since
`users` runs FreeBSD, it doesn't play nicely with the run scripts, so you
should run the scripts from another node in your experiment. 

**There is one caveat.** In order for Fabric to do the *host* -> *role* conversion
discussed in the [DETER Topologies] section, it needs to
know the names of a host. From inside of an experiment, the
only good way to do this is to run the `node_list` command
on `users`, so before you do anything else, run `python lib/hosts.py`
 on `users`:

This will generate `hostfile.yaml` which tells Fabric
what hosts exist and how to use them. 

If you have the scripts in your home directory, that's all
you need to do since your home directory is NFS-mounted on
DETER. If you have the scripts somewhere else, then you need
to copy `hostfile.yaml` to the control script directory.  

### Standalone Operation

Most of the operations can be performed in a standalone
manner thanks to Fabric. The Fabric processor is invoked
with the `fab` command, which automatically looks for
functions in `fabfile.py` in the current directory. 

You can list all of the available actions by typing `fab
-l`. To get more specific information about a specific
action, you can type `fab -d <action>`. The descriptions are
fairly extensive.

The general order in which these standalone operations needs
to be run is:

1. Configure clients and servers
  - `fab setup_clients setup_servers`
2. Deploy and install Tor
  - `fab deploy_tor:src=deploytarball.tgz` **or** `fab
    deploy_tor:config_file=experiments/rapidtor.example`
  - `fab setup_tor:force=True`
3. Configure directory servers
  - `fab configure_dirservers`
4. Configure Tor 
  - `fab
    configure_torrc:config_file=experiments/rapidtor.example`
5. Run Tor (*some delay betweene these is probably
   desirable*)
  - `fab run_tor:roles=directory`
  - `fab run_tor:roles=router`
  - `fab run_tor:roles=client`
5. Run client software
  - `fab
    run_clients:config_file=experiments/rapidtor.example`

### Running Experiments

Since the whole point of this is to be able to run
experiments easily, there are two helper scripts that are
designed to be able to run and recover the results of
experiments. These are `scripts/start_exp.sh` and
`scripts/multirun`.  

`start_exp.sh` runs an entire
experiment lifecycle from start to finish with a single
configuration. 

`multirun` runs multiple experiments back to
back through repeated invocations of the `start_exp.sh`
script.

These tools require the existence of a *configuration file*,
which specified which options are to be used and how it is
to run. There's an example configuration file in
`experiments/rapidtor.example`, reproduced below for
convenience:


    tor_options:
      datadir: /var/lib/tor
      directory_opts: []
      router_opts:
        - "VivUseMinimumInsteadOfMedian 1"
        - "VivSelectStrategy tor"
        - "VivProtectErrorRejectRate 0.3"
        - "VivProtectErrorWindow 30"
        - "VivUnprotectedBootstrapCount 200"
        - "VivProtectCentroidRejectRate 0.3"
        - "VivProtectCentroidWindow 30"
        - "NeighborPingInterval 3"
        - "NumPingMeasurements 3"
        - "CellStatistics 1"
        - "ExitPolicy accept *:*"
      client_opts:
        - "VivSelectStrategy bestof"
        - "VivSelectCount 10"
        - "VivSelectVar 0"
    experiment_options:
      clients_per_client_host: 3
      bulk_clients: [client2.inbuild2.safer,client1.inbuild2.safer]
      tor_deploy_tarball: ~/eval_ctrl_2012/deploy/rapidtor.tgz


The *configuration file* has the following format:

- tor\_options:
    - datadir: `<string>` *The Tor data directory to use*
    - directory\_opts: `<list>` *A list of strings
      representing valid Tor options that should be applied
      to the directory servers.*
    - router\_opts: `<list>` *A list of strings representing
      valid Tor options that should be applied to the Tor
      relays. **These will also be applied to the
      directories**.*
    - client\_opts: `<list>` *A list of strings representing
      valid Tor options that should be applied to the Tor
      clients.*
- experiment\_options:
    - clients\_per\_client\_host `<int>` *The number of
      clients to operate on each physical client host*
    - bulk\_clients: `<list>` *A list of hostname for
      clients that should operate as bulk clients. All
      clients on that physical host will become bulk
      clients.* 
    - tor\_deploy\_tarball: `<string>` *A path to the
      tarball containing the version of Tor that you would
      like to use. These tarballs have certain requirements
      as outlined [below][Tor Deploy Tarballs].*


Tor Deploy Tarballs
-------------------
The deploy scripts expect the Tor versions that they deploy
to be specified in a particular way. They take the tarball,
deploy it on the target machine, and use hintfiles within the
tarball to compile and prep Tor to run. These hints are as
follows:

- **deploy-build.sh**

    Should build the Tor binary and any other requirements for
    this tarball. It should copy an executable file to
    /usr/bin/tor, which should be a script that launches Tor
    appropriately. It should also copy the actual Tor binary
    to /usr/bin/tor.bin

    The script at /usr/bin/tor will automatically be passed
    the following argument list. 

    `<type> <ip_address> <tor_datadirectory> <tor_rcfile>`

    - `<type>: One of 'client', 'router', or 'directory'.`
    - `<ip_address>: Self explanatory`
    - `<tor_datadirectory>: Self explanatory`
    - `<tor_rcfile>: Self explanatory`


- **tor\_env\_flags**

    A file containing any shell commands that should be run
    before attempting to run the Tor binary. This will be
    `source`d by `bash` immediately before running Tor. This
    can be used to set things like LD\_LIBRARY\_PATH if
    necessary.

- **tor\_tools\_dir** 

    A file containing a hint for where the tor/src/tools
    directory is related to top level.

- **tor\_or\_dir**

    A file containing a hit for where the tor/src/or directory
    is in relation to the top level                  



[1]: http://docs.fabfile.org/en/1.4.3/index.html "Fabric"
[2]: http://http://www.yaml.org/ "YAML Ain't Markup Language"

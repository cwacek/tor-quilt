from fabric.api import local,env,roles,hosts,execute,cd,parallel,sudo,hide,put,runs_once
import fabric.api
from lib.util import state
from lib.util import ensure_file_open
import os
import yaml
import lib.hosts
lib.hosts.load_host_file()


@parallel(pool_size=5)
@roles('server')
def setup_servers(force=False):
  import lib.server
  """ Install apache and tcpping tools """
  lib.server.setup_http(force)
  lib.server.install_voip_tools(force)
  lib.server.start_voip()
  sudo("apt-get -qq install -y bittorrent dtach")
  put("deploy/bt_runner", "/usr/bin", use_sudo=True)
  sudo("chmod +x /usr/bin/bt_runner")


@roles('client')
@parallel(pool_size=5)
def setup_clients(force=False):
  """ Install curl, tcpping, and client helpers """
  import lib.server

  sudo("apt-get -qq install -y curl tsocks bittorrent dtach build-essential")
  lib.server.install_voip_tools(force)
  put("deploy/curl_runner.pl", "/usr/bin/", use_sudo=True)
  put("deploy/voip_runner.pl", "/usr/bin", use_sudo=True)
  put("deploy/torify.pl", "/usr/bin", use_sudo=True)
  put("deploy/bt_runner", "/usr/bin", use_sudo=True)
  sudo("chmod +x /usr/bin/voip_runner.pl")
  sudo("chmod +x /usr/bin/torify.pl")
  sudo("chmod +x /usr/bin/bt_runner")

@runs_once
def start_clients(config_file):
  """ Run clients. Uses the following settings from
  the config file:

  experiment_options:
    client_active_time: <int>
          (The time in seconds clients should be active)
    bulk_clients: <list>
          (A list of the short hostnames that should host bulk clients)
    bt_tracker_host: <string>
          (A hostname to run the BitTorrent tracker on)
    bt_torrent_path: <string>
          (The torrent path)
    bt_data_path: <string>
          (Some sort of data path (ask melkins))
    bt_seed_hosts:  <list>
          (Short hostnames for seeders)
  """
  if state.get('client.bittorrent.running') == True:
    print("Bittorrent appears to be running. You might want to run stop_clients before starting it again")
    return
  execute(_start_bttrack, config_file)
  execute(_start_btserv, config_file)
  execute(_run_clients, config_file)
  state.store('client.bittorrent.running',True)

@runs_once
def stop_clients():
  execute(_stop_btserv)
  execute(_stop_clients)
  state.store('client.bittorrent.running',False)
  
@roles('client')
def _run_clients(config_file):
  """ Run curl clients. Uses the following settings from
  the config file:

  experiment_options:
    client_active_time: <int>
          (The time in seconds clients should be active)
    bulk_clients: <list>
          (A list of the hostnames that should host bulk clients)
  """
  if config_file is None:
    print("Must specify config_file")
    return
  with ensure_file_open(config_file) as config_in:
    conf = yaml.load(config_in)
  import lib.client
  lib.client.start_http(conf)
  lib.client.start_voip_client(conf)
  lib.client.start_btclient(conf)

@roles('client')
@parallel(pool_size=10)
def _stop_clients():
  import lib.client
  lib.client.stop_http()
  lib.client.stop_voip()
  lib.client.stop_btclient()


@roles('client','router','directory')
@parallel(pool_size=10)
def configure_torrc(config_file):
  """ Configure Tor clients

  Configures Tor clients according to the settings 
  specified in the experiment configuration file. Uses 
  the following options:

  tor_options:
    datadir: <string>
          The Tor data directory to use)
    directory_opts: <list>
          A list of strings representing valid Tor 
           options that should be applied to the 
           directory servers.
    router_opts: <list>
          A list of strings representing valid Tor 
           options that should be applied to the 
           Tor relays. **THESE WILL ALSO BE APPLIED
           TO THE DIRECTORIES**.
    client_opts: <list>
          A list of strings representing valid Tor 
           options that should be applied to the 
           Tor clients.
  """
  import lib.tor
  if config_file is None:
    print("Must specify config_file")
    return
  with ensure_file_open(config_file) as config_in:
    conf = yaml.load(config_in)
    lib.tor.apply_config(conf['tor_options'],
                            conf['experiment_options']['clients_per_client_host'])

@roles('client','router','directory')
def deploy_tor(config_file=None,src=None):
  """
  The Tor sofware to be deployed can be specified in two
  ways. There are two parameters to this command that 
  control that choice. 

  1. Via the [experiment_options][tor_deploy_tarball] 
     value in an experiment config file. This is useful
     for running experiment specific binaries. The 
     config file should be passed in the 'config_file'
     parameter.
  2. Via the 'src' parameter, which should point to a 
     tarball directly.
  """

  import lib.tor
  lib.tor.deploy(config_file=config_file,src=src)

@parallel(pool_size=25)
@roles('client','router','directory')
def setup_tor(force=False):
  env.linewise=True
  """ Deploy Tor. 'fab -d setup_tor' for more help...

  This should be called after 'deploy_tor'.

  The previously copied tarball will be extracted, and the 'deploy-build.sh'
  script will be executed.  It is *REQUIRED* that this script completely
  compile Tor (and any dependencies), and copy an executable script to
  '/usr/bin/tor' that will start Tor when passed the following command line
  arguments:
  
  <type> <ip_address> <tor_datadirectory> <tor_rcfile>

  - <type> 
    One of 'client', 'router', or 'directory'.
  - <ip_address>
    Self explanatory
  - <tor_datadirectory>
    Self explanatory
  - <tor_rcfile>
    Self explanatory
  
 `deploy-build.sh` should also copy the
  actual Tor binary to */usr/bin/tor.bin*.
  Tor binary itself.  

  In addition to the `deploy-build.sh` script, 
  the tarball should contain three special hint files

    - tor_env_flags 
      A file containing any shell
      commands that should be run before attempting to
      run the Tor binary. This will be `source`d by
      `bash` immediately before running Tor. This can
      be used to set things like LD_LIBRARY_PATH if
      necessary.

    - tor_tools_dir 
      A file containing a hint for where
      the tor/src/tools directory is related to top
      level.

    - tor_or_dir 
      A file containing a hint for where the
      tor/src/or directory is in relation to the top
      level

  Since this process can be expensive, it will not be 
  repeated on any machine where the statefile knows it 
  has been done already. To FORCE recompilation, pass 
  'force=True' as an option.
  """
  import lib.tor
  lib.tor.install(force=force)

@parallel(pool_size=10)
@roles('client','router','directory')
def run_tor(restart=False):
  """ Start Tor instances
  
  This simply runs '/usr/bin/tor' in a way that
  detaches cleanly. That's why you should make sure
  that /usr/bin/tor is what you want to be running.
  """
  import lib.tor
  lib.tor.start(restart)

@parallel(pool_size=10)
@roles('client','router','directory')
def kill_tor():
  """ Kill running Tor instances"""
  import lib.tor
  lib.tor.kill()

@hosts('localhost')
def configure_dirservers():
  """ Configure directory server keys.

  This should only need to be done once when a 
  topology is swapped in.
  """
  import lib.tor
  if os.path.exists('dirlines.conf'):
    os.unlink("dirlines.conf")
  execute(lib.tor.generate_dir_keys)

@roles('client','router','directory')
def save_data(save_base):
  """ Copy experiment data somewhere

  Experiment data is copied from each router,
  directory, and client to the directory
  specified by the 'save_base' parameter.
  """
  import lib.experiment
  lib.experiment.save_data(save_base)

@hosts('localhost')
def update_hosts_list():
  """ Rebuild host knowledge for a topology

  Needs to be run once every time you use these scripts
  on a different topology. 
  MUST BE RUN FROM users.isi.deterlab.net
  """
  lib.hosts.update_hosts_list()


@parallel(pool_size=10)
@roles('client', 'router', 'directory')
def update_apt():
    """ Run apt-get update.

    """
    sudo("apt-get clean")
    sudo("apt-get update -qq")


@parallel(pool_size=5)
@roles('client', 'server', 'control')
def setup_magi():
    """ Run the magi bootstrap script.

    """
    sudo("python /share/magi/v08/magi_bootstrap.py")


@roles('server')
def _start_bttrack(config_file):
    if config_file is None:
        print("Must specify config_file")
        return
    with ensure_file_open(config_file) as config_in:
        conf = yaml.load(config_in)
    import lib.client
    lib.client.start_bttrack(conf)


@roles('server')
def _start_btserv(config_file):
    if config_file is None:
        print("Must specify config_file")
        return
    with ensure_file_open(config_file) as config_in:
        conf = yaml.load(config_in)
    import lib.client
    lib.client.start_btseed(conf)
    state.current.store("servers.bittorrent.started",True)


@roles('server')
def _stop_btserv():
    import lib.client
    lib.client.stop_btseed()
    lib.client.stop_bttrack()
    state.current.store("servers.bittorrent.started",False)

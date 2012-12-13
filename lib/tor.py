from fabric.api import local,run,env,roles,cd,sudo,put,settings,hide,parallel
from lib.util import state
state.establish()
from fabric.contrib.files import upload_template,append
from lib.util import state,network
import os

def start(restart=False):
  if check_running():
    if restart:
      sudo("killall tor")
    else:
      return

  sudo("chown -R {1} {0}".format(
            state.current.config['tor_datadir'],
            os.getlogin()))

  with cd(state.current.config['tor_datadir']):
    if env.host.lower() in map(str.lower,env.roledefs['directory']):
      run("chmod 700 .")
      run("rm -rf cached-* lock log state router-stability lastor.log")
      run("(nohup tor directory {ip} {datadir} {rcfile} >tor_startup 2>&1 </dev/null &)".format(
            ip=network.get_deter_ip(),
            datadir=state.current.config['tor_datadir'],
            rcfile=state.current.config['tor_datadir'] + "/torrc"
          ),pty=False)

    elif env.host.lower() in map(str.lower,env.roledefs['router']):
      run("chmod 700 .")
      run("rm -rf cached-* lock log state router-stability")
      run("(nohup tor router {ip} {datadir} {rcfile} >tor_startup 2>&1 </dev/null &)".format(
            ip=network.get_deter_ip(),
            datadir=state.current.config['tor_datadir'],
            rcfile=state.current.config['tor_datadir'] + "/torrc"
          ),pty=False)

    elif env.host.lower() in map(str.lower,env.roledefs['client']):
      for i in xrange(state.current.config['clients_per_host']):
        with cd(str(i)):
          run("chmod 700 .")
          run("rm -rf cached-* lock log state router-stability")
          run("(nohup tor client {ip} {datadir} {rcfile} >tor_startup 2>&1 </dev/null &)".format(
            ip=network.get_deter_ip(),
            datadir=state.current.config['tor_datadir'] + "/{0}".format(i),
            rcfile=state.current.config['tor_datadir'] + "/{0}".format(i) +"/torrc"
          ),pty=False)

    else: 
      print("This host [{0}] does not run Tor".format(env.host))

def kill():
  with settings(hide('warnings'),warn_only=True):
    pid = run("pgrep tor | xargs")
    if pid:
      sudo("kill {0}".format(pid))

def check_running():
  with settings(hide('warnings'),warn_only=True):
    pid = run("pgrep tor")
    if pid:
      print("Tor is running with pid {0}".format(pid.strip()))
      return True
    return False

def __install():
  with settings(hide("stdout")):
    sudo("apt-get install -y libevent-dev")
  with cd("/tmp/tor-compile"):
    run("bash deploy-build.sh")

def __deploy(src):
  #with settings(warn_only=True):
  sudo("rm -rf /tmp/tor-compile")
  run("mkdir -p /tmp/tor-compile")
  with cd("/tmp/tor-compile"):
    with settings(hide('stdout')):
      while True:
        try:
          failed = put(src,"tor-build.tgz").failed
          run("tar zxvf tor-build.tgz")
        except Exception as e:
          print("Error {0}".format(e))
        else:
          if len(failed) == 0:
            break;

def install(force=False):
  if state.is_configured("tor.compiled") and not force:
    print("Tor already compiled")
    return
  __install()

def deploy(config_file,src,force=False):
  if src is not None:
    __deploy(src)
  elif config_file is not None:
    import yaml
    with open(config_file) as config_in:
      conf = yaml.load(config_in)
    if 'tor_deploy_tarball' in conf['experiment_options']:
      __deploy(conf['experiment_options']['tor_deploy_tarball'])
    else:
      raise Exception("Couldn't find 'tor_deploy_tarball' "
                      "option in experiment config")
  else:
    raise Exception("Either 'config_file' or 'src' must "
                    "be provided to install command.")




  with settings(hide('warnings'),warn_only=True):
    sudo("mkdir -p /var/lib/tor")
    sudo("chown {0} /var/lib/tor".format(os.getlogin()))
 

    
  state.set_configured("tor.compiled")

REQUIRED_DIR_OPTIONS="""
DirPort 10000
DirListenAddress {ip}:10000
V3AuthoritativeDirectory 1
V2AuthoritativeDirectory 1
AuthoritativeDirectory 1
ContactInfo NULL
""" 

REQUIRED_RELAY_OPTIONS="""
ORPort 5000
ORListenAddress {ip}:5000
Address {ip}
"""
def __apply_relay_config(exp_config):

  template_conf = {
    'directory_options': "",
    'relay_options': "",
    'addl_options': "",
    'dirservlines': "",
    "datadir": exp_config['datadir']
    }

  nickname = "Nickname {0}".format(env.host_string.split(".")[0])

  try:
    host_options = exp_config['host_specific_options'][env.host_string.lower()]
  except KeyError:
    print("No host specific options to add")
    host_options = list()

  relay_options = exp_config['router_opts']
  relay_options.extend(host_options)
  relay_options.append(nickname)

  template_conf['relay_options'] = REQUIRED_RELAY_OPTIONS.format(**exp_config)
  template_conf['addl_opts'] = "\n".join(relay_options)

  with open("dirlines.conf") as dirin:
    template_conf['dirservlines'] = dirin.read()

  _upload_torrc(template_conf,exp_config['datadir'])

def __apply_directory_config(exp_config):

  template_conf = {
    'directory_options': "",
    'relay_options': "",
    'addl_options': "",
    'dirservlines': "",
    "datadir": exp_config['datadir']
    }

  nickname = "Nickname {0}".format(env.host_string.split(".")[0])

  try:
    host_options = exp_config['host_specific_options'][env.host_string.lower()]
  except KeyError:
    print("No host specific options to add")
    host_options = list()

  template_conf['directory_options'] = REQUIRED_DIR_OPTIONS.format(**exp_config) 
  template_conf['relay_options'] = REQUIRED_RELAY_OPTIONS.format(**exp_config)

  router_opts = exp_config['router_opts']
  router_opts.extend(host_options)
  router_opts.extend(exp_config['directory_opts'])
  router_opts.append(nickname)

  template_conf['addl_opts'] = "\n".join(router_opts)

  with open("dirlines.conf") as dirin:
    template_conf['dirservlines'] = dirin.read()

  _upload_torrc(template_conf,exp_config['datadir'])


REQUIRED_CLIENT_OPTS="""
ReachableAddresses 10.0.0.0/8
ReachableORAddresses 10.0.0.0/8
SocksPort {socks_port}
SocksListenAddress 127.0.0.1:{socks_port}
Address {ip}
"""

def __apply_client_config(exp_config,clients_per_client_host=1):

  state.store('clients_per_host',clients_per_client_host)
  
  for i in xrange(clients_per_client_host):

    datadir = "{0}/{1}".format(exp_config['datadir'],i)
    exp_config['socks_port'] = 2000 + i

    template_conf = {
      'directory_options': "",
      'relay_options': "",
      'addl_options': "",
      'dirservlines': "",
      "datadir": datadir
      }

    sudo("mkdir -p {0}".format(datadir))

    nickname = "Nickname {0}Sub{1}".format(env.host_string.split(".")[0],i)

    try:
      host_options = exp_config['host_specific_options'][env.host_string.lower()]
    except KeyError:
      print("No host specific options to add")
      host_options = list()

    user_options = exp_config['client_opts']
    user_options.extend(host_options)
    user_options.append(nickname)

    template_conf['addl_opts'] = "\n".join(user_options)
    required_options = REQUIRED_CLIENT_OPTS.format(**exp_config)
    template_conf['addl_opts'] += "\n{0}".format(required_options)
  
    with open("dirlines.conf") as dirin:
      template_conf['dirservlines'] = dirin.read()

    _upload_torrc(template_conf,datadir)

def _upload_torrc(template_data,datadir):

    upload_template("lib/templates/torrc.conf",
                    "{0}/torrc".format(datadir),
                    template_data,use_sudo=True,backup=False)
    sudo("chown root:root {0}/torrc".format(datadir))

def apply_config(config,clients_per_client_host):
  ip = network.get_deter_ip()

  config.update({"ip":ip, "datadir":config['datadir'] })

  state.store("tor_datadir",config['datadir'])
  
  if env.host in env.roledefs['directory']:
    __apply_directory_config(config)
  elif env.host in env.roledefs['router']:
    __apply_relay_config(config)
  elif env.host in env.roledefs['client']:
    __apply_client_config(config,clients_per_client_host)
  else: raise Exception("unknown host role")


gen_dir_key="""
DirServer {0} {1}:5000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000
ORPort 5000
TestingTorNetwork 1
Nickname Fingerprinter
"""

@roles('directory')
@parallel('5')
def generate_dir_keys():
  ip = network.get_deter_ip()
  with cd("/var/lib/tor"):

    with settings(hide('stdout')):
      sudo("cat /dev/null > torrc.fingerprinter")
      append("torrc.fingerprinter",gen_dir_key.format(env.host_string.split('.')[0],
                                                      ip),
              use_sudo=True)


    with settings(hide('stdout')):
      sudo("rm -rf keys")
      run("mkdir keys")
    with cd("keys"):
      run("yes vivaldi | /tmp/tor-compile/$(cat /tmp/tor-compile/tor_tools_dir)/tor-gencert "
           "--create-identity-key --passphrase-fd 0")
      v3ident = run("grep 'fingerprint' authority_certificate "
           "| awk '{print $2}'")


    fingerprint = run("( . /tmp/tor-compile/tor_env_flags; /usr/bin/tor.bin --list-fingerprint "
                       "--DataDirectory /var/lib/tor "
                       "-f /var/lib/tor/torrc.fingerprinter | "
                       "grep '^Fingerprinter' | sed '-e s/^Fingerprinter //')").strip()


    if not fingerprint:
      raise Exception

    local("echo 'DirServer {0} v3ident={1} orport=5000 "
          "{2}:10000 {3}' >> dirlines.conf".format(
                    env.host_string.split('.')[0],
                    v3ident.strip(),
                    ip,
                    fingerprint.strip()))



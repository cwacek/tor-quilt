from fabric.api import local,run,env,roles,cd,sudo,put,settings,hide,parallel
from lib.util import state
state.establish()
from fabric.utils import puts
from fabric.contrib.files import upload_template,append, exists
from lib.util import state,network
from lib.countries import get_country_code
import os
import sys

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
      sudo("chmod 700 .")
      sudo("rm -rf cached-* lock log state router-stability lastor.log")
      sudo("(nohup /usr/bin/tor directory {ip} {datadir} {rcfile} >tor_startup 2>&1 </dev/null &)".format(
            ip=network.get_deter_ip(),
            datadir=state.current.config['tor_datadir'],
            rcfile=state.current.config['tor_datadir'] + "/torrc"
          ),pty=False)

    elif env.host.lower() in map(str.lower,env.roledefs['router']):
      sudo("chmod 700 .")
      sudo("rm -rf cached-* lock log state router-stability lastor.log")
      sudo("(nohup /usr/bin/tor router {ip} {datadir} {rcfile} >tor_startup 2>&1 </dev/null &)".format(
            ip=network.get_deter_ip(),
            datadir=state.current.config['tor_datadir'],
            rcfile=state.current.config['tor_datadir'] + "/torrc"
          ),pty=False)

    elif env.host.lower() in map(str.lower,env.roledefs['client']):
      for i in xrange(state.current.config['clients_per_host']):
        with cd(str(i)):
          sudo("chmod 700 .")
          sudo("rm -rf cached-* lock log state router-stability lastor.log")
          sudo("(nohup /usr/bin/tor client {ip} {datadir} {rcfile} >tor_startup 2>&1 </dev/null &)".format(
            ip=network.get_deter_ip(),
            datadir=state.current.config['tor_datadir'] + "/{0}".format(i),
            rcfile=state.current.config['tor_datadir'] + "/{0}".format(i) +"/torrc"
          ),pty=False)

          if exists("control.start"):
            sudo("(nohup bash control.start > tor_control.out 2>&1 </dev/null &)"
                 .format(
                   datadir=state.current.config['tor_datadir'] + "/{0}".format(i))
                 )

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
    sudo("apt-get install -y libevent-dev automake")
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
    sudo("chown -R {0} /var/lib/tor".format(os.getlogin()))



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
User {user}
"""
def __apply_relay_config(exp_config):

  template_conf = {
    'directory_options': "",
    'relay_options': "",
    'addl_options': "",
    'dirservlines': "",
    'tor_logdomain': '[ DIR ] info [ *, ~DIR ] notice',
    "datadir": exp_config['datadir'],
    'control_port': 9100
    }

  if 'tor_logdomain' in exp_config:
    template_conf['tor_logdomain'] = exp_config['tor_logdomain']

  nickname = configure_nickname(exp_config)

  try:
    host_options = exp_config['host_specific_options'][env.host_string.split(".")[0].lower()]
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

  if 'enable_ratpac_delay' in exp_config:
    with cd('/tmp'):
      if env.host_string.split(".")[0] in exp_config['enable_ratpac_delay']:
        put('deploy/ratpac.config.enabled', 'ratpac.config')
      else:
        put('deploy/ratpac.config.disabled', 'ratpac.config')

  return template_conf


def __apply_directory_config(exp_config):

  template_conf = {
    'directory_options': "",
    'relay_options': "",
    'addl_options': "",
    'dirservlines': "",
    'tor_logdomain': '[ DIR ] info [ *, ~DIR ] notice',
    "datadir": exp_config['datadir'],
    'control_port': 9100
    }

  if 'tor_logdomain' in exp_config:
    template_conf['tor_logdomain'] = exp_config['tor_logdomain']

  nickname = configure_nickname(exp_config)

  try:
    host_options = exp_config['host_specific_options'][env.host_string.split(".")[0].lower()]
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

  return template_conf


REQUIRED_CLIENT_OPTS="""
ReachableAddresses 10.0.0.0/8
ReachableORAddresses 10.0.0.0/8
SocksPort {socks_port}
SocksListenAddress 127.0.0.1:{socks_port}
Address {ip}
User {user}
"""

def __apply_client_config(exp_config,clients_per_client_host=1):

  state.store('clients_per_host',clients_per_client_host)
  configs = []

  for i in xrange(clients_per_client_host):

    datadir = "{0}/{1}".format(exp_config['datadir'],i)
    exp_config['socks_port'] = 2000 + i

    template_conf = {
      'directory_options': "",
      'relay_options': "",
      'addl_options': "",
      'dirservlines': "",
      'tor_logdomain': '[ DIR ] info [ *, ~DIR ] notice',
      "datadir": datadir,
      'control_port': 9100 + i
      }

    if 'tor_logdomain' in exp_config:
      template_conf['tor_logdomain'] = exp_config['tor_logdomain']

    sudo("mkdir -p {0}".format(datadir))

    nickname = configure_nickname(exp_config, i)

    try:
      host_options = exp_config['host_specific_options'][env.host_string.split(".")[0].lower()]
    except KeyError:
      print("No host specific options to add")
      host_options = list()

    user_options = exp_config['client_opts'][:]
    user_options.extend(host_options)
    user_options.append(nickname)

    template_conf['addl_opts'] = "\n".join(user_options)
    required_options = REQUIRED_CLIENT_OPTS.format(**exp_config)
    template_conf['addl_opts'] += "\n{0}".format(required_options)

    with open("dirlines.conf") as dirin:
      template_conf['dirservlines'] = dirin.read()

    _upload_torrc(template_conf,datadir)

    configs.append(template_conf)

  return configs

def _upload_torrc(template_data,datadir):

    puts("Uploading torrc with template_data {0}".format(
      template_data))
    upload_template("lib/templates/torrc.conf",
                    "{0}/torrc".format(datadir),
                    template_data,use_sudo=True,backup=False)
    sudo("chown root:root {0}/torrc".format(datadir))

def apply_config(config,clients_per_client_host):
  ip = network.get_deter_ip()

  config.update({"ip":ip, "datadir":config['datadir'] , "user":os.getlogin()})

  state.store("tor_datadir",config['datadir'])

  if env.host in env.roledefs['directory']:
    opts = __apply_directory_config(config)
  elif env.host in env.roledefs['router']:
    opts = __apply_relay_config(config)
  elif env.host in env.roledefs['client']:
    opts = __apply_client_config(config,clients_per_client_host)

    for opt in opts:
      setup_client_controller(config, opt)

  else:
    raise Exception("unknown host role")

def setup_client_controller(tor_config, client_opts):
  """ Setup a client controller, if one was requested, 
  using general :tor_config: and this client's :client_opts:
  """
  try:
    controller_config = tor_config['use_client_controller']
  except KeyError:
    sys.stderr.write("Not configuring client controller\n")
    return

  hostname = env.host_string.split(".")[0]

  # Figure out what opts we need from the config file
  config_opts = dict.fromkeys(controller_config['opts'])
  for opt in config_opts:
    try:
      config_opts[opt] = controller_config['opts'][opt][hostname]
    except KeyError:
      config_opts[opt] = controller_config['opts'][opt]['_default']

  client_opts.update(config_opts)

  cmd = controller_config['run'].format(**client_opts)
  puts("Setting client controller start cmd to '{0}'\n".format(cmd))

  append("{0}/control.start".format(client_opts['datadir']),
         "( {cmd} &)".format(cmd=cmd),
         use_sudo=True,
         escape=True)


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

  with settings(warn_only=True):
    sudo("killall tor")
  sudo("chown -R {0}:SAF-SAFEST /var/lib/tor".format(os.getlogin()))
  sudo("chmod g+rwx /var/lib/tor")
  sudo("chmod -R g+rw /var/lib/tor")

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

def configure_nickname(tor_options, enumerator=None):
  """ Configure the nickname as the hostname of
  the machine, with an optional :enumerator:. If
  :country_codes: is in the Tor config, then configure
  countrycodes into the nickname too """

  hostname = env.host_string.split(".")[0]
  index = ""
  cc = None

  if enumerator is not None:
    index = "Sub{0}".format(enumerator)

  try:
    default = tor_options['country_codes']['_default']

  except KeyError:
    raise Exception("If 'country_codes' is supplied, you must give a '_default' key")

  else:
    if hostname not in tor_options['country_codes']:
      cc = get_country_code(default)

    else:
      cc = get_country_code(tor_options['country_codes'][hostname])
      if cc is None:
        cc = get_country_code(default)

  return "Nickname {hostname}{index}{cc}".format(
      hostname=hostname,
      index=index,
      cc="CC{0}".format(cc) if cc is not None else "")

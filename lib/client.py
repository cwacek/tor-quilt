import random
from lib.util import state
state.establish()
from fabric.api import local,run,env,roles,hosts,execute,cd,sudo,put,settings,hide,parallel
from fabric.contrib.files import upload_template,append
from lib.util import state,network
import os

def stop_http():
  sudo("killall curl_runner.pl")

def start_http(config):
  put("deploy/curl_runner.pl","/usr/bin/",use_sudo=True)
  sudo("chmod +x /usr/bin/curl_runner.pl")
  
  for i in xrange(state.current.config['clients_per_host']):
    http_conf = dict()
    http_conf['port'] = 2000 + i
    http_conf['client_active_time'] = ("-a {0}".format(config['experiment_options']['client_active_time']) 
                                        if 'client_active_time' in config['experiment_options']
                                        else "")
    http_conf['tor_datadir'] = "{0}/{1}".format(state.current.config['tor_datadir'],i)
    http_conf['servers'] = ",".join(map(lambda x: x.split(".")[0],env.roledefs['server']))
    http_conf['bulk_flag'] = "-b" if env.host_string.lower() in config['experiment_options']['bulk_clients'] else ""

    sudo("apt-get install -y dtach")
    run("mkdir -p /tmp/curl_dtach")
    
    start_cmd = "dtach -n /tmp/curl_dtach/{0} /usr/bin/curl_runner.pl -h 127.0.0.1 ".format(random.randint(0, 1000000000))
    start_cmd += " -p {port} {client_active_time}".format(**http_conf)
    start_cmd += "-D {tor_datadir} -d {servers} {bulk_flag} ".format(**http_conf)
    #start_cmd += "2>&1 >/dev/null "

    run("cat /dev/null > {0}/curl".format(http_conf['tor_datadir']))

    run(start_cmd,pty=False)


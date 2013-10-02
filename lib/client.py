import random
from lib.util import state
state.establish()
from fabric.api import local,run,env,roles,hosts,execute,cd,sudo,put,settings,hide,parallel
from fabric.contrib.files import upload_template,append
from lib.util import state,network
import os
import socket

def stop_http():
    with settings(warn_only=True):
        sudo("killall curl_runner.pl")

def start_http(config):
  try:
      if config['experiment_options']['client_active_time'] == 0:
          return
  except KeyError:
      pass

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
    http_conf['bulk_flag'] = "-b" if env.host_string.split('.')[0].lower() in config['experiment_options']['bulk_clients'] else ""

    sudo("apt-get install -y dtach")
    run("mkdir -p /tmp/curl_dtach")
    sudo("chmod g+w /tmp/curl_dtach")

    dtach_socket = random.randint(0,10000000000)
    with settings(hide('warnings'),warn_only=True):
      sudo("rm -f /tmp/curl_dtach/{0}".format(dtach_socket))
    
    start_cmd = "dtach -n /tmp/curl_dtach/{0} /usr/bin/curl_runner.pl -h 127.0.0.1 ".format(dtach_socket)
    start_cmd += " -p {port} {client_active_time}".format(**http_conf)
    start_cmd += " -D {tor_datadir} -d {servers} {bulk_flag} ".format(**http_conf)
    #start_cmd += "2>&1 >/dev/null "

    with settings(hide("warnings"),warn_only=True):
      sudo("rm {0}/curl".format(http_conf['tor_datadir']))

    run(start_cmd,pty=False)


def start_voip_client(config):
    chat_time = config['experiment_options']['voip_active_time']
    if chat_time == 0:
        return
    run("mkdir -p /tmp/voip_dtach")
    sudo("chmod g+w /tmp/voip_dtach")
    # do IP lookup here because voip_emul doesn't consult /etc/hosts
    dest = ','.join(socket.gethostbyname(x.split('.')[0]) for x in env.roledefs['server'])
    for i in xrange(state.current.config['clients_per_host']):
        dtach_sock = '/tmp/voip_dtach/%d' % random.randint(0, 1000000000)
        datadir = '%s/%d' % (state.current.config['tor_datadir'], i)
        with settings(hide('warnings'),warn_only=True):
            sudo("rm -f " + dtach_sock)
            sudo("rm -f %s/voip" % datadir)
        cmd = "dtach -n %(dtach)s /usr/bin/voip_runner.pl -h 127.0.0.1 -p %(socks_port)d -t %(send_time)d -D %(datadir)s -d %(dest)s -S /usr/bin/torify.pl" % {
            'dtach': dtach_sock,
            'socks_port': 2000 + i,
            'send_time': chat_time,
            'datadir': datadir,
            'dest': dest,
        }
        run(cmd, pty=False)


def start_voip_server(config):
    run("mkdir -p /tmp/voip_dtach")
    sudo("chmod g+w /tmp/voip_dtach")
    dtach_sock = '/tmp/voip_dtach/%d' % random.randint(0, 1000000000)
    with settings(hide('warnings'),warn_only=True):
      sudo("rm -f " + dtach_sock)
    cmd = "dtach -n %s /usr/bin/voip_emul -s 4500" % dtach_sock
    run(cmd, pty=False)


def stop_voip():
    with settings(warn_only=True):
        sudo("killall voip_runner.pl voip_emul")


def start_bttrack(conf):
    h = env.host_string.split('.')[0]
    if h == conf['experiment_options']['bt_tracker_host']:
        torrent = conf['experiment_options']['bt_torrent_path']
        data_path = conf['experiment_options']['bt_data_path']
        print 'This host %s runs the tracker' % env.host_string
        ip = socket.gethostbyname(h)
        print 'My IP address appears to be ' + ip
        with settings(warn_only=True):
            sudo('rm -f /var/lib/tor/bttrack.log /tmp/dstate /tmp/dtach.bttrack %s' % torrent)
        run('btmakemetafile %s http://%s:6969/announce --target %s' % (data_path, ip, torrent))
        run('dtach -n /tmp/dtach.bttrack bttrack --port 6969 --dfile /tmp/dstate')


def stop_bttrack():
    with settings(hide('warnings'),warn_only=True):
        sudo('pkill -f bttrack')


def start_btseed(conf):
    seeds = conf['experiment_options']['bt_seed_hosts']
    torrent = conf['experiment_options']['bt_torrent_path']
    data_path = conf['experiment_options']['bt_data_path']
    tracker = conf['experiment_options']['bt_tracker_host']

    if not torrent:
        return

    # if this host is the tracker, do not use it as a seeder event if it is
    # listed in the config file, because this seems to break bit bittorrent
    h = env.host_string.split('.')[0]
    if h in seeds and h != tracker:
        print 'This host (%s) is seeding' % env.host_string
        with settings(warn_only=True):
            sudo('rm -f /var/log/btclient /tmp/dtach.btseed')

        # ensure that the non-tor btclients can't talk to the seeders and are
        # forced to talk only to the tor clients
        sudo('iptables -A OUTPUT -p tcp -m multiport --dports 6881:6889 -j REJECT')

        run('dtach -n /tmp/dtach.btseed bt_runner %s %s /tmp/btseed.log' % (torrent, data_path))


def stop_btseed():
    with settings(hide('warnings'),warn_only=True):
        sudo('pkill -f btdownloadheadless')
        # this assumes that there are no other iptables rules!
        sudo('iptables -D OUTPUT 1')


def start_btclient(conf):
    torrent = conf['experiment_options']['bt_torrent_path']
    if not torrent:
        return

    with settings(hide('warnings'),warn_only=True):
        sudo('rm -rf /tmp/dtach_bt /tmp/btclient.nontor.data')
    run('mkdir /tmp/dtach_bt')

    # start up tor+bittorrent
    for i in xrange(state.current.config['clients_per_host']):
        port = 2000 + i
        with settings(hide('warnings'),warn_only=True):
            sudo('rm -rf /tmp/btclient.%d.data /var/lib/tor/%d/btclient' % (i, i))
        run('dtach -n /tmp/dtach_bt/%(id)d bt_runner %(torrent)s /tmp/btclient.%(id)d.data %(log)s %(port)d' % {
            'id': i,
            'port': port,
            'torrent': torrent,
            'log': '/var/lib/tor/%d/btclient' % i
        })

    # ensure that the non-tor btclients can't talk to the seeders and are
    # forced to talk only to the tor clients
    sudo('iptables -A OUTPUT -p tcp -m multiport --dports 6881:6889 -j REJECT')

    # start up bittorrent w/o tor
    run('dtach -n /tmp/dtach_bt/nontor btdownloadheadless %s --saveas /tmp/btclient.nontor.data --display_interval 30' % torrent)



def stop_btclient():
    with settings(warn_only=True):
        # use -f to catch the torify.pl script as well
        sudo('pkill -f btdownloadheadless')
        # this assumes that there are no other iptables rules!
        sudo('iptables -D OUTPUT 1')


from fabric.api import local,run,env,roles,cd,sudo,put,settings,hide,parallel
from lib.util import state
import random
state.establish()
from fabric.contrib.files import upload_template,append,exists
from lib.util import state,network
import os
import StringIO

def _setup_dtach():
  sudo("apt-get install -y dtach")
  with settings(warn_only=True):
    run("mkdir -p /tmp/curl_dtach")
  sudo("chmod g+w /tmp/curl_dtach")

def start_tcpdump(conf):
  _setup_dtach()
  ip = network.get_deter_ip()
  net_if = run("ifconfig | grep '{0}' -B 1 | grep eth |  cut -d ' ' -f 1".format(ip))
  tcpd_filter = conf['experiment_options']['capture'].get('filter',"").format(ip=ip)

  if env.host.lower() in map(str.lower,env.roledefs['client']):
    for i in xrange(state.current.config['clients_per_host']):
      with cd("{0}/{1}".format(state.get('tor_datadir'),str(i))):
        with settings(warn_only=True):
          pid = run("pgrep tcpdump | xargs")
          if pid:
            sudo("kill {0}".format(pid))
          sudo("rm {host}.pcap".format(host=env.host_string.split(".")[0]))

          dtach_socket = random.randint(0,10000000000)
          with settings(hide('warnings'),warn_only=True):
            sudo("rm -f /tmp/curl_dtach/{0}".format(dtach_socket))


          sudo("dtach -n /tmp/curl_dtach/{dtach} tcpdump -i {net_if} -s 80 -w {host}-{i}.pcap {filter}"
                    .format(net_if=net_if,
                            host=env.host_string.split(".")[0],
                            dtach=dtach_socket,
                            filter=tcpd_filter,
                            i = str(i)))

  else: # directories or rouers
    with cd("{0}".format(state.get('tor_datadir'))):
      with settings(warn_only=True):
        pid = run("pgrep tcpdump | xargs")
        if pid:
          sudo("kill {0}".format(pid))
        sudo("rm {host}.pcap".format(host=env.host_string.split(".")[0]))

        dtach_socket = random.randint(0,10000000000)
        with settings(hide('warnings'),warn_only=True):
          sudo("rm -f /tmp/curl_dtach/{0}".format(dtach_socket))


        sudo("dtach -n /tmp/curl_dtach/{dtach} tcpdump -i {net_if} -s 80 -w {host}.pcap {filter}"
                  .format(net_if=net_if,
                          host=env.host_string.split(".")[0],
                          dtach=dtach_socket,
                          filter=tcpd_filter))

def stop_tcpdump():
  with settings(warn_only=True):
    pid = run("pgrep tcpdump | xargs")
    if pid:
      sudo("kill {0}".format(pid))

socat_runner = """
#!/bin/bash

< $1 socat unix-connect:$2 - | awk '{print strftime("%s"), $0; }' > $3

"""

def start_tor_events():
# Put the control input on the remote host
  control_input = StringIO.StringIO('authenticate ""\nsetevents circ stream stream_bw\n')
  put(control_input,"/tmp/control.in")

  socat_script = StringIO.StringIO(socat_runner)
  put(socat_script, "/tmp/socat_runner")
  sudo("apt-get install -y socat ")
  _setup_dtach()

  if env.host.lower() in map(str.lower,env.roledefs['client']):
    for i in xrange(state.current.config['clients_per_host']):
      with cd("{0}/{1}".format(state.get('tor_datadir'),str(i))):
        if not exists("control"):
          print("No control port found for Tor")
          return


        event_dump = "{host}-{i}.events".format(host=env.host_string.split(".")[0],i=i)

        dtach_socket = random.randint(0,10000000000)
        with settings(hide('warnings'),warn_only=True):
          sudo("rm -f /tmp/curl_dtach/{0}".format(dtach_socket))

        sudo("dtach -n /tmp/curl_dtach/{dtach} bash /tmp/socat_runner /tmp/control.in control {outf} "
                .format(outf=event_dump,
                        dtach=dtach_socket))

  else:
    with cd("{0}".format(state.get('tor_datadir'))):
      if not exists("control"):
        print("No control port found for Tor")
        return

      sudo("apt-get install -y socat ")
      _setup_dtach()

      event_dump = "{host}.events".format(host=env.host_string.split(".")[0])

      dtach_socket = random.randint(0,10000000000)
      with settings(hide('warnings'),warn_only=True):
        sudo("rm -f /tmp/curl_dtach/{0}".format(dtach_socket))

      sudo("dtach -n /tmp/curl_dtach/{dtach} bash /tmp/socat_runner /tmp/control.in control {outf} "
              .format(outf=event_dump,
                      dtach=dtach_socket))

def stop_tor_events():
  with settings(warn_only=True):
    pid = run("pgrep socat | xargs")
    if pid:
      sudo("kill {0}".format(pid))

    
  

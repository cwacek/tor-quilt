from fabric.api import local,run,env,roles,cd,sudo,put,settings,hide,parallel
from lib.util import state
state.establish()
from fabric.contrib.files import upload_template,append,exists
from lib.util import state,network
import os
import StringIO

def start_tcpdump():

  ip = network.get_deter_ip()

  with settings(warn_only=True):
    pid = run("pgrep tcpdump | xargs")
    if pid:
      sudo("kill {0}".format(pid))
    sudo("rm {dir}/{host}.pcap".format(dir=state.get('tor_datadir'),
                                      host=env.host_string.split(".")[0]))

  sudo("( tcpdump -i {ip} -s 64 -w {dir}/{host}.pcap & )".format(ip=ip,
                                                                dir=state.get('tor_datadir'),
                                                                host=env.host_string.split(".")[0]))

def stop_tcpdump():
  with settings(warn_only=True):
    pid = run("pgrep tcpdump | xargs")
    if pid:
      sudo("kill {0}".format(pid))

def start_tor_events():
  if not exists("{dir}/control".format(state.get("tor_datadir"))):
    print("No control port found for Tor")
    return

  sudo("apt-get install socat")

  event_dump = "{dir}/events.capture".format(state.get("tor_datadir"))

# Put the control input on the remote host
  control_input = StringIO.StringIO('authenticate ""\nsetevents circ stream stream_bw\n')
  put(control_input,"/tmp/control.in")

  sudo("( < /tmp/control.in socat unix-connect:{dir}/control - > {outf} ) &".format(dir=state.get("tor_datadir"),
                                                                                  outf=event_dump))

def stop_tor_events():
  with settings(warn_only=True):
    pid = run("pgrep socat | xargs")
    if pid:
      sudo("kill {0}".format(pid))

    
  

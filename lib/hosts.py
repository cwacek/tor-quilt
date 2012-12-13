import yaml
import os
import sys

def load_host_file():
  from fabric.api import env
  if os.path.exists("hostfile.yaml"):
    with open('hostfile.yaml') as hostfilereader:
      hostfile = yaml.load(hostfilereader)
      env.hosts = hostfile['hosts']
      env.roles = hostfile['roles']
      env.roledefs = hostfile['roledefs']

def update_hosts_list():
  import subprocess
  hostfile =dict()
  roles = set()
  hostlist = set()
  roledef = dict()
  try: 
    hosts = subprocess.Popen([ "node_list" ],stdout=subprocess.PIPE).communicate()[0]
  except subprocess.CalledProcessError,e:
    sys.stderr.write("Failed to run 'node_list': [{0}] '{1}'\n".format(e.returncode,e.output))
    return -1
  except OSError,e:
    sys.stderr.write("Failed to find command 'node_list'. "
                     "Are you running this on users.isi.deterlab.net?\n")
    return -1

  import re
  role_re = re.compile("(([a-zA-Z-]+)[^\.]*\.(?:[-a-zA-Z0-9]+)\.(?:[-a-zA-Z0-9]+))")

  #We skip the first line
  for hoststring in hosts.split("\n")[1:]:
    host = hoststring.split("/")[0].strip()
    m = re.match(role_re,host)
    if m:
      host = m.group(1)
      role = m.group(2)
      roles.add(role)
      hostlist.add(host)
      try:
        roledef[role].append(host)
      except KeyError:
        roledef[role] = [host]

  hostfile['roles'] = list(roles)
  hostfile['hosts'] = list(hostlist)
  hostfile['roledefs'] = roledef
  with open('hostfile.yaml','w') as hostfilewriter:
    yaml.dump(hostfile,hostfilewriter)


if __name__ == "__main__":
  update_hosts_list()

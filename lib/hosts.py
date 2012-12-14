import yaml
import os
import sys
import subprocess

# check_output appears in 2.7
try:
    from subprocess import check_output
except:
    def check_output(args):
        return subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]

def load_host_file():
  from fabric.api import env
  if os.path.exists("hostfile.yaml"):
    with open('hostfile.yaml') as hostfilereader:
      hostfile = yaml.load(hostfilereader)
      env.roledefs = hostfile['roledefs']

def update_hosts_list(expname):
  import subprocess
  hostfile =dict()
  roles = set()
  hostlist = set()
  roledef = dict()

  args = ['script_wrapper.py', 'node_list', '-v', '-e', 'SAFER,%s' % expname]
  container = False

  if os.path.exists('/proj/SAFER/exp/%s/containers' % expname):
      # containerized experiment
      args.append('-c')
      container = True

  try:
      hosts = check_output(args).split()
  except subprocess.CalledProcessError, e:
      sys.stderr.write("Failed to find command 'node_list'. "
              "Are you running this on users.isi.deterlab.net?\n")
      sys.stderr.write(str(e))
      return -1

  import re
  role_re = re.compile("(([a-zA-Z]+).*)")

  for host in hosts:
    m = re.match(role_re,host)
    if m:
      if not container:
        host = '%s.%s.safer' % (host, expname)

      role = m.group(2)
      roles.add(role)
      hostlist.add(host)
      try:
        roledef[role].append(host)
      except KeyError:
        roledef[role] = [host]

  #hostfile['roles'] = list(roles)
  #hostfile['hosts'] = list(hostlist)
  hostfile['roledefs'] = roledef
  with open('hostfile.yaml','w') as hostfilewriter:
    yaml.dump(hostfile,hostfilewriter)


if __name__ == "__main__":
  if len(sys.argv) < 2:
    sys.stderr.write("Missing required argument 'experiment_name'\n")
    sys.exit(1)
    
  update_hosts_list(sys.argv[1])

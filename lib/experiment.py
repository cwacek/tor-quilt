from fabric.api import local,run,env,roles,hosts,execute,cd,sudo,put,settings,hide,parallel,get
from lib.util import state
state.establish()
from fabric.contrib.files import upload_template,append
from fabric.colors import red
from lib.util import state,network
import os

def _lower(it):
  return map(str.lower,it)

def save_data(save_to):

  if env.host.lower() in _lower(env.roledefs['directory']):
    __pull_directory_data(state.current.config['tor_datadir'],save_to)
  elif env.host.lower() in _lower(env.roledefs['router']):
    __pull_directory_data(state.current.config['tor_datadir'],save_to)
  elif env.host.lower() in _lower(env.roledefs['client']):
    __pull_client_data(state.current.config['tor_datadir'],save_to)
  else: raise Exception("Unknown host role")
  
def __pull_directory_data(datadir,save_to):
  save_name = "{0}/routers/{1}".format(save_to,env.host_string.split('.')[0])
  src = "{0}/*".format(datadir)
  run("mkdir -p {0}".format(save_name))
  with settings(hide("running","stderr"),warn_only=True):
    for i in xrange(0,10):
      try:
        transferred = get(src, save_name)
      except Exception:
        print(red("Unhandled exception when grabbing files"))
        pass
      else:
        if len(transferred.failed) > 0:
          print(red("Failed to transfer: {0}".format(",".join(transferred.failed))))
        else:
          break


def __pull_client_data(datadir,save_to):
  
  for i in xrange(state.current.config['clients_per_host']):
    save_name = "{0}/clients/{1}-{2}/".format(save_to,env.host_string.split('.')[0],str(i))
    src  = "{0}/{1}/*".format(datadir,str(i))
    run("mkdir -p {0}".format(save_name))
    with settings(hide("running","stderr"),warn_only=True):
      for i in xrange(0,10):
        try:
          transferred = get(src, save_name)
        except Exception:
          print(red("Unhandled exception when grabbing files"))
          pass
        else:
          if len(transferred.failed) > 0:
            print(red("Failed to transfer: {0}".format(",".join(transferred.failed))))
          else:
            break

    





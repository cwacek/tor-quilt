from fabric.contrib.files import exists,contains,append
from fabric.api import sudo,run,settings,hide
import re

STATEFILE="/var/eval_fabric.state"

def ensure_file_open(fname):
  while True:
    try:
      fhandle = open(fname)
    except IOError,e:
      if e.errno == 2:
        raise
      else: pass
    else:
      return fhandle

class state(object):
  """ DONT RUN ME """

  current = None

  @classmethod
  def establish(classtype):
    classtype.current = classtype()

  def __init__(self):
    import shelve
    self.config =  shelve.open('state')
    state.current = self

  @classmethod
  def store(classtype,key,val):
    classtype.current.config[key] = val
    classtype.current.config.sync()

  @staticmethod
  def is_configured(keyword):
    if contains(STATEFILE,"{0}".format(keyword),exact=True):
      return True
    return False

  @staticmethod
  def set_configured(keyword):
    with settings(hide('running','stdout')):
      if not exists(STATEFILE):
        sudo("touch {0}".format(STATEFILE))
        sudo("chmod a+w {0}".format(STATEFILE))
      append(STATEFILE,keyword)

class network(object):
  
  @staticmethod
  def get_iplist():
    with settings(hide('stdout','running')):
      ifconfig_out = run("ifconfig")
      m = re.findall("addr:((?:[0-9]{1,3}.){3}[0-9]+)",ifconfig_out)
      if m:
        return m
  
  @staticmethod
  def get_deter_ip():
    with settings(hide('stdout','running')):
      ifconfig_out = run("ifconfig")
      m = re.findall("addr:(10\.[0-9]{1,3}\.[0-9]{1,3}.[0-9]+)",ifconfig_out)
      if m:
        return m[0]
    


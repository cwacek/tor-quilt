from fabric.api import local,run,env,cd,sudo,put,settings,hide
from lib.util import state
state.establish()
from fabric.contrib.files import upload_template

def setup_http(force=False):
  if state.is_configured("server.setup.http") and force is False:
    print("server.setup.http")
    return
  with settings(hide('stdout')):
    sudo("apt-get -qq update")
    sudo("apt-get -qq install nginx")
    upload_template("lib/templates/nginx-server.conf","/etc/nginx/sites-enabled/default",
                    {'hostname':env.host_string},use_sudo=True,backup=False)
    sudo("mkdir -p /var/www")
    with cd("/var/www/"):
      sudo("dd if=/dev/urandom of=5MB.file bs=1M count=5 >/dev/null 2>&1 ")
      sudo("dd if=/dev/urandom of=3MB.file bs=1M count=3 >/dev/null 2>&1 ")
      sudo("dd if=/dev/urandom of=1MB.file bs=1M count=1 >/dev/null 2>&1")
      sudo("dd if=/dev/urandom of=750KB.file bs=1K count=750 >/dev/null 2>&1")
      sudo("dd if=/dev/urandom of=500KB.file bs=1K count=500 >/dev/null 2>&1")
      sudo("dd if=/dev/urandom of=250KB.file bs=1K count=250 >/dev/null 2>&1")
    sudo("service nginx restart")

    local("wget http://{0}/250KB.file -O /dev/null 2>/dev/null".format(env.host_string),capture=True)

  state.set_configured("server.setup.http")
  print("Nginx up and running on: {0}".format(env.host_string))


def install_voip_tools(force=False):
  if state.is_configured("server.setup.voip") and not force:
    print("server.setup.voip already configured")
    return
  with settings(hide('warnings'),warn_only=True):
    run("mkdir /tmp/staging")
  put("deploy/tcpping.tgz","/tmp/staging/")
  with cd("/tmp/staging"):
    run("tar zxvf tcpping.tgz")
    with cd("tcpping"):
      run("make")
      sudo("make install")
  run("which tcpping")
  run("which voip_emul")
  state.set_configured("server.setup.voip")

  

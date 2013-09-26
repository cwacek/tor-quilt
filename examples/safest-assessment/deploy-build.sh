#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"


cd $DIR/tor
./autogen.sh && ./configure --disable-asciidoc --enable-vivaldi && make

(sudo tee /usr/bin/tor) <<RUNFILE 
#!/bin/bash

type="\$1"
ip="\$2"
datadir="\$3"
rcfile="\$4"

#Start Tor
(
  . $DIR/tor_env_flags
  $DIR/tor/src/or/tor -f \$rcfile 2>&1 >\$datadir/tor_startup &
)

RUNFILE

sudo cp $DIR/tor/src/or/tor /usr/bin/tor.bin

sudo chmod +x /usr/bin/tor


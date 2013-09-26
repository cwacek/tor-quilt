#!/bin/bash

usage(){
  if [[ -n "$1" ]]; then
    echo "Error: $1"
  fi
  echo "mk-tarballs.sh <source_dir> <destination_directory>"
  exit 1
}

asksure() {
echo -n "Continue (Y/N)? "
while read -r -n 1 -s answer; do
  if [[ $answer = [YyNn] ]]; then
    [[ $answer = [Yy] ]] && retval=0
    [[ $answer = [Nn] ]] && retval=1
    break
  fi
done
echo ""
return $retval
}

checkfiles() {
  src=$1
  [[ ! -d "$src" ]] && usage "Source '$src' is not a directory"
  [[ ! -f "$src/deploy-build.sh" ]] && usage "deploy-build.sh does not exist"
  [[ ! -f "$src/tor_tools_dir" ]] && usage "tor_tools_dir does not exist"
  [[ ! -f "$src/tor_or_dir" ]] && usage "tor_or_dir does not exist"
  [[ ! -f "$src/tor_env_flags" ]] && usage "tor_env_flags does not exist"
  [[ ! -d "$src/$(cat $src/tor_or_dir)" ]] && usage "tor_or_dir doesn't point to a valid location"
  [[ ! -d "$src/$(cat $src/tor_tools_dir)" ]] && usage "tor_tools_dir doesn't point to a valid location"
}

dest="$2"
if [[ ! -d "$dest" ]]; then
  usage "Destination '$dest' is not a directory"
fi

src="$1"
checkfiles $src

DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [[ $dest != /* ]];then
  dest="$DIR/$dest"
fi

declare -a tarballs

echo "Ready to tarball $src:"
asksure || exit 3

cd $DIR/$src
echo "tar zcvhf $dest/${src%%/}.tgz *"
tar zcvhf $dest/${src%/}.tgz *




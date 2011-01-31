#!/bin/bash

echo "in lamb2.sh"

cd /home/pkgbuild/packagebuilder 

pushd /home/biocbuild/BBS/$2/bioc/lamb2

. config.sh

popd



export BBS_USER="pkgbuild"
export SVN_USER="pkgbuild"
export SVN_PASS="buildpkg"
export BBS_RSAKEY="/home/pkgbuild/packagebuilder/.packagebuilder.private_key.rsa"
export RSAKEY="/home/pkgbuild/packagebuilder/.packagebuilder.private_key.rsa"
 
$BBS_PYTHON_CMD builder.py $1
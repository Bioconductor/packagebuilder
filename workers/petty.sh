#!/bin/bash

cd /Users/pkgbuild/packagebuilder
pushd /Users/biocbuild/BBS/$2/bioc/petty

. config.sh

popd


export BBS_USER="pkgbuild"
export SVN_USER="pkgbuild"
export SVN_PASS="buildpkg"
export BBS_RSAKEY="/Users/pkgbuild/packagebuilder/.packagebuilder.private_key.rsa"
export RSAKEY="/Users/pkgbuild/packagebuilder/.packagebuilder.private_key.rsa"


$BBS_PYTHON_CMD builder.py $1
 

#!/bin/bash

export PACKAGEBUILDER_RSAKEY="/Users/pkgbuild/packagebuilder/.packagebuilder.private_key.rsa"


cd /Users/pkgbuild/packagebuilder/workers
pushd /Users/pkgbuild/BBS/$2/bioc/montagu

. config.sh

popd


export BBS_USER="pkgbuild"
export SVN_USER="pkgbuild"
export SVN_PASS="buildpkg"

export BBS_PYTHON_CMD=/usr/local/bin/python

$BBS_PYTHON_CMD builder.py $1
 

#!/bin/bash

export PACKAGEBUILDER_RSAKEY="/Users/pkgbuild/packagebuilder/.packagebuilder.private_key.rsa"


cd /Users/pkgbuild/packagebuilder
pushd /Users/biocbuild/BBS/$2/bioc/oaxaca

. config.sh

popd

export BBS_HOME="/Users/biocbuild/BBS"

export BBS_USER="pkgbuild"
export SVN_USER="pkgbuild"
export SVN_PASS="buildpkg"

export BBS_PYTHON_CMD="/usr/bin/python"

export SPB_R_LIBS="/Users/pkgbuild/packagebuilder/R-libs"

$BBS_PYTHON_CMD builder.py $1
 

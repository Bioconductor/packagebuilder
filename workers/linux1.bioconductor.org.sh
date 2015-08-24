#!/bin/bash

echo "in linux1.bioconductor.org.sh"

export PACKAGEBUILDER_RSAKEY="/home/pkgbuild/packagebuilder/.packagebuilder.private_key.rsa"


cd /home/pkgbuild/packagebuilder 

pushd /home/biocbuild/BBS/$2/bioc/linux1.bioconductor.org

. config.sh

popd



export BBS_USER="pkgbuild"
export SVN_USER="pkgbuild"
export SVN_PASS="buildpkg"
 
$BBS_PYTHON_CMD builder.py $1
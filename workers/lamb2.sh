#!/bin/bash

echo "in lamb2.sh"

cd /home/pkgbuild/packagebuilder 

pushd /home/biocbuild/BBS/$2/bioc/lamb2

. config.sh

popd



export BBS_USER="pkgbuild"
export SVN_USER="pkgbuild"
export SVN_PASS="buildpkg"
 
$BBS_PYTHON_CMD $PYARGS builder.py $1
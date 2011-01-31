#!/bin/bash

cd /Users/pkgbuild/packagebuilder
pushd /Users/biocbuild/BBS/$2/bioc/petty

. config.sh

popd


export BBS_USER="pkgbuild"
export SVN_USER="pkgbuild"
export SVN_PASS="buildpkg"

$BBS_PYTHON_CMD $PYARGS builder.py $1


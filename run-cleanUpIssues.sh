#!/usr/bin/env bash

#source ../env/bin/activate

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

source env/bin/activate

python workers/cleanUpIssues.py

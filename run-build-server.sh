#!/usr/bin/env bash

# TODO: Switch to common error handler
err_handler() {
    echo "Error on line $1"
}

trap 'err_handler $LINENO' ERR

# cd to the scripts current directory
cd -P -- "$(dirname -- "$0")"

# As a workaround to https://github.com/pypa/virtualenv/issues/150 , we should 
# enable the virtual environment before setting "nounset"
echo "Enabling virtual environment"
source env/bin/activate

# Fail fast (err_handler above will be invoked)
# Exit immediately if a command exits with a non-zero status.
set -o errexit
# Treat unset variables as an error when substituting.
set -o nounset

# TODO: Load variables in a more modular way
echo "Sourcing environment variables"
. workers/static-config.sh

echo "Now starting server.py ..."
nohup python3 -m workers.server >> server.log 2>&1 &
echo "Server is started."

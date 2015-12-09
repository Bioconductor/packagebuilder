#!/usr/bin/env bash

# TODO: Switch to common error handler
err_handler() {
    echo "Error on line $1"
}

trap 'err_handler $LINENO' ERR

# Fail fast (err_handler above will be invoked)
# Exit immediately if a command exits with a non-zero status.
set -o errexit
# Treat unset variables as an error when substituting.
set -o nounset

# TODO: Load variables in a more modular way
echo "Sourcing unified environment variables"
. workers/static-config.sh

echo "Now starting archiver.py ..."
python -m spb_history.archiver > archiver.log 2>&1 &
echo "Archiver is started."

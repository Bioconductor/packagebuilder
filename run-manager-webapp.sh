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
echo "Sourcing environment variables"
. workers/static-config.sh

# Need to replace crontab entry which originally contained : 
# @reboot python /home/biocadmin/packagebuilder/spb_history/manage.py runserver 0.0.0.0:8000 > /home/biocadmin/packagebuilder/spb_history/server.log 2>&1

# 	Module syntax
# cd spb_history
# python -m ...

# 	Non module syntax
python spb_history/manage.py runserver 0.0.0.0:8000 > manager.log 2>&1 &

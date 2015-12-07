#!/usr/bin/env bash

set -e

# TODO: Load variables in a more modular way
echo "Sourcing unified environment variables"
. workers/static-config.sh

echo "Now starting server.py ..."
python -m workers.server > server.log 2>&1 &
echo "Server is started."

echo "Now starting archiver.py ..."
python -m spb_history.archiver > archiver.log 2>&1 &
echo "Archiver is started."

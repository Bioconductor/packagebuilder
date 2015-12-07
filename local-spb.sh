#!/usr/bin/env bash

set -e
python -m workers/server > server.log 2>&1 &

echo "Server should be started ..."
sleep 3
echo "Now starting archiver"
python -m spb_history/archiver > archiver.log 2>&1 &


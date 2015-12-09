#!/usr/bin/env bash

set -e

ps -ef |grep python| awk '{print $2}'|xargs kill -9

find . -name *pyc |xargs rm

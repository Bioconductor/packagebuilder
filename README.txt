Bioconductor Single Package Builder
====================================

Can be found in this Subversion repository:
https://hedgehog.fhcrc.org/bioconductor/trunk/bioC/admin/build/packagebuilder/

Consists of three main components in three top-level directories:

node - a web application written in node.js (server-side Javascript based on V8).
  Accessible at http://merlot2.fhcrc.org:8000
spb_history - a Django/Python web application that tracks build history
  Accessible at http://merlot2.fhcrc.org:4000
workers - python scripts that run on each build machine

Overview
========

The user interacts with the web application written in node.js to kick off
build jobs. The web application sends messages via ActiveMQ (a Java-based
messaging framework) to listeners on each build machine. The build machines
start building the package and send back progress messages to the web
application, which can display them in real time without page reloading
or Ajax. (This is why node.js is used, because it supports web sockets,
full duplex communication, not just request/response.)

The spb_history web application is simply another listener that writes
all build events to a database.

Where possible, the code uses existing code from the Bioconductor Build
System (BBS). In particular, it uses BBS scripts to set environment variables
for the build, though these are overridden in a couple of cases.

On the build machines, the listener that is always running is called
server.py. When it receives a build request, it kicks off a script
particular to that build machine (called e.g. petty.sh or moscato2.bat)
which sets environment variables, then runs builder.py to do the
actual building.


Deployment
==========

The node and spb_history web applications are deployed on merlot2
(see the 'single package builder' section of biocadmin@merlot2's crontab
to see how they are started).

On the build machines, the listeners run as the user 'pkgbuild' 
(which has the same password as the 'biocbuild' user).

On Mac and Linux, the listeners are started as follows:

cd ~/packagebuilder
nohup python server.py > server.log 2>&1 &

On Windows, the listener is configured as a service (called
BioC Single Package Builder) which can be restarted under
Control Panel:Services.

Build Machines
==============
As of 6/11/2012, the single package builder builds on the following machines:
- lamb2 (linux)
- petty (Mac)
- moscato2 (windows)

The single package builder only builds packages for BioC 2.10 at the present
time. Further modification will be required in order for it to build BioC 2.11
packages as well.

Known Issues
============

The code does not always seem to properly install dependencies required
by packages that it builds.

The following minor issues are also listed in the bug tracker:
https://bioc-internal.atlassian.net/browse/BUILD-4
https://bioc-internal.atlassian.net/browse/BUILD-1



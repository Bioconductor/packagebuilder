Bioconductor Single Package Builder 
====================================

Can be found in this Subversion repository:
https://hedgehog.fhcrc.org/bioconductor/trunk/bioC/admin/build/packagebuilder/

Consists of three main components in three top-level directories:

node - a web application written in node.js (server-side Javascript based on V8).
  Accessible at http://staging.bioconductor.org:8000
spb_history - a Django/Python web application that tracks build history
  (eventually will be) Accessible at http://staging.bioconductor.org:4000
workers - python scripts that run on each build machine

Overview
========

The user interacts with the web application written in node.js to kick off
build jobs. The web application sends messages via ActiveMQ (a Java-based
messaging framework) to listeners on each build machine. The build machines
start building the package and send back progress messages to the web
pplication, which can display them in real time without page reloading
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

The node and spb_history web applications are deployed on
staging.bioconductor.org
(see the 'single package builder' section of 
biocadmin@staging.bioconductor.org's crontab
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
As of 6/12/2012, the single package builder builds on the following machines:
BioC 2.10:
- lamb2 (linux)
- petty (Mac)
- moscato2 (windows)
BioC 2.11:
- lamb1 (linux)
- perceval (Mac)
- moscato1 (windows)

Known Issues
============

The code does not always seem to properly install dependencies required
by packages that it builds.

The following minor issues are also listed in the bug tracker:
https://bioc-internal.atlassian.net/browse/BUILD-1
https://bioc-internal.atlassian.net/browse/BUILD-4
https://bioc-internal.atlassian.net/browse/BUILD-6


Roundup Tracker Integration
===========================

When a tarball is submitted to the issue tracker
(http://tracker.bioconductor.org/), a job is
submitted to the Single Package Builder (SPB).

There are several components to this integration. The
first is an add-on to Roundup known as a 'reactor'.

The tracker lives on habu at 
www-data@habu:/var/www-trackers/bioc_submit
The tracker code is in sourceforge (mercurial) at:
https://sourceforge.net/u/dtenenba/roundup-bioc/ci/default/tree/
The reactor will be migrated here (FIXME: do this):
https://hedgehog.fhcrc.org/bioconductor/trunk/bioC/Projects/bioc_submit_tracker/detectors/builder_reactor.py

Integration Workflow
--------------------
FIXME: update this

When new messages are added to the tracker, the reactor is run.
If a new tarball is detected, the reactor calls another
python script 
(https://hedgehog.fhcrc.org/bioconductor/trunk/bioC/Projects/bioc_submit_tracker/customizations/sendmessage.py).
Another script is necessary because the tracker runs under 
Python 2.3, but the libraries that are required to start
an SPB job require a newer version of python (2.7 is used).

This second script sends a message to an Amazon Simple Queue Service
(SQS) queue. SQS is used here (instead of ActiveMQ which is used 
for the rest of SPB) because mamba is in the DMZ and cannot connect
to pinot, where the ActiveMQ server is located.

A script running on pinot
(https://hedgehog.fhcrc.org/bioconductor/trunk/bioC/admin/build/packagebuilder/spb_history/aws_monitor.py)
listens for messages posted to this SQS queue. When it receives a message,
it sends another message to the ActiveMQ queue used to signal new builds.
This starts the normal SPB workflow described at the start of this document.
The message sent to SPB contains a flag indicating that this build was
originated by the SPB.

When the build is complete, another script on pinot
(https://hedgehog.fhcrc.org/bioconductor/trunk/bioC/admin/build/packagebuilder/spb_history/spb_poster.py)
is listening, and it posts a message to the tracker
(using an HTTPS request) including a link to the build report.

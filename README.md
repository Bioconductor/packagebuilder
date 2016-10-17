Bioconductor Single Package Builder (SPB)
=========================================
[![Build
Status](https://travis-ci.org/Bioconductor/packagebuilder.svg)](https://travis-ci.org/Bioconductor/packagebuilder)

The code is stored in [GitHub](https://github.com/Bioconductor/packagebuilder).

Currently, SPB consists of 2 components in this git repo, in top-level directories:
* spb_history - A Django web app to track build history.
  Accessible at http://staging.bioconductor.org:4000
* workers - Python scripts that run on each build machine

Overview
========

##### Options to start a build:
1. Submitting packages to [github](https://github.com/Bioconductor/Contributions)
2. Running the [rerun_build.py](spb_history/rerun_build.py) script

These all send messages to an installation of RabbitMQ (a Java-based messaging framework)
to listeners on each build machine ([server.py](workers/server.py)). The build machines
start building the package and send back progress messages.

There is another listener (called [archiver.py](workers/archiver.py) which
writes build events to a database, where they can
then be displayed by the spb_history web application
(written in Python's Django framework).

Where possible, the code uses existing code from the Bioconductor Build
System (BBS). In particular, it uses BBS scripts to set environment variables
for the build, though these are overridden in a couple of cases.

On the build machines, the listener that is always running is called
[server.py](workers/server.py). When it receives a build request, it kicks off a script
particular to that build machine (called e.g. petty.sh or moscato2.bat)
which sets environment variables, then runs [builder.py](workers/builder.py) to do the
actual building.



Build Machines
==============

See `active_devel_builders` in http://bioconductor.org/config.yaml
to see which machines are used by the SPB.



System Integration
===========================

When a package is submitted to the github contributions
(https://github.com/Bioconductor/Contributions), a job is
submitted to the Single Package Builder (SPB).

There are several components to this integration. The
first manages when issues (packages) are submitted. The code
for this component can be found at
[issue_tracker_github](https://github.com/Bioconductor/issue_tracker_github)
and is implemented on the AWS cloud instance issues.bioconductor.org


Integration Workflow
--------------------
When a package submits a version bump, the above manager is run.
It sends a message to the listeners on each build node as described
at the start of this document.

The message sent to SPB contains a flag indicating that this build was
originated by the SPB.

When the build is complete, another script on staging
[track_build_completion.py](spb_history/track_build_completion.py)
is listening, and it posts a message to the contribuctions issue
(using an HTTPS request) including a link to the build report.



## SPB Moving Parts

The SPB was designed to use a message broker (in this case RabbitMQ)
so that components could be loosely coupled and so that they could
send information in an asynchronous, real-time fashion, allowing
live updates.

In practice there are some dependencies between the moving parts.

Here are the moving parts, first briefly and then in more detail.

* Broker - currently a machine in the cloud called
  rabbitmq. All it does is run an RabbitMQ
  message broker. Messages are passed using a text protocol
  called STOMP.
* Issue manager. Currently implemented on the machine
  issues.bioconductor.org. It detects when a package is submitted,
  or updated, and sends a message to the SPB telling it to start a build.
* build node server; a python script called [server.py](workers/server.py) should
  be running on each build node at all times. When an
  instruction is received to start a build, this script
  starts a new process (first sourcing some variables
  specific to the build node, then running a python script
  called [builder.py](workers/builder.py)).
* Three scripts that run on the staging.bioconductor.org machine:
  1. [track_build_completion.py](spb_history/track_build_completion.py): monitors progress
     of builds and when a build is complete (all machines
     have finished) it posts the build report to the web
     and posts a message to the issue.
  2. [archiver.py](workers/archiver.py): monitors progress of builds, writes all build
     info to a database to be displayed by a Django web app
     (what you see when you hit
[http://staging.bioconductor.org:8000/](http://staging.bioconductor.org:8000/)).
  3. [rerun_build.py](spb_history/rerun_build.py): for manually kicking off an SPB build
     without having to version bump or resubmit.

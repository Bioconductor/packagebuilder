Bioconductor Single Package Builder 
====================================

Can be found in this Github repository:
https://github.com/Bioconductor/packagebuilder

Consists of three main components in three top-level directories:

* node - a web application written in node.js (server-side Javascript based on V8). Currently disabled. Formerly
  accessible at http://staging.bioconductor.org:4000
* spb_history - a Django/Python web application that tracks build history
  Accessible at http://staging.bioconductor.org:4000
* workers - python scripts that run on each build machine

Overview
========

Build jobs are kicked off by 1) submitting tarballs to the tracker,
2) running the spb_history/rerun_build.py script, or 3) using
the node.js gui front end (which is currently disabled).
These all send messages via ActiveMQ (a Java-based
messaging framework) to listeners on each build machine. The build machines
start building the package and send back progress messages.
If using the (currently disabled) node.js web app, these messages
are displayed on receipt without page reloading or Ajax. (This is why node.js is used, because it supports web sockets,
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

See `active_devel_builders` in http://bioconductor.org/config.yaml
to see which machines are used by the SPB.



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

When new messages are added to the tracker, the reactor is run.
It sends a message to the listeners on each build node as described
at the start of this document.

The message sent to SPB contains a flag indicating that this build was
originated by the SPB.

When the build is complete, another script on staging
(https://github.com/Bioconductor/packagebuilder/blob/master/spb_history/track_build_completion.py)
is listening, and it posts a message to the tracker
(using an HTTPS request) including a link to the build report.

Care and Feeding
----------------

A lot of work was done to make the spb run stably, but
there are some new issues, especially since moving
the build machines back to the Hutch. The build nodes
seem to lose contact with the broker even though
they appear to be listening. These steps should take
you through diagnosing the problem.

## Determining if the SPB is stuck

If you are working with a particular package you may already 
suspect that the SPB is stuck because you are awaiting a
build report and it has not shown up.

You can go to
[http://staging.bioconductor.org:8000/](http://staging.bioconductor.org:8000/)
and click on the name of the package and then the most recent build.
(if a build is in progress, you can refresh this page to see progress).
If you do not see all 3 build machines (Linux, Windows and Mac OS X Mavericks), or if the builds all appear to be stuck, then something is wrong.

Before you can diagnose the problem further, you need to understand
the various components of the SPB.


## SPB Moving Parts

The SPB was designed to use a message broker (in this case ActiveMQ)
so that components could be loosely coupled and so that they could 
send information in an asynchronous, real-time fashion, allowing
live updates.

In practice there are some dependencies between the moving parts.

Here are the moving parts, first briefly and then in more detail.

* Broker - currently a machine in the cloud called 
  broker.bioconductor.org. All it does is run an ActiveMQ
  message broker. Messages are passed using a text protocol
  called STOMP. We may want to change the SPB to use 
  Amazon Simple Queue Service (SQS) instead of ActiveMQ, then
  we would not pay for a broker machine to be up all the time,
  just for the individual messages we send.
* Roundup detector. Part of the issue tracker, it detects
  when a tarball is submitted and sends a message to the
  SPB telling it to start a build.
* build node server; a python script called server.py should
  be running on each build node at all times. when an 
  instruction is received to start a build, this script
  starts a new process (first sourcing some variables 
  specific to the build node, then running a python script
  called builder.py).
* the node.js front end; not currently enabled
* Three scripts that run on the staging.bioconductor.org machine:
  1) track_build_completion.py: monitors progress
     of builds and when a build is complete (all machines
     have finished) it posts the build report to the web
     and sends a message to the tracker.
  2) archiver.py: monitors progress of builds, writes all build
     info to a database to be displayed by a Django web app
     (what you see when you hit [http://staging.bioconductor.org:8000/](http://staging.bioconductor.org:8000/)).
  3) rerun_build.py: for manually kicking off an SPB build without
     having to repost a tarball to the tracker.

## Troubleshooting Workflow

 As mentioned above, first go to 
 [http://staging.bioconductor.org:8000/](http://staging.bioconductor.org:8000/)
 to see if the build is indeed stuck. If it appears that one or
 more build nodes are not responding, you probably need to
 restart the listener (server.py) on those nodes (see next section).

 # Restarting listeners on build nodes

### Unix Nodes

 For unix nodes (Linux and Mac) you should `ssh` to
 the build node as the `pkgbuild` user; (the "credentials")
 Google Doc can tell you how to do this.

 You should `cd` to the `~/packagebuilder` directory.
 Then do this to see if the `server.py` script is running:

     ps aux|grep server.py|grep -v grep

 If it is not running, then you can examine the server.log 
 which may tell you why the server is not running.

 Or, it may be that the `server.py` process is still running,
 but for some reason it is not receiving messages.
 (This has started to happen since the move back to the
 hutch, and I'm just guessing, but switching to Amazon SQS
 _might_ fix this). To test this, examine the end of `server.log`
 with the `tail` command and look at the last modified time
 of the file. If it does not seem to be receiving messages
 that you know it should have received, then the server needs
 to be restarted. The `ps` command above should have
 given you a process id (in the second column).

 You can kill that process with `kill -9`.

Then to start or re-start the server, do this:

nohup python server.py > server.log 2>&1 &

Note that `pkgbuild`'s crontab has entries that will
start the server when the node is rebooted.

### Windows Nodes

On windows the server.py script is managed by
a windows service.

On windows you should log into the build node as 
FHCRC\your_hutchnet_id or as Administrator.
You can examine the server logs by switching to
the packagebuilder directory, which is
`d:\packagebuilder` on moscato1 and 
`e:\packagebuilder` on moscato2.
You can examine server.log in the same way as you
would on a unix node. The files `server.stdout.log`
and `server.stderr.log` also exist and contain the
output that windows generates when trying to start
the server. 

To actually stop and restart the service on windows
you use the Server Manager. Navigate to Services.
Find the service called "BioC Single Package Builder"
and note if it is running (should say "Started" in the
"Status" column). Whether or not it is running, you
can restart it by selecting the row called
"BioC Single Package Builder" and clicking the
restart button (which looks like an audio "Play"
button with a vertical line to the left of it).

## Scripts on staging.bioconuctor.org

It is essential that the scripts `track_build_completion.py`
and `archiver.py` be running on staging.bioconductor.org.

You can check that these are running by ssh'ing to
staging.bioconductor.org as the `biocadmin` user.
Refer to the "credentials" google doc if you need help with this.

Then `cd` to `~/packagebuilder/spb_history`.

You can determine if the scripts are running as follows:

    ps aux|grep track_build_completion.py|grep -v grep
    ps aux|grep archiver.py|grep -v grep

If either script is not running you can restart it with 
one of the following commands:

    nohup python track_build_completion.py > track_build_completion.log 2>&1 &
    nohup python archiver.py > archiver.log 2>&1 &

Note that if either of these scripts were not running, you probably
have to restart a given build to get it to complete (see 
next section).

### Manually restarting a build

ssh to staging.bioconductor.org as `biocadmin`. 
cd to `~/packagebuilder/spb_history`. 

You need to determine two pieces of information in 
order to restart a build manually. Both pieces can
be determined in the tracker
([https://tracker.bioconductor.org](https://tracker.bioconductor.org)).
Find the issue containing the tarball that you want to
restart a build of. Let's say for example that the issue number is
558 (the issue number will appear in the tracker URL, for
example [https://tracker.bioconductor.org/issue558](https://tracker.bioconductor.org/issue558)).
Then get the URL of the tarball that
you want to restart a build for. You can do this by right-clicking
on the appropriate link and choosing "Copy Link". 
An example URL is: 
[https://tracker.bioconductor.org/file3243/spbtest2_0.99.0.tar.gz](https://tracker.bioconductor.org/file3243/spbtest2_0.99.0.tar.gz)

So now with these two pieces of information you
can restart an SPB build as follows:

python rerun_build.py 558 https://tracker.bioconductor.org/file3243/spbtest2_0.99.0.tar.gz

You can then monitor the build by going to 
[http://staging.bioconductor.org:8000/](http://staging.bioconductor.org:8000/)
and then navigating to the package and latest build. You can
periodically refresh the page to see progress.

You might wonder why you have to ssh to staging.biooconductor.org
to run this script. Seemingly you should be able to check out
and run the rerun_build.py script on your own machine.
The reason is that not every machine has access to the 
security group under which the ActiveMQ broker runs. 
You can give your IP (or subnet) access to this
group [here](https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#SecurityGroups:search=stomp;sort=Name).


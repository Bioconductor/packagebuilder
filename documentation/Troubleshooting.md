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
If you do not see all 3 build machines (Linux, Windows and Mac OS X Mavericks), or if the
builds all appear to be stuck, then something is wrong.

Before you can diagnose the problem further, you need to understand
the various components of the SPB.


## Troubleshooting Workflow

 As mentioned above, first go to
 [http://staging.bioconductor.org:8000/](http://staging.bioconductor.org:8000/)
 to see if the build is indeed stuck. If it appears that one or
 more build nodes are not responding, you probably need to
 restart the listener (server.py) on those nodes (see next section).

## Restarting listeners on build nodes

### Unix Nodes

 For unix nodes (Linux and Mac) you should `ssh` to
 the build node as the `pkgbuild` user; (the "credentials"
 Google Doc can tell you how to do this).

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
example
[https://tracker.bioconductor.org/issue558](https://tracker.bioconductor.org/issue558)).
Then get the URL of the tarball that
you want to restart a build for. You can do this by right-clicking
on the appropriate link and choosing "Copy Link".
An example URL is:

[https://tracker.bioconductor.org/file3243/spbtest2_0.99.0.tar.gz](https://tracker.bioconductor.org/file3243/spbtest2_0.99.0.tar.gz)

So now with these two pieces of information you
can restart an SPB build as follows:

    python rerun_build.py 558
https://tracker.bioconductor.org/file3243/spbtest2_0.99.0.tar.gz

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
group
[here](https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#SecurityGroups:search=stomp;sort=Name).
You need to enable TCP access on port 61613 (the STOMP port).

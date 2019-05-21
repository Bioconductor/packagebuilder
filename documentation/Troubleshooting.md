Troubleshooting
----------------

A lot of work was done to make the spb run stably, but
there are some lingering issues. The most common is build nodes
seem to lose contact with the broker even though
they appear to be listening. These steps should take
you through diagnosing the problem. These steps are also for restarting build
nodes, restarting spb scripts on staging.biocondcutor.org, and for diagnosing 
stomp (rabbitmq) issues.

# Determining if the SPB is stuck

ps aux | grep pkgbuildIf you are working with a particular package you may already
suspect that the SPB is stuck because you are awaiting a
build report and it has not shown up.

You can go to
[http://staging.bioconductor.org:8000/](http://staging.bioconductor.org:8000/)
and click on the name of the package and then the most recent build.
(if a build is in progress, you can refresh this page to see progress).
If you do not see all 3 build machines (Linux, Windows and Mac OS X Mavericks), 
or if the builds all appear to be stuck, then something is wrong.

Before you can diagnose the problem further, you need to understand
the various components of the SPB.


# Troubleshooting Workflow

 As mentioned above, first go to
 [http://staging.bioconductor.org:8000/](http://staging.bioconductor.org:8000/)
 to see if the build is indeed stuck. If it appears that one or
 more build nodes are not responding, you probably need to
 restart the listener (server.py) on those nodes (see next section). Before
 restarting please check the logs for the package trying to be installed on the
 build node[s] in questions to see if there was an issue with the package itself: 
 Currently on a build node that location is 
 /packagebuilder/workers/jobs/\<issue number\>/

# Restarting listeners on build nodes

### Unix Nodes

 For unix nodes (Linux and Mac) you should `ssh` to
 the build node as the `pkgbuild` user; (the "credentials"
 Google Doc can tell you how to do this).

 You should `cd` to the `~/packagebuilder` directory. I generally always
 activate the virtual environment as well `source env/bin/activate`.
 Then do this to see if the `server.py` script is running:

     ps aux|grep server.py

Or look at all pkgbuild processes

    ps aux | grep pkgbuild

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

Alternatively, you can start all relevant scripts for the spb

    source env/bin/activate
    killall python
    ./run-build-server.sh

**Note** that `pkgbuild`'s crontab has entries that will
start the server when the node is rebooted.

Sometimes if the builder was in the middle of a build, there could be random
R processes running that may or may not complete.  similarly to above you could 
killall R process 

    killall R 
    
And sometimes still other random processes kicked off by packages 

    ps aux | grep pkgbuild
    killall -u pkgbuild
    
### Windows Nodes

On windows the server.py script is managed by
a windows task scheduler.

On windows you should log into the build node as pkgbuild.
You can examine the server logs by switching to the packagebuilder directory, 
which is `C:\Users\pkgbuild\packagebuilder`. You can examine server.log in the 
same way as you would on a unix node. The file `server.log` exist and contain 
the output that windows generates when trying to start the server.

To actually stop and restart the service on windows you can use the Server 
Manager Task Scheduler. Open the task scheduler and navigate to Task Scheduler -> Task Scheduler Library -> BBS. Find the task called `spb-server` and see if it is not running (should say 
"Running" in the "Status" column). Whether or not it is running, you can restart
it by selecting the row called `spb-server` and right-click. This will bring a 
drop down menu of options. Select `End` to stop the task. Optionally at 
this point, you can navigate to the `~/packagebuilder/` in the admin command 
window and `rm server.log`. We also must stop the taks
loggon_pkgbuild_at_startup. Selecting the row called
`loggon_pkgbuild_at_startup` and right-click. This will bring a drop down menu
of options. Select `End` to stop the task. Next bring up the Task Manager. One
way to do this is to right-click on the bottom tool bar and Select `Task
Manager` in the drop down menu that appears. Select the tab called
`Details`. Next order the tasks by `User name`. Find the process `python.exe`
Running by the user name pkgbuild. Select this row and terminate the process.  
Then back in the task scheduler, right-click on `loggon_pkgbuild_at_startup`
again, and choose `Run`, the "Status" should change to "Running". The select
`spb-server`, and choose `Run`, the "Status" should change to "Running"; if it
does not repeat the process.

**Note:** Like on linux, if the SPB stopped suddenly or there is some issue that
required a hard stop, sometime there are rogue R processes running.  When in the 
Task Manager, any R process that is labelled as pkgbuild owned should be stopped before
restarting the server.


# Scripts on staging.bioconuctor.org

### Archiver and Track\_build\_completion

It is essential that the scripts `track_build_completion.py`
and `archiver.py` be running on staging.bioconductor.org.

You can check that these are running by ssh'ing to
staging.bioconductor.org as the `biocadmin` user.
Refer to the "credentials" google doc if you need help with this.

Then `cd` to `~/packagebuilder`. I generally always activate the virtual
environment as well `source env/bin/activate`.

You can determine if the scripts are running as follows:

    ps aux | grep python 

You should see an entry for archiver and track\_build\_completion. If either 
script is not running you can restart it with one of the following commands:

    nohup python track_build_completion.py > track_build_completion.log 2>&1 &
    nohup python archiver.py > archiver.log 2>&1 &
    
or 

    ./run-achiver.sh
    ./run-track_build_completion.sh

Note that if either of these scripts were not running, you probably
have to restart a given build to get it to complete (see Manually restarting a 
build section).

### Web Browser/Django

Another component to the spb is django which controls the web browser interaction. 
You can determine if the django script is running through the same command as 
above and look for two entries for manage. If there have been updates to any of 
scripts that control the web browser output it is recommended to restart django.
If the scripts are running determine the parent and child process started for 
manage and `kill -9` both. To restart use the following command:

    ./run-django.sh


### Restart all spb scripts on staging 

Alternatively, if all scripts were down or a manual reboot is necessary, the 
following will restart all scripts relevant to the spb

    source env/bin/activate
    killall python
    ./all.sh

To see if all the servers (build nodes) and staging scripts are running, while 
logged in as `biocadmin` on staging.bioconductor.org, in `~/packagebuilder`, 
activate the virtual environment with `source env/bin/activate`, and then run 
the `python pinger.py`.  This script will show all the active scripts talking to 
the rabbitmq messaging service. (**NOTE:** Django/manager will not have an entry.)
If the stomp connection cannot be connected rabbitmq might not be running and 
may need to be restarted (see section Reactivating Rabbitmq)

### Manually restarting a build

ssh to staging, change to the apropriate directory, and activate the virtual environment

    ssh biocadmin@staging.bioconductor.org
    cd ~/packagebuilder
    source env/bin/activate

You need to determine two pieces of information in
order to restart a build manually. Both pieces can
be determined in the [GitHub tracker][].
Find the issue number assigned to the package that you want to
restart a build of. The get the URL of the GitHub repository containing all the 
code of the package that you want to start a build for. 

An example is [spbtest3](https://github.com/Bioconductor/Contributions/issues/51):
It's issue number is 51 and it's URL is:
[https://github.com/Bioconductor/spbtest3](https://github.com/Bioconductor/spbtest3).

So now with these two pieces of information you can restart an SPB build as follows:

    python rerun_build.py 51 https://github.com/Bioconductor/spbtest3

You can then monitor the build by going to
[http://staging.bioconductor.org:8000/](http://staging.bioconductor.org:8000/)
and then navigating to the package and latest build. You can
periodically refresh the page to see progress.

You might wonder why you have to ssh to staging.biooconductor.org
to run this script. Seemingly you should be able to check out
and run the rerun_build.py script on your own machine.
The reason is that not every machine has access to the
security group under which the RabbitMQ broker runs.
You can give your IP (or subnet) access to this
group
[here](https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#SecurityGroups:search=stomp;sort=Name).
You need to enable TCP access on port 61613 (the STOMP port).

[GitHub tracker]: https://github.com/Bioconductor/Contributions/issues

# Restarting RabbitMQ

RabbitMQ connects `staging.bioconductor.org` with the build nodes. If there is a
problem with the stomp connection rabbitmq may have been disconnected. The 
following are the steps that should be taken to check and restart. 

You can check that it is running by ssh'ing to
rabbitmq.bioconductor.org as the `ubuntu` user.

Once logged in you can check which docker instances are running with the following: 

    sudo docker ps -a 
    
A process with the name `some-rabbit` should be running with Status (`Up <some amount of time>`).  If it is not running restart the process with the following:

    sudo docker restart some-rabbit
    
This should restart the docker. 

Now that the docker has been restarted. All the build nodes and 
staging.bioconductor.org should be restarted as they are talking to a stale 
rabbitmq instance. Follow the procedures above for restarting listners on 
build nodes and for restarting all scripts on staging. 

# Node not connecting to Rabbitmq

When a node is first being deployed it might have issues connecting to
rabbitmq.bioconductor.org.  If the node is not displaying as active on staging,
log back into the node and check /Users/pkgbuild/packagebuilder/server.log.  

If you see something like the following you will have to adjust the security
setting on the AWS instance for rabbitmq:

```
ERROR: 05/15/2017 07:06:35 AM communication.py:30 - Cannot connect to Stomp at 'rabbitmq.bioconductor.org:61613'.
ERROR: 05/15/2017 07:06:35 AM server.py:250 - main() Could not connect to RabbitMQ: 
```
Log on to AWS, EC2 instances, select instances and find the
rabbitmq.bioconductor.org:

1. Select that instance. 
2. In the description box below, find Security groups, click on stomp. 
3. Select Inbound
4. Select Edit
5. Add a custom tcp rule, for port 61613, for the IP address of the node and add
`/32` : so the format `<IP>/32`

If you don't know the nodes IP address you can run the following command line on
the node `ifconfig |grep inet`


# Valid push but no report and no TIMEOUT

1.  Check http://staging.bioconductor.org:8000/ for the package.  See if
temporary build report is displaying correctly 

2. Sometimes when connection is bad/slow (or other misc reasons), the build
report will not show the OS /Arch - this generally means it couldn't connect
correctly. 

3. Recommended to restart that particular node 

4. Also Recommend restart staging.bioconductor.org scripts. 



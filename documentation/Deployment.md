Deployment
==========

# Update the AWS rabbitmq instance 
**NOTE:** This section applies if adding a new Bioconductor Build server.

Login to AWS, Navigate to Instances, click on rabbitmq. In the details section
on the bottom, navigate to Security groups and click on stomp. Add the new
server's external IP address to the Inbound.

# Linux/MAC Install : 

All steps should be performed as user `pkgbuild` unless otherwise noted.

#### Clone Repositories

**Note**: For now (Nov 2019) you need to use the `python3` branch
of `packagebuilder` and `bioc-common-python`. This is until the `python3`
branch of these 2 repositories gets merged into their `master` branch.

```
git clone https://github.com/Bioconductor/packagebuilder.git
git -C packagebuilder checkout python3      # temporarily needed

git clone https://github.com/Bioconductor/bioc-common-python.git
git -C bioc-common-python checkout python3  # temporarily needed

cd packagebuilder
```

#### Set Up Virtual Envirnment and Install Dependencies 
At this point, you need to determine if it's a new
or previously used build server.  If new (or simply a new install 
on the same server), you'll need to create a virtual environment.

1. If `virtualenv` is not installed on your machine,
   [install it](http://virtualenv.readthedocs.org/en/latest/installation.html).  
   Afterwards, create an environment called "env":   
  ```
  virtualenv -p python3 env
    
  # python3 is indicator of executable path location: 
  which python3
  ```
NOTE:  do not use venv.  There are subtle differences from venv and virtualenv that have proven problematic.

2. Next, activate the environment:
  ```
  source env/bin/activate
  ```

3. You should see your shell change with the environment activated.  Next
   install the dependencies:
   
```
   pip3 install stomp.py pytz stompy

   cd ../bioc-common-python
   pip3 install --upgrade -r PIP-DEPENDENCIES--bioc-common-python.txt
   python3 setup.py install

   cd ../packagebuilder
   pip3 install --upgrade -r PIP-DEPENDENCIES--packagebuilder.txt
```

   **Note:** The `stompy` module doesn't seem to be available for Python 3
   at the moment (Nov 2019) so skip it. It doesn't seem to be needed anyway.

   **Note**: For now (Nov 2019), the first line in
   `packagebuilder/PIP-DEPENDENCIES--packagebuilder.txt` has been modified
   to install the `python3` branch of bioc-common-python from GitHub.
   Remove `@python3` from this line once the `python3` branch of
   bioc-common-python gets merged into its `master` branch.

   **Note:** If there is trouble with a particular version of a dependency
   you can update the versions in these files. These versions were stable 
   and working on our systems. 
   
   **Note:** There are several system dependecies that may need to be 
   installed. Some common ones that have been needed if not already installed 
   are: libffi-dev, build-essential, libssl-dev, python-dev, openssl. These 
   generally would be installed with [sudo] apt-get install \<name\>
   
   **Note:** Sometimes the 'egg' doesn't install properly when installing the
   above from bioc-common-python and there is an ERROR when installing the
   packagebuilder dependencies. If this is the case go back and redo the
   bioc-common-python commands above.

#### Configuration 

1.  Navigate back into the packagebuilder directory. Create a new directory
entitled `spb-properties` with a text file entitled `spb.properties`. Be mindful
of capitalization and punctuation. The `spb.properties` file should contain the
following: 
```
[Sensitive]
svn.user=
svn.pass=
tracker.user=
tracker.pass=
github.token=
```
    The values can be undefined. If you are deploying on a Bioconductor Build
    Node please grab this file from the private repository. 

2. You'll need to modify two configuration files. 

    i. Copy the provided `TEMPLATE.properties` to a unique properties file for
    your system `<host name>.properties`. Update all the values in this
    file as necessary. The `builders` value should match `<host name>`.

    ii. Secondly, change `bioconductor.properties` values. The `environment`
    variable should match  `<host name>` and update the BioC version
    accordingly
    
3. **NOTE:** For Bioconductor Nodes, we standardized the private/public key
information copy over the key from existing builder (see properties file)

#### Start server
Kick off the server 
```
killall python3
./run-build-server.sh
```

#### Automate

Crontab for pkgbuild on `<host name>`: 
```
@reboot /home/pkgbuild/packagebuilder/run-build-server.sh
00 04 * * * /home/pkgbuild/packagebuilder/run-cleanUpIssues.sh
```

#### MAC specific Note:

If the new node is a new version of MAC OS, the following script on staging.bioconductor.org should be updated: 
`/loc/www/bioconductor-test.fhcrc.org/scratch-repos/<BiocVersion>/update-repo.R`

# Windows Install: 

All steps should be performed as user `pkgbuild` unless otherwise noted.
Ensure that the pkgbuild account is set up following the [BBS
directions](https://github.com/Bioconductor/BBS/blob/master/Doc/Prepare-Windows-Server-2019-HOWTO.md#7-single-package-builder-requirements). It
is important that the pkgbuild account has access to the BBS of the biocbuild
account. Make sure Python 3 is installed on the machine (check that you can start
`python` at the command line and that this starts Python 3).
Also `pip` should be available (equivalent of `pip3` on Linux or Mac).



#### Clone Repositories and Make Log Directory

**Note**: For now (Nov 2019) you need to use the `python3` branch
of `packagebuilder` and `bioc-common-python`. This is until the `python3`
branch of these 2 repositories gets merged into their `master` branch.

```
git clone https://github.com/Bioconductor/packagebuilder.git
git -C packagebuilder checkout python3      # temporarily needed

git clone https://github.com/Bioconductor/bioc-common-python.git
git -C bioc-common-python checkout python3  # temporarily needed

mkdir log

cd packagebuilder
```

#### Set Up Virtual Envirnment and Install Dependencies 
At this point, you need to determine if it's a new
or previously used build server.  If new (or simply a new install 
on the same server), you'll need to create a virtual environment.

1. If `virtualenv` is not installed on your machine,
   [install it](http://virtualenv.readthedocs.org/en/latest/installation.html).  
   Afterwards, create an environment called "env":   
```
    virtualenv env
```
**Note:** It was suggested to use venv that is shipped with python3. Do NOT use this. We need to use virtualenv

2. Next, activate the environment:
```
    .\env\Scripts\activate
```

3. You should see your shell change with the environment activated.  Next
   install the the dependencies:
   
```
   pip install stomp.py pytz
   
   cd ../bioc-common-python
   pip install --upgrade -r PIP-DEPENDENCIES--bioc-common-python.txt
   python setup.py install

   cd ../packagebuilder
   pip install --upgrade -r PIP-DEPENDENCIES--packagebuilder.txt
```
   
   **Note**: For now (Nov 2019), the first line in
   `packagebuilder/PIP-DEPENDENCIES--packagebuilder.txt` has been modified
   to install the `python3` branch of bioc-common-python from GitHub.
   Remove `@python3` from this line once the `python3` branch of
   bioc-common-python gets merged into its `master` branch.

  **Note:** If there is trouble with a particular version of a dependency
   you can update the versions in these files. These versions were stable 
   and working on our systems. 

  **Note:** It may be necessary to log in as Administrator and run the 
  `pip install stomp.py pytz stompy` _without_ any virtual env activated
  

#### Configuration 

1.  Navigate back into the packagebuilder directory. Create a new directory
entitled `spb-properties` with a text file entitled `spb.properties`. Be mindful
of capitalization and punctuation. The `spb.properties` file should contain the
following: 
```
[Sensitive]
svn.user=
svn.pass=
tracker.user=
tracker.pass=
github.token=
```
    The values can be undefined. If you are deploying on a Bioconductor Build
    Node please grab this file from the private repository. 

2. You'll need to modify two configuration files. 

    i. Copy the provided `TEMPLATE.properties` to a unique properties file for
    your system `<host name>.properties`. Update all the values in this
    file as necessary. The `builders` value should match `<host name>`.

    ii. Secondly, change `bioconductor.properties` values. The `environment`
    variable should match  `<host name>` and update the BioC version
    accordingly
    
3. **NOTE:** For Bioconductor Nodes, you may need to create new private/public key information and add the key to known hosts on staging.bioconductor.org (.packagebuilder.prive_key.rsa / .packagebuilder.prive_key.rsa.pub)
  
  **NOTE:** The single package builder utilizes directories shared with the 
  daily builder (biocbuild) mainly the same R. It may be necessary to have 
  an Administrator change permissions of these directories to allow read and 
  execute by pkgbuild 


4. Modify server.py

  As of June 2021, subscripts run through the task schedule do not inherit the
  virtualenv that the original server.py script is run under. To accomodate the
  subscripts change around line 202 in the server.py script that launches the
  builder.py script to explicitly call the python in the virtualenv. So this
  line:

   `shell_cmd = ["python", "-m", "workers.builder", jobfilename, bioc_version]`

   becomes something like:

   `shell_cmd = ["D:\pkgbuild\packagebuilder\env\Scripts\python.exe", "-m", "workers.builder", jobfilename, bioc_version]`

#### Test server
You can test if the server will run by the following:
cd into the `~\pkgbuilder\packagebuilder`
```
.\env\Scripts\activate
killall python
python -m workers.server
```
This is just to test that the server will connect. You will want it to run 
through the task scheduler (see next section)

#### Automate

Set up a task scheduler to automate the launch of the server and clean up scripts. This will serve as a general guideline and will detail the steps used for the last setup. Keep in mind depending on your desired actions and system set up these may differ slightly. 

Log in as an Administrator account. 

Before creating the SPB server task, we need to create the do_nothing_forever
task. This is the same setup used for the biocbuild account but using
pkgbuild. The pkgbuild uses the BBS/utils/do_nothing_forever.py script. See
[biocbuild
setup](https://github.com/Bioconductor/BBS/blob/master/Doc/Prepare-Windows-Server-2019-HOWTO.md#22-add-loggon_biocbuild_at_startup-task-to-task-scheduler)
for Add loggon_biocbuild_at_startup task to Task Scheduler. It should run as
pkgbuild and the log should go into `D:\pkgbuild\log` that we created in the
first step.


Navigate the Serve Manager Dashboard, in the right top there is Tools, select Task Scheduler. Once this opens navigate down task scheduler -> Task Scheduler Library -> BBS.  On the right hand side select `create task`. We will now go through the details of the last setup in each of the tabs for a create task. 

1. General. Name your task. We generally have used spb\_server. Under Security Options, select Change User or Groups. In our case we will be running our tasks as the pkgbuild account. When set correctly this should show \<host name\>\\pkgbuild. This account will need to have `log on as batch job rights`. Make sure the "Run whether user is logged in or not" is selected and Change the "configure for"" to match the system. Our last deployment was `Windows Server 2012 R2` 
2. Triggers. Set the trigger to whatever is appropriate for your task. For the
server task we will set the trigger to `At System Startup` and choose a delay of
30 seconds or 1 minute to have the do_nothing_forever.py start first. 
3. Actions. The following are the entries for the last set up of the spb_server task. Program/Script: `C:\Windows\System32\cmd.exe`.  Additional Arguments: `/C ".\env\Scripts\activate && python -m workers.server >> server.log 2>&1"` Start In: `D:\pkgbuild\packagebuilder`.  Again these may differe depending on your locations and system setup. 
4. Conditions. All that should be selected are the following "Start task only if the computer is on AC power" and "Stop if computer switches to battery power".
5. Settings. All that should be selected are the following: "Allow task to be run on demand" and "If the running task does not end when requested force to stop"

We generally will create another task for spb\_package\_cleanUp. It has many of the same settings except the trigger is set to a daily time and the Action Additional Arguments: `/C ".\env\Scripts\activate && python workers\cleanUpIssues.py"`

If any additional tasks for the spb are added similar steps for the setup can be followed. 

# Adjust spb_history/staging.bioconductor.org

Log into staging.biocondcutor.org as `biocadmin`

1. Update staging.properties to include the new server[s] as a builder

2. Update viewhistory/static/css/2.7/report.css and
viewhistory/templates/base.html 
   **NOTE:** When entering server name, use all lowercase

3. Make sure the following are set in the crontab for `biocadmin@staging.bioconductor.org`:

```
@reboot /home/biocadmin/spb_history/run-archiver.sh
@reboot /home/biocadmin/spb_history/run-django.sh
@reboot /home/biocadmin/spb_history/run-track_build_completion.sh
```

3. Test
If the server is communicating correctly, on
'biocadmin@staging.bioconductor.org` run pinger.py. 

```
cd packagebuilder
. env/bin/activate
python3 pinger.py
```
There should be an entry for the new server provided it is running either 
interactively or automatically. 

# Other
Don't forget if these are replacing other build nodes or updating, go to the old
build nodes and turn off/kill the listeners and to comment out the crontab jobs

# Troubleshoot


A. Occassionally, we have builder ids that have additional naming information
(oaxaca.local, toluca2.bioconductor.org, etc...), to get the information to
display correctly on the build reports ensure the following: 

1. appropriate changes were made: see above Adjust
spb_history/staging.bioconductor.org - to add entries to report.css, etc. 
2. on the builder/server - adjust server.py to truncate name
3. on the builder/server - adjust bioc-common-python/bioconductor/config.py to
truncate name 
4. on the builder/server reinstall property file: see below for updating
property files

B. Also when a node is first being deployed it might have issues connecting to
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

# Updating property files :

1. Pull bioc-common-python and packagebuilder
2. source env/bin/activate
3. killall python3
4. cd ../bioc-common-python
5. pip3 install --upgrade -r PIP-DEPENDENCIES--bioc-common-python.txt
6. python3 setup.py install
7. cd ../packagebuilder
8. pip3 install --upgrade -r PIP-DEPENDENCIES--packagebuilder.txt
9. restart node

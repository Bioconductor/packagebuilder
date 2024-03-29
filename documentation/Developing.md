Developing
==========

This page describes how to configure and run the Single Package Builder locally.

Table of Contents
-----------------

[**Installation**](#installation)  
[**Set up RabbitMQ messaging client**](#rabbitmq)  
[**Set up Python environment**](#python)  
[**Configuration**](#configuration)  
[**Usage**](#usage)
* [Run a local build node](#localnode)
* [Test communications](#communications)
* [Kick off a job](#job)

<a name="installation"></a>
Installation
------------

To run the Single Package Builder (SPB) locally, you will need to clone the following Bioconductor Github repositories:

* packagebuilder  
    ```
    git clone https://github.com/Bioconductor/packagebuilder.git
    ```
* spb\_history  
    ```
    git clone https://github.com/Bioconductor/spb_history.git
    ```
* bioc-common-python  
    ```
    git clone https://github.com/Bioconductor/bioc-common-python.git
    ```
* BBS  
    ```
    git clone https://github.com/Bioconductor/BBS.git
    ```

**Note**: For now (Nov 2019) you need to use the `python3` branch
of `packagebuilder`, `spb\_history`, and `bioc-common-python` (e.g.
`cd packagebuilder; git checkout python3`). This is until the `python3`
branch for these 3 repositories gets merged into the `master` branch.

<a name="rabbitmq"></a>
Set up RabbitMQ messaging client
--------------------------------
To run the SPB locally, you'll need an RabbitMQ instance.  The
simplest way to accomplish that, is using Docker. We'll use [this docker image](https://github.com/resilva87/docker-rabbitmq-stomp).

* Prerequisites  
On Linux, you need Docker [installed](https://docs.docker.com/installation/) and on [Mac](http://docs.docker.com/installation/mac/)
or [Windows](http://docs.docker.com/installation/windows/) you need Docker Toolbox installed and running.

**Note**: You may need sudo before all docker commands

* Get the image
```
docker pull resilva87/docker-rabbitmq-stomp
```

* Start stomp broker
```
docker run -d -e RABBITMQ_NODENAME=my-rabbit --name rabbitmq -p 61613:61613 resilva87/docker-rabbitmq-stomp
```

* Auto-start docker on boot

In production, we want the docker on the rabbitmq.bioconductor.org EC2
instance to start-up on boot. This step is probably not necessary for
a test enviornment.

Get the container ID:
```
sudo docker ps
```

Stop the docker service:
```
sudo docker stop
```

Modify /var/lib/docker/containers/CONTAINER_ID/hostconfig.json such that
`RestartPolicy` is set to "always" and `MaximumRetryCount` is set to "3".
`CONTAINER_ID` is the ID you saw in the `docker ps` command.
```
sudo vim /var/lib/docker/containers/CONTAINER_ID/hostconfig.json
```

Reboot the machine and confirm the docker auto-starts:
```
sudo docker ps
```

<a name="python"></a>
Setting up the Python environment
---------------------------------

To work on the SPB, you should use a virtual environment.  Eventually, a
[virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/) should also
be used in production.

1. Create a virtual environment for your work (this is where you'll install dependencies
  of the SPB).  If `virtualenv` is not installed on your machine,
  [install it](http://virtualenv.readthedocs.org/en/latest/installation.html).  Afterwards,
  create an environment called "env" in the directory above where you cloned packagebuilder, spb_history, BBS, and bioc-common-python:

  ```
  virtualenv env
  ```
  **Note:** Make sure Python3 is used to create the environment. On the Linux
  and Mac builders, you'll need to specify the path to the `python3` command
  with `virtualenv -p /usr/bin/python3 env`.

  This virtual environment is important, as we do not want to pollute the
  global Python package space.  Assume other python services are running
  on this host and require different versions of various modules.
  
  **Note:** SPB last tested with Python 3.7.3

2. Next, activate the environment in **every shell** you'll be working in :
  ```
  source env/bin/activate
  ```
3. You should see your shell change with the environment activated.  Next
  install the required modules.  Since the virtualenv is active, the packages
  are kept in isolation.  For example, the
  [stomp.py](https://github.com/jasonrbriggs/stomp.py) module will be installed
  at `./env/lib/python3.5/site-packages/stomp`. 

    Install the dependencies :

    ```pip3 install stomp.py==4.1.9 pytz==2015.7 django==3.0.3```

    **Note:** Use `pip` instead of `pip3` on the Windows builder.


4. Install additional dependencies:

    Install the necessary PIP-DEPENDENCIES and global variable environment.
    ```
    cd packagebuilder
    pip3 install --upgrade -r ./PIP-DEPENDENCIES--packagebuilder.txt

    cd ../spb_history
    pip3 install --upgrade -r ./PIP-DEPENDENCIES--spb_history.txt

    cd ../bioc-common-python
    pip3 install --upgrade -r ./PIP-DEPENDENCIES--bioc-common-python.txt
    python3 setup.py install
    
    cd packagebuilder
    pip3 install --upgrade -r ./PIP-DEPENDENCIES--packagebuilder.txt
    ```

   **Note:** Use `pip` and `python` instead of `pip3` and `python3` on the
   Windows builder.

   **Note**: For now (Nov 2019), the first line in
   `packagebuilder/PIP-DEPENDENCIES--packagebuilder.txt` and
   `spb_history/PIP-DEPENDENCIES--spb_history.txt` has been modified
   to install the `python3` branch of bioc-common-python from GitHub.
   Remove `@python3` from these 2 lines once the `python3` branch of
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
   packagebuilder  dependencies. If this is the case go back and redo the
   bioc-common-python commands above.

    **Note:** We upgraded to python3 June 2020.  At that time a new PIP dependency
   file was generate.  It can't hurt to also check the dependency versions vs
   newlyGeneratedPIP3dependencies.txt in spb_history.

<a name="configuration"></a>
Configuration
-------------

1. In the packagebuilder and spb\_history directories:

    Create a new directory entitled `spb-properties` with a text file entitled `spb.properties`. Be mindful of capitalization and punctuation. The `spb.properties` file should contain the following:
```
[Sensitive]
svn.user=
svn.pass=
tracker.user=
tracker.pass=
github.token=
```
    The values can be undefined.

2. You'll need to modify two configuration files. These files should be updated and identical in both packagebuilder and spb\_history directories.

    i. Copy the provided `TEMPLATE.properties` to a unique properties file for your system `<your machine name>.properties`. Update all the values in this file as necessary. The `builders` value should match `<your machine name>`.

    ii. Secondly, change `bioconductor.properties` values. The `environment` variable should match  `<your machine name>`

3. In the BBS directory: 

   i. Create a directory for `<your machine name>` in `BBS/nodes/`. A file
   `local-settings.sh` should be created. If you have access to the other
   existing nodes, I would suggest just coping an existing file over. 

   ii. Update `BBS/nodes/nodespecs.py` to include an entry for `<your machine name>`.


<a name="usage"></a>
Usage

<a name="localnode"></a>
#### Run a local build node

There are several pieces to the SPB. To see each piece run interactively, open new shells for each of the following commands below **Be sure to source the virtual environment created above in EVERY shell**


1. packagebuilder: Start the main server

    The main builder server is in the packagebuilder directory and will store it's data in the `workers` subdirectory.  To start the builder service, run the following in the packagebuilder top directory:
    ```
    python3 -m workers.server
    ```

    **Note:** Use `python` instead of `python3` on the Windows builder.

    You should see some output similar to the follow which indicates the server is up and running and your rabbitmq was initialized properly:
    ```
    INFO: 09/13/2016 10:37:33 AM server.py:238 - Connection established using new communication module
    INFO: 09/13/2016 10:37:33 AM server.py:241 - Subscribed to destination /topic/buildjobs
    INFO: 09/13/2016 10:37:33 AM server.py:244 - Subscribed to  /topic/keepalive
    INFO: 09/13/2016 10:37:33 AM server.py:249 - Waiting for messages; CTRL-C to exit.
    ```

2. (optional) spb_history: archiver

    The archiver shows logging/progress messages while the package is being built and checked. This is in the spb\_history directory. To start the archiver, run the following in the spb\_history top directory:
    ```
    python3 -m archiver
    ```

    **Note:** Use `python` instead of `python3` on the Windows builder.

3. (optional) spb_history: track build completion

    The track build completion shows logging/progress messages while the package is being built and checked as well as when the process finishes and the completed output is available for view on the web page. This is in the spb\_history directory. To start the track\_build\_completion, run the following in the spb\_history top directory:
    ```
    python3 -m track_build_completion
    ```

    **Note:** Use `python` instead of `python3` on the Windows builder.

4. (optional) spb_history: Django web app - this allows a local web view of build report

    The Django web application allows for a local web view of the build report. Once the report is generated you can open the following `http://0.0.0.0:8000/` to view in web browser. To start Django, run the following in the spb\_history top directory:
    ```
    python3 -m manage runserver 0.0.0.0:8000
    ```

    **Note:** Use `python` instead of `python3` on the Windows builder.
    
<a name="communications"></a>
#### Test communications

To test the connections, run the command below in the spb\_history directory.  Be sure you're in a terminal with the appropriate virtualenv activated.

```
python3 pinger.py
```

**Note:** Use `python` instead of `python3` on the Windows builder.

You should see responses from any of the activated pieces above.
An example with only the packagebuilder main server activated with no optional pieces:

```
(env) lori@lori-HP-ZBook-15-G2:~/a/singlePackageBuilder/spb_history$ python pinger.py
INFO: 09/26/2016 01:08:53 PM Attempting to connect using new communication module
INFO: 09/26/2016 01:08:53 PM Connection established using new communication module
INFO: 09/26/2016 01:08:53 PM {"host": "lori-HP-ZBook-15-G2", "script": "server.py"}
```

<a name="job"></a>
#### Kick off a job
To kick off a job, run the command below in the spb\_history directory.  Be sure you're in a terminal with the appropriate virtualenv activated.

```
# new way assumes on git.bioconductor.org
# this will fail because on on git.bioconductor
python3 rerun_build_git.py 51 https://git.bioconductor.org/packages/spbtest3 true
# this should work
python3 rerun_build_git.py 51 https://github.com/Bioconductor/spbtest3 true

# old way
python3 rerun_build.py 51 https://github.com/Bioconductor/spbtest3
```

**Note:** Use `python` instead of `python3` on the Windows builder.

The output directory and log files for the build are created in the `spb_home` directory specified in the `<your machine name>.properties` file in subdirectory: jobs/51/

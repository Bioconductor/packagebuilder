Developing
==========

#### Running the SPB stack locally
To run the Single Package Builder locally, you'll need an ActiveMQ instance.  The
simplest way to accomplish that, is using Docker. We'll use [this docker image](https://github.com/disaster37/activemq).  

```
# Get the image
docker pull webcenter/activemq:5.12.0

# Start ActiveMQ
docker run --name='activemq' -d -p 8161:8161 -p 61616:61616 -p 61613:61613 \
   -e 'ACTIVEMQ_REMOVE_DEFAULT_ACCOUNT=false' webcenter/activemq:5.12.0
```
If you need to debug ActiveMQ, open a shell.  You may want to inspect the content
of `/var/log/activemq` and `/data/activemq`: 
```
# Debugging ActiveMQ
developer@laptop:~/$ docker exec -it activemq /bin/bash
root@c604e22226f6:/# cd /var/log/activemq/
root@c604e22226f6:/var/log/activemq# ls -l
total 12
-rw-r--r-- 1 activemq activemq 3537 Dec  7 03:54 activemq.log
-rw-r--r-- 1 activemq activemq    0 Dec  7 03:54 audit.log
-rw-r--r-- 1 activemq activemq 4518 Dec  7 03:54 wrapper.log
root@c604e22226f6:/var/log/activemq# cd /data/activemq/
root@c604e22226f6:/data/activemq# ls -l
total 4
drwxr-xr-x 2 activemq activemq 4096 Dec  7 03:54 kahadb

```
#### Setting up the Python environment

To work on the SPB, you should use a virtual environment.  Eventually, a
[virtualenv] (http://docs.python-guide.org/en/latest/dev/virtualenvs/) should also
be used in production.

1. Create a virtual environment for your work (this is where you'll install dependencies
  of the SPB).  If `virtualenv` is not installed on your machine,
  [install it](http://virtualenv.readthedocs.org/en/latest/installation.html).  Afterwards,
  create an environment called "env":
  ```
  virtualenv env
  ```
  This virtual environment is important, as we do not want to pollute the
  global Python package space.  Assume other python services are running
  on this host and require different versions of various modules.

2. Next, activate the environment in **every shell** you'll be working in :
  ```
  source env/bin/activate
  ```
3. You should see your shell change with the environment activated.  Next
  install the required modules.  Since the virtualenv is active, the packages
  are kept in isolation.  For example, the
  [stomp.py](https://github.com/jasonrbriggs/stomp.py) module will be installed
  at `./env/lib/python2.7/site-packages/stomp`.  There are two **important**
  notes about the next command (1), yes right now, we need both `stomp.py`
  and `stompy`.  We'll migrate off `stompy` soon.  (2) It's very important
  that you install **version 1.8.4** of Django, as newer versions have caused
  problems.

  Install the dependencies :

  ```
  pip install stomp.py pytz stompy django==1.8.4
  ```

#### Run a local build node
The builder service will store it's data in the `work` directory.  To start the
builder service, run the following :
  ```
  python -m workers/server >> server.log 2>&1 &
  ```
  You should see some output by viewing `server.log`:

  ```
  nohup: ignoring input
  [2015-12-01 12:05:39.565315] Attempting to connect to stomp broker
'broker.bioconductor.org:61613'
  [2015-12-01 12:05:39.624604] on_connecting broker.bioconductor.org 61613
  [2015-12-01 12:05:39.624690] on_send STOMP {'accept-version': '1.1'}
  [2015-12-01 12:05:39.624776] Connected to stomp broker 'broker.bioconductor.org:61613'
  [2015-12-01 12:05:39.624893] on_send SUBSCRIBE {'ack': 'client', 'destination':
'/topic/buildjobs', 'id': 'eae21baf7e5042d292f3046a28334b7d'}
  [2015-12-01 12:05:39.624924] Subscribed to channel /topic/buildjobs
  [2015-12-01 12:05:39.624977]  [*] Waiting for messages. To exit press CTRL+C
  [2015-12-01 12:05:39.664368] on_connected {'session':
'ID:broker-46292-1448469945488-2:60', 'version': '1.1', 'server': 'ActiveMQ/5.6.0',
'heart-beat': '0,0'}

  ```

#### Running the Django web app
  To run Django (`archiver.py`):
  ```
  python -m spb_history/archiver > archiver.log 2>&1 &
  ```

#### Kick off a job
To kick off a job, run the command below.  Be sure you're in a terminal with the
appropriate virtualenv activated.
```
python -m spb_history/rerun_build 1343 \
  https://tracker.bioconductor.org/file6714/spbtest_0.99.1.tar.gz
```

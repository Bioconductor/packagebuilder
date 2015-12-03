Developing
==========

#### Running a test controller node locally
_TODO: Determine feasability and document me._

You'll need an ActiveMQ instance.  To accomplish that, we'll use [this
docker image](https://github.com/disaster37/activemq).  

```
# Get the image
docker pull webcenter/activemq:5.12.0

# Start ActiveMQ
docker run --name='activemq' -d -p 8161:8161 -p 61616:61616 -p 61613:61613 \
-v /data/activemq:/data/activemq -v /var/log/activemq:/var/log/activemq \
webcenter/activemq:5.12.0

```
#### Running a test build node locally

Developers working on this system should use the following workflow :

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

2. Next, activate the environment :
```
source env/bin/activate
```
3. You should see your shell change with the environment activated.  Next
install the required module.  For example, the
[stomp.py](https://github.com/jasonrbriggs/stomp.py) module will be installed
using the virtual environment.  The result is the module installed at
`./env/lib/python2.7/site-packages/stomp` :

  ```
  # YES, right now, we need both stomp.py and stompy.  We'll migrate off stompy soon.
  pip install stomp.py pytz stompy
  ```

4. Next, you'll run the builder service.  Note that the work this service
does will be stored in `work`, as defined by the variable `PACKAGEBUILDER_HOME` :
```
export PACKAGEBUILDER_HOME="work" && nohup python workers/server.py >> server.log 2>&1 &
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

Developing
==========

#### Running a test controller node locally
_TODO: Determine feasability and document me._

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
using the virtual environment.  The result is the module installed at `./env/lib/python2.7/site-packages/stomp` :

  ```
  pip install stomp.py
  ```

4. Next, you'll run the builder service.  Note that the work this service
does will be stored in `work`, as defined by the variable `PACKAGEBUILDER_HOME` :
```
export PACKAGEBUILDER_HOME="work" && nohup python workers/server.py >> server.log 2>&1 &
```

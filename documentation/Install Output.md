The output of installing Python modules:

```
(env)blong@santiago:~/Desktop/packagebuilder$ pip install stomp.py pytz stompy django==1.8.4
Downloading/unpacking stomp.py
  Downloading stomp.py-4.1.8.tar.gz (40kB): 40kB downloaded
  Running setup.py (path:/home/blong/Desktop/packagebuilder/env/build/stomp.py/setup.py) egg_info for package stomp.py

Downloading/unpacking pytz
  Downloading pytz-2015.7-py2.py3-none-any.whl (476kB): 476kB downloaded
Downloading/unpacking stompy
  Downloading stompy-0.2.9.tar.gz
  Running setup.py (path:/home/blong/Desktop/packagebuilder/env/build/stompy/setup.py) egg_info for package stompy

Downloading/unpacking django==1.8.4
  Downloading Django-1.8.4-py2.py3-none-any.whl (6.2MB): 6.2MB downloaded
Installing collected packages: stomp.py, pytz, stompy, django
  Running setup.py install for stomp.py
    changing mode of build/scripts-2.7/stomp from 664 to 775

    changing mode of /home/blong/Desktop/packagebuilder/env/bin/stomp to 775
  Running setup.py install for stompy

Successfully installed stomp.py pytz stompy django
Cleaning up...
```

Looking at files created from the ActiveMQ docker container:
```
# Data files
(env)blong@santiago:~/Desktop/packagebuilder$ ls -la /data/activemq/*
total 52
drwxr-xr-x 2 999 1000     4096 Dec  3 21:59 .
drwxr-xr-x 3 999 1000     4096 Dec  3 21:59 ..
-rw-r--r-- 1 999 1000 33554432 Dec  3 22:02 db-1.log
-rw-r--r-- 1 999 1000    12288 Dec  3 22:02 db.data
-rw-r--r-- 1 999 1000    12304 Dec  3 22:02 db.redo
-rw-r--r-- 1 999 1000        8 Dec  3 21:59 lock

# Log files
(env)blong@santiago:~/Desktop/packagebuilder$ ls -la /var/log/activemq/*
-rw-r--r-- 1 999 1000 4909 Dec  3 21:59 /var/log/activemq/activemq.log
-rw-r--r-- 1 999 1000    0 Dec  3 21:59 /var/log/activemq/audit.log
-rw-r--r-- 1 999 1000 5728 Dec  3 21:59 /var/log/activemq/wrapper.log
```

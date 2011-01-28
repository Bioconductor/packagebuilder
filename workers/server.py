#!/usr/bin/env python


## Assume this script is started by a shell script which has read 
## BBS variables and also changed to the correct directory.

import pika
import sys
import json
import time
import tempfile
import os
import subprocess

BBS_home = os.environ['BBS_HOME']
sys.path.append(BBS_home)

import BBScorevars

connection = pika.AsyncoreConnection(pika.ConnectionParameters(
        host='merlot2.fhcrc.org'))
channel = connection.channel()



from_web_exchange = channel.exchange_declare(exchange="from_web_exchange",type="fanout")
from_worker_exchange = channel.exchange_declare(exchange="from_worker_exchange", type='fanout')

from_web_queue = channel.queue_declare(exclusive=True)
from_web_queue_name = from_web_queue.queue

channel.queue_bind(exchange='from_web_exchange', queue=from_web_queue_name)

print ' [*] Waiting for messages. To exit press CTRL+C'
sys.stdout.flush()

builder_id = os.getenv("BBS_NODE")

def callback(ch, method, properties, body):
    print " [x] Received %r" % (body,)
    received_obj = json.loads(body)
    if('job_id' in received_obj.keys()): # ignore malformed messages
        job_id = received_obj['job_id']
        job_dir = os.path.join("jobs", job_id)
        if not os.path.exists(job_dir):
            os.mkdir(job_dir)
        
        jobfilename = os.path.join(job_dir, "manifest.json")
        
        jobfile = open(jobfilename, "w")
        jobfile.write(body)
        jobfile.close
        print "Wrote job info to %s." % jobfilename
        
        builder_log = open(os.path.join(job_dir, "builder.log"), "w")
        pid = subprocess.Popen([os.getenv("BBS_PYTHON_CMD"), "builder.py", jobfilename],
            stdout=builder_log, stderr=subprocess.STDOUT).pid # todo - somehow close builder_log filehandle if possible
        msg_obj = {}
        msg_obj['originating_host'] = received_obj['originating_host']
        msg_obj['builder_id'] = builder_id
        msg_obj['body'] = "Got build request..."
        msg_obj['first_message'] = True
        json_str = json.dumps(msg_obj)
        channel.basic_publish(exchange='from_worker_exchange',
                              routing_key="key.frombuilders",
                              body= json_str)

channel.basic_consume(callback,
                      queue=from_web_queue.queue,
                      no_ack=True)

pika.asyncore_loop()


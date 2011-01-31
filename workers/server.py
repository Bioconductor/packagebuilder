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
import platform

#BBS_home = os.environ['BBS_HOME']
#sys.path.append(BBS_home)

#import BBScorevars

connection = pika.AsyncoreConnection(pika.ConnectionParameters(
        host='merlot2.fhcrc.org'))
channel = connection.channel()

hostname = platform.node()
shell_ext = None
if (platform.system() == "Darwin" or platform.system() == "Linux"):
    shell_ext = ".sh"
else:
    shell_ext = ".bat"

r_bioc_map = {"2.12": "2.7", "2.8": "2.13", "2.9": "2.14", "2.10": "2.15"} # need a better way to determine bioc version

from_web_exchange = channel.exchange_declare(exchange="from_web_exchange",type="fanout")
from_worker_exchange = channel.exchange_declare(exchange="from_worker_exchange", type='fanout')

from_web_queue = channel.queue_declare(exclusive=True)
from_web_queue_name = from_web_queue.queue

channel.queue_bind(exchange='from_web_exchange', queue=from_web_queue_name)

print ' [*] Waiting for messages. To exit press CTRL+C'
sys.stdout.flush()

builder_id = os.getenv("BBS_NODE")

def callback(ch, method, properties, body):
    global r_bioc_map
    global shell_ext
    print " [x] Received %r" % (body,)
    received_obj = json.loads(body)
    if('job_id' in received_obj.keys()): # ignore malformed messages
        job_id = received_obj['job_id']
        r_version = received_obj['r_version']
        bioc_version = r_bioc_map[r_version]
        job_dir = os.path.join("jobs", job_id)
        if not os.path.exists(job_dir):
            os.mkdir(job_dir)
        
        jobfilename = os.path.join(job_dir, "manifest.json")
        
        jobfile = open(jobfilename, "w")
        jobfile.write(body)
        jobfile.close
        print "Wrote job info to %s." % jobfilename
        
        shell_cmd = "%s%s" % (hostname, shell_ext)
        print "shell_cmd = %s" % shell_cmd
        builder_log = open(os.path.join(job_dir, "builder.log"), "w")
        pid = subprocess.Popen([shell_cmd,jobfilename, bioc_version,],
            stdout=builder_log, stderr=subprocess.STDOUT).pid # todo - somehow close builder_log filehandle if possible
        msg_obj = {}
        msg_obj['originating_host'] = received_obj['originating_host']
        msg_obj['client_id'] = received_obj['client_id']
        msg_obj['builder_id'] = builder_id
        msg_obj['body'] = "Got build request..."
        msg_obj['first_message'] = True
        json_str = json.dumps(msg_obj)
        channel.basic_publish(exchange='from_worker_exchange',
                              routing_key="key.frombuilders",
                              body= json_str)
        time.sleep(0.5)

channel.basic_consume(callback,
                      queue=from_web_queue.queue,
                      no_ack=True)

pika.asyncore_loop()


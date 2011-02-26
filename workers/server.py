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

packagebuilder_home = os.environ["PACKAGEBUILDER_HOME"]
connection = pika.AsyncoreConnection(pika.ConnectionParameters(
        host='merlot2.fhcrc.org'))
channel = connection.channel()

builder_id = platform.node().replace(".fhcrc.org","")


shell_ext = None
if (platform.system() == "Darwin" or platform.system() == "Linux"):
    shell_ext = ".sh"
else:
    shell_ext = ".bat"

r_bioc_map = {"2.12": "2.7", "2.13": "2.8", "2.14": "2.9", "2.15": "2.10"} # need a better way to determine bioc version

from_web_exchange = channel.exchange_declare(exchange="from_web_exchange",type="fanout")
from_worker_exchange = channel.exchange_declare(exchange="from_worker_exchange", type='fanout')
from_worker_exchange_dev = channel.exchange_declare(exchange="from_worker_exchange_dev", type='fanout')

from_web_queue = channel.queue_declare(exclusive=True)
from_web_queue_name = from_web_queue.queue

channel.queue_bind(exchange='from_web_exchange', queue=from_web_queue_name)

print ' [*] Waiting for messages. To exit press CTRL+C'
sys.stdout.flush()


def callback(ch, method, properties, body):
    global r_bioc_map
    global shell_ext
    global packagebuilder_home
    print " [x] Received %r" % (body,)
    received_obj = json.loads(body)
    if('job_id' in received_obj.keys()): # ignore malformed messages
        job_id = received_obj['job_id']
        r_version = received_obj['r_version']
        bioc_version = r_bioc_map[r_version]
        jobs_dir = os.path.join(packagebuilder_home, "jobs")
        if not os.path.exists(jobs_dir):
            os.mkdir(jobs_dir)
        job_dir = os.path.join(jobs_dir, job_id)
        if not os.path.exists(job_dir):
            os.mkdir(job_dir)
        
        jobfilename = os.path.join(packagebuilder_home, job_dir, "manifest.json")
        
        jobfile = open(jobfilename, "w")
        jobfile.write(body)
        jobfile.close
        print "Wrote job info to %s." % jobfilename
        shell_cmd = os.path.join(packagebuilder_home, "%s%s" % (builder_id, shell_ext))
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
        msg_obj['job_id'] = job_id
        json_str = json.dumps(msg_obj)
        xname = 'from_worker_exchange'
        if (received_obj['dev'] == True):
            xname += "_dev"
        print "xname = %s" % xname
        channel.basic_publish(exchange=xname,
                              routing_key="key.frombuilders",
                              body= json_str)

channel.basic_consume(callback,
                      queue=from_web_queue.queue,
                      no_ack=True)

pika.asyncore_loop()


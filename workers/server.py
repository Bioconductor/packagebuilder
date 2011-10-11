#!/usr/bin/env python



import sys
import json
import time
import tempfile
import os
import subprocess
import platform
from stompy import Stomp


try:
    stomp = Stomp("merlot2.fhcrc.org", 61613)
    # optional connect keyword args "username" and "password" like so:
    # stomp.connect(username="user", password="pass")
    stomp.connect()
except:
    print("Cannot connect")
    raise

stomp.subscribe({'destination': "/topic/buildjobs", 'ack': 'client'})




packagebuilder_home = os.environ["PACKAGEBUILDER_HOME"]

builder_id = platform.node().replace(".fhcrc.org","")
## Temporary hack
if (builder_id.lower().startswith("dhcp") or \
  builder_id == 'PHS-ITs-Lion-Test-MacBook.local'):
    if ("PACKAGEBUILDER_HOST" in os.environ.keys()):
        builder_id = os.environ["PACKAGEBUILDER_HOST"]
    else:
        print "who ami i?"
        raise

shell_ext = None
if (platform.system() == "Darwin" or platform.system() == "Linux"):
    shell_ext = ".sh"
else:
    shell_ext = ".bat"

r_bioc_map = {"2.12": "2.7", "2.13": "2.8", "2.14": "2.9", "2.15": "2.10"} # need a better way to determine bioc version


print ' [*] Waiting for messages. To exit press CTRL+C'
sys.stdout.flush()


def callback(body):
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
        msg_obj['builder_id'] = builder_id
        msg_obj['body'] = "Got build request..."
        msg_obj['first_message'] = True
        msg_obj['job_id'] = job_id
        json_str = json.dumps(msg_obj)
        this_frame = stomp.send({'destination': "/queue/builderevents",
          'body': json_str,
          'persistent': 'true'})
        print("Receipt: %s" % this_frame.headers.get('receipt-id'))

while True:
    try:
        frame = stomp.receive_frame()
        stomp.ack(frame) # do this?
        #print(frame.headers.get('message-id'))
        #print(frame.body)
        callback(frame.body)
    except KeyboardInterrupt:
        stomp.disconnect()
        break


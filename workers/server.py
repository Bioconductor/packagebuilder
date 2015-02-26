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

os.environ['TRACKER_LOGIN'] = 'pkgbuild'
os.environ['TRACKER_PASSWORD'] = 'buildpkg'


packagebuilder_home = os.environ["PACKAGEBUILDER_HOME"]

builder_id = platform.node().lower().replace(".fhcrc.org","")
builder_id = builder_id.replace(".local", "")

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

# need a better way to determine bioc version
r_bioc_map = {"2.12": "2.7", "2.13": "2.8", "2.14": "2.9", "2.15": "2.10", "3.1": "3.0", "3.2": "3.1"} 

bioc_r_map = {"2.10": "2.15", "2.11": "2.15", "2.12": "2.16",
"2.13": "2.16", "2.14": "3.1", "3.0": "3.1", "3.1": "3.2"}


print ' [*] Waiting for messages. To exit press CTRL+C'
sys.stdout.flush()


def callback(body):
    global r_bioc_map
    global shell_ext
    global packagebuilder_home
    print " [x] Received %r" % (body,)
    try:
        received_obj = json.loads(body)
    except ValueError:
        print("Caught Value error, not a valid JSON object?")
        sys.stdout.flush()
        return()
    if('job_id' in received_obj.keys()): # ignore malformed messages
        job_id = received_obj['job_id']
        bioc_version = received_obj['bioc_version']
        r_version = bioc_r_map[bioc_version]
        jobs_dir = os.path.join(packagebuilder_home, "jobs")
        if not os.path.exists(jobs_dir):
            os.mkdir(jobs_dir)
        job_dir = os.path.join(jobs_dir, job_id)
        if not os.path.exists(job_dir):
            os.mkdir(job_dir)
        r_libs_dir = os.path.join(job_dir, "R-libs")
        if (not os.path.exists(r_libs_dir)):
            os.mkdir(r_libs_dir)
        
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
        msg_obj['client_id'] = received_obj['client_id']
        msg_obj['bioc_version'] = bioc_version
        json_str = json.dumps(msg_obj)
        this_frame = stomp.send({'destination': "/topic/builderevents",
          'body': json_str,
          'persistent': 'true'})
        print("Receipt: %s" % this_frame.headers.get('receipt-id'))
        sys.stdout.flush()
    else:
        print("Invalid JSON (missing job_id key)")
        sys.stdout.flush()

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


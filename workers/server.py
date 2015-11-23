#!/usr/bin/env python

import time
import datetime
import sys
import json
import os
import subprocess
import platform
import uuid

# Stomp client imports
import stomp
import stomp.exception as exception
import stomp.utils as utils


builder_id = platform.node().lower().replace(".fhcrc.org","")
builder_id = builder_id.replace(".local", "")

builder_id = platform.node().lower().replace(".fhcrc.org","")
builder_id = builder_id.replace(".local", "")

# TODO: Replace with a logging framework
def logMsg(msg):
    print "[%s] %s" % (datetime.datetime.now(), msg)


# TODO: Name the callback for it's functionality, not usage.  This seems like it's as
#       useful as 'myFunction' or 'myMethod'.  Why not describe capability provided ?
class MyListener(stomp.ConnectionListener):
    def on_connecting(self, host_and_port):
        logMsg('on_connecting %s %s' % host_and_port)

    def on_connected(self, headers, body):
        logMsg('on_connected %s %s' % (headers, body))

    def on_disconnected(self):
        logMsg('on_disconnected')

    def on_heartbeat_timeout(self):
        logMsg('on_heartbeat_timeout')

    def on_before_message(self, headers, body):
        logMsg('on_before_message %s %s' % (headers, body))
        return headers, body

    def on_receipt(self, headers, body):
        logMsg('on_receipt %s %s' % (headers, body))

    def on_send(self, frame):
        logMsg('on_send %s %s %s' % (frame.cmd, frame.headers, frame.body))

    def on_heartbeat(self):
        logMsg('on_heartbeat')

    def on_error(self, headers, message):
        logMsg('received an error "%s"' % message)
    def on_message(self, headers, body):
        # FIXME : The maps defined above seem to be an anti-pattern.  Also, it's very odd
        #           IMHO that we're invoking 'global' here.  The variable is in scope and
        #           we're not attempting any read or assignment.
        global r_bioc_map
        global shell_ext
        global packagebuilder_home
        logMsg(" [x] Received %r" % (body,))
        try:
            received_obj = json.loads(body)
        except ValueError:
            logMsg("Caught Value error, not a valid JSON object?")
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
            logMsg("Wrote job info to %s." % jobfilename)
            shell_cmd = os.path.join(packagebuilder_home, "%s%s" % (builder_id, shell_ext))
            logMsg("shell_cmd = %s" % shell_cmd)
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
            this_frame = stomp.send(destination="/topic/builderevents", body=json_str, headers={"persistent": "true"})
            logMsg("Receipt: %s" % this_frame.headers.get('receipt-id'))
            sys.stdout.flush()
        else:
            logMsg("Invalid JSON (missing job_id key)")
            sys.stdout.flush()

        # Acknowledge that the message has been processed
        self.message_received = True

try:
    stompBroker="broker.bioconductor.org"
    stompBrokerPort=61613
    logMsg("Attempting to connect to stomp broker '%s:%s'" % (stompBroker, stompBrokerPort))

    stomp = stomp.Connection([(stompBroker, stompBrokerPort)])
    stomp.set_listener('', MyListener())
    stomp.start()
    # optional connect keyword args "username" and "password" like so:
    # stomp.connect(username="user", password="pass")
    stomp.connect() # clientid=uuid.uuid4().hex)
    logMsg("Connected to stomp broker '%s:%s'" % (stompBroker, stompBrokerPort))
    chan = '/topic/buildjobs'
    stomp.subscribe(destination=chan, id=uuid.uuid4().hex, ack='client')
    logMsg("Subscribed to channel %s" % chan)
except Exception as e:
    logMsg("Error connecting to ActiveMQ.  Error: %s" % e)
    raise

os.environ['TRACKER_LOGIN'] = 'pkgbuild'
os.environ['TRACKER_PASSWORD'] = 'buildpkg'

packagebuilder_home = os.environ["PACKAGEBUILDER_HOME"]

builder_id = platform.node().lower().replace(".fhcrc.org","")
if sys.platform == "win32":
    # bad hardcoding! I don't know why this is necessary:
    if builder_id in ["windows1", "windows2"]:
        os.environ["USERDNSDOMAIN"] = "bioconductor.org"
    if "USERDNSDOMAIN" in os.environ:
        builder_id += "." + os.environ['USERDNSDOMAIN'].lower()
builder_id = builder_id.replace(".local", "")

## Temporary hack
if (builder_id.lower().startswith("dhcp") or \
  builder_id == 'PHS-ITs-Lion-Test-MacBook.local'):
    if ("PACKAGEBUILDER_HOST" in os.environ.keys()):
        builder_id = os.environ["PACKAGEBUILDER_HOST"]
    else:
        logMsg("who ami i?")
        raise

shell_ext = None
if (platform.system() == "Darwin" or platform.system() == "Linux"):
    shell_ext = ".sh"
else:
    shell_ext = ".bat"

# FIXME Get this information dynamically.  Consider bioc-cm or
#       master.bioconductor.org/config.yaml
#
# FIXME: Name the next two variables more clearly.  Their names seeem cryptic.
r_bioc_map = {"2.12": "2.7", "2.13": "2.8", "2.14": "2.9",
  "2.15": "2.10", "3.1": "3.0", "3.2": "3.2", "3.3": "3.3"}

bioc_r_map = {"2.10": "2.15", "2.11": "2.15", "2.12": "2.16",
"2.13": "2.16", "2.14": "3.1", "3.0": "3.1",
"3.1": "3.2", "3.2": "3.2", "3.3": "3.3"}


logMsg(' [*] Waiting for messages. To exit press CTRL+C')
sys.stdout.flush()

while True:
    logMsg("Waiting to do work ... ")
    time.sleep(15)

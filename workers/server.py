#!/usr/bin/env python

import time
import sys
import json
import os
import subprocess
import platform
import uuid
import stomp
import logging
# Modules created by Bioconductor
from bioconductor.config import ENVIR
from bioconductor.config import TOPICS
from bioconductor.config import BUILDER_ID
from bioconductor.communication import getNewStompConnection


logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.DEBUG)


# FIXME Get this information dynamically.  Consider bioc-cm or
#       master.bioconductor.org/config.yaml

if sys.platform == "win32":
    # bad hardcoding! I don't know why this is necessary:
    if BUILDER_ID in ["windows1", "windows2"]:
        os.environ["USERDNSDOMAIN"] = "bioconductor.org"
    if "USERDNSDOMAIN" in os.environ:
        BUILDER_ID += "." + os.environ['USERDNSDOMAIN'].lower()
BUILDER_ID = BUILDER_ID.replace(".local", "")
## Temporary hack
if (BUILDER_ID.lower().startswith("dhcp") or \
  BUILDER_ID == 'PHS-ITs-Lion-Test-MacBook.local'):
    if ("PACKAGEBUILDER_HOST" in os.environ.keys()):
        BUILDER_ID = os.environ["PACKAGEBUILDER_HOST"]
    else:
        logging.error("main() Cannot determine who I am")
        raise
shell_ext = ".bat"
if (platform.system() == "Darwin" or platform.system() == "Linux"):
    shell_ext = ".sh"

# TODO: Name the callback for it's functionality, not usage.  This
# seems like it's as useful as 'myFunction' or 'myMethod'.  Why not
# describe capability provided ?
class MyListener(stomp.ConnectionListener):
    def on_connecting(self, host_and_port):
        logging.debug('on_connecting() %s %s.' % host_and_port)

    def on_connected(self, headers, body):
        logging.debug('on_connected() %s %s.' % (headers, body))

    def on_disconnected(self):
        logging.debug('on_disconnected().')

    def on_heartbeat_timeout(self):
        logging.debug('on_heartbeat_timeout().')

    def on_before_message(self, headers, body):
        logging.debug('on_before_message() %s %s.' % (headers, body))
        return headers, body

    def on_receipt(self, headers, body):
        logging.debug('on_receipt() %s %s.' % (headers, body))

    def on_send(self, frame):
        logging.debug('on_send() %s %s %s.' %
                      (frame.cmd, frame.headers, frame.body))

    def on_heartbeat(self):
        logging.debug('on_heartbeat().')

    def on_error(self, headers, message):
        logging.debug('on_error(): "%s".' % message)

    def on_message(self, headers, body):
        # FIXME : The maps defined above seem to be an anti-pattern.
        # Also, it's very odd IMHO that we're invoking 'global' here.
        # The variable is in scope and we're not attempting any read
        # or assignment.
        global shell_ext

        logging.info("Message received")
        try:
            received_obj = json.loads(body)
        except ValueError:
            logging.error("on_message() ValueError: invalid JSON?")
            return()
        if ('job_id' in received_obj.keys()): # ignore malformed messages
            job_id = received_obj['job_id']
            bioc_version = received_obj['bioc_version']

            job_dir = os.path.join(ENVIR['packagebuilder_home'], "jobs")
            if not os.path.exists(job_dir):
                os.mkdir(job_dir)
            job_dir = os.path.join(job_dir, job_id)
            if not os.path.exists(job_dir):
                os.mkdir(job_dir)
            r_libs_dir = os.path.join(job_dir, "R-libs")
            if not os.path.exists(r_libs_dir):
                os.mkdir(r_libs_dir)
            jobfilename = os.path.join(ENVIR['packagebuilder_home'], job_dir,
                                       "manifest.json")

            jobfile = open(jobfilename, "w")
            jobfile.write(body)
            jobfile.close
            logging.debug("on_message() job_dir = %s." % job_dir)
            
            logging.info("\n\n\n************************************")
            logging.info("Replace this bit...")

            logging.info("BUILDER_ID: '%s'", BUILDER_ID)
            logging.info("shell_ext: '%s'", shell_ext)
            logging.info("job_dir: '%s'", job_dir)
            
            # FIXME: Host specific scripts are bad!
            use_host_specific_script = False
            if use_host_specific_script:
                host_specific_script = os.path.join(ENVIR['packagebuilder_home'], "%s%s" % (BUILDER_ID, shell_ext))
                if os.path.isfile(host_specific_script) and os.access(host_specific_script, os.R_OK):
                    logging.info("The SPB will depend on host-specific script '%s'", host_specific_script)
                else :
                    logging.error("The SPB relies on host-specific script '%s',"
                        "which is inaccessible.  Can not continue!", host_specific_script)
                    raise
                shell_cmd = [host_specific_script, jobfilename, bioc_version]
            else:
                shell_cmd = ["python", "-m", "workers.builder", jobfilename, bioc_version]

            builder_log = open(os.path.join(job_dir, "builder.log"), "w")
                                     
            logging.info("Attempting to run commands from directory: '%s'", os.getcwd())
            logging.info("shell_cmd: '%s'", shell_cmd)
            logging.info("jobfilename: '%s'", jobfilename)
            logging.info("builder_log: '%s'", builder_log)
            blderProcess = subprocess.Popen(shell_cmd, stdout=builder_log, stderr=builder_log)
            logging.info("blderProcess: '%s'", blderProcess)
            
            
            logging.info("************************************\n\n\n")
            
            ## TODO - somehow close builder_log filehandle if possible
            msg_obj = {}
            msg_obj['builder_id'] = BUILDER_ID
            msg_obj['body'] = "Got build request..."
            msg_obj['first_message'] = True
            msg_obj['job_id'] = job_id
            msg_obj['client_id'] = received_obj['client_id']
            msg_obj['bioc_version'] = bioc_version
            json_str = json.dumps(msg_obj)
            stomp.send(destination=TOPICS['events'], body=json_str,
                       headers={"persistent": "true"})
            logging.info("Reply sent")
        else:
            logging.error("on_message() Invalid JSON: missing job_id key.")

        # Acknowledge that the message has been processed
        self.message_received = True

try:
    logging.info("Attempting to connect using new communication module")
    stomp = getNewStompConnection('', MyListener())
    logging.info("Connection established using new communication module")
    stomp.subscribe(destination=TOPICS['jobs'], id=uuid.uuid4().hex,
                    ack='client')
    logging.info("Subscribed to destination %s" % TOPICS['jobs'])
except Exception as e:
    logging.error("main() Could not connect to ActiveMQ: %s." % e)
    raise

logging.info('Waiting for messages; CTRL-C to exit.')

while True:
    if logging.getLogger().isEnabledFor("debug"):
        logging.debug("main() Waiting to do work.")
    time.sleep(60 * 5)

logging.info("Done.")

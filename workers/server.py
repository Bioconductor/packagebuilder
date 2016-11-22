#!/usr/bin/env python

import time
import sys
import json
import os
import subprocess
import uuid
import stomp
import logging
import threading
import socket
from datetime import datetime
from urllib2 import Request, urlopen, URLError
# Modules created by Bioconductor
from bioconductor.config import ENVIR
from bioconductor.config import TOPICS
from bioconductor.config import BUILDER_ID
from bioconductor.communication import getNewStompConnection


logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s:%(lineno)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)

logging.getLogger("stomp.py").setLevel(logging.WARNING)

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
        # FIXME, don't hardcode keepalive topic name:
        if headers['destination'] == '/topic/keepalive':
            # by default this log message will not
            # be visible (logging level is INFO)
            # but can be made visible if necessary:
            logging.debug('got keepalive message')
            response = {
                "host": socket.gethostname(),
                "script": os.path.basename(__file__)
            }
            stomp.send(body=json.dumps(response),
                destination="/topic/keepalive_response")
            return()

        debug_msg = {"script": os.path.basename(__file__),
            "host": socket.gethostname(), "timestamp":
            datetime.now().isoformat(), "message":
            "received message from %s before thread" % headers['destination']}
        stomp.send(body=json.dumps(debug_msg),
            destination="/topic/keepalive_response")


        logging.info("on_message() Message received")

        # Acknowledge that the message has been received
        self.message_received = True
        t = threading.Thread(target=do_work, args=(body,))
        t.start()


def do_work(body):
    debug_msg = {"script": os.path.basename(__file__),
        "host": socket.gethostname(), "timestamp":
        datetime.now().isoformat(), "message":
        "received message in thread"}
    stomp.send(body=json.dumps(debug_msg),
        destination="/topic/keepalive_response")


    logging.info("on_message() Message acknowledged")
    try:
        received_obj = json.loads(body)
    except ValueError:
        logging.error("on_message() ValueError: invalid JSON?")
        return()
    if ('job_id' in received_obj.keys()): # ignore malformed messages
        try:
            job_id = received_obj['job_id']
            # job_base = job_id.rsplit("_", 1)[0]
            job_base = received_obj['client_id'].rsplit(":")[1]
            bioc_version = received_obj['bioc_version']

            job_dir = os.path.join(ENVIR['spb_home'], "jobs")
            if not os.path.exists(job_dir):
                os.mkdir(job_dir)
            # create package specific directory under jobs/
            job_dir_main = os.path.join(job_dir, job_base)
            if not os.path.exists(job_dir_main):
                os.mkdir(job_dir_main)
            # create package specific R-libs directory for package dependencies
            r_libs_dir = os.path.join(job_dir_main, "R-libs")
            if not os.path.exists(r_libs_dir):
                os.mkdir(r_libs_dir)

            # create package/github commit specific directory
            url_name = received_obj['svn_url'].split("/")
            url_user = url_name[3]
            url_pkg = url_name[4]
            cmd = "/".join(["https://api.github.com/repos",url_user,
                               url_pkg, "commits/HEAD"])
            request = Request(cmd)
            try:
                response = urlopen(request)
                res = response.read()
                run_dir = json.loads(res)['sha'][0:7]
            except URLError, err_url:
                logging.info('Cannot access github log: %s', err_url)
                run_dir = job_id

            job_dir = os.path.join(job_dir_main, run_dir)

            logging.info("Package Working Directory: %s", job_dir)
            if not os.path.exists(job_dir):
                os.mkdir(job_dir)

            jobfilename = os.path.join(ENVIR['spb_home'], job_dir,
                                       "manifest.json")

            jobfile = open(jobfilename, "w")
            jobfile.write(body)
            jobfile.close()

            logging.info("on_message() job_dir: '%s'.", job_dir)

            # create other imports
            os.environ['SPB_HOME'] = ENVIR['spb_home']
            # create BBS-specific imports
            os.environ['BBS_HOME'] = ENVIR['bbs_home']
            os.environ['BBS_SSH_CMD'] = ENVIR['bbs_ssh_cmd'] + " -qi " + ENVIR['bbs_RSA_key'] + " -o StrictHostKeyChecking=no"
            os.environ['BBS_R_HOME'] = ENVIR['bbs_R_home']
            os.environ['BBS_R_CMD'] = ENVIR['bbs_R_cmd']
            os.environ['BBS_BIOC_VERSION'] = ENVIR['bbs_Bioc_version']
            os.environ['BBS_RSYNC_CMD'] = ENVIR['bbs_rsync_cmd']
            os.environ['BBS_RSYNC_RSH_CMD'] = os.environ.get('BBS_RSYNC_CMD') + " -e " + os.environ.get('BBS_SSH_CMD')
            os.environ['BBS_MODE'] = ENVIR['bbs_mode']
            os.environ['BBS_BIOC_VERSIONED_REPO_PATH'] = os.environ.get('BBS_BIOC_VERSION') + "/" + os.environ.get('BBS_MODE')
            os.environ['BBS_STAGE2_R_SCRIPT'] = os.environ.get('BBS_HOME') + "/" + os.environ.get('BBS_BIOC_VERSIONED_REPO_PATH') + "/STAGE2.R"
            os.environ['BBS_NON_TARGET_REPOS_FILE'] = os.environ.get('BBS_HOME') + "/" + os.environ.get('BBS_BIOC_VERSIONED_REPO_PATH') + "/non_target_repos.txt"
            os.environ['BBS_CENTRAL_RHOST'] = ENVIR['bbs_central_rhost']
            os.environ['BBS_CENTRAL_RUSER'] = ENVIR['bbs_central_ruser']
            os.environ['BBS_CENTRAL_RDIR'] = "/home/" +  os.environ.get('BBS_CENTRAL_RUSER') + "/public_html/BBS/" + os.environ.get('BBS_BIOC_VERSIONED_REPO_PATH')
            os.environ['BBS_CENTRAL_BASEURL'] = "http://" + os.environ.get('BBS_CENTRAL_RHOST') + "/BBS/" + os.environ.get('BBS_BIOC_VERSIONED_REPO_PATH')
            os.environ['BBS_CURL_CMD'] =  ENVIR['bbs_curl_cmd']
            os.environ['LANG'] = ENVIR['bbs_lang']
            # R CMD check variables
            os.environ['_R_CHECK_TIMINGS_']="0"
            os.environ['_R_CHECK_EXECUTABLES_']="FALSE"
            os.environ['_R_CHECK_EXECUTABLES_EXCLUSIONS_']="FALSE"
            # R CMD BiocCheck variable
            os.environ['BIOC_DEVEL_PASSWORD'] = ENVIR['bioc_devel_password']

            shell_cmd = ["python", "-m", "workers.builder", jobfilename, bioc_version]

            builder_log = open(os.path.join(job_dir, "builder.log"), "w")

            logging.info("on_message() Attempting to run commands from directory: '%s'", os.getcwd())
            logging.info("on_message() shell_cmd: '%s'", shell_cmd)
            logging.info("on_message() jobfilename: '%s'", jobfilename)
            logging.info("on_message() builder_log: '%s'", builder_log)
            blderProcess = subprocess.Popen(shell_cmd, stdout=builder_log, stderr=builder_log)

            ## TODO - somehow close builder_log filehandle if possible
            msg_obj = {}
            msg_obj['builder_id'] = BUILDER_ID
            msg_obj['status'] = "Got Build Request"
            msg_obj['body'] = "Got build request..."
            msg_obj['first_message'] = True
            msg_obj['job_id'] = job_id
            msg_obj['client_id'] = received_obj['client_id']
            msg_obj['bioc_version'] = bioc_version
            json_str = json.dumps(msg_obj)
            stomp.send(destination=TOPICS['events'], body=json_str,
                       headers={"persistent": "true"})
            logging.info("on_message() Reply sent")
            blderProcess.wait()
            logging.info("on_message() blderProcess finished with status {s}.".format(s=blderProcess.returncode))
            builder_log.close()
            logging.info("on_message() builder_log closed.")
        except Exception as e:
            logging.error("on_message() Caught exception: {e}".format(e=e))
            return()
    else:
        logging.error("on_message() Invalid JSON: missing job_id key.")


try:
    logging.debug("Attempting to connect using new communication module")
    stomp = getNewStompConnection('', MyListener())
    logging.info("Connection established using new communication module")
    stomp.subscribe(destination=TOPICS['jobs'], id=uuid.uuid4().hex,
                    ack='auto')
    logging.info("Subscribed to destination %s" % TOPICS['jobs'])
    stomp.subscribe(destination="/topic/keepalive", id=uuid.uuid4().hex,
                    ack='auto')
    logging.info("Subscribed to  %s" % "/topic/keepalive")
except Exception as e:
    logging.error("main() Could not connect to RabbitMQ: %s." % e)
    raise

logging.info('Waiting for messages; CTRL-C to exit.')



while True:
    if logging.getLogger().isEnabledFor("debug"):
        logging.debug("main() Waiting to do work.")
    time.sleep(60 * 5)

logging.info("Done.")

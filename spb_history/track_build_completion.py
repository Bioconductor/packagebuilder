
# This script listens to messages from the single
# package builder, and posts build reports to the
# issue tracker when it detects a completed build.

import sys
import json
import time
import tempfile
import os
import subprocess
import platform
import ConfigParser
import requests
import cookielib
import threading
import pprint
from stompy import Stomp

try:
    stomp = Stomp("merlot2.fhcrc.org", 61613)
    stomp.connect()
except:
    print("Cannot connect")
    raise

stomp.subscribe({'destination': "/topic/builderevents", 'ack': 'client'})

global build_counter
build_counter = {}
# bad hardcoding:
hosts = ["zin1", "perceval", "moscato1"]

def handle_builder_event(obj):
    global build_counter
    pp = pprint.PrettyPrinter(indent=4)
    if ("client_id" in obj and  \
        "single_package_builder" in obj['client_id'] \
        and 'status' in obj and obj['status'] == 'autoexit'):
        builder_id = obj['builder_id']
        job_id = obj['job_id']
        print("Looks like the build is complete on node %s" % \
          builder_id)
        pp.pprint(build_counter)
        if (not job_id in build_counter):
            build_counter[job_id] = 1
        else:
            build_counter[job_id] += 1
        if (build_counter[job_id] == len(hosts)):
            print("We have enough finished builds to send a report.")

def callback(body, destination):
    print " [x] Received %r" % (body,)
    sys.stdout.flush() ## make sure we see everything
    received_obj = None
    try:
        received_obj = json.loads(body)
    except ValueError as e:
        print("!!!Received invalid JSON!!!")
        print("Invalid json was: %s" % body)
        return
    handle_builder_event(received_obj)
    print("Destination: %s" % destination)
    sys.stdout.flush()


def main_loop():
    print("Waiting for messages...")
    while True:
        try:
            frame = stomp.receive_frame()
            stomp.ack(frame) # do this?
            callback(frame.body, frame.headers.get('destination'))
        except KeyboardInterrupt:
            stomp.disconnect()
            break



if __name__ == "__main__":
    main_loop()
#else:


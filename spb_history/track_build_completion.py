
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
from stompy import Stomp

try:
    stomp = Stomp("merlot2.fhcrc.org", 61613)
    stomp.connect()
except:
    print("Cannot connect")
    raise

stomp.subscribe({'destination': "/topic/builderevents", 'ack': 'client'})

build_counter = {}
# bad hardcoding:
hosts = ["zin1", "perceval", "moscato1"]

def handle_builder_event(obj):
    
    pass

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


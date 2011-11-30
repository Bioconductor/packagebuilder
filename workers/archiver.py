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

# do we want acks?
stomp.subscribe({'destination': "/topic/buildjobs", 'ack': 'client'})
stomp.subscribe({'destination': "/topic/builderevents", 'ack': 'client'})



def callback(body, destination):
    #print " [x] Received %r" % (body,)
    received_obj = json.loads(body) # put this in try block to handle invalid json
    print("Destination: %s" % destination)

while True:
    try:
        frame = stomp.receive_frame()
        stomp.ack(frame) # do this?
        callback(frame.body, frame.headers.get('destination'))
    except KeyboardInterrupt:
        stomp.disconnect()
        break



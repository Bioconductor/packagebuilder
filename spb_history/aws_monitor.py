# no hashbang string, because we are using a specific version of python

import boto
from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message
import json
import sys
import os
import subprocess
import base64
import time
import ConfigParser
from stompy import Stomp

print("Starting monitor...\n")
sys.stdout.flush()

config = ConfigParser.ConfigParser()
config.read('/home/biocadmin/packagebuilder/spb_history/aws.ini')
access_key = config.get("aws", "access_key_id")
secret_key = config.get("aws", "secret_key")

conn = SQSConnection(access_key, secret_key)

q = conn.get_queue("packagesubmitted")
try:
    stomp = Stomp("pinot.fhcrc.org", 61613)
    stomp.connect()
except:
    print("Cannot connect")
    raise



def handle_message(msg):
    body = msg.get_body()
    print("got this message: %s\n" % body)
    sys.stdout.flush()
    # spawn another script to handle notifications of new packages:
    script_path = os.path.dirname(os.path.realpath(__file__))
    arg = base64.b64encode(body)
    cmd = "ruby %s/new_package_notifier.rb %s" % (script_path, arg)
    result_code = subprocess.call(cmd, shell=True)
    this_frame = stomp.send({'destination': "/topic/buildjobs",
      'body': body,
      'persistent': 'true'})
    print("Receipt: %s" % this_frame.headers.get('receipt-id'))
    sys.stdout.flush()
    return True

while (True):
    try:
        m = q.read()
        if (m != None):
            result = handle_message(m)
            if (result):
                q.delete_message(m)
        time.sleep(5)
    except KeyboardInterrupt:
        stomp.disconnect()
        break



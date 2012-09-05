# no hashbang string, because we are using a specific version of python

import boto
from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message
import json
import sys
from datetime import datetime
import os
import time
import ConfigParser
import base64
from stompy import Stomp


config = ConfigParser.ConfigParser()
config.read('/home/biocadmin/packagebuilder/spb_history/aws.ini')
access_key = config.get("aws", "access_key_id")
secret_key = config.get("aws", "secret_key")

conn = SQSConnection(access_key, secret_key)

q = conn.get_queue("packagesubmitted")
try:
    stomp = Stomp("merlot2.fhcrc.org", 61613)
    # optional connect keyword args "username" and "password" like so:
    # stomp.connect(username="user", password="pass")
    stomp.connect()
except:
    print("Cannot connect")
    raise



def handle_message(msg):
    body = base64.b64decode(msg.get_body())
    print("got this message: %s\n" % body)
    this_frame = stomp.send({'destination': "/topic/buildjobs",
      'body': body,
      'persistent': 'true'})
    print("Receipt: %s" % this_frame.headers.get('receipt-id'))
    

while (True):
    m = q.read()
    if (m != None):
        handle_message(m)




#!/usr/bin/env python


## Assume this script is started by a shell script which has read 
## BBS variables and also changed to the correct directory.

import pika
import os
import sys
import json

BBS_home = os.environ['BBS_HOME']
sys.path.append(BBS_home)

import BBScorevars

connection = pika.AsyncoreConnection(pika.ConnectionParameters(
        host='merlot2.fhcrc.org'))
channel = connection.channel()

builder_id = os.getenv("BBS_NODE")

from_web_exchange = channel.exchange_declare(exchange="from_web_exchange",type="fanout")
from_worker_exchange = channel.exchange_declare(exchange="from_worker_exchange", type='fanout')

from_web_queue = channel.queue_declare(exclusive=True)
from_web_queue_name = from_web_queue.queue

channel.queue_bind(exchange='from_web_exchange', queue=from_web_queue_name)

startup_message = {}
startup_message['builder_id'] = builder_id
startup_message['body'] = "Builder has been started"
json_str = json.dumps(startup_message)

channel.basic_publish(exchange='from_worker_exchange',
                      routing_key="key.frombuilders",
                      body= json_str)

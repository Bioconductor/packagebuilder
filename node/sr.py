#!/usr/bin/env python3
import pika
import sys
import json
import time

connection = pika.AsyncoreConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()



from_web_exchange = channel.exchange_declare(exchange="from_web_exchange",type="fanout")
from_worker_exchange = channel.exchange_declare(exchange="from_worker_exchange", type='fanout')

from_web_queue = channel.queue_declare(exclusive=True)
from_web_queue_name = from_web_queue.queue

channel.queue_bind(exchange='from_web_exchange', queue=from_web_queue_name)

print(' [*] Waiting for messages. To exit press CTRL+C')

builder_id = "No-arg"
#print len(sys.argv)
if (len(sys.argv) == 2):
    builder_id = sys.argv[1]


def callback(ch, method, properties, body):
    print((" [x] Received %r" % (body,)))
    msg_obj = {}
    msg_obj['builder_id'] = builder_id
    msg_obj['body'] = "Build starting..."
    msg_obj['first_message'] = True
    json_str = json.dumps(msg_obj)
    channel.basic_publish(exchange='from_worker_exchange',
                          routing_key="loquat", # key.frombuilders
                          body= json_str)
    time.sleep(1)
    msg_obj = {}
    msg_obj['builder_id'] = builder_id
    msg_obj['body'] = '\na second message'
    msg_obj['first_message'] = False
    json_str = json.dumps(msg_obj)
    channel.basic_publish(exchange='from_worker_exchange',
                          routing_key="loquat", # key.frombuilders
                          body= json_str)
    

channel.basic_consume(callback,
                      queue=from_web_queue.queue,
                      no_ack=True)

pika.asyncore_loop()


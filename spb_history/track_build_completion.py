
# This script listens to messages from the single
# package builder, and posts build reports to the
# issue tracker when it detects a completed build.


# FIXME - be aware that builds for different BioC versions
# may be occuring and we need to be aware of them and be able
# to tell them apart. Right now we're ignoring this.

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
import urllib
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
    if ("client_id" in obj and  \
        "single_package_builder" in obj['client_id'] \
        and 'status' in obj and obj['status'] == 'autoexit'):
        builder_id = obj['builder_id']
        job_id = obj['job_id']
        print("Looks like the build is complete on node %s" % \
          builder_id)
        if (not job_id in build_counter):
            build_counter[job_id] = 1
        else:
            build_counter[job_id] += 1
        if (build_counter[job_id] == len(hosts)):
            print("We have enough finished builds to send a report.")
            post_report_to_tracker(obj)

def post_report_to_tracker(obj):
    segs = obj['client_id'].split(":")
    roundup_issue = segs[1]
    tarball_name = segs[2]
    f = urllib.urlopen("http://merlot2.fhcrc.org:8000/jid/%s" % obj['job_id'])
    job_id = f.read().strip()
    if job_id == "0":
        print("There is no build report for this job!")
        return
    url = "http://merlot2.fhcrc.org:8000/job/%s/" % job_id
    print("build report url: %s\n" %url)
    sys.stdout.flush()
    #print("Sleeping for 30 seconds...\n")
    #time.sleep(30)
    response = requests.get(url)
    html = response.text.encode('ascii', 'ignore')
    #print("html before filtering: %s\n" % html)
    html = filter_html(html)
    #print("html after filtering: %s\n" % html)
    result = get_overall_build_result(job)
    url = copy_report_to_site(html, tarball_name)
    post_text = get_post_text(result, url)
    status  = post_to_tracker(roundup_issue, tarball_name, result, html, \
        post_text)
    print("Done.\n")
    sys.stdout.flush()



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


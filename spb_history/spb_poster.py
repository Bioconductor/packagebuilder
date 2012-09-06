import sys
import json
import time
import tempfile
import os
import subprocess
import platform
import urllib2
from datetime import datetime, date, time
from stompy import Stomp

## this may need to change:
num_builders = 3

# set up django environment
path = os.path.abspath(os.path.dirname(sys.argv[0]))
segs = path.split("/")
segs.pop()
path =  "/".join(segs)
sys.path.append(path)
os.environ['DJANGO_SETTINGS_MODULE'] = 'spb_history.settings'
# now you can do stuff like this:
#from spb_history.viewhistory.models import Package
#print Package.objects.count()

from spb_history.viewhistory.models import Job
from spb_history.viewhistory.models import Package
from spb_history.viewhistory.models import Build
from spb_history.viewhistory.models import Message
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

def parse_time(time_str):
    """ take a string like 'Tue Nov 29 2011 11:55:40 GMT-0800 (PST)'
        and convert it to a DateTime """
    segs = time_str.split(" GMT")
    return(datetime.strptime(segs[0], "%a %b %d %Y %H:%M:%S"))

def handle_dcf_info(obj, build):
    build.maintainer = obj['maintainer']
    build.version = obj['version']
    build.save()

def get_build_obj(obj):
    return(Build.objects.get(jid=obj['job_id'], builder_id=obj['builder_id']))


def handle_builder_event(obj):
    phases = ["building", "checking", "buildingbin", "preprocessing",
      "post_processing"]
    parent_job = None
    job_id = None
    if (obj.has_key('job_id')):
        job_id = obj['job_id']
        try:
            parent_job = Job.objects.get(job_id=job_id)
        except Job.DoesNotExist:
            print("No parent job for %s; ignoring message." % job_id)
            return()
    else:
        print("Malformed message, ignoring it.")
        return
    build_obj = None
    if (obj.has_key('status')):
        status = obj['status']
        build_obj = get_build_obj(obj)
        if (status == 'dcf_info'):
            print("handling dcf info")
            handle_dcf_info(obj, build_obj)
        elif (status in phases):
            handle_completed_builds(obj, build_obj)
            if obj['status'] == 'post_processing':
                if obj.has_key('build_product'):
                    build_obj.build_product = obj['build_product']
                if obj.has_key('filesize'):
                    build_obj.filesize = obj['filesize']
                    handle_completed_builds(obj, build_obj)
                    return()

def handle_completed_builds(obj, build_obj):
    ##  did all builders finish this job?
    ## if so, post it to the tracker
    if (obj['status'] == "post_processing_complete" \
    and (obj['body']=="Synced repository to website" or \
    obj['body']=='Syncing repository failed' or\
    obj['body'] == "Post-processing complete.")):
        print("build is complete for this node, do we have all nodes?")
        buildlist = Build.objects.filter(job=build_obj.job.id)
        ok = 0
        for item in buildlist:
          if (item.buildbin_result != ""):
            ok += 1
        if ok == num_builders:
            print("we have enough nodes, sending a message")
            job_id = build_obj.job.id
            obj['job_id'] = job_id
            json_str = json.dumps(obj)
            #this_frame = stomp.send({'destination': "/topic/buildcomplete",
            #  'body': json_str,
            #  'persistent': 'true'})
            #print("Receipt: %s" % this_frame.headers.get('receipt-id'))
            post_report_to_tracker(job_id)

def post_report_to_tracker(job_id)
    time.sleep(1) # need this?
    jobs = Job.objects.filter(id=job_id)
    job = jobs[0]
    if (!"single_package_builder" in job.client_id):
        print("This is not an SPB job, not posting it to tracker.\n")
        print("Job id = %s" % job_id)
        return
    url = "http://merlot2.fhcrc.org:4000/job/%s/" % job_id
    response = urllib2.urlopen(url)
    html = response.read()
    print("html is\n\n%d\n\n" % html)
    sys.stdout.flush()

def callback(body, destination):
    print " [x] Received %r" % (body,)
    sys.stdout.flush() ## make sure we see everything
    received_obj = json.loads(body) # put this in try block to handle invalid json
    elif (destination == '/topic/builderevents'):
        handle_builder_event(received_obj)
    print("Destination: %s" % destination)

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
    # test it:
    post_report_to_tracker(232)
    
import sys
import json
import time
import tempfile
import os
import subprocess
import platform
from datetime import datetime, date, time
from stompy import Stomp

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

def handle_job_start(obj):
    pkg = obj['job_id'].split("_")[0]
    try:
        existing_pkg = Package.objects.get(name=pkg)
    except Package.DoesNotExist:
        existing_pkg = Package(name=pkg)
        existing_pkg.save()
    
    j = Job(package=existing_pkg,
      job_id=obj['job_id'],
      time_started=parse_time(obj['time']),
      pkg_url=obj['svn_url'],
      force=obj['force'],
      client_id=obj['client_id'])
    j.save()

def handle_dcf_info(obj, build):
    build.maintainer = obj['maintainer']
    build.version = obj['version']
    build.save()

def handle_first_message(obj, parent_job):
    build = Build(job=parent_job,
      builder_id=obj['builder_id'],
      jid=obj['job_id'],
      maintainer='unknown',
      version='0.0.0',
      preprocessing_result='unknown',
      buildsrc_result='unknown',
      checkinstall_result='unknown',
      checksrc_result='unknown',
      buildbin_result='unknown',
      postprocessing_result='unknown')
    build.save()
    return(build)

def handle_check_complete(obj, build_obj):
    if obj['warnings'] == True:
        result = "WARNINGS"
    else:
        result = "OK"
    build_obj.checksrc_result = result
    build_obj.save()

def get_build_obj(obj):
    return(Build.objects.get(jid=obj['job_id'], builder_id=obj['builder_id']))

def handle_builder_event(obj):
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
    if(obj.has_key('first_message') and obj['first_message'] == True):
        print("handling first message")
        build_obj = handle_first_message(obj, parent_job)
    if (obj.has_key('status')):
        status = obj['status']
        if (status == 'dcf_info'):
            print("handling dcf info")
            handle_dcf_info(obj, get_build_obj(obj))
        elif (status == 'check_complete'):
            print("handle check_complete")
            handle_check_complete(obj, get_build_obj(obj))
        else:
            print("ignoring message:%s" % obj)

def callback(body, destination):
    print " [x] Received %r" % (body,)
    received_obj = json.loads(body) # put this in try block to handle invalid json
    if (destination == '/topic/buildjobs'):
        handle_job_start(received_obj)
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



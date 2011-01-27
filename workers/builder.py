#!/usr/bin/env python


## Assume this script is started by a shell script which has read 
## BBS variables and also changed to the correct directory.

import pika
import os
import sys
import json

if (len(sys.argv) < 2):
    sys.exit("builder.py started without manifest file argument, exiting...")

manifest_fh = open(sys.argv[1], "r")
manifest_json = fh.read()
manifest_fh.close()
manifest = json.loads(manifest_json)
working_dir = os.path.split(sys.argv[1])[0]
os.chdir(working_dir)
    

print "Builder has been started"

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

def send_message(msg):
    global builder_id
    merged_dict = {}
    merged_dict['builder_id'] = builder_id
    if type(msg) is dict:
        merged_dict.update(msg)
    else:
        merged_dict['body'] = msg
    json_str = json.dumps(merged_dict)
    print "sending message:"
    print json_str
    print
    channel.basic_publish(exchange='from_worker_exchange',
                          routing_key="key.frombuilders",
                          body= json_str)

def is_build_required(manifest):
    if ("force" in manifest.keys()):
        if (manifest['force'] == True):
            return(True)
    
    package_name = manifest['job_id'].split("_")[0]
    description_url = manifest['svn_url'].rstrip("/") + "/DESCRIPTION"
    description = subprocess.Popen(["curl", "-s", 
        "--user" "%s:%s" % (os.getenv("SVN_USER"), os.getenv("SVN_PASS")),
        description_url]) # todo - handle it if description does not exist
        
    for line in description.split("\n"):
        if line.startswith("Version: "):
            svn_version = line.split(": ")[1]
            
    bioc_r_map = {"2.7": "2.12", "2.8": "2.13", "2.9": "2.14", "2.10": "2.15"} # need a better way to determine R version
    r_version = bioc_r_map[os.getenv["BBS_BIOC_VERSION"]]
    cran_repo_map = { \
        'source': "src/contrib", \
        'win.binary': "bin/windows/contrib/" + r_version, \
        'win64.binary': "bin/windows64/contrib/" + r_version, \
        'mac.binary.leopard': "bin/macosx/leopard/contrib/" + r_version \
    }
    # todo - put repos url in config file (or get it from user)
    repository_url = "http://bioconductor.org/course-packages/%s/PACKAGES" % cran_repo_map[r_version]
    packages = subprocess.Popen(["curl", "-s", repository_url])
    inpackage = False
    for line in packages.split("\n"):
        if line == "Package: %s" % package_name:
            inpackage = true
        if line.startswith("Version: "):
            repository_version = line.split(": ")[1]
            break
    print "[%s] svn version is %s, repository version is %s" % (package_name, svn_version,
        repository_version)
    return(svn_version != repository_version)

send_message("Builder has been started")
if not (is_build_required(manifest)):
    send_message({"status": "build_not_required",
        "body": "Build not required (versions identical in svn and repository)."})

send_message("hello hello hello")
#!/usr/bin/env python


## Assume this script is started by a shell script which has read 
## BBS variables and also changed to the correct directory.

import pika
import os
import sys
import json
import subprocess
import thread
import time
import datetime

if (len(sys.argv) < 2):
    sys.exit("builder.py started without manifest file argument, exiting...")

print("argument is %s" % sys.argv[1])
manifest_fh = open(sys.argv[1], "r")
manifest_json = manifest_fh.read()
manifest_fh.close()
print("manifest_json is %s" % manifest_json)
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
    now = datetime.datetime.now()
    merged_dict['time'] = str(now)
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
        "--user", "%s:%s" % (os.getenv("SVN_USER"), os.getenv("SVN_PASS")),
        description_url], stdout=subprocess.PIPE).communicate()[0] # todo - handle it if description does not exist
        
    for line in description.split("\n"):
        if line.startswith("Version: "):
            svn_version = line.split(": ")[1]
            
    bioc_r_map = {"2.7": "2.12", "2.8": "2.13", "2.9": "2.14", "2.10": "2.15"} # need a better way to determine R version
    r_version = bioc_r_map[os.getenv("BBS_BIOC_VERSION")]
    pkg_type = BBScorevars.getNodeSpec(builder_id, "pkgType")
    
    cran_repo_map = { \
        'source': "src/contrib", \
        'win.binary': "bin/windows/contrib/" + r_version, \
        'win64.binary': "bin/windows64/contrib/" + r_version, \
        'mac.binary.leopard': "bin/macosx/leopard/contrib/" + r_version \
    }
    # todo - put repos url in config file (or get it from user)
    repository_url = "http://bioconductor.org/course-packages/%s/PACKAGES" % cran_repo_map[pkg_type]
    packages = subprocess.Popen(["curl", "-s", repository_url],
        stdout=subprocess.PIPE).communicate()[0]
    inpackage = False
    repository_version = False
    for line in packages.split("\n"):
        if line == "Package: %s" % package_name:
            inpackage = True
        if (line.startswith("Version: ") and inpackage):
            repository_version = line.split(": ")[1]
            break
    if not repository_version:
        return True # package hasn't been pushed to repo before
    print "[%s] svn version is %s, repository version is %s" % (package_name, svn_version,
        repository_version)
    return(svn_version != repository_version)

send_message("Builder has been started")
if not (is_build_required(manifest)):
    send_message({"status": "build_not_required",
        "body": "Build not required (versions identical in svn and repository)."})
    send_message({"status": "normal_end", "body": "Build process is ending normally."})
    sys.exit(0)


stop_thread = False
thread_is_done = False
message_sequence = 1

def tail(filename):
    global thread_is_done
    global message_sequence
    prevsize = 0
    while 1:
        time.sleep(0.2)
        #print ".",
        if not os.path.isfile(filename):
            continue
        st = os.stat(filename)
        if st.st_size == 0:
            continue
        if stop_thread == True:
            num_bytes_to_read = st.st_size - prevsize
            f = open(filename, 'r')
            f.seek(prevsize)
            bytes = f.read(num_bytes_to_read)
            f.close()
            print bytes,
            sys.stdout.flush()
            send_message({"status": "building", "sequence": message_sequence, "body": bytes})
            prevsize = st.st_size
            thread_is_done = True
            print "Thread says I'm done"
            break # not needed here but might be needed if program was to continue doing other stuff
            # and we wanted the thread to exit

        if (st.st_size > 0) and (st.st_size > prevsize):
            num_bytes_to_read = st.st_size - prevsize
            f = open(filename, 'r')
            f.seek(prevsize)
            bytes = f.read(num_bytes_to_read)
            f.close()
            print bytes,
            sys.stdout.flush()
            send_message({"status": "building", "sequence": message_sequence, "body": bytes})
            message_sequence += 1
            prevsize = st.st_size

# Don't use BBS_SVN_CMD because it may not be defined on all nodes
package_name = manifest['job_id'].split("_")[0]
export_path = os.path.join(working_dir, package_name)
svn_cmd = "svn --non-interactive --username %s --password %s export %s %s" % ( \
    os.getenv("SVN_USER"), os.getenv("SVN_PASS"), manifest['svn_url'], package_name)
clean_svn_cmd = svn_cmd.replace(os.getenv("SVN_USER"),"xxx").replace(os.getenv("SVN_PASS"),"xxx")
send_message({"status": "svn_cmd", "body": clean_svn_cmd})
p = subprocess.Popen(svn_cmd, shell=True)
sts = os.waitpid(p.pid, 0)[1]
send_message({"status": "svn_result", "result": sts, "body": \
    "svn export completed with status %d" % sts})


outfile = "R.out"
if (os.path.exists(outfile)):
    os.remove(outfile)
pkg_type = BBScorevars.getNodeSpec(builder_id, "pkgType")
if pkg_type == "source":
    flags = ""
else:
    flags = "--binary"
out_fh = open(outfile, "w")
start_time = datetime.datetime.now()
thread.start_new(tail,(outfile,))
r_cmd = "%s CMD build %s %s" % (os.getenv("BBS_R_CMD"), flags, package_name)
send_message({"status": "r_cmd", "body": r_cmd})
p = subprocess.Popen(r_cmd, stdout=out_fh, stderr=subprocess.STDOUT, shell=True)
sts = os.waitpid(p.pid, 0)[1]
stop_time = datetime.datetime.now()
elapsed_time = str(stop_time - start_time)
stop_thread = True # tell thread to stop
out_fh.close()

while thread_is_done == False: pass # wait till thread tells us to stop
print "Done"


send_message({"status": "build_complete", "result_code": sts,
    "body": "Build completed with status %d" % sts, "elapsed_time": elapsed_time})

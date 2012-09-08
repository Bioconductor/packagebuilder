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



def get_build_obj(obj):
    print("in get_build_obj(), obj['job_id']==%s, obj['builder_id']==%s\n"\
        % (obj['job_id'], obj['builder_id']))
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
        handle_completed_builds(obj, build_obj)
    else:
        print("job does not have status key!\n")
        sys.stdout.flush()

def handle_completed_builds(obj, build_obj):
    ##  did all builders finish this job?
    ## if so, post it to the tracker
    sys.stdout.flush()
    print("in handle_completed_builds()\n")
    if(obj['status'] =='build_failed'):
        print("obj['status'] is 'build_failed'!!!!")
    if ((obj['status'] == 'build_failed') or \
    (obj['status'] == "post_processing_complete" \
    and (obj['body']=="Synced repository to website" or \
    obj['body']=='Syncing repository failed' or\
    obj['body'] == "Post-processing complete."))):
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
            post_report_to_tracker(job_id)
        else:
            print("we only have %d nodes, not sending a message" % ok)

def post_report_to_tracker(job_id):
    jobs = Job.objects.filter(id=job_id)
    job = jobs[0]
    if (not "single_package_builder" in job.client_id):
        print("This is not an SPB job, not posting it to tracker.\n")
        print("Job id = %s" % job_id)
        return
    #single_package_builder_autobuild:558:spbtest_0.99.0.tar.gz
    segs = job.client_id.split(":")
    roundup_issue = segs[1]
    tarball_name = segs[2]
    url = "http://merlot2.fhcrc.org:8000/job/%s/" % job_id
    print("build report url: %s\n" %url)
    print("Sleeping for 10 seconds...\n")
    sys.stdout.flush()
    time.sleep(10)
    response = requests.get(url)
    html = response.text.encode('ascii', 'ignore')
    print("html before filtering: %s\n" % html)
    html = filter_html(html)
    print("html after filtering: %s\n" % html)
    result = get_overall_build_result(job)
    url = copy_report_to_site(html, tarball_name)
    post_text = get_post_text(result, url)
    status  = post_to_tracker(roundup_issue, tarball_name, result, html, \
        post_text)
    print("Done.\n")
    sys.stdout.flush()

def copy_report_to_site(html, tarball_name):
    print("HTML=\n\n%s\n\n" % html)
    t = tempfile.mkstemp()
    f = open(t[1], "w")
    f.write(html)
    f.close
    segs = tarball_name.split(".tar.gz")
    pkg = segs[0]
    now = time.localtime()
    ts = time.strftime("%Y%m%d%H%M%S", now)
    destfile = "%s_buildreport_%s.html" % (pkg, ts)
    cmd = \
      "/usr/bin/scp -i /home/biocadmin/.ssh/pkgbuild_rsa %s webadmin@krait:/extra/www/bioc/spb_reports/%s" % \
      (t[1], destfile)
    print("cmd = %s\n" % cmd)
    result = subprocess.call(cmd, shell=True)
    chmod_cmd = "/usr/bin/ssh -i /home/biocadmin/.ssh/pkgbuild_rsa webadmin@krait \"chmod a+r /extra/www/bioc/spb_reports/%s\"" % destfile
    print("chmod_cmd = %s\n" % chmod_cmd)
    result = subprocess.call(chmod_cmd, shell=True)
    #time.sleep(1) # is this needed?
    os.remove(t[1])
    url = "http://bioconductor.org/spb_reports/%s" % destfile
    return(url)

def post_to_tracker(roundup_issue, tarball_name, result,\
  html, post_text):
    config = ConfigParser.ConfigParser()
    config.read('/home/biocadmin/packagebuilder/spb_history/tracker.ini')
    username = config.get("tracker", "username")
    password = config.get("tracker", "password")
    url = "http://tracker.fhcrc.org/roundup/bioc_submit/"
    jar = cookielib.CookieJar()
    params = {"__login_name": username, "__login_password": password,\
      "@action": "login", "__came_from": \
      "http://tracker.fhcrc.org/roundup/bioc_submit/"}
    r = requests.get(url, params=params, cookies=jar)
    url2 = url + "issue%s" % roundup_issue
    params2 = {"@action": "edit", "@note": post_text}
    r2 = requests.get(url2, params=params2, cookies=jar)
    
    

def get_post_text(build_result, url):
    ok = True
    if not build_result == "OK":
        ok = False
    msg = """
Dear Package contributor,

This is the automated single package builder at bioconductor.org.

Your package has been built on Linux, Mac, and Windows. 

    """
    if ok:
        msg = msg + """
Congratulations! The package built without errors or warnings
on all platforms.
        """
    else:
        msg = msg + """
On one or more platforms, the build result was "%s".
This may mean there is a problem with the package that you need to fix.
Or it may mean that there is a problem with the build system itself.

        """ % build_result
    msg = msg + """
Please see the following build report for more details:

%s

    """ % url
    return(msg)
    
def get_overall_build_result(job):
    builds = Build.objects.filter(job=job)
    for build in builds:
        if build.version == "0.0.0" and build.preprocessing_result == "":
            continue # filter out builds on wrong machines
        buildbin_result = "OK"
        if "linux" in build.platform.lower():
            if not build.buildbin_result in ["OK", "skipped"]:
                return(build.buildbin.result)
        else:
            if not build.buildbin_result == "OK":
                return(build.buildbin_result)
        if not build.buildsrc_result == "OK":
            return(build.buildsrc_result)
        if not build.checksrc_result == "OK":
            return(build.checksrc_result)
        return "OK"

def filter_html(html):
    lines = html.split("\n")
    good_lines = []
    for line in lines:
        if ("InstallCommand" in line):
            segs = line.split("<pre")
            line = segs[0]
        if("pkgInstall(" in line):
            segs = line.split("</pre>")
            line = segs[1]
        if (not "merlot2" in line):
            good_lines.append(line)
    return("\n".join(good_lines))
    
def callback(body, destination):
    print " [x] Received %r" % (body,)
    sys.stdout.flush() ## make sure we see everything
    received_obj = json.loads(body) # put this in try block to handle invalid json
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
    # test it:
    #post_report_to_tracker(232)
    main_loop()
#else:
#    main_loop()


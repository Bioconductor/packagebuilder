#!/usr/bin/env python

## Assume this script is started by a shell script which has read
## BBS variables and also changed to the correct directory.
import logging
import sys
from bioconductor.config import ENVIR

log_level = int(ENVIR['log_level'])
logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=log_level)


logging.getLogger("stomp.py").setLevel(logging.WARNING)

logging.info("logg" + str(log_level))

import os
import os.path
import json
import subprocess
import threading
import time
import datetime
import platform
import unicodedata
import atexit
import mechanize
import re
import urllib2
#from stomp.listener import PrintingListener
from stomp.listener import StatsListener
from urllib2 import Request, urlopen, URLError
from threading import Timer

# Modules created by Bioconductor
from bioconductor.communication import getNewStompConnection
from bioconductor.config import BIOC_R_MAP
from bioconductor.config import BUILDER_ID
from bioconductor.config import HOSTS
from bioconductor.config import TOPICS

sys.path.append(ENVIR['bbs_home'])
sys.path.append(os.path.join(ENVIR['bbs_home'], "test", "python"))
import BBScorevars
import dcf

stomp = None
manifest = None
working_dir = None
packagebuilder_ssh_cmd = None
packagebuilder_scp_cmd = None
build_product = None
callcount = None

log_highlighter = "***************"

# This class is meant to behave like Linux/Unix `tail -f <file>`.
#
#    Usage example :
# Run a command that continuously emits output, capture the output as soon as possible
# and sent it in a stomp message.  We inspect the output every .2 seconds and handle it.
class Tailer(threading.Thread):
    def __init__(self, filename, status):
        logging.info("Attempting to tail file {fname}".format(fname = filename))
        threading.Thread.__init__(self)
        self.filename = filename
        self.status = status
        self.message_sequence = 1
        self._stop = threading.Event()
    def stop(self):
        self._stop.set()
    def stopped(self):
        return self._stop.isSet()
    def run(self):
        prevsize = 0
        while True:
            time.sleep(0.2)
            if not os.path.isfile(self.filename):
                continue
            st = os.stat(self.filename)
            if st.st_size == 0:
                continue

            if self.stopped():
                logging.debug("Tailer.run() stopped: %s." % self.status)
                if (st.st_size == 0):
                    logging.debug("Tailer.run() 0 bytes in output; exiting.")
                    return()
                num_bytes_to_read = st.st_size - prevsize
                logging.debug("Tailer.run() num_bytes_to_read = %d." %
                              num_bytes_to_read)
                if (num_bytes_to_read == 0):
                    logging.debug("Tailer.run() 0 bytes to read; exiting.")
                    return()

                f = open(self.filename, 'r')
                f.seek(prevsize)
                bytes = f.read(num_bytes_to_read)
                f.close()
                logging.debug("Tailer.run() stopped; read %d bytes." % len(bytes))
                send_message({
                    "status": self.status,
                    "sequence": self.message_sequence,
                    "body": bytes
                })
                logging.info(self.status + ":\n" + bytes)
                prevsize = st.st_size
                logging.debug("Tailer.run() done %s" % self.status)
                break
                # not needed here but might be needed if program was
                # to continue doing other stuff and we wanted the
                # thread to exit

            if (st.st_size > 0) and (st.st_size > prevsize):
                num_bytes_to_read = st.st_size - prevsize
                f = open(self.filename, 'r')
                f.seek(prevsize)
                bytes = f.read(num_bytes_to_read)
                f.close()
                logging.debug("Tailer.run() read %d bytes" % len(bytes))
                send_message({
                    "status": self.status,
                    "sequence": self.message_sequence,
                    "body": bytes
                })
                logging.info(self.status + ":\n" + bytes)
                self.message_sequence += 1
                prevsize = st.st_size

# Since we're modifying encoding in this function, it's important that we're consistent
# (as unicode) when attempting to write to the log file.
def send_message(msg, status=None):
    global stomp
    global manifest
    logging.debug(u"Attempting to send message: '{msg}'".format(msg=msg))
    merged_dict = {}
    merged_dict['builder_id'] = BUILDER_ID
    merged_dict['client_id'] = manifest['client_id']
    merged_dict['job_id'] = manifest['job_id']
    now = datetime.datetime.now()
    merged_dict['time'] = str(now)
    if type(msg) is dict:
        logging.debug(u"msg is dict")
        merged_dict.update(msg)
        if not ('status' in merged_dict.keys()):
            if not (status == None):
                merged_dict['status'] = status
    else:
        logging.debug(u"msg is NOT dict")
        merged_dict['body'] = msg
        if not (status == None):
            merged_dict['status'] = status

    if("body" in merged_dict):
        body = None
        try:
            body = unicode(merged_dict['body'], errors='replace')
        except TypeError:
            body = merged_dict['body']
        logging.debug(u"Final modified body: '{body}'".format(body=body))
        merged_dict['body'] = \
                unicodedata.normalize('NFKD', body).encode('ascii','ignore')
        logging.debug(u"Ascii encoded body: '{body}'".format(body=merged_dict['body']))

    logging.debug(u"Final merged_dict: '{merged_dict}'".format(merged_dict=merged_dict))
    json_str = json.dumps(merged_dict)
    logging.debug(u"JSON json_str: '{json_str}'".format(json_str=json_str))

    logging.debug(u"Sending message: %s" % json_str)
    stomp.send(destination=TOPICS['events'], body=json_str,
               headers={"persistent": "true"})
    logging.debug(u"send_message(): Message sent.")

def send_dcf_info(dcf_file):
    try:
        maintainer = dcf_file.getValue("Maintainer")
    except:
        maintainer = "unknown"
    send_message({
        "status": "dcf_info",
        "package_name": dcf_file.getValue("Package"),
        "maintainer": maintainer,
        "version": dcf_file.getValue("Version")
    })

def is_build_required(manifest):
    global svn_url_global
    svn_url_global = manifest['svn_url']
    package_name = manifest['job_id'].split("_")[0]
    logging.info("Starting is_build_required() '%s'." % package_name)

    if (get_package_source() == "svn"):
        description_url = manifest['svn_url'].rstrip("/") + "/DESCRIPTION"
        logging.debug("is_build_required() package source is svn" +
            "\n  description_url = " + description_url +
            "\n  svn_user ="  + ENVIR['svn_user'] +
            "\n  svn_pass = " + ENVIR['svn_pass'])
        try:
            description = subprocess.Popen([
                "curl", "-k", "-s", "--user", "%s:%s" %
                (ENVIR['svn_user'], ENVIR['svn_pass']),
                description_url
            ], stdout=subprocess.PIPE).communicate()[0]
            # TODO - handle it if description does not exist
        except:
            logging.error("is_build_required() curl exception: %s.",
                          sys.exc_info()[0])
            raise

        logging.debug("is_build_required()" +
                      "\n  description = %s" % description +
                      "\n  length = %d" % len(description))

        dcf_file = dcf.DcfRecordParser(description.rstrip().split("\n"))
        send_dcf_info(dcf_file)

        svn_version = dcf_file.getValue("Version")
    elif get_package_source() == "github":
        github_url = re.sub(r'\.git$', '', manifest['svn_url'])
        if not github_url.endswith("/"):
            github_url += "/"
        # We only build the master branch. There had better be one.
        # (technically we build whatever the default branch is, but
        # this step looks at master because to find out what the
        # default branch is at this point we would need octokit here).
        github_url += "master/DESCRIPTION"
        github_url = github_url.replace("https://github.com",
          "https://raw.githubusercontent.com")
        f = urllib2.urlopen(github_url)
        dcf_text = f.read()
        dcf_file = dcf.DcfRecordParser(dcf_text.rstrip().split("\n"))
        send_dcf_info(dcf_file)
        svn_version = dcf_file.getValue("Version")
    elif get_package_source() == "tracker":
        tmp = manifest["svn_url"].split("/")
        pkgname = tmp[len(tmp)-1].replace(".tar.gz", "")
        if (pkgname.find("_") == -1): # package name doesn't have version in it
            return(True) # TODO - download tarball and examine DESCRIPTION file
        svn_version = pkgname.split("_")[1]

    if ("force" in manifest.keys()):
        if (manifest['force'] is True):
            return(True)

    r_version = BIOC_R_MAP[ENVIR['bbs_Bioc_version']]
    pkg_type = BBScorevars.getNodeSpec(BUILDER_ID, "pkgType")

    cran_repo_map = {
        'source': "src/contrib",
        'win.binary': "bin/windows/contrib/" + r_version,
        'win64.binary': "bin/windows64/contrib/" + r_version,
        'mac.binary': "bin/macosx/contrib/" + r_version,
        'mac.binary.mavericks': "bin/macosx/mavericks/contrib/" + r_version
    }
    # todo - put repos url in config file (or get it from user)
    base_repo_url = HOSTS['bioc']
    if (manifest['repository'] == 'course'):
        base_repo_url += '/course-packages'
    elif (manifest['repository'] == 'scratch'):
        base_repo_url += '/scratch_repos/' + manifest['bioc_version']

    repository_url = "%s/%s/PACKAGES" % (base_repo_url, cran_repo_map[pkg_type])
    # What if there is no file at this url?
    packages = subprocess.Popen(["curl", "-k", "-s", repository_url],
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
    logging.debug("is_build_required()" +
                  "\n  [%s] svn version is %s, repository version is %s" %
                  (package_name, svn_version, repository_version))
    return svn_version != repository_version

def setup():
    global manifest
    global working_dir
    global dcf
    global packagebuilder_ssh_cmd, packagebuilder_rsync_cmd, \
        packagebuilder_rsync_rsh_cmd, packagebuilder_scp_cmd
    global callcount


    logging.info("Starting setup().")

    callcount = 1

    packagebuilder_ssh_cmd = BBScorevars.ssh_cmd.replace(
        ENVIR['bbs_RSA_key'], ENVIR['spb_RSA_key'])
    packagebuilder_rsync_cmd = BBScorevars.rsync_cmd.replace(
        ENVIR['bbs_RSA_key'], ENVIR['spb_RSA_key'])
    packagebuilder_rsync_rsh_cmd = BBScorevars.rsync_rsh_cmd.replace(
        ENVIR['bbs_RSA_key'], ENVIR['spb_RSA_key'])
    packagebuilder_scp_cmd = packagebuilder_ssh_cmd.replace("ssh", "scp", 1)

    if (platform.system() == "Windows"):
        packagebuilder_scp_cmd = \
            "c:/cygwin/bin/scp.exe -qi %s -o StrictHostKeyChecking=no" % \
            ENVIR['spb_RSA_key']
        packagebuilder_ssh_cmd = \
            "c:/cygwin/bin/ssh.exe -qi %s -o StrictHostKeyChecking=no" % \
            ENVIR['spb_RSA_key']

    logging.debug("setup()" +
        "\n  argument = %s" % sys.argv[1] +
        "\n  cwd = %s" % os.getcwd() +
        "\n  does %s exist? %s" % (sys.argv[1], os.path.exists(sys.argv[1])) +
        "\n  size of %s: %d" % (sys.argv[1], os.stat(sys.argv[1]).st_size))

    timeout = 10
    i = 0
    while (os.stat(sys.argv[1]).st_size == 0):
        logging.debug("Empty manifest file, waiting.")
        time.sleep(1)
        i += 1
        if i == timeout:
            logging.warning("Empty manifest file in setup().")
            # todo - send a message and do something with it
            break
    time.sleep(1)
    manifest_fh = open(sys.argv[1], "r")
    manifest_json = manifest_fh.read()
    manifest_fh.close()
    logging.debug("Reading manifest_json = %s" % manifest_json)
    manifest = json.loads(manifest_json)
    manifest['svn_url'] = manifest['svn_url'].strip()
    logging.debug("Attempting to determine `working_dir` based on sys.argv.")
    logging.debug("Contents of `sys.argv`: {content}.".format(content = sys.argv))
    working_dir = os.path.split(sys.argv[1])[0]
    logging.info("Initial working directory: {wd}".format(wd = os.getcwd()))
    os.chdir(working_dir)
    working_dir = os.getcwd()
    logging.info("New working directory: {wd}".format(wd = os.getcwd()))

    if 'R_LIBS_USER' in os.environ:
        logging.info("Initial R_LIBS_USER: {rLibsUser}".format(rLibsUser = os.environ['R_LIBS_USER']))
    else:
        logging.info("Initial R_LIBS_USER variable is empty.")

    # package lib
    package_dir = os.path.dirname(working_dir)
    expectedRLibsUser = os.path.join(package_dir, "R-libs")

    # system-lib
    sysLib = os.path.join(os.environ['BBS_R_HOME'], "library")

    AllLibs = expectedRLibsUser + os.pathsep + sysLib

    os.environ['R_LIBS_USER'] = AllLibs
    logging.info("New R_LIBS_USER: {rLibsUser}".format(
        rLibsUser = os.environ['R_LIBS_USER']))

    os.environ['PATH'] = os.environ['PATH'] + \
        os.pathsep + ENVIR['bbs_R_home'] + os.sep + \
        "bin"
    logging.debug("Working dir = %s" % working_dir)
    logging.info("Finished setup().")

def setup_stomp():
    global stomp
    logging.info("Getting Stomp Connection:")
    try:
        stomp = getNewStompConnection('', StatsListener())
    except:
        logging.error("setup_stomp(): Cannot connect.")
        raise


def git_clone():
    git_url = re.sub(r'\/$', '', manifest['svn_url'])
    if not git_url.endswith(".git"):
        git_url += ".git"
    git_cmd = "git clone %s" % git_url
    send_message({"status": "git_cmd", "body": git_cmd})
    logging.info("git_clone command: " + git_cmd)
    retcode = subprocess.call(git_cmd, shell=True)
    send_message({"status": "post_processing", "retcode": retcode, "body": "Finished git clone. "})
    send_message({"status": "git_result", "result": retcode, "body": \
        "git clone completed with status %d" % retcode})
    logging.info("Finished git clone. \n git clone completed with status: " +  str(retcode))
    if (not retcode == 0):
        sys.exit("git clone failed")



def svn_export():
    # Don't use BBS_SVN_CMD because it may not be defined on all nodes
    package_name = manifest['job_id'].split("_")[0]
    svn_cmd = "svn --non-interactive --username %s --password %s export %s %s" % ( \
        ENVIR['svn_user'], ENVIR['svn_pass'], manifest['svn_url'], package_name)
    clean_svn_cmd = svn_cmd.replace(ENVIR['svn_user'],"xxx").replace(ENVIR['svn_pass'],"xxx")
    send_message({"status": "svn_cmd", "body": clean_svn_cmd})
    retcode = subprocess.call(svn_cmd, shell=True)
    send_message({"status": "post_processing", "retcode": retcode, "body": "Finished svn export. "})
    send_message({"status": "svn_result", "result": retcode, "body": \
        "svn export completed with status %d" % retcode})
    if (not retcode == 0):
        sys.exit("svn export failed")

def extract_tarball():
    package_name = manifest['job_id'].split("_")[0]
    # first, log in to the tracker and get a cookie
    tracker_url = HOSTS['tracker']
    if not "tracker.bioconductor.org" in manifest['svn_url'].lower():
        tracker_url = tracker_url + '/roundup/bioc_submit'

    br = mechanize.Browser()
    br.open(tracker_url)
    br.select_form(nr=2)
    br["__login_name"] = ENVIR['tracker_user']
    br["__login_password"] = ENVIR['tracker_pass']
    br.submit()

    segs = manifest['svn_url'].split("/")
    local_file = segs[len(segs)-1]
    try:
        br.retrieve(manifest['svn_url'], local_file)
        retcode = 0
    except:
        retcode = 255
        logging.error("extract_tarball() Failed to download '%s' to '%s'.",
                      manifest['svn_url'], local_file)
        raise

    send_message({
        "status": "post_processing",
        "retcode": retcode,
        "body": "Download of tarball completed. "})
    if (retcode != 0):
        logging.error("extract_tarball() Failed to 'curl' tarball.")
        raise

    tmp = manifest['svn_url'].split("/")
    tarball = tmp[len(tmp)-1]
    package_name = tarball.split("_")[0]
    # what if package name does not have version in it? do this:
    package_name = package_name.replace(".tar.gz", "")

    os.rename(tarball, "%s.orig" % tarball)
    extra_flags = ""
    if platform.system() == "Windows":
        extra_flags = " --no-same-owner "
    retcode = subprocess.call("tar %s -zxf %s.orig" %
                              (extra_flags, tarball), shell=True)
    send_message({
        "status": "post_processing",
        "retcode": retcode,
        "body": "Untar of tarball completed. "})
    if (not retcode == 0):
        logging.error("extract_tarball() Failed to 'untar' tarball.")
        raise
    f = open("%s/DESCRIPTION" % package_name)
    description = f.read()
    f.close()
    dcf_file = dcf.DcfRecordParser(description.rstrip().split("\n"))
    send_dcf_info(dcf_file)

def install_pkg_deps():
    package_name = manifest['job_id'].split("_")[0]
    f = open("%s/%s/DESCRIPTION" % (working_dir, package_name))
    description = f.read()
    logging.info("DESCRIPTION file loaded for package '%s': \n%s", package_name, description)
    f.close()
    desc = dcf.DcfRecordParser(description.rstrip().split("\n"))
    fields = ["Depends", "Imports", "Suggests", "Enhances", "LinkingTo"]
    args = ""
    for field in fields:
        try:
            args += '%s=@@%s@@; ' % (field, desc.getValue(field))
        except KeyError:
            pass
    r_script = os.path.join(ENVIR['spb_home'], "installPkgDeps.R")
    log = "%s/installDeps.log" % working_dir
    if args.strip() == "":
        args = "None=1"
    rscript_dir = os.path.dirname(ENVIR['bbs_R_cmd'])
    rscript_binary = os.path.join(rscript_dir, "Rscript")
    cmd = "%s --vanilla --no-save --no-restore %s  --args \"%s\" > %s 2>&1" % \
      (rscript_binary, r_script, args.strip(), log)

    send_message({
        "body": "Installing dependencies. ",
        "status": "preprocessing",
        "retcode": 0
    })
    logging.info("Command to install dependencies:" +
                  "\n  %s" % cmd)
    retcode = subprocess.call(cmd, shell=True)
    send_message({
        "body": "Installing dependency status: " + str(retcode) + ". ",
        "status": "post_processing",
        "retcode": retcode
    })
    logging.info("Finished Installing Dependencies.\n completed with status: " + str(retcode))
    return retcode

def install_pkg():
    package_name = manifest['job_id'].split("_")[0]
    package_dir = os.path.dirname(working_dir)
    pkg_git_clone = os.path.join(working_dir, package_name)

    r_cmd = ENVIR['bbs_R_cmd']
    lib_dir = os.path.join(package_dir, "R-libs")

    cmd = "%s CMD INSTALL --library=%s %s" % (r_cmd, lib_dir, pkg_git_clone)

    send_message({
        "body": "Installing package: " + package_name,
        "status": "preprocessing",
        "retcode": 0
    })
    logging.info("Command to install package:" + "\n  %s" % cmd)
    retcode = subprocess.call(cmd, shell=True)
    send_message({
        "body": "Installing package status: " + str(retcode) + ". ",
        "status": "post_processing",
        "retcode": retcode
    })
    logging.info("Finished Installing Package.\n completed with status: " + str(retcode))
    return retcode

def get_source_tarball_name():
    pkgname = manifest['job_id'].split("_")[0]
    # if tarball name does not have version:
    pkgname = pkgname.replace(".tar.gz", "")
    files = os.listdir(os.getcwd())
    tarball = None
    for file in files:
        if pkgname in file and ".tar.gz" in file and (not ".orig" in file):
            tarball = file
            break
    return(tarball)

def do_check(cmdCheck, cmdBiocCheck):
    outfile = "Rcheck.out"
    if (os.path.exists(outfile)):
        os.remove(outfile)

    out_fh = open(outfile, "w")

    background = Tailer(outfile, "checking")
    background.start()

    timeout_limit = int(ENVIR['timeout_limit'])
    min_time, sec_time = divmod(timeout_limit, 60)

    start_time = datetime.datetime.now()
    kill = lambda process: process.kill()
    pope = subprocess.Popen(cmdCheck, stdout=out_fh, stderr=subprocess.STDOUT,
                            shell=True)
    my_timer = Timer(timeout_limit, kill, [pope])
    try:
        my_timer.start()
        retcode1 = pope.wait()
    finally:
        my_timer.cancel()

    stop_time = datetime.datetime.now()

    # in testing, had to close and reopen with append
    # in order to have ERROR message occur in middle of pipe/check
    # if not the message would be at the bottom of BiocCheck and checks would
    # not format correctly
    out_fh.close()
    out_fh = open(outfile, "a")
    if (retcode1 == -9):
         out_fh.write(" ERROR\nTIMEOUT: R CMD check exceeded " +  str(min_time) + "mins\n\n\n")
    out_fh.close()

    out_fh = open(outfile, "a")
    pope2 = subprocess.Popen(cmdBiocCheck, stdout=out_fh,
                             stderr=subprocess.STDOUT, shell=True)
    my_timer = Timer(timeout_limit, kill, [pope2])
    try:
        my_timer.start()
        retcode2 = pope2.wait()
    finally:
        my_timer.cancel()

    # in testing, had to close and reopen with append
    # in order to have ERROR message occur in middle of pipe/check
    # if not the message would be at the bottom of BiocCheck and checks would
    # not format correctly
    out_fh.close()
    out_fh = open(outfile, "a")
    if (retcode2 == -9):
         out_fh.write(" ERROR\nTIMEOUT: R CMD BiocCheck exceeded " +  str(min_time) + "mins\n\n\n")

    time_dif = stop_time - start_time
    min_time, sec_time = divmod(time_dif.seconds,60)
    sec_time = str(format(float(str(time_dif).split(":")[2]), '.2f'))
    elapsed_time = str(min_time) + " minutes " + sec_time + " seconds"
    out_fh.close()
    background.stop()

    background.join()
    # check for warnings from R CMD check/BiocCheck
    out_fh = open(outfile)
    warnings = False
    for line in out_fh:
        if line.rstrip().endswith("WARNING") or \
             "* WARNING:" in line:
            warnings = True
            break
    out_fh.close()

    if (retcode1 == 0 and retcode2 == 0):
        retcode = 0
    elif (retcode1 == -9 or retcode2 == -9):
        retcode = -9
    else:
        retcode = 1

    send_message({
        "status": "check_complete",
        "retcode": retcode,
        "warnings": warnings,
        "body": "Check completed",
        "elapsed_time": elapsed_time})

    logging.info("Check Complete\n R CMD check completed with status: " +
                 str(retcode1) + " Elapsed time: " + elapsed_time +
                 ". \n R CMD BiocCheck completed with status: " + str(retcode2))

    return (retcode)

def win_multiarch_check():
    tarball = get_source_tarball_name()
    pkg = tarball.split("_")[0]
    libdir = "%s.buildbin-libdir" % pkg
    if (os.path.exists(libdir)):
        retcode = _call("rm -rf %s" % libdir, False)
    if (not os.path.exists(libdir)):
        os.mkdir(libdir)

    r = ENVIR['bbs_R_cmd']

    cmd = ("%s CMD INSTALL --build --merge-multiarch --library=%s.buildbin-libdir"
           " %s >%s-install.out 2>&1" % (r, pkg, tarball, pkg))

    cmdCheck = ("%s CMD check --library=%s.buildbin-libdir"
        " --install='check:%s-install.out' --force-multiarch --no-vignettes"
        " --timings %s" % (r, pkg, pkg, tarball))

    cmdBiocCheck = ("%s CMD BiocCheck --build-output-file=R.out --new-package %s" % (r, tarball))

    send_message({"status": "check_cmd", "body": cmd})
    logging.info("R Install Command:\n" + cmd)
    logging.info("R Check Command:\n" + cmdCheck)
    logging.info("R BiocCheck Command:\n" + cmdBiocCheck)
    send_message({
        "status": "checking",
        "sequence": 0,
        "body": "Installing package prior to check...\n\n"
    })
    logging.info("Installing package prior to check...\n\n")
    retcode = win_multiarch_buildbin("checking")
    if (retcode == 0):
           send_message({"status": "clear_check_console"})

           # run install
           outfileI = "Rinstall.out"
           if (os.path.exists(outfileI)):
             os.remove(outfileI)
           out_fh = open(outfileI, "w")
           pope = subprocess.Popen(cmd, stdout=out_fh,
                                   stderr=subprocess.STDOUT,
                                   shell=True)
           retcode1 = pope.wait()
           out_fh.close()
           if (retcode1 != 0):
               logging.info("Install cmd failed")
           # run check
           retcode = do_check(cmdCheck, cmdBiocCheck)

    else:
        send_message({
            "status": "check_complete",
            "retcode": retcode,
            "warnings": False,
            "body": "Pre-check installation failed with status %d" % retcode,
            "elapsed_time": 999
        })
    return (retcode)

def win_multiarch_buildbin(message_stream):
    logging.info("Starting win_multiarch_buildbin")
    tarball = get_source_tarball_name()
    pkg = tarball.split("_")[0]
    libdir = "%s.buildbin-libdir" % pkg
    if (os.path.exists(libdir)):
        _call("rm -rf %s" % libdir, False)
    logging.debug("win_multiarch_buildbin() Does %s exist? %s." %
                  (libdir, os.path.exists(libdir)))
    if not (os.path.exists(libdir)):
        os.mkdir(libdir)
    logging.debug("win_multiarch_buildbin() After mkdir: does %s exist? %s" %
                  (libdir, os.path.exists(libdir)))
    time.sleep(1)
    cmd = "{R} CMD INSTALL --build --merge-multiarch --library={libdir} {tarball}".format(
        R=ENVIR['bbs_R_cmd'], libdir=libdir, tarball=tarball)

    send_message({"status": "r_buildbin_cmd", "body": cmd})

    return do_build(cmd, message_stream, False)

def check_package():
    send_message({"status": "starting_check", "body": ""})

    if (platform.system() == "Windows"):
        return(win_multiarch_check())

    tarball = get_source_tarball_name()

    extra_flags = ""
    if (platform.system() == "Darwin"):
        extra_flags = " --no-multiarch "

    cmdCheck = ("%s CMD check --no-vignettes --timings %s %s") % (ENVIR['bbs_R_cmd'], extra_flags, tarball)

    cmdBiocCheck = "%s CMD BiocCheck --build-output-file=R.out --new-package %s" % (ENVIR['bbs_R_cmd'], tarball)

    send_message({"status": "check_cmd", "body": cmdCheck})
    logging.info("R Check Command:\n" + cmdCheck)
    logging.info("R BiocCheck Command:\n" + cmdBiocCheck)
    retcode = do_check(cmdCheck, cmdBiocCheck)

    return (retcode)

def do_build(cmd, message_stream, source):
    if source:
        outfile = "R.out"
    else:
        outfile = "Rbuildbin.out"
    if (os.path.exists(outfile)):
        os.remove(outfile)
    out_fh = open(outfile, "w")
    logging.info("Starting do_build(); message {msgStream}.".format(msgStream= message_stream))
    logging.info("The working directory: {wd}".format(wd=os.getcwd()))
    logging.debug("The current environment variables: \n {envVars}".format(envVars=os.environ))
    logging.info("Build command: '{cmd}'.".format(cmd= cmd))
    background = Tailer(outfile, message_stream)
    background.start()
    
    timeout_limit = int(ENVIR['timeout_limit'])
    min_time, sec_time = divmod(timeout_limit, 60)

    kill = lambda process: process.kill()
    pope  = subprocess.Popen(cmd, stdout=out_fh, stderr=subprocess.STDOUT,
                             shell=True)
    my_timer = Timer(timeout_limit, kill, [pope])
    try:
        my_timer.start()
        retcode = pope.wait()
    finally:
        my_timer.cancel()

    background.stop()
    out_fh.close()

    # in testing, had to close and reopen with append
    # in order to have ERROR message occur in middle of pipe
    # if not the message would be at the bottom not format correctly
    out_fh = open(outfile, "a")
    if (retcode == -9):
        out_fh.write(" ERROR\nTIMEOUT: R CMD build exceeded " +  str(min_time) + "mins\n\n\n")
    out_fh.close()

    logging.debug("do_build() Before joining background thread.")
    background.join()
    logging.debug("do_build() After joining background thread.")
    logging.info("Done do_build().")
    return(retcode)

def build_package(source_build):
    global pkg_type

    pkg_type = BBScorevars.getNodeSpec(BUILDER_ID, "pkgType")

    buildmsg = None
    if (source_build):
        buildmsg = "building"
    else:
        buildmsg = "buildingbin"

    if ((not source_build) and (pkg_type == "source")):
        send_message({"status": "skip_buildbin", "body": "skipped"})
        logging.info("Skip buildbin")
        return(0)

    if (not source_build):
        if platform.system() == "Darwin":
            pkg_type = "mac.binary.mavericks"
        elif platform.system() == "Linux":
            pkg_type = "source"
        elif platform.system() == "Windows":
            pkg_type = "win.binary"
        else:
            pkg_type = "source"
        send_message({"status": "starting_buildbin", "body": ""})
        logging.info("Start buildbin")

    global message_sequence
    global warnings
    message_sequence = 1
    flags = "--keep-empty-dirs --no-resave-data"

    if (source_build):
        package_name = manifest['job_id'].split("_")[0]
        r_cmd = "%s CMD build %s %s" % \
                (ENVIR['bbs_R_cmd'], flags, package_name)
    else:
        if pkg_type == "mac.binary" or pkg_type == "mac.binary.mavericks":
            libdir = "libdir"
            if os.path.exists(libdir):
                _call("rm -rf %s" % libdir, False)
            if (not (os.path.exists(libdir))):
                os.mkdir(libdir)
            r_cmd = os.environ['SPB_HOME'] + "/build-universal.sh %s %s" % (
                get_source_tarball_name(), libdir)

    status = None
    if (source_build):
        status = "r_cmd"
        outfile = "R.out"
    else:
        status = "r_buildbin_cmd"
        outfile = "Rbuildbin.out"
    logging.debug("Before build, working dir is %s." %
                  working_dir)

    start_time = datetime.datetime.now()
    if ((not source_build) and pkg_type == "win.binary"):
        retcode = win_multiarch_buildbin(buildmsg)
    else:
        send_message({"status": status, "body": r_cmd})
        retcode = do_build(r_cmd, buildmsg, source_build)

    stop_time = datetime.datetime.now()
    time_dif = stop_time - start_time
    min_time, sec_time = divmod(time_dif.seconds,60)
    sec_time = str(format(float(str(time_dif).split(":")[2]), '.2f'))
    elapsed_time = str(min_time) + " minutes " + sec_time + " seconds"

    # check for warnings
    out_fh = open(outfile)
    warnings = False
    for line in out_fh:
        if line.lower().startswith("warning:"):
            warnings = True
        if line.lower().startswith("error:"):
            retcode = 1
    out_fh.close()

    complete_status = None
    if (source_build):
        complete_status = "build_complete"
    else:
        complete_status = "buildbin_complete"

    send_message({
        "status": complete_status,
        "retcode": retcode,
        "warnings": warnings,
        "body": "Build completed with status %d" % retcode,
        "elapsed_time": elapsed_time})
    logging.info(complete_status + "\n Build completed with status: " +
                 str(retcode) + " Elapsed time: " + elapsed_time)

    return (retcode)

def svn_info():
    logging.debug("svn_info() svn_url is %s" % manifest['svn_url'])
    svn_info = subprocess.Popen([
        "svn", "info", manifest['svn_url']
    ], stdout=subprocess.PIPE).communicate()[0]
    logging.debug("svn_info() svn_info is:\n%s" % svn_info)
    dcf_records = dcf.DcfRecordParser(svn_info.rstrip().split("\n"))
    keys = ['Path', 'URL', 'Repository Root', 'Repository UUID', 'Revision',
            'Node Kind', 'Last Changed Author', 'Last Changed Rev',
            'Last Changed Date']
    svn_hash = {}
    for key in keys:
        svn_hash[key] = dcf_records.getValue(key)
    svn_hash['status'] = "svn_info"
    svn_hash['body'] = "svn info"
    send_message(svn_hash)

def git_info():
    logging.info("git_info():")
    logging.info("git_url is %s" % manifest['svn_url'])
    url_name = manifest['svn_url'].split("/")
    url_user = url_name[3]
    url_pkg = url_name[4]
    cmd = "/".join(["https://api.github.com/repos",url_user,
                       url_pkg, "commits/HEAD"])
    request = Request(cmd)
    try:
        response = urlopen(request)
        res = response.read()
        git_dir = json.loads(res)
        sha = git_dir['sha']
        last_auth = git_dir['commit']['author']['name']
        last_date = git_dir['commit']['author']['date']
        commit_msg = git_dir['commit']['message']
        files_mod = ''
        for dic in git_dir['files']:
            files_mod = files_mod + " "  + dic['filename']
        logging.info("\n Commit ID: " + sha + "\n Last Change Author: " +
                      last_auth + "\n Last Chage Date: " + last_date +
                      "\n Last Commit Message: \n" + commit_msg +
                      "\n Files Changes: " + files_mod)
    except URLError, err_url:
        logging.info('Cannot access github log: %s', err_url)

# This function does the following, acting on behalf of biocadmin on staging.bioconductor.org:
#   1. First prune old copies of the package in a path like :
#      /loc/www/bioconductor-test.fhcrc.org/scratch-repos/3.3/src/contrib/PKG_*.tar.gz
#
#       Where "PKG" is the name of the package.
#
#   2. Second, packages are copied to this location, so that later packages (submitted
#       to the tracker) can depend upon a package already submitted for inclusion.
#
#   TODO: Get rid of ugly windows workarounds now that we know how
def propagate_package():
    global build_product
    global repos
    global url
    pkg_type = BBScorevars.getNodeSpec(BUILDER_ID, "pkgType")
    ext = BBScorevars.pkgType2FileExt[pkg_type]
    files = os.listdir(working_dir)
    build_product = filter(lambda x: x.endswith(ext), files)[0]
    r_version = BIOC_R_MAP[ENVIR['bbs_Bioc_version']]
    if (platform.system() == "Darwin"):
        os_seg = "bin/macosx/mavericks/contrib/%s" % r_version
    elif (platform.system() == "Linux"):
        os_seg = "src/contrib"
    else:
        os_seg = "bin/windows/contrib/%s" % r_version

    if (manifest['repository'] == 'course'):
        repos = "/loc/www/bioconductor-test.fhcrc.org/course-packages/%s" % os_seg
        url = repos.replace("/loc/www/bioconductor-test.fhcrc.org/",
            HOSTS['bioc'])
    elif (manifest['repository'] == 'scratch'):
        repos = '/loc/www/bioconductor-test.fhcrc.org/scratch-repos/%s/%s' % (
            manifest['bioc_version'], os_seg)
        url = repos.replace(
            "/loc/www/bioconductor-test.fhcrc.org/scratch-repos/",
            HOSTS['bioc'] + '/scratch-repos')

    url += "/" + build_product

    rawsize = os.path.getsize(build_product)
    kib = rawsize / float(1024)
    filesize = "%.2f" % kib

    package_name = manifest['job_id'].split("_")[0]
    files_to_delete = "%s/%s_*.%s" % (repos, package_name, ext)

    if (platform.system() == "Windows"):
        command = "c:/cygwin/bin/ssh.exe -qi %s -o StrictHostKeyChecking=no biocadmin@%s 'rm -f %s/%s_*.zip'"
        command = command % (ENVIR['spb_RSA_key'], ENVIR['spb_staging_url'], repos, package_name)
        retcode = subprocess.call(command)
    else:
        logging.info("propagate_package() files_to_delete: %s" %
                      files_to_delete)
        retcode = ssh("rm -f %s" % files_to_delete)

    logging.info("Finished propagate_package().\n Result of deleting files: %d." % retcode)
    send_message({
        "body": "Pruning older packages from repository. ",
        "status": "post_processing",
        "retcode": retcode
    })
    if retcode != 0:
        logging.error("propagate_package() Failed to prune repos.")
        sys.exit("repos prune failed")

    if (platform.system() == "Windows"):
        logging.info("propagate_package() Windows chmod")
        chmod_retcode = subprocess.call(
            "chmod a+r %s" % os.path.join(working_dir, package_name))
        logging.info("propagate_package() Windows chmod_retcode = %d" %
                      chmod_retcode)
        send_message({
            "status": "chmod_retcode",
            "body": "chmod_retcode=%d" % chmod_retcode,
            "retcode": chmod_retcode
        })
        command = "c:/cygwin/bin/scp.exe -qi %s -o StrictHostKeyChecking=no %s biocadmin@%s:%s/"
        command = command % (ENVIR['spb_RSA_key'], build_product, ENVIR['spb_staging_url'], repos)
        logging.info("propagate_package() Windows scp command = %s." %
                      command)
        retcode = subprocess.call(command)
        command = "c:/cygwin/bin/ssh.exe -qi %s -o StrictHostKeyChecking=no biocadmin@%s 'chmod a+r %s/%s_*.zip'"
        command = command % (ENVIR['spb_RSA_key'], ENVIR['spb_staging_url'], repos, package_name)
        remote_chmod_retcode = subprocess.call(command)
        logging.info("propagate_package() Windows remote_chmod_retcode = %s" %
                      remote_chmod_retcode)
    else:
        logging.info("propagate_package() %s chmod not run" %
                      platform.system())
        retcode = scp(build_product, repos)

    logging.info("propagate_package() Result of copying file: %d" % retcode)
    send_message({
        "body": "Copied build file to repository. ",
        "status": "post_processing",
        "retcode": retcode,
        "build_product": build_product,
        "filesize": filesize
    })
    if retcode != 0:
        logging.error("propagate_package() Failed to copy file to repository.")
        sys.exit("failed to copy file to repository")

## todo - get rid of ugly workarounds
def _call(command_str, shell):
    global callcount
    if (platform.system() == "Windows"):
        stdout_fn = os.path.join(working_dir, "%dout.txt" % callcount)
        stderr_fn = os.path.join(working_dir, "%derr.txt" % callcount)

        stdout_fh = open(stdout_fn, "w")
        stderr_fh = open(stderr_fn, "w")

        callcount += 1
        # ignore shell arg
        command_str = str(command_str)
        logging.debug("_call()" +
                      "\n  command_str = %s" % command_str +
                      "\n  len(command_str) = %d" % len(command_str))
        retcode = subprocess.call(command_str, shell=False, stdout=stdout_fh,
                                  stderr=stderr_fh)
        stdout_fh.close()
        stderr_fh.close()
        return(retcode)
    else:
        return(subprocess.call(command_str, shell=shell))

def ssh(command, user='biocadmin', host=ENVIR['spb_staging_url']):
    command = "%s %s@%s \"%s\"" % (packagebuilder_ssh_cmd, user, host, command)
    logging.info("ssh() command: %s" % command)
    retcode = _call([command], shell=True)
    return(retcode)

def scp(src, dest, srcLocal=True, user='biocadmin',
        host=ENVIR['spb_staging_url']):
    if (srcLocal):
        chmod_cmd = "chmod a+r %s" % src
        logging.info("chmod_cmd: " + chmod_cmd)
        chmod_retcode = _call([chmod_cmd], shell=True) #todo abort build if retcode != 0
        send_message({
            "status": "post_processing",
            "retcode": chmod_retcode,
            "body": "Set read permissions on build product. "
        })
        if chmod_retcode != 0:
            sys.exit("chmod failed")
        logging.info("scp() chmod retcode: %s" % chmod_retcode)
        send_message({
            "status": "chmod_retcode",
            "body": "chmod_retcode=%d" % chmod_retcode,
            "retcode": chmod_retcode
        })
        command = "%s %s %s@%s:%s" % (
            packagebuilder_scp_cmd, src, user, host, dest)
    else:
        command = "%s %s@%s:%s %s" % (
            packagebuilder_scp_cmd, user, host, src, dest)
    logging.info("scp() command: %s" % command)
    retcode = _call([command], shell=True)

    return(retcode)

def onexit():
    global svn_url_global
    try:
        svn_url_global
    except NameError:
        svn_url_global = "undefined"

    logging.info("Cleaning Directory().")
    clean_up_dir()
    logging.info("Ending via onexit().")
    send_message({
        "body": "builder.py exited",
        "status": "autoexit",
        "retcode": -1,
        "svn_url": svn_url_global
    })
    stomp.disconnect(receipt=None)

def update_packages_file():
    global repos
    global build_product

    r_version = BIOC_R_MAP[ENVIR['bbs_Bioc_version']]
    if (platform.system() == "Darwin"):
        pkg_type = BBScorevars.getNodeSpec(BUILDER_ID, "pkgType")
        if pkg_type == "mac.binary.leopard":
            os_seg = "bin/macosx/contrib/%s" % r_version
        else:
            os_seg = "bin/macosx/mavericks/contrib/%s" % r_version
    elif (platform.system() == "Linux"):
        os_seg = "src/contrib"
    else:
        os_seg = "bin/windows/contrib/%s" % r_version

    if (manifest['repository'] == 'course'):
        repos = "/loc/www/bioconductor-test.fhcrc.org/course-packages/%s" % os_seg
        url = repos.replace("/loc/www/bioconductor-test.fhcrc.org/",
                            HOSTS['bioc'] + '/')
        script_loc = "/loc/www/bioconductor-test.fhcrc.org/course-packages"
    elif (manifest['repository'] == 'scratch'):
        repos = '/loc/www/bioconductor-test.fhcrc.org/scratch-repos/%s/%s' % (
            manifest['bioc_version'], os_seg)
        url = repos.replace(
            "/loc/www/bioconductor-test.fhcrc.org/scratch-repos/",
            HOSTS['bioc'] + "/scratch-repos/")
        script_loc = "/loc/www/bioconductor-test.fhcrc.org/scratch-repos/%s" % manifest['bioc_version']

    pkg_type = BBScorevars.getNodeSpec(BUILDER_ID, "pkgType")
    if pkg_type == "mac.binary.leopard":
        pkg_type = "mac.binary"
    command = "%s biocadmin@%s 'R -f %s/update-repo.R --args %s %s'"
    command = command % (packagebuilder_ssh_cmd, ENVIR['spb_staging_url'], script_loc, repos, pkg_type)
    logging.info("update_packages_file() command: %s"  % command)
    retcode = subprocess.call(command, shell=True)
    logging.info("update_packages_file() retcode: %d" % retcode)
    send_message({
        "status": "post_processing",
        "retcode": retcode,
        "body": "Updated packages list. "
    })
    if retcode != 0:
        send_message({
            "status": "post_processing_complete",
            "retcode": retcode,
            "body": "Updating packages failed.",
            "build_product": build_product,
            "url": url
        })
        sys.exit("updating packages failed")
    if (manifest['repository'] == 'course' or manifest['repository'] == 'scratch'):
        command = "%s biocadmin@%s \"source ~/.bash_profile && cd /home/biocadmin/bioc-test-web/bioconductor.org && rake deploy_production\""
        command = command % (packagebuilder_ssh_cmd, ENVIR['spb_staging_url'])
        logging.info("update_packages_file() sync command = %s" % command)
        retcode = subprocess.call(command, shell=True)
        send_message({
            "status": "post_processing",
            "retcode": retcode,
            "body": "Synced repository to website. ",
            "build_product": build_product,
            "url": url
        })
        if retcode != 0:
            send_message({
                "status": "post_processing_complete",
                "retcode": retcode,
                "body": "Syncing repository failed",
                "build_product": build_product,
                "url": url})
            sys.exit("sync to website failed")
        send_message({
            "status": "post_processing_complete",
            "retcode": retcode,
            "body": "Post-processing complete.",
            "build_product": build_product,
            "url": url})

def get_r_version():
    logging.info("BBS_R_CMD = %s" % ENVIR['bbs_R_cmd'])
    r_version_raw, stderr = subprocess.Popen([
        ENVIR['bbs_R_cmd'],"--version"
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
    lines = r_version_raw.split("\n")
    r_version_line = lines[0]
    return r_version_line.replace("R version ", "")

def get_node_info():
    logging.info("Node Info:")
    r_version = get_r_version()
    osys = BBScorevars.getNodeSpec(BUILDER_ID, "OS")
    arch = BBScorevars.getNodeSpec(BUILDER_ID, "Arch")
    plat = BBScorevars.getNodeSpec(BUILDER_ID, "Platform")
    send_message({
        "status": "node_info",
        "r_version": r_version,
        "os": osys,
        "arch": arch,
        "platform": plat,
        "body": "node_info",
        "bioc_version": ENVIR['bbs_Bioc_version']})
    logging.info("\n os: " + osys +  "\n r_version: " + r_version +
                 "\n bioc_version: " + ENVIR['bbs_Bioc_version'])

def is_valid_url():
    # todo bulletproof this; sometimes fails bogusly on windows
    if (manifest['svn_url'].lower().startswith(HOSTS['svn'])):
        svn_url = True
    elif (manifest['svn_url'].lower().find("tracker.fhcrc.org") > -1 or
      manifest['svn_url'].lower().find("tracker.bioconductor.org") > -1): # todo, ensure .tar.gz end
        svn_url = False
    elif "https://github.com" in manifest['svn_url'].lower():
        svn_url = False
    else:
        return False

    if svn_url:

        description_url = manifest['svn_url'].rstrip("/") + "/DESCRIPTION"

        timeout = 10
        i  = 0
        description = None
        while i < timeout:
            i += 1
            description = subprocess.Popen([
                "curl", "-k", "-s", "--user",
                "%s:%s" % (ENVIR['svn_user'], ENVIR['svn_pass']),
                description_url
            ], stdout=subprocess.PIPE).communicate()[0]
            logging.warning("is_valid_url() Invalid svn URL; retrying.")
            time.sleep(0.5)
            if (len(description) > 0):
                break

        if (len(description) == 0  or description.lower().find("404 not found") > -1):
            return False
        return True
    return True

def get_package_source():
    if manifest['svn_url'].lower().startswith(HOSTS['svn']):
        return("svn")
    if "https://github.com" in manifest['svn_url'].lower():
        return("github")
    if "tracker.bioconductor.org" in manifest['svn_url'].lower():
        return("tracker")
    raise

def clean_up_dir():

    path_tar = get_source_tarball_name()
    if path_tar == None:
        path_tar = manifest['job_id'].split("_")[0] + ".tar.gz"
    if os.path.exists(path_tar):
        os.remove(path_tar)

    if (platform.system() == "Windows"):
        path_zip = path_tar.replace(".tar.gz", ".zip")
        if os.path.exists(path_zip):
            os.remove(path_zip)
        lib_dir = re.split('_', path_tar)[0] + ".buildbin-libdir"
        if os.path.exists(lib_dir):
            os.system("rm -rf " + lib_dir)
        if os.path.exists("1err.txt"):
            os.remove("1err.txt")
        if os.path.exists("1out.txt"):
            os.remove("1out.txt")
        if os.path.exists("2err.txt"):
            os.remove("2err.txt")
        if os.path.exists("2out.txt"):
            os.remove("2out.txt")

    if (platform.system() == "Darwin"):
        path_tgz = path_tar.replace(".tar.gz", ".tgz")
        if os.path.exists(path_tgz):
            os.remove(path_tgz)
        if os.path.exists("libdir"):
            os.system("rm -rf libdir")

#    if os.path.exists("manifest.json"):
#        os.remove("manifest.json")

    pkgDirName = manifest['job_id'].split("_")[0]
    cloneDir = "rm -rf " + pkgDirName
    if os.path.exists(pkgDirName):
        os.system(cloneDir)



## Main namespace. execution starts here.
if __name__ == "__main__":
    logging.info("Starting builder")
    if (len(sys.argv) < 2):
        logging.error("main() Missing manifest and R version arguments.")
        sys.exit("missing manifest and R version arguments")
    logging.info("Starting builder.py.")

    logging.info("\n\n" + log_highlighter + "\n\n")

    setup()
    atexit.register(onexit)

    setup_stomp()

    logging.info("\n\n" + log_highlighter + "\n\n")

    if (manifest['bioc_version'] != ENVIR['bbs_Bioc_version']):
        logging.error("main() BioC-%s not supported." %
                      manifest['bioc_version'])
        sys.exit("BioC version not supported")

    send_message({"status": "Builder has been started"})

    if not is_valid_url():
        send_message({
            "status": "invalid_url",
            "body": "Invalid SVN url."
        })
        logging.error("main() Invalid svn url.")
        sys.exit("invalid svn url")

    get_node_info()
    logging.info("\n\n" + log_highlighter + "\n\n")

    if get_package_source() == "svn":
        svn_info()
        logging.info("\n\n" + log_highlighter + "\n\n")

    if get_package_source() == "github":
        git_info()
        logging.info("\n\n" + log_highlighter + "\n\n")

    is_build_required = is_build_required(manifest)
    if not (is_build_required):
        send_message({
            "status": "build_not_required",
            "body": "Identical versions for %s." % get_package_source()
        })
        send_message({
            "status": "normal_end",
            "body": "Build not required."
        })
        logging.info("Normal build completion; build not required.")
        sys.exit(0)

    if get_package_source() == "svn":
        svn_export()
    elif get_package_source() == "tracker":
        extract_tarball()
    elif get_package_source() == "github":
        git_clone()

    logging.info("\n\n" + log_highlighter + "\n\n")
    logging.info("Installing Package Dependencies:")
    result = install_pkg_deps()
    if (result != 0):
        logging.error("main() Failed to install dependencies: %d." % result)

    result = install_pkg()
    if (result != 0):
        logging.error("main() Failed to install package: %d." % result)

    logging.info("\n\n" + log_highlighter + "\n\n")
    logging.info("Attempting to build package")
    result = build_package(True)
    logging.info("\n\n" + log_highlighter + "\n\n")

    if (result == 0):
        global warnings
        warnings = False
        logging.info("Starting to check package")
        check_result = check_package()
        buildbin_result = build_package(False)

        logging.info("\n\n" + log_highlighter + "\n\n")

        if buildbin_result == 0: # and check_result == 0:
            propagate_package()
            if (is_build_required):
                update_packages_file()
        if warnings: # todo separate build / check / build bin warnings
            body = "Build completed with warnings."
        else:
            body = "Build successful."

        send_message({
            "status": "normal_end",
            "body": body
        })
        logging.info("Normal build completion, %s." % body)



    logging.info("End of main function, onexit() should run next.")

#!/usr/bin/env python3

## Assume this script is started by a shell script which has read
## BBS variables and also changed to the correct directory.
import logging
import sys
from bioconductor.config import ENVIR

log_level = int(ENVIR['log_level_builder'])
logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=log_level)


logging.getLogger("stomp.py").setLevel(logging.DEBUG)

logging.info("log" + str(log_level))

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
import re
import urllib.request, urllib.error, urllib.parse
import requests
#from stomp.listener import PrintingListener
from stomp.listener import StatsListener
from urllib.error import URLError
from threading import Timer

# Modules created by Bioconductor
from bioconductor.communication import getNewStompConnection
from bioconductor.config import BUILDER_ID
from bioconductor.config import TOPICS

sys.path.append(ENVIR['bbs_home'])
sys.path.append(os.path.join(ENVIR['bbs_home'], "test", "python"))
import BBSutils
import bbs.parse

stomp = None
manifest = None
working_dir = None
packagebuilder_ssh_cmd = None
packagebuilder_scp_cmd = None
build_product = None
callcount = None
longBuild = None
pkg_type_views = None
gitclone_retcode = None

log_highlighter = "***************"

# Since we're modifying encoding in this function, it's important that we're consistent
# (as unicode) when attempting to write to the log file.
def send_message(msg, status=None):
    global stomp
    global manifest
    logging.debug("Attempting to send message: '{msg}'".format(msg=msg))
    merged_dict = {}
    merged_dict['builder_id'] = BUILDER_ID
    merged_dict['client_id'] = manifest['client_id']
    merged_dict['job_id'] = manifest['job_id']
    now = datetime.datetime.now()
    merged_dict['time'] = str(now)
    if type(msg) is dict:
        logging.debug("msg is dict")
        merged_dict.update(msg)
        if not ('status' in list(merged_dict.keys())):
            if not (status == None):
                merged_dict['status'] = status
    else:
        logging.debug("msg is NOT dict")
        merged_dict['body'] = msg
        if not (status == None):
            merged_dict['status'] = status

    if("body" in merged_dict):
        body = None
        try:
            body = str(merged_dict['body'], errors='replace')
        except TypeError:
            body = merged_dict['body']
        logging.debug("Final modified body: '{body}'".format(body=body))
        merged_dict['body'] = unicodedata.normalize('NFKD', body)
        logging.debug("Ascii encoded body: '{body}'".format(body=merged_dict['body']))

    logging.debug("Final merged_dict: '{merged_dict}'".format(merged_dict=merged_dict))
    json_str = json.dumps(merged_dict)
    logging.debug("JSON json_str: '{json_str}'".format(json_str=json_str))

    logging.debug("Sending message: %s" % json_str)
    stomp.send(destination=TOPICS['events'], body=json_str,
               headers={"persistent": "true"})
    logging.debug("send_message(): Message sent.")


def send_dcf_info(DESCRIPTION):
    try:
        maintainer = DESCRIPTION["Maintainer"]
    except KeyError:
        maintainer = "unknown"
    send_message({
        "status": "dcf_info",
        "package_name": DESCRIPTION["Package"],
        "maintainer": maintainer,
        "version": DESCRIPTION["Version"]
    })


def setup():
    global manifest
    global working_dir
    global packagebuilder_ssh_cmd, packagebuilder_rsync_cmd, \
        packagebuilder_rsync_rsh_cmd, packagebuilder_scp_cmd
    global callcount


    logging.info("Starting setup().")

    callcount = 1

    bbs_ssh_cmd = BBSutils.getenv('BBS_SSH_CMD')
    bbs_rsync_cmd = BBSutils.getenv('BBS_RSYNC_CMD')
    bbs_rsync_rsh_cmd = BBSutils.getenv('BBS_RSYNC_RSH_CMD')
    packagebuilder_ssh_cmd = bbs_ssh_cmd.replace(
        ENVIR['bbs_RSA_key'], ENVIR['spb_RSA_key'])
    packagebuilder_rsync_cmd = bbs_rsync_cmd.replace(
        ENVIR['bbs_RSA_key'], ENVIR['spb_RSA_key'])
    packagebuilder_rsync_rsh_cmd = bbs_rsync_rsh_cmd.replace(
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
            break
    time.sleep(1)
    manifest_fh = open(sys.argv[1], "rb")
    manifest_json = bbs.parse.bytes2str(manifest_fh.read())
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
    BBSLib = os.path.join(os.environ['BBS_R_HOME'], "site-library")

    if os.path.exists(BBSLib):
        AllLibs = expectedRLibsUser + os.pathsep + BBSLib + os.pathsep + sysLib
    else:
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


##def is_valid_url():

##    github_url = re.sub(r'\.git$', '', manifest['svn_url'])
##    logging.info("Checking valid github_url: " + github_url)
##    if not github_url.endswith("/"):
##        github_url += "/"
##    github_url += "master/DESCRIPTION"
##    github_url = github_url.replace("https://github.com",
##    "https://raw.githubusercontent.com")
###    logging.debug("Checking valid github_url: " + github_url)
##    response = requests.get(github_url)
##    # 1xx info 2xx success 3xx redirect 4xx client error 5xx server error
##    return response.status_code < 400


def get_node_info():
    logging.info("Node Info:")
    r_version = get_r_version()
    osys = BBSutils.getNodeSpec(BUILDER_ID, "OS")
    arch = BBSutils.getNodeSpec(BUILDER_ID, "Arch")
    plat = BBSutils.getNodeSpec(BUILDER_ID, "Platform")
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


def get_r_version():
    logging.info("BBS_R_CMD = %s" % ENVIR['bbs_R_cmd'])
    r_version_raw, stderr = subprocess.Popen([
        ENVIR['bbs_R_cmd'],"--version"
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
    r_version_raw = bbs.parse.bytes2str(r_version_raw)
    lines = r_version_raw.split("\n")
    r_version_line = lines[0]
    return r_version_line.replace("R version ", "")



def get_dcf_info():
    global svn_url_global
    svn_url_global = manifest['svn_url']
    package_name = manifest['job_id'].split("_")[0]
    logging.info("Starting get_dcf_info() '%s'." % package_name)

    github_url = package_name + "/DESCRIPTION"
    try:
        DESCRIPTION = bbs.parse.parse_DCF(github_url, merge_records=True)
        send_dcf_info(DESCRIPTION)
        desc_name = DESCRIPTION["Package"]
    except:
        logging.error("ERROR: get_dcf_info() failed\n  Could not open ",
                      github_url)
        send_message({
            "status": "build_complete",
            "retcode": 1,
            "warnings": False,
            "body": "get_dcf_info failed; could not open. ",
            "elapsed_time": "NA"})
        send_message({"status": "post_processing",
                      "retcode": 1,
                      "body": "get_dcf_info failed; could not open. "})
        sys.exit("Exiting get_dcf_info check failed")
    if package_name != desc_name:
        msg = "ERROR: Repository name: '" + package_name + \
        "' and DESCRIPTION Package: '" + desc_name + \
        "' do not match. "
        send_message({
            "status": "build_complete",
            "retcode": 1,
            "warnings": False,
            "body": msg,
            "elapsed_time": "NA"})
        send_message({"status": "post_processing",
                      "retcode": 1,
                      "body": msg})
        sys.exit("Exiting get_dcf_info check failed")



def git_clone():
    git_url = re.sub(r'\/$', '', manifest['svn_url'])
    if not git_url.endswith(".git"):
        git_url += ".git"
    git_cmd = "git clone %s --branch devel --single-branch --depth 1" % git_url
    send_message({"status": "git_cmd", "body": git_cmd})
    logging.info("git_clone command: " + git_cmd)
    send_message({"status": "preprocessing",
                  "retcode": 0,
                  "body": "Starting Git clone. "})
    retcode = subprocess.call(git_cmd, shell=True)
    logging.info("Finished git clone. \n git clone completed with status: " +  str(retcode))
    if (not retcode == 0):
        send_message({
            "status": "build_complete",
            "retcode": retcode,
            "warnings": False,
            "body": "Git clone Failed with status %d" % retcode,
            "elapsed_time": "NA"})
        send_message({"status": "post_processing",
                      "retcode": retcode,
                      "body": "Git clone Failed. "})

        sys.exit("git clone failed")
    else:
        send_message({"status": "post_processing",
                      "retcode": retcode,
                      "body": "Finished Git clone. "})
        send_message({"status": "git_result",
                      "result": retcode, "body": \
                      "git clone completed with status %d" % retcode})


def checkgitclone():
    package_name = manifest['job_id'].split("_")[0]
    pkg_git_clone = os.path.join(working_dir, package_name)

    r_cmd = os.path.join(os.path.dirname(ENVIR['bbs_R_cmd']), "Rscript")
    r_script = os.path.join(ENVIR['spb_home'], "BiocCheckGitCloneScript.R")
    cmd = "%s %s %s" % (r_cmd, r_script, pkg_git_clone)
    send_message({
        "body": "Checking Git Clone. ",
        "status": "preprocessing",
        "retcode": 0
    })
    logging.info("Command to check git clone:" + "\n  %s" % cmd)
    outfile = "CheckGitClone.out"
    if (os.path.exists(outfile)):
        os.remove(outfile)
    out_fh = open(outfile, "w")
    retcode = subprocess.call(cmd, stdout=out_fh, stderr=subprocess.STDOUT,
                               shell=True)
    out_fh.flush()
    out_fh.close()
    send_message({
        "body": "Checking git clone status: " + str(retcode) + ". ",
        "status": "post_processing",
        "retcode": retcode
    })
    logging.info("Finished Checking Git Clone of Package.\n completed with status: " + str(retcode))
    return retcode



def getPackageType():
    global longBuild
    global pkg_type_views
    package_name = manifest['job_id'].split("_")[0]
    DESCRIPTION_path = "%s/%s/DESCRIPTION" % (working_dir, package_name)
    DESCRIPTION = bbs.parse.parse_DCF(DESCRIPTION_path, merge_records=True)
    try:
        BiocType = DESCRIPTION["BiocType"]
    except KeyError:
        pass
        BiocType = "Software"
    pkg_type_views = BiocType
    BiocType = BiocType.lower()
    if (BiocType == "workflow"):
        longBuild = True
        pkg_type_views = "Workflow"
        logging.info("Package is a workflow.")
    elif (BiocType == "book"):
        longBuild = True
        pkg_type_views = "Book"
        logging.info("Package is a book.")
    elif (BiocType == "docker"):
        logging.info("Package is a docker container.")
        send_message({
            "status": "unsupported",
            "retcode": 0,
            "warnings": False,
            "body": "Docker Container",
            "elapsed_time": "NA"})
        send_message({"status": "post_processing",
                      "retcode": 0,
                      "body": "Docker Container. "})
        sys.exit("docker container")
    else:
        try:
            views = DESCRIPTION["biocViews"].replace(",", "")
            r_script = os.path.join(ENVIR['spb_home'], "getPackageType.R")
            rscript_dir = os.path.dirname(ENVIR['bbs_R_cmd'])
            rscript_binary = os.path.join(rscript_dir, "Rscript")
            cmd = "%s --vanilla --no-save --no-restore %s" % (rscript_binary, r_script)
            cmd = cmd + " " + views
            logging.info("Get Package Type command:\n" + cmd)
            pkg_type_views = subprocess.check_output(cmd, shell=True).decode()
            if (pkg_type_views == "ExperimentData"):
                longBuild = True
        except KeyError:
            pkg_type_views = "Software"

    send_message({
        "body": "Package type: " + pkg_type_views + ". ",
        "status": "post_processing",
        "retcode": 0
    })
    logging.info("Package is of type: " + pkg_type_views)
    logging.info("Package gets long build: " + str(longBuild))



def install_pkg_deps():
    package_name = manifest['job_id'].split("_")[0]
    DESCRIPTION_path = "%s/%s/DESCRIPTION" % (working_dir, package_name)
    DESCRIPTION = bbs.parse.parse_DCF(DESCRIPTION_path, merge_records=True)
    f = open("%s/%s/DESCRIPTION" % (working_dir, package_name), 'rb')
    description = bbs.parse.bytes2str(f.read())
    logging.info("DESCRIPTION file loaded for package '%s': \n%s", package_name, description)
    f.close()
    fields = ["Depends", "Imports", "Suggests", "Enhances", "LinkingTo"]
    args = ""
    for field in fields:
        try:
            args += '%s=@@%s@@; ' % (field, DESCRIPTION[field])
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
    install_name = package_name + ".install-out.txt"
    install_output_file = os.path.join(working_dir, install_name)
    
    r_cmd = ENVIR['bbs_R_cmd']
    lib_dir = os.path.join(package_dir, "R-libs")

    cmd = "%s CMD INSTALL --library=%s %s > %s 2>&1" % (r_cmd, lib_dir, pkg_git_clone, install_output_file)

    send_message({
        "body": "Installing package: " + package_name + ". ",
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
    logging.info("Finished Installing Package.\n completed with status: " +
        str(retcode))
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


def build_package(source_build):
    global pkg_type_views
    global longBuild
    global packagebuilder_scp_cmd

    pkg_type = BBSutils.getNodeSpec(BUILDER_ID, "pkgType")

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
            pkg_type = "mac.binary"
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
    flags = "--keep-empty-dirs --no-resave-data"

    if (source_build):
        package_name = manifest['job_id'].split("_")[0]
        r_cmd = "%s CMD build %s %s" % \
                    (ENVIR['bbs_R_cmd'], flags, package_name)
    else:
        if pkg_type == "mac.binary":
            libdir = "libdir"
            if os.path.exists(libdir):
                _call("rm -rf %s" % libdir, False)
            if (not (os.path.exists(libdir))):
                os.mkdir(libdir)
            r_cmd = os.environ['BBS_HOME'] + "/utils/build-universal.sh %s %s %s" % (
                get_source_tarball_name(),os.environ['BBS_R_CMD'],libdir)

    status = None
    if (source_build):
        status = "r_cmd"
        outfile = "R.out"
    else:
        status = "r_buildbin_cmd"
        outfile = "Rbuildbin.out"
    logging.debug("Before build, working dir is %s." %
                  working_dir)

    send_message({
        "body": "Starting Build package. ",
        "status": "preprocessing",
        "retcode": 0
    })
    start_time = datetime.datetime.now()
    if ((not source_build) and pkg_type == "win.binary"):
        retcode = win_buildbin(buildmsg)
    else:
        send_message({"status": status, "body": r_cmd})
        retcode = do_build(r_cmd, buildmsg, source_build)

    stop_time = datetime.datetime.now()
    time_dif = stop_time - start_time
    min_time, sec_time = divmod(time_dif.seconds,60)
    sec_time = str(format(float(str(time_dif).split(":")[2]), '.2f'))
    elapsed_time = str(min_time) + " minutes " + sec_time + " seconds"
    send_message({
        "body": "Build Package status: " + str(retcode) + ". ",
        "status": "post_processing",
        "retcode": retcode
    })

    # check for warnings
    out_fh = open(outfile, 'rb')
    warnings = False
    for line in out_fh:
        lineStr = bbs.parse.bytes2str(line)
        if lineStr.lower().startswith("warning:"):
            warnings = True
        if lineStr.lower().startswith("error:"):
            retcode = 1
    out_fh.close()

    # to catch windows timeout
    timeout_limit = int(ENVIR['timeout_limit'])
    if longBuild:
        timeout_limit = int(10800)
    if (timeout_limit <= time_dif.seconds):
        logging.info("Build time indicates TIMEOUT")
        retcode = -9

    tarname = get_source_tarball_name()
    if ((retcode == 0) and (source_build)):
        rawsize = os.path.getsize(tarname)
        sizeFile = rawsize/(1024*1024.0)
        # size for build report
        kib = rawsize / float(1024)
        filesize = "%.2f" % kib
        logging.info("Size: " + str(sizeFile))
        send_message({
            "body": "Determining package size complete: " + format(sizeFile,'.4f') + "MB. ",
            "status": "post_processing",
            "retcode": retcode,
            "filesize": filesize
        })
        url = "webadmin@master.bioconductor.org:/extra/www/bioc/spb_reports"
        scp_cmd = "%s %s %s/%s" % \
            (packagebuilder_scp_cmd, tarname, url, tarname)
        logging.info("Copying build product: " + scp_cmd)
        scp_code = 0
        if (not (tarname == None)):
            scp_code = subprocess.call(scp_cmd, shell=True)
        else:
            scp_code = -9
            tarname = ""
        send_message({
            "body": "Adding Build Product Information to Database.",
            "status": "post_processing",
            "retcode": scp_code,
            "build_product": tarname
        })


    complete_status = None
    if (source_build):
        complete_status = "build_complete"
    else:
        complete_status = "buildbin_complete"


    # build output printed entirely here
    # changed from interactively during build
    out_fh = open(outfile, "rb")
    out_str = bbs.parse.bytes2str(out_fh.read())
    out_fh.close()
    send_message({
        "status": buildmsg,
        "body": out_str
    })

    send_message({
        "status": complete_status,
        "retcode": retcode,
        "warnings": warnings,
        "body": "Build completed with status %d" % retcode,
        "elapsed_time": elapsed_time})
    logging.info(complete_status + "\n Build completed with status: " +
                 str(retcode) + " Elapsed time: " + elapsed_time)

    logging.info("Build output: \n" + out_str)

    # gave specific retcode to trigger warning but
    # still want to proceed with rest of build/check after reporting
    if (retcode == -4 or retcode == -6):
        retcode = 0

    return (retcode)


def do_build(cmd, message_stream, source):
    global longBuild
    if source:
        outfile = "R.out"
    else:
        outfile = "Rbuildbin.out"
    if (os.path.exists(outfile)):
        os.remove(outfile)
    out_fh = open(outfile, "w")
    out_fh.write("\n===============================\n\n R CMD BUILD\n\n===============================\n\n")
    out_fh.flush()

    logging.info("Starting do_build(); message {msgStream}.".format(msgStream= message_stream))
    logging.info("The working directory: {wd}".format(wd=os.getcwd()))
    logging.debug("The current environment variables: \n {envVars}".format(envVars=os.environ))
    logging.info("Build command: '{cmd}'.".format(cmd= cmd))

    timeout_limit = int(ENVIR['timeout_limit'])
    if longBuild:
        timeout_limit = int(10800)
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

    if (retcode == -9):
        out_fh.write(" ERROR\nTIMEOUT: R CMD build exceeded " +  str(min_time) + " mins\n\n\n")

    out_fh.flush()
    out_fh.close()
    return(retcode)


def win_buildbin(message_stream):
    logging.info("Starting win_buildbin")
    tarball = get_source_tarball_name()
    pkg = tarball.split("_")[0]
    libdir = "%s.buildbin-libdir" % pkg
    if (os.path.exists(libdir)):
        _call("rm -rf %s" % libdir, False)
    logging.debug("win_buildbin() Does %s exist? %s." %
                  (libdir, os.path.exists(libdir)))
    if not (os.path.exists(libdir)):
        os.mkdir(libdir)
    logging.debug("win_buildbin() After mkdir: does %s exist? %s" %
                  (libdir, os.path.exists(libdir)))
    time.sleep(1)
    cmd = "{R} CMD INSTALL --build --library={libdir} {tarball}".format(
            R=ENVIR['bbs_R_cmd'], libdir=libdir, tarball=tarball)

    send_message({"status": "r_buildbin_cmd", "body": cmd})

    return do_build(cmd, message_stream, False)


def check_package():
    send_message({"status": "starting_check", "body": ""})

    package_name = manifest['job_id'].split("_")[0]
    package_dir = os.path.dirname(working_dir)
    lib_dir = os.path.join(package_dir, "R-libs")
    install_name = package_name + ".install-out.txt"
    install_output_file = os.path.join(working_dir, install_name)

    tarball = get_source_tarball_name()
    pkg = tarball.split("_")[0]
  
 
    extra_flags = ""
    if (platform.system() == "Windows"):
        extra_flags = '--no-multiarch'

    cmdCheck = ('%s CMD check --no-vignettes --timings --library=%s --install=check:%s %s %s') % (ENVIR['bbs_R_cmd'], lib_dir, install_output_file, extra_flags, tarball)

    newpackage = True
    if ('newpackage' in manifest.keys()):
        newpackage = manifest['newpackage']

    r_cmd = os.path.join(os.path.dirname(ENVIR['bbs_R_cmd']), "Rscript")
    r_script = os.path.join(ENVIR['spb_home'], "BiocCheckScript.R")
    cmdBiocCheck = "%s %s %s %s" % (r_cmd, r_script, tarball, newpackage)

    package_name = manifest['job_id'].split("_")[0]
    cmdMessage = "BiocCheckGitClone('" + package_name + "')  &&  " + cmdCheck + "  &&  BiocCheck('" + tarball + "',  `new-package`=TRUE)"

    send_message({"status": "check_cmd", "body": cmdMessage})
    send_message({
        "body": "Starting Check package. ",
        "status": "preprocessing",
        "retcode": 0
    })
    logging.info("R Check Command:\n" + cmdCheck)
    logging.info("R BiocCheck Command:\n" + cmdBiocCheck)

    retcode = do_check(cmdCheck, cmdBiocCheck)
    logging.info("do_check result: " + str(retcode))
    if (retcode == -4):
        send_message({
            "body": "WARNING: check time exceeded 10 min. ",
            "status": "post_processing",
            "retcode": retcode
        })
    else:
        send_message({
            "body": "Checking Package status: " + str(retcode) + ". ",
            "status": "post_processing",
            "retcode": retcode
        })

    return (retcode)


def do_check(cmdCheck, cmdBiocCheck):
    global longBuild
    global pkg_type_views
    global gitclone_retcode
    outfile = "Rcheck.out"
    package_name = manifest['job_id'].split("_")[0]
    if (os.path.exists(outfile)):
        os.remove(outfile)

    send_message({
        "status": "write_gitclone",
        "body": "writing bioccheckgitclone results"
    })
    out_fh = open(outfile, "w")
    out_fh.write("\n===============================\n\n BiocCheckGitClone('" + package_name + "')\n\n===============================\n\n")
    # copy BiocCheckGitClone results
    gitcheckfile = open("CheckGitClone.out")
    for line in gitcheckfile:
        out_fh.write(line)
    gitcheckfile.close()
    out_fh.write("\n\n\n")
    send_message({
        "status": "r_check",
        "body": "starting R CMD check"
    })
    out_fh.write("\n===============================\n\n R CMD CHECK\n\n===============================\n\n")
    out_fh.flush()

    timeout_limit = int(ENVIR['timeout_limit'])
    if longBuild:
        timeout_limit = int(10800)
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
    time_dif = stop_time - start_time
    min_time, sec_time = divmod(time_dif.seconds,60)
    sec_time = str(format(float(str(time_dif).split(":")[2]), '.2f'))
    elapsed_time = str(min_time) + " minutes " + sec_time + " seconds"

    logging.info("The timeout_limit is: " + str(timeout_limit))

    if ((600 <= time_dif.seconds) & (pkg_type_views == "Software")):
        logging.info("Build time indicates longer than 10 min requirement")
        warntime = 10
        retcode1 = -4

    if (timeout_limit <= time_dif.seconds):
        logging.info("Build time indicates TIMEOUT")
        retcode1 = -9

    out_fh.flush()
    if (retcode1 == -9):
        out_fh.write(" ERROR\nTIMEOUT: R CMD check exceeded " + str(min_time) + " mins\n\n\n")
        out_fh.flush()

    if (retcode1 == -4):
        out_fh.write(" WARNING: R CMD check exceeded " + str(warntime) +" min requirement\n\n\n")
        out_fh.flush()


    out_fh.flush()
    out_fh.write("\n\n\n")
    send_message({
        "status": "bioc_check",
        "body": "starting BiocCheck"
    })
    out_fh.write("\n===============================\n\n BiocCheck('" + cmdCheck.split(" ")[-1] + "')\n\n===============================\n\n")
    out_fh.flush()

    start_time2 = datetime.datetime.now()
    pope2 = subprocess.Popen(cmdBiocCheck, stdout=out_fh,
                             stderr=subprocess.STDOUT, shell=True)
    my_timer = Timer(timeout_limit, kill, [pope2])
    try:
        my_timer.start()
        retcode2 = pope2.wait()
    finally:
        my_timer.cancel()

    stop_time2 = datetime.datetime.now()
    time_dif2 = stop_time2 - start_time2
    min_time2, sec_time2 = divmod(time_dif2.seconds,60)
    sec_time2 = str(format(float(str(time_dif2).split(":")[2]), '.2f'))
    elapsed_time2 = str(min_time2) + " minutes " + sec_time2 + " seconds"
    if (timeout_limit <= time_dif2.seconds):
        logging.info("Build time indicates TIMEOUT")
        retcode2 = -9

    out_fh.flush()
    if (retcode2 == -9):
        out_fh.write(" ERROR\nTIMEOUT: BiocCheck exceeded " +  str(min_time2) + "mins\n\n\n")

    out_fh.flush()
    out_fh.close()

    # check for warnings from R CMD check/BiocCheck
    out_fh = open(outfile, 'rb')
    warnings = False
    for line in out_fh:
        lineStr = bbs.parse.bytes2str(line)
        if lineStr.rstrip().endswith("WARNING") or \
             "* WARNING:" or "! WARNING" in lineStr:
            warnings = True
            break
    out_fh.close()

    logging.info("retcode1: " + str(retcode1))
    logging.info("retcode2: " + str(retcode2))

    if (retcode1 == 0 and retcode2 == 0 and gitclone_retcode == 0):
        retcode = 0
    elif (retcode1 == -4 and retcode2 == 0 and gitclone_retcode == 0):
        retcode = -4
    elif (retcode1 == -9 or retcode2 == -9):
        retcode = -9
    else:
        retcode = 1

    logging.info("retcode: " + str(retcode))

    send_message({
        "status": "check_complete",
        "retcode": retcode,
        "warnings": warnings,
        "body": "Check completed",
        "elapsed_time": elapsed_time})

    logging.info("Check Complete\n R CMD check completed with status: " +
                 str(retcode1) + " Elapsed time: " + elapsed_time +
                 ". \n BiocCheck completed with status: " +
                 str(retcode2)+ " Elapsed time: " + elapsed_time2)

    out_fh = open(outfile, "rb")
    out_str = bbs.parse.bytes2str(out_fh.read())
    out_fh.close()
    logging.info("Check output: \n" + out_str)
    send_message({
        "status": "checking",
        "body": out_str
    })
    return (retcode)


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


def isUnsupported(mySys, key):
    package_name = manifest['job_id'].split("_")[0]
    unsupport = bbs.parse.get_BBSoption_from_pkgsrctree(package_name,
                                          "UnsupportedPlatforms")
    if (unsupport is not None):
        unsupport = [x.strip().lower() for x in unsupport.split(",")]
        return (((platform.system() == mySys) and (key in unsupport)))
    else:
        return (False)

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

##    if not is_valid_url():
##        send_message({"status": "preprocessing",
##            "retcode": -1,
##            "body": "Invalid Github URL"})
##        send_message({
##            "status": "invalid_url",
##            "body": "Invalid Github url."
##        })
##        logging.error("main() Invalid Github url.")
##        sys.exit("invalid github url")

    get_node_info()
    logging.info("\n\n" + log_highlighter + "\n\n")

    git_clone()
    get_dcf_info()
    logging.info("\n\n" + log_highlighter + "\n\n")

    exitOut = False
    if ((isUnsupported(platform.system(), BUILDER_ID)) or
       (isUnsupported("Linux","linux")) or (isUnsupported("Darwin","mac")) or
       (isUnsupported("Windows","win"))):
            exitOut = True

    if (exitOut):
        logging.info("Unsupported Platform.")
        send_message({
            "status": "unsupported",
            "retcode": 0,
            "warnings": False,
            "body": "Unsupported Platform",
            "elapsed_time": "NA"})
        send_message({"status": "post_processing",
                      "retcode": 0,
                      "body": "Unsupported Platform. "})
        sys.exit("unsupported platform")
    else:
        logging.info("Initial Platform Check Passed.")


    logging.info("\n\n" + log_highlighter + "\n\n")
    logging.info("Checking package type")
    getPackageType()
    logging.info("\n\n" + log_highlighter + "\n\n")

    logging.info("\n\n" + log_highlighter + "\n\n")
    logging.info("Installing Package Dependencies:")
    result = install_pkg_deps()
    if (result != 0):
        logging.error("main() Failed to install dependencies: %d." % result)

    logging.info("\n\n" + log_highlighter + "\n\n")
    logging.info("Checking Git Clone of Package")
    gitclone_retcode = checkgitclone()
    logging.info("\n\n" + log_highlighter + "\n\n")

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

        send_message({
            "status": "post_processing_complete",
            "retcode": 0,
            "body": "Post-processing complete."})

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

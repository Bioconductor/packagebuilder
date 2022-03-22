
####################################
##
##  workers/server.py
##
####################################

import time
import sys
import json
import os
import subprocess
import uuid
import stomp
import logging
import threading
import socket
import requests
from datetime import datetime
from urllib.error import URLError
from bioconductor.config import ENVIR
from bioconductor.config import TOPICS
from bioconductor.config import BUILDER_ID
from bioconductor.communication import getNewStompConnection


example_json = '{"job_id":"spbtest3_20220311133725","time":"Fri Mar 11 2022 13:37:25 GMT-0800 (UTC)","client_id":"single_package_builder_github:51:spbtest3","force":true,"bioc_version":"3.15","r_version":"4.2","svn_url":"https://git.bioconductor.org/packages/spbtest3","repository":"scratch","commit_id":"d148999ba9d931fc5ae41c10a36ee147da9c3a86","newpackage":true}'


received_obj = json.loads(example_json)

job_id = received_obj['job_id']
job_base = received_obj['client_id'].rsplit(":")[1]
bioc_version = received_obj['bioc_version']
job_dir = os.path.join(ENVIR['spb_home'], "jobs")
if not os.path.exists(job_dir):
    os.mkdir(job_dir)


    
job_dir_main = os.path.join(job_dir, job_base)
if not os.path.exists(job_dir_main):
    os.mkdir(job_dir_main)


    
r_libs_dir = os.path.join(job_dir_main, "R-libs")
if not os.path.exists(r_libs_dir):
    os.mkdir(r_libs_dir)


    
url_name = received_obj['svn_url'].split("/")
url_user = url_name[3]
url_pkg = url_name[4]

if ('commit_id' in list(received_obj.keys())):
    run_dir = received_obj['commit_id']
else:
    run_dir = job_id

    
job_dir = os.path.join(job_dir_main, run_dir)
if not os.path.exists(job_dir):
    os.mkdir(job_dir)

    
jobfilename = os.path.join(ENVIR['spb_home'], job_dir,
                           "manifest.json")

body = example_json
jobfile = open(jobfilename, "w")
jobfile.write(body)
jobfile.close()

os.environ['SPB_HOME'] = ENVIR['spb_home']
os.environ['BBS_HOME'] = ENVIR['bbs_home']
os.environ['BBS_SSH_CMD'] = ENVIR['bbs_ssh_cmd'] + " -qi " + ENVIR['bbs_RSA_key'] + " -o StrictHostKeyChecking=no"
os.environ['BBS_R_HOME'] = ENVIR['bbs_R_home']
os.environ['BBS_R_CMD'] = ENVIR['bbs_R_cmd']
os.environ['BBS_BIOC_VERSION'] = ENVIR['bbs_Bioc_version']
os.environ['BBS_RSYNC_CMD'] = ENVIR['bbs_rsync_cmd']
os.environ['BBS_RSYNC_RSH_CMD'] = os.environ.get('BBS_RSYNC_CMD') + " -e " + os.environ.get('BBS_SSH_CMD')
os.environ['BBS_MODE'] = ENVIR['bbs_mode']
os.environ['BBS_BIOC_VERSIONED_REPO_PATH'] = os.environ.get('BBS_BIOC_VERSION') + "/" + os.environ.get('BBS_MODE')
os.environ['BBS_STAGE2_R_SCRIPT'] = os.environ.get('BBS_HOME') + "/" + os.environ.get('BBS_BIOC_VERSIONED_REPO_PATH') + "/STAGE2.R"
os.environ['BBS_NON_TARGET_REPOS_FILE'] = os.environ.get('BBS_HOME') + "/" + os.environ.get('BBS_BIOC_VERSIONED_REPO_PATH') + "/non_target_repos.txt"
os.environ['BBS_CENTRAL_RHOST'] = ENVIR['bbs_central_rhost']
os.environ['BBS_CENTRAL_RUSER'] = ENVIR['bbs_central_ruser']
os.environ['BBS_CENTRAL_RDIR'] = "/home/" +  os.environ.get('BBS_CENTRAL_RUSER') + "/public_html/BBS/" + os.environ.get('BBS_BIOC_VERSIONED_REPO_PATH')
os.environ['BBS_CENTRAL_BASEURL'] = "http://" + os.environ.get('BBS_CENTRAL_RHOST') + "/BBS/" + os.environ.get('BBS_BIOC_VERSIONED_REPO_PATH')
os.environ['BBS_CURL_CMD'] =  ENVIR['bbs_curl_cmd']
os.environ['LANG'] = ENVIR['bbs_lang']
os.environ['R_CHECK_ENVIRON']=ENVIR['r_check_environ']
os.environ['BIOC_DEVEL_PASSWORD'] = ENVIR['bioc_devel_password']


## shell_cmd = ["python", "-m", "workers.builder", jobfilename, bioc_version]

sys.argv = ["workers.builder",jobfilename, bioc_version]


####################################
##
##  workers/builder.py
##
####################################


import logging
import sys
from bioconductor.config import ENVIR
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


## loriBuilder.py is copy of builder.py
## removes main and disables send.stomp in send_message
## allows functions to be defined/called
builderfile = open("loriBuilder.py")
exec(builderfile.read())
builderfile.close()

####################
##
## From main
##
####################

setup()
#setup_stomp()

#if (manifest['bioc_version'] != ENVIR['bbs_Bioc_version']):
#    print("Not passed biocversion")

#if not is_valid_url():
#    print("Not passed url")

get_node_info()
git_clone()
get_dcf_info()

########################################################
##
## Come back to clean up unsupported section in main 
##
########################################################


getPackageType()
result = install_pkg_deps()
if (result != 0):
    print("Not passed install deps")

gitclone_retcode = checkgitclone()

result = install_pkg()
if (result != 0):
   print("Not passed install itself")

result = build_package(True)

global warnings
warnings = False
check_result = check_package()
buildbin_result = build_package(False)

/build_pa

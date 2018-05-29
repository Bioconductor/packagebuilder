#
# make cron job to run once a day.
#

import os
import json
from urllib2 import Request, urlopen, URLError
import requests
from bioconductor.config import ENVIR
import logging
import datetime
import subprocess

logging.basicConfig(filename='cleanUpIssues.log',level=logging.INFO)

# max item limit of 100 - so must run fairly frequently
cmd = "https://api.github.com/repos/Bioconductor/Contributions/issues?state=closed&per_page=100"

#request = Request(cmd)
#response = urlopen(request)
#res = response.read()
res = requests.get(cmd)
git_dir = json.loads(res.text)

issue_nums = set()
close_nums = set()

for k in git_dir:
    closing_date = k['closed_at']
    diff_date = datetime.datetime.today() - datetime.datetime.strptime(closing_date, '%Y-%m-%dT%H:%M:%SZ')
    if diff_date.days > 30:
        issue_nums.add(k['number'])
    else:
        close_nums.add(k['number'])

job_dir = os.path.join(ENVIR['spb_home'], "jobs")
for issue_name in list(issue_nums):
    pkg_rm = os.path.join(job_dir, str(issue_name))
    if os.path.exists(pkg_rm):
        logging.info("Removing " + pkg_rm)
        #os.system("rm -rf " + pkg_rm)
        cmd = "rm -rf " + pkg_rm
        try:
            retcode = subprocess.call(cmd, shell=True)
        except:
            logging.error("Remove of package " + pkg_rm + " Failed")
    else:
        logging.debug("Issue " + pkg_rm + " Not Found")


def sorted_ls(path):
    mtime = lambda f: os.stat(os.path.join(path, f)).st_mtime
    return list(sorted(os.listdir(path), key=mtime))

job_dir = os.path.join(ENVIR['spb_home'], "jobs")
for issue_name in list(close_nums):
    pkg_rm = os.path.join(job_dir, str(issue_name))
    if os.path.exists(pkg_rm):
        order_list = sorted_ls(pkg_rm)
        order_list = filter(lambda a: a != 'R-libs', order_list)
        temp = order_list.pop()
        for subdir in order_list:
            newpath = os.path.join(pkg_rm, subdir)
            cmd = "rm -rf " + newpath
            try:
                retcode = subprocess.call(cmd, shell=True)
            except:
                logging.error("Remove of package " + newpath + " Failed")
    else:
        logging.debug("Issue " + pkg_rm + " Not Found")

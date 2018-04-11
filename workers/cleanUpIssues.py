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

for k in git_dir:
    # only issues closed for more than 30 days
    closing_date = k['closed_at']
    diff_date = datetime.datetime.today() - datetime.datetime.strptime(closing_date, '%Y-%m-%dT%H:%M:%SZ')
    if diff_date.days > 30:
        issue_nums.add(k['number'])


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

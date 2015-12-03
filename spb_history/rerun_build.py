#!/usr/bin/env python

# '{"force": true, "job_id": "RnaSeqSampleSizeData_20141016222857",
# "repository": "scratch",
#"bioc_version": "3.0",
# "svn_url": "https://tracker.bioconductor.org/file4746/RnaSeqSampleSizeData_0.99.0.tar.gz",
#"r_version": "3.1",
# "client_id": "single_package_builder_autobuild:1061:RnaSeqSampleSizeData_0.99.0.tar.gz",
# "time": "Thu Oct 16 2014 22:28:57 GMT-0700 (PST)"}'

import json
import sys
import datetime
from pytz import timezone
from stompy import Stomp
import logging
# Modules created by Bioconductor
from bioconductor.config import BROKER
from bioconductor.config import BIOC_R_MAP
from bioconductor.config import BIOC_VERSION

logging.basicConfig(format='%(levelname)s: %(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.DEBUG)

if (len(sys.argv) != 3):
    logging.info("usage: %s <issue_id> <tracker_tarball_url>" % sys.argv[0])
    sys.exit(1)

pacific = timezone("US/Pacific")
now0 = datetime.datetime.now()
tzname = pacific.tzname(now0)
if tzname == "PDT":
    offset = "0700"
else: # PST
    offset = "0800"

obj = {}
issue_id = sys.argv[1]
url = sys.argv[2]
segs = url.split("/")
pkgname = segs[4]
pkgname_bare = pkgname.split("_")[0]

obj['force']  = True
obj['bioc_version'] = BIOC_VERSION
obj['r_version'] = BIOC_R_MAP[BIOC_VERSION]
obj['svn_url'] = url
obj['repository'] = 'scratch'
now = pacific.localize(now0)
timestamp1 = now.strftime("%Y%m%d%H%M%S")
timestamp2 = now.strftime("%a %b %d %Y %H:%M:%S")
timestamp2 = timestamp2 + " GMT-%s (%s)" % (offset, tzname)
obj['job_id'] = "%s_%s" % (pkgname_bare, timestamp1)
obj['time'] = timestamp2
obj['client_id'] = "single_package_builder_autobuild:%s:%s" % (issue_id, pkgname)

json = json.dumps(obj)


#print(json)
logging.info("Attempting to connect to Stomp server: '%s:%s'", BROKER['host'], BROKER['port'])
try:
    stomp = Stomp(BROKER['host'], BROKER['port'])
    # optional connect keyword args "username" and "password" like so:
    # stomp.connect(username="user", password="pass")
    stomp.connect()
    logging.info("Connection established.")
except:
    logging.info("Cannot connect")
    raise

this_frame = stomp.send({'destination': "/topic/buildjobs",
  'body': json,
  'persistent': 'true'})
logging.info("Receipt: %s" % this_frame.headers.get('receipt-id'))

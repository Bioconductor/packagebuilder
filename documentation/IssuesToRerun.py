# coding=utf-8

import json
from urllib2 import Request, urlopen, URLError
import requests
import datetime


# change date to a date close to (before) the SPB crashed

cmd = "https://api.github.com/repos/Bioconductor/Contributions/issues?state=open&per_page=100&since=2019-06-16T00:00:00"


# commented out code was when there could be more than 100 open issues
# because we use since and only expect a day or two for failures, don't need to
# loop over pages - if for some reason more than 100 than implement loop (python
# uses indentation to determine code chunks so if implemented adjust indentation)


issue_rerun = []

#count=1
#while count <= 1:
#    print(count)
#cmd=cmd+"&page="+str(count)

request = Request(cmd)
response = urlopen(request)
res = response.read()
git_dir = json.loads(res)
for k in git_dir:
    issue_rerun.append(k['html_url'])

#count +=1

for i in issue_rerun:
    print(i)


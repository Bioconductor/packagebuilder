# This script assumes it is in the top level directory of the django project.
import os
import sys
path = os.path.abspath(os.path.dirname(sys.argv[0]))
segs = path.split("/")
segs.pop()
path =  "/".join(segs)
sys.path.append(path)
os.environ['DJANGO_SETTINGS_MODULE'] = 'spb_history.settings'
from spb_history.viewhistory.models import Package
print Package.objects.count()


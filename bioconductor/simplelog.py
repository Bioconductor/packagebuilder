import datetime
import sys

# TODO: Replace with a logging framework
def logMsg(msg):
    print "[%s] %s" % (datetime.datetime.now(), msg)
    sys.stdout.flush()

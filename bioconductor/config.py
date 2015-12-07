# A simple configuration module to reduce duplication.  Settings will be loaded
# dynamically next.

import os
import platform
import logging
import ConfigParser

logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.DEBUG)

logging.info("Loading configuration")

globalConfigParser = ConfigParser.RawConfigParser()
globalConfigParser.read(os.path.join(os.getcwd(),'spb.properties'))
SPB_ENVIRONMENT = globalConfigParser.get('Environment', 'environment');

envSpecificConfigParser = ConfigParser.RawConfigParser()
if (SPB_ENVIRONMENT == "production"):
    logging.info("Working in production")
    envSpecificConfigParser.read(os.path.join(os.getcwd(),'production.properties'))
else:
    logging.info("Working in development")
    envSpecificConfigParser.read(os.path.join(os.getcwd(),'development.properties'))

BUILD_NODES = envSpecificConfigParser.get('Properties', 'builders').split(",")
BROKER = {
    "host": envSpecificConfigParser.get('Properties', 'stomp.host'),
    "port": int(envSpecificConfigParser.get('Properties', 'stomp.port'))
}
logging.info("The builds nodes enabled are: '%s'", BUILD_NODES)
ACTIVEMQ_USER=  envSpecificConfigParser.get('Properties', 'activemq.username') #.rstrip('\n')
ACTIVEMQ_PASS = envSpecificConfigParser.get('Properties', 'activemq.password') #.rstrip('\n')

BIOC_VERSION = globalConfigParser.get('UniversalProperties', 'bbs.bioc.version')

# TODO: Consider a better way to determine this
BIOC_R_MAP = {"2.7": "2.12", "2.8": "2.13", "2.9": "2.14",
    "2.10": "2.15", "2.14": "3.1", "3.0": "3.1",
    "3.1": "3.2", "3.2": "3.2", "3.3": "3.3"}

BUILDER_ID = platform.node().lower().replace(".fhcrc.org","")
BUILDER_ID = BUILDER_ID.replace(".local", "")

ENVIR = {
    'bbs_home': envSpecificConfigParser.get('Properties', 'bbs.home'),
    'bbs_R_home': envSpecificConfigParser.get('Properties', 'bbs.r.home'),
    'bbs_node_hostname': BUILDER_ID,
    'bbs_R_cmd': envSpecificConfigParser.get('Properties', 'bbs.r.cmd'),
    'bbs_Bioc_version': BIOC_VERSION,

    'packagebuilder_home': envSpecificConfigParser.get('Properties', 'packagebuilder.workers.directory'),

    'bbs_RSA_key': envSpecificConfigParser.get('Properties', 'bbs.rsa.key'),
    'packagebuilder_RSA_key': envSpecificConfigParser.get('Properties', 'spb.rsa.key'),
    'svn_user': envSpecificConfigParser.get('Properties', 'svn.user'),
    'svn_pass': envSpecificConfigParser.get('Properties', 'svn.user'),
    'tracker_user': envSpecificConfigParser.get('Properties', 'tracker.user'),
    'tracker_pass': envSpecificConfigParser.get('Properties', 'tracker.pass')
}

TOPICS = {
    "jobs": "/topic/buildjobs",
    "events": "/topic/builderevents"
}

HOSTS = {
    'svn': 'https://hedgehog.fhcrc.org',
    'tracker': 'https://tracker.bioconductor.org',
    'bioc': 'https://bioconductor.org'
}


logging.info("Finished loading configuration.")

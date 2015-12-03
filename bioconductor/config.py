# A simple configuration module to reduce duplication.  Settings will be loaded
# dynamically next.

import os
import logging
import ConfigParser

logging.basicConfig(format='%(levelname)s: %(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.DEBUG)

logging.info("Loading configuration")

globalConfigParser = ConfigParser.RawConfigParser()
globalConfigParser.read(os.path.join(os.getcwd(),'spb.properties'))
environment = globalConfigParser.get('Environment', 'environment');

envSpecificConfigParser = ConfigParser.RawConfigParser()
if (environment == "production"):
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


BIOC_VERSION = "3.3"

# TODO: Consider a better way to determine this
BIOC_R_MAP = {"2.7": "2.12", "2.8": "2.13", "2.9": "2.14",
    "2.10": "2.15", "2.14": "3.1", "3.0": "3.1",
    "3.1": "3.2", "3.2": "3.2", "3.3": "3.3"}

ENVIR = {
    'bbs_home': "/home/mtmorgan/a/BBS",
    'bbs_R_home': "",
    'bbs_node_hostname': "hp-zb",
    'bbs_R_cmd': "/home/mtmorgan/bin/R-devel/bin/R",
    'bbs_Bioc_version': "3.3",

    'packagebuilder_home': "/home/mtmorgan/a/packagebuilder/workers",

    'bbs_RSA_key': os.getenv("BBS_RSAKEY"),
    'packagebuilder_RSA_key': os.getenv("PACKAGEBUILDER_RSAKEY"),
    'svn_user': os.getenv("SVN_USER"),
    'svn_pass': os.getenv("SVN_PASS"),
    'tracker_user': os.getenv("TRACKER_USER"),
    'tracker_pass': os.getenv("TRACKER_PASS")
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

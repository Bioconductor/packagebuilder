import datetime
import logging
import mechanize
import sys


logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.INFO)
                    
logging.debug("The module search path is: \n%s", sys.path)

from stompy import Stomp as oldStompConstructor
import stomp

# Modules created by Bioconductor
from bioconductor.config import ACTIVEMQ_USER
from bioconductor.config import ACTIVEMQ_PASS
from bioconductor.config import BROKER
from bioconductor.config import SPB_ENVIRONMENT
         

stompHost = BROKER['host']
stompPort = BROKER['port']

def getOldStompConnection():
    try:
        logging.debug("Attempting to open connection to ActiveMQ at '%s:%s'.",
            stompHost,stompPort)
        # Connect using the old model
        stompClient = oldStompConstructor(stompHost, stompPort)
        if (SPB_ENVIRONMENT == "production"):
            logging.debug("Not attempting authentication")
            stompClient.connect()
        else:
            logging.debug("Attempting authentication with user: '%s'.", ACTIVEMQ_USER)
            stompClient.connect(username=ACTIVEMQ_USER, password=ACTIVEMQ_PASS)
        logging.debug("Stomp connection established.")
    except:
        logging.error("Cannot connect to Stomp at '%s:%s'.", stompHost, stompPort)
        raise
    
    return stompClient

def getNewStompConnection(listenerName, listenerObject):
    try:
        logging.debug("Attempting to open connection to ActiveMQ at '%s:%s'.",
            stompHost, stompPort)
        stompClient = stomp.Connection([(stompHost, stompPort)])
        
        stompClient.set_listener(listenerName, listenerObject)
        stompClient.start()
                
        if (SPB_ENVIRONMENT == "production"):
            logging.debug("Not attempting authentication")
            stompClient.connect()
        else:
            logging.debug("Attempting authentication with user: '%s'.", ACTIVEMQ_USER)
            stompClient.connect(username=ACTIVEMQ_USER, password=ACTIVEMQ_PASS)
        logging.debug("Stomp connection established.")
    except:
        logging.error("Cannot connect to Stomp at '%s:%s'.", stompHost, stompPort)
        raise
    
    return stompClient

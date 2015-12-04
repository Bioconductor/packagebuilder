import datetime
import logging
import stomp
from stompy import Stomp
import sys

# Modules created by Bioconductor
from bioconductor.config import ACTIVEMQ_USER
from bioconductor.config import ACTIVEMQ_PASS
from bioconductor.config import BROKER
from bioconductor.config import SPB_ENVIRONMENT

logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.DEBUG)            

stompHost = BROKER['host']
stompPort = BROKER['port']

def getOldStompConnection():
    try:
        logging.info("Attempting to open connection to ActiveMQ at '%s:%s'.",
            stompHost,stompPort)
        # Connect using the old model
        stompClient = Stomp(stompHost, stompPort)
        if (SPB_ENVIRONMENT == "production"):
            logging.info("Not attempting authentication")
            stompClient.connect()
        else:
            logging.info("Attempting to connect with user: '%s' and pass: '%s'",
                    ACTIVEMQ_USER, ACTIVEMQ_PASS)
            stompClient.connect(username=ACTIVEMQ_USER, password=ACTIVEMQ_PASS)
        logging.info("Stomp connection established.")
    except:
        logging.error("Cannot connect to %s.", stompHost)
        raise
    
    return stompClient

def getNewStompConnection(listenerName, listenerObject):
    try:
        logging.info("Attempting to open connection to ActiveMQ at '%s:%s'.",
            stompHost,stompPort)
        stompClient = stomp.Connection([(stompHost, stompPort)])
        
        stompClient.set_listener(listenerName, listenerObject)
        stompClient.start()
                
        if (SPB_ENVIRONMENT == "production"):
            logging.info("Not attempting authentication")
            stompClient.connect()
        else:
            logging.info("Attempting to connect with user: '%s' and pass: '%s'",
                    ACTIVEMQ_USER, ACTIVEMQ_PASS)
            stompClient.connect(username=ACTIVEMQ_USER, password=ACTIVEMQ_PASS)
        logging.info("Stomp connection established.")
    except:
        logging.error("Cannot connect to %s.", stompHost)
        raise
    
    return stompClient

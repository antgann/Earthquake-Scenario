#!/usr/bin/env python

"""ScenarioAMQProcessor parses eqinfo2GM messages, builds CAP XML, and returns the file."""

import collections
import logging
import time
import sys
import stomp

from xml.etree import ElementTree as ET
from configparser import ConfigParser
from pathlib import Path
from datetime import datetime
from datetime import timedelta
from django.conf import settings

class ScenarioAMQProcessor:

    """ScenarioAMQProcessor
    Provides means to send files to ActiveMQ for EEW Scenario application
    """

    def __init__(self, AMQValues):
        config = ConfigParser()
        config.read(settings.EEWSCENARIO_FOLDER + 'EEWScenarioConfig.cfg')

        currentDate = time.strftime("%d%m%Y")
        self.logger = logging.getLogger('EEWScenario')

        self.AMQServer = config.get("AMQ",'AMQServer')
        self.AMQSTOMPPort = config.get("AMQ",'AMQSTOMPPort')

        self.fileLocation = AMQValues.get("fileLocation")

        self.nextEventIDLocation = config.get("FILES",'nextEventIDLocation')
        self.nextEventID = ""
        with open(self.nextEventIDLocation, 'r') as nextEventIDFile:
            self.nextEventID=nextEventIDFile.read().strip()

        self.userID = AMQValues.get("userID")
        self.passwd = AMQValues.get("passwd")
        self.topicName = "/topic/" + AMQValues.get("topicName")
        encoding = AMQValues.get("encoding")
        if encoding == "bytesMessage":
            self.outBytes = True
        else:
            self.outBytes = False


    def parseEEW(self):
        """If an EEW file is provided, parse the values for the message file locations
        as well as the time delays between sends.
        """
        if not self.fileLocation.endswith(".eew"):   # it's a single alert message, parsing isn't needed
            return {0: (5000, self.fileLocation)}   # give it a five second delay from origin time by default

        parentDir = str(Path(self.fileLocation).parent) + "/"
        EEWDict = collections.OrderedDict()
        EEWFile = open(self.fileLocation,'r')
        lines = EEWFile.readlines()
        lastTimestamp = 0
#        counter = 0
        try:
            for line in lines:
                x = line.split(" ")
                if lastTimestamp == 0:
                    sleepTime = 0
                else:
                    sleepTime = int(x[0]) - lastTimestamp
                fileLocation = parentDir + (x[1].strip())
                with open(fileLocation,'r') as input_xml:
                    tree = ET.parse(input_xml)
                root = tree.getroot()
                counter = root.get('version')
                EEWDict[counter] = (sleepTime, fileLocation)
                lastTimestamp = int(x[0])
#                counter = counter + 1
        except Exception as e:
            print(str(e))
            self.logger.error(str(e))
        return EEWDict

    def sendAMQwithSTOMP(self, EEWDict):
        """Sets up a connection to the ActiveMQ server via STOMP protocol,
        sends message(s) based on input delay key values in the EEWDict
        """
        if self.outBytes:  # output will be bytesMessage
            conn = stomp.Connection([(self.AMQServer,int(self.AMQSTOMPPort))], use_ssl=True)
        else:   # output will be textMessage
            conn = stomp.Connection([(self.AMQServer,int(self.AMQSTOMPPort))], use_ssl=True, auto_content_length=False)
        try:
            conn.start()
            conn.connect(self.userID, self.passwd, wait=True)
            timeNow = datetime.utcnow()
            originTime = timeNow.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            for key, value in EEWDict.items():
                sleepDelta = value[0]
                fileLocation = value[1]
                self.logger.info("sleepDelta: " + str(sleepDelta) + "  fileLoc: " + fileLocation)
                with open(fileLocation,'r') as input_xml:
                    tree = ET.parse(input_xml)
                root = tree.getroot()

                # NOTE: this is to mimic the ARC's protocol of sending follow-up
                version = root.get('version')
                if version == '900':
                    conn.disconnect()
                    conn = stomp.Connection([(self.AMQServer,int(self.AMQSTOMPPort))], use_ssl=True)
                    conn.connect(self.userID, self.passwd, wait=True)

                timeStamp = (timeNow + timedelta(milliseconds = sleepDelta)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                root.set('timestamp', timeStamp)
                root.set('category', "test")
                root.set('instance', "eew-ci-ext1")
                root.set('orig_sys', "EEWScenario")
                origTimeElement = (root.find('core_info')).find('orig_time')
                origTimeElement.text = originTime
                coreIDElement = root.find('core_info')
                coreID = coreIDElement.get('id')
                coreIDElement.set('id', (self.nextEventID + "_" + coreID))
                msg = ET.tostring(root, encoding='unicode', method='xml')
#               self.logger.debug("msg: " + msg)
                time.sleep((sleepDelta/1000))
                conn.send(body=msg, destination=self.topicName)
                message = "Sent message " + fileLocation + " at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + " to " + self.topicName
                self.logger.warning(message)
            incrementID = (int(self.nextEventID)) + 1

            with open(self.nextEventIDLocation, 'w') as f:
                f.write(str(incrementID))
            with open(self.nextEventIDLocation, 'r') as f:
                print(f.read().strip())
            conn.disconnect()
        except Exception as e:
            print(str(e))
            self.logger.error(str(e))

    def sendAMQwithSTOMPTest(self, EEWDict):
        """Same as sendAMQwithSTOMP, but for testing purposes only.  
        Hardcoded file location is used here
        """
        conn = stomp.Connection([(self.AMQServer,int(self.AMQSTOMPPort))], use_ssl=True, auto_content_length=False)
        try:
            conn.start()
            conn.connect(self.userID, self.passwd, wait=True)
            timeNow = datetime.utcnow()
            originTime = timeNow.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            fileLocation = "/app/eew/EEWScenario/eqplayer/examples/Point_Source/test.xml"
            inputFile = open(fileLocation,'r')
            msg=inputFile.read()
            self.logger.warning("msg: " + msg)
            conn.send(body=msg, destination=self.topicName)
            message = "Sent message " + fileLocation + " at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + " to " + self.topicName
            self.logger.warning(message)
            conn.disconnect()
        except Exception as e:
            print(str(e))
            self.logger.error(str(e))


if __name__ == "__main__":
    main()

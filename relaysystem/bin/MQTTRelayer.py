"""
    MQTTRelayer - relays messages via MQTT protocol to ActiveMQ server(s)
"""

import paho.mqtt.client as mqtt
import ssl

import time
import xml.etree.ElementTree as ET
from configparser import ConfigParser


global HBActive

# Load the properties configuration file
config = ConfigParser()
config.read('../params/MQTTRelayerProperties.cfg')

relayServerList = (config.get("CFG", 'relayServerList')).split(",")
port = int(config.get("CFG", 'port'))
topicsListen = (config.get("CFG", 'topicsListen')).split(",")
HBtopic = config.get("CFG", 'HBtopic')
userid = config.get("CFG", 'userid')
passwd = config.get("CFG", 'passwd')
HBInterval = int(config.get("CFG", 'HBInterval'))
HBRetries = int(config.get("CFG", 'HBRetries'))
HAFile = config.get("CFG", 'HAFile')
relayClientID = config.get("CFG", 'relayClientID')
localClientID = config.get("CFG", 'localClientID')

def on_disconnect(client, userdata, rc):
    print("client disconnected ok")

# MQTT functions
def on_subscribe_MQTT(client, userdata, mid, granted_qos):
    print("Subscribed via MQTT: "+str(mid)+" "+str(granted_qos))

def on_message_MQTT(client, userdata, msg):
    global HBActive
    if msg.topic == HBtopic:
        # it's a heartbeat message
        HBActive = True
#        print(msg.topic+" "+str(msg.qos)+" "+str(msg.payload))
    else:
        logMsg = ("MESSAGE RECEIVED at "
                  + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
        print(logMsg)
#        print(msg.topic+" "+str(msg.qos)+" "+str(msg.payload))
        root = ET.fromstring(msg.payload.decode("utf-8"))
        ref_id = root.get('ref_id')
        if ref_id == "99":
            print("No relay")
        else:
            root.set('ref_id', "99")
            updatedMsg = ET.tostring(root).decode("utf-8")
#            print("relay message: " + updatedMsg)
            relayMessage(relayServerList, updatedMsg, msg.topic)



def relayMessage(serverList, relayMsg, relayTopic):
    for server in serverList:
        # modify message to put server in orig_sys
        root = ET.fromstring(relayMsg)
        root.set('orig_sys', server)
        updatedMsg = ET.tostring(root).decode("utf-8")

        # connect to server and relay message
        print("Relaying to broker " + server + " with MQTT")
        relayClient.connect(server, port=port) #connect to broker
        relayClient.publish(relayTopic, payload=updatedMsg)
        relayClient.disconnect()


# set up relay client
relayClient = mqtt.Client(client_id=relayClientID,protocol=mqtt.MQTTv311) #create new instance
relayClient.username_pw_set(userid, passwd)
relayClient.on_disconnect = on_disconnect

# connect and listen for messages with MQTT
print("Creating new MQTT instance")
client = mqtt.Client(client_id=localClientID,protocol=mqtt.MQTTv311) #create new instance
client.on_subscribe = on_subscribe_MQTT
client.on_message = on_message_MQTT

client.username_pw_set(userid, passwd)
print("Connecting to broker with MQTT")
client.connect("localhost", port=port) #connect to broker
for topic in topicsListen:
    print("Subscribing to topic with MQTT", topic)
    client.subscribe(topic, qos=1)

inputFile = open(HAFile,'r')
HBmsg=inputFile.read()
inputFile.close()

client.loop_start()
while True:
    client.publish(HBtopic, payload=HBmsg)
    time.sleep(HBInterval)

client.loop_stop()
print('Goodbye!')
logMsg = ("LOST HEARTBEATS WITH SERVER at "
          + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
print(logMsg)

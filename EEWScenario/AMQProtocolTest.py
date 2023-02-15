"""
    AMQProtocolTest - tests MQTT and AMQP protocols for ActiveMQ
"""

import paho.mqtt.client as mqtt


from proton import Message
from proton import SSLDomain
from proton.handlers import MessagingHandler
from proton.reactor import Container

from time import sleep

# MQTT functions
def on_subscribe_MQTT(client, userdata, mid, granted_qos):
    print("Subscribed via MQTT: "+str(mid)+" "+str(granted_qos))

def on_message_MQTT(client, userdata, msg):
    print(msg.topic+" "+str(msg.qos)+" "+str(msg.payload)) 


# AMQP class with functions
class AMQPMessaging(MessagingHandler):
    def __init__(self, server, address, uid, passwd, certLoc):
        super(AMQPMessaging, self).__init__()
        self.server = server
        self.address = address
        self.uid = uid
        self.passwd = passwd
        self.certLoc = certLoc

    def on_start(self, event):
        mySSL = SSLDomain(mode=SSLDomain.MODE_CLIENT)
        mySSL.set_trusted_ca_db(self.certLoc)
        conn = event.container.connect(self.server, user=self.uid, password=self.passwd)
        event.container.create_receiver(conn, self.address)

    def on_connection_opened(self, event):
        print("AMQP connection is open")

    def on_message(self, event):
        print(event.message.body)
        event.connection.close()



broker_address="eew-test1.wr.usgs.gov"
port = 61612
MQTTtopic = "eew/test_guest1/dm/data"
AMQPtopic = "topic://eew.test_guest1.dm.data"
userid = "guest1"
passwd = ""
certLoc = "/etc/pki/tls/certs/ca-bundle.crt"

# test AMQP
Container(AMQPMessaging("amqps://" + broker_address + ':' + str(port), AMQPtopic, userid, passwd, certLoc)).run()

sleep(15)


# test MQTT
print("Creating new MQTT instance")
client = mqtt.Client("P1") #create new instance
client.on_subscribe = on_subscribe_MQTT
client.on_message = on_message_MQTT
client.tls_set(certLoc)
client.tls_insecure_set(True)

client.username_pw_set(userid, passwd)
print("Connecting to broker with MQTT")
client.connect(broker_address, port=port) #connect to broker
print("Subscribing to topic with MQTT", MQTTtopic)
client.subscribe(MQTTtopic, qos=1)

client.loop_start()
print("sleep for 15")
sleep(15)
client.loop_stop()

#!/home/ec2-user/venvs/mot/bin/python
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import argparse
import json
import random
import requests
import html
import shelve

AllowedActions = ['both', 'publish', 'subscribe']

# Read in command-line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-e", "--endpoint", action="store", required=True, dest="host", help="Your AWS IoT custom endpoint")
parser.add_argument("-r", "--rootCA", action="store", required=True, dest="rootCAPath", help="Root CA file path")
parser.add_argument("-c", "--cert", action="store", dest="certificatePath", help="Certificate file path")
parser.add_argument("-k", "--key", action="store", dest="privateKeyPath", help="Private key file path")
parser.add_argument("-p", "--port", action="store", dest="port", type=int, help="Port number override")
parser.add_argument("-w", "--websocket", action="store_true", dest="useWebsocket", default=False,
                    help="Use MQTT over WebSocket")
parser.add_argument("-id", "--clientId", action="store", dest="clientId", default="basicPubSub",
                    help="Targeted client id")
parser.add_argument("-m", "--mode", action="store", dest="mode", default="both",
                    help="Operation modes: %s"%str(AllowedActions))
parser.add_argument("-g", "--game-id", action="store", dest="game_id", default=0)

args = parser.parse_args()
host = args.host
rootCAPath = args.rootCAPath
certificatePath = args.certificatePath
privateKeyPath = args.privateKeyPath
port = args.port
useWebsocket = args.useWebsocket
clientId = args.clientId
topic = f'qq/game/{args.game_id}' 


question_url = f'https://opentdb.com/api.php?amount=1'

if args.mode not in AllowedActions:
    parser.error("Unknown --mode option %s. Must be one of %s" % (args.mode, str(AllowedActions)))
    exit(2)

if args.useWebsocket and args.certificatePath and args.privateKeyPath:
    parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
    exit(2)

if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
    parser.error("Missing credentials for authentication.")
    exit(2)

# Port defaults
if args.useWebsocket and not args.port:  # When no port override for WebSocket, default to 443
    port = 443
if not args.useWebsocket and not args.port:  # When no port override for non-WebSocket, default to 8883
    port = 8883

# Configure logging
logger = logging.getLogger("AWSIoTPythonSDK.core")
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

# Init AWSIoTMQTTClient
myAWSIoTMQTTClient = None
if useWebsocket:
    myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId, useWebsocket=True)
    myAWSIoTMQTTClient.configureEndpoint(host, port)
    myAWSIoTMQTTClient.configureCredentials(rootCAPath)
else:
    myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId)
    myAWSIoTMQTTClient.configureEndpoint(host, port)
    myAWSIoTMQTTClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTClient connection configuration
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec


'''
{
  "player_id" : "id",
  "correct" : "true|false"
}
'''

player_db = '/tmp/.playerdb'

question_ans_msgtype = 1
leaders_msgtype = 2
question_msgtype = 3

def recordCb(client,userdata,message):
    print("Received a new message: ")
    print(message.payload)
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")

    msg = json.loads(message.payload)

    if msg['msgtype'] != question_ans_msgtype:
        print ('unsupported msg type',msg['msgtype'])
        return

    with shelve.open(player_db,writeback=True) as db:
        if msg['player_id'] not in db:
            db[msg['player_id']] = {}
        if args.game_id not in db[msg['player_id']]:
            db[msg['player_id']][args.game_id] = dict(correct=0,incorrect=0,streak=0) 
        if msg["correct"]:
            db[msg['player_id']][args.game_id]['correct'] += 1
            db[msg['player_id']][args.game_id]['streak'] += 1
        else:
            db[msg['player_id']][args.game_id]['streak'] = 0
            db[msg['player_id']][args.game_id]['incorrect'] += 1




# Connect and subscribe to AWS IoT
myAWSIoTMQTTClient.connect()
time.sleep(2)
myAWSIoTMQTTClient.subscribe(topic=topic, QoS=1, callback=recordCb)

# Publish to the same topic in a loop forever
loopCount = 0

def sort_leaders(l):
    return l['count']

def get_leaders(useStreak=False):
    res = {}

    
    leaders = []
    with shelve.open(player_db,writeback=True) as db:
        for _n in db:
            if args.game_id in db[_n]:
                if useStreak:
                    leaders.append(dict(player_id=_n,
                                        count=db[_n][args.game_id]['streak']))
                else:
                    leaders.append(dict(player_id=_n,
                                        count=db[_n][args.game_id]['correct']))

    return sorted(leaders,key=sort_leaders,reverse=True)



while True:
    leaders = get_leaders()


    msg = dict(msgtype=leaders_msgtype,
               leaders=leaders)

    messageJson = json.dumps(msg)
    myAWSIoTMQTTClient.publish(topic, messageJson, 1)
    print('Published topic %s: %s\n' % (topic, messageJson))
    time.sleep(30)

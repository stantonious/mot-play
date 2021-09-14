#!/home/ec2-user/venvs/mot/bin/python
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import argparse
import json
import random
import requests

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
parser.add_argument("-T", "--player-type", action="store", dest="player_type", default=1, help="player type 1-wizard 2-rogue 3-fighter")
parser.add_argument("-m", "--mode", action="store", dest="mode", default="both",
                    help="Operation modes: %s"%str(AllowedActions))
parser.add_argument("-x", "--start-x", action="store", type=int,dest="startx", default=0,)
parser.add_argument("-y", "--start-y", action="store", type=int,dest="starty", default=0,)
parser.add_argument("-M", "--maze-id", action="store", type=int,dest="maze_id", default=0,)

NORTH_BIT = 0x0001
SOUTH_BIT= 0x0002
EAST_BIT =0x0004
WEST_BIT =0x0008

NORTH_DIR=0
EAST_DIR= 1
SOUTH_DIR= 2
WEST_DIR= 3

def get_possible_moves(m,c_x,c_y):
  #assert c_x < len(m[0]) and c_x >= 0
  #assert c_y < len(m) and c_y >= 0

  res = []
  if c_x >= len(m[0]) or c_x < 0 or c_y >= len(m) or c_y < 0:
      return res

  w = m[c_y][c_x]

  print ("w %s y %s x %s" % (w,c_y,c_x))

  if w & NORTH_BIT == 0:
      res.append(NORTH_DIR)
  if w & SOUTH_BIT == 0:
      res.append(SOUTH_DIR)
  if w & EAST_BIT == 0:
      res.append(EAST_DIR)
  if w & WEST_BIT == 0:
      res.append(WEST_DIR)

  print (res)
  return res

def move(c_x,c_y,d):
  if d == NORTH_DIR:
      return c_x,c_y-1
  if d == SOUTH_DIR:
      return c_x,c_y+1
  if d == EAST_DIR:
      return c_x+1,c_y
  if d == WEST_DIR:
      return c_x-1,c_y

args = parser.parse_args()
host = args.host
rootCAPath = args.rootCAPath
certificatePath = args.certificatePath
privateKeyPath = args.privateKeyPath
port = args.port
useWebsocket = args.useWebsocket
clientId = args.clientId
topic = f'motivate/game/{args.maze_id}' 

maze_url = f'http://dl3to8c26ssxq.cloudfront.net/production/maze?id={args.maze_id}'

resp = requests.get(url=maze_url)
maze = resp.json()["cells"]

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

# Connect and subscribe to AWS IoT
myAWSIoTMQTTClient.connect()
time.sleep(2)

# Publish to the same topic in a loop forever
loopCount = 0
current_x = args.startx
current_y = args.starty
last_move=0

while True:
    possible_moves = get_possible_moves(maze,current_x,current_y)

    #current_x,current_y = move(current_x,current_y,random.choice(possible_moves))
    backwards_d = (last_move+2)%4

    if len(possible_moves) == 0:
        current_x = args.startx
        current_y = args.starty
    else:
        if len(possible_moves)>1:
            possible_moves.remove(backwards_d)
    #last_move = min(possible_moves)
        last_move = random.choice(possible_moves)
        current_x,current_y = move(current_x,current_y,last_move)
    message = {}
    message['time'] = int(time.time())
    message['id'] = clientId
    message['x'] = current_x
    message['y'] = current_y
    message['t'] = args.player_type
    messageJson = json.dumps(message)
    myAWSIoTMQTTClient.publish(topic, messageJson, 1)
    print('Published topic %s: %s\n' % (topic, messageJson))
    loopCount += 1
    time.sleep(.9)

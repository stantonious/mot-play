#!/home/ec2-user/venvs/mot/bin/python
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import argparse
import json
import random
import csv
import time

AllowedActions = ['both', 'publish', 'subscribe']

# Read in command-line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-e", "--endpoint", action="store", required=True, dest="host", help="Your AWS IoT custom endpoint")
parser.add_argument("-r", "--rootCA", action="store", required=True, dest="rootCAPath", help="Root CA file path")
parser.add_argument("-c", "--cert", action="store", dest="certificatePath", help="Certificate file path")
parser.add_argument("-C", "--csv", action="store", dest="csvPath", help="CSV DB")
parser.add_argument("-k", "--key", action="store", dest="privateKeyPath", help="Private key file path")
parser.add_argument("-p", "--port", action="store", dest="port", type=int, help="Port number override")
parser.add_argument("-w", "--websocket", action="store_true", dest="useWebsocket", default=False,
                    help="Use MQTT over WebSocket")
parser.add_argument("-id", "--clientId", action="store", dest="clientId", default="basicPubSub",
                    help="Targeted client id")
parser.add_argument("-t", "--topic", action="store", dest="topic", default="sdk/test/Python", help="Targeted topic")
parser.add_argument("-m", "--mode", action="store", dest="mode", default="both",
                    help="Operation modes: %s"%str(AllowedActions))
parser.add_argument("-M", "--message", action="store", dest="message", default="Hello World!",
                    help="Message to publish")

args = parser.parse_args()
host = args.host
rootCAPath = args.rootCAPath
certificatePath = args.certificatePath
privateKeyPath = args.privateKeyPath
port = args.port
useWebsocket = args.useWebsocket
clientId = args.clientId
topic = args.topic
csvPath = args.csvPath


'''
{\n\t"time":\t27,\n\t"type":\t2,\n\t"acc_samples":\t{\n\t\t"x":\t[-0.01025390625, -0.006103515625, -0.0205078125, -0.0107421875, -0.013916015625, -0.01123046875, -0.012451171875, -0.012939453125, -0.020751953125, 0.14892578125],\n\t\t"y":\t[-0.001708984375, -0.002197265625, -0.005859375, -0.001953125, 0.001220703125, -0.013427734375, -0.00439453125, -0.01171875, -0.028076171875, -0.082275390625],\n\t\t"z":\t[0.075439453125, 0.086181640625, 0.068115234375, 0.072998046875, 0.0751953125, 0.0791015625, 0.053955078125, 0.093017578125, 0.08203125, 0.13720703125]\n\t},\n\t"gyro_samples":\t{\n\t\t"x":\t[1.9843740463256836, 1.5917228394633278e+38, 1.5917228394633278e+38, 1.5917228394633278e+38, 1.5917228394633278e+38, 1.5917228394633278e+38, 1.5917228394633278e+38, 1.5917228394633278e+38, 1.5917228394633278e+38, 1.5917228394633278e+38],\n\t\t"y":\t[0.18310546875, -0.54931640625, -0.1220703125, -0.30517578125, -0.42724609375, -0.3662109375, -0.30517578125, 3.35693359375, 128.84521484375, 2.5634765625],\n\t\t"z":\t[-5.18798828125, -5.43212890625, -4.94384765625, -5.31005859375, -5.4931640625, -5.4931640625, -5.43212890625, -5.9814453125, -7.568359375, -7.080078125]\n\t}\n}'
'''


def recordCb(client,userdata,message):
    print("Received a new message: ")
    print(message.payload)
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")

    d = json.loads(message.payload);
    print("Json data: ",d)
    with open(csvPath,'a') as csvfile:
        rec = csv.DictWriter(csvfile,fieldnames=['time',
                                                 'type',
                                                 'acc_x',
                                                 'acc_y',
                                                 'acc_z',
                                                 'gyr_x',
                                                 'gyr_y',
                                                 'gyr_z',
                                                 ])

        #t = d['time']
        t = time.time()
        _type = d['type']
        acc_x = d['acc_samples']['x']
        acc_y = d['acc_samples']['y']
        acc_z = d['acc_samples']['z']
        gyr_x = d['gyro_samples']['x']
        gyr_y = d['gyro_samples']['y']
        gyr_z = d['gyro_samples']['z']

        for i in range(len(acc_x)):
            csv_d = dict(time=t,
                         type=_type,
                         acc_x=acc_x[i],
                         acc_y=acc_y[i],
                         acc_z=acc_z[i],
                         gyr_x=gyr_x[i],
                         gyr_y=gyr_y[i],
                         gyr_z=gyr_z[i],)
            rec.writerow(csv_d)





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
myAWSIoTMQTTClient.subscribe(topic, 1, recordCb)
time.sleep(2)

while True:
    time.sleep(.8)

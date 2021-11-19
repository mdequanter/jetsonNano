'''

Script to get all messages from posenet.  You need to subscribe to the broker and you will receive messages on topics "posenet"

nose = 0
leftEye = 1
rightEye = 2
leftEar = 3
rightEar = 4
leftShoulder = 5
rightShoulder = 6
leftElbow = 7
rightElbow = 8
leftWrist = 9
rightWrist = 10
leftHip = 11
rightHip = 12
leftKnee = 13
rightKnee = 14
leftAnkle = 15
rightAnkle = 16
neck = 17

'''


import time
import paho.mqtt.client as paho
import json
import math

broker="192.168.0.7"

def current_milli_time():
    return round(time.time() * 1000)




#define callback
def on_message(client, userdata, message):
    #print("received message",str(message.payload.decode("utf-8"))
    message = message.payload.decode("utf-8")

    posenet = json.loads(message)

    distanceLF = distance(posenet[9], posenet[10])

    print ("Distance leftWrist and RightWrist :" + str(distanceLF))



def distance(keypoint2, keypoint1):
    distance = 0
    if (keypoint1[0] > 0 and keypoint1[1] > 0 and keypoint2[0] > 0 and keypoint2[1] > 0):
        distance = math.sqrt((keypoint2[1] - keypoint1[1]) * (keypoint2[1] - keypoint1[1]) + (
                    keypoint2[0] - keypoint1[0]) * (keypoint2[0] - keypoint1[0]))
    return distance


client= paho.Client("client1")
######Bind function to callback
client.on_message=on_message
#####



print("connecting to broker ",broker)
client.connect(broker)#connect
client.loop_start() #start loop to process received messages


print("subscribing ")
client.subscribe("posenet")#subscribe

time.sleep(1000)

client.disconnect() #disconnect
client.loop_stop() #stop loop
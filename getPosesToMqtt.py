#!/usr/bin/python3
#
# Copyright (c) 2021, Maarten Dequanter. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#

import jetson.inference
import jetson.utils
import threading
import os
import time
import math

import argparse
import sys
import paho.mqtt.client as paho
import json

broker = "127.0.0.1"
port = 1883


def on_publish(client, userdata, result):  # create function for callback
    # print("data published \n")
    pass


client1 = paho.Client("control1")  # create client object
client1.on_publish = on_publish  # assign function to callback
client1.connect(broker, port)  # establish connection

# parse the command line
parser = argparse.ArgumentParser(description="Run pose estimation DNN on a video/image stream.",
                                 formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument("input_URI", type=str, default="", nargs='?', help="URI of the input stream")
parser.add_argument("output_URI", type=str, default="", nargs='?', help="URI of the output stream")
parser.add_argument("--network", type=str, default="resnet18-body",
                    help="pre-trained model to load (see below for options)")
parser.add_argument("--overlay", type=str, default="links",
                    help="pose overlay flags (e.g. --overlay=links,keypoints)\nvalid combinations are:  'links', 'keypoints', 'boxes', 'none'")
parser.add_argument("--threshold", type=float, default=0.10, help="minimum detection threshold to use")

try:
    opt = parser.parse_known_args()[0]
except:
    print("")
    parser.print_help()
    sys.exit(0)

# load the pose estimation model
net = jetson.inference.poseNet(opt.network, sys.argv, opt.threshold)

# create video sources & outputs
input = jetson.utils.videoSource(opt.input_URI, argv=sys.argv)
output = jetson.utils.videoOutput(opt.output_URI, argv=sys.argv)

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

minimumMovement = 20

Xlist = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
Ylist = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
vMovement = ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S',
             'S']  # S: Static,  U: UP, D: Down
hMovement = ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S',
             'S']  # S: Static,  L: Left, R: Right

leftWristX = 0
leftElbowX = 0
leftShoulderX = 0
leftWristY = 0
leftElbowY = 0
leftShoulderY = 0

rightWristX = 0
rightElbowX = 0
rightShoulderX = 0
rightWristY = 0
rightElbowY = 0
rightShoulderY = 0

tempo = 5
directionLeftArm = 0
directionRightArm = 0

frameCounter = 0


def lookDirection():
    global Xlist, Ylist, neck, nose
    if (Xlist[nose] > Xlist[neck] + 10):
        return ("L")
    elif (Xlist[nose] < Xlist[neck] - 10):
        return ("R")
    else:
        return ("F")


def distance(keypoint2, keypoint1):
    global Xlist, Ylist
    p = [Xlist[keypoint2], Ylist[keypoint2]]
    q = [Xlist[keypoint1], Ylist[keypoint1]]
    distance = 0
    if (Ylist[keypoint1] > 0 and Ylist[keypoint2] > 0 and Xlist[keypoint1] > 0 and Xlist[keypoint2] > 0):
        distance = math.sqrt((Ylist[keypoint2] - Ylist[keypoint1]) * (Ylist[keypoint2] - Ylist[keypoint1]) + (
                    Xlist[keypoint2] - Xlist[keypoint1]) * (Xlist[keypoint2] - Xlist[keypoint1]))
    return distance


def updown(keypoint2, keypoint1):
    global Ylist
    Y = Ylist[keypoint2] - Ylist[keypoint1]
    if (Y > 50):
        return ('H')
    elif (Y < -50):
        return ('L')
    else:
        return ('M')


def direction(keypoint2, keypoint1):
    global Xlist, Ylist
    X = Xlist[keypoint2] - Xlist[keypoint1]
    Y = Ylist[keypoint2] - Ylist[keypoint1]
    direction = math.atan2(X, Y)
    return math.degrees(direction)


def speed(keypoint, x, y):
    global Xlist, Ylist
    p = [Xlist[keypoint], Ylist[keypoint]]
    q = [x, y]
    distance = 0
    if (Ylist[keypoint] > 0 and Ylist[keypoint] > 0 and x > 0 and y > 0):
        distance = math.sqrt(
            (Ylist[keypoint] - y) * (Ylist[keypoint] - y) + (Xlist[keypoint] - x) * (Xlist[keypoint] - x))
    print (distance)
    if (distance < 1):
        return ('L')
    elif (distance > 1 and distance < 20):
        return ('M')
    elif (distance > 20):
        return ('H')


def processKeypoints(keypoints):
    global Xlist, Ylist, vMovement, hMovement, tempo
    for keypoint in pose.Keypoints:
        if (keypoint.ID < 18):
            if (Ylist[keypoint.ID] > keypoint.y + minimumMovement):
                vMovement[keypoint.ID] = 'U'
            elif (Ylist[keypoint.ID] < keypoint.y - minimumMovement):
                vMovement[keypoint.ID] = 'D'
            else:
                vMovement[keypoint.ID] = 'S'

            if (Xlist[keypoint.ID] > keypoint.x + minimumMovement):
                hMovement[keypoint.ID] = 'L'
            elif (Xlist[keypoint.ID] < keypoint.x - minimumMovement):
                hMovement[keypoint.ID] = 'R'
            else:
                hMovement[keypoint.ID] = 'S'

            if (keypoint.ID == leftWrist or keypoint.ID == rightWrist):
                tempo = speed(keypoint.ID, keypoint.x, keypoint.y)
                # print (tempo)

            Xlist[keypoint.ID] = keypoint.x
            Ylist[keypoint.ID] = keypoint.y


# process frames until the user exits
while True:
    frameCounter += 1
    # capture the next image
    img = input.Capture()

    # perform pose estimation (with overlay)
    poses = net.Process(img, overlay=opt.overlay)

    # print the pose results
    # print("detected {:d} objects in image".format(len(poses)))

    for pose in poses:
        oldDirectionRightArm = directionRightArm
        oldDirectionLeftArm = directionLeftArm
        oldTempo = tempo
        processKeypoints(pose)

        '''
    if (vMovement[nose] == 'U'):
      print ("nose up")
    if (vMovement[nose] == 'D'):
      print ("nose down")
    if (vMovement[nose] == 'S'):
      print ("nose static")
    if (hMovement[nose] == 'R'):
      print ("nose left")
    if (hMovement[nose] == 'L'):
      print ("nose right")
    if (hMovement[nose] == 'S'):
      print ("nose static")
    '''

        directionRightArm = updown(rightShoulder, rightWrist)
        if (directionRightArm != oldDirectionRightArm):
            ret = client1.publish("RIGHT", directionRightArm)
            oldDirectionRightArm = directionRightArm
            #print("right:" + str(directionRightArm))

        directionLeftArm = updown(leftShoulder, leftWrist)
        if (directionLeftArm != oldDirectionLeftArm):
            ret = client1.publish("LEFT", directionLeftArm)
            oldDirectionLeftArm = directionLeftArm
            #print("left:" + str(directionLeftArm))
        if (tempo != oldTempo):
            client1.publish("TEMPO", tempo)
            #print("tempo:" + str(tempo))
            oldTempo = tempo

        '''
    print ("Looking : ", lookDirection())

    distanceHands = distance(leftWrist,rightWrist)
    ret= client1.publish("jetson",str(distanceHands)) 
    print ("distance hands: ", str(distanceHands))
    '''

    frameCounter += 1
    if (frameCounter > 60):
        client1.publish("Y", json.dumps(Ylist))
        client1.publish("X", json.dumps(Xlist))

    # render the image
    output.Render(img)
    # update the title bar
    output.SetStatus("{:s} | Network {:.0f} FPS".format(opt.network, net.GetNetworkFPS()))

    # print (net.GetNetworkFPS())
    # print out performance info
    # net.PrintProfilerTimes()

    # exit on input/output EOS
    if not input.IsStreaming() or not output.IsStreaming():
        break

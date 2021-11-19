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
#output = jetson.utils.videoOutput(opt.output_URI, argv=sys.argv)

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

posList = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]


frameCounter = 0

def processKeypoints(keypoints):
    global Xlist, Ylist,posList
    for keypoint in pose.Keypoints:
        if (keypoint.ID < 18):
            posList[keypoint.ID]= [keypoint.x,keypoint.y]


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
        processKeypoints(pose)

    frameCounter += 1
    client1.publish("posenet", json.dumps(posList))

    # render the image
    #output.Render(img)
    # update the title bar
    #output.SetStatus("{:s} | Network {:.0f} FPS".format(opt.network, net.GetNetworkFPS()))

    # print (net.GetNetworkFPS())
    # print out performance info
    # net.PrintProfilerTimes()

    # exit on input/output EOS
    if not input.IsStreaming():
        break

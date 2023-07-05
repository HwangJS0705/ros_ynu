#!/usr/bin/env python
import rospy
import sys, select, os
import tty
import termios
import cv2
import time
import math
import numpy as np
from geometry_msgs.msg import Twist
from std_msgs.msg import String
#import sys, select, os
velocity = 0
steering = 0
breakcontrol = 1
gear = 0
MAX_Velocity = 50
MAX_Steering = 120
MIN_Steering = 240
publisher = rospy.Publisher('/teleop_cmd_vel', Twist,queue_size=1)

def DetectLineSlope(src):
    
    gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.GaussianBlur(gray,(7,7),0)
    
    can = cv2.Canny(gray2, 50, 200, None, 3)


    height = can.shape[0]
    # rectangle = np.array([[(-100, height), (200, 350), (1080, 350), (1380, height)]])
    rectangle = np.array([[(-100, height), (50, 250), (590, 250), (740, height)]])
    # rectangle = np.array([[(0, height),(0, 0),(640, 0),(640, height)]])
    mask = np.zeros_like(can)
    cv2.fillPoly(mask, rectangle, 255)
    masked_image = cv2.bitwise_and(can, mask)
    ccan = cv2.cvtColor(masked_image, cv2.COLOR_GRAY2BGR)


    line_arr = cv2.HoughLinesP(masked_image, 1, np.pi / 180, 20, minLineLength=10, maxLineGap=10)

    # line color
    # color = [0, 0, 255]
    # thickness = 5
    # for line in line_arr:
    #   for x1, y1, x2, y2 in line:
    #        cv2.line(ccan, (x1, y1), (x2, y2), color, thickness)

    line_R = np.empty((0, 5), int)
    line_L = np.empty((0, 5), int)
    if line_arr is not None:
        line_arr2 = np.empty((len(line_arr), 5), int)
        for i in range(0, len(line_arr)):
            temp = 0
            l = line_arr[i][0]
            line_arr2[i] = np.append(line_arr[i], np.array((np.arctan2(l[1] - l[3], l[0] - l[2]) * 180) / np.pi))
            if line_arr2[i][1] > line_arr2[i][3]:
                temp = line_arr2[i][0], line_arr2[i][1]
                line_arr2[i][0], line_arr2[i][1] = line_arr2[i][2], line_arr2[i][3]
                line_arr2[i][2], line_arr2[i][3] = temp
            if line_arr2[i][0] < 320 and (abs(line_arr2[i][4]) < 170 and abs(line_arr2[i][4]) > 95):
                line_L = np.append(line_L, line_arr2[i])
            elif line_arr2[i][0] > 320 and (abs(line_arr2[i][4]) < 170 and abs(line_arr2[i][4]) > 95):
                line_R = np.append(line_R, line_arr2[i])
    line_L = line_L.reshape(int(len(line_L) / 5), 5)
    line_R = line_R.reshape(int(len(line_R) / 5), 5)
    cv2.line(ccan, (320, 250), (320, 250), (0, 255, 0), 10)
    try:
        line_L = line_L[line_L[:, 0].argsort()[-1]]
        center_x = (((line_L[0]+line_L[2])/2)+((line_R[0]+line_R[2])/2))/2
        degree_L = line_L[4]
        cv2.line(ccan, (line_L[0], line_L[1]), (line_L[2], line_L[3]), (255, 0, 0), 10, cv2.LINE_AA)
        # cv2.line(ccan, ((line_L[0]+line_R[0])/2, 250), ((line_L[0]+line_R[0])/2, 250), (0, 0, 255), 10)
        # print("left")
        # print(line_L[0], line_L[1],line_L[2],line_L[3])
    except:
        degree_L = 0
    try:
        line_R = line_R[line_R[:, 0].argsort()[0]]
        center_x = (((line_L[0]+line_L[2])/2)+((line_R[0]+line_R[2])/2))/2
        degree_R = line_R[4]
        cv2.line(ccan, (line_R[0], line_R[1]), (line_R[2], line_R[3]), (255, 0, 0), 10, cv2.LINE_AA)
        # cv2.line(ccan, ((line_L[0]+line_R[0])/2, 250), ((line_L[0]+line_R[0])/2, 250), (0, 0, 255), 10)
        # cv2.line(ccan, (0, 0), (640, 480), (0, 0, 255), 10)
        # print("right")
        # print(line_R[0], line_R[1],line_R[2],line_R[3])
    except:
        degree_R = 0
    # cv2.line(ccan, ((line_L[0]+line_R[0])/2, 250), ((line_L[0]+line_R[0])/2, 250), (0, 255, 255), 10)
    mimg = cv2.addWeighted(src, 1, ccan, 1, 0)
    return mimg, degree_L, degree_R

def color_filter(image):
    hls = cv2.cvtColor(image, cv2.COLOR_BGR2HLS)
    
    lower = np.array([20,150,20])
    upper = np.array([255,255,255])
    
    yellow_lower = np.array([0,85,81])
    yellow_upper = np.array([190,255,255])
    
    yellow_mask = cv2.inRange(hls, yellow_lower, yellow_upper)
    white_mask = cv2.inRange(hls, lower, upper)
    mask = cv2.bitwise_or(yellow_mask, white_mask)
    masked = cv2.bitwise_and(image, image, mask - mask)
    
    return masked

def getkey():
    fd = sys.stdin.fileno()
    original_attributes = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original_attributes)
    return ch    

def teleop():
    global velocity,steering,breakcontrol,gear
    cap = cv2.VideoCapture("a2.mp4")
    rospy.init_node('teleop', anonymous=True)
#    rospy.Subscriber("/move_base_simple/goal", PoseStamped, callback)
    rate = rospy.Rate(50) # 10hz
#    try:
    status = 0
    while not rospy.is_shutdown():
        ret, frame = cap.read()
    # frame = cv2.flip(frame, 0)

        if ret:
            time.sleep(0.01)
            frame = cv2.resize(frame, (640, 480))
            # frame = cv2.resize(frame, (1280, 720))
            cv2.imshow('ImageWindow', DetectLineSlope(frame)[0])
            # cv2.imshow('ImageWindow2', color_filter(cap))
            l, r = DetectLineSlope(frame)[1], DetectLineSlope(frame)[2]
            
            if r==0:
                steering = 0
                print("r none")
            else:
                steering = -(r + 95)/2 -20
                print(r, steering)

            if cv2.waitKey(1) & 0xff == ord('q'):
                break
        # key = getkey()
        # if key == 'w':
        #     velocity = velocity + 2
        #     steering = 0 
        #     status = status + 1
        # elif key == 's':
        #     velocity = 0
        #     steering = 0
        #     status = status + 1
        # elif key == 'a':
        #     steering = steering + 1
        #     status = status + 1
        # elif key == 'd':
        #     steering = steering - 1
        #     status = status + 1
        # elif key == 'x':
        #     velocity = velocity - 2
        #     steering = 0
        #     status = status + 1
        # else:
        #     if (key == '\x03'):
        #         break
        if steering >= 20:
            steering = 20
        if steering <= -20:
            steering = -20
        if velocity >= MAX_Velocity:
            velocity = MAX_Velocity
        if velocity <= 0:
            velocity = 0
        pubmsg = Twist()
		
        pubmsg.linear.x = velocity
        pubmsg.angular.z = steering
        publisher.publish(pubmsg)
        print('cmd : ' + str(velocity) + ','+ str(steering))
        #rate.sleep()
    cv2.destroyAllWindows()
    rospy.spin()

if __name__ == '__main__':
    try:
        teleop()
    except rospy.ROSInterruptException: pass

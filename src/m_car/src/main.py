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
import time
#import sys, select, os
velocity = 0
steering = 0
breakcontrol = 1
gear = 0
MAX_Velocity = 50
MAX_Steering = 120
MIN_Steering = 240
publisher = rospy.Publisher('/teleop_cmd_vel', Twist,queue_size=1)
stop_type = 0
stop_count = 0

#stop_line
def roi_image(image):
    (x,y),(w,h) = (120,300),(300,300)
    # (x,y),(w,h) = (00,0),(1920,1080)
    roi_img = image[y:y+h, x:x+w]

    return roi_img

def white_filter(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    white_lower = np.array([0, 0, 150])
    white_upper = np.array([100, 100, 255])

    white_mask = cv2.inRange(hsv, white_lower, white_upper)

    white_masked = cv2.bitwise_and(image, image, mask=white_mask)

    return white_masked

def grayscale(src):
    return cv2.cvtColor(src, cv2.COLOR_RGB2GRAY)

def gaussian_blur(src, kernel_size):
    return cv2.GaussianBlur(src, (kernel_size, kernel_size), 0)

def canny(src, low_threshold, high_threshold):
    return cv2.Canny(src, low_threshold, high_threshold)

def DetectLineSlope(src):
    gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.GaussianBlur(gray,(7,7),5)
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
    # for x1, y1, x2, y2 in line:
    # cv2.line(ccan, (x1, y1), (x2, y2), color, thickness)

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

# def r_steering_angle(angle):
# if angle>0:
#new_value = ( (old_value - old_min) / (old_max - old_min) ) * (new_max - new_min) + new_min
#new_value = ((old_value - 95) / 3) - 20
# value = -(angle/155) * 20
# elif angle<0:
# value = -(angle/155) * 20
# else:
# return value
# def l_steering_angle(angle):

def teleop():
    global velocity,steering,breakcontrol,gear
    cap_stop_line = cv2.VideoCapture(4)
    cap_line = cv2.VideoCapture(2)
    rospy.init_node('teleop', anonymous=True)
    # rospy.Subscriber("/move_base_simple/goal", PoseStamped, callback)
    rate = rospy.Rate(50) # 10hz
    # try:
    status = 0
    
    steering = -4
    k=0
    while not rospy.is_shutdown():
        kernel_size = 5
        low_threshold = 50
        high_threshold = 200
        ret1, src1 = cap_stop_line.read()
        ret, frame = cap_line.read()
        # frame = cv2.flip(frame,0)
        # frame = cv2.flip(frame,0)
        # frame = cv2.flip(frame, 0)
        velocity = 50
        if ret:
            # time.sleep(0.01)
            frame = cv2.resize(frame, (640, 480))
            # frame = cv2.resize(frame, (1280, 720))
            # cv2.imshow('ImageWindow', DetectLineSlope(frame)[0])
            # cv2.imshow('ImageWindow2', color_filter(cap))
            l, r = DetectLineSlope(frame)[1], DetectLineSlope(frame)[2]

            # if abs(l) <= 155 or abs(r) <= 155:
                # if l == 0:
                    # if r>0:
                        # steering = ((r - 95) / 3) - 20
                        # elif r<0:
                        # steering = ((r + 95) / 3) + 20
                    # else:
                    # steering = 0
                # elif r == 0:
                    # if l>0:
                        # steering = ((l - 95) / 3) - 20
                    # elif l<0:
                        # steering = ((r + 95) / 3) + 20
                    # else:
                        # steering = 0
                # else
                    # if
                # elif abs(l - 15) > abs(r):
                    # steering = -10
                    # print('right')
                    # print(l, r)
                # elif abs(r + 15) > abs(l):
                    # steering = 10
                    # print('left')
                    # print(l, r)
                # else:
                    # steering = 0
                    # print('go')
                    # print(l, r)
            # else:
                # if l > 155 or r > 155:
                    # steering = 15
                    # print('hard right')
                    # print(l, r)
                # elif l < -155 or r < -155:
                    # steering = -15
                    # print('hard left')
                    # print(l, r)

            if abs(l) <= 155 or abs(r) <= 155:
                if l == 0 or r == 0:
                    if l < 0 or r < 0:
                        steering = 10
                        # print('left')
                        # print(l, r)
                    elif l > 0 or r > 0:
                        steering = -10
                        # print('right')
                        # print(l, r)
                elif abs(l - 15) > abs(r):
                    steering = -10
                    # print('right')
                    # print(l, r)
                elif abs(r + 15) > abs(l):
                    steering = 10
                    # print('left')
                    # print(l, r)
                else:
                    steering = 0
                    # print('go')
                    # print(l, r)
            else:
                if l > 155 or r > 155:
                    steering = 20
                    # print('hard right')
                    # print(l, r)
                elif l < -155 or r < -155:
                    steering = -20
                    # print('hard left')
                    # print(l, r)

            if cv2.waitKey(1) & 0xff == ord('q'):
                break
            pt1 = (0,0)
            pt2 = (0,0)
            steering = -3
            src1=roi_image(src1)
            src1 = cv2.flip(src1,0)
            gray_src = grayscale(src1)
            blur_src = gaussian_blur(gray_src, kernel_size)
            canny_src = canny(blur_src, low_threshold, high_threshold)
            # time.sleep(0.01)
            cv2.imshow('test2', src1)
            cv2.imshow('test1', canny_src)
            
            white_src = white_filter(src1)
            white_dst = cv2.Canny(white_src, 400, 600, None, 3)
            white_cdst = cv2.cvtColor(white_dst, cv2.COLOR_GRAY2BGR)
            white_cdstP = np.copy(white_cdst)
            stop_lines = cv2.HoughLines(white_dst, 1, 5*np.pi / 180, 150, None, 0, 0, 89, 91)
            if stop_lines is not None:
                for i in range(0, len(stop_lines)):
                    # global pt1
                    global stop_count
                    rho = stop_lines[0][0][0]
                    theta = stop_lines[0][0][1] 
                    a = math.cos(theta)
                    b = math.sin(theta)
                    x0 = a * rho 
                    y0 = b * rho
                    pt1 = (int(x0 + 1000 * (-b)), int(y0 + 1000 * (a))) 
                    pt2 = (int(x0 - 1000 * (-b)), int(y0 - 1000 * (a))) 
                    cv2.line(white_cdstP, pt1, pt2, (0, 0, 255), 5) 
                    print(k, pt1, pt2)
                    k+=1
                    velocity = 0
                    stop_count += 1
                    # if k >=1 stop == True
                    # stop == True -> velocity = 0

                #if yolo == go -> velocity = 30

            stop_linesP = cv2.HoughLinesP(white_dst, 1, 15*np.pi /180, 2, None, 150) 
            if stop_linesP is not None:
                for i in range(0, len(stop_linesP)):
                    global stop_count
                    l = stop_linesP[i][0]
                    cv2.line(white_cdstP, (l[0], l[1]), (l[2], l[3]), (0, 0, 255), 2, cv2.LINE_AA)
                    cv2.line(white_cdst, pt1, pt2, (255, 0, 0), 5) 
                    print("hh")
                    velocity = 0
                    stop_count += 1
            # key = getkey()
            # if key == 'w':
            # velocity = velocity + 2
            # steering = 0
            # status = status + 1
            # elif key == 's':
            # velocity = 0
            # steering = 0
            # status = status + 1
            # elif key == 'a':
            # steering = steering + 1
            # status = status + 1
            # elif key == 'd':
            # steering = steering - 1
            # status = status + 1
            # elif key == 'x':
            # velocity = velocity - 2
            # steering = 0
            # status = status + 1
            # else:
            # if (key == '\x03'):
            # break
        
        if steering >= 20:
            steering = 20
        if steering <= -20:
            steering = -20
        if velocity >= MAX_Velocity:
            velocity = MAX_Velocity
        if velocity <= 0:
            velocity = 0
        # stop_count += 2
        if stop_count > 0:
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
#!/usr/bin/env python
import rospy, rospkg, time
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import sys, select, os
import matplotlib as plt
import tty
import termios
import cv2
import time
import math
import signal
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


#==============================================================================================

#image = np.empty(shape=[0])
cap = cv2.VideoCapture(0)
bridge = CvBridge()
CAM_FPS = 30    
WIDTH, HEIGHT = 640, 480    

def img_callback(data):
    global image
    image = bridge.imgmsg_to_cv2(data, "bgr8")

def region_of_interest(img_1, vertices, color3=(255,255,255), color1=255):

    mask = np.zeros_like(img_1)
    
    if len(img_1.shape) > 2:
        color = color3
    else:
        color = color1
        

    cv2.fillPoly(mask, vertices, color)
    
    ROI_image = cv2.bitwise_and(img_1, mask)
    return ROI_image

def grayscale(img_1):
    return cv2.cvtColor(img_1,cv2.COLOR_RGB2GRAY)

def gaussian_blur(img_1, kernel_size):
    return cv2.GaussianBlur(img_1,(kernel_size,kernel_size),0)

def canny(img_1, low_threshold, high_threshold):
    return cv2.Canny(img_1,low_threshold, high_threshold)

def smoothing(lines, pre_frame):
    lines = np.squeeze(lines)
    avg_line = np.array([0,0,0,0])
    
    for ii,line in enumerate(reversed(lines)):
        if ii == pre_frame:
            break
        avg_line += line
    avg_line = avg_line / pre_frame

    return avg_line

def set_rpos(img_1, lines, color=[0,0,255], thickness=2):
    global rpos
    if lines is not None:
           for line in lines:
                for x1,y1,x2,y2 in line:
                    global rpos,rpos_prev
                    if (x1>400) and (y1==315):
                        rpos=x1
                    else:
                        pass
    return rpos

def set_lpos(img_1, lines, color=[0,0,255], thickness=2):
    if lines is not None:
           for line in lines:
                for x1,y1,x2,y2 in line:
                    global lpos,lpos_prev
                    if (x1<230) and (y1==315):
                        lpos=x1
                    else:
                        pass
    return lpos


def line_existence(img_1, lines, color=[0, 0, 255], thickness=2):
    if lines is not None:
        global rpos_exist
        global lpos_exist
        global R_turn,L_turn

        for line in lines:
            for x1,y1,x2,y2 in line:
                if (x1<100):
                    left_rec=x1
                    rpos_exist=rpos_exist+1
                    if rpos_exist==500:
                        print("lefline")
                        rpos_exist=0
                        R_turn=1
                    else:
                        pass
                else:
                    pass

                if (x1>560):
                    right_rec=x1
                    lpos_exist=lpos_exist+1
                    if lpos_exist==500:
                        print("rightline")
                        lpos_exist=0
                        L_turn=1
                    else:
                        pass
                else:
                    pass

                if lpos_exist>=200 and rpos_exist>=200:
                    print("double")
                    rpos_exist=0
                    lpos_exist=0
                    R_turn=0
                    L_turn=0
                else:
                    pass

    else:
        pass
    return 

def LPF(raw_data,sensor_value,filtered_value,sensitivity=0.05):
    sensor_value=raw_data
    filtered_value=filtered_value*(1-sensitivity)+sensor_value*sensitivity
    return filtered_value


def draw_rectangle(img_1, lpos, rpos, offset=0):
    center = (lpos + rpos) / 2

    cv2.rectangle(img_1, (lpos - 25, 15 + offset),
                       (lpos -15, 25 + offset),
                       (0, 255, 0), 2)
    cv2.rectangle(img_1, (rpos + 5, 15 + offset),
                       (rpos + 15, 25 + offset),
                       (0, 255, 0), 2)   
    cv2.rectangle(img_1, (center-5, 15 + offset),
                       (center+ 5, 25 + offset),
                       (0, 0, 255), 2)   


    return img_1


def draw_lines(img_1, lines, color=[0,0,255], thickness=2):
    if lines is not None:
           for line in lines:
              for x1,y1,x2,y2 in line:
                  cv2.line(img, (x1, y1), (x2, y2), color, thickness)

def final_lines(img_1, rho, theta, threshold, min_line_len, max_line_gap):
    global rpos, lpos,center, R_sensor_value, R_filtered_value, L_sensor_value, L_filtered_value
    lines = cv2.HoughLinesP(img_1, rho, theta, threshold, np.array([]), minLineLength=min_line_len, maxLineGap=max_line_gap)
    line_img = np.zeros((img_1.shape[0], img_1.shape[1], 3), dtype=np.uint8)
    smoothing(lines,3)
    draw_lines(line_img, lines)

    rpos=set_rpos(line_img, lines) 
    lpos=set_lpos(line_img, lines)
    line_existence(line_img, lines)
    R_filtered_value=LPF(rpos,R_sensor_value,R_filtered_value,0.8)
    L_filtered_value=LPF(lpos,L_sensor_value,L_filtered_value,0.8)
    rpos=int(R_filtered_value)
    lpos=int(L_filtered_value)   
    
    if R_turn==1:
        rpos=620    
    if L_turn==1:
        lpos=20

    draw_rectangle(line_img, lpos, rpos,310)
    cv2.line(line_img,(rpos+10,325),(640,385),(0, 255, 0),4)
    cv2.line(line_img,(lpos - 20, 325),(10, 410),(0, 255, 0),4) 
    center = (lpos + rpos) / 2
    cv2.rectangle(line_img, (335, 325),
                       (345, 335),
                       (255, 0, 0), 2)  

    return line_img

def weighted_img(img_1, initial_img, a=1, b=1.0, c=0.0):
    return cv2.addWeighted(initial_img, a, img_1, b, c)



#==============================================================================================


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
    global velocity,steering,breakcontrol,gear, image, img, motor, STEER_filtered_value, count, cap
    
    rospy.init_node('teleop', anonymous=True)
    # rospy.Subscriber("/move_base_simple/goal", PoseStamped, callback)
    rate = rospy.Rate(10) # 10hz
    # try:
    status = 0

    while not rospy.is_shutdown():
        img = cap.copy()  
        height, width = img.shape[:2]
        gray_img = grayscale(img)
        blur_img = gaussian_blur(gray_img, 3) 
        canny_img = canny(blur_img, 70, 210) 
        vertices = np.array([[(-135,height),(width/2-90, height/2+50), (width/2+90, height/2+50), (width+110,height)]], dtype=np.int32)
        roi_img = region_of_interest(canny_img, vertices,(0,0,255))
        hough_img = final_lines(roi_img, 1, 1 * np.pi/180, 30, 0.01, 0.1)
        result = weighted_img(hough_img, img)

        cv2.imshow('roi_white',result)      
        cv2.imshow("CAM View", img)
        cv2.waitKey(1)  

        pubmsg = Twist()
        pubmsg.linear.x = velocity
        pubmsg.angular.z = steering
        publisher.publish(pubmsg)
        print('cmd : ' + str(velocity) + ','+ str(steering))
        #rate.sleep()



    rospy.spin()

if __name__ == '__main__':
    try:
        teleop()
    except rospy.ROSInterruptException: pass
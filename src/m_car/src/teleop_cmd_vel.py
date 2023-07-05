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
    rospy.init_node('teleop', anonymous=True)
#    rospy.Subscriber("/move_base_simple/goal", PoseStamped, callback)
    rate = rospy.Rate(50) # 10hz
#    try:
    status = 0
    while not rospy.is_shutdown():    
        key = getkey()
        if key == 'w':
            velocity = velocity + 2
            steering = 0 
            status = status + 1
        elif key == 's':
            velocity = 0
            steering = 0
            status = status + 1
        elif key == 'a':
            steering = steering + 2
            status = status + 1
        elif key == 'd':
            steering = steering - 2
            status = status + 1
        elif key == 'x':
            velocity = velocity - 2
            steering = 0
            status = status + 1
        else:
            if (key == '\x03'):
                break
        if steering >= 20:
            steering = 20
        if steering <= -20:
            steering = -20
        if velocity >= MAX_Velocity:
            velocity = MAX_Velocity
        if velocity <= -MAX_Velocity:
            velocity = -MAX_Velocity
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
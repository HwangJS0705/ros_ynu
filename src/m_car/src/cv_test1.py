import cv2
import numpy as np

cap1 = cv2.VideoCapture(2)
# cap2 = cv2.VideoCapture(4)

while 1:
    ret, src = cap1.read()
    # ret1, src1 = cap2.read()
    
    cv2.imshow('roi_white',src)      
    # cv2.imshow("CAM View", src1)
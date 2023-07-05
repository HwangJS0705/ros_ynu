import cv2
import math
import numpy as np
from cv_bridge import CvBridge
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

cap = cv2.VideoCapture(4)
k = 0

def roi_image(image):
    (x,y),(w,h) = (100,400),(350,700)
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
    return cv2.GaussianBlur(src, (kernel_size, kernel_size), 5)

def canny(src, low_threshold, high_threshold):
    return cv2.Canny(src, low_threshold, high_threshold)


while (True):
    
    kernel_size = 5
    low_threshold = 50
    high_threshold = 200
    ret, src = cap.read()
    src = cv2.resize(src, (640, 480))
    src = roi_image(src)
    gray_src = grayscale(src)
    blur_src = gaussian_blur(gray_src, kernel_size)
    canny_src = canny(blur_src, low_threshold, high_threshold)
    
    cv2.imshow('test2', src)
    cv2.imshow('test1', canny_src)
    
    
      
    white_src = white_filter(src)
    white_dst = cv2.Canny(white_src, 300, 600, None, 3)
    white_cdst = cv2.cvtColor(white_dst, cv2.COLOR_GRAY2BGR)
    white_cdstP = np.copy(white_cdst)
    stop_lines = cv2.HoughLines(white_dst, 1, 5*np.pi / 180, 150, None, 0, 0, 88, 93)
    if stop_lines is not None:
        for i in range(0, len(stop_lines)):
            # global pt1, pt2
            rho = stop_lines[0][0][0]
            theta = stop_lines[0][0][1] 
            a = math.cos(theta)
            b = math.sin(theta)
            x0 = a * rho
            y0 = b * rho
            pt1 = (int(x0 + 1000 * (-b)), int(y0 + 1000 * (a))) 
            pt2 = (int(x0 - 1000 * (-b)), int(y0 - 1000 * (a))) 
            cv2.line(white_cdst, pt1, pt2, (0, 0, 255), 2, cv2.LINE_AA) 
            print(k)
            k+=1
            
    stop_linesP = cv2.HoughLinesP(white_dst, 1, 15*np.pi /180, 2, None, 150, 1) 
    # if stop_linesP is not None:
    #     for i in range(0, len(stop_linesP)):
    #         global pt1, pt2
    #         l = stop_linesP[i][0]
    #         cv2.line(white_cdstP, (l[0], l[1]), (l[2], l[3]), (0, 0, 255), 2, cv2.LINE_AA)
    #         cv2.line(white_cdst, pt1, pt2, (255, 0, 0), 2, cv2.LINE_AA) 
    #         print("hh")
    # cv2.imshow('roi_white',result) 
    # cv2.imshow("Source", src)
    # cv2.imshow("Stop Lines (in red) - Standard Hough Line Transform", white_cdst)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release(10)
cv2.destroyAllWindows()
# -*- coding: utf-8 -*-
import cv2
import math
import sys
import numpy as np
from math import *
import traceback
import tellopy
import av
import time
import threading
from multiprocessing  import Process
from collections import deque
import socket
from autopiolot import *
from datetime import datetime
aruco = cv2.aruco
dictionary = aruco.getPredefinedDictionary(aruco.DICT_6X6_1000)
parameters =  aruco.DetectorParameters_create()
parameters.cornerRefinementMethod = aruco.CORNER_REFINE_CONTOUR

drone = tellopy.Tello()
#board = aruco.GridBoard_create(5, 7, 0.033, 0.0035, dictionary) 
board = aruco.GridBoard_create(8, 8,0.1515, 0.0585, dictionary) 
arucoMarkerLength = 0.0033
PI = 3.141592653

frameA = None
run_recv_thread = True


#udp_ip = "127.0.0.1"
#udp_port = 5555

#clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

#serverSock.bind((udp_ip, udp_port))

posQueue = deque([[0.0,0.0,0.0]])
#pos = np.random.randint(-10,10,size=(1,10,3))

def handler(event, sender, data, **args):
    drone = sender
    if event is drone.EVENT_FLIGHT_DATA:
       pass
        #print("event is coming")
       #print(data)

def init_logger():
    handler = StreamHandler()
    handler.setLevel(INFO)
    handler.setFormatter(Formatter("[%(asctime)s] [%(threadName)s] %(message)s"))
    logger = getLogger()
    logger.addHandler(handler)
    logger.setLevel(INFO)




class DroneReg():
    def __init__(self):
        self.worldPos = None
        self.cameraMatrix = np.load('./camPara/mtx.npy')
        self.distanceCoefficients = np.load('./camPara/dist.npy')

    def findARMarker(self,frame):
        self.frame =  frame
        self.corners, self.ids, self.rejectedImgPoints = aruco.detectMarkers(self.frame, dictionary)
        #aruco.drawDetectedMarkers(self.frame, self.corners, self.ids, (0,255,0))

    def show(self):
        cv2.imshow("result", self.frame)

    def getDistance(self):
        if len(self.corners) > 0:
            self.rvec, self.tvec, _ = aruco.estimatePoseSingleMarkers(self.corners, arucoMarkerLength, self.cameraMatrix, self.distanceCoefficients)
            G = np.mean(self.tvec, axis = 0)
            return G[0][2]

            #return self.tvec[0][0][2], self.tvec[1][0][2]
    def estimatePos(self):
        if len(self.corners) > 0:
            self.retval, self.rvec, self.tvec = aruco.estimatePoseBoard(self.corners, self.ids, board, self.cameraMatrix, self.distanceCoefficients)
            self.dst, jacobian = cv2.Rodrigues(self.rvec)
            self.extristics = np.matrix([[self.dst[0][0],self.dst[0][1],self.dst[0][2],self.tvec[0][0]],
                                        [self.dst[1][0],self.dst[1][1],self.dst[1][2],self.tvec[1][0]],
                                        [self.dst[2][0],self.dst[2][1],self.dst[2][2],self.tvec[2][0]],
                                        [0.0, 0.0, 0.0, 1.0]
                    ])
            #print(self.dst,self.tvec)
            #print("self.extr:", self.extristics)
            #print("self.extr.I:",self.extristics.I )
            #self.worldRot = cv2.Rodrigues(self.rvec_trs)
            self.extristics_I = self.extristics.I
            self.worldPos = [round(self.extristics_I[0,3]*100),\
                    round(self.extristics_I[1,3]*100),\
                    round(self.extristics_I[2,3]*100)]
            self.worldRotM = np.zeros(shape=(3,3))
            cv2.Rodrigues(self.rvec, self.worldRotM,  jacobian = 0 )
            self.worldRot = cv2.RQDecomp3x3(self.worldRotM)

            #self.worldPos = - self.tvec * self.rvec_trs 
            #print( self.tvec, self.rvec)
            #self.worldPos = [self.worldPos[0][0],self.worldPos[1][1],  self.worldPos[2][2]]
            print("X:%.0f " % (self.worldPos[0]),\
                    "Y:%.0f "% (self.worldPos[1]),\
                    "Z:%.0f "% (self.worldPos[2]),\
                    "rot:%.0f "% (self.worldRot[0][2]))
            #self.rvec, self.tvec, _ = aruco.estimatePoseSingleMarkers(self.corners[0], arucoMarkerLength, self.cameraMatrix, self.distanceCoefficients)
            if self.retval != 0:
                self.frame = aruco.drawAxis(self.frame, self.cameraMatrix, self.distanceCoefficients, self.rvec, self.tvec, 0.1)
            

    def getAngle(self):
            (roll_angle, pitch_angle, yaw_angle) =  self.rvec[0][0][0]*180/PI, self.rvec[0][0][1]*180/PI, self.rvec[0][0][2]*180/PI
            if pitch_angle < 0:
                roll_angle, pitch_angle, yaw_angle = -roll_angle, -pitch_angle, -yaw_angle
            return (roll_angle, pitch_angle, yaw_angle)

    def getExistMarker(self):
        return len(self.corners)


def recv_thread():
    global frameA
    global run_recv_thread
    global drone
    print('start recv_thread()')
    drone.connect()
    drone.wait_for_connection(60.0)
    drone.subscribe(drone.EVENT_FLIGHT_DATA, handler)
    drone.set_video_encoder_rate(4)
    drone.set_loglevel(drone.LOG_WARN)
    container = av.open(drone.get_video_stream())
    run_recv_thread = True
    while run_recv_thread:
        print("debug: ready to receive video frames...")
        for f in container.decode(video=0):
            frameA = f
        time.sleep(0.001)

            #if DroneVideo.worldPos is not None:
            #    messageToUdp = DroneVideo.worldPos
            #    messageToUdp = " ".join(str(x) for x in messageToUdp)
            #    clientSock.sendto(messageToUdp.encode(), (udp_ip, udp_port))
    




def main():
    try:
       # flightData = tellopy.FlightData()
        DroneVideo = DroneReg()
        frameCount = 0
        threading.Thread(target = recv_thread).start()
        #threading.Thread(target = showCamPos_thread).start()

        flyflag = False
        target = [2, 2, 2]
        count = 0
        #aa = cv2.imread("./Calibration_letter_chessboard_7x5.png")
        #cv2.imshow("result", aa)
        while run_recv_thread:
            if frameA is None :
                time.sleep(0.01)
            else:
                #---------show frame start-------------------------------#
                TimeStart = datetime.now()
                frameCount += 1
                frame = frameA
                im = np.array(frame.to_image())
                image = cv2.flip(im, 0)
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                #image = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
                
                #cv2.imshow('Original', image)
                DroneVideo.findARMarker(image)
                DroneVideo.estimatePos()
                aTimeEnd = datetime.now()
                aalltime  = aTimeEnd - TimeStart
                #$print(DroneVideo.getARPoint2())
                DroneVideo.show()
                if flyflag == True:
                    #targetAchived = True if abs(self.worldPos[0] - target[0])<3 and abs(self.worldPos[1]-\
                    #        target[1]) < 3 else False
                    AdjustX, AdjustY = sameAngleAutoflytoXY(DroneVideo.worldPos, DroneVideo.worldRot[0][2],target )
                    drone.flytoXYZ(AdjustX, AdjustY,0)
                    #drone.forward(AdjustY)
                    print("adjust: ",AdjustX, AdjustY)
                    #if targetAchived == True:
                    #    count += 1
                    #    if count % 2 == 1:
                    #        target = [15, 15, 15]
                    #    else:
                    #        target = [2,2,2]
                key = cv2.waitKey(1)
                if key & 0xFF == ord ('j'):
                    drone.down(20)
                if key & 0xFF == ord ('q'):
                    drone.up(20)
                elif key & 0xFF == ord ('k'):
                    drone.down(0)
                elif key & 0xFF == ord ('a'):
                    flyflag = True
                elif key & 0xFF == ord ('o'):
                    drone.clockwise(40)
                elif key & 0xFF == ord ('b'):
                    target= [100,100,100]
                    
                elif key & 0xFF == ord ('m'):
                    target= [20,20,20]
                

                elif key & 0xFF == ord ('o'):
                    drone.counter_clockwise(20)
                elif key & 0xFF == ord ('s'):
                    drone.counter_clockwise(0)
                    drone.forward(0)
                    drone.right(0)
                elif key & 0xFF == ord ('f'):
                    drone.takeoff()
                elif key & 0xFF == ord ('d'):
                    drone.land()
                    flyflag = False
                elif key & 0xFF == ord('t'):
                    cv2.imwrite (str(frameCount) + ".png", image)
                #test fly

               # if cv2.waitKey(5) & 0xFF == ord ('q'):
                #---------show frame end---------------------------------#
                #print("debug: got frame")
                TimeEnd = datetime.now()
                alltime  = TimeEnd - TimeStart
                print("all time: ",int(alltime.total_seconds()*1000),"ms", " aaaall time: ",int(aalltime.total_seconds()*1000),"ms")

    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        print(ex)
    finally:
        #drone.quit()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()

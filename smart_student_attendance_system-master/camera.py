import pickle
from imutils.video import WebcamVideoStream
import face_recognition
import glob
import tensorflow as tf
from keras.models import Sequential
from keras.layers import Conv2D, ZeroPadding2D, Activation, Input, concatenate
from keras.models import Model
from keras.layers.normalization import BatchNormalization
from keras.layers.pooling import MaxPooling2D, AveragePooling2D
from keras.layers.merge import Concatenate
from keras.layers.core import Lambda, Flatten, Dense
from keras.engine.topology import Layer
from keras import backend as K
import cv2
import os
import keras
import numpy as np
from numpy import genfromtxt
import pandas as pd
import tensorflow as tf
import utils
#from utils import LRN2D
import joblib
from keras.models import load_model
from face_recognition_code import recognition



class VideoCamera(object):
    def __init__(self):
        # Using OpenCV to capture from device 0. If you have trouble capturing
        # from a webcam, comment the line below out and use a video file
        # instead.

        self.stream = WebcamVideoStream(src=0).start()
        new_model = keras.models.load_model('test.h5', custom_objects={'tf': tf})

    def __del__(self):
        self.stream.stop()

    def predict(self,image):

        input_embeddings = recognition.create_input_image_embeddings()
        name,face_img = recognition.recognize_faces_in_cam(input_embeddings)
        return name,face_img
    def get_frame(self):
        image = self.stream.read()
        f = open("trainStatus.txt")
        for i in f:
            isTrained = int(i)
        if isTrained:
            # load again
            new_model = load_model('test.h5')
            file = open("trainStatus.txt", "w")
            file.write("0")
            file.close()
        predictions = self.predict(image)
        name = ''
        for name, (top, right, bottom, left) in predictions:
            startX = int(left)
            startY = int(top)
            endX = int(right)
            endY = int(bottom)

            cv2.rectangle(image, (startX, startY), (endX, endY), (0, 255, 0), 2)
            cv2.putText(image, name, (endX - 70, endY - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)

        ret, jpeg = cv2.imencode('.jpg', image)
        data = []
        data.append(jpeg.tobytes())
        data.append(name)
        return data

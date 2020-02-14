import cereal
import numpy as np
import sys
import time
from selfdrive.traffic import traffic_wrapper
import cv2


W, H = 1164, 874
y_hood_crop = 665
traffic_model, ffi = traffic_wrapper.get_wrapper()
traffic_model.init_model()
data_dir = '/data/openpilot/selfdrive/traffic/test_images'

image = cv2.imread('{}/GREEN/{}'.format(data_dir, '20200210202741.0.png')).astype(np.float16)
image = image / 255.0
print(image.shape)
image = image.flatten().tolist()
print(len(image))
print(type(image))
image = image[:2322179]
print(type(image))
print(len(image))

ap = ffi.new("float[6]")
arr=np.array[1,2,3,4,5,6]
ap.cast(arr.ctypes.data)
ap = ffi.cast(arr.ctypes.data)

pred = traffic_model.predict_traffic(ap)
print(pred)



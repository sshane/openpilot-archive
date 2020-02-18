import cereal
import numpy as np
import sys
import time
from selfdrive.traffic import traffic_wrapper
import cv2
import ctypes

# traffic_model, ffi = traffic_wrapper.get_wrapper()
# traffic_model.initModel()
# # traffic_model.visionTest()

W, H = 1164, 874
y_hood_crop = 665
traffic_model, ffi = traffic_wrapper.get_wrapper()
traffic_model.initModel()
data_dir = '/data/openpilot/selfdrive/traffic/test_images'

image = cv2.imread('{}/RED/{}'.format(data_dir, '20200211001955.0.png'))
print(image.dtype)
image = image  # / 255.0
print(image.shape)
image = image.flatten().tolist()
print(len(image))
print(type(image))

ap = ffi.new("int[1257630]", image)
op = ffi.new("float[4]")
r = 50
t = time.time()
for _ in range(r):
    traffic_model.predictTraffic(ap, op)
print(time.time() - t)
spp = (time.time() - t) / r
print('{} seconds/prediction'.format(round(spp, 6)))
print('Potential model rate: {}'.format(round(1 / spp, 6)))
print(list(op))


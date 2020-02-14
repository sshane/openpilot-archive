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

image = cv2.imread('{}/GREEN/{}'.format(data_dir, '20200210202741.0.png'))
print(image.dtype)
# image = image / 255.0
print(image.shape)
image = image.flatten().tolist()
print(len(image))
print(type(image))
image = image[:2322180]
print(type(image))
print(len(image))

ap = ffi.new("int[2322180]", image)

t = time.time()
for _ in range(100):
    pred = traffic_model.predict_traffic(ap)
print(time.time() - t)
# print(pred)



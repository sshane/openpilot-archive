import time
from selfdrive.traffic import traffic_wrapper
import cv2
import numpy as np

traffic_model = traffic_wrapper.get_wrapper()
traffic_model.init_model()
start = time.time()

W, H = 1164, 874

img = cv2.imread('/data/openpilot/selfdrive/traffic/GREEN.png')
img = cv2.resize(img, dsize=(W // 2, H // 2), interpolation=cv2.INTER_CUBIC)
img = np.asarray(img) / 255
for i in range(100):
  model_output = traffic_model.run_model()

print('Took: {} seconds'.format(time.time() - start))
print(model_output)

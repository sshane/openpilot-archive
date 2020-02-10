import tflite_runtime.interpreter as tflite
import cv2
import numpy as np
import os
import time
import pickle

os.chdir('/data/openpilot/selfdrive/traffic')
W, H = 1164, 874

# img = cv2.imread('/data/openpilot/selfdrive/traffic/GREEN_high.png')
# img = cv2.resize(img, dsize=(W // 2, H // 2), interpolation=cv2.INTER_CUBIC)
# img = np.asarray(img, dtype=np.float32) / 255.  # normalize
with open('/data/openpilot/selfdrive/traffic/phot_none_9989287', 'rb') as f:
    img = np.array([pickle.load(f)])
print(img)
print(img.shape)

print(img.dtype)

interpreter = tflite.Interpreter(model_path='newest.tflite')
# print(dir(interpreter))
interpreter.allocate_tensors()

t = time.time()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
print(input_details)

input_shape = input_details[0]['shape']
print('Model input shape: {}'.format(input_shape))
# input_data = np.array(np.random.random_sample(input_shape), dtype=np.float32)
interpreter.set_tensor(input_details[0]['index'], img)

interpreter.invoke()

output_data = interpreter.get_tensor(output_details[0]['index'])
print(time.time()-t)
print(output_data)
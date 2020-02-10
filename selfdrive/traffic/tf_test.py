import tflite_runtime.interpreter as tflite
import cv2
import numpy as np
import os

os.chdir('/data/openpilot/selfdrive/traffic')
W, H = 1164, 874

img = cv2.imread('/data/openpilot/selfdrive/traffic/GREEN_high.png')
img = cv2.resize(img, dsize=(W // 2, H // 2), interpolation=cv2.INTER_CUBIC)


print(img.shape)

interpreter = tflite.Interpreter(model_path='model.tflite')
print(dir(interpreter))
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

input_shape = input_details[0]['shape']
print('Model input shape: {}'.format(input_shape))
# input_data = np.array(np.random.random_sample(input_shape), dtype=np.float32)
interpreter.set_tensor(input_details[0]['index'], img)

interpreter.invoke()

output_data = interpreter.get_tensor(output_details[0]['index'])
print(output_data)
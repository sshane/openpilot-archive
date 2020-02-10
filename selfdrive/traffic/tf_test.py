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

print(input_details)
print(output_details)
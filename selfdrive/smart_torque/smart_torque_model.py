"""
  Generated using Konverter: https://github.com/ShaneSmiskol/Konverter
"""

import numpy as np

wb = np.load('/data/openpilot/selfdrive/smart_torque/smart_torque_model_weights.npz', allow_pickle=True)
w, b = wb['wb']

def simplernn(x, idx):
  print(w[idx][0].shape[1])
  print(x.shape[0])
  states = [np.zeros(w[idx][0].shape[1], dtype=np.float32)]
  for step in range(x.shape[0]):
    states.append(np.tanh(np.dot(x[step], w[idx][0]) + np.dot(states[-1], w[idx][1]) + b[idx]))
  return np.array(states[1:])

def predict(x):
  l0 = simplernn(x, 0)
  l1 = simplernn(l0, 1)[-1]
  l2 = np.dot(l1, w[2]) + b[2]
  l2 = np.maximum(0, l2)
  l3 = np.dot(l2, w[3]) + b[3]
  l3 = np.maximum(0, l3)
  l4 = np.dot(l3, w[4]) + b[4]
  return l4

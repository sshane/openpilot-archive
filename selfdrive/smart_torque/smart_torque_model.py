"""
  Generated using Konverter: https://github.com/ShaneSmiskol/Konverter
"""

import numpy as np

wb = np.load('/data/openpilot/selfdrive/smart_torque/smart_torque_model_weights.npz', allow_pickle=True)
w, b = wb['wb']

def sigmoid(x):
  return 1 / (1 + np.exp(-x))

def gru(x, idx, units):
  states = [np.zeros(units, dtype=np.float32)]
  for step in range(100):
    x_ = np.split(np.matmul(x[step], w[idx][0]) + b[idx][0], 3, axis=-1)
    recurrent = np.split(np.matmul(states[-1], w[idx][1]) + b[idx][1], 3, axis=-1)
    z = sigmoid(x_[0] + recurrent[0])
    states.append(z * states[-1] + (1 - z) * np.tanh(x_[2] + sigmoid(x_[1] + recurrent[1]) * recurrent[2]))
  return np.array(states[1:])

def predict(x):
  l0 = gru(x, 0, 64)
  l1 = gru(l0, 1, 64)
  l2 = gru(l1, 2, 64)
  l3 = gru(l2, 3, 64)[-1]
  l4 = np.dot(l3, w[4]) + b[4]
  l4 = np.maximum(0, l4)
  l5 = np.dot(l4, w[5]) + b[5]
  l5 = np.maximum(0, l5)
  l6 = np.dot(l5, w[6]) + b[6]
  l6 = np.maximum(0, l6)
  l7 = np.dot(l6, w[7]) + b[7]
  return l7

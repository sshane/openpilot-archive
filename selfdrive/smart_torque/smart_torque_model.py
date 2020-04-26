"""
  Generated using Konverter: https://github.com/ShaneSmiskol/Konverter
"""

import numpy as np

wb = np.load('/data/openpilot/selfdrive/smart_torque/smart_torque_model_weights.npz', allow_pickle=True)
w, b = wb['wb']
ws = {0: 64, 1: 32}

def simplernn(x, idx):
  states = [np.zeros(ws[idx], dtype=np.float32)]
  for step in range(50):
    states.append(np.tanh(np.matmul(x[step], w[idx][0]) + np.matmul(states[-1], w[idx][1]) + b[idx]))
  return np.array(states[1:])

def predict(x):
  l0 = simplernn(x, 0)
  l1 = simplernn(l0, 1)[-1]
  l2 = np.matmul(l1, w[2]) + b[2]
  l2 = np.maximum(0, l2)
  l3 = np.matmul(l2, w[3]) + b[3]
  l3 = np.maximum(0, l3)
  l4 = np.matmul(l3, w[4]) + b[4]
  return l4

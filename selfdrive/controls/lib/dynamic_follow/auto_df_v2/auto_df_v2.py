"""
  Generated using Konverter: https://github.com/ShaneSmiskol/Konverter
"""

import numpy as np

wb = np.load('/data/openpilot/selfdrive/controls/lib/dynamic_follow/auto_df_v2/auto_df_v2_weights.npz', allow_pickle=True)
w, b = wb['wb']

def gru(x, idx, units):
  states = [np.zeros(units, dtype=np.float32)]
  for step in range(9):
    x_ = np.split(np.matmul(x[step], w[idx][0]) + b[idx][0], 3, axis=-1)
    recurrent = np.split(np.matmul(states[-1], w[idx][1]) + b[idx][1], 3, axis=-1)
    z = sigmoid(x_[0] + recurrent[0])
    states.append(z * states[-1] + (1 - z) * np.tanh(x_[2] + sigmoid(x_[1] + recurrent[1]) * recurrent[2]))
  return np.array(states[1:])

def sigmoid(x):
  return 1 / (1 + np.exp(-x))

def predict(x):
  x = np.array(x, dtype=np.float32)
  l0 = gru(x, 0, 16)
  l1 = gru(l0, 1, 32)[-1]
  l2 = np.dot(l1, w[2]) + b[2]
  l2 = np.where(l2 > 0, l2, l2 * 0.3)
  l3 = np.dot(l2, w[3]) + b[3]
  l3 = np.where(l3 > 0, l3, l3 * 0.3)
  l4 = np.dot(l3, w[4]) + b[4]
  l4 = np.where(l4 > 0, l4, l4 * 0.3)
  l5 = np.dot(l4, w[5]) + b[5]
  return l5

"""
  Generated using Konverter: https://github.com/ShaneSmiskol/Konverter
"""

import numpy as np

wb = np.load('/data/openpilot/auto_feedforward/ff_model_weights.npz', allow_pickle=True)
w, b = wb['wb']

def predict(x):
  x = np.array(x, dtype=np.float32)
  l0 = np.dot(x, w[0]) + b[0]
  l0 = np.tanh(l0)
  l1 = np.dot(l0, w[1]) + b[1]
  return l1

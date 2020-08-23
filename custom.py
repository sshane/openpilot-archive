import numpy as np
import random


param = 1.
desired = 5.5

results = []

runs = 50
learning_rate = 1 / 10.

for _ in range(runs):
  error1 = abs(param - desired)

  change = np.random.uniform(-1, 1)
  param += change
  print(error1)
  error2 = abs(param - desired)
  print(error2)
  results.append({'divergence': error2 - error1, 'tuned': change})
  print(results)
  input()




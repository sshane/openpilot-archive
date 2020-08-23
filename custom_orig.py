import numpy as np
import random


params = np.array([1., 1.])
desired = np.array([2., 2.])
last_probabilities = np.array([0., 0.])
probabilities = np.array([.24, .98])


runs = 5
learning_rate = 1 / 10.
last_error = np.sum(np.abs(params - desired))

for _ in range(runs):
  error = np.sum(np.abs(params - desired))
  print('error: {}'.format(error))
  change_in_error = error - last_error
  print('change_in_error: {}'.format(change_in_error))

  change_in_probabilities = probabilities - last_probabilities
  print('probabilities: {}'.format(probabilities))
  sum_p = np.sum(np.abs(change_in_probabilities))
  print('change_in_probabilities: {}'.format(change_in_probabilities))
  change_in_probabilities /= sum_p
  print('change_in_probabilities normalized: {}'.format(change_in_probabilities))
  probabilities *= (change_in_probabilities + error)

  print('new probabilities: {}'.format(probabilities))

  last_error = float(error)
  last_probabilities = probabilities.copy()
  params += probabilities
  input()

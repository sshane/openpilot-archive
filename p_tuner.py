import numpy as np
import random


params = np.array([1., 1.])
desired = np.array([2., 2.])
last_probabilities = np.array([0., 0.])
probabilities = np.array([.24, .98])


runs = 5
learning_rate = 1 / 10.
last_error = np.sum(np.abs(params - desired))


error = np.sum(np.abs(params - desired))
change = np.random.uniform(-1, 1, 2)
params += change
print(error)
error = np.sum(np.abs(params - desired))
print(error)




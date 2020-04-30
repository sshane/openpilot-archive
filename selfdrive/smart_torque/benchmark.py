from selfdrive.smart_torque.smart_torque_model import predict
import numpy as np
import time

t = time.time()
samples = np.random.rand(2000, 200*3).astype(np.float32)
for s in samples:
  predict(s)
t = time.time() - t
print('Time: {} sec'.format(round(t, 4)))
print('Rate: {} Hz'.format(round(len(samples) / t, 4)))
print('Average time: {} sec'.format(round(t / len(samples), 8)))

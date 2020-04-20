import numpy as np
import time
from selfdrive.smart_torque.dense_model import predict

samples = np.random.rand(10000, 103).tolist()
print('samples: {}\n'.format(len(samples)))

t = time.time()
predict(samples)
t = time.time() - t
print('Konverted model batch prediction time: {}s'.format(round(t, 6)))

print('-----')

t = time.time()
konverter_preds = []
for i in samples:
  predict(i)
t = time.time() - t
print('Konverted model single prediction time: {}s'.format(round(t, 6)))
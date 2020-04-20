import time
from selfdrive.smart_torque import st_wrapper
import numpy as np

st_model = st_wrapper.get_wrapper()
st_model.init_model()
start = time.time()
samples = np.random.rand(100, 103)
for i in range(samples):
  model_output = st_model.run_model(i)

print('Took: {} seconds'.format(time.time() - start))
print(model_output)


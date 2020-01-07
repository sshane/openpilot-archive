import time
from selfdrive.smart_torque import st_wrapper

st_model = st_wrapper.get_wrapper()
st_model.init_model()
start = time.time()
for i in range(100):
  model_output = st_model.run_model([.5]*103)

print('Took: {} seconds'.format(time.time() - start))
print(model_output)


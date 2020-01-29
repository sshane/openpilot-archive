import time
from selfdrive.df import df_wrapper

df_model = df_wrapper.get_wrapper()
df_model.init_model()
start = time.time()
for i in range(100):
  model_output = df_model.run_model([.5] * 49)

print('Took: {} seconds'.format(time.time() - start))
print(model_output)


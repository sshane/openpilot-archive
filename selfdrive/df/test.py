import time
from selfdrive.df import df_wrapper
df_model = df_wrapper.get_wrapper()
df_model.init_model()
start = time.time()
for i in range(30):
 model_output = df_model.run_model(0.8653078153514447,
  0.46805728618371273,
  0.46805728618371273,
  0.28780443294609244,
  0.01075646532123655)
print(time.time() - start)
model_output = df_model.run_model(29.02843475,  0.35738668, 30.92068291, 30.125,  0.31128621)
print(model_output)

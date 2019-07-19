import time
from selfdrive.df import df_wrapper
df_model = df_wrapper.get_wrapper()
df_model.init_model()
'''start = time.time()
for i in range(30):
 model_output = df_model.run_model(0.8653078153514447,
  0.46805728618371273,
  0.46805728618371273,
  0.28780443294609244,
  0.01075646532123655)
print(time.time() - startl)'''
pred = df_model.test_fun([0.5, 0.4, 0.4]*10)
print(pred)
'''model_output = df_model.run_model(.5, .5, .2, .1, .5)
print(model_output)
model_output = df_model.run_model(.05, .5, .3, .4, .6)
print(model_output)
model_output = df_model.run_model(.7, .5, .85, .55, .5)
print(model_output)'''

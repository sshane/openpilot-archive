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

input_data = [[.6, .6, .55]]
for i in range(29):
    input_data.append([input_data[-1][0]-.003, input_data[-1][1], input_data[-1][2]-.001])
input_data = sum(input_data, [])
pred = df_model.run_model_lstm(input_data)
print(pred)
'''model_output = df_model.run_model(.5, .5, .2, .1, .5)
print(model_output)
model_output = df_model.run_model(.05, .5, .3, .4, .6)
print(model_output)
model_output = df_model.run_model(.7, .5, .85, .55, .5)
print(model_output)'''

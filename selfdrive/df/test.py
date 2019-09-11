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

df_input = [0.19223077, 0.49374455, 0.45246605, 0.60768255, 0.,
            0., 1., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0.39866667, 0.09543314, 0.71238349,
            0.40266666, 0.09481876, 0.71271639, 0.49066667, 0.0468974,
            0.70173103, 0.49333333, 0.04669261, 0.70239681, 0.504,
            0.13905387, 0.73335553, 0.572, 0.09481876, 0.59853529,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.]

#s = time.time()

for i in range(100):
  model_output = df_model.run_model_live_tracks(df_input)
  print("Model output: {}".format(model_output))


model_output = df_model.run_model_live_tracks(df_input)
print("Model output: {}".format(model_output))


#print(time.time()-s)
'''model_output = df_model.run_model(.3, 0.0, .3, .5)
print(model_output)
model_output = df_model.run_model(.05, .3, .4, .6)
print(model_output)
model_output = df_model.run_model(.7, .85, .55, .5)
print(model_output)'''
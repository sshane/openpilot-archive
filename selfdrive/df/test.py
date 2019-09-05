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

data = [0.88556903, 0.4255532, 0.37684943, 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0.31466667, 0.46783504, 0.27668118, 0.32283465, 1.,
        0.5, 0.6251546, 0.65473403, 0.49606299, 1.,
        0.50133333, 0.21587628, 0.6918702, 0.53543307, 1.,
        0.50133333, 0.21567011, 0.69086652, 0.53543307, 1.,
        0.50133333, 0.22659794, 0.6918702, 0.50393701, 1.,
        0.59733334, 0.29731957, 0.67079291, 0.50393701, 1.,
        0.59866667, 0.29752576, 0.67213115, 0.60629921, 1.,
        0.608, 0.6620618, 0.66677819, 0.51968504, 1.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.]

s = time.time()
for i in range(39):
  model_output = df_model.run_model_live_tracks(data)

model_output = df_model.run_model_live_tracks(data)

print(model_output)
print(time.time()-s)
'''model_output = df_model.run_model(.3, 0.0, .3, .5)
print(model_output)
model_output = df_model.run_model(.05, .3, .4, .6)
print(model_output)
model_output = df_model.run_model(.7, .85, .55, .5)
print(model_output)'''
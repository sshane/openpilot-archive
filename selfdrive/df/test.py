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
s = time.time()
data = [0.47091574, 0.48880402, 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0.50133333, 0.13730304, 0.66645286, 1.,
        0.504, 0.13730304, 0.66805645, 1., 0.696,
        0.08123593, 0.24983964, 1., 0.73333333, 0.43523631,
        0.44194997, 1., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0.]
for i in range(1000):
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
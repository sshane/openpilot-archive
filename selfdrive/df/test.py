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
data = [0.18767295, 0.47943065, 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0.37733333, 0.0726417,
        0.57184093, 1., 0.392, 0.10926948, 0.57152021,
        1., 0.4, 0.14507877, 0.56927518, 1.,
        0.40266666, 0.18416205, 0.56927518, 1., 0.46266667,
        0.15469613, 0.57023734, 1., 0.50533333, 0.12052384,
        0.57087878, 1., 0.632, 0.16247186, 0.57152021,
        1., 0.66000001, 0.19787189, 0.57152021, 1.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0., 0., 0., 0., 0.,
        0.]

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
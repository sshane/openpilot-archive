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

df_input = [0.82767506, 0.4288575, 0.37597911, 1., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0.444, 0.12474227, 0.62395451, 0.4488189, 1.,
            0.45466667, 0.1243299, 0.62295083, 0.48818898, 1.,
            0.56133333, 0.10206186, 0.71060556, 0.54330709, 1.,
            0.56266667, 0.10206186, 0.70960188, 0.46456693, 1.,
            0.6, 0.10948453, 0.70993644, 0.33858268, 1.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
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
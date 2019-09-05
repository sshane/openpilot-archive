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

df_input = [0.50559583, 0.42775607, 0.37859008, 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.]

df_input2 = [0.00269265, 0.42665463, 0.37684943, 1., 0.,
             0., 0., 0., 0., 0.,
             0., 0., 0., 0., 0.,
             0., 0., 0., 0., 0.,
             0.424, 0.39628866, 0.84476414, 0.51968504, 1.,
             0.45333333, 0.07876289, 0.68618268, 0.50393701, 1.,
             0.52133333, 0.06701031, 0.66912011, 0.50393701, 1.,
             0.56266667, 0.14865979, 0.69387756, 0.50393701, 1.,
             0.64133333, 0.31072164, 0.62060891, 0.22047244, 1.,
             0.65466666, 0.23690721, 0.6801606, 0.50393701, 1.,
             0.65466666, 0.30865978, 0.62529275, 0.51968504, 1.,
             0.65866667, 0.23690721, 0.6801606, 0.50393701, 1.,
             0.74933333, 0.28164948, 0.67982604, 0.50393701, 1.,
             0.87466666, 0.24515463, 0.68116428, 0.50393701, 1.,
             0., 0., 0., 0., 0.,
             0., 0., 0., 0., 0.,
             0., 0., 0., 0., 0.]

#s = time.time()

for i in range(100):
  model_output = df_model.run_model_live_tracks(df_input)
  print("Model output: {}".format(model_output))
  model_output = df_model.run_model_live_tracks(df_input2)
  print("Model output: {}".format(model_output))


model_output = df_model.run_model_live_tracks(df_input)
print("Model output: {}".format(model_output))
model_output = df_model.run_model_live_tracks(df_input2)
print("Model output: {}".format(model_output))


#print(time.time()-s)
'''model_output = df_model.run_model(.3, 0.0, .3, .5)
print(model_output)
model_output = df_model.run_model(.05, .3, .4, .6)
print(model_output)
model_output = df_model.run_model(.7, .85, .55, .5)
print(model_output)'''
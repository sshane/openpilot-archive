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

df_input = [0.25796314, 0.49061683, 0.45389564, 0.42270676, 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.,
            0., 0., 0., 0., 0.376,
            0.07618268, 0.56957391, 0.37733333, 0.15461806, 0.61917444,
            0.38133334, 0.14560721, 0.56657791, 0.39333333, 0.17878354,
            0.56557923, 0.4, 0.19250462, 0.60652464, 0.4,
            0.20417776, 0.56591213, 0.44, 0.41286097, 0.56524635,
            0.50133333, 0.43088266, 0.56491346, 0., 0.,
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
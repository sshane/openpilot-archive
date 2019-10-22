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

df_input = [0.07935380707331754, 0.48409070810214455, 0.4947692307692308, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.45383487328989697, 0.1470767929873602, 0.6097099641935587,
            0.4723986255116041, 0.14463230561343307, 0.6081336716564076, 0.5105031700820197, 0.14524343231367956,
            0.6097099641935587, 0.5339521200269284, 0.12976165951841565, 0.6090794447734668, 0.5373717582875792,
            0.1285394158314521, 0.6075031522363157, 0.5613092290239396, 0.22305968171173213, 0.6097099641935587, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

#s = time.time()


model_output = df_model.run_model_live_tracks(df_input)
print("Model output: {}".format(model_output))


#print(time.time()-s)
'''model_output = df_model.run_model(.3, 0.0, .3, .5)
print(model_output)
model_output = df_model.run_model(.05, .3, .4, .6)
print(model_output)
model_output = df_model.run_model(.7, .85, .55, .5)
print(model_output)'''
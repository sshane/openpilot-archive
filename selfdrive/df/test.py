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

df_input = [0.0026889600053403235, 0.43496543793411613, 0.37684943429068757, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2933333396911621, 0.46639174563736013,
            0.6801605955634497, 1.0, 0.3800000031789144, 0.4362886332548297, 0.6801605955634497, 1.0,
            0.4106666644414266, 0.29237112098804974, 0.6801605955634497, 1.0, 0.42266666889190674, 0.29154637952985624,
            0.6808297156770637, 1.0, 0.498666666696469, 0.30680410633812927, 0.6801605955634497, 1.0, 0.5,
            0.4301030821500723, 0.6798260355066427, 1.0, 0.6306666692097982, 0.26845359903705146, 0.6804951556202566,
            1.0, 0.6440000057220459, 0.2678350478592532, 0.6801605955634497, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

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
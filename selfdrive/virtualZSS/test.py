import time
from selfdrive.virtualZSS import virtualZSS_wrapper
virtualZSS_model = virtualZSS_wrapper.get_wrapper()
virtualZSS_model.init_model()
'''start = time.time()
for i in range(30):
 model_output = virtualZSS_model.run_model(0.8653078153514447,
  0.46805728618371273,
  0.46805728618371273,
  0.28780443294609244,
  0.01075646532123655)
print(time.time() - startl)'''
for i in range(1000):
  model_output = virtualZSS_model.run_model_lstm([-0.006666666666666667,9.399999618530273])
  print(model_output) #10.320219039916992
  model_output = virtualZSS_model.run_model_lstm([-0.12266666666666666,1.899999976158142])
  print(model_output) #2.2325875759124756,
'''model_output = virtualZSS_model.run_model(.3, 0.0, .3, .5)
print(model_output)
model_output = virtualZSS_model.run_model(.05, .3, .4, .6)
print(model_output)
model_output = virtualZSS_model.run_model(.7, .85, .55, .5)
print(model_output)'''

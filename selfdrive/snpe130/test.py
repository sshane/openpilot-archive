import time
#lib1 = cdll.LoadLibrary("/data/openpilot/selfdrive/df/libs/libSNPE.so")
from selfdrive.snpe130 import wrapper

ffi, model = wrapper.get_model()
model.init_model()
start = time.time()
model_output = model.run_model(.542, .2, .15, .2, .5)
print('model output: {}'.format(model_output))
print('time to pred: {}'.format(time.time() - start))
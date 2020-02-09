import time
from selfdrive.traffic import traffic_wrapper
import cv2
import numpy as np

traffic_model, ffi = traffic_wrapper.get_wrapper()
traffic_model.init_model()
start = time.time()
# model_output = traffic_model.run_model()
# print(model_output)

def multi_test_b(x):
    dsize = ffi.sizeof("double")
    ap = ffi.new("double* [%d]" % 3)
    ptr = ffi.cast("double *", x.ctypes.data)
    for i in range(x.shape[0]):
        ap[i] = ptr + i*x.shape[1]
    traffic_model.multi_test(ap, x.shape[0], x.shape[1], x.shape[2])

multi_array = np.random.rand(2, 4, 5)

x = np.array(multi_array, dtype='float64')


multi_test_b(x)

# W, H = 1164, 874
#
# img = cv2.imread('/data/openpilot/selfdrive/traffic/GREEN.png')
# img = cv2.resize(img, dsize=(W // 2, H // 2), interpolation=cv2.INTER_CUBIC)
# img = np.asarray(img) / 255
# for i in range(100):
#   model_output = traffic_model.run_model()
#
# print('Took: {} seconds'.format(time.time() - start))
# print(model_output)

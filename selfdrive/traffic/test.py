import time
from selfdrive.traffic import traffic_wrapper
import cv2
import numpy as np
import pickle

traffic_model, ffi = traffic_wrapper.get_wrapper()
traffic_model.init_model()
# start = time.time()
# model_output = traffic_model.run_model()
# print(model_output)
# from cffi import FFI
#
# ffi = FFI()

def multi_test_a(x):
    ap = ffi.new("double [{}][{}][{}]".format(x.shape[0], x.shape[1], x.shape[2]))
    for i in range(x.shape[0]):
        ap[i] = ffi.cast("double [{}][{}]".format(x.shape[1], x.shape[2]), x[i].ctypes.data)
        for k in range(x.shape[1]):
            ap[i][k] = ffi.cast("double [{}]".format(x.shape[2]), x[i][k].ctypes.data)
    traffic_model.multi_test(ap, x.shape[0], x.shape[1], x.shape[2])

def multi_test_b(x):
    dsize = ffi.sizeof("double")
    ap = ffi.new("double* [{}][{}]".format(x.shape[0], x.shape[1]))
    ptr = ffi.cast("double *", x.ctypes.data)
    for i in range(x.shape[0]):
        for k in range(x.shape[1]):
            print(ap[i])
            ap[i][k] = ptr + i*x.shape[1] + i*x.shape[2]
            print(ap[i])
    traffic_model.multi_test(ap, x.shape[0], x.shape[1], x.shape[2])
    # C.multi_test(ap, x.shape[0], x.shape[1])


# def multi_test_b(x):
#     ap = ffi.new("double** [%d]" % (x.shape[0]))
#     ptr = ffi.cast("double **", x.ctypes.data)
#     for i in range(x.shape[0]):
#         ap[i] = ptr + i*x.shape[1]
#         for z in range(x.shape[1]):
#             ap[i][z] = ptr + i*x.shape[1]
#     print(ap)
#     # traffic_model.multi_test(ap, x.shape[0], x.shape[1], x.shape[2])

multi_array = np.random.rand(437, 582, 3)

x = np.array(multi_array, dtype='float64')
# print(x)



W, H = 1164, 874

# img = cv2.imread('/data/openpilot/selfdrive/traffic/GREEN_high.png')
# img = cv2.resize(img, dsize=(W // 2, H // 2), interpolation=cv2.INTER_CUBIC)
# cv2.imwrite('/data/openpilot/selfdrive/traffic/GREEN.png', img)
# img = np.asarray(img) / 255

with open('/data/openpilot/selfdrive/traffic/phot_none_9989287', 'rb') as f:
    img = np.array([pickle.load(f)]).astype('float32')

print(img.shape)
# img = img.reshape(582, 437, 3)
multi_test_a(img)
# for i in range(100):
#   model_output = traffic_model.run_model()
#
# print('Took: {} seconds'.format(time.time() - start))
# print(model_output)

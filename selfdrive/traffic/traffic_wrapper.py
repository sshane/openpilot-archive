from cffi import FFI
import subprocess
try:
    subprocess.check_call(["make", "-j4"], cwd="/data/openpilot/selfdrive/traffic")
except:
    pass


def get_wrapper():  # initialize st model and process long predictions
    libmpc_fn = "/data/openpilot/selfdrive/traffic/traffic.so"

    ffi = FFI()
    ffi.cdef("""    
    void init_model();
    float run_model();
    void multi_test(double inputArray[582][437][3], int x, int y, int z);
    int predict_traffic(float inputArray[100000]);
    """)

    return ffi.dlopen(libmpc_fn), ffi

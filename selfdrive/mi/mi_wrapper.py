from cffi import FFI
import subprocess
try:
    subprocess.check_call(["make", "-j4"], cwd="/data/openpilot/selfdrive/df")
except:
    pass

def get_wrapper():  # initialize df model and process long predictions
    libmpc_fn = "/data/openpilot/selfdrive/df/multi_input.so"

    ffi = FFI()
    ffi.cdef("""    
    float run_model(float a, float b);
    void init_model();
    float run_model_lstm(float inputData[60]);
    float run_model_live_tracks(float inputData[54]);
    """)

    return ffi.dlopen(libmpc_fn)
from cffi import FFI
import subprocess
try:
    subprocess.check_call(["make", "-j4"], cwd="/data/openpilot/selfdrive/df")
except:
    pass

def get_wrapper():  # initialize df model and process long predictions
    libmpc_fn = "/data/openpilot/selfdrive/df/dynamic_follow.so"

    ffi = FFI()
    ffi.cdef("""    
    float run_model(float v_ego, float v_lead, float x_lead, float a_lead, float a_rel);
    void init_model();
    float run_model_lstm(float testarr[30]);
    """)

    return ffi.dlopen(libmpc_fn)
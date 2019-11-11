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
    void init_model();
    float run_model(float v_ego, float v_lead, float x_lead, float a_lead);
    float run_model_live_tracks(float inputData[54]);
    """)

    return ffi.dlopen(libmpc_fn)

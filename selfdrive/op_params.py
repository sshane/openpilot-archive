import os
import json
import time


def write_config(params_file, params):
  with open(params_file, "w") as f:
    json.dump(params, f, indent=2, sort_keys=True)
  os.chmod(params_file, 0o764)

class opParams:
  def __init__(self):
    self.params_file = "/data/op_params.json"
    self.kegman_file = "/data/kegman.json"
    self.params = {}
    self.read_params()
    self.last_read_time = time.time()

  def read_params(self):
    default_params = {'cameraOffset': 0.06, 'wheelTouchSeconds': 300, 'lane_hug_direction': 'none',
                      'lane_hug_mod': 1.2, 'lane_hug_angle': 10}

    if os.path.isfile(self.params_file):
      try:
        with open(self.params_file, "r") as f:
          self.params = json.load(f)
      except:
        self.params = default_params
        return

      for i in default_params:
        if i not in self.params:
          self.params.update({i: default_params[i]})
    elif os.path.isfile(self.kegman_file):  # restores params from kegman.json
      try:
        with open(self.kegman_file, "r") as f:
          self.params = json.load(f)
      except:
        self.params = default_params
      write_config(self.params_file, self.params)
    else:
      self.params = default_params
      write_config(self.params_file, self.params)

  def put(self, key, value):
    self.params.update({key: value})
    write_config(self.params_file, self.params)

  def get(self, key=None, default=None):  # can specify a default value if key doesn't exist
    if time.time() - self.last_read_time >= 0.5:  # make sure we aren't reading file too often
      self.read_params()
      self.last_read_time = time.time()
    if key is None:  # get all
      return self.params
    else:
      return self.params[key] if key in self.params else default

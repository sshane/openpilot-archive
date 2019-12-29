import time
import cereal.messaging as messaging
from common.travis_checker import travis


class Phantom:
  def __init__(self, timeout=1.):
    self.sm = messaging.SubMaster(['phantomData'])
    self.data = {"status": False, "speed": 0.0}
    self.lost_connection = False
    self.last_receive_time = time.time()
    self.timeout = timeout  # in seconds

  def update(self):
    if not travis:
      self.sm.update(0)
      phantom_data = self.sm['phantomData']
      self.data = {"status": phantom_data.status, "speed": phantom_data.speed, "angle": phantom_data.angle}

      if self.sm.updated['phantomData']:
        self.last_receive_time = time.time()

      if time.time() - self.last_receive_time >= self.timeout and self.data['status']:
        self.data = {"status": True, "speed": 0.0, "angle": 0.0}
        self.lost_connection = True
      else:
        self.lost_connection = False

  def __getitem__(self, s):
    return self.data[s]

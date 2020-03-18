import datetime
import numpy as np


class ETA:
  def __init__(self, start_time, max_progress):  # only supports up to minutes
    self.start_time = start_time
    self.max_progress = max_progress
    self.progress = 0
    self.time = 0
    self.etr = 0  # in seconds, estimated time remained
    self.seconds = 60

  # def init(self, t, max_progress):
  #     self.start_time = t
  #     self.max_progress = max_progress

  def log(self, progress, t):
    self.progress = progress
    self.time = t

  def get_eta(self):
    elapsed = self.time - self.start_time
    percentage = elapsed / (self.progress + 1)
    factor = np.interp(self.progress, [0, self.max_progress], [2.0, 1.0])
    etr = (self.max_progress * ((percentage + 1) ** factor - 1)) - elapsed
    hours, remainder = divmod(round(etr), self.seconds ** 2)
    minutes, seconds = divmod(remainder, self.seconds)

    time_list = [hours, minutes, seconds]
    time_str_list = ['hour', 'minute', 'second']

    etr_list = []
    for t, t_str in zip(time_list, time_str_list):
      plural = 's' if t != 1 else ''
      if t != 0:
        etr_list.append('{} {}{}'.format(t, t_str, plural))
    return ', '.join(etr_list)

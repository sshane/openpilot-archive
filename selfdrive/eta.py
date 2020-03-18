import datetime
import numpy as np
import time


class ETA:
  def __init__(self, start_time, max_progress, frequency):  # only supports up to minutes
    self.start_time = start_time
    self.max_progress = max_progress
    self.frequency = frequency
    self.progress = 0
    self.last_progress = 0
    self.time = 0
    self.last_time = time.time()
    self.etr = 0  # in seconds, estimated time remained
    self.ips_list = []

    self.seconds = 60

  # def init(self, t, max_progress):
  #     self.start_time = t
  #     self.max_progress = max_progress

  def log(self, progress, t):
    self.progress = progress
    self.time = t

  def format_etr(self, etr):
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

  def get_eta(self):
    total_ips = self.progress / (self.time - self.start_time)
    last_ips = (self.progress - self.last_progress) / (self.time - self.last_time)

    remaining = self.max_progress - self.progress
    etr_total = remaining / total_ips
    etr_last = remaining / last_ips
    if last_ips < total_ips:
      etr = etr_total * 0.6 + etr_last * 0.4
    else:
      etr = etr_total * 0.4 + etr_last * 0.6

    self.last_time = float(self.time)
    self.last_progress = int(self.progress)
    etr = self.format_etr(etr)
    return etr, round(last_ips, 2), round(total_ips, 2)

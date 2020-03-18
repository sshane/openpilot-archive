import datetime
import numpy as np
import time
import threading


class ETA(threading.Thread):
  def __init__(self, start_time, max_progress, frequency, sfp, spinner=None):  # only supports up to minutes
    threading.Thread.__init__(self)
    self.start_time = start_time
    self.max_progress = max_progress
    self.frequency = frequency
    self.progress = 0
    self.last_progress = 0
    self.time = 0
    self.last_time = time.time()
    self.etr = 0  # in seconds, estimated time remained
    self._start = time.time()
    self.progress_subtract = 0
    self.times = [727.05, 722.89, 722.78, 722.72, 722.69, 716.83, 713.04, 706.94, 705.69, 704.11, 704.09, 700.19, 699.27, 698.14, 698.12, 689.12, 687.45, 685.81, 684.36, 682.18, 679.99, 679.14, 677.8, 675.98, 675.24, 673.88, 672.43, 670.69, 669.88, 668.05, 667.24, 665.81, 664.14, 663.32, 661.78, 660.33, 659.36, 658.12, 656.63, 655.63, 653.92, 652.04, 651.31, 649.84, 648.61, 647.47, 646.18, 644.82, 643.74, 642.48, 640.7, 639.51, 638.31, 636.98, 635.88, 634.72, 632.98, 632.25, 630.78, 629.21, 627.47, 626.57, 626.55, 626.54, 626.53, 626.52, 623.98, 613.96, 613.73, 613.53, 609.79, 586.08, 586.06, 586.06, 586.05, 586.04, 586.03, 585.94, 576.13, 572.26, 571.6, 570.47, 568.58, 568.35, 568.34, 568.33, 568.32, 568.31, 568.3, 568.3, 567.93, 566.71, 563.85, 563.03, 562.28, 559.7, 559.01, 559.0, 558.99, 558.98, 558.97, 558.14, 557.55, 557.54, 557.53, 557.52, 557.51, 557.5, 557.49, 557.49, 557.45, 555.27, 554.51, 554.47, 552.79, 551.8, 551.78, 547.81, 547.77, 546.45, 545.48, 545.47, 545.46, 545.45, 544.42, 543.46, 543.45, 543.44, 542.35, 541.26, 540.21, 539.04, 538.2, 532.34, 530.35, 529.73, 529.35, 528.5, 528.44, 528.43, 527.33, 526.22, 525.13, 523.84, 521.69, 506.09, 504.01, 503.22, 502.32, 502.31, 502.3, 502.29, 502.28, 502.27, 502.26, 502.25, 502.24, 502.24, 502.23, 502.22, 502.21, 502.2, 502.19, 502.18, 502.17, 502.16, 502.15, 502.14, 502.13, 502.12, 502.11, 502.1, 502.09, 502.09, 502.07, 502.06, 502.06, 502.05, 502.04, 502.03, 502.02, 502.01, 502.0, 501.99, 501.98, 501.97, 501.96, 501.95, 501.94, 501.93, 489.7, 276.17, 275.48, 243.8, 214.41, 200.68, 161.13, 147.59, 143.19, 131.22, 130.58, 130.57, 130.56, 128.82, 128.74, 128.3, 110.79, 110.78, 110.6, 110.59, 110.58, 110.57, 110.56, 110.55, 101.57, 93.07, 85.54, 84.73, 57.15, 45.54, 45.46, 31.75, 29.88, 15.1, 13.76, 13.27, 12.45, 8.48, 0.0]
    self.seconds = 60
    self.total_ips = 0
    self.spinner = spinner
    self.this_ips = 0
    self.last_ips = 0
    self.has_update = False
    self.run_thread = False
    self.scons_finished_progress = sfp
    self.start_eta_thread()

  # def init(self, t, max_progress):
  #     self.start_time = t
  #     self.max_progress = max_progress

  def start_eta_thread(self):
    while self.progress < self.max_progress:
      print(self.run_thread)
      if not self.run_thread:
        print('NOT RUNNING THREAD')
        time.sleep(1)
        continue
      if self.has_update:
        print('HAS UPDATE!\n------')
        self.has_update = False
      eta_message = self.get_eta()
      self.spinner.update("%d" % (self.progress / self.max_progress * self.scons_finished_progress), eta_message)
      # spinner.update("%d" % (percentage * scons_finished_progress), eta_message)
      time.sleep(1 / self.frequency)


  def update(self, progress, t):
    self.progress = progress
    self.time = t
    self.has_update = True
    self.run_thread = True

  def set_ips(self):
    self.last_ips = float(self.this_ips)
    self.this_ips = (self.progress - self.last_progress) / (self.time - self.last_time)

    if self.this_ips < 10 < self.last_ips:
      print('RESET HERE!!!\n--------')
      self.start_time = float(self.last_time)  # ensures ips accuracy
      self.progress_subtract = int(self.progress)

    self.total_ips = (self.progress - self.progress_subtract) / (self.time - self.start_time)

  def get_eta(self):
    self.set_ips()
    print('TOTAL IPS: {}\n------------'.format(self.total_ips))
    self.last_time = float(self.time)
    self.last_progress = int(self.progress)
    percentage = round(self.progress / self.max_progress * 100, 1)

    ips = self.total_ips * 0.6 + self.this_ips * 0.4
    if self.this_ips < self.total_ips:
      ips = self.this_ips * 0.8 + self.total_ips * 0.2
      if self.last_ips < self.this_ips:
        ips = self.last_ips * 0.8 + ips * 0.2
        print('USING IPS: {}\n---------'.format(ips))

    if self.this_ips > 10:  # probably pulling from cache
      remaining = self.max_progress - self.progress
      return 'compiled: {}% ETA: {}'.format(percentage, self.format_etr(remaining / ips))

    remaining = self.max_progress - self.progress
    return 'compiling: {}% ETA: {}'.format(percentage, self.format_etr(remaining / ips))

    times_idx = len(self.times) * (self.progress / self.max_progress)
    if times_idx == round(times_idx):
      etr = self.times[int(times_idx)]
    else:
      times_scale = [self.times[round(times_idx + i)] for i in [-1, 1]]
      etr = sum(times_scale) / 2.0

    return 'compiling: {}% ETA: {}'.format(percentage, self.format_etr(etr))

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

  def get_eta_old(self):
    total_ips = (self.progress - self.progress_subtract) / (self.time - self.start_time)
    last_ips = (self.progress - self.last_progress) / (self.time - self.last_time)
    self.last_time = float(self.time)
    self.last_progress = int(self.progress)

    ips = total_ips * 0.8 + last_ips * 0.8
    if last_ips < total_ips:
      ips = last_ips * 0.8 + total_ips * 0.8

    if time.time() - self._start > 5:
      return 'calculating', '', ''

    if last_ips > 10:  # probably pulling from cache
      self.start_time = time.time()  # ensures ips accuracy
      self.progress_subtract = self.progress
      return 'calculating', '', ''

    remaining = self.max_progress - self.progress
    etr = self.format_etr(remaining / ips)

    return etr, round(last_ips, 2), round(total_ips, 2)

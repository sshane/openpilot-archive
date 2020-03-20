import datetime
import numpy as np
import time
import threading
import os


class ETAData:
  def __init__(self, t=0, progress=0):
    self.time = t
    self.progress = progress

class ETA(threading.Thread):
  def __init__(self, start_time, max_progress, frequency, sfp, spinner=None):  # only supports up to minutes
    self.start_time = start_time
    self.max_progress = max_progress
    self.frequency = frequency
    self.time = 0
    self.etr = 0  # in seconds, estimated time remained
    self._start = time.time()
    self.progress_subtract = 0
    self.times = [727.05, 722.89, 722.78, 722.72, 722.69, 716.83, 713.04, 706.94, 705.69, 704.11, 704.09, 700.19, 699.27, 698.14, 698.12, 689.12, 687.45, 685.81, 684.36, 682.18, 679.99, 679.14, 677.8, 675.98, 675.24, 673.88, 672.43, 670.69, 669.88, 668.05, 667.24, 665.81, 664.14, 663.32, 661.78, 660.33, 659.36, 658.12, 656.63, 655.63, 653.92, 652.04, 651.31, 649.84, 648.61, 647.47, 646.18, 644.82, 643.74, 642.48, 640.7, 639.51, 638.31, 636.98, 635.88, 634.72, 632.98, 632.25, 630.78, 629.21, 627.47, 626.57, 626.55, 626.54, 626.53, 626.52, 623.98, 613.96, 613.73, 613.53, 609.79, 586.08, 586.06, 586.06, 586.05, 586.04, 586.03, 585.94, 576.13, 572.26, 571.6, 570.47, 568.58, 568.35, 568.34, 568.33, 568.32, 568.31, 568.3, 568.3, 567.93, 566.71, 563.85, 563.03, 562.28, 559.7, 559.01, 559.0, 558.99, 558.98, 558.97, 558.14, 557.55, 557.54, 557.53, 557.52, 557.51, 557.5, 557.49, 557.49, 557.45, 555.27, 554.51, 554.47, 552.79, 551.8, 551.78, 547.81, 547.77, 546.45, 545.48, 545.47, 545.46, 545.45, 544.42, 543.46, 543.45, 543.44, 542.35, 541.26, 540.21, 539.04, 538.2, 532.34, 530.35, 529.73, 529.35, 528.5, 528.44, 528.43, 527.33, 526.22, 525.13, 523.84, 521.69, 506.09, 504.01, 503.22, 502.32, 502.31, 502.3, 502.29, 502.28, 502.27, 502.26, 502.25, 502.24, 502.24, 502.23, 502.22, 502.21, 502.2, 502.19, 502.18, 502.17, 502.16, 502.15, 502.14, 502.13, 502.12, 502.11, 502.1, 502.09, 502.09, 502.07, 502.06, 502.06, 502.05, 502.04, 502.03, 502.02, 502.01, 502.0, 501.99, 501.98, 501.97, 501.96, 501.95, 501.94, 501.93, 489.7, 276.17, 275.48, 243.8, 214.41, 200.68, 161.13, 147.59, 143.19, 131.22, 130.58, 130.57, 130.56, 128.82, 128.74, 128.3, 110.79, 110.78, 110.6, 110.59, 110.58, 110.57, 110.56, 110.55, 101.57, 93.07, 85.54, 84.73, 57.15, 45.54, 45.46, 31.75, 29.88, 15.1, 13.76, 13.27, 12.45, 8.48, 0.0]
    self.seconds = 60
    self.total_ips = 0
    self.spinner = spinner
    self.this_ips = 0
    self.last_ips = 0
    self.updated = False
    self.etr = 0
    self.can_reset = False
    self.run_thread = False
    self.eta_data = []
    self.scons_finished_progress = sfp
    threading.Thread.__init__(self)
    self.window_len = 20 * self.frequency  # in seconds * frequency
    self.etrs = [16 * 60 for _ in range(int(self.window_len / 2))]

  # def init(self, t, max_progress):
  #     self.start_time = t
  #     self.max_progress = max_progress

  def get_eta_data(self, idx=-1):
    # By default this will return latest
    if len(self.eta_data) == 0:
      return ETAData()
    return self.eta_data[idx]

  def run(self):
    progress = 0
    while progress < self.max_progress:
      progress = self.get_eta_data().progress
      if os.path.exists('/data/stop'):
        os.remove('/data/stop')
        return
      if not self.run_thread:
        self.spinner.update("%d" % (progress / self.max_progress * self.scons_finished_progress), 'calculating...')
        time.sleep(1)
        continue

      eta_message = self.get_eta()
      self.spinner.update("%d" % (progress / self.max_progress * self.scons_finished_progress), eta_message)
      # spinner.update("%d" % (percentage * scons_finished_progress), eta_message)
      if self.updated:
        self.updated = False
      time.sleep(1 / self.frequency)

  def update(self, progress, t):
    self.can_reset = True
    self.last_ips = float(self.this_ips)
    self.eta_data.append(ETAData(progress=progress, t=t))
    self.updated = True
    removed = False
    while len(self.eta_data) > 3:  # we only need past 3
      del self.eta_data[0]
      removed = True

    if time.time() - self.get_eta_data().time < 1e-4:  # we don't care about these updates
      self.progress_subtract += 1
    # else:
    #   print('GOT UPDATE')

    if not self.run_thread:
      self.run_thread = removed  # wait until we have enough data

  def set_ips(self):
    # print(self.time)
    # print(self.last_time)
    cur_time = time.time()
    # # if self.has_update:
    self.this_ips = (self.get_eta_data().progress - self.get_eta_data(-2).progress) / (cur_time - self.get_eta_data(-2).time)
    print('last ips: {}'.format(self.last_ips))
    if self.this_ips < 10 < self.last_ips and self.can_reset:  # and self.updated:
      self.can_reset = False
      print('RESET HERE!!!\n---------')
      self.start_time = cur_time  # reset total ips when we stop getting cached files
      self.progress_subtract = int(self.get_eta_data(-1).progress)
      self.total_ips = self.this_ips
    else:
      self.total_ips = (self.get_eta_data().progress - self.progress_subtract) / (cur_time - self.start_time)

  def get_eta(self):
    self.set_ips()
    percentage = round(self.get_eta_data().progress / self.max_progress * 100, 1)
    print('TOTAL IPS: {}\n---------'.format(round(self.total_ips, 2)))
    while len(self.etrs) > self.window_len:
      del self.etrs[0]

    ips = self.total_ips * 0.8 + self.this_ips * 0.2

    x = np.linspace(0, 1, 10)
    y = [(i + 1) ** -2 for i in x]

    ips = np.interp(ips / 10, x, y) * ips  # penalize large ips's

    if time.time() - self.get_eta_data().time > 5 or self.etr == 0:
      self.etr = (self.max_progress - self.get_eta_data().progress) / ips
      self.etr -= self.total_ips / self.frequency
      print('---WAITING ETR: {}'.format(self.etr))

    else:
      self.etr = (self.max_progress - self.get_eta_data().progress) / ips
    self.etrs.append(self.etr)

    # if self.this_ips < ips:
    #   ips = self.this_ips * 0.2 + ips * 0.8
    #   if self.last_ips < ips:
    #     ips = self.last_ips * 0.2 + ips * 0.8
    print('USING IPS: {} THIS IPS: {}\n---------'.format(round(ips, 2), round(self.this_ips, 2)))
    self.etr = (self.max_progress - self.get_eta_data().progress) / ips
    print(self.etr)
    self.etrs.append(self.etr)
    # self.etr -= ips / self.frequency

    w = np.hanning(self.window_len)

    s = np.r_[self.etrs[self.window_len-1:0:-1], self.etrs, self.etrs[-1:-self.window_len:-1]]
    y = np.convolve(w/w.sum(), s, mode='valid')
    print(len(self.etrs))
    print(len(y))

    if len(y) - 1 < self.window_len:
      print('calculated: {}'.format(y[-1]))
      return "calculating..."

    etr = self.format_etr(y[self.window_len - 2])




    # if self.this_ips > 10:  # probably pulling from cache
    #   remaining = self.max_progress - self.get_eta_data().progress
    #   print('CACHE!')
    #   return 'compiled: {}% ETA: {}'.format(percentage, self.format_etr(remaining / ips))

    # avg = self.total_ips * 0.7 + self.this_ips * 0.15 + self.last_ips * 0.15
    # elif ips < 10:
    #   self.etr -= ips / self.frequency
    #   # print('LAST UPDATE OVER 5 SECONDS!')
    #   # return 'compiling: {}% ETA: {}'.format(percentage, self.format_etr(self.etr))
    # print('NORMAL ETR: {}'.format(self.etr))

    # etr = self.format_etr(y[self.window_len])

    # # print('after etr: {}'.format(self.etr))
    # etr = self.format_etr(self.etr)
    # print('NORMAL!')
    return 'compiling: {}% ETA: {}'.format(percentage, etr)

    #
    # etr = self.format_etr((self.max_progress - self.get_eta_data().progress) / ips)
    # # print("ETA: {}".format(etr))
    # # return 'TOTAL IPS: {} - CUR IPS: {} - LAST IPS: {} - USING IPS: {}'.format(round(self.total_ips, 2), round(self.this_ips, 2), round(self.last_ips, 2), round(ips, 2))
    # return 'compiling: {}% ETA: {}'.format(percentage, etr)

  def format_etr(self, etr):
    hours, remainder = divmod(round(etr), self.seconds ** 2)
    minutes, seconds = divmod(remainder, self.seconds)

    time_list = [hours, minutes, seconds]
    time_str_list = ['hour', 'minute', 'second']

    etr_list = []
    for t, t_str in zip(time_list, time_str_list):
      plural = 's' if t != 1 else ''
      if t != 0:
        etr_list.append('{} {}{}'.format(int(t), t_str, plural))
    return ', '.join(etr_list)

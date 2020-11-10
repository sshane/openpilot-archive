import copy
import os
import matplotlib.pyplot as plt
import ast

# os.chdir(os.getcwd())


def get_data(file_path):
  DT_CTRL = 100
  steer_delay = round(0.12 * DT_CTRL)

  keys_6 = ['v_ego', 'angle_steers_des', 'angle_steers', 'angle_offset', 'torque', 'time']
  keys_7 = ['v_ego', 'angle_steers_des', 'angle_steers', 'steer_rate', 'angle_offset', 'torque', 'time']
  with open(file_path, 'r') as f:
    dat = f.read()

  dat = [ast.literal_eval(line) for line in dat.split('\n')[:-1]]
  dat = [dict(zip(keys_6 if len(line) == 6 else keys_7, line)) for line in dat]

  DISENGAGE_NOT_FILTERED = True
  if DISENGAGE_NOT_FILTERED:  # todo: fix this while gathering data
    dat = [line for idx, line in enumerate(dat) if line['torque'] != 0]

  split = [[]]
  for idx, line in enumerate(dat):  # split samples by time
    if idx > 0:  # can't get before first
      if line['time'] - dat[idx - 1]['time'] > 1 / 20:  # 1/100 is rate but account for lag
        split.append([])
      split[-1].append(line)
  del dat

  split = [sec for sec in split if len(sec) > int(1 * DT_CTRL)]  # long enough section
  for i in range(len(split)):  # accounts for steer actuator delay (moves torque up by 12 samples)
    torque = [line['torque'] for line in split[i]]
    for j in range(len(split[i])):
      if j < steer_delay:
        continue
      split[i][j]['torque'] = torque[j - steer_delay]
    split[i] = split[i][steer_delay:]  # removes leading samples

  return [i for j in split for i in j]  # flatten

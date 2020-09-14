import math
import os
import json
import time

import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from selfdrive.config import Conversions as CV

os.chdir(os.getcwd())

data = []
for fi in os.listdir():
  if not fi.endswith('.py') and 'straight' in fi:
    print(fi)
    with open(fi) as f:
      for line in f.read().split('\n')[:-1]:
        line = line.replace('array([', '[').replace('])', ']')  # formats dpoly's np array
        line = line.replace("'", '"')  # for json
        try:
          data.append(json.loads(line))
        except:
          raise Exception('error: {}'.format(line))

TR = 0.75
for line in data:
  dist = line['v_ego'] * TR

  lat_pos = np.polyval(line['d_poly'], dist)  # lateral position in meters at TR seconds
  lat_pos -= line['d_poly'][3]  # want curvature of road from start of path not car
  line['lat_pos'] = lat_pos

abs_lateral_positions = [abs(line['lat_pos']) for line in data]
abs_angle_steers = [abs(line['angle_steers']) for line in data]
print('max lateral position: {}'.format(max(abs_lateral_positions)))
print('min lateral position: {}'.format(min(abs_lateral_positions)))
print('mean lateral position: {}'.format(np.mean(abs_lateral_positions)))

plt.figure(0)
# plt.xlim(0, 0.5)
plt.title('lat_pos')
sns.distplot(np.array(abs_lateral_positions))
plt.show()
# plt.figure(1)
# plt.title('angle_steers')
# sns.distplot(abs_angle_steers)
# plt.show()


raise Exception()
plt.figure(2)
for idx, line in enumerate(data[500:]):
  plt.clf()
  plt.ylim(-1, 1)
  # plt.title('sample: {}, speed: {} mph'.format(idx, round(line['v_ego'] * CV.MS_TO_MPH, 2)))

  max_dist = round(line['v_ego'] * TR)
  # line['d_poly'][3] = 0
  # print(max_dist)
  x = np.linspace(0, max_dist, max_dist)
  y = np.polyval(line['d_poly'], x)
  plt.plot(x, y, label='original')
  plt.plot(x, y - line['d_poly'][3], label='offset by d_poly[3]')
  plt.scatter(x[-1], 0, label='zero')
  plt.scatter(x[-1], line['lat_pos'], label='curvature_new')
  plt.legend()
  plt.pause(0.001)



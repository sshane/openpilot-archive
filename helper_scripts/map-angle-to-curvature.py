import os
import json
import numpy as np
from selfdrive.config import Conversions as CV


os.chdir(os.getcwd())

data = []
for fi in os.listdir():
  if not fi.endswith('.py'):
    with open(fi) as f:
      for line in f.read().split('\n')[:-1]:
        line = line.replace('array([', '[').replace('])', ']')  # formats dpoly's np array
        line = line.replace("'", '"')  # for json
        try:
          data.append(json.loads(line))
        except:
          print('error: {}'.format(line))

min_angle = 1.
center_max = 2.5
inner_max = 7.5
outer_max = 15.
sharp_max = float('inf')
TR = 0.9
data_banded = {'center': [], 'inner': [], 'outer': [], 'sharp': []}

within_percent = 0.1  # only use angles within 10% lower than max angle to get higher max average (instead of max())

for line in data:
  if line['v_ego'] < 15 * CV.MPH_TO_MS:
    continue
  angle_steers = line['angle_steers']
  if abs(angle_steers) >= min_angle:
    if abs(angle_steers) < center_max * (1 + within_percent):
      if center_max * (1 - within_percent) < abs(angle_steers):  # within 10% lower
        data_banded['center'].append(line)
      continue
    if abs(angle_steers) < inner_max * (1 + within_percent):
      if inner_max * (1 - within_percent) < abs(angle_steers):
        data_banded['inner'].append(line)
      continue
    if abs(angle_steers) < outer_max * (1 + within_percent):
      if outer_max * (1 - within_percent) < abs(angle_steers):
        data_banded['outer'].append(line)
      continue
    data_banded['sharp'].append(line)

for band in data_banded:
  print('{}: {}'.format(band, len(data_banded[band])), end=' ')
print()

avg_angle_bands = {}
max_angle_text = {'center': '{} deg'.format(center_max),
                  'inner': '{} deg'.format(inner_max),
                  'outer': '{} deg'.format(outer_max),
                  'sharp': 'doen\'t matter as much/inf'}
for band in data_banded:
  avg_angle_bands[band] = np.mean([abs(line['angle_steers']) for line in data_banded[band]])
  print('MA {} angle: {} ({})'.format(band, round(avg_angle_bands[band], 4), max_angle_text[band]))
print()

curvature_dict = {'center': [], 'inner': [], 'outer': [], 'sharp': []}
for band in data_banded:
  for line in data_banded[band]:
    dist = line['v_ego'] * TR
    lat_pos = np.polyval(line['d_poly'], dist)  # lateral position in meters at 1.8 seconds
    curvature_dict[band].append(lat_pos)

avg_curvatures = {band: np.mean(np.abs(curvature_dict[band])) for band in curvature_dict}
std_curvatures = {band: np.std(np.abs(curvature_dict[band])) for band in curvature_dict}

modifiers = {}
modifiers['center'] = center_max / avg_angle_bands['center']  # just since average angle doesn't equal the exact max limit
modifiers['inner'] = inner_max / avg_angle_bands['inner']
modifiers['outer'] = outer_max / avg_angle_bands['outer']
modifiers['sharp'] = 1  # we don't even use this

for band in avg_curvatures:
  print('MA {} curvature: {}, std: {} (ADJUSTED: {})'.format(band, round(avg_curvatures[band], 5),
                                                             round(std_curvatures[band], 4),
                                                             round(avg_curvatures[band] * modifiers[band], 5)))

min_curv_from_angle = (min_angle * avg_curvatures['center']) / avg_angle_bands['center']  # calcs 0.1 deg min equivelent
print('max. calc. curvature for CL: {} (ADJUSTED: {})'.format(round(min_curv_from_angle, 5), round(min_curv_from_angle * modifiers['center'], 5)))

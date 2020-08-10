import math
import os
import json
import time

import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from selfdrive.config import Conversions as CV
from sklearn.cluster import KMeans


os.chdir(os.getcwd())

data = []
for fi in os.listdir():
  if not fi.endswith('.py'):
    print(fi)
    with open(fi) as f:
      for line in f.read().split('\n')[:-1]:
        line = line.replace('array([', '[').replace('])', ']')  # formats dpoly's np array
        line = line.replace("'", '"')  # for json
        try:
          data.append(json.loads(line))
        except:
          print('error: {}'.format(line))

print('\nsamples before filtering: {}'.format(len(data)))
round_to = 6
min_angle = 1.
max_angle = 45.
TR = 0.9
data_filtered = []


for line in data:
  if line['v_ego'] < 15 * CV.MPH_TO_MS:
    continue
  if min_angle <= abs(line['angle_steers']) <= max_angle:
    dist = line['v_ego'] * TR
    # line['d_poly'][3] = 0  # want curvature of road from start of path not car
    lat_pos = abs(np.polyval(line['d_poly'], dist) - line['d_poly'][3])  # lateral position in meters at TR seconds
    line['lat_pos'] = lat_pos
    line['d_poly_0'] = line['d_poly'][0]
    line['d_poly_1'] = line['d_poly'][1]
    line['d_poly_2'] = line['d_poly'][2]
    data_filtered.append(line)
print('samples after filtering: {}'.format(len(data_filtered)))
data = data_filtered

use_data_y = 'lat_pos'

PLOT_DISTS = False
if PLOT_DISTS:
  plt.figure(0)
  sns.distplot([line['v_ego'] for line in data], bins=75)
  plt.title('speed (m/s)')
  plt.show()

  plt.figure(1)
  sns.distplot([abs(line[use_data_y]) for line in data], bins=100)
  plt.title(use_data_y)
  plt.show()

# plt.figure(2)
# plt.scatter([line['v_ego'] for line in data], [abs(line[use_data_y]) for line in data], marker='o')
# plt.show()
n_clusters = 12

v_egos = [line['v_ego'] for line in data]
y = np.array([abs(line[use_data_y]) for line in data])
max_v_ego = np.max(v_egos)
y_axis_factor = max(v_egos) / max(y)  # to scale max y to be max x
y_axis_factor *= 1.5  # 2x more weight to y axis
kmeans = KMeans(n_clusters=n_clusters, max_iter=200*10)
x = np.array([v_egos, y * y_axis_factor]).T
print(x.shape)
kmeans.fit(x)

plt.figure(3)
# pred_y = kmeans.fit_predict(x)
# plt.scatter(x[:,0], x[:,1], s=0.6)

cluster_coords = kmeans.cluster_centers_
# cluster_coords[:, 1] /= y_axis_factor  # scale back down


def find_distance(pt1, pt2):
  x1, x2 = pt1[0], pt2[0]
  y1, y2 = pt1[1], pt2[1]
  return math.hypot((x2 - x1), (y2 - y1))

t = time.time()
clusters = [[] for _ in range(n_clusters)]
for line in data:
  dists = [find_distance([line['v_ego'], abs(line[use_data_y]) * y_axis_factor], clstr_coord) for clstr_coord in cluster_coords]
  closest = min(range(len(dists)), key=dists.__getitem__)
  clusters[closest].append([line['v_ego'], abs(line[use_data_y]) * y_axis_factor])
print(time.time() - t)

for cluster in clusters:
  if len(cluster):
    d1, d2 = np.array(cluster).T
    plt.scatter(d1, d2 / y_axis_factor, s=2)

plt.xlabel('speed (m/s)')
if use_data_y == 'lat_pos':
  plt.ylabel(use_data_y + ' at {} TR'.format(TR))
else:
  plt.ylabel(use_data_y)

plt.scatter(kmeans.cluster_centers_[:, 0], kmeans.cluster_centers_[:, 1] / y_axis_factor, s=150, c='red')
plt.show()

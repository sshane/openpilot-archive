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
          raise Exception('error: {}'.format(line))

print('\nSamples before filtering: {}'.format(len(data)))
ROUND_TO = 8
MIN_ANGLE = 1.
MAX_ANGLE = 45.
TR = 0.9

Y_AXIS_KEY = 'lat_pos'
KMEANS_N_CLUSTERS = 12
KMEANS_MAX_ITER = 2000
Y_AXIS_WEIGHT = 1  # importance of y axis, more clusters for curvature vs. speed

USE_ABS = True

data_filtered = []
for line in data:
  if line['v_ego'] < 15 * CV.MPH_TO_MS:
    continue
  if MIN_ANGLE <= abs(line['angle_steers']) <= MAX_ANGLE:
    dist = line['v_ego'] * TR

    lat_pos = np.polyval(line['d_poly'], dist)  # lateral position in meters at TR seconds
    lat_pos -= line['d_poly'][3]  # want curvature of road from start of path not car
    line['lat_pos'] = lat_pos

    if USE_ABS:
      line['lat_pos'] = abs(line['lat_pos'])
    data_filtered.append(line)

print('Samples after filtering: {}'.format(len(data_filtered)))
data = data_filtered

PLOT_DIST_PLOTS = False
if PLOT_DIST_PLOTS:
  plt.figure(0)
  sns.distplot([line['v_ego'] for line in data], bins=75)
  plt.title('speed (m/s)')
  plt.show()

  plt.figure(1)
  sns.distplot([line[Y_AXIS_KEY] for line in data], bins=100)
  plt.title(Y_AXIS_KEY)
  plt.show()

v_egos = [line['v_ego'] for line in data]
y = np.array([line[Y_AXIS_KEY] for line in data])
kmeans = KMeans(n_clusters=KMEANS_N_CLUSTERS, max_iter=KMEANS_MAX_ITER)

y_axis_factor = (max(v_egos) - min(v_egos)) / (max(y) - min(y))  # to make y axis as important as x since it's smaller
y_axis_factor *= Y_AXIS_WEIGHT  # x more weight to y axis

x = np.array([v_egos, y * y_axis_factor]).T
kmeans.fit(x)
cluster_coords = kmeans.cluster_centers_


def find_distance(pt1, pt2):
  x1, x2 = pt1[0], pt2[0]
  y1, y2 = pt1[1], pt2[1]
  return math.hypot(x2 - x1, y2 - y1)


t = time.time()
clusters = [[] for _ in range(KMEANS_N_CLUSTERS)]
for line in data:
  dists = [find_distance([line['v_ego'], line[Y_AXIS_KEY] * y_axis_factor], clstr_coord) for clstr_coord in cluster_coords]
  closest = min(range(len(dists)), key=dists.__getitem__)
  clusters[closest].append([line['v_ego'], line[Y_AXIS_KEY]])
print(time.time() - t)

plt.figure(3)
for cluster in clusters:
  if len(cluster):
    d1, d2 = np.array(cluster).T
    plt.scatter(d1, d2, s=2)
  else:
    raise Exception('Cluster cannot be empty')

plt.xlabel('speed (m/s)')
if Y_AXIS_KEY == 'lat_pos':
  plt.ylabel(Y_AXIS_KEY + ' at {} TR'.format(TR))
else:
  plt.ylabel(Y_AXIS_KEY)

plt.scatter(cluster_coords[:, 0], cluster_coords[:, 1] / y_axis_factor, s=100, c='black')
plt.show()

# now print data to copy into curvature_learner.py
cluster_dict = {}
print('Number of clusters: {}'.format(KMEANS_N_CLUSTERS))
for idx, cluster_coord in enumerate(sorted(cluster_coords, key=lambda coord: coord[0])):
  cluster_name = 'CLUSTER_' + str(idx)
  # cluster_coord[1] /= y_axis_factor  # scale back down
  cluster_coord = np.round(cluster_coord, ROUND_TO).tolist()
  print('{}: {}'.format(cluster_name, cluster_coord))
  cluster_dict[cluster_name] = cluster_coord

print('\ncluster_coords = {}'.format(cluster_dict))
# print('Make sure to multiply each cluster y coordinate by the y axis factor below as well as the y position of the sample!')
print('Make sure to multiply each sample y coordinate by the y axis factor below (y coord of clusters are pre-multiplied)!')
print('y axis factor: {}'.format(round(y_axis_factor, ROUND_TO)))

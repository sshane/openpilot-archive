import time
import math
import numpy as np

coords = np.random.uniform(0, 1.6, (20, 2))


def find_distance(pt1, pt2):
  x1, x2 = pt1[0], pt2[0]
  y1, y2 = pt1[1], pt2[1]
  return math.hypot(x2 - x1, y2 - y1)


cluster_coords = {'CLUSTER_0': [9.50898744, 1.15147653], 'CLUSTER_1': [11.61555388, 6.77329492], 'CLUSTER_2': [13.12260049, 1.41386154], 'CLUSTER_3': [16.87001474, 5.64168796],
                  'CLUSTER_4': [17.71598068, 1.25741708], 'CLUSTER_5': [21.80838089, 6.11567922], 'CLUSTER_6': [22.6046087, 15.91567986], 'CLUSTER_7': [22.91549021, 1.72555002],
                  'CLUSTER_8': [23.3612511, 10.85114753], 'CLUSTER_9': [25.07931061, 6.36175232], 'CLUSTER_10': [26.75841484, 2.01383989], 'CLUSTER_11': [30.30274637, 4.88505625]}

y_axis_factor = 17.41918337

seconds = 60 * 60

start = time.time()
cs = []
for _ in range(seconds):
  for sample_coord in coords:
    if abs(-.08) >= 0.050916:
      sample_coord = [sample_coord[0], abs(sample_coord[1] * y_axis_factor)]
      dists = {cluster: find_distance(sample_coord, cluster_coord) for cluster, cluster_coord in cluster_coords.items()}
      closest_cluster = min(dists, key=dists.__getitem__)
      cs.append(closest_cluster)
total = time.time() - start

print('total time: {}'.format(total))
print('time per clustering: {}'.format(total / (seconds * 20)))
print('clustering rate: {} hz'.format(1 / (total / (seconds * 20))))

cluster_coords = list(cluster_coords.values())
start = time.time()
cs = []
for _ in range(seconds):
  for sample_coord in coords:
    if abs(-.08) >= 0.050916:
      sample_coord = [sample_coord[0], abs(sample_coord[1] * y_axis_factor)]
      dists = [find_distance(sample_coord, cluster_coord) for cluster_coord in cluster_coords]
      closest_cluster = min(range(len(dists)), key=dists.__getitem__)
      cs.append(closest_cluster)
total = time.time() - start

print('\ntotal time: {}'.format(total))
print('time per clustering: {}'.format(total / (seconds * 20)))
print('clustering rate: {} hz'.format(1 / (total / (seconds * 20))))

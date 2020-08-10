import time
import math
import numpy as np

coords1 = np.random.uniform(0, 45, (1e8, 2))
coords2 = np.random.uniform(0, 45, (1e8, 2))

def find_distance_hypot(pt1, pt2):
  x1, x2 = pt1[0], pt2[0]
  y1, y2 = pt1[1], pt2[1]
  return math.hypot((x2 - x1), (y2 - y1))

def find_distance_hypot2(pt1, pt2):
  return math.hypot((pt2[0] - pt1[0]), (pt2[1] - pt1[1]))

n = []
start = time.time()
for c1, c2 in zip(coords1, coords2):
  n.append(find_distance_hypot(c1, c2))
print(time.time() - start)

hyp = []
start = time.time()
for c1, c2 in zip(coords1, coords2):
  hyp.append(find_distance_hypot2(c1, c2))
print(time.time() - start)

print(np.allclose(n, hyp))

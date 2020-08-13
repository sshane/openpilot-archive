import os
import math
import json
from common.numpy_fast import clip
from common.realtime import sec_since_boot
from selfdrive.config import Conversions as CV
from selfdrive.controls.lib.lane_planner import eval_poly
from common.op_params import opParams

# CurvatureLearner v4 by Zorrobyte
# Modified to add direction as a learning factor as well as clusters based on speed x curvature (lateral pos in 0.9 seconds)
# Clusters found with sklearn KMeans, this assigns more clusters to areas with more data and viceversa
# Version 5 due to json incompatibilities

GATHER_DATA = True
VERSION = 5.5

FT_TO_M = 0.3048


def find_distance(pt1, pt2):
  x1, x2 = pt1[0], pt2[0]
  y1, y2 = pt1[1], pt2[1]
  return math.hypot(x2 - x1, y2 - y1)


class CurvatureLearner:
  def __init__(self):
    self.op_params = opParams()
    self.curvature_file = '/data/curvature_offsets.json'
    self.fast_learn_file = '/data/curvature_fast_learn.json'
    rate = 1 / 20.  # pathplanner is 20 hz
    self.learning_rate = 2.5833e-3 * rate
    self.write_frequency = 5  # in seconds
    self.min_lr_prob = .65
    self.min_speed = 15 * CV.MPH_TO_MS

    self.y_axis_factor = 14.52823993  # weight y/curvature as much as speed
    self.min_curvature = 0.047963  # ~0.8 degrees

    self.directions = ['left', 'right']
    self.cluster_coords = [[10.08089463, 1.14077195], [11.92443682, 13.72311586], [12.00668782, 5.76182834], [14.69486009, 1.31361394], [18.1817087, 5.62112812], [18.75565424, 1.41016134],
                           [21.98173854, 10.84622124], [22.96835188, 1.65274428], [23.47335083, 6.07894073], [23.76092757, 16.71622771], [26.74476333, 10.2416992], [26.98587618, 1.67010251],
                           [29.2826046, 4.8478324]]
    # self.cluster_names = ['CLUSTER_{}'.format(idx) for idx in range(len(self.cluster_coords))]
    self.cluster_names = ['22.6MPH-.08CURV', '26.7MPH-.94CURV', '26.9MPH-.4CURV', '32.9MPH-.09CURV', '40.7MPH-.39CURV', '42.MPH-.1CURV', '49.2MPH-.75CURV', '51.4MPH-.11CURV', '52.5MPH-.42CURV',
                          '53.2MPH-1.15CURV', '59.8MPH-.7CURV', '60.4MPH-.11CURV', '65.5MPH-.33CURV']

    self.fast_learning_for = 90  # seconds per cluster
    self.fast_learning_for = round(self.fast_learning_for / rate)  # speed up learning first time user uses curvature learner
    self.fast_lr_multiplier = 2.  # 2x faster learning until ~1 MIN for each cluster
    self._load_curvature()

  def update(self, v_ego, d_poly, lane_probs, angle_steers):
    self._gather_data(v_ego, d_poly, angle_steers)
    offset = 0
    if v_ego < self.min_speed or math.isnan(d_poly[0]) or len(d_poly) != 4 or not self.op_params.get('curvature_learner'):
      return offset

    cluster, direction = self.cluster_sample(v_ego, d_poly)
    if cluster is not None:  # don't learn/return an offset if below min curvature
      lr_prob = lane_probs[0] + lane_probs[1] - lane_probs[0] * lane_probs[1]

      if lr_prob >= self.min_lr_prob:  # only learn when lane lines are present; still use existing offset
        if direction == 'right':
          d_poly[3] = -d_poly[3]  # d_poly's sign switches for oversteering in different directions

        lr = self.get_learning_rate(direction, cluster)  # faster learning for first ~minute per cluster
        self.learned_offsets[direction][cluster] -= d_poly[3] * lr  # the learning
      offset = self.learned_offsets[direction][cluster]

    self._write_data()
    return clip(offset, -0.3, 0.3)

  def cluster_sample(self, v_ego, d_poly):
    TR = 0.9
    dist = v_ego * TR
    # we want curvature of road from start of path not car, so subtract d_poly[3]
    lat_pos = eval_poly(d_poly, dist) - d_poly[3]  # lateral position in meters at TR seconds
    direction = 'left' if lat_pos > 0 else 'right'

    lat_pos = abs(lat_pos)
    closest_cluster = None
    if lat_pos >= self.min_curvature:
      sample_coord = [v_ego, lat_pos * self.y_axis_factor]  # we multiply y so that the dist function weights x and y the same
      dists = [find_distance(sample_coord, cluster_coord) for cluster_coord in self.cluster_coords]  # todo: remove clusters far away based on v_ego to speed this up
      closest_cluster = self.cluster_names[min(range(len(dists)), key=dists.__getitem__)]

    return closest_cluster, direction

  def get_learning_rate(self, direction, cluster):
    lr = self.learning_rate
    fast_iter_left = self.fast_learn[direction][cluster]
    if not isinstance(fast_iter_left, str):
      if 1 <= fast_iter_left:  # decrement until we reach 0
        self.fast_learn[direction][cluster] -= 1
        lr *= self.fast_lr_multiplier
      else:  # mark done
        self.fast_learn[direction][cluster] = 'done'
    return lr

  def _gather_data(self, v_ego, d_poly, angle_steers):
    if GATHER_DATA:
      with open('/data/curv_learner_data', 'a') as f:
        f.write('{}\n'.format({'v_ego': v_ego, 'd_poly': list(d_poly), 'angle_steers': angle_steers}))

  def _load_curvature(self):
    self._last_write_time = 0
    try:
      with open(self.curvature_file, 'r') as f:
        self.learned_offsets = json.load(f)
      if 'version' in self.learned_offsets and self.learned_offsets['version'] == VERSION:
        return
    except:
      pass
    # can't read file, doesn't exist, or old version
    # todo: old: self.learned_offsets = {d: {c: {'offset': 0., 'fast_learn': self.fast_learning_for} for c in self.cluster_names} for d in self.directions}
    self.learned_offsets = {d: {c: 0. for c in self.cluster_names} for d in self.directions}
    self.fast_learn = {d: {c: self.fast_learning_for for c in self.cluster_names} for d in self.directions}
    self.learned_offsets['version'] = VERSION  # update version
    self._write_data()  # rewrite/create new file

  def _write_data(self):
    if sec_since_boot() - self._last_write_time >= self.write_frequency:
      with open(self.curvature_file, 'w') as f:
        f.write(json.dumps(self.learned_offsets, indent=2))
      with open(self.fast_learn_file, 'w') as f:
        f.write(json.dumps(self.fast_learn, indent=2))

      os.chmod(self.curvature_file, 0o777)
      os.chmod(self.fast_learn_file, 0o777)
      self._last_write_time = sec_since_boot()

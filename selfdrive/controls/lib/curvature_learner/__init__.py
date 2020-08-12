import os
import math
import json
from common.numpy_fast import clip
from common.realtime import sec_since_boot
from selfdrive.config import Conversions as CV
from selfdrive.controls.lib.lane_planner import eval_poly

# CurvatureLearner v4 by Zorrobyte
# Modified to add direction as a learning factor as well as clusters based on speed x curvature (lateral pos in 0.9 seconds)
# Clusters found with sklearn KMeans, this assigns more clusters to areas with more data and viceversa
# Version 5 due to json incompatibilities

GATHER_DATA = True
VERSION = 5.4

FT_TO_M = 0.3048


def find_distance(pt1, pt2):
  x1, x2 = pt1[0], pt2[0]
  y1, y2 = pt1[1], pt2[1]
  return math.hypot(x2 - x1, y2 - y1)


class CurvatureLearner:
  def __init__(self):
    self.curvature_file = '/data/curvature_offsets.json'
    rate = 1 / 20.  # pathplanner is 20 hz
    self.learning_rate = 2.5833e-3 * rate
    self.write_frequency = 5  # in seconds
    self.min_lr_prob = .65
    self.min_speed = 15 * CV.MPH_TO_MS

    self.y_axis_factor = 17.41918337  # weight y/curvature as much as speed
    self.min_curvature = 0.050916

    self.directions = ['left', 'right']
    self.cluster_coords = [[10.05191962, 1.20043602], [11.89420311, 13.75759581], [11.99125505, 5.82722866], [14.68832472, 1.4674782], [18.3783435, 5.8264243], [18.65555506, 1.59153737],
                           [22.03290771, 11.39689355], [22.76205145, 1.87613217], [23.55201934, 6.46182886], [23.79765186, 17.08974372], [26.68562309, 1.9429673], [26.78159669, 10.61987505],
                           [29.36640861, 4.81450979]]
    self.cluster_names = ['CLUSTER_{}'.format(idx) for idx in range(len(self.cluster_coords))]

    self.fast_learning_for = (30 * 60) / (len(self.cluster_names) * len(self.directions))  # speed up learning for ~1 minute per cluster (30 hr / total clusters)
    self.fast_learning_for = round(self.fast_learning_for / rate)  # get iterations equivalent to 20hz for ~1 min
    self.fast_lr_multiplier = 2.  # 2x faster learning until ~1 MIN for each cluster
    self._load_curvature()

  def update(self, v_ego, d_poly, lane_probs, angle_steers):
    self._gather_data(v_ego, d_poly, angle_steers)
    offset = 0
    if v_ego < self.min_speed or math.isnan(d_poly[0]) or len(d_poly) != 4:
      return offset

    cluster, direction = self.cluster_sample(v_ego, d_poly)
    if cluster is not None:  # don't learn/return an offset if below min curvature
      lr_prob = lane_probs[0] + lane_probs[1] - lane_probs[0] * lane_probs[1]

      if lr_prob >= self.min_lr_prob:  # only learn when lane lines are present; still use existing offset
        if direction == 'right':
          d_poly[3] = -d_poly[3]  # d_poly's sign switches for oversteering in different directions

        lr = self.get_learning_rate(direction, cluster)  # faster learning for first ~minute per cluster
        self.learned_offsets[direction][cluster]['offset'] -= d_poly[3] * lr  # the learning
      offset = self.learned_offsets[direction][cluster]['offset']

    self._write_curvature()
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
    fast_iter_left = self.learned_offsets[direction][cluster]['fast_learn']
    if not isinstance(fast_iter_left, str):
      if 1 <= fast_iter_left:  # decrement until we reach 0
        self.learned_offsets[direction][cluster]['fast_learn'] -= 1
        lr *= self.fast_lr_multiplier
      else:  # mark done
        self.learned_offsets[direction][cluster]['fast_learn'] = 'done'
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
    self.learned_offsets = {d: {c: {'offset': 0., 'fast_learn': self.fast_learning_for} for c in self.cluster_names} for d in self.directions}
    self.learned_offsets['version'] = VERSION  # update version
    self._write_curvature()  # rewrite/create new file

  def _write_curvature(self):
    if sec_since_boot() - self._last_write_time >= self.write_frequency:
      with open(self.curvature_file, 'w') as f:
        f.write(json.dumps(self.learned_offsets, indent=2))
      os.chmod(self.curvature_file, 0o777)
      self._last_write_time = sec_since_boot()

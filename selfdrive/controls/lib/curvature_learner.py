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
VERSION = 5.81

FT_TO_M = 0.3048


def find_distance(pt1, pt2):
  x1, x2 = pt1[0], pt2[0]
  y1, y2 = pt1[1], pt2[1]
  return math.hypot(x2 - x1, y2 - y1)


class CurvatureLearner:
  def __init__(self):
    self.op_params = opParams()
    self.curvature_file = '/data/curvature_offsets.json'
    # self.fast_learn_file = '/data/curvature_fast_learn.json'
    rate = 1 / 20.  # pathplanner is 20 hz
    # self.learning_rate = 2.5833e-3 * rate
    self.learning_rate = 1.333e-3 * rate  # equivelent to x / 12000
    self.write_frequency = 5  # in seconds
    self.min_lr_prob = .65
    self.min_speed = 15 * CV.MPH_TO_MS
    self.TR = 0.75

    self.y_axis_factor = 22.13036275  # weight y/curvature as much as speed
    self.min_curvature = 0.09231

    self.directions = ['left', 'right']
    self.cluster_coords = [[9.7096459, 1.49880538], [12.46788049, 6.77883128], [14.68319912, 1.72736249], [17.93326323, 12.16199009], [18.44112269, 5.57405353], [19.19873998, 1.75578853],
                           [23.6038175, 2.59984835], [23.80767759, 7.17517484], [24.77788145, 19.06035759], [26.542156, 11.93785523], [27.37704368, 2.23912583], [29.48215029, 5.80828739]]
    # self.cluster_names = ['CLUSTER_{}'.format(idx) for idx in range(len(self.cluster_coords))]
    self.cluster_names = ['21.7MPH-.07CURV', '27.9MPH-.31CURV', '32.8MPH-.08CURV', '40.1MPH-.55CURV', '41.3MPH-.25CURV', '42.9MPH-.08CURV', '52.8MPH-.12CURV', '53.3MPH-.32CURV', '55.4MPH-.86CURV',
                          '59.4MPH-.54CURV', '61.2MPH-.1CURV', '65.9MPH-.26CURV']

    # self.fast_learning_for = 90  # seconds per cluster  # todo: finish this once curv-learner is working well
    # self.fast_learning_for = round(self.fast_learning_for / rate)  # speed up learning first time user uses curvature learner
    # self.fast_lr_multiplier = 2.  # 2x faster learning until ~1 MIN for each cluster
    self._load_curvature()

  def update(self, v_ego, d_poly, lane_probs, angle_steers):
    self._gather_data(v_ego, d_poly, angle_steers)
    offset = 0
    if v_ego < self.min_speed or math.isnan(d_poly[0]) or len(d_poly) != 4 or not self.op_params.get('curvature_learner'):
      return offset
    lr_prob = lane_probs[0] + lane_probs[1] - lane_probs[0] * lane_probs[1]

    cluster, direction, lat_pos = self.cluster_sample(v_ego, d_poly)
    if cluster is not None:
      if lr_prob >= self.min_lr_prob:  # only learn when lane lines are present; still use existing offset
        if direction == 'right':
          d_poly[3] = -d_poly[3]  # d_poly's sign switches for oversteering in different directions
        # lr = self.get_learning_rate(direction, cluster)  # todo: faster learning for first ~minute per cluster
        self.learned_offsets[direction][cluster] -= d_poly[3] * self.learning_rate  # the learning

        offset = self.learned_offsets[direction][cluster]

    # print('CLUSTER: {} - OFFSET: {}  -  LAT_POS: {}'.format(cluster, round(offset, 4), round(lat_pos, 4)))

    self._write_data()
    return clip(offset, -0.05, 0.05)

  def cluster_sample(self, v_ego, d_poly):
    dist = v_ego * self.TR
    # we want curvature of road from start of path not car, so subtract d_poly[3]
    lat_pos = eval_poly(d_poly, dist)  # lateral position in meters at TR seconds
    if self.op_params.get('subtract_d_poly'):
      lat_pos -= d_poly[3]  # lateral position in meters at TR seconds
    direction = 'left' if lat_pos > 0 else 'right'

    lat_pos = abs(lat_pos)
    closest_cluster = None
    if lat_pos >= self.min_curvature:
      sample_coord = [v_ego, lat_pos * self.y_axis_factor]  # we multiply y so that the dist function weights x and y the same
      dists = [find_distance(sample_coord, cluster_coord) for cluster_coord in self.cluster_coords]  # todo: remove clusters far away based on v_ego to speed this up
      closest_cluster = self.cluster_names[min(range(len(dists)), key=dists.__getitem__)]
    return closest_cluster, direction, lat_pos

  # def get_learning_rate(self, direction, cluster):  # todo: make sure this is correct
  #   lr = self.learning_rate
  #   fast_iter_left = self.fast_learn[direction][cluster]
  #   if not isinstance(fast_iter_left, str):
  #     if 1 <= fast_iter_left:  # decrement until we reach 0
  #       self.fast_learn[direction][cluster] -= 1
  #       lr *= self.fast_lr_multiplier
  #     else:  # mark done
  #       self.fast_learn[direction][cluster] = 'done'
  #   return lr

  def _gather_data(self, v_ego, d_poly, angle_steers):
    if GATHER_DATA:
      with open('/data/curv_learner_data', 'a') as f:
        f.write('{}\n'.format({'v_ego': v_ego, 'd_poly': list(d_poly), 'angle_steers': angle_steers}))

  def _load_curvature(self):
    self._last_write_time = 0
    try:
      with open(self.curvature_file, 'r') as f:
        self.learned_offsets = json.load(f)
      # with open(self.fast_learn_file, 'r') as f:
      #   self.fast_learn = json.load(f)
      if 'version' in self.learned_offsets and self.learned_offsets['version'] == VERSION:
        return
    except:
      pass
    # can't read file, doesn't exist, or old version
    # todo: old: self.learned_offsets = {d: {c: {'offset': 0., 'fast_learn': self.fast_learning_for} for c in self.cluster_names} for d in self.directions}
    self.learned_offsets = {d: {c: 0. for c in self.cluster_names} for d in self.directions}
    # self.fast_learn = {d: {c: self.fast_learning_for for c in self.cluster_names} for d in self.directions}
    self.learned_offsets['version'] = VERSION  # update version
    self._write_data()  # rewrite/create new file

  def _write_data(self):
    if sec_since_boot() - self._last_write_time >= self.write_frequency:
      with open(self.curvature_file, 'w') as f:
        f.write(json.dumps(self.learned_offsets, indent=2))
      # with open(self.fast_learn_file, 'w') as f:
      #   f.write(json.dumps(self.fast_learn, indent=2))

      os.chmod(self.curvature_file, 0o777)
      # os.chmod(self.fast_learn_file, 0o777)
      self._last_write_time = sec_since_boot()

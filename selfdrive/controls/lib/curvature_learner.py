import os
import math
import json
from common.numpy_fast import clip
from common.realtime import sec_since_boot
from selfdrive.config import Conversions as CV
from selfdrive.controls.lib.lane_planner import eval_poly

# CurvatureLearner v4 by Zorrobyte
# Modified to add direction as a learning factor as well as clusters based on speed x curvature (lateral pos in 0.9 seconds)
# Clusters found with Scikit KMeans, this assigns more clusters to areas with more data and viceversa
# Version 5 due to json incompatibilities

GATHER_DATA = True
VERSION = 5.1

FT_TO_M = 0.3048


def find_distance(pt1, pt2):
  x1, x2 = pt1[0], pt2[0]
  y1, y2 = pt1[1], pt2[1]
  return math.hypot(x2 - x1, y2 - y1)


class CurvatureLearner:
  def __init__(self):
    self.curvature_file = '/data/curvature_offsets.json'
    rate = 1 / 20.  # pathplanner is 20 hz
    self.learning_rate = 3.85e-3 * rate  # equivalent to x/12000
    self.write_frequency = 5  # in seconds
    self.min_lr_prob = .65
    self.min_speed = 15 * CV.MPH_TO_MS

    self.y_axis_factor = 17.41918337  # weight y/curvature as much as speed
    self.min_curvature = 0.050916

    self.directions = ['left', 'right']
    self.cluster_coords = [[9.45621173, 1.50435016], [13.2693701, 5.96614348], [13.65293944, 1.34539057], [13.86556033, 11.91932353], [17.88677666, 1.9553742], [20.12247867, 6.5955202],
                           [22.36113962, 1.6691], [22.7191736, 20.48649402], [23.92071721, 8.99952259], [24.24342697, 14.23803407], [24.73679439, 4.4804306], [27.11112119, 1.79429335],
                           [29.58971969, 5.9109405]]
    self.cluster_names = ['21.2MPH-0.1CURV', '29.7MPH-0.3CURV', '30.5MPH-0.1CURV', '31.0MPH-0.7CURV', '40.0MPH-0.1CURV', '45.0MPH-0.4CURV', '50.0MPH-0.1CURV', '50.8MPH-1.2CURV', '53.5MPH-0.5CURV',
                          '54.2MPH-0.8CURV', '55.3MPH-0.3CURV', '60.6MPH-0.1CURV', '66.2MPH-0.3CURV']

    self.fast_learning_for = (60 * 60) / (len(self.cluster_names) * len(self.directions))  # speed up learning for ~2.3 minutes per cluster (1 hr / total clusters)
    self.fast_learning_for = round(self.fast_learning_for / rate)  # get iterations equivalent to 20hz for ~2.3 min
    self.fast_lr_multiplier = 5.  # 5x faster learning until ~2.3 for each cluster

    self._load_curvature()

  def group_into_cluster(self, v_ego, d_poly):
    TR = 0.9
    dist = v_ego * TR
    # we want curvature of road from start of path not car, so subtract d_poly[3]
    lat_pos = eval_poly(d_poly, dist) - d_poly[3]  # lateral position in meters at TR seconds

    closest_cluster = None
    if abs(lat_pos) >= self.min_curvature:
      sample_coord = [v_ego, abs(lat_pos * self.y_axis_factor)]  # we multiply y so that the dist function weights x and y the same

      dists = [find_distance(sample_coord, cluster_coord) for cluster_coord in self.cluster_coords]
      closest_cluster = self.cluster_names[min(range(len(dists)), key=dists.__getitem__)]
    return closest_cluster, lat_pos

  def update(self, v_ego, d_poly, lane_probs, angle_steers):
    self._gather_data(v_ego, d_poly, angle_steers)
    offset = 0
    if v_ego < self.min_speed or math.isnan(d_poly[0]) or len(d_poly) != 4:
      return offset

    cluster, lat_pos = self.group_into_cluster(v_ego, d_poly)
    if cluster is not None:  # don't learn/return an offset if below min curvature
      direction = 'left' if lat_pos > 0 else 'right'
      lr_prob = lane_probs[0] + lane_probs[1] - lane_probs[0] * lane_probs[1]
      if lr_prob >= self.min_lr_prob:  # only learn when lane lines are present; still use existing offset
        learning_sign = 1 if lat_pos >= 0 else -1
        lr = self.get_learning_rate(direction, cluster)
        self.learned_offsets[direction][cluster]['offset'] -= d_poly[3] * lr * learning_sign  # the learning
      offset = self.learned_offsets[direction][cluster]['offset']

    self._write_curvature()
    return clip(offset, -0.3, 0.3)

  def get_learning_rate(self, direction, cluster):
    lr = self.learning_rate
    fast_iter_left = self.learned_offsets[direction][cluster]['fast_learn']
    if not isinstance(fast_iter_left, str):
      if 1 <= fast_iter_left:  # decrement until we reach 0 (self.fast_learning_for has passed)
        self.learned_offsets[direction][cluster]['fast_learn'] -= 1
        lr *= self.fast_lr_multiplier  # faster learning
      else:
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

import os
import math
import json
from common.numpy_fast import clip
from common.realtime import sec_since_boot
from selfdrive.config import Conversions as CV
from selfdrive.controls.lib.lane_planner import eval_poly

FT_TO_M = 0.3048

# by Zorrobyte
# version 4
# modified by ShaneSmiskol to add speed and curve direction as learning factors
# version 5 due to json incompatibilities


class CurvatureLearner:  # todo: disable when dynamic camera offset is working
  def __init__(self):
    self.curvature_file = '/data/curvature_offsets.json'
    rate = 1 / 20.  # pathplanner is 20 hz
    self.learning_rate = 2.8e-3 * rate  # equivalent to x/12000
    self.write_frequency = 60 * 2  # in seconds
    self.min_lr_prob = .75
    self.min_speed = 15 * CV.MPH_TO_MS

    self.directions = ['left', 'right']
    self.speed_bands = {'slow': 35 * CV.MPH_TO_MS, 'medium': 55 * CV.MPH_TO_MS, 'fast': float('inf')}
    self.curvature_bands = {'center': 5, 'inner': 5, 'outer': 5, 'sharp': float('inf')}
    self._load_curvature()

  def pick_curvature_band(self, v_ego, d_poly):
    TR = 0.9
    dist = v_ego * TR
    lat_pos = eval_poly(d_poly, dist)  # lateral position in meters at 1.8 seconds

    if abs(lat_pos) >= 0.05275:  # todo: WIP, tuning
      if abs(lat_pos) < 0.131:  # between +=[.1, 2)
        return 'center', lat_pos
      if abs(lat_pos) < 0.29618:  # between +=[2, 5)
        return 'inner', lat_pos
      if abs(lat_pos) < 0.67579:
        return 'outer', lat_pos  # between +=[5, inf)
      return 'sharp'
    return None, lat_pos  # return none when below +-0.1, removes possibility of returning offset in this case

  def _gather_data(self, v_ego, d_poly, angle_steers):
    with open('/data/curv_learner_data', 'a') as f:
      f.write('{}\n'.format({'v_ego': v_ego, 'd_poly': d_poly, 'angle_steers': angle_steers}))

  def update(self, v_ego, d_poly, lane_probs, angle_steers):
    self._gather_data(v_ego, d_poly, angle_steers)
    offset = 0
    if v_ego < self.min_speed or math.isnan(d_poly[0]) or len(d_poly) != 4:
      return offset

    lr_prob = lane_probs[0] + lane_probs[1] - lane_probs[0] * lane_probs[1]
    curvature_band, lat_pos = self.pick_curvature_band(v_ego, d_poly)

    if curvature_band is not None:  # don't learn/return an offset if not in a band
      direction = 'left' if lat_pos > 0 else 'right'
      speed_band = self.pick_speed_band(v_ego)  # will never be none
      if lr_prob >= self.min_lr_prob:  # only learn when lane lines are present; still use existing offset
        learning_sign = 1 if lat_pos >= 0 else -1
        self.learned_offsets[direction][speed_band][curvature_band] -= d_poly[3] * self.learning_rate * learning_sign  # the learning
      offset = self.learned_offsets[direction][speed_band][curvature_band]

    if sec_since_boot() - self._last_write_time >= self.write_frequency:
      self._write_curvature()
    return clip(offset, -0.3, 0.3)

  def pick_speed_band(self, v_ego):
    if v_ego <= 35 * CV.MPH_TO_MS:
      return 'slow'
    if v_ego <= 55 * CV.MPH_TO_MS:
      return 'medium'
    return 'fast'

  def _load_curvature(self):
    self._last_write_time = 0
    try:
      with open(self.curvature_file, 'r') as f:
        self.learned_offsets = json.load(f)
    except:  # can't read file or doesn't exist
      self.learned_offsets = {d: {s: {a: 0 for a in self.curvature_bands} for s in self.speed_bands} for d in self.directions}
      self._write_curvature()  # rewrite/create new file

  def _write_curvature(self):
    with open(self.curvature_file, 'w') as f:
      f.write(json.dumps(self.learned_offsets, indent=2))
    os.chmod(self.curvature_file, 0o777)
    self._last_write_time = sec_since_boot()

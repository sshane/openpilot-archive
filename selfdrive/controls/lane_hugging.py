from common.numpy_fast import interp
from common.op_params import opParams


class LaneHugging:
  def __init__(self):
    self.op_params = opParams()
    self.lane_hug_direction = self.op_params.get('lane_hug_direction', None)  # if lane hugging is present and which side. None, 'left', or 'right'
    self.lane_hug_multiplier = self.op_params.get('lane_hug_multiplier', 0.83)  # how much to reduce angle by.
    self.lane_hug_angle = 10  # where to end increasing angle modification. from 0 to this

  def lane_hug(self, angle_steers):
    if self.lane_hug_direction == 'left' and angle_steers > 0:
      angle_steers *= interp(angle_steers, [0, self.lane_hug_angle], [1.0, self.lane_hug_multiplier])  # suggestion thanks to zorrobyte
    elif self.lane_hug_direction == 'right' and angle_steers < 0:
      angle_steers *= interp(angle_steers, [0, -self.lane_hug_angle], [1.0, self.lane_hug_multiplier])

    return angle_steers

  def lane_hug_angle_steers(self, angle_steers):  # only use this function for current steer angle, not desired
    # negative angles: right
    # positive angles: left
    direction_hugging = 'left'
    hug_angle = 2.5
    if direction_hugging == 'left':
      angle_steers += hug_angle
    elif direction_hugging == 'right':
      angle_steers -= hug_angle

    return angle_steers

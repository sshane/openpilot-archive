from common.op_params import opParams
from cereal import log

LaneChangeState = log.PathPlan.LaneChangeState
LaneChangeDirection = log.PathPlan.LaneChangeDirection

class LaneHugging:
  def __init__(self):
    self.op_params = opParams()
    self.direction = self.op_params.get('lane_hug_direction', None)  # if lane hugging is present and which side. None, 'left', or 'right'
    if isinstance(self.direction, str):
      self.direction = self.direction.lower()
    self.angle_offset = abs(self.op_params.get('lane_hug_angle_offset', 0.0))

  def offset_mod(self, path_plan):
    # negative angles: right
    # positive angles: left
    angle_steers_des = path_plan.angleSteers
    lane_change_state = path_plan.laneChangeState
    direction = path_plan.laneChangeDirection
    starting = LaneChangeState.laneChangeStarting
    if self.direction == 'left' and ((lane_change_state == starting and direction != LaneChangeDirection.left) or lane_change_state != starting):
      angle_steers_des -= self.angle_offset
    elif self.direction == 'right' and ((lane_change_state == starting and direction != LaneChangeDirection.right) or lane_change_state != starting):
      angle_steers_des += self.angle_offset
    return angle_steers_des

#!/usr/bin/env python3
import math
import numpy as np
from common.params import Params
from common.numpy_fast import interp

import cereal.messaging as messaging
from cereal import car
from common.realtime import sec_since_boot
from selfdrive.swaglog import cloudlog
from selfdrive.config import Conversions as CV
from selfdrive.controls.lib.speed_smoother import speed_smoother
from selfdrive.controls.lib.longcontrol import LongCtrlState, MIN_CAN_SPEED
from selfdrive.controls.lib.fcw import FCWChecker
from selfdrive.controls.lib.long_mpc import LongitudinalMpc
from selfdrive.controls.lib.drive_helpers import V_CRUISE_MAX
from selfdrive.controls.lib.long_mpc_model import LongitudinalMpcModel

MAX_SPEED = 255.0

LON_MPC_STEP = 0.2  # first step is 0.2s
MAX_SPEED_ERROR = 2.0
AWARENESS_DECEL = -0.2     # car smoothly decel at .2m/s^2 when user is distracted

# lookup tables VS speed to determine min and max accels in cruise
# make sure these accelerations are smaller than mpc limits
_A_CRUISE_MIN_V = [-1.15, -.85, -.7, -.55, -.32]
_A_CRUISE_MIN_BP = [   0., 5.,  10., 20.,  40.]

# need fast accel at very low speed for stop and go
# make sure these accelerations are smaller than mpc limits
_A_CRUISE_MAX_V = [1.55, 1.4, 0.7, .4]
_A_CRUISE_MAX_V_FOLLOWING = [1.7, 1.65, 0.7, .5]
_A_CRUISE_MAX_BP = [0.,  6.4, 22.5, 40.]

# Lookup table for turns
_A_TOTAL_MAX_V = [2.2, 4.35]
_A_TOTAL_MAX_BP = [20., 40.]

# 75th percentile
SPEED_PERCENTILE_IDX = 7


def calc_cruise_accel_limits(v_ego, following):
  a_cruise_min = interp(v_ego, _A_CRUISE_MIN_BP, _A_CRUISE_MIN_V)

  if following:
    a_cruise_max = interp(v_ego, _A_CRUISE_MAX_BP, _A_CRUISE_MAX_V_FOLLOWING)
  else:
    a_cruise_max = interp(v_ego, _A_CRUISE_MAX_BP, _A_CRUISE_MAX_V)
  return np.vstack([a_cruise_min, a_cruise_max])


def limit_accel_in_turns(v_ego, angle_steers, a_target, CP):
  """
  This function returns a limited long acceleration allowed, depending on the existing lateral acceleration
  this should avoid accelerating when losing the target in turns
  """

  a_total_max = interp(v_ego, _A_TOTAL_MAX_BP, _A_TOTAL_MAX_V)
  a_y = v_ego**2 * angle_steers * CV.DEG_TO_RAD / (CP.steerRatio * CP.wheelbase)
  a_x_allowed = math.sqrt(max(a_total_max**2 - a_y**2, 0.))

  return [a_target[0], min(a_target[1], a_x_allowed)]


def mean(l):
  return sum(l) / len(l)


def calc_ttc(v_ego, a_ego, x_lead, v_lead, a_lead):
  max_ttc = 5.0

  v_rel = v_ego - v_lead
  a_rel = a_ego - a_lead

  # assuming that closing gap ARel comes from lead vehicle decel,
  # then limit ARel so that v_lead will get to zero in no sooner than t_decel.
  # This helps underweighting ARel when v_lead is close to zero.
  t_decel = 2.
  a_rel = np.minimum(a_rel, v_lead / t_decel)

  # delta of the quadratic equation to solve for ttc
  delta = v_rel**2 + 2 * x_lead * a_rel

  # assign an arbitrary high ttc value if there is no solution to ttc
  if delta < 0.1 or (np.sqrt(delta) + v_rel < 0.1):
    ttc = max_ttc
  else:
    ttc = np.minimum(2 * x_lead / (np.sqrt(delta) + v_rel), max_ttc)
  return ttc


class DynamicSpeed:  # todo: include DynamicLaneSpeed for adjacent lane slowing, or just merge the two together
  def __init__(self):
    self.RATE = 1 / 20.
    self.MIN_SPEED = 10 * CV.MPH_TO_MS

    self.reset()

  def reset(self):
    self.v_mpc = 0
    self.a_mpc = 0  # todo: this
    self.valid = False

  def update(self, v_ego, a_ego, lead, following):
    self.v_ego = v_ego
    self.a_ego = a_ego
    self.v_lead = lead.vLead
    self.a_lead = lead.aLeadK
    self.x_lead = lead.dRel

    if self.v_ego >= self.MIN_SPEED and following:  # todo: use lead.status if it's reliable
      self._calculate_speed()  # also sets valid
    else:
      self.reset()

  def _calculate_speed(self):
    """This will calculate the immediate speed of ego based on lead"""
    v_rel = self.v_lead - self.v_ego
    # mods = []
    # if v_rel <= -1 * CV.MPH_TO_MS:
    #   v_rels = [i * CV.MPH_TO_MS for i in [-20, -10, -5, -2.5, -1]]
    #   multipliers = [3.25, 2, 1.5, 1, .5]  # the slower the lead is, the quicker we get to half of the immediate v_rel
    #   # mods.append(abs(v_rel / 2) * interp(v_rel, v_rels, multipliers))  # todo: actually we could just use weighted average instead of multipliers. w. avg. v_ego and v_lead (maybe?)
    #   mods.append(interp(v_rel, v_rels, multipliers))
    #
    # if self.a_lead < 0.5 * CV.MPH_TO_MS:  # todo: factor in distance
    #   pass

    if v_rel <= -1 * CV.MPH_TO_MS:
      ttc = calc_ttc(self.v_ego, self.a_ego, self.x_lead, self.v_lead, self.a_lead)
      if ttc < 5:
        change = (abs(v_rel) / ttc) * self.RATE
        self.v_mpc = self.v_ego - change
        self.a_mpc = -abs(change / self.RATE)  # fixme: verify 20 is correct
        self.valid = True
        return
    self.valid = False


    # if len(mods):
    #   # mod = mean(mods)
    #   mod = mods[0]  # todo: this is temp
    #   self.v_mpc = self.v_ego - (mod * self.PER_SECOND)
    #   self.valid = True
    # else:
    #   self.valid = False


class Planner():
  def __init__(self, CP):
    self.CP = CP

    self.mpc1 = LongitudinalMpc(1)
    self.mpc2 = LongitudinalMpc(2)
    self.mpc_model = LongitudinalMpcModel()
    self.dynamic_speed = DynamicSpeed()

    self.v_acc_start = 0.0
    self.a_acc_start = 0.0

    self.v_acc = 0.0
    self.v_acc_future = 0.0
    self.a_acc = 0.0
    self.v_cruise = 0.0
    self.a_cruise = 0.0

    self.longitudinalPlanSource = 'cruise'
    self.fcw_checker = FCWChecker()
    self.path_x = np.arange(192)

    self.params = Params()
    self.first_loop = True

  def choose_solution(self, v_cruise_setpoint, enabled, model_enabled):
    if enabled:
      solutions = {'cruise': self.v_cruise}
      if self.mpc1.prev_lead_status:
        solutions['mpc1'] = self.mpc1.v_mpc
      if self.mpc2.prev_lead_status:
        solutions['mpc2'] = self.mpc2.v_mpc
      if self.mpc_model.valid and model_enabled:
        solutions['model'] = self.mpc_model.v_mpc
      if self.dynamic_speed.valid:
        solutions['dynamicSpeed'] = self.dynamic_speed.v_mpc

      slowest = min(solutions, key=solutions.get)

      self.longitudinalPlanSource = slowest
      # Choose lowest of MPC and cruise
      if slowest == 'mpc1':
        self.v_acc = self.mpc1.v_mpc
        self.a_acc = self.mpc1.a_mpc
      elif slowest == 'mpc2':
        self.v_acc = self.mpc2.v_mpc
        self.a_acc = self.mpc2.a_mpc
      elif slowest == 'cruise':
        self.v_acc = self.v_cruise
        self.a_acc = self.a_cruise
      elif slowest == 'model':
        self.v_acc = self.mpc_model.v_mpc
        self.a_acc = self.mpc_model.a_mpc
      elif slowest == 'dynamicSpeed':
        self.v_acc = self.dynamic_speed.v_mpc
        self.a_acc = self.dynamic_speed.a_mpc

    self.v_acc_future = min([self.mpc1.v_mpc_future, self.mpc2.v_mpc_future, self.mpc_model.v_mpc_future, v_cruise_setpoint])

  def update(self, sm, pm, CP, VM, PP):
    """Gets called when new radarState is available"""
    cur_time = sec_since_boot()
    v_ego = sm['carState'].vEgo

    long_control_state = sm['controlsState'].longControlState
    v_cruise_kph = sm['controlsState'].vCruise
    force_slow_decel = sm['controlsState'].forceDecel

    v_cruise_kph = min(v_cruise_kph, V_CRUISE_MAX)
    v_cruise_setpoint = v_cruise_kph * CV.KPH_TO_MS

    lead_1 = sm['radarState'].leadOne
    lead_2 = sm['radarState'].leadTwo

    enabled = (long_control_state == LongCtrlState.pid) or (long_control_state == LongCtrlState.stopping)
    following = lead_1.status and lead_1.dRel < 45.0 and lead_1.vLeadK > v_ego and lead_1.aLeadK > 0.0
    self.dynamic_speed.update(v_ego, sm['carState'].aEgo, lead_1, following)

    # Calculate speed for normal cruise control
    if enabled and not self.first_loop and not sm['carState'].gasPressed:  # gasPress is to avoid hard decel after user accelerates with gas while engaged
      accel_limits = [float(x) for x in calc_cruise_accel_limits(v_ego, following)]
      jerk_limits = [min(-0.1, accel_limits[0]), max(0.1, accel_limits[1])]  # TODO: make a separate lookup for jerk tuning
      accel_limits_turns = limit_accel_in_turns(v_ego, sm['carState'].steeringAngle, accel_limits, self.CP)

      if force_slow_decel:
        # if required so, force a smooth deceleration
        accel_limits_turns[1] = min(accel_limits_turns[1], AWARENESS_DECEL)
        accel_limits_turns[0] = min(accel_limits_turns[0], accel_limits_turns[1])

      self.v_cruise, self.a_cruise = speed_smoother(self.v_acc_start, self.a_acc_start,
                                                    v_cruise_setpoint,
                                                    accel_limits_turns[1], accel_limits_turns[0],
                                                    jerk_limits[1], jerk_limits[0],
                                                    LON_MPC_STEP)

      # cruise speed can't be negative even is user is distracted
      self.v_cruise = max(self.v_cruise, 0.)
    else:
      starting = long_control_state == LongCtrlState.starting
      a_ego = min(sm['carState'].aEgo, 0.0)
      reset_speed = MIN_CAN_SPEED if starting else v_ego
      reset_accel = self.CP.startAccel if starting else a_ego
      self.v_acc = reset_speed
      self.a_acc = reset_accel
      self.v_acc_start = reset_speed
      self.a_acc_start = reset_accel
      self.v_cruise = reset_speed
      self.a_cruise = reset_accel

    self.mpc1.set_cur_state(self.v_acc_start, self.a_acc_start)
    self.mpc2.set_cur_state(self.v_acc_start, self.a_acc_start)
    self.mpc_model.set_cur_state(self.v_acc_start, self.a_acc_start)

    self.mpc1.update(pm, sm['carState'], lead_1, v_cruise_setpoint)
    self.mpc2.update(pm, sm['carState'], lead_2, v_cruise_setpoint)
    self.mpc_model.update(sm['carState'].vEgo, sm['carState'].aEgo,
                          sm['model'].longitudinal.distances,
                          sm['model'].longitudinal.speeds,
                          sm['model'].longitudinal.accelerations)

    self.choose_solution(v_cruise_setpoint, enabled, sm['modelLongButton'].enabled)

    # determine fcw
    if self.mpc1.new_lead:
      self.fcw_checker.reset_lead(cur_time)

    blinkers = sm['carState'].leftBlinker or sm['carState'].rightBlinker
    fcw = self.fcw_checker.update(self.mpc1.mpc_solution, cur_time,
                                  sm['controlsState'].active,
                                  v_ego, sm['carState'].aEgo,
                                  lead_1.dRel, lead_1.vLead, lead_1.aLeadK,
                                  lead_1.yRel, lead_1.vLat,
                                  lead_1.fcw, blinkers) and not sm['carState'].brakePressed
    if fcw:
      cloudlog.info("FCW triggered %s", self.fcw_checker.counters)

    radar_dead = not sm.alive['radarState']

    radar_errors = list(sm['radarState'].radarErrors)
    radar_fault = car.RadarData.Error.fault in radar_errors
    radar_can_error = car.RadarData.Error.canError in radar_errors

    # **** send the plan ****
    plan_send = messaging.new_message('plan')

    plan_send.valid = sm.all_alive_and_valid(service_list=['carState', 'controlsState', 'radarState'])

    plan_send.plan.mdMonoTime = sm.logMonoTime['model']
    plan_send.plan.radarStateMonoTime = sm.logMonoTime['radarState']

    # longitudal plan
    plan_send.plan.vCruise = float(self.v_cruise)
    plan_send.plan.aCruise = float(self.a_cruise)
    plan_send.plan.vStart = float(self.v_acc_start)
    plan_send.plan.aStart = float(self.a_acc_start)
    plan_send.plan.vTarget = float(self.v_acc)
    plan_send.plan.aTarget = float(self.a_acc)
    plan_send.plan.vTargetFuture = float(self.v_acc_future)
    plan_send.plan.hasLead = self.mpc1.prev_lead_status
    plan_send.plan.longitudinalPlanSource = self.longitudinalPlanSource

    radar_valid = not (radar_dead or radar_fault)
    plan_send.plan.radarValid = bool(radar_valid)
    plan_send.plan.radarCanError = bool(radar_can_error)

    plan_send.plan.processingDelay = (plan_send.logMonoTime / 1e9) - sm.rcv_time['radarState']

    # Send out fcw
    plan_send.plan.fcw = fcw

    pm.send('plan', plan_send)

    # Interpolate 0.05 seconds and save as starting point for next iteration
    a_acc_sol = self.a_acc_start + (CP.radarTimeStep / LON_MPC_STEP) * (self.a_acc - self.a_acc_start)
    v_acc_sol = self.v_acc_start + CP.radarTimeStep * (a_acc_sol + self.a_acc_start) / 2.0
    self.v_acc_start = v_acc_sol
    self.a_acc_start = a_acc_sol

    self.first_loop = False

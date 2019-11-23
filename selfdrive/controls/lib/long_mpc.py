import os
from common.numpy_fast import interp, clip
import math

import selfdrive.messaging as messaging
from selfdrive.swaglog import cloudlog
from common.realtime import sec_since_boot
from selfdrive.controls.lib.radar_helpers import _LEAD_ACCEL_TAU
from selfdrive.controls.lib.longitudinal_mpc import libmpc_py
from selfdrive.controls.lib.drive_helpers import MPC_COST_LONG
from common.op_params import opParams

LOG_MPC = os.environ.get('LOG_MPC', False)


class LongitudinalMpc():
  def __init__(self, mpc_id):
    self.mpc_id = mpc_id

    self.setup_mpc()
    self.v_mpc = 0.0
    self.v_mpc_future = 0.0
    self.a_mpc = 0.0
    self.v_cruise = 0.0
    self.prev_lead_status = False
    self.prev_lead_x = 0.0
    self.new_lead = False

    self.op_params = opParams()
    self.car_state = None
    self.lead_data = {'v_lead': None, 'x_lead': None, 'a_lead': None, 'status': False}
    self.v_ego = 0.0
    self.a_ego = 0.0
    self.last_cost = 0.0
    self.TR = 1.8
    self.customTR = self.op_params.get('following_distance', None)

    self.last_cloudlog_t = 0.0

  def send_mpc_solution(self, pm, qp_iterations, calculation_time):
    qp_iterations = max(0, qp_iterations)
    dat = messaging.new_message()
    dat.init('liveLongitudinalMpc')
    dat.liveLongitudinalMpc.xEgo = list(self.mpc_solution[0].x_ego)
    dat.liveLongitudinalMpc.vEgo = list(self.mpc_solution[0].v_ego)
    dat.liveLongitudinalMpc.aEgo = list(self.mpc_solution[0].a_ego)
    dat.liveLongitudinalMpc.xLead = list(self.mpc_solution[0].x_l)
    dat.liveLongitudinalMpc.vLead = list(self.mpc_solution[0].v_l)
    dat.liveLongitudinalMpc.cost = self.mpc_solution[0].cost
    dat.liveLongitudinalMpc.aLeadTau = self.a_lead_tau
    dat.liveLongitudinalMpc.qpIterations = qp_iterations
    dat.liveLongitudinalMpc.mpcId = self.mpc_id
    dat.liveLongitudinalMpc.calculationTime = calculation_time
    pm.send('liveLongitudinalMpc', dat)

  def setup_mpc(self):
    ffi, self.libmpc = libmpc_py.get_libmpc(self.mpc_id)
    self.libmpc.init(MPC_COST_LONG.TTC, MPC_COST_LONG.DISTANCE,
                     MPC_COST_LONG.ACCELERATION, MPC_COST_LONG.JERK)

    self.mpc_solution = ffi.new("log_t *")
    self.cur_state = ffi.new("state_t *")
    self.cur_state[0].v_ego = 0
    self.cur_state[0].a_ego = 0
    self.a_lead_tau = _LEAD_ACCEL_TAU

  def set_cur_state(self, v, a):
    self.cur_state[0].v_ego = v
    self.cur_state[0].a_ego = a

  def set_TR(self):
    if not self.lead_data['status']:
      self.TR = 1.8

    elif self.customTR is not None:
      self.TR = clip(self.customTR, 0.9, 2.7)

    else:
      self.TR = self.dynamic_follow()

    self.change_cost()

  def change_cost(self):
    new_cost = self.get_cost()
    if self.last_cost != new_cost:
      self.libmpc.change_tr(MPC_COST_LONG.TTC, new_cost, MPC_COST_LONG.ACCELERATION, MPC_COST_LONG.JERK)
      self.last_cost = new_cost

  def get_cost(self):
    TRs = [0.9, 1.8, 2.7]
    costs = [1.0, 0.1, 0.05]
    return interp(self.TR, TRs, costs)

  def dynamic_follow(self):  # in m/s
    x_vel = [0.0, 5.222, 11.164, 14.937, 20.973, 33.975, 42.469]
    y_mod = [1.542, 1.553, 1.599, 1.68, 1.75, 1.855, 1.9]

    if self.v_ego > 6.7056:  # 15 mph
      TR = interp(self.v_ego, x_vel, y_mod)
    else:  # this allows us to get slightly closer to the lead car when stopping, while being able to have smooth stop and go
      x = [4.4704, 6.7056]  # smoothly ramp TR between 10 and 15 mph from 1.8s to defined TR above at 15mph
      y = [1.8, interp(x[1], x_vel, y_mod)]
      TR = interp(self.v_ego, x, y)

    # Dynamic follow modifications
    x = [-15.6464, -9.8422, -6.0, -4.0, -2.68, -2.3, -1.8, -1.26, -0.61, 0, 0.61, 1.26, 2.1, 2.68]  # relative velocity values
    y = [.504, 0.34, 0.29, 0.25, 0.22, 0.19, 0.13, 0.053, 0.017, 0, -0.015, -0.042, -0.108, -0.163]  # modification values
    TR_mod = interp(self.lead_data['v_lead'] - self.v_ego, x, y)

    x = [-2.235, -1.49, -1.1, -0.67, -0.224, 0.0, 0.67, 1.1, 1.49]  # lead acceleration values
    y = [0.26, 0.182, 0.104, 0.052, 0.039, 0.0, -0.016, -0.032, -0.056]  # modification values
    TR_mod += interp(self.lead_data['a_lead'], x, y)
    # TR_mod += interp(self.get_acceleration(), x, y)  # todo: when lead car has been braking over the past 3 seconds, slightly increase TR

    TR += TR_mod

    if self.car_state.leftBlinker or self.car_state.rightBlinker:
      x = [8.9408, 22.352, 31.2928]  # 20, 50, 70 mph
      y = [1.0, .86, .84]  # reduce TR when changing lanes
      TR *= interp(self.v_ego, x, y)

    #TR *= self.get_traffic_level()  # modify TR based on last minute of traffic data  # todo: look at getting this to work, a model could be used

    return clip(round(TR, 3), 0.9, 2.7)

  def update(self, pm, CS, lead, v_cruise_setpoint):
    self.v_ego = CS.vEgo
    self.a_ego = CS.aEgo
    self.car_state = CS

    # Setup current mpc state
    self.cur_state[0].x_ego = 0.0

    if lead is not None and lead.status:
      x_lead = lead.dRel
      v_lead = max(0.0, lead.vLead)
      a_lead = lead.aLeadK

      if (v_lead < 0.1 or -a_lead / 2.0 > v_lead):
        v_lead = 0.0
        a_lead = 0.0

      self.lead_data['v_lead'] = v_lead
      self.lead_data['a_lead'] = a_lead
      self.lead_data['x_lead'] = x_lead
      self.lead_data['status'] = lead.status

      self.a_lead_tau = lead.aLeadTau
      self.new_lead = False
      if not self.prev_lead_status or abs(x_lead - self.prev_lead_x) > 2.5:
        self.libmpc.init_with_simulation(self.v_mpc, x_lead, v_lead, a_lead, self.a_lead_tau)
        self.new_lead = True

      self.prev_lead_status = True
      self.prev_lead_x = x_lead
      self.cur_state[0].x_l = x_lead
      self.cur_state[0].v_l = v_lead
    else:
      self.lead_data['v_lead'] = 0.0
      self.lead_data['a_lead'] = 0.0
      self.lead_data['x_lead'] = 0.0
      self.lead_data['status'] = False
      self.prev_lead_status = False
      # Fake a fast lead car, so mpc keeps running
      self.cur_state[0].x_l = 50.0
      self.cur_state[0].v_l = self.v_ego + 10.0
      a_lead = 0.0
      self.a_lead_tau = _LEAD_ACCEL_TAU

    # Calculate mpc
    t = sec_since_boot()
    self.set_TR()
    n_its = self.libmpc.run_mpc(self.cur_state, self.mpc_solution, self.a_lead_tau, a_lead, self.TR)
    duration = int((sec_since_boot() - t) * 1e9)

    if LOG_MPC:
      self.send_mpc_solution(pm, n_its, duration)

    # Get solution. MPC timestep is 0.2 s, so interpolation to 0.05 s is needed
    self.v_mpc = self.mpc_solution[0].v_ego[1]
    self.a_mpc = self.mpc_solution[0].a_ego[1]
    self.v_mpc_future = self.mpc_solution[0].v_ego[10]

    # Reset if NaN or goes through lead car
    crashing = any(lead - ego < -50 for (lead, ego) in zip(self.mpc_solution[0].x_l, self.mpc_solution[0].x_ego))
    nans = any(math.isnan(x) for x in self.mpc_solution[0].v_ego)
    backwards = min(self.mpc_solution[0].v_ego) < -0.01

    if ((backwards or crashing) and self.prev_lead_status) or nans:
      if t > self.last_cloudlog_t + 5.0:
        self.last_cloudlog_t = t
        cloudlog.warning("Longitudinal mpc %d reset - backwards: %s crashing: %s nan: %s" % (
                          self.mpc_id, backwards, crashing, nans))

      self.libmpc.init(MPC_COST_LONG.TTC, MPC_COST_LONG.DISTANCE,
                       MPC_COST_LONG.ACCELERATION, MPC_COST_LONG.JERK)
      self.cur_state[0].v_ego = self.v_ego
      self.cur_state[0].a_ego = 0.0
      self.v_mpc = self.v_ego
      self.a_mpc = CS.aEgo
      self.prev_lead_status = False

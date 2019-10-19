import os
import math

import selfdrive.messaging as messaging
from selfdrive.swaglog import cloudlog
from common.realtime import sec_since_boot
from selfdrive.controls.lib.radar_helpers import _LEAD_ACCEL_TAU
from selfdrive.controls.lib.longitudinal_mpc import libmpc_py
from selfdrive.controls.lib.drive_helpers import MPC_COST_LONG
from selfdrive.services import service_list
from common.travis_checker import travis
import time

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

    self.last_cloudlog_t = 0.0

    self.liveTracks = messaging.sub_sock(service_list['liveTracks'].port)
    self.last_track_data = {'tracks': []}
    self.df_data = []
    self.sensor = messaging.sub_sock(service_list['sensorEvents'].port)
    self.df_file_path = "/data/openpilot/selfdrive/df_dc/df-data"
    self.inputs_list = ['v_ego', 'a_ego', 'v_lead', 'lead_status', 'x_lead', 'y_lead', 'a_lead', 'a_rel', 'v_lat',
                        'steer_angle', 'steer_rate', 'track_data', 'time', 'gas', 'brake',
                        'car_gas', 'left_blinker', 'right_blinker', 'set_speed', 'new_accel', 'gyro']
    if not os.path.exists(self.df_file_path) and not travis:
      with open(self.df_file_path, "a") as f:
        f.write('{}\n'.format(self.inputs_list))

    self.last_velocity = 0
    self.last_time = time.time()
    self.last_gyro = None
    self.write_time = time.time()

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

  def get_track_data(self):
    tracks = messaging.recv_sock(self.liveTracks)
    if tracks is not None:
      track_data = {'tracks': [], 'live': True}  # true tells us it's live data
      for track in tracks.liveTracks:
        track_data['tracks'].append(
          {'trackID': track.trackId, 'yRel': track.yRel, 'dRel': track.dRel, 'vRel': track.vRel,
           'stationary': track.stationary, 'oncoming': track.oncoming, 'status': track.status})
      self.last_track_data = track_data
    else:  # live track data not available, use last tracks
      track_data = self.last_track_data
      track_data['live'] = False  # false tells us it's old data
    return track_data

  def get_gyro(self):
    gyro = None
    sensors = messaging.recv_sock(self.sensor)
    if sensors is not None:
      for sensor in sensors.sensorEvents:
        if sensor.type == 4:  # gyro
          gyro = list(sensor.gyro.v)
    if gyro is None:
      gyro = self.last_gyro
    else:
      self.last_gyro = gyro
    return gyro

  def update(self, pm, CS, lead, v_cruise_setpoint):
    v_ego = CS.vEgo
    abs_time = (time.time() - self.last_time)
    new_accel = ((v_ego - self.last_velocity) / abs_time) if abs_time > 0 else None
    self.last_time = time.time()
    self.last_velocity = v_ego
    a_ego = CS.aEgo
    gas = CS.gas
    car_gas = CS.stockGas
    brake = CS.brake
    steer_angle = CS.steeringAngle
    steer_rate = CS.steeringRate
    left_blinker = CS.leftBlinker
    right_blinker = CS.rightBlinker
    set_speed = CS.cruiseState.speed
    track_data = self.get_track_data()
    gyro = self.get_gyro()

    if lead is not None and lead.status:
      x_lead = lead.dRel
      y_lead = lead.yRel
      v_lat = lead.vLat
      v_lead = max(0.0, lead.vLead)
      a_lead = lead.aLeadK
      a_rel = lead.aRel
      lead_status = lead.status
    else:
      x_lead = 0.0
      y_lead = 0.0
      v_lat = 0.0
      v_lead = 0.0
      a_lead = 0.0
      a_rel = 0.0
      lead_status = False

    if self.mpc_id == 1 and not CS.cruiseState.enabled and CS.gearShifter == 'drive' and CS.sportOn is False and not travis:  # if openpilot not engaged and in drive, gather data
      self.df_data.append([v_ego, a_ego, v_lead, lead_status, x_lead, y_lead, a_lead, a_rel, v_lat, steer_angle, steer_rate,
                           track_data, time.time(), gas, brake, car_gas, left_blinker, right_blinker, set_speed, new_accel, gyro])

      if time.time() - self.write_time > 2*60 and len(self.df_data) > 1:
        try:
          with open(self.df_file_path, "a") as f:
            f.write('{}\n'.format("\n".join([str(i) for i in self.df_data])))
          self.df_data = []
          self.write_time = time.time()
        except Exception as e:
          with open('/data/write_errors', 'a') as f:
            f.write('write error: {}\n'.format(e))

    # Setup current mpc state
    self.cur_state[0].x_ego = 0.0

    if lead is not None and lead.status:
      x_lead = lead.dRel
      v_lead = max(0.0, lead.vLead)
      a_lead = lead.aLeadK

      if (v_lead < 0.1 or -a_lead / 2.0 > v_lead):
        v_lead = 0.0
        a_lead = 0.0

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
      self.prev_lead_status = False
      # Fake a fast lead car, so mpc keeps running
      self.cur_state[0].x_l = 50.0
      self.cur_state[0].v_l = v_ego + 10.0
      a_lead = 0.0
      self.a_lead_tau = _LEAD_ACCEL_TAU

    # Calculate mpc
    t = sec_since_boot()
    n_its = self.libmpc.run_mpc(self.cur_state, self.mpc_solution, self.a_lead_tau, a_lead)
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
      self.cur_state[0].v_ego = v_ego
      self.cur_state[0].a_ego = 0.0
      self.v_mpc = v_ego
      self.a_mpc = CS.aEgo
      self.prev_lead_status = False

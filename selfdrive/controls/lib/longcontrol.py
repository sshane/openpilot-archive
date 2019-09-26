from cereal import log
from common.numpy_fast import clip, interp
from selfdrive.controls.lib.pid import PIController
from selfdrive.df import df_wrapper

LongCtrlState = log.ControlsState.LongControlState

STOPPING_EGO_SPEED = 0.5
MIN_CAN_SPEED = 0.3  # TODO: parametrize this in car interface
STOPPING_TARGET_SPEED = MIN_CAN_SPEED + 0.01
STARTING_TARGET_SPEED = 0.5
BRAKE_THRESHOLD_TO_PID = 0.2

STOPPING_BRAKE_RATE = 0.2  # brake_travel/s while trying to stop
STARTING_BRAKE_RATE = 0.8  # brake_travel/s while releasing on restart
BRAKE_STOPPING_TARGET = 0.5  # apply at least this amount of brake to maintain the vehicle stationary

_MAX_SPEED_ERROR_BP = [0., 30.]  # speed breakpoints
_MAX_SPEED_ERROR_V = [1.5, .8]  # max positive v_pid error VS actual speed; this avoids controls windup due to slow pedal resp

RATE = 100.0


def interp_fast(x, xp, fp=[0, 1], ext=False):  # extrapolates above range when ext is True
  interped = (((x - xp[0]) * (fp[1] - fp[0])) / (xp[1] - xp[0])) + fp[0]
  return interped if ext else min(max(fp[0], interped), fp[1])

def pad_tracks(tracks, max_tracks):
  to_add = max_tracks - len(tracks)
  to_add_left = to_add - (to_add // 2)
  to_add_right = to_add - to_add_left
  to_pad = [[0, 0, 0]]
  return (to_pad * to_add_left) + tracks + (to_pad * to_add_right)

def long_control_state_trans(active, long_control_state, v_ego, v_target, v_pid,
                             output_gb, brake_pressed, cruise_standstill):
  """Update longitudinal control state machine"""
  stopping_condition = (v_ego < 2.0 and cruise_standstill) or \
                       (v_ego < STOPPING_EGO_SPEED and \
                        ((v_pid < STOPPING_TARGET_SPEED and v_target < STOPPING_TARGET_SPEED) or
                        brake_pressed))

  starting_condition = v_target > STARTING_TARGET_SPEED and not cruise_standstill

  if not active:
    long_control_state = LongCtrlState.off

  else:
    if long_control_state == LongCtrlState.off:
      if active:
        long_control_state = LongCtrlState.pid

    elif long_control_state == LongCtrlState.pid:
      if stopping_condition:
        long_control_state = LongCtrlState.stopping

    elif long_control_state == LongCtrlState.stopping:
      if starting_condition:
        long_control_state = LongCtrlState.starting

    elif long_control_state == LongCtrlState.starting:
      if stopping_condition:
        long_control_state = LongCtrlState.stopping
      elif output_gb >= -BRAKE_THRESHOLD_TO_PID:
        long_control_state = LongCtrlState.pid

  return long_control_state


class LongControl(object):
  def __init__(self, CP, compute_gb):
    self.long_control_state = LongCtrlState.off  # initialized to off
    self.pid = PIController((CP.longitudinalTuning.kpBP, CP.longitudinalTuning.kpV),
                            (CP.longitudinalTuning.kiBP, CP.longitudinalTuning.kiV),
                            rate=RATE,
                            sat_limit=0.8,
                            convert=compute_gb)
    self.v_pid = 0.0
    self.last_output_gb = 0.0
    self.model_wrapper = df_wrapper.get_wrapper()
    self.model_wrapper.init_model()
    self.past_data = []
    self.scales = {'a_ego': [-4.098987579345703, 3.713705539703369],
                   'a_lead': [-3.709836483001709, 3.4350156784057617],
                   'dRel': [0.11999999731779099, 196.32000732421875],
                   'max_tracks': 16,
                   'steer_angle': [-568.0, 591.5999755859375],
                   'steer_rate': [-775.0, 816.0],
                   'vRel': [-51.20000076293945, 28.100000381469727],
                   'v_ego': [-0.15605801343917847, 36.29853057861328],
                   'yRel': [-15.0, 15.0]}
    self.P = 0.17
    self.prev_gas = 0.0

  def p_controller(self, des_acc, cur_acc, v_ego):  # desired acceleration
    error = cur_acc - des_acc
    gas = clip(self.prev_gas - (error * self.P), -1, 1)
    self.prev_gas = gas
    if abs(des_acc) < 0.11176 and v_ego < 0.22352:  # holds us at a stop
      gas = -0.2
    return gas

  def df_live_tracks_acc(self, v_ego, a_ego, track_data, steering_angle, steering_rate, left_blinker, right_blinker,
                     radar_state, set_speed):
    tracks_normalized = [[interp_fast(track[0], self.scales['yRel']),
                          interp_fast(track[1], self.scales['dRel']),  # normalize track data
                          interp_fast(track[2], self.scales['vRel'])] for track in track_data]

    tracks_sorted = sorted(tracks_normalized, key=lambda track: track[0])  # sort tracks by yRel
    padded_tracks = pad_tracks(tracks_sorted,
                               self.scales['max_tracks'])  # pad tracks, keeping data in the center, sorted by yRel

    flat_tracks = [i for x in padded_tracks for i in x]  # flatten track data for model
    v_ego = interp_fast(v_ego, self.scales['v_ego'])
    steering_angle = interp_fast(steering_angle, self.scales['steer_angle'])
    steering_rate = interp_fast(steering_rate, self.scales['steer_rate'])
    left_blinker = 1 if left_blinker else 0
    right_blinker = 1 if right_blinker else 0
    a_lead, lead_status = self.get_lead(radar_state)
    if lead_status == 0:
      a_lead = 0.0
    else:
      a_lead = interp_fast(a_lead, self.scales['a_lead'])
    # set_speed = interp_fast(set_speed, self.scales['set_speed'])

    final_input = [v_ego, steering_angle, steering_rate, a_lead, left_blinker, right_blinker] + flat_tracks
    model_output = float(self.model_wrapper.run_model_live_tracks(final_input))

    des_acc = interp_fast(model_output, [0, 1], self.scales['a_ego'], ext=True)
    gas_output = self.p_controller(des_acc, a_ego, v_ego)
    return gas_output

  def df_live_tracks(self, v_ego, a_ego, track_data, steering_angle, steering_rate, left_blinker, right_blinker,
                     radar_state, set_speed):
    tracks_normalized = [[interp_fast(track[0], self.scales['yRel']),
                          interp_fast(track[1], self.scales['dRel']),  # normalize track data
                          interp_fast(track[2], self.scales['vRel'])] for track in track_data]

    tracks_sorted = sorted(tracks_normalized, key=lambda track: track[0])  # sort tracks by yRel
    padded_tracks = pad_tracks(tracks_sorted,
                               self.scales['max_tracks'])  # pad tracks, keeping data in the center, sorted by yRel

    flat_tracks = [i for x in padded_tracks for i in x]  # flatten track data for model
    v_ego = interp_fast(v_ego, self.scales['v_ego'])
    steering_angle = interp_fast(steering_angle, self.scales['steer_angle'])
    steering_rate = interp_fast(steering_rate, self.scales['steer_rate'])
    left_blinker = 1 if left_blinker else 0
    right_blinker = 1 if right_blinker else 0
    a_lead, lead_status = self.get_lead(radar_state)
    if lead_status == 0:
      a_lead = 0.0
    else:
      a_lead = interp_fast(a_lead, self.scales['a_lead'])
    # set_speed = interp_fast(set_speed, self.scales['set_speed'])

    final_input = [v_ego, steering_angle, steering_rate, a_lead, left_blinker, right_blinker] + flat_tracks
    with open('/data/testshape', 'a') as f:
      f.write('{}\n'.format(len(final_input)))
    model_output = float(self.model_wrapper.run_model_live_tracks(final_input))
    model_output = (model_output - 0.52) * 2.0
    if model_output < 0.0:
      model_output *= 2.5
    return clip(model_output, -1.0, 1.0)


  def get_lead(self, radar_state):
    if radar_state is not None:
      lead_1 = radar_state.leadOne
      if lead_1 is not None and lead_1.status:
        return lead_1.aLeadK, 1
    return 0, 0  # second 0 tells model to not care about 0 a_lead instead of interpreting it as 0 accel

  def df(self, radar_state, v_ego, a_ego, set_speed):
    scales = {'v_ego_scale': [0.0, 40.755523681641],
              'v_lead_scale': [0.0, 44.508262634277],
              'x_lead_scale': [0.125, 146.375]}

    #TR = 1.4
    #v_lead = set_speed
    #x_lead = v_ego * TR
    #a_lead = 0.0
    #a_rel = 0.0
    seq_len = 20 # shape 20, 3
    has_lead = False
    if radar_state is not None:
      lead_1 = radar_state.leadOne
      if lead_1 is not None and lead_1.status:
        has_lead = True
        #x_lead, v_lead, a_lead, a_rel = (lead_1.dRel, lead_1.vLead, lead_1.aLeadK, lead_1.aRel) if lead_1.vLead < set_speed else (x_lead, set_speed, 0.0, 0.0)
        self.past_data.append([interp_fast(v_ego, scales['v_ego_scale']), interp_fast(lead_1.vLead, scales['v_lead_scale']), interp_fast(lead_1.dRel, scales['x_lead_scale'])])

    #model_output = float(self.model_wrapper.run_model(norm(v_ego, scales['v_ego_scale']), norm(a_ego, scales['a_ego_scale']), norm(v_lead, scales['v_lead_scale']), norm(x_lead, scales['x_lead_scale']), norm(a_lead, scales['a_lead_scale'])))
    #return clip((model_output - 0.50) * 2.3, -1.0, 1.0)

    while len(self.past_data) > seq_len:
      del self.past_data[0]

    if len(self.past_data) == seq_len and has_lead:
      model_output = self.model_wrapper.run_model_lstm([i for x in self.past_data for i in x])
      with open('/data/df_output', 'a') as f:
        f.write('\n' + str(model_output) + ' ' + str(self.past_data))
      return clip((model_output - 0.50) * 4.0, -1.0, 1.0)
    else:
      with open('/data/noneh', 'a') as f:
        f.write('none\n')
      return None

  def reset(self, v_pid):
    """Reset PID controller and change setpoint"""
    self.pid.reset()
    self.v_pid = v_pid

  def update(self, active, v_ego, a_ego, set_speed, radar_state, brake_pressed, standstill, cruise_standstill, v_cruise, v_target, v_target_future, a_target, CP, track_data, steering_angle,
             steering_rate, left_blinker, right_blinker):
    """Update longitudinal control. This updates the state machine and runs a PID loop"""
    # Actuation limits
    df_output = self.df_live_tracks_acc(v_ego, a_ego, track_data, steering_angle, steering_rate, left_blinker,
                                    right_blinker, radar_state, set_speed)
    #df_output = self.df(radar_state, v_ego, a_ego, set_speed)
    if df_output is not None:
      return max(df_output, 0), -min(df_output, 0.0)
    else:  # use mpc when no lead
      gas_max = interp(v_ego, CP.gasMaxBP, CP.gasMaxV)
      brake_max = interp(v_ego, CP.brakeMaxBP, CP.brakeMaxV)

      # Update state machine
      output_gb = self.last_output_gb
      self.long_control_state = long_control_state_trans(active, self.long_control_state, v_ego,
                                                         v_target_future, self.v_pid, output_gb,
                                                         brake_pressed, cruise_standstill)

      v_ego_pid = max(v_ego, MIN_CAN_SPEED)  # Without this we get jumps, CAN bus reports 0 when speed < 0.3

      if self.long_control_state == LongCtrlState.off:
        self.v_pid = v_ego_pid
        self.pid.reset()
        output_gb = 0.

      # tracking objects and driving
      elif self.long_control_state == LongCtrlState.pid:
        self.v_pid = v_target
        self.pid.pos_limit = gas_max
        self.pid.neg_limit = - brake_max

        # Toyota starts braking more when it thinks you want to stop
        # Freeze the integrator so we don't accelerate to compensate, and don't allow positive acceleration
        prevent_overshoot = not CP.stoppingControl and v_ego < 1.5 and v_target_future < 0.7
        deadzone = interp(v_ego_pid, CP.longitudinalTuning.deadzoneBP, CP.longitudinalTuning.deadzoneV)

        output_gb = self.pid.update(self.v_pid, v_ego_pid, speed=v_ego_pid, deadzone=deadzone, feedforward=a_target, freeze_integrator=prevent_overshoot)

        if prevent_overshoot:
          output_gb = min(output_gb, 0.0)

      # Intention is to stop, switch to a different brake control until we stop
      elif self.long_control_state == LongCtrlState.stopping:
        # Keep applying brakes until the car is stopped
        if not standstill or output_gb > -BRAKE_STOPPING_TARGET:
          output_gb -= STOPPING_BRAKE_RATE / RATE
        output_gb = clip(output_gb, -brake_max, gas_max)

        self.v_pid = v_ego
        self.pid.reset()

      # Intention is to move again, release brake fast before handing control to PID
      elif self.long_control_state == LongCtrlState.starting:
        if output_gb < -0.2:
          output_gb += STARTING_BRAKE_RATE / RATE
        self.v_pid = v_ego
        self.pid.reset()

      self.last_output_gb = output_gb
      final_gas = clip(output_gb, 0., gas_max)
      final_brake = -clip(output_gb, -brake_max, 0.)

      return final_gas, final_brake

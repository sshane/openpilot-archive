from cereal import log
from common.numpy_fast import clip, interp
from selfdrive.controls.lib.pid import PIController
from selfdrive.df import df_wrapper
from common.travis_checker import travis
import time

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
  return interped if ext else min(max(min(fp), interped), max(fp))


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


class LongControl():
  def __init__(self, CP, compute_gb):
    self.long_control_state = LongCtrlState.off  # initialized to off
    self.pid = PIController((CP.longitudinalTuning.kpBP, CP.longitudinalTuning.kpV),
                            (CP.longitudinalTuning.kiBP, CP.longitudinalTuning.kiV),
                            rate=RATE,
                            sat_limit=0.8,
                            convert=compute_gb)
    self.pid_acc = PIController(([0., 35.], [.0, .1]),
                                 ([0, 35], [2, .5]),
                                 k_f=1, pos_limit=1.0, neg_limit=-1.0, rate=20)
    self.v_pid = 0.0
    self.last_output_gb = 0.0
    self.model_wrapper = df_wrapper.get_wrapper()
    self.model_wrapper.init_model()
    self.past_data = []
    self.scales = {'yRel': [-23.416223526000977, 23.289180755615234], 'dRel': [0.75, 151.5], 'vRel': [-32.875, 30.0],
                   'v_ego': [0.0, 29.5767879486084], 'steer_angle': [-506.0, 449.8125], 'steer_rate': [-360.0, 369.5],
                   'a_lead': [-4.980541229248047, 8.461540222167969],
                   'x_lead': [-16.047168731689453, 169.9757843017578],
                   'v_lead': [0.0, 30.18574333190918], 'max_tracks': 18}
    self.P = 0.04
    self.prev_gas = 0.0
    self.last_speed = None
    self.last_model_output = None
    self.last_time = time.time()

  def df_controller(self, v_ego, a_ego, track_data, steering_angle, steering_rate, left_blinker, right_blinker, radar_state, set_speed):  # out of date with current architecture
    predict_rate = 0.25  # seconds
    if time.time() - self.last_time >= predict_rate or self.last_model_output is None:
      self.last_time = time.time()
      model_output = self.df_live_tracks(v_ego, a_ego, track_data, steering_angle, steering_rate, left_blinker,
                                         right_blinker, radar_state, set_speed)
      self.last_model_output = float(model_output)

    return self.last_model_output

  def df_live_tracks(self, v_ego, a_ego, track_data, steering_angle, steering_rate, left_blinker, right_blinker,
                     radar_state, set_speed):

    try:  # removes tracks under 5 mph when above 25 mph to help the model
      track_data = [track for track in track_data if (v_ego >= 11.176 and track[2] + v_ego > 2.2352) or v_ego < 11.176]
    except:
      pass

    tracks_normalized = [[interp_fast(track[0], self.scales['yRel']),
                          interp_fast(track[1], self.scales['dRel']),  # normalize track data
                          interp_fast(track[2], self.scales['vRel'])] for track in track_data]

    tracks_sorted = sorted(tracks_normalized, key=lambda track: track[0])  # sort tracks by yRel
    padded_tracks = pad_tracks(tracks_sorted,
                               self.scales['max_tracks'])  # pad tracks, keeping data in the center, sorted by yRel

    flat_tracks = [i for x in padded_tracks for i in x]  # flatten track data for model
    v_ego_normalized = interp_fast(v_ego, self.scales['v_ego'])
    steering_angle = interp_fast(steering_angle, self.scales['steer_angle'])
    steering_rate = interp_fast(steering_rate, self.scales['steer_rate'])
    left_blinker = int(left_blinker)
    right_blinker = int(right_blinker)
    lead_status, lead_data = self.get_lead(radar_state)
    if lead_status:
      a_lead = interp_fast(lead_data[0], self.scales['a_lead'])
      x_lead = interp_fast(lead_data[1], self.scales['x_lead'])
      v_lead = interp_fast(lead_data[2], self.scales['v_lead'])
    else:
      a_lead, x_lead, v_lead = 0.0, 0.0, 0.0
    # set_speed = interp_fast(set_speed, self.scales['set_speed'])

    final_input = [v_ego_normalized, steering_angle, steering_rate, a_lead, x_lead, v_lead, left_blinker, right_blinker] + flat_tracks

    model_output = float(self.model_wrapper.run_model_live_tracks(final_input))
    model_output = (model_output - 0.52) * 2.2
    model_output = clip(model_output, -1.0, 1.0)
    # the following is for speed model
    #desired_vel = v_ego + interp_fast(model_output, [0, 1], self.scales['v_diff'], ext=True)
    #return desired_vel, model_output
    gas, brake = max(model_output, 0), -min(model_output, 0)
    return gas, brake

  def get_lead(self, radar_state):
    if radar_state is not None:
      lead_1 = radar_state.leadOne
      if lead_1 is not None and lead_1.status:
        a_lead, x_lead, v_lead = lead_1.aLeadK, lead_1.dRel, lead_1.vLead
        return True, [a_lead, x_lead, v_lead]
    return False, None  # second 0 tells model to not care about 0 a_lead instead of interpreting it as 0 accel

  # def df(self, radar_state, v_ego, a_ego, set_speed):
  #   scales = {'v_ego_scale': [0.0, 40.755523681641],
  #             'v_lead_scale': [0.0, 44.508262634277],
  #             'x_lead_scale': [0.125, 146.375]}
  #
  #   #TR = 1.4
  #   #v_lead = set_speed
  #   #x_lead = v_ego * TR
  #   #a_lead = 0.0
  #   #a_rel = 0.0
  #   seq_len = 20 # shape 20, 3
  #   has_lead = False
  #   if radar_state is not None:
  #     lead_1 = radar_state.leadOne
  #     if lead_1 is not None and lead_1.status:
  #       has_lead = True
  #       #x_lead, v_lead, a_lead, a_rel = (lead_1.dRel, lead_1.vLead, lead_1.aLeadK, lead_1.aRel) if lead_1.vLead < set_speed else (x_lead, set_speed, 0.0, 0.0)
  #       self.past_data.append([interp_fast(v_ego, scales['v_ego_scale']), interp_fast(lead_1.vLead, scales['v_lead_scale']), interp_fast(lead_1.dRel, scales['x_lead_scale'])])
  #
  #   #model_output = float(self.model_wrapper.run_model(norm(v_ego, scales['v_ego_scale']), norm(a_ego, scales['a_ego_scale']), norm(v_lead, scales['v_lead_scale']), norm(x_lead, scales['x_lead_scale']), norm(a_lead, scales['a_lead_scale'])))
  #   #return clip((model_output - 0.50) * 2.3, -1.0, 1.0)
  #
  #   while len(self.past_data) > seq_len:
  #     del self.past_data[0]
  #
  #   if len(self.past_data) == seq_len and has_lead:
  #     model_output = self.model_wrapper.run_model_lstm([i for x in self.past_data for i in x])
  #     return clip((model_output - 0.50) * 4.0, -1.0, 1.0)
  #   else:
  #     return None

  def reset(self, v_pid):
    """Reset PID controller and change setpoint"""
    self.pid.reset()
    self.v_pid = v_pid

  def update(self, active, v_ego, a_ego, set_speed, radar_state, brake_pressed, standstill, cruise_standstill, v_cruise, v_target, v_target_future, a_target, CP, track_data, steering_angle,
             steering_rate, left_blinker, right_blinker):
    """Update longitudinal control. This updates the state machine and runs a PID loop"""
    # Actuation limits
    # df_output = self.df_live_tracks(v_ego, a_ego, track_data, steering_angle, steering_rate, left_blinker, right_blinker,
    #                                 radar_state, set_speed)

    # df_output = self.df_controller(v_ego, a_ego, track_data, steering_angle, steering_rate, left_blinker, right_blinker,
    #                                radar_state, set_speed)
    # mpc_v_target = float(v_target)
    # if not travis:
    return self.df_live_tracks(v_ego, a_ego, track_data, steering_angle, steering_rate, left_blinker,
                               right_blinker, radar_state, set_speed)

    # with open("/data/df_d", "a") as f:
    #   f.write("{}\n".format([v_ego, mpc_v_target, v_target, model_out,
    #                          interp_fast(model_out, [0, 1], self.scales['v_diff'], ext=True)]))
    

    gas_max = interp(v_ego, CP.gasMaxBP, CP.gasMaxV)
    brake_max = interp(v_ego, CP.brakeMaxBP, CP.brakeMaxV)

    # Update state machine
    output_gb = self.last_output_gb
    # self.long_control_state = long_control_state_trans(active, self.long_control_state, v_ego,
    #                                                    v_target_future, self.v_pid, output_gb,
    #                                                    brake_pressed, cruise_standstill)

    self.long_control_state = long_control_state_trans(active, self.long_control_state, v_ego,
                                                       v_target, self.v_pid, output_gb,
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
      # prevent_overshoot = not CP.stoppingControl and v_ego < 1.5 and v_target_future < 0.7
      prevent_overshoot = not CP.stoppingControl and v_ego < 1.5 and v_target < 0.7
      deadzone = interp(v_ego_pid, CP.longitudinalTuning.deadzoneBP, CP.longitudinalTuning.deadzoneV)

      # output_gb = self.pid.update(self.v_pid, v_ego_pid, speed=v_ego_pid, deadzone=deadzone, feedforward=a_target, freeze_integrator=prevent_overshoot)
      # output_gb = self.pid.update(self.v_pid, v_ego_pid, speed=v_ego_pid, deadzone=deadzone, feedforward=a_target,
      #                             freeze_integrator=prevent_overshoot)
      output_gb = self.pid.update(self.v_pid, v_ego_pid, speed=v_ego_pid, deadzone=deadzone, freeze_integrator=prevent_overshoot)

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

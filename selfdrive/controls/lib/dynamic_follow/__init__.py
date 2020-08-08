from common.realtime import sec_since_boot
from selfdrive.controls.lib.drive_helpers import MPC_COST_LONG
from common.numpy_fast import interp, clip
from selfdrive.config import Conversions as CV

from selfdrive.controls.lib.dynamic_follow.support import LeadData, CarData, dfData, dfProfiles
travis = False


class DynamicFollow:
  def __init__(self, mpc_id):
    self.mpc_id = mpc_id
    self.df_profiles = dfProfiles()

    # Dynamic follow variables
    self.default_TR = 1.8
    self.v_ego_retention = 2.5
    self.v_rel_retention = 1.75

    self.sng_TR = 1.8  # reacceleration stop and go TR
    self.sng_speed = 18.0 * CV.MPH_TO_MS

    self._setup_changing_variables()

  def _setup_changing_variables(self):
    self.TR = self.default_TR

    self.sng = False
    self.car_data = CarData()
    self.lead_data = LeadData()
    self.df_data = dfData()  # dynamic follow data

    self.last_cost = 0.0

  def update(self, CS, libmpc):
    self._update_car(CS)

    if not self.lead_data.status:  # todo: for example, add an or check for mpc_id==1 here. this is not tested yet so feel free to experiment
      self.TR = self.default_TR
    else:
      self._store_df_data()
      self.TR = self._get_TR()

    self._change_cost(libmpc)
    return self.TR

  def _change_cost(self, libmpc):
    TRs = [0.9, 1.8, 2.7]
    costs = [1.25, 0.2, 0.075]
    cost = interp(self.TR, TRs, costs)

    if self.last_cost != cost:
      libmpc.change_tr(MPC_COST_LONG.TTC, cost, MPC_COST_LONG.ACCELERATION, MPC_COST_LONG.JERK)
      self.last_cost = cost

  def _store_df_data(self):
    cur_time = sec_since_boot()
    # Store custom relative accel over time
    if self.lead_data.status:
      if self.lead_data.new_lead:
        self.df_data.v_rels = []  # reset when new lead
      else:
        self.df_data.v_rels = self._remove_old_entries(self.df_data.v_rels, cur_time, self.v_rel_retention)
      self.df_data.v_rels.append({'v_ego': self.car_data.v_ego, 'v_lead': self.lead_data.v_lead, 'time': cur_time})

    # Store our velocity for better sng
    self.df_data.v_egos = self._remove_old_entries(self.df_data.v_egos, cur_time, self.v_ego_retention)
    self.df_data.v_egos.append({'v_ego': self.car_data.v_ego, 'time': cur_time})

  def _remove_old_entries(self, lst, cur_time, retention):
    return [sample for sample in lst if cur_time - sample['time'] <= retention]

  def _relative_accel_mod(self):
    """
    Returns relative acceleration mod calculated from list of lead and ego velocities over time (longer than 1s)
    If min_consider_time has not been reached, uses lead accel and ego accel from openpilot (kalman filtered)
    """
    a_ego = self.car_data.a_ego
    a_lead = self.lead_data.a_lead
    min_consider_time = 0.75  # minimum amount of time required to consider calculation
    if len(self.df_data.v_rels) > 0:  # if not empty
      elapsed_time = self.df_data.v_rels[-1]['time'] - self.df_data.v_rels[0]['time']
      if elapsed_time > min_consider_time:
        a_ego = (self.df_data.v_rels[-1]['v_ego'] - self.df_data.v_rels[0]['v_ego']) / elapsed_time
        a_lead = (self.df_data.v_rels[-1]['v_lead'] - self.df_data.v_rels[0]['v_lead']) / elapsed_time

    mods_x = [0, -.75, -1.5]
    mods_y = [1.5, 1.25, 1]
    if a_lead < 0:  # more weight to slight lead decel
      a_lead *= interp(a_lead, mods_x, mods_y)

    rel_x = [-2.6822, -1.7882, -0.8941, -0.447, -0.2235, 0.0, 0.2235, 0.447, 0.8941, 1.7882, 2.6822]
    mod_y = [0.3245 * 1.25, 0.277 * 1.2, 0.11075 * 1.15, 0.08106 * 1.075, 0.06325 * 1.05, 0.0, -0.09, -0.09375, -0.125, -0.3, -0.35]
    return interp(a_lead - a_ego, rel_x, mod_y)

  def _get_TR(self):
    x_vel = [0.0, 1.8627, 3.7253, 5.588, 7.4507, 9.3133, 11.5598, 13.645, 22.352, 31.2928, 33.528, 35.7632, 40.2336]  # velocities
    profile_mod_x = [5 * CV.MPH_TO_MS, 30 * CV.MPH_TO_MS, 55 * CV.MPH_TO_MS, 80 * CV.MPH_TO_MS]  # profile mod speeds

    df_profile = self.df_profiles.traffic  # todo: change this to change profiles

    if df_profile == self.df_profiles.roadtrip:
      y_dist = [1.5486, 1.556, 1.5655, 1.5773, 1.5964, 1.6246, 1.6715, 1.7057, 1.7859, 1.8542, 1.8697, 1.8833, 1.8961]  # TRs
      profile_mod_pos = [0.5, 0.35, 0.1, 0.03]
      profile_mod_neg = [1.3, 1.4, 1.8, 2.0]
    elif df_profile == self.df_profiles.traffic:  # for in congested traffic
      x_vel = [0.0, 1.892, 3.7432, 5.8632, 8.0727, 10.7301, 14.343, 17.6275, 22.4049, 28.6752, 34.8858, 40.35]
      y_dist = [1.3781, 1.3791, 1.3457, 1.3134, 1.3145, 1.318, 1.3485, 1.257, 1.144, 0.979, 0.9461, 0.9156]
      profile_mod_pos = [1.075, 1.55, 2.6, 3.75]
      profile_mod_neg = [0.95, .275, 0.1, 0.05]
    elif df_profile == self.df_profiles.relaxed:  # default to relaxed/stock
      y_dist = [1.385, 1.394, 1.406, 1.421, 1.444, 1.474, 1.521, 1.544, 1.568, 1.588, 1.599, 1.613, 1.634]
      profile_mod_pos = [1.0, 0.955, 0.898, 0.905]
      profile_mod_neg = [1.0, 1.0825, 1.1877, 1.174]
    else:
      raise Exception('Unknown profile type: {}'.format(df_profile))

    # Profile modifications - Designed so that each profile reacts similarly to changing lead dynamics
    profile_mod_pos = interp(self.car_data.v_ego, profile_mod_x, profile_mod_pos)
    profile_mod_neg = interp(self.car_data.v_ego, profile_mod_x, profile_mod_neg)

    if self.car_data.v_ego > self.sng_speed:  # keep sng distance until we're above sng speed again
      self.sng = False

    if (self.car_data.v_ego >= self.sng_speed or self.df_data.v_egos[0]['v_ego'] >= self.car_data.v_ego) and not self.sng:
      # if above 15 mph OR we're decelerating to a stop, keep shorter TR. when we reaccelerate, use sng_TR and slowly decrease
      TR = interp(self.car_data.v_ego, x_vel, y_dist)
    else:  # this allows us to get closer to the lead car when stopping, while being able to have smooth stop and go when reaccelerating
      self.sng = True
      x = [self.sng_speed * 0.7, self.sng_speed]  # decrease TR between 12.6 and 18 mph from 1.8s to defined TR above at 18mph while accelerating
      y = [self.sng_TR, interp(self.sng_speed, x_vel, y_dist)]
      TR = interp(self.car_data.v_ego, x, y)

    TR_mods = []
    # Dynamic follow modifications (the secret sauce)
    x = [-26.8224, -20.0288, -15.6871, -11.1965, -7.8645, -4.9472, -3.0541, -2.2244, -1.5045, -0.7908, -0.3196, 0.0, 0.5588, 1.3682, 1.898, 2.7316, 4.4704]  # relative velocity values
    y = [.76, 0.62323, 0.49488, 0.40656, 0.32227, 0.23914*1.025, 0.12269*1.05, 0.10483*1.075, 0.08074*1.15, 0.04886*1.25, 0.0072*1.075, 0.0, -0.05648, -0.0792, -0.15675, -0.23289, -0.315]  # modification values
    TR_mods.append(interp(self.lead_data.v_lead - self.car_data.v_ego, x, y))

    x = [-4.4795, -2.8122, -1.5727, -1.1129, -0.6611, -0.2692, 0.0, 0.1466, 0.5144, 0.6903, 0.9302]  # lead acceleration values
    y = [0.24, 0.16, 0.092, 0.0515, 0.0305, 0.022, 0.0, -0.0153, -0.042, -0.053, -0.059]  # modification values
    TR_mods.append(interp(self.lead_data.a_lead, x, y))

    # deadzone = 7.5 * CV.MPH_TO_MS
    # if self.lead_data.v_lead - deadzone > self.car_data.v_ego:
    #   TR_mods.append(self._relative_accel_mod())  # todo: not sure if this is needed, causes harsh braking without pedal

    x = [self.sng_speed, self.sng_speed / 5.0]  # as we approach 0, apply x% more distance
    y = [1.0, 1.05]
    profile_mod_pos *= interp(self.car_data.v_ego, x, y)  # but only for currently positive mods

    TR_mod = sum([mod * profile_mod_neg if mod < 0 else mod * profile_mod_pos for mod in TR_mods])  # alter TR modification according to profile
    TR += TR_mod

    if (self.car_data.left_blinker or self.car_data.right_blinker) and df_profile != self.df_profiles.traffic:
      x = [8.9408, 22.352, 31.2928]  # 20, 50, 70 mph
      y = [1.0, .75, .65]
      TR *= interp(self.car_data.v_ego, x, y)  # reduce TR when changing lanes

    min_TR = 0.9
    return float(clip(TR, min_TR, 2.7))

  def update_lead(self, v_lead=None, a_lead=None, x_lead=None, status=False, new_lead=False):
    self.lead_data.v_lead = v_lead
    self.lead_data.a_lead = a_lead
    self.lead_data.x_lead = x_lead

    self.lead_data.status = status
    self.lead_data.new_lead = new_lead

  def _update_car(self, CS):
    self.car_data.v_ego = CS.vEgo
    self.car_data.a_ego = CS.aEgo

    self.car_data.left_blinker = CS.leftBlinker
    self.car_data.right_blinker = CS.rightBlinker
    self.car_data.cruise_enabled = CS.cruiseState.enabled

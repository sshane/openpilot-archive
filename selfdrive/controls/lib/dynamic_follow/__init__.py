import math
import numpy as np
import cereal.messaging as messaging
from common.realtime import sec_since_boot
from selfdrive.controls.lib.drive_helpers import MPC_COST_LONG
from common.op_params import opParams
from common.numpy_fast import interp, clip
from selfdrive.config import Conversions as CV
from cereal.messaging import SubMaster

from selfdrive.controls.lib.dynamic_follow.auto_df import predict
from selfdrive.controls.lib.dynamic_follow.df_manager import dfManager
from selfdrive.controls.lib.dynamic_follow.support import LeadData, CarData, dfData, dfProfiles
from common.data_collector import DataCollector
travis = False


class DynamicFollow:
  def __init__(self, mpc_id):
    self.mpc_id = mpc_id
    self.op_params = opParams()
    self.df_profiles = dfProfiles()
    self.df_manager = dfManager(self.op_params)

    if not travis and mpc_id == 1:
      self.pm = messaging.PubMaster(['dynamicFollowData'])
    else:
      self.pm = None

    # Model variables
    mpc_rate = 1 / 20.
    self.model_scales = {'v_ego': [-0.06112159043550491, 37.96522521972656], 'v_lead': [0.0, 35.27671432495117], 'x_lead': [2.4600000381469727, 139.52000427246094]}
    self.predict_rate = 1 / 4.
    self.skip_every = round(0.2 / mpc_rate)
    self.model_input_len = round(35 / mpc_rate)  # int: model input time

    # Dynamic follow variables
    self.default_TR = 1.8
    self.TR = 1.8
    # self.v_lead_retention = 2.0  # keep only last x seconds
    self.v_ego_retention = 2.5
    self.v_rel_retention = 1.5

    self._setup_collector()
    self._setup_changing_variables()

  def _setup_collector(self):
    self.sm = SubMaster(['liveTracks'])
    self.data_collector = DataCollector(file_path='/data/df_data', keys=['v_ego', 'a_lead', 'v_lead', 'x_lead', 'live_tracks', 'profile', 'time'])

  def _setup_changing_variables(self):
    self.TR_mod = 0
    self.TR = self.default_TR
    self.user_profile = self.df_profiles.relaxed  # just a starting point
    self.model_profile = self.df_profiles.relaxed

    self.sng = False
    self.car_data = CarData()
    self.lead_data = LeadData()
    self.df_data = dfData()  # dynamic follow data

    self.last_cost = 0.0
    self.last_predict_time = 0.0
    self.auto_df_model_data = []

  def update(self, CS, libmpc):
    self._get_live_params()
    self._update_car(CS)
    self._get_profiles()

    if self.mpc_id == 1:
      self._gather_data()

    if not self.lead_data.status:
      self.TR = self.default_TR
    else:
      self._store_df_data()
      self.TR = self._get_TR()

    if not travis:
      self._change_cost(libmpc)
      self._send_cur_state()

    return self.TR

  def _get_profiles(self):
    """This receives profile change updates from dfManager and runs the auto-df prediction if auto mode"""
    df_out = self.df_manager.update()
    self.user_profile = df_out.user_profile
    if df_out.is_auto:  # todo: find some way to share prediction between the two mpcs to reduce processing overhead
      self._get_pred()  # sets self.model_profile, all other checks are inside function

  def _gather_data(self):
    self.sm.update(0)
    live_tracks = [[i.dRel, i.vRel, i.aRel, i.yRel] for i in self.sm['liveTracks']]
    if self.car_data.cruise_enabled:
      self.data_collector.update([self.car_data.v_ego,
                                  self.lead_data.a_lead,
                                  self.lead_data.v_lead,
                                  self.lead_data.x_lead,
                                  live_tracks,
                                  self.user_profile,
                                  sec_since_boot()])

  def _norm(self, x, name):
    self.x = x
    return np.interp(x, self.model_scales[name], [0, 1])

  def _send_cur_state(self):
    if self.mpc_id == 1 and self.pm is not None:
      dat = messaging.new_message()
      dat.init('dynamicFollowData')
      dat.dynamicFollowData.mpcTR = 1.8  # self.TR  # FIX THIS! sometimes nonetype
      dat.dynamicFollowData.profilePred = self.model_profile
      self.pm.send('dynamicFollowData', dat)

  def _change_cost(self, libmpc):
    TRs = [0.9, 1.8, 2.7]
    costs = [1.0, 0.115, 0.05]
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

    # Store data for auto-df model
    self.auto_df_model_data.append([self._norm(self.car_data.v_ego, 'v_ego'),
                                    self._norm(self.lead_data.v_lead, 'v_lead'),
                                    self._norm(self.lead_data.x_lead, 'x_lead')])
    while len(self.auto_df_model_data) > self.model_input_len:
      del self.auto_df_model_data[0]

  def _get_pred(self):
    cur_time = sec_since_boot()
    if self.car_data.cruise_enabled and self.lead_data.status:
      if cur_time - self.last_predict_time > self.predict_rate:
        if len(self.auto_df_model_data) == self.model_input_len:
          pred = predict(np.array(self.auto_df_model_data[::self.skip_every], dtype=np.float32).flatten())
          self.last_predict_time = cur_time
          self.model_profile = int(np.argmax(pred))

  def _remove_old_entries(self, lst, cur_time, retention):
    return [sample for sample in lst if cur_time - sample['time'] <= retention]

  def _calculate_relative_accel_new(self):
    #   """
    #   Moving window returning the following: (final relative velocity - initial relative velocity) / dT with a few extra mods
    #   Output properties:
    #     When the lead is starting to decelerate, and our car remains the same speed, the output decreases (and vice versa)
    #     However when our car finally starts to decelerate at the same rate as the lead car, the output will move to near 0
    #       >>> a = [(15 - 18), (14 - 17)]
    #       >>> (a[-1] - a[0]) / 1
    #       > 0.0
    #   """
    min_consider_time = 0.5  # minimum amount of time required to consider calculation
    if len(self.df_data.v_rels) > 0:  # if not empty
      elapsed_time = self.df_data.v_rels[-1]['time'] - self.df_data.v_rels[0]['time']
      if elapsed_time > min_consider_time:
        x = [-2.6822, -1.7882, -0.8941, -0.447, -0.2235, 0.0, 0.2235, 0.447, 0.8941, 1.7882, 2.6822]
        y = [0.3245, 0.277, 0.11075, 0.08106, 0.06325, 0.0, -0.09, -0.09375, -0.125, -0.3, -0.35]

        v_lead_start = self.df_data.v_rels[0]['v_lead']  # setup common variables
        v_ego_start = self.df_data.v_rels[0]['v_ego']
        v_lead_end = self.df_data.v_rels[-1]['v_lead']
        v_ego_end = self.df_data.v_rels[-1]['v_ego']

        v_ego_change = v_ego_end - v_ego_start
        v_lead_change = v_lead_end - v_lead_start

        if v_lead_change - v_ego_change == 0 or v_lead_change + v_ego_change == 0:
          return None

        initial_v_rel = v_lead_start - v_ego_start
        cur_v_rel = v_lead_end - v_ego_end
        delta_v_rel = (cur_v_rel - initial_v_rel) / elapsed_time

        neg_pos = False
        if v_ego_change == 0 or v_lead_change == 0:  # FIXME: this all is a mess, but works. need to simplify
          lead_factor = v_lead_change / (v_lead_change - v_ego_change)

        elif (v_ego_change < 0) != (v_lead_change < 0):  # one is negative and one is positive, or ^ = XOR
          lead_factor = v_lead_change / (v_lead_change - v_ego_change)
          if v_ego_change > 0 > v_lead_change:
            delta_v_rel = -delta_v_rel  # switch when appropriate
          neg_pos = True

        elif v_ego_change * v_lead_change > 0:  # both are negative or both are positive
          lead_factor = v_lead_change / (v_lead_change + v_ego_change)
          if v_ego_change > 0 and v_lead_change > 0:  # both are positive
            if v_ego_change < v_lead_change:
              delta_v_rel = -delta_v_rel  # switch when appropriate
          elif v_ego_change > v_lead_change:  # both are negative and v_ego_change > v_lead_change
            delta_v_rel = -delta_v_rel

        else:
          raise Exception('Uncovered case! Should be impossible to be be here')

        if not neg_pos:  # negative and positive require different mod code to be correct
          rel_vel_mod = (-delta_v_rel * abs(lead_factor)) + (delta_v_rel * (1 - abs(lead_factor)))
        else:
          rel_vel_mod = math.copysign(delta_v_rel, v_lead_change - v_ego_change) * lead_factor

        calc_mod = np.interp(rel_vel_mod, x, y)
        if v_lead_end > v_ego_end and calc_mod >= 0:
          # if we're accelerating quicker than lead but lead is still faster, reduce mod
          # todo: could remove this since we restrict this mod where called
          x = np.array([0, 2, 4, 8]) * CV.MPH_TO_MS
          y = [1.0, -0.25, -0.65, -0.95]
          v_rel_mod = np.interp(v_lead_end - v_ego_end, x, y)
          calc_mod *= v_rel_mod
        return calc_mod
    return None

  def global_profile_mod(self, TR, profile_mod_pos, profile_mod_neg):
    if self.global_df_mod is not None:  # only apply when not in sng
      TR *= self.global_df_mod
      profile_mod_pos *= (1 - self.global_df_mod) + 1
      profile_mod_neg *= self.global_df_mod
    return TR, profile_mod_pos, profile_mod_neg

  def _get_TR(self):
    # profile_mod_x = [2.2352, 13.4112, 24.5872, 35.7632]  # profile mod speeds, mph: [5., 30., 55., 80.]


    x_vel = [0.0, 1.892, 3.7432, 5.8632, 8.0727, 10.7301, 14.343, 17.6275, 22.4049, 28.6752, 34.8858, 40.35]
    y_dist = [1.3781, 1.3791, 1.3457, 1.3134, 1.3145, 1.318, 1.3485, 1.257, 1.144, 0.979, 0.9461, 0.9156]
    # profile_mod_pos = [1.05, 1.55, 2.6, 3.75]
    # profile_mod_neg = [0.84, .275, 0.1, 0.05]


    # Profile modifications - Designed so that each profile reacts similarly to changing lead dynamics
    # profile_mod_pos = interp(self.car_data.v_ego, profile_mod_x, profile_mod_pos)
    # profile_mod_neg = interp(self.car_data.v_ego, profile_mod_x, profile_mod_neg)

    TR = interp(self.car_data.v_ego, x_vel, y_dist)

    TR_mods = []
    # Dynamic follow modifications (the secret sauce)
    x = [-26.8224, -20.0288, -15.6871, -11.1965, -7.8645, -4.9472, -3.0541, -2.2244, -1.5045, -0.7908, -0.3196, 0.0, 0.5588, 1.3682, 1.898, 2.7316, 4.4704]  # relative velocity values
    y = [.76, 0.62323, 0.49488, 0.40656, 0.32227, 0.23914, 0.12269, 0.10483, 0.08074, 0.04886, 0.0072, 0.0, -0.05648, -0.0792, -0.15675, -0.23289, -0.315]  # modification values
    TR_mod = interp(self.lead_data.v_lead - self.car_data.v_ego, x, y) * (1 / 10)
    self.TR_mod += TR_mod
    TR += self.TR_mod

    return clip(TR, 0.9, 2.7)

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

  def _get_live_params(self):
    self.global_df_mod = self.op_params.get('global_df_mod', None)
    if self.global_df_mod is not None:
      self.global_df_mod = np.clip(self.global_df_mod, 0.7, 1.1)

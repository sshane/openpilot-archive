from common.numpy_fast import interp
from common.kalman.simple_kalman import KF1D
from selfdrive.can.parser import CANParser, CANDefine
from selfdrive.config import Conversions as CV
from selfdrive.car.honda.values import CAR, DBC, STEER_THRESHOLD, SPEED_FACTOR, HONDA_BOSCH
from selfdrive.car.modules.UIBT_module import UIButtons,UIButton
from selfdrive.car.modules.UIEV_module import UIEvents
import numpy as np
import os
import subprocess
import sys

def parse_gear_shifter(gear, vals):

  val_to_capnp = {'P': 'park', 'R': 'reverse', 'N': 'neutral',
                  'D': 'drive', 'S': 'sport', 'L': 'low'}
  try:
    return val_to_capnp[vals[gear]]
  except KeyError:
    return "unknown"


def calc_cruise_offset(offset, speed):
  # euristic formula so that speed is controlled to ~ 0.3m/s below pid_speed
  # constraints to solve for _K0, _K1, _K2 are:
  # - speed = 0m/s, out = -0.3
  # - speed = 34m/s, offset = 20, out = -0.25
  # - speed = 34m/s, offset = -2.5, out = -1.8
  _K0 = -0.3
  _K1 = -0.01879
  _K2 = 0.01013
  return min(_K0 + _K1 * speed + _K2 * speed * offset, 0.)


def get_can_signals(CP):
# this function generates lists for signal, messages and initial values
  signals = [
      ("XMISSION_SPEED", "ENGINE_DATA", 0),
      ("WHEEL_SPEED_FL", "WHEEL_SPEEDS", 0),
      ("WHEEL_SPEED_FR", "WHEEL_SPEEDS", 0),
      ("WHEEL_SPEED_RL", "WHEEL_SPEEDS", 0),
      ("WHEEL_SPEED_RR", "WHEEL_SPEEDS", 0),
      ("STEER_ANGLE", "STEERING_SENSORS", 0),
      ("STEER_ANGLE_RATE", "STEERING_SENSORS", 0),
      ("STEER_TORQUE_SENSOR", "STEER_STATUS", 0),
      ("LEFT_BLINKER", "SCM_FEEDBACK", 0),
      ("RIGHT_BLINKER", "SCM_FEEDBACK", 0),
      ("GEAR", "GEARBOX", 0),
      ("SEATBELT_DRIVER_LAMP", "SEATBELT_STATUS", 1),
      ("SEATBELT_DRIVER_LATCHED", "SEATBELT_STATUS", 0),
      ("BRAKE_PRESSED", "POWERTRAIN_DATA", 0),
      ("BRAKE_SWITCH", "POWERTRAIN_DATA", 0),
      ("CRUISE_BUTTONS", "SCM_BUTTONS", 0),
      ("ESP_DISABLED", "VSA_STATUS", 1),
      ("HUD_LEAD", "ACC_HUD", 0),
      ("USER_BRAKE", "VSA_STATUS", 0),
      ("STEER_STATUS", "STEER_STATUS", 5),
      ("GEAR_SHIFTER", "GEARBOX", 0),
      ("PEDAL_GAS", "POWERTRAIN_DATA", 0),
      ("CRUISE_SETTING", "SCM_BUTTONS", 0),
      ("ACC_STATUS", "POWERTRAIN_DATA", 0),
  ]

  checks = [
      ("ENGINE_DATA", 100),
      ("WHEEL_SPEEDS", 50),
      ("STEERING_SENSORS", 100),
      ("SCM_FEEDBACK", 10),
      ("GEARBOX", 100),
      ("SEATBELT_STATUS", 10),
      ("CRUISE", 10),
      ("POWERTRAIN_DATA", 100),
      ("VSA_STATUS", 50),
      ("SCM_BUTTONS", 25),
  ]
  
  if CP.carFingerprint == CAR.CRV_HYBRID:
    checks += [
      ("GEARBOX", 50),
    ]
    
  if CP.radarOffCan:
    # Civic is only bosch to use the same brake message as other hondas.
    if CP.carFingerprint not in (CAR.ACCORDH, CAR.CIVIC_BOSCH, CAR.CRV_HYBRID):
      signals += [("BRAKE_PRESSED", "BRAKE_MODULE", 0)]
      checks += [("BRAKE_MODULE", 50)]
    signals += [("CAR_GAS", "GAS_PEDAL_2", 0),
                ("MAIN_ON", "SCM_FEEDBACK", 0),
                ("EPB_STATE", "EPB_STATUS", 0),
                ("BRAKE_HOLD_ACTIVE", "VSA_STATUS", 0),
                ("CRUISE_SPEED", "ACC_HUD", 0)]
    checks += [("GAS_PEDAL_2", 100)]
  else:
    # Nidec signals.
    signals += [("BRAKE_ERROR_1", "STANDSTILL", 1),
                ("BRAKE_ERROR_2", "STANDSTILL", 1),
                ("CRUISE_SPEED_PCM", "CRUISE", 0),
                ("CRUISE_SPEED_OFFSET", "CRUISE_PARAMS", 0)]
    checks += [("CRUISE_PARAMS", 50),
               ("STANDSTILL", 50)]

  if CP.carFingerprint in (CAR.ACCORD, CAR.ACCORD_15, CAR.ACCORDH, CAR.CIVIC_BOSCH, CAR.CRV_HYBRID):
    signals += [("DRIVERS_DOOR_OPEN", "SCM_FEEDBACK", 1)]
  else:
    signals += [("DOOR_OPEN_FL", "DOORS_STATUS", 1),
                ("DOOR_OPEN_FR", "DOORS_STATUS", 1),
                ("DOOR_OPEN_RL", "DOORS_STATUS", 1),
                ("DOOR_OPEN_RR", "DOORS_STATUS", 1),
                ("WHEELS_MOVING", "STANDSTILL", 1)]
    checks += [("DOORS_STATUS", 3)]

  if CP.carFingerprint == CAR.CIVIC:
    signals += [("CAR_GAS", "GAS_PEDAL_2", 0),
                ("MAIN_ON", "SCM_FEEDBACK", 0),
                ("EPB_STATE", "EPB_STATUS", 0),
                ("BRAKE_HOLD_ACTIVE", "VSA_STATUS", 0)]
  elif CP.carFingerprint == CAR.ACURA_ILX:
    signals += [("CAR_GAS", "GAS_PEDAL_2", 0),
                ("MAIN_ON", "SCM_BUTTONS", 0)]
  elif CP.carFingerprint in (CAR.CRV, CAR.ACURA_RDX, CAR.PILOT_2019, CAR.RIDGELINE):
    signals += [("MAIN_ON", "SCM_BUTTONS", 0)]
  elif CP.carFingerprint == CAR.ODYSSEY:
    signals += [("MAIN_ON", "SCM_FEEDBACK", 0),
                ("EPB_STATE", "EPB_STATUS", 0),
                ("BRAKE_HOLD_ACTIVE", "VSA_STATUS", 0)]
    checks += [("EPB_STATUS", 50)]
  elif CP.carFingerprint == CAR.PILOT:
    signals += [("MAIN_ON", "SCM_BUTTONS", 0),
                ("CAR_GAS", "GAS_PEDAL_2", 0)]

  # add gas interceptor reading if we are using it
  if CP.enableGasInterceptor:
    signals.append(("INTERCEPTOR_GAS", "GAS_SENSOR", 0))
    checks.append(("GAS_SENSOR", 50))

  return signals, checks


def get_can_parser(CP):
  signals, checks = get_can_signals(CP)
  return CANParser(DBC[CP.carFingerprint]['pt'], signals, checks, 0)

def get_cam_can_parser(CP):
  signals = []

  # all hondas except CRV and RDX use 0xe4 for steering
  checks = [(0xe4, 100)]
  if CP.carFingerprint in [CAR.CRV, CAR.ACURA_RDX]:
    checks = [(0x194, 100)]

  cam_bus = 1 if CP.carFingerprint in HONDA_BOSCH else 2

  return CANParser(DBC[CP.carFingerprint]['pt'], signals, checks, cam_bus)

class CarState(object):
  def __init__(self, CP):
    self.Angle = [0, 5, 10, 15,20,25,30,35,60,100,180,270,500]
    self.Angle_Speed = [255,160,100,80,70,60,55,50,40,30,20,10,5]
    self.blind_spot_on = bool(0)
    #labels for ALCA modes
    self.alcaLabels = ["MadMax","Normal","Wifey"]
    self.visionLabels = ["normal","wiggly"]
    self.visionMode = 0
    self.trLabels = ["0.9","1.8","2.7","dyn"]
    self.alcaMode = 0
    self.trMode = 1
    #if (CP.carFingerprint == CAR.MODELS):
    # ALCA PARAMS
    # max REAL delta angle for correction vs actuator
    self.CL_MAX_ANGLE_DELTA_BP = [10., 32., 44.]
    self.CL_MAX_ANGLE_DELTA = [2.0, 1., 0.5]
    # adjustment factor for merging steer angle to actuator; should be over 4; the higher the smoother
    self.CL_ADJUST_FACTOR_BP = [10., 44.]
    self.CL_ADJUST_FACTOR = [16. , 8.]
    # reenrey angle when to let go
    self.CL_REENTRY_ANGLE_BP = [10., 44.]
    self.CL_REENTRY_ANGLE = [5. , 5.]
    # a jump in angle above the CL_LANE_DETECT_FACTOR means we crossed the line
    self.CL_LANE_DETECT_BP = [10., 44.]
    self.CL_LANE_DETECT_FACTOR = [1.5, 2.5]
    self.CL_LANE_PASS_BP = [10., 20., 44.]
    self.CL_LANE_PASS_TIME = [40.,10., 4.] 
    # change lane delta angles and other params
    self.CL_MAXD_BP = [10., 32., 44.]
    self.CL_MAXD_A = [.358, 0.084, 0.040] #delta angle based on speed; needs fine tune, based on Tesla steer ratio of 16.75
    self.CL_MIN_V = 8.9 # do not turn if speed less than x m/2; 20 mph = 8.9 m/s
    # do not turn if actuator wants more than x deg for going straight; this should be interp based on speed
    self.CL_MAX_A_BP = [10., 44.]
    self.CL_MAX_A = [10., 10.] 
    # define limits for angle change every 0.1 s
    # we need to force correction above 10 deg but less than 20
    # anything more means we are going to steep or not enough in a turn
    self.CL_MAX_ACTUATOR_DELTA = 2.

    self.CL_MIN_ACTUATOR_DELTA = 0. 
    self.CL_CORRECTION_FACTOR = [1.,1.1,1.2]
    self.CL_CORRECTION_FACTOR_BP = [10., 32., 44.]
    #duration after we cross the line until we release is a factor of speed
    self.CL_TIMEA_BP = [10., 32., 44.]
    self.CL_TIMEA_T = [0.7 ,0.30, 0.30]
    #duration to wait (in seconds) with blinkers on before starting to turn
    self.CL_WAIT_BEFORE_START = 1
    #END OF ALCA PARAMS
    
    self.read_distance_lines_prev = 3
    
    self.CP = CP
    self.can_define = CANDefine(DBC[CP.carFingerprint]['pt'])
    self.shifter_values = self.can_define.dv["GEARBOX"]["GEAR_SHIFTER"]

    self.user_gas, self.user_gas_pressed = 0., 0
    self.brake_switch_prev = 0
    self.brake_switch_ts = 0

    self.cruise_buttons = 0
    self.cruise_setting = 0
    self.v_cruise_pcm_prev = 0
    self.blinker_on = 0

    self.left_blinker_on = 0
    self.right_blinker_on = 0

    self.stopped = 0
    
    #BB UIEvents
    self.UE = UIEvents(self)
    
    #BB variable for custom buttons
    self.cstm_btns = UIButtons(self,"Honda","honda")
    
    #BB pid holder for ALCA
    self.pid = None
    
    #BB custom message counter
    self.custom_alert_counter = -1 #set to 100 for 1 second display; carcontroller will take down to zero
    
    #BB visiond last type
    self.last_visiond = self.cstm_btns.btns[2].btn_label2
    
    # vEgo kalman filter
    dt = 0.01
    # Q = np.matrix([[10.0, 0.0], [0.0, 100.0]])
    # R = 1e3
    self.v_ego_kf = KF1D(x0=[[0.0], [0.0]],
                         A=[[1.0, dt], [0.0, 1.0]],
                         C=[[1.0, 0.0]],
                         K=[[0.12287673], [0.29666309]])
    self.v_ego = 0.0
    #BB init ui buttons
  def init_ui_buttons(self):
    btns = []
    btns.append(UIButton("alca", "ALC", 1, self.alcaLabels[self.alcaMode], 0))
    btns.append(UIButton("lka","LKA",1,"",1))
    btns.append(UIButton("vision","VIS",0,self.visionLabels[self.visionMode],2))
    btns.append(UIButton("sound","SND",0,"",3))
    btns.append(UIButton("tr","TR",0,self.trLabels[self.trMode],4))
    btns.append(UIButton("gas","Gas",1,"",5))
    return btns

  #BB update ui buttons
  def update_ui_buttons(self,id,btn_status):
    if self.cstm_btns.btns[id].btn_status > 0:
      if (id == 0) and (btn_status == 0) and self.cstm_btns.btns[id].btn_name=="alca":
          if self.cstm_btns.btns[id].btn_label2 == self.alcaLabels[self.alcaMode]:
            self.alcaMode = (self.alcaMode + 1 ) % 3
          else:
            self.alcaMode = 0
          self.cstm_btns.btns[id].btn_label2 = self.alcaLabels[self.alcaMode]
          self.cstm_btns.hasChanges = True
          
      elif (id == 2) and (btn_status == 0) and self.cstm_btns.btns[id].btn_name=="vision":
          if self.cstm_btns.btns[id].btn_label2 == self.visionLabels[self.visionMode]:
            self.visionMode = (self.visionMode + 1) % 2
          else:
            self.visionMode = 0
          self.cstm_btns.btns[id].btn_label2 = self.visionLabels[self.visionMode]
          self.cstm_btns.hasChanges = True
          self.last_visiond = self.cstm_btns.btns[id].btn_label2
          args = ["/data/openpilot/selfdrive/car/modules/ch_visiond.sh", self.cstm_btns.btns[id].btn_label2]
          subprocess.Popen(args, shell = False, stdin=None, stdout=None, stderr=None, env = dict(os.environ), close_fds=True)
        
      elif (id == 4) and (btn_status == 0) and self.cstm_btns.btns[id].btn_name=="tr":
          if self.cstm_btns.btns[id].btn_label2 == self.trLabels[self.trMode]:
            self.trMode = (self.trMode + 1 ) % 3
          else:
            self.trMode = 0
          self.cstm_btns.btns[id].btn_label2 = self.trLabels[self.trMode]
          self.cstm_btns.hasChanges = True

      else:
        self.cstm_btns.btns[id].btn_status = btn_status * self.cstm_btns.btns[id].btn_status
    else:
        self.cstm_btns.btns[id].btn_status = btn_status

  def update(self, cp, cp_cam):

    # copy can_valid on buses 0 and 2
    self.can_valid = cp.can_valid
    self.cam_can_valid = cp_cam.can_valid

    # car params
    v_weight_v = [0., 1.]  # don't trust smooth speed at low values to avoid premature zero snapping
    v_weight_bp = [1., 6.]   # smooth blending, below ~0.6m/s the smooth speed snaps to zero

    # update prevs, update must run once per loop
    self.prev_cruise_buttons = self.cruise_buttons
    self.prev_blinker_on = self.blinker_on

    self.prev_left_blinker_on = self.left_blinker_on
    self.prev_right_blinker_on = self.right_blinker_on

    # ******************* parse out can *******************

    if self.CP.carFingerprint in (CAR.ACCORD, CAR.ACCORD_15, CAR.ACCORDH, CAR.CIVIC_BOSCH, CAR.CRV_HYBRID): # TODO: find wheels moving bit in dbc
      self.standstill = cp.vl["ENGINE_DATA"]['XMISSION_SPEED'] < 0.1
      self.door_all_closed = not cp.vl["SCM_FEEDBACK"]['DRIVERS_DOOR_OPEN']
    else:
      self.standstill = not cp.vl["STANDSTILL"]['WHEELS_MOVING']
      self.door_all_closed = not any([cp.vl["DOORS_STATUS"]['DOOR_OPEN_FL'], cp.vl["DOORS_STATUS"]['DOOR_OPEN_FR'],
                                      cp.vl["DOORS_STATUS"]['DOOR_OPEN_RL'], cp.vl["DOORS_STATUS"]['DOOR_OPEN_RR']])
    self.seatbelt = not cp.vl["SEATBELT_STATUS"]['SEATBELT_DRIVER_LAMP'] and cp.vl["SEATBELT_STATUS"]['SEATBELT_DRIVER_LATCHED']

    # 2 = temporary; 3 = TBD; 4 = temporary, hit a bump; 5 = (permanent); 6 = temporary; 7 = (permanent)
    # TODO: Use values from DBC to parse this field
    self.steer_error = cp.vl["STEER_STATUS"]['STEER_STATUS'] not in [0, 2, 3, 4, 6]
    self.steer_not_allowed = cp.vl["STEER_STATUS"]['STEER_STATUS'] != 0
    self.steer_warning = cp.vl["STEER_STATUS"]['STEER_STATUS'] not in [0, 3]   # 3 is low speed lockout, not worth a warning
    if self.CP.radarOffCan:
      self.brake_error = 0
    else:
      self.brake_error = cp.vl["STANDSTILL"]['BRAKE_ERROR_1'] or cp.vl["STANDSTILL"]['BRAKE_ERROR_2']
    self.esp_disabled = cp.vl["VSA_STATUS"]['ESP_DISABLED']

    # calc best v_ego estimate, by averaging two opposite corners
    speed_factor = SPEED_FACTOR[self.CP.carFingerprint]
    self.v_wheel_fl = cp.vl["WHEEL_SPEEDS"]['WHEEL_SPEED_FL'] * CV.KPH_TO_MS * speed_factor
    self.v_wheel_fr = cp.vl["WHEEL_SPEEDS"]['WHEEL_SPEED_FR'] * CV.KPH_TO_MS * speed_factor
    self.v_wheel_rl = cp.vl["WHEEL_SPEEDS"]['WHEEL_SPEED_RL'] * CV.KPH_TO_MS * speed_factor
    self.v_wheel_rr = cp.vl["WHEEL_SPEEDS"]['WHEEL_SPEED_RR'] * CV.KPH_TO_MS * speed_factor
    self.v_wheel = (self.v_wheel_fl+self.v_wheel_fr+self.v_wheel_rl+self.v_wheel_rr)/4.

    # blend in transmission speed at low speed, since it has more low speed accuracy
    self.v_weight = interp(self.v_wheel, v_weight_bp, v_weight_v)
    speed = (1. - self.v_weight) * cp.vl["ENGINE_DATA"]['XMISSION_SPEED'] * CV.KPH_TO_MS * speed_factor + \
      self.v_weight * self.v_wheel

    if abs(speed - self.v_ego) > 2.0:  # Prevent large accelerations when car starts at non zero speed
      self.v_ego_x = [[speed], [0.0]]

    self.v_ego_raw = speed
    v_ego_x = self.v_ego_kf.update(speed)
    self.v_ego = float(v_ego_x[0])
    self.a_ego = float(v_ego_x[1])

    # this is a hack for the interceptor. This is now only used in the simulation
    # TODO: Replace tests by toyota so this can go away
    if self.CP.enableGasInterceptor:
      self.user_gas = cp.vl["GAS_SENSOR"]['INTERCEPTOR_GAS']
      self.user_gas_pressed = self.user_gas > 0 # this works because interceptor read < 0 when pedal position is 0. Once calibrated, this will change

    self.gear = 0 if self.CP.carFingerprint == CAR.CIVIC else cp.vl["GEARBOX"]['GEAR']
    self.angle_steers = cp.vl["STEERING_SENSORS"]['STEER_ANGLE']
    self.angle_steers_rate = cp.vl["STEERING_SENSORS"]['STEER_ANGLE_RATE']

    
    self.cruise_buttons = cp.vl["SCM_BUTTONS"]['CRUISE_BUTTONS']

    self.blinker_on = cp.vl["SCM_FEEDBACK"]['LEFT_BLINKER'] or cp.vl["SCM_FEEDBACK"]['RIGHT_BLINKER']
    self.left_blinker_on = cp.vl["SCM_FEEDBACK"]['LEFT_BLINKER']
    self.right_blinker_on = cp.vl["SCM_FEEDBACK"]['RIGHT_BLINKER']

    if self.CP.carFingerprint in (CAR.CIVIC, CAR.ODYSSEY, CAR.CRV_5G, CAR.ACCORD, CAR.ACCORD_15, CAR.ACCORDH, CAR.CIVIC_BOSCH, CAR.CRV_HYBRID):
      self.park_brake = cp.vl["EPB_STATUS"]['EPB_STATE'] != 0
      self.brake_hold = cp.vl["VSA_STATUS"]['BRAKE_HOLD_ACTIVE']
      self.main_on = cp.vl["SCM_FEEDBACK"]['MAIN_ON']
    else:
      self.park_brake = 0  # TODO
      self.brake_hold = 0  # TODO
      self.main_on = cp.vl["SCM_BUTTONS"]['MAIN_ON']

    can_gear_shifter = int(cp.vl["GEARBOX"]['GEAR_SHIFTER'])
    self.gear_shifter = parse_gear_shifter(can_gear_shifter, self.shifter_values)

    self.pedal_gas = cp.vl["POWERTRAIN_DATA"]['PEDAL_GAS']
    # crv doesn't include cruise control
    if self.CP.carFingerprint in (CAR.CRV, CAR.ODYSSEY, CAR.ACURA_RDX, CAR.RIDGELINE, CAR.PILOT_2019):
      self.car_gas = self.pedal_gas
    else:
      self.car_gas = cp.vl["GAS_PEDAL_2"]['CAR_GAS']

    self.steer_torque_driver = cp.vl["STEER_STATUS"]['STEER_TORQUE_SENSOR']
    self.steer_override = abs(self.steer_torque_driver) > STEER_THRESHOLD[self.CP.carFingerprint]

    self.brake_switch = cp.vl["POWERTRAIN_DATA"]['BRAKE_SWITCH']

    if self.CP.radarOffCan:
      self.stopped = cp.vl["ACC_HUD"]['CRUISE_SPEED'] == 252.
      self.cruise_speed_offset = calc_cruise_offset(0, self.v_ego)
      if self.CP.carFingerprint in (CAR.CIVIC_BOSCH, CAR.ACCORDH, CAR.CRV_HYBRID):
        self.brake_switch = cp.vl["POWERTRAIN_DATA"]['BRAKE_SWITCH']
        self.brake_pressed = cp.vl["POWERTRAIN_DATA"]['BRAKE_PRESSED'] or \
                          (self.brake_switch and self.brake_switch_prev and \
                          cp.ts["POWERTRAIN_DATA"]['BRAKE_SWITCH'] != self.brake_switch_ts)
        self.brake_switch_prev = self.brake_switch
        self.brake_switch_ts = cp.ts["POWERTRAIN_DATA"]['BRAKE_SWITCH']
      else:
        self.brake_pressed = cp.vl["BRAKE_MODULE"]['BRAKE_PRESSED']
      # On set, cruise set speed pulses between 254~255 and the set speed prev is set to avoid this.
      self.v_cruise_pcm = self.v_cruise_pcm_prev if cp.vl["ACC_HUD"]['CRUISE_SPEED'] > 160.0 else cp.vl["ACC_HUD"]['CRUISE_SPEED']
      self.v_cruise_pcm_prev = self.v_cruise_pcm
    else:
      self.brake_switch = cp.vl["POWERTRAIN_DATA"]['BRAKE_SWITCH']
      self.cruise_speed_offset = calc_cruise_offset(cp.vl["CRUISE_PARAMS"]['CRUISE_SPEED_OFFSET'], self.v_ego)
      self.v_cruise_pcm = cp.vl["CRUISE"]['CRUISE_SPEED_PCM']
      # brake switch has shown some single time step noise, so only considered when
      # switch is on for at least 2 consecutive CAN samples
      self.brake_pressed = cp.vl["POWERTRAIN_DATA"]['BRAKE_PRESSED'] or \
                         (self.brake_switch and self.brake_switch_prev and \
                         cp.ts["POWERTRAIN_DATA"]['BRAKE_SWITCH'] != self.brake_switch_ts)
      self.brake_switch_prev = self.brake_switch
      self.brake_switch_ts = cp.ts["POWERTRAIN_DATA"]['BRAKE_SWITCH']
    
    self.v_cruise_pcm = int(min(self.v_cruise_pcm, interp(self.angle_steers, self.Angle, self.Angle_Speed)))
    self.user_brake = cp.vl["VSA_STATUS"]['USER_BRAKE']
    self.pcm_acc_status = cp.vl["POWERTRAIN_DATA"]['ACC_STATUS']
    self.hud_lead = cp.vl["ACC_HUD"]['HUD_LEAD']
    if self.cruise_setting == 3:
      if cp.vl["SCM_BUTTONS"]["CRUISE_SETTING"] == 0:
        self.trMode = (self.trMode + 1 ) % 3
        self.cstm_btns.btns[4].btn_label2 = self.trLabels[self.trMode]
    self.prev_cruise_setting = self.cruise_setting
    self.cruise_setting = cp.vl["SCM_BUTTONS"]['CRUISE_SETTING']
    self.read_distance_lines = self.trMode + 1
    if self.read_distance_lines <> self.read_distance_lines_prev:
      if self.read_distance_lines == 1:
        self.UE.custom_alert_message(2,"Following distance set to 0.9s",200,3)
      if self.read_distance_lines == 2:
        self.UE.custom_alert_message(2,"Dynamic following distance",200,3)
      if self.read_distance_lines == 3:
        self.UE.custom_alert_message(2,"Following distance set to 2.7s",200,3)
      self.read_distance_lines_prev = self.read_distance_lines

# carstate standalone tester
if __name__ == '__main__':
  import zmq
  context = zmq.Context()

  class CarParams(object):
    def __init__(self):
      self.carFingerprint = "HONDA CIVIC 2016 TOURING"
      self.enableGasInterceptor = 0
  CP = CarParams()
  CS = CarState(CP)

  # while 1:
  #   CS.update()
  #   time.sleep(0.01)

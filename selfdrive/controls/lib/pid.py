import numpy as np
from common.numpy_fast import clip, interp
from common.op_params import opParams
import time

def apply_deadzone(error, deadzone):
  if error > deadzone:
    error -= deadzone
  elif error < - deadzone:
    error += deadzone
  else:
    error = 0.
  return error


class PIController:
  def __init__(self, k_p, k_i, k_f=1., pos_limit=None, neg_limit=None, rate=100, sat_limit=0.8, convert=None):
    self._k_p = k_p  # proportional gain
    self._k_i = k_i  # integral gain
    self.k_f = k_f  # feedforward gain

    self.pos_limit = pos_limit
    self.neg_limit = neg_limit

    self.sat_count_rate = 1.0 / rate
    self.i_unwind_rate = 0.3 / rate
    self.i_rate = 1.0 / rate
    self.sat_limit = sat_limit
    self.convert = convert

    self.reset()

  @property
  def k_p(self):
    return interp(self.speed, self._k_p[0], self._k_p[1])

  @property
  def k_i(self):
    return interp(self.speed, self._k_i[0], self._k_i[1])

  def _check_saturation(self, control, check_saturation, error):
    saturated = (control < self.neg_limit) or (control > self.pos_limit)

    if saturated and check_saturation and abs(error) > 0.1:
      self.sat_count += self.sat_count_rate
    else:
      self.sat_count -= self.sat_count_rate

    self.sat_count = clip(self.sat_count, 0.0, 1.0)

    return self.sat_count > self.sat_limit

  def reset(self):
    self.p = 0.0
    self.i = 0.0
    self.f = 0.0
    self.sat_count = 0.0
    self.saturated = False
    self.control = 0

  def update(self, setpoint, measurement, speed=0.0, check_saturation=True, override=False, feedforward=0., deadzone=0., freeze_integrator=False):
    self.speed = speed

    error = float(apply_deadzone(setpoint - measurement, deadzone))
    self.p = error * self.k_p
    self.f = feedforward * self.k_f

    if override:
      self.i -= self.i_unwind_rate * float(np.sign(self.i))
    else:
      i = self.i + error * self.k_i * self.i_rate
      control = self.p + self.f + i

      if self.convert is not None:
        control = self.convert(control, speed=self.speed)

      # Update when changing i will move the control away from the limits
      # or when i will move towards the sign of the error
      if ((error >= 0 and (control <= self.pos_limit or i < 0.0)) or \
          (error <= 0 and (control >= self.neg_limit or i > 0.0))) and \
         not freeze_integrator:
        self.i = i

    control = self.p + self.f + self.i
    if self.convert is not None:
      control = self.convert(control, speed=self.speed)

    self.saturated = self._check_saturation(control, check_saturation, error)

    self.control = clip(control, self.neg_limit, self.pos_limit)
    return self.control


class PIDController:
  def __init__(self, k_p, k_i, k_d, k_f=1., pos_limit=None, neg_limit=None, rate=100, sat_limit=0.8, convert=None):
    self.op_params = opParams()
    self._k_p = k_p  # proportional gain
    self._k_i = k_i  # integral gain
    self._k_d = k_d  # derivative gain
    self.k_f = k_f  # feedforward gain

    self.enable_derivative = self.op_params.get('enable_long_derivative', True)
    self.write_errors = self.op_params.get('write_errors', False)
    self.restrict_sign_change = self.op_params.get('restrict_sign_change', False)
    self.kd = self.op_params.get('kd', 1.2)
    self.use_kd = self.op_params.get('use_kd', True)

    self.max_accel_d = 0.44704  # 0.6 mph/s

    self.pos_limit = pos_limit
    self.neg_limit = neg_limit

    self.sat_count_rate = 1.0 / rate
    self.i_unwind_rate = 0.3 / rate
    self.rate = 1.0 / rate
    self.sat_limit = sat_limit
    self.convert = convert

    self.reset()

  @property
  def k_p(self):
    return interp(self.speed, self._k_p[0], self._k_p[1])

  @property
  def k_i(self):
    return interp(self.speed, self._k_i[0], self._k_i[1])

  @property
  def k_d(self):
    if self.use_kd:
      return self.kd
    else:
      return interp(self.speed, self._k_d[0], self._k_d[1])

  def _check_saturation(self, control, check_saturation, error):
    saturated = (control < self.neg_limit) or (control > self.pos_limit)

    if saturated and check_saturation and abs(error) > 0.1:
      self.sat_count += self.sat_count_rate
    else:
      self.sat_count -= self.sat_count_rate

    self.sat_count = clip(self.sat_count, 0.0, 1.0)

    return self.sat_count > self.sat_limit

  def reset(self):
    self.p = 0.0
    self.id = 0.0
    self.f = 0.0
    self.sat_count = 0.0
    self.saturated = False
    self.control = 0
    self.last_setpoint = 0.0
    self.last_measurement = 0.0
    self.last_error = 0.0

  def update(self, setpoint, measurement, speed=0.0, check_saturation=True, override=False, feedforward=0., derivative=0, deadzone=0., freeze_integrator=False):
    self.enable_derivative = self.op_params.get('enable_long_derivative', True)
    self.write_errors = self.op_params.get('write_errors', False)
    self.restrict_sign_change = self.op_params.get('restrict_sign_change', False)
    self.kd = self.op_params.get('kd', 1.2)
    self.use_kd = self.op_params.get('use_kd', True)

    self.speed = speed

    error = float(apply_deadzone(setpoint - measurement, deadzone))

    if self.write_errors:
      # keys: error, setpoint, measurement, enable_derivative, time
      with open('/data/long_errors', 'a') as f:
        f.write('{}\n'.format([error, setpoint, measurement, self.enable_derivative, time.time()]))

    self.p = error * self.k_p
    self.f = feedforward * self.k_f

    d = -self.k_d * derivative * self.rate
    if override:
      self.id -= self.i_unwind_rate * float(np.sign(self.id))
    else:
      i = self.id + error * self.k_i * self.rate
      control = self.p + self.f + i + d

      if self.convert is not None:
        control = self.convert(control, speed=self.speed)

      # Update when changing i will move the control away from the limits
      # or when i will move towards the sign of the error
      if ((error >= 0 and (control <= self.pos_limit or i < 0.0)) or \
          (error <= 0 and (control >= self.neg_limit or i > 0.0))) and \
         not freeze_integrator:
        self.id = i

      # if self.enable_derivative:
      #   if abs(setpoint - self.last_setpoint) / self.rate < self.max_accel_d:  # and if cruising with minimal setpoint change
      #     # only multiply i_rate if we're adding to self.i
      #     # d = self.k_d * ((error - self.last_error) / self.i_rate)
      #     # d = -k_d * ((measurement - self.last_measurement) / self.d_rate) * self.i_rate
      #     d = -self.k_d * derivative * self.rate
      #     if (self.id > 0 and self.id + d >= 0) or (self.id < 0 and self.id + d <= 0):  # and if adding d doesn't make i cross 0
      #       # then add derivative to integral
      #       self.id += d
      #     elif not self.restrict_sign_change:
      #       self.id += d

    control = self.p + self.f + self.id + d
    if self.convert is not None:
      control = self.convert(control, speed=self.speed)

    self.saturated = self._check_saturation(control, check_saturation, error)

    self.last_setpoint = setpoint
    self.last_measurement = measurement
    self.last_error = error

    self.control = clip(control, self.neg_limit, self.pos_limit)
    return self.control

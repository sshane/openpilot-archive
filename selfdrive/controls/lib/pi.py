from numpy import clip, interp


class CustomPID:
  def __init__(self, k_p, k_i, limits, rate):
    self._k_p = k_p
    self._k_i = k_i
    self.limits = limits
    self.rate = rate
    self.i_rate = 1 / rate
    self.p = 0  # proportional
    self.i = 0  # integral (over time)
    self.f = 0  # derivative (amount of change)

  @property
  def k_p(self):
    return interp(self.speed, self._k_p[0], self._k_p[1])

  @property
  def k_i(self):
    return interp(self.speed, self._k_i[0], self._k_i[1])

  def update(self, set_point, measurement, speed):
    self.speed = speed
    error = set_point - measurement
    p = error * self.k_p
    self.i = self.i + error * self.k_i * self.i_rate
    output = p + self.i
    return clip(output, *self.limits)

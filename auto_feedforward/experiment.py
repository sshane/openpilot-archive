import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression

MS_TO_MPH = 2.23694
MPH_TO_MS = 1 / MS_TO_MPH

k_f = 0.00007818594
steerRatio = 17.8
wheelbase = 2.70

MAX_TORQUE = 1500


def get_feedforward(angle_steers_des, v_ego):
  # steer_feedforward = v_ego ** 2 * angle_steers_des * CV.DEG_TO_RAD / (CP.steerRatio * CP.wheelbase)
  steer_feedforward = angle_steers_des * v_ego**2  # proportional to realigning tire momentum (~ lateral accel)
  return steer_feedforward


speeds = [20 * MPH_TO_MS, 40 * MPH_TO_MS, 60 * MPH_TO_MS, 80 * MPH_TO_MS]
angles = [40, 45, 5, -5]
torque = [1200, 1350, 200, 250]
torque = [torq / MAX_TORQUE for torq in torque]
feedfs = [torq / get_feedforward(ang, spd) for ang, spd, torq in zip(angles, speeds, torque)]

print(f"{speeds=}")
print(f"{angles=}")
print(f"{torque=}")
print(f"{feedfs=}")

# plt.plot(speeds, torque, label='torque')
plt.plot(speeds, feedfs, label='feedforward')

# Prepare data for lineral regression
speeds = np.array(speeds).reshape(-1, 1)

lr = LinearRegression()
lr.fit(speeds, feedfs)

print(f'\nregression score: {lr.score(speeds, feedfs)}')
print(f'f(x) = {lr.coef_[0]}x + {lr.intercept_}')

x = np.linspace(0, max(speeds), 50)
y = [lr.predict([spd])[0] for spd in x]

plt.plot(x, y, label='fitted')
plt.legend()
plt.show()

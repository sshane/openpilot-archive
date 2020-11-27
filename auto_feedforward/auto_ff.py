import os
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib import cm
from scipy.optimize import curve_fit
from auto_feedforward.load_data import get_data

MS_TO_MPH = 2.23694
MPH_TO_MS = 1 / MS_TO_MPH

# old_k_f = 0.0000795769068
old_k_f = 0.00003
steerRatio = 17.8
wheelbase = 2.70

MAX_TORQUE = 1500


def old_feedforward(v_ego, angle_steers, angle_offset=0):
  steer_feedforward = (angle_steers - angle_offset)
  steer_feedforward *= v_ego ** 2
  return steer_feedforward


class CustomFeedforward:
  def __init__(self, fit_all=True):
    """
      fit_all: if True, then it fits kf as well as speed poly
               if False, then it only fits kf using speed poly found from prior fitting and data
    """
    if not fit_all:
      self.c1, self.c2, self.c3 = 0.35189607550172824, 7.506201251644202, 69.226826411091
      self.fit_func = self._fit_just_kf
    else:
      # self.fit_func = self._fit_all
      self.fit_func = self._fit_just_poly

  def get(self, v_ego, angle_steers, *args):  # helper function to easily use fitting ff function):
    x_input = np.array((v_ego, angle_steers)).T
    return self.fit_func(x_input, *args)

  @staticmethod
  def _fit_all(x_input, _kf, _c1, _c2, _c3):
    """
      x_input is array of v_ego and angle_steers
      all _params are to be fit by curve_fit
      kf is multiplier from angle to torque
      c1-c3 are poly coefficients
    """
    v_ego, angle_steers = x_input.copy()
    steer_feedforward = angle_steers * np.polyval([_c1, _c2, _c3], v_ego) * _kf
    return steer_feedforward

  def _fit_just_kf(self, x_input, _kf):
    """
      Just fits kf using best-so-far speed poly
    """
    v_ego, angle_steers = x_input.copy()
    steer_feedforward = angle_steers * np.polyval([self.c1, self.c2, self.c3], v_ego)
    return steer_feedforward * _kf

  @staticmethod
  def _fit_just_poly(x_input, _c1, _c2, _c3):
    v_ego, angle_steers = x_input.copy()
    steer_feedforward = angle_steers * np.polyval([_c1, _c2, _c3], v_ego) * old_k_f
    return steer_feedforward


CF = CustomFeedforward(fit_all=True)


data = get_data(os.getcwd() + '/ff_data')
print(f'Samples: {len(data)}')

print('Max angle: {}'.format(max([abs(i['angle_steers']) for i in data])))
print('Top speed: {} mph'.format(max([i['v_ego'] for i in data]) * MS_TO_MPH))

for line in data:  # need to apply average angle offset for feedforward calculations
  line['angle_steers'] -= line['angle_offset']

# Data filtering
if FILTER_DATA := True:
  max_angle_error = 0.75
  data = [line for line in data if 1e-4 <= abs(line['angle_steers']) <= 60]
  data = [line for line in data if abs(line['v_ego']) > 1 * MPH_TO_MS]
  data = [line for line in data if abs(line['angle_steers'] - line['angle_steers_des']) < max_angle_error]

  # data = [line for line in data if abs(line['torque']) >= 25]
  # data = [line for line in data if np.sign(line['angle_steers']) == np.sign(line['torque'])]

# Data preprocessing
for line in data:
  line['angle_steers'] = abs(line['angle_steers'])
  line['angle_steers_des'] = abs(line['angle_steers_des'])
  line['torque'] = abs(line['torque'])
  del line['time']

print(f'Samples: {len(data)}')
data_speeds = np.array([line['v_ego'] for line in data])
data_angles = np.array([line['angle_steers'] for line in data])
data_torque = np.array([line['torque'] for line in data])

# Tests
assert all([i >= 0 for i in data_angles]), 'An angle sample is negative'
assert all([i >= 0 for i in data_torque]), 'A torque sample is negative'

params, covs = curve_fit(CF.fit_func, np.array([data_speeds, data_angles]), np.array(data_torque) / MAX_TORQUE, maxfev=1000)

if len(params) == 4:
  print('FOUND KF: {}'.format(params[0]))
  print('FOUND POLY: {}'.format(params[1:].tolist()))
elif len(params) == 3:
  print('FOUND POLY: {}'.format(params.tolist()))
elif len(params) == 1:
  print('FOUND KF: {}'.format(params[0]))
else:
  print('Unsupported number of params')
  raise Exception('Unsupported number of params: {}'.format(len(params)))

std_func = []
fitted_func = []
for line in data:
  std_func.append(abs(old_feedforward(line['v_ego'], line['angle_steers']) * old_k_f * MAX_TORQUE - line['torque']))
  fitted_func.append(abs(CF.get(line['v_ego'], line['angle_steers'], *params) * MAX_TORQUE - line['torque']))

print('Torque MAE: {} (standard) - {} (fitted)'.format(np.mean(std_func), np.mean(fitted_func)))
print('Torque STD: {} (standard) - {} (fitted)\n'.format(np.std(std_func), np.std(fitted_func)))


if SPEED_DATA_ANALYSIS := True:  # analyzes how torque needed changes based on speed
  if PLOT_ANGLE_DIST := False:
    sns.distplot([line['angle_steers'] for line in data if abs(line['angle_steers']) < 30], bins=200)
    raise Exception

  res = 100
  color = 'blue'

  _angles = [
    [5, 10],
    [10, 20],
    [10, 15],
    [15, 20],
    [20, 25],
    # [20, 30],
  ]

  for idx, angle_range in enumerate(_angles):
    temp_data = [line for line in data if angle_range[0] <= abs(line['angle_steers']) <= angle_range[1]]
    print(f'{angle_range} samples: {len(temp_data)}')
    plt.figure(idx)
    speeds, torque = zip(*[[line['v_ego'], line['torque']] for line in temp_data])
    plt.scatter(np.array(speeds) * MS_TO_MPH, torque, label='{} deg'.format('-'.join(map(str, angle_range))), color=color, s=0.05)

    _x_ff = np.linspace(0, max(speeds), res)
    _y_ff = [old_feedforward(_i, np.mean(angle_range)) * old_k_f * MAX_TORQUE for _i in _x_ff]
    plt.plot(_x_ff * MS_TO_MPH, _y_ff, color='orange', label='standard ff model at {} deg'.format(np.mean(angle_range)))

    _y_ff = [CF.get(_i, np.mean(angle_range), *params) * MAX_TORQUE for _i in _x_ff]
    plt.plot(_x_ff * MS_TO_MPH, _y_ff, color='purple', label='new fitted ff function')

    plt.legend()
    plt.xlabel('speed (mph)')
    plt.ylabel('torque')

  # plt.scatter(speeds, feedfs, s=0.1)
  # sns.distplot(ffs)


if ANGLE_DATA_ANALYSIS := True:  # analyzes how angle changes need of torque (RESULT: seems to be relatively linear, can be tuned by k_f)
  if PLOT_ANGLE_DIST := False:
    sns.distplot([line['angle_steers'] for line in data if abs(line['angle_steers']) < 30], bins=200)
    raise Exception

  res = 100

  _speeds = np.r_[[
    [0, 10],
    [10, 20],
    [20, 30],
    [30, 40],
    [40, 50],
    [50, 60],
    [60, 70],
  ]] * MPH_TO_MS
  color = 'blue'

  for idx, speed_range in enumerate(_speeds):
    temp_data = [line for line in data if speed_range[0] <= line['v_ego'] <= speed_range[1]]
    print(f'{speed_range} samples: {len(temp_data)}')
    plt.figure(idx + 7)
    angles, torque, speeds = zip(*[[line['angle_steers'], line['torque'], line['v_ego']] for line in temp_data])
    plt.scatter(angles, torque, label='{} mph'.format('-'.join([str(round(i * MS_TO_MPH, 1)) for i in speed_range])), color=color, s=0.05)

    _x_ff = np.linspace(0, max(angles), res)
    _y_ff = [old_feedforward(np.mean(speed_range), _i) * old_k_f * MAX_TORQUE for _i in _x_ff]
    plt.plot(_x_ff, _y_ff, color='orange', label='standard ff model at {} mph'.format(np.round(np.mean(speed_range) * MS_TO_MPH, 1)))

    _y_ff = [CF.get(np.mean(speed_range), _i, *params) * MAX_TORQUE for _i in _x_ff]
    plt.plot(_x_ff, _y_ff, color='purple', label='new fitted ff function')

    plt.legend()
    plt.xlabel('angle (deg)')
    plt.ylabel('torque')

  # plt.scatter(speeds, feedfs, s=0.1)
  # sns.distplot(ffs)


if PLOT_3D := False:
  X_test = np.linspace(0, max(data_speeds), 20)
  Y_test = np.linspace(0, max(data_angles), 20)

  Z_test = np.zeros((len(X_test), len(Y_test)))
  for i in range(len(X_test)):
    for j in range(len(Y_test)):
      Z_test[i][j] = CF.get(X_test[i], Y_test[j], *params)

  X_test, Y_test = np.meshgrid(X_test, Y_test)

  fig = plt.figure()
  ax = plt.axes(projection='3d')

  surf = ax.plot_surface(X_test * MS_TO_MPH, Y_test, Z_test, cmap=cm.magma,
                         linewidth=0, antialiased=False)
  fig.colorbar(surf, shrink=0.5, aspect=5)

  ax.set_xlabel('speed (mph)')
  ax.set_ylabel('angle')
  ax.set_zlabel('feedforward')
  plt.title('New fitted polynomial feedforward function')

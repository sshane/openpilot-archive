import os
import matplotlib.pyplot as plt
import numpy as np
import itertools
from matplotlib import cm
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import scipy
from tensorflow.keras.layers import Dense, LeakyReLU, Dropout
from tensorflow.keras.models import Sequential, load_model
from mpl_toolkits.mplot3d import Axes3D
from auto_feedforward.load_data import get_data
import seaborn as sns

MS_TO_MPH = 2.23694
MPH_TO_MS = 1 / MS_TO_MPH

k_f = 0.00007818594
steerRatio = 17.8
wheelbase = 2.70

MAX_TORQUE = 1500


def get_feedforward(v_ego, angle_steers_des):
  # steer_feedforward = v_ego ** 2 * angle_steers_des * CV.DEG_TO_RAD / (CP.steerRatio * CP.wheelbase)
  steer_feedforward = angle_steers_des * v_ego ** 2  # proportional to realigning tire momentum (~ lateral accel)
  return steer_feedforward


# speeds, angles, torque = get_data(os.getcwd() + '/ff_data')
data = get_data(os.getcwd() + '/ff_data')
print(f'Samples: {len(data)}')

print('Max angle: {}'.format(max([abs(i['angle_steers']) for i in data])))
print('Top speed: {} mph'.format(max([i['v_ego'] for i in data]) * MS_TO_MPH))

data = [line for line in data if .001 <= abs(line['angle_steers']) <= 45]
data = [line for line in data if abs(line['v_ego']) > 1 * MPH_TO_MS]
data = [line for line in data if np.sign(line['angle_steers']) == np.sign(line['torque'])]
data = [line for line in data if abs(line['angle_steers'] - line['angle_steers_des']) < 3]

print(f'Samples: {len(data)}')

speeds = [line['v_ego'] for line in data]
angles = [abs(line['angle_steers']) for line in data]
torque = [abs(line['torque']) / MAX_TORQUE for line in data]

feedfs = [torq / get_feedforward(spd, ang) for ang, spd, torq in zip(angles, speeds, torque)]

USE_TORQUE_AS_FF = True
if USE_TORQUE_AS_FF:
  feedfs = torque
else:
  speeds, angles, feedfs = zip(*[[spd, ang, ff] for spd, ang, ff in zip(speeds, angles, feedfs) if ff < .0001])  # or .0008
del torque

print(f'Samples: {len(speeds)}')

PLOT_FF_DIST = False
if PLOT_FF_DIST:
  plt.figure()
  sns.distplot(feedfs)

assert all([i > 0 for i in feedfs]), 'A feedforward sample is negative?'



# feedf_scale = [min(feedfs), max(feedfs)]  # todo: the following is a 2d model (speed in, ff out)
# scale_to = [0, 1]
# feedfs = np.interp(feedfs, feedf_scale, scale_to)
#
# # speeds = np.array(speeds).reshape(-1, 1)
# # reg = LinearRegression()
# # reg.fit(speeds, feedfs)
# # print(f'\nregression score: {reg.score(speeds, feedfs)}')
# poly = np.polyfit(speeds, feedfs, 3)
#
# X = np.linspace(0, max(speeds), 50)
#
# # plt.plot(X, reg.coef_ * X + reg.intercept_, label='fitted')
# plt.plot(X, np.polyval(poly, X), label='fitted')
# plt.scatter(speeds, feedfs, s=.5)
# plt.legend()
# raise Exception



X = np.array((speeds, angles)).T
feedfs = np.array(feedfs)

fig = plt.figure()
ax = plt.axes(projection='3d')

NORMALIZED = False
if NORMALIZED:
  feedf_scale = [min(feedfs), max(feedfs)]
  scale_to = [0, 1]
  feedfs = np.interp(feedfs, feedf_scale, scale_to)

use_polyfit = False
if use_polyfit:
  degree = 3
  polyreg = make_pipeline(PolynomialFeatures(degree), LinearRegression(normalize=False))
  polyreg.fit(X, feedfs)
  print(f'\nregression score: {polyreg.score(X, feedfs)}')
else:
  LOAD_MODEL = False
  if LOAD_MODEL:
    model = load_model('ff_model.h5')
  else:
    model = Sequential()
    model.add(Dense(12, activation='tanh', input_shape=X.shape[1:]))
    # model.add(Dropout(1/12))
    model.add(Dense(1))
    model.compile('adam', loss='mse', metrics=['mae'])
    model.fit(X, feedfs, epochs=7, batch_size=32)


X_test = np.linspace(0, max(speeds), 20)
Y_test = np.linspace(0, max(angles), 20)


Z_test = np.zeros((len(X_test), len(Y_test)))
for i in range(len(X_test)):
  for j in range(len(Y_test)):
    if use_polyfit:
      Z_test[i][j] = polyreg.predict([[X_test[i], Y_test[j]]])[0]
    else:
      Z_test[i][j] = model.predict_on_batch(np.array([[X_test[i], Y_test[j]]]))[0][0]
    if NORMALIZED:
      Z_test[i][j] = np.interp(Z_test[i][j], scale_to, feedf_scale)

X_test, Y_test = np.meshgrid(X_test, Y_test)

# ax.contour3D(X, Y, Z)
PLOT_DATA = True
if PLOT_DATA:
  if not NORMALIZED:
    ax.scatter3D(speeds, angles, feedfs, c='red', s=.1)
  else:
    ax.scatter3D(speeds, angles, np.interp(feedfs, scale_to, feedf_scale), c='red', s=.1)

PLOT_PRED = True
if PLOT_PRED:
  surf = ax.plot_surface(X_test, Y_test, Z_test, cmap=cm.magma,
                         linewidth=0, antialiased=False)
  fig.colorbar(surf, shrink=0.5, aspect=5)

ax.set_xlabel('speed')
ax.set_ylabel('angle')
ax.set_zlabel('feedforward')
if use_polyfit:
  plt.title(f'Feedforward model ({degree} deg. poly)')
else:
  plt.title('Feedforward keras model')


plt.show()


PLOT_MODEL_2D = True
if PLOT_MODEL_2D:
  # plt.clf()
  plt.figure()
  for spd in [5, 25, 45]:
    x = np.linspace(0, 75, 100)
    y = model.predict([[spd * 0.4470392589877243, i] for i in x])
    plt.plot(x, y, label='{} mph'.format(spd))
  plt.ylabel('torque output')
  plt.xlabel('angle')
  plt.legend()
  plt.show()

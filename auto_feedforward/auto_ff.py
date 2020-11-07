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


def get_feedforward(v_ego, angle_steers, angle_offset=0):
  steer_feedforward = (angle_steers - angle_offset)
  steer_feedforward *= v_ego ** 2
  return steer_feedforward


# speeds, angles, torque = get_data(os.getcwd() + '/ff_data')
data = get_data(os.getcwd() + '/ff_data')
print(f'Samples: {len(data)}')

print('Max angle: {}'.format(max([abs(i['angle_steers']) for i in data])))
print('Top speed: {} mph'.format(max([i['v_ego'] for i in data]) * MS_TO_MPH))

# Data filtering
data = [line for line in data if 1 <= abs(line['angle_steers']) <= 60]
data = [line for line in data if abs(line['torque']) >= 25]
data = [line for line in data if abs(line['v_ego']) > 1 * MPH_TO_MS]
data = [line for line in data if np.sign(line['angle_steers']) == np.sign(line['torque'])]
data = [line for line in data if abs(line['angle_steers'] - line['angle_steers_des']) < 5]

# Data preprocessing
for line in data:
  line['angle_steers'] = abs(line['angle_steers'])
  line['angle_steers_des'] = abs(line['angle_steers_des'])
  line['torque'] = abs(line['torque'])
  line['feedforward'] = (line['torque'] / MAX_TORQUE) / get_feedforward(line['v_ego'], line['angle_steers'])
  # line['feedforward'] = (line['torque'] / MAX_TORQUE) / get_feedforward(line['v_ego'], line['angle_steers'], line['angle_offset'])
  # line['feedforward'] = (line['torque'] / MAX_TORQUE) / get_feedforward(line['v_ego'], line['angle_steers'], -line['angle_offset'])

data = [line for line in data if line['feedforward'] < .001]
print(f'Samples: {len(data)}')
speeds = [line['v_ego'] for line in data]


DATA_ANALYSIS = True
if DATA_ANALYSIS:
  ffs = []
  mae = []
  for line in data:
    ffs.append(line['feedforward'])
    mae.append(abs(line['feedforward'] - k_f))

  print('\nmae: {}'.format(np.mean(mae)))
  print('avg. kf: {}'.format(np.mean(ffs)))
  print('std. kf: {}'.format(np.std(ffs)))
  # sns.distplot([line['v_ego'] * MS_TO_MPH for line in data])
  # raise

  data_10mph = [line for line in data if 8 * MPH_TO_MS <= line['v_ego'] <= 25 * MPH_TO_MS]
  print(f'{len(data_10mph)=}')
  data_35mph = [line for line in data if 32 * MPH_TO_MS <= line['v_ego'] <= 37 * MPH_TO_MS]
  print(f'{len(data_35mph)=}')
  data_55mph = [line for line in data if 55 * MPH_TO_MS <= line['v_ego'] <= 65 * MPH_TO_MS]
  print(f'{len(data_55mph)=}')
  # data_60mph = [line for line in data if 58 * MPH_TO_MS <= line['v_ego'] <= 62 * MPH_TO_MS]
  # print(f'{len(data_60mph)=}')

  slopes = []

  plt.figure(0)
  angles_35mph, torque_35mph = zip(*[[line['angle_steers'], line['torque']] for line in data_35mph])
  plt.scatter(angles_35mph, torque_35mph, label='35 mph', s=0.5)
  poly_35mph = np.polyfit(angles_35mph, torque_35mph, 1)
  plt.plot(np.linspace(0, max(angles_35mph), 50), np.polyval(poly_35mph, np.linspace(0, max(angles_35mph), 50)), color='orange')
  slopes.append(poly_35mph[0] * ((max(angles_35mph) - min(angles_35mph)) / (max(torque_35mph) - min(torque_35mph))))
  plt.plot(np.linspace(0, max(angles_35mph), len(data_35mph)), get_feedforward(np.mean([line['v_ego'] for line in data_35mph]), np.linspace(0, max(angles_35mph), len(data_35mph))) * k_f * 1500, color='red')
  plt.plot(np.linspace(0, max(angles_35mph), len(data_35mph)), get_feedforward(np.mean([line['v_ego'] for line in data_35mph]), np.linspace(0, max(angles_35mph), len(data_35mph))) * k_f * 0.7744 * 1500, color='green')
  print('\nSLOPE OF 35 MPH is {}'.format(slopes[-1]))

  plt.figure(1)
  angles_55mph, torque_55mph = zip(*[[line['angle_steers'], line['torque']] for line in data_55mph])
  plt.scatter(angles_55mph, torque_55mph, label='55 mph', s=0.5)
  poly_55mph = np.polyfit(angles_55mph, torque_55mph, 1)
  plt.plot(np.linspace(0, max(angles_55mph), 50), np.polyval(poly_55mph, np.linspace(0, max(angles_55mph), 50)), color='orange')
  slopes.append(poly_55mph[0] * ((max(angles_55mph) - min(angles_55mph)) / (max(torque_55mph) - min(torque_55mph))))
  print('\nSLOPE OF 55 MPH is {}'.format(slopes[-1]))

  plt.figure(2)
  angles_10mph, torque_10mph = zip(*[[line['angle_steers'], line['torque']] for line in data_10mph])
  plt.scatter(angles_10mph, torque_10mph, label='10 mph (low speed)', s=0.5)
  poly_10mph = np.polyfit(angles_10mph, torque_10mph, 1)
  plt.plot(np.linspace(0, max(angles_10mph), 50), np.polyval(poly_10mph, np.linspace(0, max(angles_10mph), 50)), color='orange')
  slopes.append(poly_10mph[0] * ((max(angles_10mph) - min(angles_10mph)) / (max(torque_10mph) - min(torque_10mph))))
  print('\nSLOPE OF 10 MPH is {}'.format(slopes[-1]))

  for i in range(3):
    plt.figure(i)
    plt.legend()
    plt.xlabel('angle')
    plt.ylabel('torque')
  print('avg. of {} slopes: {}'.format(len(slopes), np.round(np.mean(slopes), 4)))

  # plt.scatter(speeds, feedfs, s=0.1)

  # sns.distplot(ffs)
  raise Exception

_2D_MODEL = True
if _2D_MODEL:
  # feedf_scale = [min(feedfs), max(feedfs)]  # todo: the following is a 2d model (speed in, ff out)
  # scale_to = [0, 1]
  # feedfs = np.interp(feedfs, feedf_scale, scale_to)

  poly = np.polyfit(speeds, feedfs, 3)

  X = np.linspace(0, max(speeds), 50)

  # plt.plot(X, reg.coef_ * X + reg.intercept_, label='fitted')
  plt.scatter(speeds, feedfs, s=.1)
  plt.plot(X, np.polyval(poly, X), color='orange', label='fitted')
  plt.legend()
  raise Exception


angles = [line['angle_steers'] for line in data]
torque = [line['torque'] for line in data]

feedfs = [line['feedforward'] for line in data]

USE_TORQUE_AS_FF = False
if USE_TORQUE_AS_FF:
  feedfs = torque
del torque

# Tests
assert all([i > 0 for i in feedfs]), 'A feedforward sample is zero or negative'
assert all([i >= 0 for i in angles]), 'An angle sample is negative'


print(f'Samples: {len(speeds)}')

PLOT_FF_DIST = False
if PLOT_FF_DIST:
  plt.figure()
  sns.distplot(feedfs)






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

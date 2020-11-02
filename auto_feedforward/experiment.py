import matplotlib.pyplot as plt
import numpy as np
import itertools
from matplotlib import cm
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import scipy
from tensorflow.keras.layers import Dense
from tensorflow.keras.models import Sequential
from mpl_toolkits.mplot3d import Axes3D

MS_TO_MPH = 2.23694
MPH_TO_MS = 1 / MS_TO_MPH

k_f = 0.00007818594
steerRatio = 17.8
wheelbase = 2.70

MAX_TORQUE = 1500


def get_feedforward(angle_steers_des, v_ego):
  # steer_feedforward = v_ego ** 2 * angle_steers_des * CV.DEG_TO_RAD / (CP.steerRatio * CP.wheelbase)
  steer_feedforward = angle_steers_des * v_ego ** 2  # proportional to realigning tire momentum (~ lateral accel)
  return steer_feedforward


RANDOM = True
if not RANDOM:
  speeds = [20, 40, 60, 15, 45, 32]
  angles = [40, 45, 5, 32.45, 1, 50]
  torque = [1200, 1350, 200, 800, 50, 1400]
else:
  samples = 100
  speeds = np.linspace(.5, 80, samples)
  angles = np.linspace(.5, 45, samples)
  torque = [np.random.uniform(a / max(angles) * 1200 + (a / max(angles) * 1200) * 0.2, a / max(angles) * 1200 - (a / max(angles) * 1200) * 0.2) for a in angles]


speeds = [spd * MPH_TO_MS for spd in speeds]
torque = [torq / MAX_TORQUE for torq in torque]
feedfs = [torq / get_feedforward(ang, spd) for ang, spd, torq in zip(angles, speeds, torque)]

assert all([i > 0 for i in feedfs]), 'A feedforward sample is negative?'

print(f"{speeds=}")
print(f"{angles=}")
print(f"{torque=}")
print(f"{feedfs=}")

# plt.plot(speeds, torque, label='torque')
# plt.plot(speeds, feedfs, label='feedforward')

# Prepare data for lineral regression
# X = np.array(speeds).reshape(-1, 1)  # for just speeds
X = np.array((speeds, angles)).T
feedfs = np.array(feedfs)

fig = plt.figure()
ax = plt.axes(projection='3d')

use_polyfit = False
if use_polyfit:
  degree = 3
  polyreg = make_pipeline(PolynomialFeatures(degree), LinearRegression())
  polyreg.fit(X, feedfs)
  print(f'\nregression score: {polyreg.score(X, feedfs)}')
else:
  model = Sequential()
  model.add(Dense(12, activation='relu', input_shape=X.shape[1:]))
  model.add(Dense(1))
  model.compile('adam', loss='mse', metrics=['mae'])
  model.fit(X, feedfs, epochs=100, batch_size=8)


X = np.linspace(0, max(speeds), 50)
Y = np.linspace(0, max(angles), 50)

Z = np.zeros((len(X), len(Y)))
for i in range(len(X)):
  for j in range(len(Y)):
    if use_polyfit:
      Z[i][j] = polyreg.predict([[X[i], Y[j]]])[0]
    else:
      Z[i][j] = model.predict_on_batch(np.array([[X[i], Y[j]]]))[0][0]

X, Y = np.meshgrid(X, Y)

# ax.contour3D(X, Y, Z)
surf = ax.plot_surface(X, Y, Z, cmap=cm.magma,
                       linewidth=0, antialiased=False)

ax.set_xlabel('speed')
ax.set_ylabel('angle')
ax.set_zlabel('feedforward')
fig.colorbar(surf, shrink=0.5, aspect=5)
if use_polyfit:
  plt.title(f'Feedforward model ({degree} deg. poly)')
else:
  plt.title('Feedforward keras model')


plt.show()

import numpy as np
import matplotlib.pyplot as plt


lane_width = 3.7

dPoly = np.array([-1.4704794921271969e-05, 0.0018400942208245397, 0.01914653740823269, -0.038708023726940155])
pPoly = np.array([-1.4704794921271969e-05, 0.0018400942208245397, 0.03914653740823269, -0.038708023726940155])
x = np.linspace(0, 100, 200)
d_y = np.polyval(pPoly, x)

lPoly = dPoly.copy()
lPoly[3] += lane_width
l_x = np.linspace(0, 100, 200)
l_y = np.polyval(lPoly, x)

rPoly = dPoly.copy()
rPoly[3] -= lane_width
r_x = np.linspace(0, 100, 200)
r_y = np.polyval(rPoly, x)

path_from_left_lane = lPoly.copy()
path_from_left_lane[3] -= lane_width / 2.0
path_from_right_lane = rPoly.copy()
path_from_right_lane[3] += lane_width / 2.0

plt.plot(x, d_y, label='dPoly')
plt.plot(x, l_y, label='simulated lPoly')
plt.plot(x, r_y, label='simulated rPoly')

plt.legend()
plt.show()
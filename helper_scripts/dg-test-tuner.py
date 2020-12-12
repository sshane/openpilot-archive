import matplotlib.pyplot as plt
import numpy as np
from selfdrive.config import Conversions as CV

x = [0.0, 1.4082, 2.8031, 4.2266, 5.3827, 6.1656, 7.2478, 8.2831, 10.2447, 12.964, 15.423, 18.119, 20.117, 24.4661, 29.0581, 32.7101, 35.7633]
y = [0.218, 0.222, 0.233, 0.25, 0.273, 0.294, 0.337, 0.362, 0.38, 0.389, 0.398, 0.41, 0.421, 0.459, 0.512, 0.564, 0.621]

# plt.plot(x, y, 'o-', label='corolla')
y = [np.interp(i, [0.218, (0.218 + 0.398) / 2, 0.398], [1.075 * i, i * 1.05, i]) for i in y]  # more gas at lower speeds up until ~40 mph
plt.plot(x, y, 'o-', label='corolla new')

y = [i * np.interp(_x, [0, 8, 20, 28, 36], [0.84, 0.94, 1.0, 1.0, 1.035]) for i, _x in zip(y, x)]
plt.plot(x, y, 'o-', label='corolla new new')



# plt.plot([min(x), max(x)], [0, 0], 'r--')
# plt.plot([0, 0], [min(y), max(y)], 'r--')

# plt.xlabel('mph')
# plt.ylabel('feet')

# poly = np.polyfit(x, y, 6)
# x = np.linspace(min(x), max(x), 100)
# y = np.polyval(poly, x)
# plt.plot(x, y, label='poly fit')

# to_round = True
# if to_round:
#   x = np.round(x, 4)
#   y = np.round(y, 5)
#   print('x = {}'.format(x.tolist()))
#   print('y = {}'.format(y.tolist()))

plt.legend()
plt.show()

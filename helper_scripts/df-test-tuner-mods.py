import matplotlib.pyplot as plt
import numpy as np
from selfdrive.config import Conversions as CV

x = [0.0, 1.8627, 3.7253, 5.588, 7.4507, 9.3133, 11.5598, 13.645, 22.352, 31.2928, 33.528, 35.7632, 40.2336]  # velocities
x_traffic = [0.0, 1.892, 3.7432, 5.8632, 8.0727, 10.7301, 14.343, 17.6275, 22.4049, 28.6752, 34.8858, 40.35]

relaxed = [1.385, 1.394, 1.406, 1.421, 1.444, 1.474, 1.521, 1.544, 1.568, 1.588, 1.599, 1.613, 1.634]
roadtrip = [1.5486, 1.556, 1.5655, 1.5773, 1.5964, 1.6246, 1.6715, 1.7057, 1.7859, 1.8542, 1.8697, 1.8833, 1.8961]

traffic = [1.3781, 1.3791, 1.3457, 1.3134, 1.3145, 1.318, 1.3485, 1.257, 1.144, 0.979, 0.9461, 0.9156]

plt.plot(x, roadtrip, 'o-', label='roadtrip')
plt.plot(x, relaxed, 'o-', label='relaxed')
# plt.plot(x_traffic, traffic, 'o-', label='traffic')

roadtrip = [i * np.interp(_x, [16, 35], [1.04, 1.0]) for _x, i in zip(x, roadtrip)]

plt.plot(x, roadtrip, 'o-', label='roadtrip new')
roadtrip = [i * np.interp(_x, [0, 13], [1.02, 1.0]) for _x, i in zip(x, roadtrip)]
plt.plot(x, roadtrip, 'o-', label='roadtrip new')



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

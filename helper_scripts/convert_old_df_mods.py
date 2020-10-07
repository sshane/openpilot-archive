import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d


x = [-4.4795, -2.8122, -1.5727, -1.1129, -0.6611, -0.2692, 0.0, 0.1466, 0.5144, 0.6903, 0.9302]  # lead acceleration values
y = [0.24, 0.16, 0.092, 0.0515, 0.0305, 0.022, 0.0, -0.0153, -0.042, -0.053, -0.059]

TR = 1.5  # converted_with_TR

old_y = []
new_y = []
for _x, _y in zip(x, y):
  old_y.append(_y)
  _y = _y / TR + 1
  new_y.append(_y)
  assert np.isclose(TR + old_y[-1], TR * new_y[-1])

new_TR = 1.2
plt.plot(x, np.array(old_y) + new_TR, label='old_y')
plt.plot(x, ((np.array(new_y) * TR - TR) / new_TR + 1) * new_TR, label='new_y')
plt.legend()
print(np.round(new_y, 4).tolist())
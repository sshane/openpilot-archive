from cereal import car
import numpy as np

actuators = car.CarControl.Actuators.new_message()

actuators.gas = np.float64(0.5362)
print('success!')

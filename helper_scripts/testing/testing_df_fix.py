from cereal import car

actuators = car.CarControl.Actuators.new_message()

actuators.gas = 1
print('success!')

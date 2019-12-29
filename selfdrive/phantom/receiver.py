import cereal.messaging as messaging


class PhantomReceiver:
  def __init__(self):
    self.pm = messaging.PubMaster(['phantomData'])

  def receive_data(self, speed, angle):
    self.broadcast_data(True, speed, angle)

  def broadcast_data(self, status, speed, angle):
    phantom_data = messaging.new_message()
    phantom_data.init('phantomData')
    phantom_data.phantomData.status = status
    phantom_data.phantomData.speed = speed
    phantom_data.phantomData.angle = angle
    self.pm.send('phantomData', phantom_data)

  def disable_phantom(self):
    self.broadcast_data(False, 0.0, 0.0)
    return 'DISABLED'

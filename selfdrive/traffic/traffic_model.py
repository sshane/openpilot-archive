import cereal.messaging as messaging
import numpy as np
import sys
import time
from selfdrive.traffic import traffic_wrapper


class Traffic:
  def __init__(self):
    self.W, self.H = 1164, 874
    self.y_hood_crop = 665
    self.input_length = np.product((515, 814, 3))

    self.traffic_model, self.ffi = traffic_wrapper.get_wrapper()
    self.traffic_model.initModel()
    self.image_sock = messaging.sub_sock('image')
    self.pm = messaging.PubMaster(['trafficLights'])

    self.classes = ['RED', 'GREEN', 'YELLOW', 'NONE']

    self.past_preds = []
    self.model_rate = 1 / 10.

    self.run_loop()

  def run_loop(self):
    while True:
      t = time.time()
      image = self.get_image()
      pred = 'NONE'
      if image is not None:
        self.predict(image)
        pred = self.classes[self.traffic_model.predictTraffic(image)]  # returns index of prediction, so we need to get string

      self.send_prediction(pred)
      with open('/data/debug', 'a') as f:
        f.write('loop took: {}s\n'.format(time.time() - t))
      self.rate_keeper(time.time() - t)

  def predict(self, image):
    output = self.ffi.new("float[4]")
    self.traffic_model.predictTraffic(image, output)
    print(np.frombuffer(self.ffi.buffer(op, 4*4), dtype=np.float32))

  def get_image(self):
    msg_data = messaging.recv_one(self.image_sock)  # wait for new frame
    # if msg_data is None and self.past_image is None:
    #   return None
    # elif msg_data is None and self.past_image is not None:
    #   msg_data = self.past_image

    image_data = msg_data.thumbnail.thumbnail
    bgr_image_array = np.frombuffer(image_data[:(3840*874)], dtype=np.uint8).reshape((874, 1280, 3))
    # discard nulls
    bgr_image_array = bgr_image_array[:, :1164]
    bgr_image_array = bgr_image_array.reshape((874, 1164, 3))

    img = self.crop_image(bgr_image_array)  # crop out hood

    img = img.flatten().tolist()  # len: 1257630
    img = self.ffi.new("float[{}]".format(self.input_length), img)

    return img

  def send_prediction(self, pred):
    traffic_send = messaging.new_message()
    traffic_send.init('trafficLights')

    traffic_send.trafficLights.status = pred
    self.pm.send('trafficLights', traffic_send)

  def crop_image(self, img_array):
    h_crop = 175  # horizontal, 150 is good, need to test higher vals
    t_crop = 150  # top, 100 is good. test higher vals
    return img_array[t_crop:self.y_hood_crop, h_crop:-h_crop]  # removes 150 pixels from each side, removes hood, and removes 100 pixels from top

  def rate_keeper(self, loop_time):
    time.sleep(max(self.model_rate - loop_time, 0))

  def most_frequent(self):
    preds = [i['pred'] for i in self.past_preds]
    return max(set(preds), key=preds.count)


def main():
  Traffic()

if __name__ == "__main__":
  main()


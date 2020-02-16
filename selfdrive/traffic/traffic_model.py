import cereal
import cereal.messaging as messaging
import numpy as np
from PIL import Image
import sys
import time
from selfdrive.traffic import traffic_wrapper
import cv2
import numpy as np


class Traffic:
  def __init__(self):
    self.W, self.H = 1164, 874
    self.y_hood_crop = 665
    self.traffic_model, self.ffi = traffic_wrapper.get_wrapper()
    self.traffic_model.init_model()
    self.image_sock = messaging.sub_sock('image')
    self.pm = messaging.PubMaster(['trafficLights'])

    self.classes = ['RED', 'GREEN', 'YELLOW', 'NONE']
    self.predictions_per_second = 10
    self.last_predict_time = 0
    self.past_preds = []
    self.past_image = None
    self.sleep_time = 0.25
    with open('/data/debug', 'a') as f:
      f.write('traffic init\n')

    self.run_loop()

  def run_loop(self):
    while True:
      t = time.time()
      image = self.get_image()
      pred = 'NONE'
      if image is not None:
        pred = self.classes[self.traffic_model.predict_traffic(image)]  # returns index of prediction, so we need to get string

      self.send_prediction(pred)
      with open('/data/debug', 'a') as f:
        f.write('loop took: {}s\n'.format(time.time() - t))
      self.rate_keeper(time.time() - t)

  def get_image(self):
    msg_data = messaging.recv_one(self.image_sock)  # wait for new frame
    # if msg_data is None and self.past_image is None:
    #   return None
    # elif msg_data is None and self.past_image is not None:
    #   msg_data = self.past_image

    image_data = msg_data.thumbnail.thumbnail
    bgr_image_array = np.frombuffer(image_data[:(3840*874)], dtype=np.uint8).reshape((874,1280,3))
    # discard nulls
    bgr_image_array = bgr_image_array[:, :1164]
    bgr_image_array = bgr_image_array.reshape((874, 1164, 3))

    img = bgr_image_array[150:self.y_hood_crop, 175:-175]  # crop out hood
    img = img.astype(np.float32)

    img = np.array([img / 255.]).flatten().tolist()  # len: 1257630
    img = self.ffi.new("float[1257630]", img)

    return img

  def send_prediction(self, pred):
    traffic_send = messaging.new_message()
    traffic_send.init('trafficLights')

    traffic_send.trafficLights.status = pred
    self.pm.send('trafficLights', traffic_send)

  def rate_keeper(self, loop_time):
    time.sleep(max(self.sleep_time - loop_time, 0))

  def most_frequent(self):
    preds = [i['pred'] for i in self.past_preds]
    return max(set(preds), key=preds.count)


def main():
  Traffic()

if __name__ == "__main__":
  main()


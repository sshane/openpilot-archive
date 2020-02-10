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
    self.traffic_model, self.ffi = traffic_wrapper.get_wrapper()
    self.traffic_model.init_model()
    self.image_sock = messaging.sub_sock('image')
    self.pm = messaging.PubMaster(['trafficLights'])

    self.classes = ['RED', 'GREEN', 'YELLOW', 'NONE']
    self.predictions_per_second = 10
    self.last_predict_time = 0
    self.past_preds = []
    self.past_image = None
    self.sleep_time = 1.0
    with open('/data/debug', 'a') as f:
      f.write('traffic init\n')

    self.send_traffic()

  def get_image(self):
    msg_data = messaging.recv_one_or_none(self.image_sock)
    if msg_data is None and self.past_image is None:
      return None
    elif msg_data is None and self.past_image is not None:
      msg_data = self.past_image

    image_data = msg_data.thumbnail.thumbnail
    bgr_image_array = np.frombuffer(image_data[:(3840*874)], dtype=np.uint8).reshape((874,1280,3))
    rgb_image_array = bgr_image_array[...,[2,1,0]]
    # discard nulls
    rgb_image_array = rgb_image_array[:, :1164]
    rgb_image_array = rgb_image_array.reshape((874, 1164, 3))

    img = Image.fromarray(rgb_image_array, 'RGB')
    img = img.resize((self.W // 2, self.H // 2))
    img = np.asarray(img).astype('float32')

    img = np.array([img / 255.]).flatten().tolist()

    return img

  def send_traffic(self):
    while True:
      with open('/data/debug', 'a') as f:
        f.write('in loop\n')
      t = time.time()
      traffic_send = messaging.new_message()
      traffic_send.init('trafficLights')
      image = self.get_image()
      if image is not None:
        pred = self.traffic_model.predict_traffic(image)
        traffic_send.trafficLights.status = self.classes[pred]
      else:
        traffic_send.trafficLights.status = 'NONE'

      self.pm.send('trafficLights', traffic_send)
      self.rate_keeper(time.time() - t)

  def rate_keeper(self, loop_time):
    time.sleep(max(self.sleep_time - loop_time, 0))

  def most_frequent(self):
    preds = [i['pred'] for i in self.past_preds]
    return max(set(preds), key=preds.count)


def main():
  Traffic()

if __name__ == "__main__":
  main()


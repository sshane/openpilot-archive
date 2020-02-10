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

    self.classes = ['RED', 'GREEN', 'YELLOW', 'NONE']
    self.predictions_per_second = 10
    self.last_predict_time = 0
    self.past_preds = []
    self.past_image = None

  def get_image(self):
    msg_data = messaging.recv_one_or_none(self.image_sock)
    if msg_data is None and self.past_image is None:
      return None
    elif msg_data is None:
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

  def get_traffic(self):
    t = time.time()
    self.past_preds = [i for i in self.past_preds if t - i['time'] <= 2]
    print(time.time() - self.last_predict_time)
    print(1/self.predictions_per_second)
    if time.time() - self.last_predict_time >= 1 / self.predictions_per_second:
      image = self.get_image()
      if image is not None:
        with open('/data/working', 'a') as f:
          f.write('working!\n')
        self.past_preds.append({'pred': self.traffic_model.predict_traffic(image), 'time': time.time()})
        self.last_predict_time = time.time()
    if len(self.past_preds) >= self.predictions_per_second / 2:
      return self.classes[self.most_frequent()]
    return self.classes[-1]

  def most_frequent(self):
    preds = [i['pred'] for i in self.past_preds]
    return max(set(preds), key=preds.count)



# traffic = Traffic()

import cereal.messaging as messaging
import numpy as np
import time
from selfdrive.traffic import traffic_wrapper


class Traffic:
  def __init__(self, use_probability=False):
    self.use_probability = use_probability
    self.y_hood_crop = 665
    self.input_length = np.product((515, 814, 3))

    self.traffic_model, self.ffi = traffic_wrapper.get_wrapper()
    self.traffic_model.initModel()
    self.image_sock = messaging.sub_sock('image')
    self.pm = messaging.PubMaster(['trafficLights'])

    self.labels = ['RED', 'GREEN', 'YELLOW', 'NONE']

    self.past_preds = []
    self.model_rate = 1 / 10.

  def start(self):
    self.traffic_loop()

  def traffic_loop(self):
    while True:
      t = time.time()
      image = self.get_image()
      if image is not None:
        pred_array = self.model_predict(image)
        self.past_preds.append(pred_array)
      pred = self.get_prediction()  # uses most common prediction from past second (1 / model_rate), NONE until car is started for 1 second

      self.send_prediction(pred)

      with open('/data/debug', 'a') as f:
        f.write('loop took: {}s\n'.format(time.time() - t))
      self.rate_keeper(time.time() - t)


  def get_prediction(self):
    des_pred_len = int(1 / self.model_rate)
    while len(self.past_preds) > des_pred_len:
      del self.past_preds[0]
    if len(self.past_preds) != des_pred_len:
      return 'NONE'
    if not self.use_probability:
      preds = [np.argmax(pred) for pred in self.past_preds]
    else:
      p = [np.array(p) / sum(p) for p in self.past_preds]
      preds = [pred.index(np.random.choice(pred, p=p[idx])) for idx, pred in enumerate(self.past_preds)]

    most_common = np.argmax(np.bincount(preds))
    return self.labels[most_common]

  def model_predict(self, image):
    output = self.ffi.new("float[4]")
    self.traffic_model.predictTraffic(image, output)
    # np.frombuffer(ffi.buffer(op, 4*4), dtype=np.float32)
    return list(output)  # faster than np.frombuffer, in order self.classes

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
    h_crop = 175
    t_crop = 150
    return img_array[t_crop:self.y_hood_crop, h_crop:-h_crop]  # removes 150 pixels from each side, removes hood, and removes 100 pixels from top

  def rate_keeper(self, loop_time):
    time.sleep(max(self.model_rate - loop_time, 0))

  def most_frequent(self):
    preds = [i['pred'] for i in self.past_preds]
    return max(set(preds), key=preds.count)


def main():
  traffic = Traffic(use_probability=True)
  traffic.start()

if __name__ == "__main__":
  main()


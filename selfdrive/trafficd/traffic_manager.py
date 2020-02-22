from common.numpy_fast import clip
import cereal.messaging as messaging
import numpy as np
import time


class Traffic:
  def __init__(self, use_probability=False):
    self.use_probability = use_probability

    self.pm = messaging.PubMaster(['trafficModelEvent'])
    self.sm = messaging.SubMaster(['trafficModelRaw'])

    self.labels = ['RED', 'GREEN', 'YELLOW', 'NONE']

    self.past_preds = []
    self.model_rate = 1 / 5.
    self.recurrent_length = 1.5  # in seconds, how far back to factor into current prediction
    self.des_pred_len = int(self.recurrent_length / self.model_rate)
    self.last_pred_weight = 8.  # places 2x weight on most recent prediction


    self.weights = np.linspace(1, self.last_pred_weight, self.des_pred_len)
    self.weight_sum = sum(self.weights)
    self.last_log_time = 0

  def start(self):
    self.traffic_loop()

  def traffic_loop(self):
    while True:
      # while not self.is_new_msg(self.sm.logMonoTime['trafficModelRaw']):  # uses rate keeper from traffic.cc, waits for new message
      self.sm.update(0)

      self.past_preds.append(list(self.sm['trafficModelRaw'].prediction))
      pred, confidence = self.get_prediction()  # uses most common prediction from weighted past second list (1 / model_rate), NONE until car is started for min time
      print('{}, confidence: {}'.format(pred, confidence))
      self.send_prediction(pred, confidence)
      time.sleep(1/5.0)

  def is_new_msg(self, log_time):
    is_new = log_time != self.last_log_time
    self.last_log_time = log_time
    return is_new


  def get_prediction(self):
    with open('/data/tdebug', 'a') as f:
      f.write('past_preds: {}\ndes_pred_len: {}\n\n'.format(self.past_preds, self.des_pred_len))

    while len(self.past_preds) > self.des_pred_len:
      del self.past_preds[0]
    if len(self.past_preds) != self.des_pred_len:
      print('Not enough predictions yet!')
      return 'NONE', 1

    # below is a weighted average, the further back in time we go, the less we care (and vice versa)
    '''time_weighted_preds = [[label * self.weights[idx] for label in pred] for idx, pred in enumerate(self.past_preds)]
    time_weighted_preds = [sum(label) / self.weight_sum for label in np.array(time_weighted_preds).T]

    prediction = np.argmax(time_weighted_preds)  # get most confident prediction
    confidence = clip(time_weighted_preds[prediction], 0, 1)'''
    return 'RED', 1.0
    # return self.labels[prediction], confidence

  def send_prediction(self, pred, confidence):
    traffic_send = messaging.new_message()
    traffic_send.init('trafficModelEvent')

    traffic_send.trafficModelEvent.status = pred
    traffic_send.trafficModelEvent.confidence = float(confidence)
    self.pm.send('trafficModelEvent', traffic_send)

  def rate_keeper(self, loop_time):
    time.sleep(max(self.model_rate - loop_time, 0))


def main():
  traffic = Traffic(use_probability=False)
  traffic.start()


if __name__ == "__main__":
  main()

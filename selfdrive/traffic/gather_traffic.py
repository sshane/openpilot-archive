import cereal.messaging as messaging
import numpy as np
from PIL import Image
import os
from threading import Thread
import time

thread_count = 0
last_msg = None


data_dir = '/data/openpilot/selfdrive/traffic/imgs'


def setup_folder():
  if not os.path.exists(data_dir):
    os.mkdir(data_dir)


def write_frame(msg_data):
  global thread_count
  thread_count += 1
  image_data = msg_data.thumbnail.thumbnail
  bgr_image_array = np.frombuffer(image_data[:(3840*874)], dtype=np.uint8).reshape((874,1280,3))
  rgb_image_array = bgr_image_array[...,[2,1,0]]
  # discard nulls
  rgb_image_array = rgb_image_array[:,:1164]
  rgb_image_array = rgb_image_array.reshape((874,1164,3))
  img = Image.fromarray(rgb_image_array, 'RGB')
  filename = time.strftime('%C%y%m%d%H%M%S.{}'.format(msg_data.frameId)) + '.png'
  img.save('{}/{}'.format(data_dir, filename))
  thread_count -= 1


def gather_loop():
  global thread_count
  global last_msg
  time.sleep(10)  # give time for everything to start up
  image_sock = messaging.sub_sock('image')
  while True:
    msg_data = messaging.recv_one(image_sock)
    if msg_data != last_msg:
      last_msg = msg_data
      while thread_count > 5:  # gives us a buffer of 5 frames
        time.sleep(0.05)
      with open('/data/thread_count', 'a') as f:
        f.write('{}\n'.format(thread_count))
      Thread(target=write_frame, args=(msg_data,)).start()


def main():
  setup_folder()
  gather_loop()


if __name__ == '__main__':
  main()

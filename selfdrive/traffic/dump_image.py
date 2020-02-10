#!/usr/bin/env python3

import cereal
import cereal.messaging as messaging
import numpy as np
from PIL import Image
import sys
import time

def main():
  image_sock = messaging.sub_sock('image')
  if not image_sock:
    print("no image socket")
    sys.exit(1)
  while True:
    print("Press [enter] to capture.")
    input()
    print("Reading image from socket.")
    msg_data = messaging.recv_one(image_sock)
    print("Image received, transforming.")
    image_data = msg_data.thumbnail.thumbnail
    bgr_image_array = np.frombuffer(image_data[:(3840*874)], dtype=np.uint8).reshape((874,1280,3))
    rgb_image_array = bgr_image_array[...,[2,1,0]]
    # discard nulls
    rgb_image_array = rgb_image_array[:,:1164]
    rgb_image_array = rgb_image_array.reshape((874,1164,3))
    img = Image.fromarray(rgb_image_array, 'RGB')
    filename = time.strftime('%C%y%m%d%H%M%S') + '.png'
    print("Saving: " + filename)
    img.save(filename)

if __name__ == '__main__':
  main()

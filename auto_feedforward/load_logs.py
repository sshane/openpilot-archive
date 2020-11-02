import os
import matplotlib.pyplot as plt

os.chdir(os.getcwd())


def hex_to_binary(hexdata):
  return (bin(int(hexdata, 16))[2:]).zfill(len(hexdata) * 4)  # adds leading/trailing zeros so data matches up with 8x8 array on cabana


def start_example():
  with open('corolla.csv', 'r') as f:
    csv = f.read().split('\n')

  data = []
  for line in csv:
    if line != "" and line != 'time,addr,bus,data':
      line = line.split(",")
      try:
        data.append({'time': float(line[0]), 'addr': int(line[1]), 'bus': int(line[2]), 'data': line[3]})
      except:
        pass

  GAS_PEDAL = [i for i in data if i['addr'] == 25 and i['bus'] == 0]
  print(len(GAS_PEDAL))

  most_sig_bit = 48  # message starts at bit 48
  size = 8  # gas pedal message is 8 bits
  factor = 0.005  # toyota pedal position is factor of 0.005

  GAS_POS = []
  for i in GAS_PEDAL:
    this_GP = hex_to_binary(i['data'])  # convert hex data to binary
    this_GP = int(this_GP[most_sig_bit:most_sig_bit + size], 2)  # get gas pedal position and convert binary to decimal
    GAS_POS.append(this_GP * factor)

  plt.plot(range(len(GAS_POS)), GAS_POS)
  plt.show()

start_example()

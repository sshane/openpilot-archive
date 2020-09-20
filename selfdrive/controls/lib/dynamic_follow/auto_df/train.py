import os
# os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
# os.environ["CUDA_VISIBLE_DEVICES"] = ""
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.optimizers import Adam, Adadelta
import tensorflow as tf
import numpy as np
import seaborn as sns
import ast
from selfdrive.config import Conversions as CV

my_devices = tf.config.experimental.list_physical_devices(device_type='CPU')
tf.config.experimental.set_visible_devices(devices=my_devices, device_type='CPU')

os.chdir(os.getcwd())


def n_grams(input_list, n):
  return list(zip(*[input_list[i:] for i in range(n)]))


with open('df_data') as f:
  df_data = f.read()
df_data = [ast.literal_eval(line) for line in df_data.split('\n')[:-1]]
df_keys, df_data = df_data[0], df_data[1:]
df_data = [dict(zip(df_keys, line)) for line in df_data]  # create list of dicts of samples

scale_to = [0, 1]
rate = 20
time_in_future = int(.3 * rate)  # in seconds
print('Time in future: {}'.format(time_in_future))

# Filter data
print('Total samples: {}'.format(len(df_data)))
df_data = [line for line in df_data if line['v_ego'] > CV.MPH_TO_MS * 5.]
df_data = [line for line in df_data if None not in [line['v_lead'], line['a_lead'], line['x_lead']]]
df_data = [line for line in df_data if line['x_lead'] / line['v_ego'] < 3]

df_data_sections = [[]]
for idx, line in enumerate(df_data):
  if not idx:
    continue
  if line['time'] - df_data[idx - 1]['time'] > .1:
    df_data_sections.append([])
  df_data_sections[-1].append(line)

df_data_sequences = []
for sec in df_data_sections:
  tokenized = n_grams(sec, time_in_future)
  if len(tokenized):
    for sec in tokenized:
      df_data_sequences.append(sec)

TRAIN = True
if TRAIN:
  print('Training on {} samples.'.format(len(df_data_sequences)))

  inputs = ['v_lead', 'a_lead', 'v_ego', 'a_ego']

  # x_train = [[line[0][key] for key in inputs] for line in df_data_sequences]
  x_train = [[line[key] for key in inputs] for line in df_data]
  # y_train = [[line[-1]['x_lead'] / line[-1]['v_ego']] for line in df_data_sequences]
  y_train = [[line['x_lead'] / line['v_ego']] for line in df_data]

  x_train, y_train = np.array(x_train), np.array(y_train)

  scales = {}
  for idx, inp in enumerate(inputs):
    _inp_data = x_train.take(indices=idx, axis=1)
    scales[inp] = np.min(_inp_data), np.max(_inp_data)

  x_train_normalized = []
  for idx, inp in enumerate(inputs):
    x_train_normalized.append(np.interp(x_train.take(indices=idx, axis=1), scales[inp], scale_to))
  x_train_normalized = np.array(x_train_normalized).T

  # sns.distplot(y_train.reshape(-1))

  model = Sequential()
  model.add(Dense(32, input_shape=x_train.shape[1:], activation='relu'))
  model.add(Dense(32, activation='relu'))
  model.add(Dense(24, activation='relu'))
  # model.add(Dropout(0.1))
  # model.add(Dense(64, activation='relu'))
  # model.add(Dropout(0.1))
  model.add(Dense(16, activation='relu'))
  model.add(Dense(1))

  opt = Adam(lr=0.001, amsgrad=True)

  model.compile(opt, loss='mse', metrics=['mae'])
  model.fit(x_train_normalized, y_train,
            epochs=100,
            batch_size=42,
            validation_split=0.1,
            )

  test_samples = np.random.choice(range(len(x_train_normalized)), 100)
  x_test = x_train_normalized[test_samples]
  y_test = y_train[test_samples]
  y_pred = model.predict(x_test)
  plt.plot(range(len(x_test)), y_test, label='ground truth')
  plt.plot(range(len(x_test)), y_pred, label='prediction')
  plt.legend()
  plt.show()

  model.save('df_model_v2.h5')

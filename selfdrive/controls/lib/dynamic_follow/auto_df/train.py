import os
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam, Adadelta
import tensorflow as tf
import numpy as np
import seaborn as sns
import ast
from selfdrive.config import Conversions as CV

os.chdir(os.getcwd())

with open('df_data') as f:
  df_data = f.read()
df_data = [ast.literal_eval(line) for line in df_data.split('\n')[:-1]]
df_keys, df_data = df_data[0], df_data[1:]
df_data = [dict(zip(df_keys, line)) for line in df_data]  # create list of dicts of samples


# Filter data
print('Total samples: {}'.format(len(df_data)))
df_data = [line for line in df_data if line['v_ego'] > CV.MPH_TO_MS * 2.5]
df_data = [line for line in df_data if None not in [line['v_lead'], line['a_lead'], line['x_lead']]]
df_data = [line for line in df_data if line['x_lead'] / line['v_ego'] < 8]
print('Training on {} samples.'.format(len(df_data)))


x_train = [[line['v_lead'], line['a_lead'], line['x_lead']] for line in df_data]
y_train = [[line['x_lead'] / line['v_ego']] for line in df_data]
x_train, y_train = np.array(x_train), np.array(y_train)

# sns.distplot(y_train.reshape(-1))

model = Sequential()
model.add(Dense(8, input_shape=x_train.shape[1:], activation='relu'))
model.add(Dense(16, activation='relu'))
model.add(Dense(32, activation='relu'))
model.add(Dense(32, activation='relu'))
model.add(Dense(16, activation='relu'))
model.add(Dense(1))

opt = Adam(lr=0.01, amsgrad=True)

model.compile(opt, loss='mse', metrics=['mae'])
model.fit(x_train, y_train,
          epochs=15,
          batch_size=16,
          validation_split=0.2,
          )

test_samples = np.random.choice(range(len(x_train)), 30)
x_test = x_train[test_samples]
y_test = y_train[test_samples]
y_pred = model.predict(x_test)
plt.plot(range(len(x_test)), y_test, label='ground truth')
plt.plot(range(len(x_test)), y_pred, label='prediction')
plt.legend()
plt.show()


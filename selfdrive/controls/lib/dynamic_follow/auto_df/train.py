import os
import matplotlib.pyplot as plt
import tensorflow as tf
import numpy as np
import seaborn as sns
import ast


os.chdir(os.getcwd())

with open('/df_data') as f:
  df_data = f.read()


df_data = [ast.literal_eval(line) for line in df_data.split('\n')[:-1]]


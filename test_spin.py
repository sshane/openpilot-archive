import time
from common.spinner import Spinner

spinner = Spinner()

for i in range(20):
  spinner.update("30")
time.sleep(0.17)
spinner.update("ERR,Test error")
print('shown error!', flush=True)
time.sleep(10)

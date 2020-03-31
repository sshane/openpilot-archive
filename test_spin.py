import time
from common.spinner import Spinner

spinner = Spinner()


for i in range(5):
  time.sleep(1)
  spinner.update("%d" % (i * 10))
spinner.update("ERR,Test error")
print('shown error!', flush=True)
time.sleep(10)

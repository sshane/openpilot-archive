import time
from common.spinner import Spinner

spinner = Spinner()

time.sleep(2)
spinner.update("30")
# time.sleep(0.17)
spinner.update("ERR,Test error")
print('shown error!', flush=True)
time.sleep(10)

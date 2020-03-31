import time
from common.spinner import Spinner

spinner = Spinner()

time.sleep(2)
spinner.update("30")
time.sleep(1)
spinner.update("ERR,Test error")
print('shown error!', flush=True)
time.sleep(5)

spinner.update("ERR,Test error2")
time.sleep(10)

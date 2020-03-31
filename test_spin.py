import time
from common.spinner import Spinner

spinner = Spinner()

spinner.update("30")
time.sleep(0.16)
spinner.update("ERR,Test error")
print('shown error!', flush=True)
time.sleep(10)

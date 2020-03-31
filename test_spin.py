import time
from common.spinner import Spinner

spinner = Spinner()

time.sleep(2)
spinner.update("30")
spinner.update("ERR,Test error")
spinner.update("ERR,Test error2")
print('shown error!', flush=True)
time.sleep(10)

# spinner.update("ERR,Test error2")
# time.sleep(10)

import time
from common.spinner import Spinner

spinner = Spinner()

spinner.update("30")
time.sleep(0.5)
spinner.update("90")
print('shown error!', flush=True)
time.sleep(10)

**How to run SNPE 1.25.1.310 on the EON:**

First we'll create a backup of the current `LD_LIBRARY_PATH` so that in the event of an error, we can reboot and the library path will be reset.

1. `mount -o remount,rw /system`
2. `cp -a /system/comma/usr/lib/. /system/comma/usr/lib_tmp`
3. `export LD_LIBRARY_PATH=/system/comma/usr/lib_tmp`
4. `cp /data/openpilot/selfdrive/snpe125/libs/libSNPE.so /system/comma/usr/lib_tmp/`

Then you can cd into `/data/openpilot/selfdrive/snpe125` and run `python test.py` to test SNPE 1.25 on a 1.25 model.
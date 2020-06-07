Dynamic lane speed
-----
*This feature is disabled until I can figure out how to improve it. Probably going to be replaced by comma's upcoming end 2 end long model.*

This is a feature that reduces your cruising speed if many vehicles around you are significantly slower than you. This works with and without an openpilot-identified lead. Ex.: It will slow you down if traveling in an open lane with cars in adjacent lanes that are slower than you. Or if the lead in front of the lead is slowing down, as well as cars in other lanes far ahead. The most it will slow you down is some average of: (the set speed and the average of the surrounding cars) The more the radar points, the more weight goes to the speeds of surrounding vehicles.

Custom wheel offset to reduce lane hugging
-----
***Update**: The performance of this modification is iffy at best, but it definitely is more apparent than just tuning your camera offset value. Removing the immediate angle offset can have some weird oscillating effect when it's windy or on roads with camber (slant to one side). Will be left in, but disabled by default.*

With the `LaneHugging` module you can specify a custom angle offset to be added to your desired steering angle. Simply find the angle your wheel is at when you're driving on a straight highway. By default, this is disabled, to enable you can:
- Use the `opEdit` class in the root directory of openpilot. To use it, simply open an `ssh` shell and enter the commands below:
    ```python
    cd /data/openpilot
    python op_edit.py
    ```
    You'll be greeted with a list of your parameters you can explore, enter the number corresponding to `lane_hug_direction`. Your options are to enter `'left'` or `'right'` for whichever direction your car has a tendency to hug toward. `None` will disable the feature.
    Finally you'll need to enter your absolute angle offset (negative will be converted to positive) with the `opParams` parameter: `lane_hug_angle_offset`.
    
    The lane hugging mod is enabled only if `lane_hug_direction` is `'left'` or `'right'`. **Warning: the learned steering offset from openpilot will no longer be used if this mod is active.**

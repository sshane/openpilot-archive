Shane's Stock Additions (0.6.6)
=====

This branch is simply stock openpilot with some additions to help it drive as smooth as possible on my 2017 Toyota Corolla.


Highlight Features
====

1. **Dynamic gas**: This aims to provide a smoother driving experience in stop and go traffic by modifying the maximum gas that can be applied based on your current velocity and the relative velocity of the lead car. It'll also of course increase the maximum gas when the lead is accelerating to help you get up to speed quicker than stock. And smoother; this eliminates the jerking you get from stock openpilot with comma pedal. Better tuning will be next.
2. **Dynamic follow**: This is my dynamic follow from 0.5, where it changes your TR (following distance) dynamically based on multiple vehicle factors, as well as data from the lead vehicle. [Here's an old write up from a while ago explaining how it works exactly. Some of it might be out of date, but how it functions is the same.](https://github.com/ShaneSmiskol/openpilot/blob/dynamic-follow/README.md)
3. **Tuning to reduce lane hugging**: From a suggestion from [zorrobyte](https://github.com/zorrobyte), I'm using some logic to reduce the decision steering angle for the respective direction that my car is hugging (left). By default, this is disabled, to enable you can:
    - Use the `opEdit` class in the root directory of openpilot. To use it, simply open an `ssh` shell and enter the commands below:
        ```python
        cd /data/openpilot
        python op_edit.py
        ```
        You'll be greeted with a list of your parameters you can change or delete, enter the number corresponding to `lane_hug_direction`. Your options are to now enter `'left'` or `'right'` for whichever direction your car has a tendency to hug toward. `None` will disable the feature.
        Further modification is available with the `op_params` variables: `lane_hug_mod`, and `lane_hug_angle`.
4. **Custom following distance**: Using the `following_distance` parameter in `opParams`, you can specify a custom TR value to always be used. Afraid of technology and want to give yourself the highest following distance out there? Try out 2.7s! Are you daredevil and don't care about pissing off the car you're tailgating ahead? Try 0.9s!
    - Again, you can use `opEdit` to change this:
        ```python
        cd /data/openpilot
        python op_edit.py
        ```
        Then enter the number for the `following_distance` parameter and set to a float or integer between `0.9` and `2.7`. `None` will use dynamic follow!
5. **opParams Parameter class**: Here you can specify parameters to be used in any fork's operation that supports `opParams`. First, ssh in to your EON and make sure you're in `/data/openpilot`, then open a Python shell. Here's an example:
    ```python
    from common.op_params import opParams
    op_params = opParams()
    op_params.get('cameraOffset')
    ```
    returns `0.06`

    ```python
    op_params.put('cameraOffset', -0.01)
    op_params.get('cameraOffset')
    ```
    returns `-0.01`

    Parameters are stored at `/data/op_params.json`

Shane's Stock Additions (0.6.3)
=====

This branch is simply stock openpilot with some additions to help it drive as smooth as possible on my 2017 Toyota Corolla.


Highlight Features
====

* **Dynamic gas**: Ripped from my dynamic gas modification on [Arne's fork](https://github.com/arne182/openpilot), this aims to provide a smoother driving experience in stop and go traffic by changing the maximum gas that can be applied based on your current velocity and the relative velocity of the lead car. It'll also of course increase the maximum gas when the lead is accelerating to help you get up to speed quicker than stock. And hopefully smoother. Better tuning and more factors to calculate from will be next.
* **INDI lateral control for Corolla**: After trying INDI on my Corolla for only a short time, I'm in love. Everything seems a whole lot smoother than `latcontrol_pid` in curves, and lane centering. So this is being used here.
* **Tuning to reduce lane hugging**: From a suggestion from [zorrobyte](https://github.com/zorrobyte), I'm using some logic in `latcontrol_indi` to reduce the decision angle steers for the respective direction that my car is lane hugging (left). By default, this is disabled, to enable you can either 
1. Use the `opParams` class in `selfdrive.op_params` to set your `lane_hug_direction` parameter to `left` or `right` or `none`. First cd into `/data/openpilot` then run
    ```python
    python
    from selfdrive.op_params import opParams
    op_params = opParams()
    op_params.put('lane_hug_direction', 'left') #  or right, none
    ```

2. modify [this line in `latcontrol_indi`](https://github.com/ShaneSmiskol/openpilot/blob/stock_additions/selfdrive/controls/lib/latcontrol_indi.py#L48) so that the default value is `left` or `right`, whichever direction your car is hugging.

    Further modification is available with the `op_params` variables: `lane_hug_mod`, and `lane_hug_angle`.
* **opParams Parameter class**: Here you can specify parameters to automatically be used in openpilot's operation. First, ssh in to your EON and make sure you're in `/data/openpilot`, then open a Python shell. Here's an example:
    ```python
    from selfdrive.op_params import opParams
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

[![](https://i.imgur.com/UetIFyH.jpg)](#)

Welcome to openpilot by Arne Schwarck
https://youtu.be/WKwSq8TPdpo
======

[openpilot](http://github.com/commaai/openpilot) is an open source driving agent. Currently, it performs the functions of Adaptive Cruise Control (ACC) and Lane Keeping Assist System (LKAS) for selected Honda, Toyota, Acura, Lexus, Chevrolet, Hyundai, Kia. It's about on par with Tesla Autopilot and GM Super Cruise, and better than [all other manufacturers](http://www.thedrive.com/tech/5707/the-war-for-autonomous-driving-part-iii-us-vs-germany-vs-japan).

Features
=======================

* Automatic Lane Change Assist (ALC): Check your surroudings, signal in the direction you would like to change lanes, and let openpilot do the rest. You can choose between three ALC profiles, [Normal, Wifey, and Mad Max](/openpilot/blob/release2/selfdrive/car/toyota/carstate.py#L145). Each increasing in steering torque.

#!/usr/bin/bash

apk_dir="/data/communitypilot_scripts"
if [ ! -d $apk_dir ]
then
  echo "$apk_dir does not exist, installing"
  curl -L https://raw.githubusercontent.com/pjlao307/communitypilot-apk-dist/master/install.py | python
else
  echo "APK already installed"
fi

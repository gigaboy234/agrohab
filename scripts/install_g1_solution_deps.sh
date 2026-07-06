#!/bin/bash
set -e
sudo apt-get update
sudo apt-get install -y git python3-pip python3-dev python3-numpy python3-opencv iproute2 net-tools psmisc
sudo apt-get install -y ros-foxy-rmw-cyclonedds-cpp ros-foxy-geometry-msgs ros-foxy-sensor-msgs ros-foxy-std-srvs ros-foxy-tf2-ros ros-foxy-cv-bridge ros-foxy-image-tools || true
sudo apt-get install -y ros-foxy-realsense2-camera || true
python3 -m pip install --user --upgrade pip setuptools wheel
python3 -m pip install --user ultralytics
if ! python3 - <<'PY2'
import unitree_sdk2py
PY2
then
  cd ~
  [ -d ~/unitree_sdk2_python ] || git clone https://github.com/unitreerobotics/unitree_sdk2_python.git
  cd ~/unitree_sdk2_python
  python3 -m pip install --user -e .
fi

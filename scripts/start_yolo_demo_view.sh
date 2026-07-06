#!/bin/bash
set -e
source ~/env_sensor_foxy.sh
ros2 run image_tools showimage --ros-args --remap image:=/demo/yolo_image

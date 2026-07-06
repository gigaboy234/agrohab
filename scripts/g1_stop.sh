#!/bin/bash
set -e
source ~/env_sensor_foxy.sh
python3 ~/publish_cmd_vel_raw_burst.py --ros-args -p topic:=/cmd_vel_raw -p duration_s:=0.10 -p linear_x:=0.0 -p linear_y:=0.0 -p angular_z:=0.0 -p rate_hz:=20.0 -p stop_count:=30

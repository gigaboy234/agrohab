#!/bin/bash
set -e
source ~/env_sensor_foxy.sh
ros2 launch realsense2_camera rs_launch.py serial_no:=_347522071733 initial_reset:=false enable_color:=true enable_depth:=true enable_infra1:=false enable_infra2:=false enable_gyro:=false enable_accel:=false enable_sync:=false align_depth.enable:=false rgb_camera.profile:=640x480x15 depth_module.profile:=640x480x15

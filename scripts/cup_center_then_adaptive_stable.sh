#!/bin/bash
set -e
source ~/env_sensor_foxy.sh
python3 ~/cup_center_then_adaptive_node.py --ros-args -p cup_topic:=/perception/cup_pose_map -p cmd_topic:=/cmd_vel_raw -p dry_run:=false -p vx:=0.30 -p far_x_m:=1.60 -p mid_x_m:=1.35 -p stop_x_m:=1.25 -p pulse_far_s:=0.60 -p pulse_mid_s:=0.45 -p pulse_near_s:=0.20 -p center_y_deadband_m:=0.12 -p max_abs_y_m:=0.45 -p yaw_rate:=0.20 -p yaw_pulse_s:=0.25 -p yaw_sign:=1.0 -p pause_after_pulse_s:=1.0 -p pose_timeout_s:=1.5 -p max_actions:=14 -p timer_hz:=20.0

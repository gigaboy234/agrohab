#!/bin/bash
set -e
source ~/env_sensor_foxy.sh
python3 ~/ros_cmd_vel_udp_exporter.py --ros-args -p input_topic:=/cmd_vel_raw -p udp_host:=127.0.0.1 -p udp_port:=15000 -p max_linear_x:=0.30 -p max_linear_y:=0.00 -p max_angular_z:=0.30

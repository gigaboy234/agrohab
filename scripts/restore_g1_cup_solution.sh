#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cp -av "$DIR/"* ~/
chmod +x ~/*.sh ~/cup_*_node.py ~/g1_*receiver*.py ~/ros_cmd_vel_udp_exporter.py ~/publish_cmd_vel_raw_burst.py ~/yolo26_cup_pose_node.py ~/temporary_tf_direct_camera_optical.py
~/check_g1_solution_deps.sh

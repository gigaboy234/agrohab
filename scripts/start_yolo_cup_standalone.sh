#!/bin/bash
set -e
source ~/env_sensor_foxy.sh
python3 ~/yolo26_cup_pose_node.py --ros-args -p model_path:=$HOME/g1_robot_delivery_solution_foxy/models/yolo26n.pt -p target_class:=cup -p confidence:=0.15 -p color_topic:=/camera/color/image_raw -p depth_topic:=/camera/depth/image_rect_raw -p camera_info_topic:=/camera/color/camera_info -p map_frame:=map -p process_every_n:=1 -p publish_demo_image:=true -p show_window:=false -p map_y_sign:=-1.0

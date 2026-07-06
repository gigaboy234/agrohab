#!/bin/bash
source ~/env_sensor_foxy.sh
sudo pkill -9 -f realsense2_camera_node || true
sudo pkill -9 -f "ros2 launch realsense2_camera" || true
sudo pkill -9 -f yolo26_cup_pose_node || true
sudo pkill -9 -f temporary_tf_direct_camera_optical.py || true
sudo pkill -9 -f yolo_realtime_demo_node.py || true
sudo pkill -9 -f ros_cmd_vel_udp_exporter.py || true
sudo pkill -9 -f g1_sdk_udp_receiver_fsm801.py || true
sudo pkill -9 -f cup_approach_mapx_pulse_debug_node.py || true
sudo pkill -9 -f cup_center_then_adaptive_node.py || true
sudo pkill -9 -f publish_cmd_vel_raw_burst.py || true
sudo fuser -k -n udp 15000 || true
killall -9 _ros2_daemon || true
sleep 2
ps -ef | grep -E "realsense|yolo26|temporary_tf|ros_cmd_vel_udp|g1_sdk_udp|cup_approach|cup_center|publish_cmd" | grep -v grep || true
ss -lunp | grep 15000 || true

#!/bin/bash
set -e
source ~/env_sensor_foxy.sh
echo "=== cup pose ==="; timeout 5 ros2 topic echo /perception/cup_pose_map || true
echo "=== /cmd_vel_raw graph ==="; ros2 topic info /cmd_vel_raw -v || true
echo "=== UDP 15000 listener ==="; ss -lunp | grep 15000 || echo "NO UDP LISTENER ON 15000"
echo "=== services ==="; ros2 service list | grep cup_approach || true

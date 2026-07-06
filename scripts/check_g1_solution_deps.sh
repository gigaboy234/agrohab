#!/bin/bash
echo "=== G1 CUP SOLUTION DEPENDENCY CHECK ==="
if [ -f /opt/ros/foxy/setup.bash ]; then source /opt/ros/foxy/setup.bash; echo "OK: ROS Foxy"; else echo "MISSING: ROS Foxy"; fi
which ros2 || echo "MISSING: ros2"
for p in rmw_cyclonedds_cpp geometry_msgs sensor_msgs std_srvs tf2_ros cv_bridge realsense2_camera image_tools; do
  ros2 pkg prefix "$p" >/dev/null 2>&1 && echo "OK: ros2 $p" || echo "MISSING: ros2 $p"
done
python3 - <<'PY2'
mods=['rclpy','geometry_msgs.msg','sensor_msgs.msg','std_srvs.srv','cv2','numpy','cv_bridge','ultralytics']
for m in mods:
    try: __import__(m); print('OK:',m)
    except Exception as e: print('MISSING:',m,repr(e))
PY2
# unitree_sdk2py проверяем в чистом окружении (без ROS в LD_LIBRARY_PATH),
# как его и запускает g1_receiver_fsm801_stable.sh
env -i HOME="$HOME" PATH="$HOME/.local/bin:/usr/bin:/bin" python3 -c \
  'import unitree_sdk2py; print("OK: unitree_sdk2py (clean env)")' \
  || echo "MISSING: unitree_sdk2py (clean env)"
[ -d ~/unitree_sdk2_python ] && echo "OK: ~/unitree_sdk2_python" || echo "MISSING: ~/unitree_sdk2_python"
[ -f ~/g1_robot_delivery_solution_foxy/models/yolo26n.pt ] && echo "OK: YOLO model" || echo "MISSING: ~/g1_robot_delivery_solution_foxy/models/yolo26n.pt"
source ~/env_g1_motion_foxy.sh >/dev/null 2>&1 || true
echo "UNITREE_NET_IFACE=$UNITREE_NET_IFACE"
ip route get 192.168.123.161 || true
ping -c 2 192.168.123.161 || true

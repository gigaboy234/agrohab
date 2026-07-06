#!/bin/bash
set -e
source ~/env_sensor_foxy.sh
ros2 service call /cup_approach_x/start std_srvs/srv/Trigger {}

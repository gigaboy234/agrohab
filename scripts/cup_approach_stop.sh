#!/bin/bash
set -e
source ~/env_sensor_foxy.sh
ros2 service call /cup_approach_x/stop std_srvs/srv/Trigger {} || true
~/g1_stop.sh || true

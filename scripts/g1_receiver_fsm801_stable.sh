#!/bin/bash
set -e
source ~/env_g1_motion_foxy.sh
python3 ~/g1_sdk_udp_receiver_fsm801.py --iface eth0 --udp-host 127.0.0.1 --udp-port 15000 --fsm 801 --max-linear-x 0.30 --max-linear-y 0.00 --max-angular-z 0.30 --send-rate-hz 20.0 --cmd-timeout-s 0.90

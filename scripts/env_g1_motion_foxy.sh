#!/bin/bash
# ВАЖНО: НЕ сорсим ROS Foxy — его LD_LIBRARY_PATH подменяет libddsc,
# и pip-cyclonedds 0.10.2 (нужен unitree_sdk2py) падает с undefined symbol.
# Ресиверу ROS не нужен: он общается с ROS-частью только через UDP.
ROBOT_IP="${UNITREE_ROBOT_IP:-192.168.123.161}"
IFACE="$(ip route get "$ROBOT_IP" 2>/dev/null | awk '{for(i=1;i<=NF;i++){if($i=="dev"){print $(i+1); exit}}}')"
if [ -z "$IFACE" ]; then IFACE="${UNITREE_NET_IFACE:-eth0}"; fi
export UNITREE_NET_IFACE="$IFACE"
cat > /tmp/cyclonedds_g1_motion.xml <<XML
<CycloneDDS>
  <Domain id="any">
    <General>
      <Interfaces><NetworkInterface name="$IFACE" multicast="true"/></Interfaces>
      <AllowMulticast>true</AllowMulticast>
    </General>
  </Domain>
</CycloneDDS>
XML
export CYCLONEDDS_URI=file:///tmp/cyclonedds_g1_motion.xml
echo "UNITREE_NET_IFACE=$UNITREE_NET_IFACE"

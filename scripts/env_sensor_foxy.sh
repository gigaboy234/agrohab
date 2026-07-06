#!/bin/bash
if [ -f /opt/ros/foxy/setup.bash ]; then source /opt/ros/foxy/setup.bash; fi
if [ -f ~/g1_foxy_ws/install/setup.bash ]; then source ~/g1_foxy_ws/install/setup.bash; fi
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-77}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"
cat > /tmp/cyclonedds_lo.xml <<'XML'
<CycloneDDS>
  <Domain id="any">
    <General>
      <!-- старый синтаксис: CycloneDDS 0.7 (стоковый Foxy) не знает <Interfaces>/<NetworkInterface>.
           Мультикаст нужен для discovery; на lo он требует "ip link set lo multicast on"
           (включено юнитом lo-multicast.service) -->
      <NetworkInterfaceAddress>lo</NetworkInterfaceAddress>
      <AllowMulticast>true</AllowMulticast>
    </General>
  </Domain>
</CycloneDDS>
XML
export CYCLONEDDS_URI=file:///tmp/cyclonedds_lo.xml

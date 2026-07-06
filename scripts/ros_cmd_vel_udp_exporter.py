#!/usr/bin/env python3
import json, socket, time, rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
def clamp(v,lo,hi): return max(lo,min(hi,v))
class RosCmdVelUdpExporter(Node):
    def __init__(self):
        super().__init__('ros_cmd_vel_udp_exporter')
        for k,v in {'input_topic':'/cmd_vel_raw','udp_host':'127.0.0.1','udp_port':15000,'max_linear_x':0.30,'max_linear_y':0.00,'max_angular_z':0.30}.items(): self.declare_parameter(k,v)
        self.input_topic=self.get_parameter('input_topic').value; self.udp_host=self.get_parameter('udp_host').value; self.udp_port=int(self.get_parameter('udp_port').value); self.max_linear_x=float(self.get_parameter('max_linear_x').value); self.max_linear_y=float(self.get_parameter('max_linear_y').value); self.max_angular_z=float(self.get_parameter('max_angular_z').value)
        self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); self.last_log_t=0.0; self.create_subscription(Twist,self.input_topic,self.cb,10)
        self.get_logger().info('ROS cmd_vel UDP exporter: %s -> udp://%s:%d max_x=%.3f max_w=%.3f'%(self.input_topic,self.udp_host,self.udp_port,self.max_linear_x,self.max_angular_z))
    def cb(self,msg):
        vx=clamp(float(msg.linear.x),-self.max_linear_x,self.max_linear_x); vy=clamp(float(msg.linear.y),-self.max_linear_y,self.max_linear_y); wz=clamp(float(msg.angular.z),-self.max_angular_z,self.max_angular_z)
        self.sock.sendto(json.dumps({'vx':vx,'vy':vy,'wz':wz,'t':time.time()}).encode(),(self.udp_host,self.udp_port))
        now=time.time()
        if abs(vx)>1e-4 or abs(vy)>1e-4 or abs(wz)>1e-4 or now-self.last_log_t>0.5: self.get_logger().info('UDP sent vx=%.3f vy=%.3f wz=%.3f'%(vx,vy,wz)); self.last_log_t=now
def main():
    rclpy.init(); n=RosCmdVelUdpExporter()
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally: n.destroy_node(); rclpy.shutdown()
if __name__=='__main__': main()

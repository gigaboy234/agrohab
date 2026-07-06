#!/usr/bin/env python3
import time, rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

def clamp(v,lo,hi): return max(lo,min(hi,v))
class SafetyTwistFilterPulse(Node):
    def __init__(self):
        super().__init__('safety_twist_filter_pulse')
        for k,v in {'input_topic':'/cmd_vel_raw','output_topic':'/cmd_vel','max_linear_x':0.30,'max_linear_y':0.00,'max_angular_z':0.30,'deadman_timeout_s':0.35,'repeat_rate_hz':20.0}.items(): self.declare_parameter(k,v)
        self.input_topic=self.get_parameter('input_topic').value; self.output_topic=self.get_parameter('output_topic').value; self.max_linear_x=float(self.get_parameter('max_linear_x').value); self.max_linear_y=float(self.get_parameter('max_linear_y').value); self.max_angular_z=float(self.get_parameter('max_angular_z').value); self.deadman_timeout_s=float(self.get_parameter('deadman_timeout_s').value); self.repeat_rate_hz=float(self.get_parameter('repeat_rate_hz').value)
        self.pub=self.create_publisher(Twist,self.output_topic,10); self.last_msg=Twist(); self.last_rx=0.0; self.create_subscription(Twist,self.input_topic,self.cb,10); self.timer=self.create_timer(1.0/max(self.repeat_rate_hz,1.0),self.tick)
        self.get_logger().info('SafetyTwistFilterPulse: %s -> %s max_x=%.3f max_y=%.3f max_w=%.3f deadman=%.2f'%(self.input_topic,self.output_topic,self.max_linear_x,self.max_linear_y,self.max_angular_z,self.deadman_timeout_s))
    def cb(self,msg):
        out=Twist(); out.linear.x=clamp(msg.linear.x,-self.max_linear_x,self.max_linear_x); out.linear.y=clamp(msg.linear.y,-self.max_linear_y,self.max_linear_y); out.angular.z=clamp(msg.angular.z,-self.max_angular_z,self.max_angular_z); self.last_msg=out; self.last_rx=time.time(); self.pub.publish(out)
        if abs(out.linear.x)>1e-4 or abs(out.angular.z)>1e-4: self.get_logger().info('PASS x=%.3f wz=%.3f'%(out.linear.x,out.angular.z))
        else: self.get_logger().info('PASS STOP', throttle_duration_sec=0.5)
    def tick(self):
        if self.last_rx and time.time()-self.last_rx>self.deadman_timeout_s: self.pub.publish(Twist())

def main():
    rclpy.init(); n=SafetyTwistFilterPulse()
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally: n.destroy_node(); rclpy.shutdown()
if __name__=='__main__': main()

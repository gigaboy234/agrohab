#!/usr/bin/env python3
import time, rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
class BurstPublisher(Node):
    def __init__(self):
        super().__init__('publish_cmd_vel_raw_burst')
        for k,v in {'topic':'/cmd_vel_raw','duration_s':0.5,'linear_x':0.0,'linear_y':0.0,'angular_z':0.0,'rate_hz':20.0,'stop_count':20}.items(): self.declare_parameter(k,v)
        self.topic=self.get_parameter('topic').value; self.duration_s=float(self.get_parameter('duration_s').value); self.linear_x=float(self.get_parameter('linear_x').value); self.linear_y=float(self.get_parameter('linear_y').value); self.angular_z=float(self.get_parameter('angular_z').value); self.rate_hz=float(self.get_parameter('rate_hz').value); self.stop_count=int(self.get_parameter('stop_count').value)
        self.pub=self.create_publisher(Twist,self.topic,10)
    def run(self):
        print('=== CMD_VEL_RAW BURST ==='); print(f'topic={self.topic} duration={self.duration_s:.2f} linear.x={self.linear_x:.3f} linear.y={self.linear_y:.3f} angular.z={self.angular_z:.3f}')
        msg=Twist(); msg.linear.x=self.linear_x; msg.linear.y=self.linear_y; msg.angular.z=self.angular_z
        period=1.0/max(self.rate_hz,1.0); end=time.time()+self.duration_s
        while rclpy.ok() and time.time()<end:
            self.pub.publish(msg); print(f'PUB RAW x={msg.linear.x:.3f} y={msg.linear.y:.3f} wz={msg.angular.z:.3f}'); rclpy.spin_once(self,timeout_sec=0.0); time.sleep(period)
        stop=Twist(); print('Publishing STOP...')
        for _ in range(self.stop_count): self.pub.publish(stop); rclpy.spin_once(self,timeout_sec=0.0); time.sleep(period)
        print('DONE')
def main():
    rclpy.init(); n=BurstPublisher()
    try: n.run()
    finally: n.destroy_node(); rclpy.shutdown()
if __name__=='__main__': main()

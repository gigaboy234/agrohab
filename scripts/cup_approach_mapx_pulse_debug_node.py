#!/usr/bin/env python3
# One-zone pulse node kept for regression tests. Use center+adaptive for current stage.
import time, rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Twist
from std_srvs.srv import Trigger
class Pulse(Node):
    def __init__(self):
        super().__init__('cup_approach_mapx_pulse_debug_node')
        for k,v in {'cup_topic':'/perception/cup_pose_map','cmd_topic':'/cmd_vel_raw','dry_run':False,'vx':0.30,'pulse_duration_s':0.60,'pause_after_pulse_s':1.0,'stop_x_m':1.20,'max_abs_y_m':0.35,'pose_timeout_s':1.5,'max_pulses':3,'timer_hz':20.0}.items(): self.declare_parameter(k,v)
        for k in ['cup_topic','cmd_topic','dry_run','vx','pulse_duration_s','pause_after_pulse_s','stop_x_m','max_abs_y_m','pose_timeout_s','max_pulses','timer_hz']: setattr(self,k,self.get_parameter(k).value)
        self.vx=float(self.vx); self.pulse_duration_s=float(self.pulse_duration_s); self.pause_after_pulse_s=float(self.pause_after_pulse_s); self.stop_x_m=float(self.stop_x_m); self.max_abs_y_m=float(self.max_abs_y_m); self.pose_timeout_s=float(self.pose_timeout_s); self.max_pulses=int(self.max_pulses)
        self.last_pose=None; self.last_pose_t=None; self.active=False; self.state='IDLE'; self.state_t=time.time(); self.pulses=0; self.pub=self.create_publisher(Twist,self.cmd_topic,10); self.create_subscription(PoseStamped,self.cup_topic,self.pose_cb,10); self.create_service(Trigger,'/cup_approach_x/start',self.start); self.create_service(Trigger,'/cup_approach_x/stop',self.stop); self.timer=self.create_timer(1.0/float(self.timer_hz),self.tick); self.get_logger().warn('DEBUG CupApproachMapX ready')
    def pose_cb(self,m): self.last_pose=m; self.last_pose_t=time.time()
    def fresh(self): return self.last_pose_t and time.time()-self.last_pose_t<=self.pose_timeout_s
    def xyz(self): p=self.last_pose.pose.position; return float(p.x),float(p.y),float(p.z)
    def start(self,req,resp): self.active=True; self.state='CHECK'; self.pulses=0; self.pub.publish(Twist()); resp.success=True; resp.message='debug cup approach by map.x started'; self.get_logger().warn('START map.x approach'); return resp
    def stop(self,req,resp): self.active=False; self.state='IDLE'; self.pub.publish(Twist()); resp.success=True; resp.message='debug cup approach by map.x stopped'; return resp
    def tick(self):
        if not self.active: return
        now=time.time()
        if self.state=='CHECK':
            if not self.fresh(): self.get_logger().warn('No fresh cup_pose_map. Waiting...', throttle_duration_sec=1.0); return
            x,y,z=self.xyz(); self.get_logger().info('Cup map pose: x=%.3f y=%.3f z=%.3f pulses=%d/%d'%(x,y,z,self.pulses,self.max_pulses), throttle_duration_sec=0.5)
            if x<=self.stop_x_m or abs(y)>self.max_abs_y_m or self.pulses>=self.max_pulses: self.active=False; self.pub.publish(Twist()); self.get_logger().warn('Stop condition reached'); return
            self.pulses+=1; self.state='PULSE'; self.state_t=now; self.get_logger().warn('ENTER PULSE %d/%d vx=%.2f duration=%.2f'%(self.pulses,self.max_pulses,self.vx,self.pulse_duration_s)); return
        if self.state=='PULSE':
            if now-self.state_t<=self.pulse_duration_s:
                if not self.dry_run: msg=Twist(); msg.linear.x=self.vx; self.pub.publish(msg); self.get_logger().warn('PUBLISH FORWARD linear.x=%.3f'%self.vx, throttle_duration_sec=0.05)
                return
            self.pub.publish(Twist()); self.state='PAUSE'; self.state_t=now; return
        if self.state=='PAUSE' and now-self.state_t>=self.pause_after_pulse_s: self.state='CHECK'
def main():
    rclpy.init(); n=Pulse()
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally: n.pub.publish(Twist()); n.destroy_node(); rclpy.shutdown()
if __name__=='__main__': main()

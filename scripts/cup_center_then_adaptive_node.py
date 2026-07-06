#!/usr/bin/env python3
import time, math, rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Twist
from std_srvs.srv import Trigger
class NodeCA(Node):
    def __init__(self):
        super().__init__('cup_center_then_adaptive_node')
        d={'cup_topic':'/perception/cup_pose_map','cmd_topic':'/cmd_vel_raw','dry_run':False,'vx':0.30,'far_x_m':1.60,'mid_x_m':1.35,'stop_x_m':1.25,'pulse_far_s':0.60,'pulse_mid_s':0.45,'pulse_near_s':0.20,'center_y_deadband_m':0.12,'max_abs_y_m':0.45,'yaw_rate':0.20,'yaw_pulse_s':0.25,'yaw_sign':1.0,'pause_after_pulse_s':1.0,'pose_timeout_s':1.5,'max_actions':14,'timer_hz':20.0}
        for k,v in d.items(): self.declare_parameter(k,v)
        for k in d: setattr(self,k,self.get_parameter(k).value)
        for k in ['vx','far_x_m','mid_x_m','stop_x_m','pulse_far_s','pulse_mid_s','pulse_near_s','center_y_deadband_m','max_abs_y_m','yaw_rate','yaw_pulse_s','yaw_sign','pause_after_pulse_s','pose_timeout_s']: setattr(self,k,float(getattr(self,k)))
        self.max_actions=int(self.max_actions); self.last_pose=None; self.last_pose_t=None; self.active=False; self.state='IDLE'; self.state_t=time.time(); self.actions_done=0; self.cmd_type='NONE'; self.cmd_duration=0.0; self.wz=0.0; self.count=0; self.last_y=None
        self.pub=self.create_publisher(Twist,self.cmd_topic,10); self.create_subscription(PoseStamped,self.cup_topic,self.pose_cb,10); self.create_service(Trigger,'/cup_approach_x/start',self.start_cb); self.create_service(Trigger,'/cup_approach_x/stop',self.stop_cb); self.timer=self.create_timer(1.0/float(self.timer_hz),self.tick)
        self.get_logger().warn('CENTER+ADAPTIVE ready: stop_x=%.2f y_deadband=%.2f yaw_sign=%.1f'%(self.stop_x_m,self.center_y_deadband_m,self.yaw_sign))
    def pose_cb(self,m): self.last_pose=m; self.last_pose_t=time.time()
    def fresh(self): return self.last_pose_t and (time.time()-self.last_pose_t)<=self.pose_timeout_s
    def xyz(self): p=self.last_pose.pose.position; return float(p.x),float(p.y),float(p.z)
    def start_cb(self,req,resp): self.active=True; self.state='CHECK'; self.actions_done=0; self.publish_stop('START_PRESTOP'); resp.success=True; resp.message='center then adaptive approach started'; self.get_logger().warn('START CENTER+ADAPTIVE approach'); return resp
    def stop_cb(self,req,resp): self.active=False; self.state='IDLE'; self.publish_stop('SERVICE_STOP'); resp.success=True; resp.message='center then adaptive approach stopped'; return resp
    def choose(self,x):
        if x>self.far_x_m: return self.pulse_far_s,'FAR'
        if x>self.mid_x_m: return self.pulse_mid_s,'MID'
        return self.pulse_near_s,'NEAR'
    def publish_stop(self,reason): self.pub.publish(Twist()); self.get_logger().info('PUBLISH STOP reason=%s'%reason, throttle_duration_sec=0.5)
    def publish_cmd(self):
        m=Twist();
        if self.cmd_type=='FORWARD': m.linear.x=self.vx
        if self.cmd_type=='YAW': m.angular.z=self.wz
        self.pub.publish(m); self.count+=1; self.get_logger().warn('PUBLISH %s #%d: vx=%.3f wz=%.3f duration=%.2fs'%(self.cmd_type,self.count,m.linear.x,m.angular.z,self.cmd_duration), throttle_duration_sec=0.05)
    def tick(self):
        if not self.active: return
        now=time.time()
        if self.state=='CHECK':
            if not self.fresh(): self.get_logger().warn('No fresh cup_pose_map. Waiting...', throttle_duration_sec=1.0); return
            x,y,z=self.xyz(); self.get_logger().info('Cup pose: x=%.3f y=%.3f z=%.3f actions=%d/%d'%(x,y,z,self.actions_done,self.max_actions), throttle_duration_sec=0.5)
            if x<=self.stop_x_m: self.get_logger().warn('DONE: x=%.3f <= stop_x=%.3f. Stop.'%(x,self.stop_x_m)); self.active=False; self.publish_stop('DONE_CLOSE'); return
            if abs(y)>self.max_abs_y_m: self.get_logger().warn('Y too large: y=%.3f. Stop for safety.'%y); self.active=False; self.publish_stop('Y_TOO_LARGE'); return
            if self.actions_done>=self.max_actions: self.get_logger().warn('Max actions reached. Stop.'); self.active=False; self.publish_stop('MAX_ACTIONS'); return
            self.actions_done+=1; self.count=0
            if abs(y)>self.center_y_deadband_m:
                self.cmd_type='YAW'; self.cmd_duration=self.yaw_pulse_s; self.wz=-self.yaw_sign*math.copysign(self.yaw_rate,y); self.last_y=y; self.get_logger().warn('ENTER YAW %d/%d: y=%.3f -> wz=%.3f for %.2fs'%(self.actions_done,self.max_actions,y,self.wz,self.cmd_duration))
            else:
                self.cmd_type='FORWARD'; self.cmd_duration,zone=self.choose(x); self.wz=0.0; self.get_logger().warn('ENTER FORWARD %d/%d zone=%s x=%.3f y=%.3f vx=%.2f duration=%.2fs'%(self.actions_done,self.max_actions,zone,x,y,self.vx,self.cmd_duration))
            self.state='PULSE'; self.state_t=now; return
        if self.state=='PULSE':
            if now-self.state_t<=self.cmd_duration:
                if not self.dry_run: self.publish_cmd()
                return
            self.publish_stop('PULSE_FINISHED'); self.get_logger().warn('%s finished. publish_count=%d. Stop and wait %.2fs'%(self.cmd_type,self.count,self.pause_after_pulse_s)); self.state='PAUSE'; self.state_t=now; return
        if self.state=='PAUSE' and now-self.state_t>=self.pause_after_pulse_s:
            if self.cmd_type=='YAW' and self.fresh() and self.last_y is not None:
                _,ya,_=self.xyz();
                if abs(ya)>abs(self.last_y)+0.03: self.get_logger().warn('WARNING: centering got worse: |y| %.3f -> %.3f. Consider yaw_sign=-1.0'%(abs(self.last_y),abs(ya)))
                else: self.get_logger().warn('Centering check: |y| %.3f -> %.3f'%(abs(self.last_y),abs(ya)))
            self.state='CHECK'; self.state_t=now
def main():
    rclpy.init(); n=NodeCA()
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally:
        try: n.publish_stop('SHUTDOWN')
        except Exception: pass
        n.destroy_node(); rclpy.shutdown()
if __name__=='__main__': main()

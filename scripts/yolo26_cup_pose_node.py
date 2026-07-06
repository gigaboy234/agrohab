#!/usr/bin/env python3
import time, cv2, numpy as np, rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
from ultralytics import YOLO
class Yolo26CupPoseNode(Node):
    def __init__(self):
        super().__init__('yolo26_cup_pose_node')
        for k,v in {'model_path':'/home/unitree/g1_robot_delivery_solution_foxy/models/yolo26n.pt','target_class':'cup','confidence':0.15,'color_topic':'/camera/color/image_raw','depth_topic':'/camera/depth/image_rect_raw','camera_info_topic':'/camera/color/camera_info','map_frame':'map','camera_frame':'camera_color_optical_frame','map_y_sign':-1.0,'publish_demo_image':True,'show_window':False,'process_every_n':1}.items(): self.declare_parameter(k,v)
        self.model_path=self.get_parameter('model_path').value; self.target_class=str(self.get_parameter('target_class').value); self.conf=float(self.get_parameter('confidence').value); self.color_topic=self.get_parameter('color_topic').value; self.depth_topic=self.get_parameter('depth_topic').value; self.info_topic=self.get_parameter('camera_info_topic').value; self.map_frame=self.get_parameter('map_frame').value; self.camera_frame=self.get_parameter('camera_frame').value; self.map_y_sign=float(self.get_parameter('map_y_sign').value); self.publish_demo=bool(self.get_parameter('publish_demo_image').value); self.process_every_n=int(self.get_parameter('process_every_n').value)
        self.bridge=CvBridge(); self.model=YOLO(self.model_path); self.last_depth=None; self.last_info=None; self.frame_count=0; self.last_log_t=time.time(); self.pose_camera_pub=self.create_publisher(PoseStamped,'/perception/cup_pose_camera',10); self.pose_map_pub=self.create_publisher(PoseStamped,'/perception/cup_pose_map',10); self.demo_pub=self.create_publisher(Image,'/demo/yolo_image',10)
        self.create_subscription(Image,self.color_topic,self.color_cb,10); self.create_subscription(Image,self.depth_topic,self.depth_cb,10); self.create_subscription(CameraInfo,self.info_topic,self.info_cb,10); self.get_logger().info('YOLO cup pose node started')
    def info_cb(self,msg): self.last_info=msg
    def depth_cb(self,msg):
        try: self.last_depth=self.bridge.imgmsg_to_cv2(msg)
        except Exception as e: self.get_logger().warn('depth conversion failed: %r'%e)
    def class_matches(self,cls_id,names):
        if self.target_class=='': return True
        if self.target_class.isdigit(): return int(self.target_class)==int(cls_id)
        name=names.get(int(cls_id),str(cls_id)) if isinstance(names,dict) else str(cls_id); return name==self.target_class
    def estimate_depth(self,u,v):
        if self.last_depth is None: return None
        h,w=self.last_depth.shape[:2]; u=int(np.clip(u,0,w-1)); v=int(np.clip(v,0,h-1)); r=4; arr=np.array(self.last_depth[max(0,v-r):min(h,v+r+1),max(0,u-r):min(w,u+r+1)]).astype(np.float32).reshape(-1); arr=arr[np.isfinite(arr)]; arr=arr[arr>0]
        if arr.size==0: return None
        z=float(np.median(arr)); z=z/1000.0 if z>20.0 else z; return z if 0.10<z<10.0 else None
    def color_cb(self,msg):
        self.frame_count+=1
        if self.process_every_n>1 and self.frame_count%self.process_every_n!=0: return
        if self.last_info is None or self.last_depth is None: self.get_logger().warn('waiting for camera_info/depth', throttle_duration_sec=2.0); return
        frame=self.bridge.imgmsg_to_cv2(msg,desired_encoding='bgr8'); result=self.model.predict(source=frame,conf=self.conf,verbose=False)[0]; names=self.model.names; best=None
        if result.boxes is not None:
            for box in result.boxes:
                cls_id=int(box.cls[0]); conf=float(box.conf[0])
                if not self.class_matches(cls_id,names): continue
                x1,y1,x2,y2=[float(v) for v in box.xyxy[0].detach().cpu().numpy()]
                if best is None or conf>best['conf']: best={'conf':conf,'box':(x1,y1,x2,y2)}
        annotated=result.plot()
        if best is None:
            if self.publish_demo:
                out=self.bridge.cv2_to_imgmsg(annotated,encoding='bgr8'); out.header=msg.header; self.demo_pub.publish(out)
            return
        x1,y1,x2,y2=best['box']; u=0.5*(x1+x2); v=0.5*(y1+y2); depth=self.estimate_depth(u,v)
        if depth is None: return
        fx=float(self.last_info.k[0]); fy=float(self.last_info.k[4]); cx=float(self.last_info.k[2]); cy=float(self.last_info.k[5])
        if fx==0 or fy==0: return
        X=(u-cx)*depth/fx; Y=(v-cy)*depth/fy; Z=depth; now=self.get_clock().now().to_msg()
        cam=PoseStamped(); cam.header.stamp=now; cam.header.frame_id=self.camera_frame; cam.pose.position.x=X; cam.pose.position.y=Y; cam.pose.position.z=Z; cam.pose.orientation.w=1.0; self.pose_camera_pub.publish(cam)
        mp=PoseStamped(); mp.header.stamp=now; mp.header.frame_id=self.map_frame; mp.pose.position.x=Z; mp.pose.position.y=self.map_y_sign*X; mp.pose.position.z=-Y; mp.pose.orientation.w=1.0; self.pose_map_pub.publish(mp)
        if time.time()-self.last_log_t>1.0: self.get_logger().info('Published cup_pose_map: x=%.3f y=%.3f z=%.3f conf=%.2f'%(mp.pose.position.x,mp.pose.position.y,mp.pose.position.z,best['conf'])); self.last_log_t=time.time()
        if self.publish_demo:
            cv2.circle(annotated,(int(u),int(v)),5,(0,255,255),-1); cv2.putText(annotated,'cup map x=%.2f y=%.2f z=%.2f'%(mp.pose.position.x,mp.pose.position.y,mp.pose.position.z),(20,40),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,255),2); out=self.bridge.cv2_to_imgmsg(annotated,encoding='bgr8'); out.header=msg.header; self.demo_pub.publish(out)
def main():
    rclpy.init(); n=Yolo26CupPoseNode()
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally: n.destroy_node(); rclpy.shutdown()
if __name__=='__main__': main()

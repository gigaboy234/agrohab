#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros import StaticTransformBroadcaster
class DirectCameraOpticalTF(Node):
    def __init__(self):
        super().__init__('temporary_tf_direct_camera_optical'); self.declare_parameter('parent_frame','map'); self.declare_parameter('child_frame','camera_color_optical_frame'); self.parent_frame=self.get_parameter('parent_frame').value; self.child_frame=self.get_parameter('child_frame').value; self.br=StaticTransformBroadcaster(self); self.publish_tf(); self.timer=self.create_timer(2.0,self.publish_tf); self.get_logger().warn('Publishing temporary static TF %s -> %s'%(self.parent_frame,self.child_frame))
    def publish_tf(self):
        t=TransformStamped(); t.header.stamp=self.get_clock().now().to_msg(); t.header.frame_id=self.parent_frame; t.child_frame_id=self.child_frame; t.transform.rotation.x=0.5; t.transform.rotation.y=-0.5; t.transform.rotation.z=0.5; t.transform.rotation.w=-0.5; self.br.sendTransform(t)
def main():
    rclpy.init(); n=DirectCameraOpticalTF()
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally: n.destroy_node(); rclpy.shutdown()
if __name__=='__main__': main()

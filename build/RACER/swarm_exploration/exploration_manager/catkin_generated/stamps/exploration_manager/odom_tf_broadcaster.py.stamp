#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
import tf2_ros


class OdomTfBroadcaster:
    def __init__(self):
        self.parent_frame = rospy.get_param("~parent_frame", "map")
        self.child_frame = rospy.get_param("~child_frame", "base_link")
        odom_topic = rospy.get_param("~odom_topic", "odom")
        self.broadcaster = tf2_ros.TransformBroadcaster()
        self.subscriber = rospy.Subscriber(odom_topic, Odometry, self.odom_callback, queue_size=10)

    def odom_callback(self, odom):
        transform = TransformStamped()
        transform.header.stamp = odom.header.stamp if odom.header.stamp else rospy.Time.now()
        transform.header.frame_id = self.parent_frame
        transform.child_frame_id = self.child_frame
        transform.transform.translation.x = odom.pose.pose.position.x
        transform.transform.translation.y = odom.pose.pose.position.y
        transform.transform.translation.z = odom.pose.pose.position.z
        transform.transform.rotation = odom.pose.pose.orientation
        self.broadcaster.sendTransform(transform)


def main():
    rospy.init_node("odom_tf_broadcaster")
    OdomTfBroadcaster()
    rospy.spin()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Transform
from quadrotor_msgs.msg import PositionCommand
from trajectory_msgs.msg import MultiDOFJointTrajectory, MultiDOFJointTrajectoryPoint
from tf.transformations import quaternion_from_euler


class TakeoffHoverUntilPoscmd:
    def __init__(self):
        self.output_topic = rospy.get_param("~output_topic", "command/trajectory")
        self.poscmd_topic = rospy.get_param("~poscmd_topic", "planning/pos_cmd")
        self.frame_id = rospy.get_param("~frame_id", "map")
        self.x = rospy.get_param("~x", 0.0)
        self.y = rospy.get_param("~y", 0.0)
        self.z = rospy.get_param("~z", 1.0)
        self.yaw = rospy.get_param("~yaw", 0.0)
        self.active = True
        self.publisher = rospy.Publisher(self.output_topic, MultiDOFJointTrajectory, queue_size=10)
        self.subscriber = rospy.Subscriber(self.poscmd_topic, PositionCommand, self.poscmd_callback, queue_size=1)
        self.rate = rospy.Rate(rospy.get_param("~publish_rate", 10.0))

    def poscmd_callback(self, _msg):
        if self.active:
            rospy.loginfo("Received Racer position command; takeoff hover publisher is handing over control.")
        self.active = False

    def make_hover_msg(self):
        msg = MultiDOFJointTrajectory()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = self.frame_id
        msg.joint_names = ["base_link"]

        transform = Transform()
        transform.translation.x = self.x
        transform.translation.y = self.y
        transform.translation.z = self.z
        qx, qy, qz, qw = quaternion_from_euler(0.0, 0.0, self.yaw)
        transform.rotation.x = qx
        transform.rotation.y = qy
        transform.rotation.z = qz
        transform.rotation.w = qw

        point = MultiDOFJointTrajectoryPoint()
        point.transforms.append(transform)
        point.time_from_start = rospy.Duration(0.0)
        msg.points.append(point)
        return msg

    def run(self):
        rospy.loginfo("Publishing takeoff hover command at [%.2f, %.2f, %.2f].", self.x, self.y, self.z)
        while not rospy.is_shutdown() and self.active:
            self.publisher.publish(self.make_hover_msg())
            self.rate.sleep()
        rospy.spin()


def main():
    rospy.init_node("takeoff_hover_until_poscmd")
    TakeoffHoverUntilPoscmd().run()


if __name__ == "__main__":
    main()

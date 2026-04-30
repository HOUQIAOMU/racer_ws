#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Transform, Twist
from quadrotor_msgs.msg import PositionCommand
from trajectory_msgs.msg import MultiDOFJointTrajectory, MultiDOFJointTrajectoryPoint
from tf.transformations import quaternion_from_euler


class PositionCommandToMavTrajectory:
    def __init__(self):
        input_topic = rospy.get_param("~input_topic", "planning/pos_cmd")
        output_topic = rospy.get_param("~output_topic", "command/trajectory")
        self.frame_id = rospy.get_param("~frame_id", "map")
        self.publisher = rospy.Publisher(output_topic, MultiDOFJointTrajectory, queue_size=10)
        self.subscriber = rospy.Subscriber(input_topic, PositionCommand, self.command_callback, queue_size=10)

    def command_callback(self, command):
        trajectory = MultiDOFJointTrajectory()
        trajectory.header.stamp = command.header.stamp if command.header.stamp else rospy.Time.now()
        trajectory.header.frame_id = command.header.frame_id or self.frame_id
        trajectory.joint_names = ["base_link"]

        transform = Transform()
        transform.translation.x = command.position.x
        transform.translation.y = command.position.y
        transform.translation.z = command.position.z
        qx, qy, qz, qw = quaternion_from_euler(0.0, 0.0, command.yaw)
        transform.rotation.x = qx
        transform.rotation.y = qy
        transform.rotation.z = qz
        transform.rotation.w = qw

        velocity = Twist()
        velocity.linear = command.velocity
        velocity.angular.z = command.yaw_dot

        acceleration = Twist()
        acceleration.linear = command.acceleration

        point = MultiDOFJointTrajectoryPoint()
        point.transforms.append(transform)
        point.velocities.append(velocity)
        point.accelerations.append(acceleration)
        point.time_from_start = rospy.Duration(0.0)
        trajectory.points.append(point)

        self.publisher.publish(trajectory)


def main():
    rospy.init_node("poscmd_to_mav_trajectory")
    PositionCommandToMavTrajectory()
    rospy.spin()


if __name__ == "__main__":
    main()

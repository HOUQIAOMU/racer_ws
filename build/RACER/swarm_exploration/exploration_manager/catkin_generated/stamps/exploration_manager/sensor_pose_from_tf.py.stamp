#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import PointCloud2
import tf2_ros


class SensorPoseFromTf:
    def __init__(self):
        self.map_frame = rospy.get_param("~map_frame", "map")
        self.sensor_frames = self.expand_sensor_frames(rospy.get_param("~sensor_frame"))
        self.pose_topic = rospy.get_param("~pose_topic", "sensor_pose")
        self.reference_topic = rospy.get_param("~reference_topic", "")
        self.timeout = rospy.Duration(rospy.get_param("~lookup_timeout", 0.05))
        self.buffer = tf2_ros.Buffer()
        self.listener = tf2_ros.TransformListener(self.buffer)
        self.publisher = rospy.Publisher(self.pose_topic, PoseStamped, queue_size=10)
        self.rate = rospy.Rate(rospy.get_param("~publish_rate", 30.0))
        self.reference_subscriber = None
        if self.reference_topic:
            self.reference_subscriber = rospy.Subscriber(
                self.reference_topic, PointCloud2, self.reference_callback, queue_size=10
            )

    @staticmethod
    def expand_sensor_frames(sensor_frame):
        frames = [sensor_frame]
        parts = sensor_frame.split("/", 1)
        if len(parts) == 2 and parts[0]:
            frames.append("%s/%s" % (parts[0], sensor_frame))
        return list(dict.fromkeys(frames))

    def lookup_sensor_transform(self):
        last_error = None
        for sensor_frame in self.sensor_frames:
            try:
                return self.buffer.lookup_transform(
                    self.map_frame, sensor_frame, rospy.Time(0), self.timeout
                )
            except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as exc:
                last_error = exc
        raise last_error

    def publish_pose(self, stamp):
        try:
            transform = self.lookup_sensor_transform()
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as exc:
            rospy.logwarn_throttle(
                5.0,
                "Waiting for TF %s -> one of %s: %s",
                self.map_frame,
                self.sensor_frames,
                exc,
            )
            return

        pose = PoseStamped()
        pose.header.stamp = stamp
        pose.header.frame_id = self.map_frame
        pose.pose.position.x = transform.transform.translation.x
        pose.pose.position.y = transform.transform.translation.y
        pose.pose.position.z = transform.transform.translation.z
        pose.pose.orientation = transform.transform.rotation
        self.publisher.publish(pose)

    def reference_callback(self, msg):
        self.publish_pose(msg.header.stamp)

    def run(self):
        if self.reference_subscriber is not None:
            rospy.spin()
            return

        while not rospy.is_shutdown():
            self.publish_pose(rospy.Time.now())
            self.rate.sleep()


def main():
    rospy.init_node("sensor_pose_from_tf")
    SensorPoseFromTf().run()


if __name__ == "__main__":
    main()

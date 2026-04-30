#!/usr/bin/env python3
import rospy
import sensor_msgs.point_cloud2 as pc2
import tf2_ros
from std_msgs.msg import Header
from sensor_msgs.msg import PointCloud2
from tf.transformations import quaternion_matrix


class PointCloudDownsample:
    def __init__(self):
        input_topic = rospy.get_param("~input_topic", "depth/points")
        output_topic = rospy.get_param("~output_topic", "depth/points_downsampled")
        self.target_frame = rospy.get_param("~target_frame", "")
        self.stride = max(1, int(rospy.get_param("~stride", 60)))
        self.max_points = max(1, int(rospy.get_param("~max_points", 5000)))
        self.lookup_timeout = rospy.Duration(rospy.get_param("~lookup_timeout", 0.05))
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        self.publisher = rospy.Publisher(output_topic, PointCloud2, queue_size=2)
        self.subscriber = rospy.Subscriber(input_topic, PointCloud2, self.cloud_callback, queue_size=1)

    def get_transform_matrix(self, source_frame):
        if not self.target_frame or source_frame == self.target_frame:
            return None
        transform = self.tf_buffer.lookup_transform(
            self.target_frame, source_frame, rospy.Time(0), self.lookup_timeout
        ).transform
        matrix = quaternion_matrix(
            [
                transform.rotation.x,
                transform.rotation.y,
                transform.rotation.z,
                transform.rotation.w,
            ]
        )
        matrix[0, 3] = transform.translation.x
        matrix[1, 3] = transform.translation.y
        matrix[2, 3] = transform.translation.z
        return matrix

    @staticmethod
    def transform_point(matrix, point):
        if matrix is None:
            return point
        x, y, z = point
        return (
            matrix[0, 0] * x + matrix[0, 1] * y + matrix[0, 2] * z + matrix[0, 3],
            matrix[1, 0] * x + matrix[1, 1] * y + matrix[1, 2] * z + matrix[1, 3],
            matrix[2, 0] * x + matrix[2, 1] * y + matrix[2, 2] * z + matrix[2, 3],
        )

    def cloud_callback(self, msg):
        try:
            transform_matrix = self.get_transform_matrix(msg.header.frame_id)
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as exc:
            rospy.logwarn_throttle(
                5.0,
                "Waiting for TF %s -> %s before publishing transformed point cloud: %s",
                self.target_frame,
                msg.header.frame_id,
                exc,
            )
            return

        points = []
        for index, point in enumerate(pc2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True)):
            if index % self.stride != 0:
                continue
            points.append(self.transform_point(transform_matrix, point))
            if len(points) >= self.max_points:
                break

        header = Header(stamp=msg.header.stamp, frame_id=self.target_frame or msg.header.frame_id)
        self.publisher.publish(pc2.create_cloud_xyz32(header, points))


def main():
    rospy.init_node("pointcloud_downsample")
    PointCloudDownsample()
    rospy.spin()


if __name__ == "__main__":
    main()

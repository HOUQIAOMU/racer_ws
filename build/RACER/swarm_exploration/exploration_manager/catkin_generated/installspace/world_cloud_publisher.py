#!/usr/bin/env python3
import math
import xml.etree.ElementTree as ET

import rospy
import sensor_msgs.point_cloud2 as pc2
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Header


def pose_values(text):
    values = [float(v) for v in (text or "").split()]
    values += [0.0] * (6 - len(values))
    return values[:6]


def pose_matrix(pose):
    x, y, z, roll, pitch, yaw = pose
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)

    return [
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr, x],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr, y],
        [-sp, cp * sr, cp * cr, z],
        [0.0, 0.0, 0.0, 1.0],
    ]


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def transform_point(matrix, point):
    x, y, z = point
    return (
        matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z + matrix[0][3],
        matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z + matrix[1][3],
        matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z + matrix[2][3],
    )


def child_pose(element):
    pose = element.find("pose")
    return pose_values(pose.text if pose is not None else "")


def sample_axis(length, resolution):
    if length <= 0.0:
        return [0.0]
    steps = max(1, int(math.ceil(length / resolution)))
    start = -0.5 * length
    return [start + length * i / steps for i in range(steps + 1)]


def sample_box(size, resolution):
    sx, sy, sz = size
    xs, ys, zs = sample_axis(sx, resolution), sample_axis(sy, resolution), sample_axis(sz, resolution)
    points = set()

    for x in (xs[0], xs[-1]):
        for y in ys:
            for z in zs:
                points.add((x, y, z))
    for y in (ys[0], ys[-1]):
        for x in xs:
            for z in zs:
                points.add((x, y, z))
    for z in (zs[0], zs[-1]):
        for x in xs:
            for y in ys:
                points.add((x, y, z))

    return list(points)


def world_points(world_file, resolution, include_ground):
    tree = ET.parse(world_file)
    root = tree.getroot()
    points = []

    for model in root.findall(".//world/model"):
        model_name = model.get("name", "")
        if model_name == "ground_plane" and not include_ground:
            continue

        model_tf = pose_matrix(child_pose(model))
        for link in model.findall("link"):
            link_tf = matmul(model_tf, pose_matrix(child_pose(link)))
            geometries = list(link.findall("collision"))
            if not geometries:
                geometries = list(link.findall("visual"))

            for geom_parent in geometries:
                box = geom_parent.find("geometry/box/size")
                if box is None:
                    continue

                size = [float(v) for v in box.text.split()]
                if len(size) != 3:
                    continue

                geom_tf = matmul(link_tf, pose_matrix(child_pose(geom_parent)))
                points.extend(transform_point(geom_tf, p) for p in sample_box(size, resolution))

    return points


def main():
    rospy.init_node("world_cloud_publisher")
    world_file = rospy.get_param("~world_file")
    topic = rospy.get_param("~topic", "/map_generator/global_cloud")
    frame_id = rospy.get_param("~frame_id", "world")
    resolution = rospy.get_param("~resolution", 0.15)
    include_ground = rospy.get_param("~include_ground", False)

    points = world_points(world_file, resolution, include_ground)
    pub = rospy.Publisher(topic, PointCloud2, queue_size=1, latch=True)
    rate = rospy.Rate(rospy.get_param("~rate", 1.0))

    rospy.loginfo("Publishing %d MAP1 world points on %s", len(points), topic)
    while not rospy.is_shutdown():
        header = Header(stamp=rospy.Time.now(), frame_id=frame_id)
        pub.publish(pc2.create_cloud_xyz32(header, points))
        rate.sleep()


if __name__ == "__main__":
    main()

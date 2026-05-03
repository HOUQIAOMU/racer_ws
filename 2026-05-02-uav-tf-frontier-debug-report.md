# 2026-05-02 UAV Frontier 排查报告

## 1. 问题现象

在仿真中出现以下现象：

- `/uav0/cloud_world` 无消息
- `/uav0/sensor_pose` 无消息
- 探索节点持续输出 `no coverable frontier`

这说明问题不在 frontier 搜索本身，而是在 frontier 之前的地图输入链路。

## 2. 相关数据流

本次问题涉及的核心链路如下：

1. `/uav0/velodyne_points`：Gazebo 激光雷达原始点云
2. `pointcloud_downsample.py`：将点云转换到 `world` 坐标系后发布 `/uav0/cloud_world`
3. `sensor_pose_from_tf.py`：根据 TF 查询传感器位姿后发布 `/uav0/sensor_pose`
4. `map_ros`：同步 `/uav0/cloud_world` 与 `/uav0/sensor_pose` 更新 SDF 地图
5. `frontier_finder`：在 SDF 地图中搜索 frontier

只要第 2 或第 3 步没有正常输出，后续地图与 frontier 都无法工作。

## 3. 排查过程

首先确认上游雷达仍在发消息：

```bash
rostopic hz /uav0/velodyne_points
```

结果显示有数据，因此问题不在雷达本身。

随后检查中间话题：

```bash
rostopic hz /uav0/cloud_world
rostopic hz /uav0/sensor_pose
```

两者均显示 `no new messages`，说明问题出现在 TF 转换或中间节点。

进一步查看 `uav0_lidar_cloud_to_world` 日志，发现关键错误：

```text
Could not find a connection between 'world' and 'uav0/uav0/velodyne'
because they are not part of the same tree.
```

这表明 `pointcloud_downsample.py` 在做 TF 查询时，需要从 `world` 变换到 `uav0/uav0/velodyne`，但这条路径不存在。

## 4. 根因分析

问题的根因是 **TF frame 被重复加了 namespace**。

### 4.1 第一层 namespace

URDF 中 velodyne 的 link 名已经带了 `${namespace}`，例如：

```xml
${namespace}/velodyne
```

当 `namespace=uav0` 时，实际 frame 已经是：

```text
uav0/velodyne
```

### 4.2 第二层 namespace

`robot_state_publisher` 又通过 `tf_prefix=uav0` 再加了一次前缀，于是最终 TF 变成：

```text
uav0/uav0/base_link
uav0/uav0/velodyne
```

而 odom 链使用的是单层 namespace：

```text
world -> uav0/odom -> uav0/base_link
```

于是系统中出现了两棵互不连通的 TF 子树：

### 子树 A：里程计链

```text
world -> uav0/odom -> uav0/base_link
```

### 子树 B：URDF / robot_state_publisher 链

```text
uav0/uav0/base_link -> ... -> uav0/uav0/velodyne
```

由于两棵树没有连接：

- `pointcloud_downsample.py` 无法完成 `world -> uav0/uav0/velodyne` 的 TF 查询
- `/uav0/cloud_world` 不发布
- `/uav0/sensor_pose` 依赖 `/uav0/cloud_world` 的时间戳，也不发布
- `map_ros` 无法更新地图
- `frontier_finder` 一直得不到可搜索 frontier 的地图

## 5. 修复方案

采用最小侵入式修复：增加一个静态 TF，把两棵子树桥接起来。

新增的静态变换为：

```text
uav0/base_link -> uav0/uav0/base_link
```

在 `uav_racer_simulation.launch` 中加入：

```xml
<node name="$(arg namespace)_baselink_bridge_tf"
      pkg="tf"
      type="static_transform_publisher"
      args="0 0 0 0 0 0 $(arg namespace)/base_link $(arg namespace)/$(arg namespace)/base_link 100"/>
```

该变换为单位变换，不改变几何关系，只负责连通 TF 树。

## 6. 修复后的效果

修复后 TF 树变为：

```text
world
  -> uav0/odom
  -> uav0/base_link
  -> uav0/uav0/base_link
  -> ...
  -> uav0/uav0/velodyne
```

这样 `world -> uav0/uav0/velodyne` 就可被正确查询，后续链路恢复：

- `/uav0/cloud_world` 开始发布
- `/uav0/sensor_pose` 开始发布
- SDF 地图开始更新
- frontier 搜索恢复正常

## 7. 验证命令

修复并重启仿真后，可以使用以下命令验证：

```bash
rosrun tf tf_echo world uav0/uav0/velodyne
rostopic hz /uav0/cloud_world
rostopic hz /uav0/sensor_pose
rostopic hz /sdf_map/occupancy_all_1
```

若修复成功：

- `tf_echo` 不再报 `not part of the same tree`
- `cloud_world` 有稳定频率
- `sensor_pose` 有稳定频率
- SDF 地图相关 topic 开始更新

## 8. 经验总结

当系统出现以下现象时：

- `cloud_world` 无消息
- `sensor_pose` 无消息
- 地图不更新
- `no coverable frontier`

建议优先按以下顺序排查：

1. 检查原始传感器是否有数据
2. 检查关键 TF 是否连通
3. 检查中间转换节点日志
4. 最后再检查 frontier 参数和算法逻辑

这次问题的核心结论是：**frontier 为 0 只是结果，真正根因是 TF 树断开导致地图输入链路中断。**

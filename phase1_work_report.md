# Phase 1 工作报告

## 1. 多无人机启动后仍只显示一架

**遇到问题：**  
最初 `gazebo_phase1.launch` 只支持启动单架 `iris` 无人机。尝试扩展多机后，Gazebo/RViz 中仍像只有一架，终端出现类似：

```text
TF_REPEATED_DATA ignoring data with redundant timestamp for frame iris/rotor_0
```

说明多架无人机复用了相同的 TF frame 或 namespace。

**解决方法：**  
将 Phase 1 的 Gazebo 多机入口改为按编号生成独立 namespace：

- `iris_1`
- `iris_2`
- `iris_3`
- `iris_4`

在 `gazebo_phase1.launch` 中增加 `drone_num`、`namespace_1~4`、`x_1~4`、`y_1~4`、`z_1~4` 等参数，使 2-4 架无人机可配置启动，并避免模型名、节点名、topic 名冲突。

同时新增/完善无后缀包装入口：

```bash
roslaunch exploration_manager uav_exploration
```

该入口默认启动 4 架无人机。

## 2. RViz 中没有地图/点云信息

**遇到问题：**  
`roslaunch exploration_manager rviz.launch` 虽然能打开 RViz，但没有同步显示 Gazebo 中 MAP1 对应的地图/点云信息。原 RViz 配置依赖 `/map_generator/global_cloud`、`/sdf_map/occupancy_all_*` 等 topic，但当前 Gazebo 场景没有发布与 `MAP1.world` 对应的点云。

**解决方法：**  
新增脚本：

```text
exploration_manager/scripts/world_cloud_publisher.py
```

该节点直接解析：

```text
fuae_gazebo/worlds/MAP1.world
```

读取其中的 box 障碍物并采样为 `PointCloud2`，发布到：

```text
/map_generator/global_cloud
```

这样 RViz 显示的点云与当前 Gazebo world 保持一致，不再依赖 `pillar.pcd` 等旧 demo 地图文件。

同时更新 `rviz.launch`，默认加载 `swarm.rviz` 并启用仿真时间：

```xml
<param name="use_sim_time" value="true"/>
```

## 3. 不希望每次手动输入 `drone_num` 和 `launch_rviz`

**遇到问题：**  
早期启动时需要手动输入：

```bash
roslaunch exploration_manager uav_exploration drone_num:=4 launch_rviz:=true
```

使用不方便。

**解决方法：**  
将默认参数写入 launch 文件：

- `drone_num` 默认设为 `4`
- `launch_rviz` 默认设为 `true`
- `publish_world_cloud` 默认设为 `true`

现在直接运行：

```bash
roslaunch exploration_manager uav_exploration
```

即可一键启动：

- MAP1 Gazebo 环境
- 4 架无人机
- MAP1 点云发布节点
- RViz

## 4. 分步启动时 Gazebo 报 `Could not wake up Gazebo`

**遇到问题：**  
当先运行：

```bash
roslaunch exploration_manager env_simulation.launch
```

再运行：

```bash
roslaunch exploration_manager uav_exploration.launch
```

时，出现：

```text
[FATAL] Could not wake up Gazebo.
```

原因是 `uav_exploration.launch` 当时也会尝试再次启动 Gazebo 环境，导致重复启动 `/gazebo` 相关节点。

**解决方法：**  
增加 `launch_env` 参数，区分两种启动方式：

1. 一键启动：

   ```bash
   roslaunch exploration_manager uav_exploration
   ```

   该无后缀包装入口默认：

   ```text
   launch_env=true
   ```

2. 分步启动：

   ```bash
   roslaunch exploration_manager env_simulation.launch
   roslaunch exploration_manager uav_exploration.launch
   ```

   `.launch` 入口默认：

   ```text
   launch_env=false
   ```

这样分步启动时不会重复启动 Gazebo。

## 5. RViz 中不显示/不同步无人机位置

**遇到问题：**  
RViz 的 `swarm.rviz` 中已经配置了：

```text
/odom_visualization_1/robot
/odom_visualization_2/robot
/odom_visualization_3/robot
/odom_visualization_4/robot
```

但 Gazebo 版 `uav_simulation.launch` 没有启动对应的 `odom_visualization` 节点，因此 RViz 中无法显示无人机位置。

**解决方法：**  
在 `uav_simulation.launch` 中增加 `odom_visualization` 节点，并将每架无人机的 ground-truth odometry 接到对应的可视化 topic：

```text
/iris_1/ground_truth/odometry -> /odom_visualization_1/robot
/iris_2/ground_truth/odometry -> /odom_visualization_2/robot
/iris_3/ground_truth/odometry -> /odom_visualization_3/robot
/iris_4/ground_truth/odometry -> /odom_visualization_4/robot
```

同时增加参数：

```text
start_odom_visualization=true
```

使该功能默认启用，也可在 launch 中关闭。

## 6. Gazebo 中可见无人机数量不稳定

**遇到问题：**  
虽然 launch 解析显示 4 个 spawn 节点都存在，且日志中也出现 `SpawnModel: Successfully spawned entity`，但 Gazebo 界面中有时只能肉眼看到 2-3 架。问题主要集中在出生点过近、靠近障碍物、或视角遮挡。

**解决方法：**  
多次根据 `MAP1.world` 中障碍物点云评估中心区域可用点位，调整默认出生点，使无人机更分散并远离障碍物。

当前默认位置为：

| 无人机 | x | y | z |
| --- | ---: | ---: | ---: |
| iris_1 | -2.8 | 0.2 | 0.6 |
| iris_2 | 0.4 | -2.4 | 0.6 |
| iris_3 | 0.0 | 1.4 | 0.6 |
| iris_4 | 1.4 | -0.2 | 0.6 |

其中 `iris_2` 曾无法正常显示，后将其从：

```text
(-0.2, -1.8, 0.6)
```

调整为：

```text
(0.4, -2.4, 0.6)
```

该位置离障碍物余量更大，也与其它无人机保持更合理间距。

## 7. `catkin_make` 编译失败

**遇到问题：**  
执行 `catkin_make` 时出现编译错误，包括：

```text
substitution_args.ArgException: namespace
```

以及并行编译时找不到生成头文件：

```text
bspline/Bspline.h
lkh_tsp_solver/SolveTSP.h
```

**解决方法：**  
在 `rotors_gazebo/CMakeLists.txt` 中，为生成 `iris.sdf` 的 xacro 命令补充：

```text
namespace:=iris
```

解决离线生成 SDF 时缺少 namespace 参数的问题。

同时在 `exploration_manager/CMakeLists.txt` 中，为：

```text
exploration_node
ground_node
```

增加生成消息/服务头文件依赖：

```cmake
add_dependencies(exploration_node ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})
add_dependencies(ground_node ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})
```

之后完整 `catkin_make` 可以通过。

## 8. 当前推荐启动方式

**一键启动：**

```bash
cd /home/jacob/racer_ws
source devel/setup.bash
roslaunch exploration_manager uav_exploration
```

**分步启动：**

```bash
cd /home/jacob/racer_ws
source devel/setup.bash
roslaunch exploration_manager env_simulation.launch
roslaunch exploration_manager uav_exploration.launch
```

## 9. 主要改动文件

本阶段主要修改/新增了以下文件：

```text
src/RACER/swarm_exploration/exploration_manager/launch/gazebo_phase1.launch
src/RACER/swarm_exploration/exploration_manager/launch/uav_simulation.launch
src/RACER/swarm_exploration/exploration_manager/launch/uav_exploration
src/RACER/swarm_exploration/exploration_manager/launch/uav_exploration.launch
src/RACER/swarm_exploration/exploration_manager/launch/rviz.launch
src/RACER/swarm_exploration/exploration_manager/config/swarm.rviz
src/RACER/swarm_exploration/exploration_manager/scripts/world_cloud_publisher.py
src/RACER/swarm_exploration/exploration_manager/CMakeLists.txt
src/RACER/swarm_exploration/exploration_manager/package.xml
src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/CMakeLists.txt
```


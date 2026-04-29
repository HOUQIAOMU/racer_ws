# Phase 2 多 UAV Racer-Gazebo 完整仿真方案

## 现状确认摘要

### xacro 文件路径

从指定命令读取到的 UAV/rotors 相关 xacro 路径如下，Phase 2 只基于这些真实路径规划修改：

- `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/iris_base.xacro`
- `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/iris.xacro`
- `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/component_snippets.xacro`
- `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/multirotor_base.xacro`
- `src/RACER/swarm_exploration/rotors_simulator/rotors_description/urdf/ardrone.xacro`
- `src/RACER/swarm_exploration/rotors_simulator/rotors_description/urdf/ardrone_base.xacro`
- `src/RACER/swarm_exploration/rotors_simulator/rotors_description/urdf/component_snippets.xacro`
- `src/RACER/swarm_exploration/rotors_simulator/rotors_description/urdf/multirotor_base.xacro`
- `src/RACER/swarm_exploration/rotors_simulator/rotors_description/urdf/VLP-16.urdf.xacro`

本方案使用当前 Phase 1 已在 Gazebo 中工作的 `iris` 模型，即修改 `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/iris_base.xacro`，并复用同目录 `component_snippets.xacro` 中已有的传感器宏。

### spawn 机制

当前实际 spawn 链路：

- `src/RACER/swarm_exploration/exploration_manager/launch/uav_exploration.launch`
  - include `src/RACER/swarm_exploration/exploration_manager/launch/gazebo_phase1.launch`
  - 启动 `world_cloud_publisher.py`
  - 可选 include `src/RACER/swarm_exploration/exploration_manager/launch/rviz.launch`
- `src/RACER/swarm_exploration/exploration_manager/launch/gazebo_phase1.launch`
  - 当前默认 `drone_num=4`
  - 当前 namespace 是 `iris_1`、`iris_2`、`iris_3`、`iris_4`
  - 逐架 include `src/RACER/swarm_exploration/exploration_manager/launch/uav_simulation.launch`
- `src/RACER/swarm_exploration/exploration_manager/launch/uav_simulation.launch`
  - 在 `<group ns="$(arg namespace)">` 内 include `$(find rotors_gazebo)/launch/spawn_mav.launch`
  - 启动 `rotors_control/lee_position_controller_node`
  - 启动 `robot_state_publisher`、`joint_state_publisher`
  - 可选启动 `rotors_gazebo/hovering_example`
  - 可选启动 `odom_visualization`
- `src/RACER/swarm_exploration/fuae_gazebo/launch/spawn_mav.launch`
  - 使用 `xacro` 生成 `robot_description`
  - 通过 `gazebo_ros/spawn_model` 以 `-model $(arg namespace)` 生成模型

Phase 2 的统一入口需要新增 `src/RACER/swarm_exploration/exploration_manager/launch/searchmap1.launch`，在该入口中把 namespace 从当前 `iris_1~4` 切换为工程约束要求的 `/uav0~3`。

### Racer 订阅 topic

原始指定命令 `grep -r ... src/racer/` 返回 `src/racer/: No such file or directory`，真实 Racer 相关代码在 `src/RACER/swarm_exploration`。根据实际文件读取：

- `src/RACER/swarm_exploration/exploration_manager/launch/single_drone_planner.xml`
  - `exploration_manager/exploration_node` remap:
    - `/odom_world` -> `$(arg odometry_topic)`
    - `/map_ros/pose` -> `$(arg sensor_pose_topic)`
    - `/map_ros/depth` -> `$(arg depth_topic)`
    - `/map_ros/cloud` -> `$(arg cloud_topic)`
- `src/RACER/swarm_exploration/exploration_manager/src/fast_exploration_fsm.cpp`
  - subscribes `/move_base_simple/goal`
  - subscribes `/odom_world`
  - subscribes `/swarm_expl/drone_state_recv`
  - subscribes `/swarm_expl/pair_opt_recv`
  - subscribes `/swarm_expl/pair_opt_res_recv`
  - subscribes `/planning/swarm_traj_recv`
- `src/RACER/swarm_exploration/plan_env/src/map_ros.cpp`
  - subscribes `/map_ros/depth` as `sensor_msgs/Image`
  - subscribes `/map_ros/cloud` as `sensor_msgs/PointCloud2`
  - both are synchronized with `/map_ros/pose` as `geometry_msgs/PoseStamped`
- `src/RACER/swarm_exploration/plan_manage/src/traj_server.cpp`
  - subscribes `planning/bspline`
  - subscribes `planning/replan`
  - subscribes `planning/new`
  - subscribes `/odom_world`
  - subscribes `/loop_fusion/pg_T_vio`

### Racer 发布 topic

根据实际文件读取：

- `src/RACER/swarm_exploration/exploration_manager/src/fast_exploration_fsm.cpp`
  - publishes `/planning/replan`
  - publishes `/planning/new`
  - publishes `/planning/bspline`
  - publishes `/swarm_expl/drone_state_send`
  - publishes `/swarm_expl/pair_opt_send`
  - publishes `/swarm_expl/pair_opt_res_send`
  - publishes `/planning/swarm_traj_send`
  - publishes `/swarm_expl/hgrid_send`
  - publishes `/swarm_expl/grid_tour_send`
- `src/RACER/swarm_exploration/plan_manage/src/traj_server.cpp`
  - publishes `/position_cmd` as `quadrotor_msgs/PositionCommand`
  - publishes `planning/position_cmd_vis`
  - publishes `planning/travel_traj`
- `src/RACER/swarm_exploration/plan_env/src/map_ros.cpp`
  - publishes `/sdf_map/occupancy_all`
  - publishes `/sdf_map/occupancy_local`
  - publishes `/sdf_map/occupancy_local_inflate`
  - publishes `/sdf_map/unknown`
  - publishes `/sdf_map/esdf`
  - publishes `/sdf_map/depth_cloud`

### rotors 接收控制 topic

根据实际文件读取：

- `src/RACER/swarm_exploration/rotors_simulator/rotors_control/src/nodes/lee_position_controller_node.cpp`
  - subscribes `mav_msgs::default_topics::COMMAND_POSE`，注释对应 `command/pose`
  - subscribes `mav_msgs::default_topics::COMMAND_TRAJECTORY`，注释对应 `command/trajectory`
  - subscribes `mav_msgs::default_topics::ODOMETRY`，注释对应 `odometry`
  - publishes `mav_msgs::default_topics::COMMAND_ACTUATORS`，注释对应 `command/motor_speed`
- `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/component_snippets.xacro`
  - `controller_plugin_macro` 的 Gazebo 接口接收 `/${namespace}/command/motor_speed`
  - 同插件发布到 Gazebo 内部 `/gazebo/command/motor_speed`

因此最小控制对接方案是新增一个 `quadrotor_msgs/PositionCommand -> trajectory_msgs/MultiDOFJointTrajectory` 桥接节点，把 Racer 的 `/uavN/planning/pos_cmd` 转成 rotors Lee 控制器的 `/uavN/command/trajectory`，不修改 Racer 核心规划代码。

## 1. 系统架构

Phase 2 数据流：

```text
Gazebo MAP1.world
  -> /uavN/depth/points 或 /uavN/depth/image
  -> /uavN/sensor_pose + /uavN/odom + /uavN/imu/data
  -> /uavN/exploration_node + /uavN/traj_server
  -> /uavN/planning/pos_cmd
  -> /uavN/poscmd_to_mav_trajectory
  -> /uavN/command/trajectory
  -> /uavN/lee_position_controller_node
  -> /uavN/command/motor_speed
  -> rotors Gazebo controller plugin
  -> UAV motion in Gazebo
```

全局约束：

- 使用 `/clock`，所有 launch 设置 `use_sim_time=true`。
- UAV namespace 改为 `/uav0`、`/uav1`、`/uav2`、`/uav3`。
- 每架 UAV 的规划、传感器、控制 topic 在自身 namespace 内隔离。
- swarm 协同 topic 保留共享总线，但通过 `single_drone_planner.xml` 的既有 remap 方式汇聚到公共 topic：
  - `/swarm_expl/drone_state`
  - `/swarm_expl/pair_opt`
  - `/swarm_expl/pair_opt_res`
  - `/planning/swarm_traj`
  - `/multi_map_manager/chunk_stamps`
  - `/multi_map_manager/chunk_data`
- TF 目标链路：
  - `map -> uavN/odom -> uavN/base_link -> uavN/camera_depth_link -> uavN/camera_depth_optical_center_link`
  - `uavN/base_link -> uavN/imu_link`

## 2. 传感器集成

### 深度相机

修改文件：

- `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/iris_base.xacro`
- 必要时修正或复用：
  - `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/component_snippets.xacro`

现有可复用插件宏：

- `component_snippets.xacro` 已有 `vi_sensor_depth_macro`
- 使用插件：`libgazebo_ros_openni_kinect.so`
- 现有宏输出：
  - `camera/image_raw`
  - `camera/camera_info`
  - `depth/disparity`
  - `depth/camera_info`
  - `depth/points`

计划接入方式：

- 在 `iris_base.xacro` 中给每架 `iris` 挂载前向深度相机。
- 使用 `parent_link="base_link"`。
- 使用 `camera_suffix="depth"`。
- 使用 `frame_rate="30.0"`，满足 20-30Hz 要求。
- 期望 topic：
  - `/uav0/depth/points`
  - `/uav1/depth/points`
  - `/uav2/depth/points`
  - `/uav3/depth/points`
  - 同时保留 `/uavN/depth/disparity` 或等价 depth image topic，作为可选输入。
- Racer 最小对接使用 point cloud：
  - `/map_ros/cloud` remap 到 `/uavN/depth/points`
  - 不优先使用 depth image，避免 Gazebo OpenNI depth/disparity 编码与 `map_ros` 的 `k_depth_scaling_factor=1000.0` 不一致。

需要注意：

- `component_snippets.xacro` 中 depth sensor name 和 plugin name 当前写作 `${namespace}_camera_{camera_suffix}`，其中 `{camera_suffix}` 疑似漏 `$`。实现时应修正为 `${namespace}_camera_${camera_suffix}`，否则多机模型中 sensor/plugin 名称可能不唯一。
- `frameName` 当前是 `camera_${camera_suffix}_optical_center_link`，为了 TF 隔离，建议改成 `${namespace}/camera_${camera_suffix}_optical_center_link` 或确认插件发布的 `frame_id` 与 TF 中 link 名一致。

### IMU

修改文件：

- `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/iris_base.xacro`

现状：

- `iris_base.xacro` 已挂载 `imu_plugin_macro`
- plugin：`librotors_gazebo_imu_plugin.so`
- 当前真实 IMU topic 参数是 `imu_topic="/imu"`
- 在 namespace 为 `uavN` 时，实际目标 topic 应为 `/uavN/imu`

计划接入方式：

- 保留现有 rotors IMU 插件，避免重复添加第二套 IMU。
- 为满足工程约束中的 `/imu/data`，把 `imu_topic` 从 `/imu` 调整为 `imu/data`，使每架 UAV 发布：
  - `/uav0/imu/data`
  - `/uav1/imu/data`
  - `/uav2/imu/data`
  - `/uav3/imu/data`
- 若 `controller_plugin_macro` 当前 `imu_sub_topic="imu"` 依赖 `/uavN/imu`，同步改为 `imu_sub_topic="imu/data"`，确保 rotors controller interface 使用同一个 IMU 源。
- frame：
  - link：`uavN/imu_link`
  - message `frame_id` 目标：`uavN/imu_link`
- 频率：
  - rotors IMU 插件跟随 Gazebo update，验收用 `rostopic hz /uavN/imu/data` 检查至少 20Hz；若远高于 30Hz，可在后续增加 throttle，但首版不主动降频，避免影响控制。

## 3. 多 UAV 设计

### namespace

Phase 1 当前 namespace 是：

- `iris_1`
- `iris_2`
- `iris_3`
- `iris_4`

Phase 2 改为：

- `uav0`
- `uav1`
- `uav2`
- `uav3`

在 `src/RACER/swarm_exploration/exploration_manager/launch/searchmap1.launch` 中设置：

- `namespace_0=uav0`
- `namespace_1=uav1`
- `namespace_2=uav2`
- `namespace_3=uav3`
- `drone_id` 传给 Racer 时使用 `1~4`，因为现有 `single_drone_exploration.xml`、`single_drone_planner.xml` 和 swarm 逻辑使用 1-based id。
- namespace 使用 `uav0~3`，Racer 内部 `drone_id` 使用 `1~4`，两者通过 launch 参数显式映射。

### launch spawn 方式

复用当前已验证的 spawn 链路：

- `searchmap1.launch`
  - include `env_simulation.launch`
  - include `uav_simulation.launch` 四次或 include 一个新增的 per-UAV launch 四次
- `uav_simulation.launch`
  - include `rotors_gazebo/launch/spawn_mav.launch`
- `spawn_mav.launch`
  - xacro -> `robot_description`
  - `gazebo_ros/spawn_model`

推荐实现：

- 不直接破坏 Phase 1 的 `uav_exploration.launch` 默认行为。
- 新增 `searchmap1.launch` 作为 Phase 2 统一入口。
- 为 Phase 2 扩展 `uav_simulation.launch`，新增参数：
  - `enable_depth_camera`
  - `enable_racer`
  - `start_hover` 默认在 Phase 2 为 `false`
  - `racer_drone_id`
  - `racer_odom_topic`
  - `racer_cloud_topic`
  - `racer_sensor_pose_topic`
- 或新增更清晰的 `src/RACER/swarm_exploration/exploration_manager/launch/uav_racer_simulation.launch`，内部 include `uav_simulation.launch` 并启动 Racer/桥接节点。

### topic 隔离

每架 UAV 的私有 topic：

- `/uavN/ground_truth/odometry`
- `/uavN/odom`
- `/uavN/imu/data`
- `/uavN/depth/points`
- `/uavN/depth/disparity` 或 `/uavN/depth/image`
- `/uavN/sensor_pose`
- `/uavN/planning/pos_cmd`
- `/uavN/command/trajectory`
- `/uavN/command/motor_speed`
- `/uavN/sdf_map/occupancy_all` 或现有兼容命名 `/sdf_map/occupancy_all_<drone_id>`

Racer 已有多机共享 topic 保持公共：

- `/swarm_expl/drone_state`
- `/swarm_expl/pair_opt`
- `/swarm_expl/pair_opt_res`
- `/planning/swarm_traj`
- `/multi_map_manager/chunk_stamps`
- `/multi_map_manager/chunk_data`

## 4. `searchmap1.launch` 核心设计

新增文件：

- `src/RACER/swarm_exploration/exploration_manager/launch/searchmap1.launch`

职责：

- 设置 `use_sim_time=true`
- 加载 MAP1：
  - include `src/RACER/swarm_exploration/exploration_manager/launch/env_simulation.launch`
  - `world_name=MAP1`
- 发布 MAP1 点云：
  - 启动 `exploration_manager/world_cloud_publisher.py`
  - topic `/map_generator/global_cloud`
  - frame `map` 或 `world`；推荐统一为 `map`
- spawn 2-4 架 UAV：
  - 默认 `drone_num=4`
  - namespace `/uav0~3`
  - 复用 Phase 1 中已调整的 MAP1 中心安全位置
- 每架 UAV 启动：
  - `spawn_mav.launch`
  - `lee_position_controller_node`
  - `robot_state_publisher`
  - `joint_state_publisher`
  - TF 辅助节点
  - sensor pose 发布节点
  - Racer `single_drone_exploration.xml`
  - 控制桥接节点
- 可选启动 RViz：
  - include `src/RACER/swarm_exploration/exploration_manager/launch/rviz.launch`

include 关系：

```text
searchmap1.launch
  -> env_simulation.launch
  -> world_cloud_publisher.py
  -> uav_racer_simulation.launch x drone_num
       -> uav_simulation.launch
            -> rotors_gazebo/launch/spawn_mav.launch
            -> rotors_control/lee_position_controller_node
       -> single_drone_exploration.xml
            -> single_drone_planner.xml
            -> traj_server
       -> poscmd_to_mav_trajectory
       -> odom_tf_broadcaster
       -> sensor_pose_from_tf
  -> rviz.launch
```

参数加载：

- 当前工程没有读取到 `algorithm.xml` 文件。
- 真实存在并被 Racer 使用的是：
  - `src/RACER/swarm_exploration/exploration_manager/launch/single_drone_exploration.xml`
  - `src/RACER/swarm_exploration/exploration_manager/launch/single_drone_planner.xml`
  - `src/RACER/swarm_exploration/plan_manage/launch/kino_algorithm.xml`
  - `src/RACER/swarm_exploration/plan_manage/launch/topo_algorithm.xml`
- 最小替代方案：
  - `searchmap1.launch` 直接 include `single_drone_exploration.xml`，继续使用其中的参数系统。
  - 若后续确实需要 `algorithm.xml` 命名兼容，可新增 `src/RACER/swarm_exploration/exploration_manager/launch/algorithm.xml`，仅作为 thin wrapper include `single_drone_planner.xml`，不复制大段参数。

## 5. Racer 对接重点

### Racer 输入 topic

每架 UAV 的 `single_drone_exploration.xml` 参数建议：

以 `/uav0` 为例：

- `drone_id=1`
- `drone_num=$(arg drone_num)`
- `odometry_topic=/uav0/odom`
- `sensor_pose_topic=/uav0/sensor_pose`
- `depth_topic=/uav0/depth/disparity`，保留但首选不用
- `cloud_topic=/uav0/depth/points`
- `simulation=false`

对应 remap 由 `single_drone_planner.xml` 完成：

- `/odom_world` -> `/uav0/odom`
- `/map_ros/pose` -> `/uav0/sensor_pose`
- `/map_ros/depth` -> `/uav0/depth/disparity`
- `/map_ros/cloud` -> `/uav0/depth/points`

同理：

- `/uav1` 对应 `drone_id=2`
- `/uav2` 对应 `drone_id=3`
- `/uav3` 对应 `drone_id=4`

IMU：

- Racer 当前核心订阅链路未发现直接订阅 `/imu` 或 `/imu/data`。
- IMU 仍必须由 Gazebo 发布给控制/状态链路和验收：
  - `/uavN/imu/data`
- 若后续加入 VIO/UKF，则把 `/uavN/imu/data` 与 `/uavN/depth/*` 接到估计节点，输出 `/uavN/odom`；Phase 2 最小闭环先使用 Gazebo ground truth odometry 转发为 `/uavN/odom`。

### Gazebo 如何提供

- odom：
  - `iris_base.xacro` 已有 `odometry_plugin_macro`
  - 当前 topic：`/uavN/ground_truth/odometry`
  - 新增 relay 或 remap：`/uavN/ground_truth/odometry -> /uavN/odom`
- cloud：
  - `iris_base.xacro` 新增/启用 depth camera
  - 输出 `/uavN/depth/points`
- sensor pose：
  - 新增 `sensor_pose_from_tf` 节点
  - 从 TF 查询 `map` 到 `uavN/camera_depth_optical_center_link`
  - 发布 `/uavN/sensor_pose`，类型 `geometry_msgs/PoseStamped`，30Hz
- IMU：
  - `iris_base.xacro` 保留/调整 IMU 插件
  - 输出 `/uavN/imu/data`

### 控制输出如何作用 UAV

Racer 输出：

- `src/RACER/swarm_exploration/plan_manage/src/traj_server.cpp`
  - 发布 `/position_cmd`，类型 `quadrotor_msgs/PositionCommand`
- `single_drone_exploration.xml`
  - 已将 `/position_cmd` remap 为 `planning/pos_cmd_$(arg drone_id)`

Phase 2 建议改成 namespace 内 topic：

- `/uav0/planning/pos_cmd`
- `/uav1/planning/pos_cmd`
- `/uav2/planning/pos_cmd`
- `/uav3/planning/pos_cmd`

rotors 输入：

- `lee_position_controller_node` 接收：
  - `/uavN/command/pose`
  - `/uavN/command/trajectory`
  - `/uavN/odometry`
- 发布：
  - `/uavN/command/motor_speed`

最小桥接方案：

- 新增节点：
  - `src/RACER/swarm_exploration/exploration_manager/scripts/poscmd_to_mav_trajectory.py`
  - 或 C++ 节点 `poscmd_to_mav_trajectory`
- 订阅：
  - `/uavN/planning/pos_cmd`，类型 `quadrotor_msgs/PositionCommand`
- 发布：
  - `/uavN/command/trajectory`，类型 `trajectory_msgs/MultiDOFJointTrajectory`
- 转换字段：
  - position -> `transforms[0].translation`
  - yaw -> `transforms[0].rotation`
  - velocity -> `velocities[0].linear`
  - yaw_dot -> `velocities[0].angular.z`
  - acceleration -> `accelerations[0].linear`
- 同时确保 `lee_position_controller_node` 的 `odometry` remap 到 `/uavN/odom` 或 `/uavN/ground_truth/odometry`。
- Phase 2 运行时必须关闭 `hovering_example`，否则它会持续向相同控制链路发送 hover 目标，与 Racer 控制冲突。

## 6. 实现步骤

### Step 1：新增 Phase 2 统一入口

- 做什么：
  - 新增 `searchmap1.launch`，统一启动 MAP1、2-4 UAV、传感器、Racer、控制桥接、RViz。
- 修改文件路径：
  - `src/RACER/swarm_exploration/exploration_manager/launch/searchmap1.launch`
- 预期结果：
  - 可执行 `roslaunch exploration_manager searchmap1.launch`
  - 默认启动 4 架 `/uav0~3`
  - 可通过 `drone_num:=2/3/4` 控制数量
- 验证方法：
  - `roslaunch --nodes exploration_manager searchmap1.launch`
  - `rosparam get /use_sim_time`
  - `rostopic echo -n 1 /clock`

### Step 2：调整多 UAV namespace

- 做什么：
  - 保留 Phase 1 的 `iris_1~4` 入口不动或只做兼容。
  - 在 `searchmap1.launch` 中明确使用 `/uav0~3`。
- 修改文件路径：
  - `src/RACER/swarm_exploration/exploration_manager/launch/searchmap1.launch`
  - 如需复用，扩展 `src/RACER/swarm_exploration/exploration_manager/launch/gazebo_phase1.launch`
  - 如需复用，扩展 `src/RACER/swarm_exploration/exploration_manager/launch/uav_simulation.launch`
- 预期结果：
  - Gazebo model 名为 `uav0`、`uav1`、`uav2`、`uav3`
  - topic 不再出现 Phase 2 的 `iris_1~4`
- 验证方法：
  - `rosservice call /gazebo/get_world_properties`
  - `rostopic list | grep '^/uav[0-3]/'`

### Step 3：为 iris 添加深度相机

- 做什么：
  - 在 `iris_base.xacro` 中挂载 depth camera。
  - 修正 `component_snippets.xacro` 中 depth sensor/plugin 名称的 `${camera_suffix}` 拼写问题。
- 修改文件路径：
  - `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/iris_base.xacro`
  - `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/component_snippets.xacro`
- 预期结果：
  - 每架 UAV 发布 `/uavN/depth/points`
  - 每架 UAV 发布 depth image 或 disparity topic
- 验证方法：
  - `rostopic hz /uav0/depth/points`
  - `rostopic echo -n 1 /uav0/depth/points/header`
  - RViz 添加 PointCloud2 查看 `/uav0/depth/points`

### Step 4：调整 IMU topic

- 做什么：
  - 把 `iris_base.xacro` 中 IMU topic 改为 `imu/data`。
  - 把 controller plugin 的 `imu_sub_topic` 同步改为 `imu/data`。
- 修改文件路径：
  - `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/iris_base.xacro`
- 预期结果：
  - 每架 UAV 发布 `/uavN/imu/data`
  - controller plugin 仍能收到 IMU。
- 验证方法：
  - `rostopic hz /uav0/imu/data`
  - `rostopic echo -n 1 /uav0/imu/data/header`

### Step 5：建立 TF 与 sensor pose

- 做什么：
  - 建立 `map -> uavN/odom -> uavN/base_link -> sensor_link`。
  - 新增 odom TF 发布节点或在 launch 中用现有 odom 转 TF。
  - 新增 sensor pose 发布节点，将 TF 转为 `geometry_msgs/PoseStamped`。
- 修改文件路径：
  - `src/RACER/swarm_exploration/exploration_manager/scripts/sensor_pose_from_tf.py`
  - `src/RACER/swarm_exploration/exploration_manager/scripts/odom_tf_broadcaster.py`
  - `src/RACER/swarm_exploration/exploration_manager/CMakeLists.txt`
  - `src/RACER/swarm_exploration/exploration_manager/package.xml`
  - `src/RACER/swarm_exploration/exploration_manager/launch/searchmap1.launch`
- 预期结果：
  - `/uavN/sensor_pose` 以 30Hz 发布。
  - TF tree 可从 `map` 查到每架 UAV 的 `base_link` 和 depth optical frame。
- 验证方法：
  - `rosrun tf tf_echo map uav0/base_link`
  - `rosrun tf tf_echo map uav0/camera_depth_optical_center_link`
  - `rostopic hz /uav0/sensor_pose`

### Step 6：启动 Racer 多机探索

- 做什么：
  - 对每架 UAV include `single_drone_exploration.xml`。
  - 传入 namespace 内 odom/cloud/sensor_pose topic。
  - 保留 `single_drone_planner.xml` 中已有 swarm remap 机制。
- 修改文件路径：
  - `src/RACER/swarm_exploration/exploration_manager/launch/searchmap1.launch`
  - 必要时新增 `src/RACER/swarm_exploration/exploration_manager/launch/uav_racer_simulation.launch`
- 预期结果：
  - 每架 UAV 启动一个 `exploration_node_<id>`。
  - 每架 UAV 启动一个 `traj_server_<id>`。
  - 每架 UAV 独立发布地图 topic。
- 验证方法：
  - `rosnode list | grep exploration_node`
  - `rostopic hz /sdf_map/occupancy_all_1`
  - `rostopic hz /sdf_map/unknown_1`
  - `rostopic echo -n 1 /swarm_expl/drone_state`

### Step 7：新增控制桥接

- 做什么：
  - 新增 `PositionCommand -> MultiDOFJointTrajectory` 桥接。
  - 关闭 Phase 2 中的 `hovering_example`。
- 修改文件路径：
  - `src/RACER/swarm_exploration/exploration_manager/scripts/poscmd_to_mav_trajectory.py`
  - `src/RACER/swarm_exploration/exploration_manager/CMakeLists.txt`
  - `src/RACER/swarm_exploration/exploration_manager/package.xml`
  - `src/RACER/swarm_exploration/exploration_manager/launch/searchmap1.launch`
  - 或 `src/RACER/swarm_exploration/exploration_manager/launch/uav_racer_simulation.launch`
- 预期结果：
  - Racer 输出 `/uavN/planning/pos_cmd`
  - 桥接输出 `/uavN/command/trajectory`
  - Lee 控制器输出 `/uavN/command/motor_speed`
  - UAV 在 Gazebo 中跟随 Racer 轨迹移动。
- 验证方法：
  - `rostopic hz /uav0/planning/pos_cmd`
  - `rostopic hz /uav0/command/trajectory`
  - `rostopic hz /uav0/command/motor_speed`
  - `rostopic echo -n 1 /gazebo/model_states`

### Step 8：RViz 与验收可视化

- 做什么：
  - 更新 RViz 配置，显示 `/uavN/odom`、`/uavN/depth/points`、`/sdf_map/occupancy_all_<id>`、`/sdf_map/unknown_<id>`。
- 修改文件路径：
  - `src/RACER/swarm_exploration/exploration_manager/launch/rviz.launch`
  - `src/RACER/swarm_exploration/exploration_manager/config/swarm.rviz`
- 预期结果：
  - `roslaunch exploration_manager searchmap1.launch` 后 RViz 同步显示 UAV、传感器点云、探索地图。
- 验证方法：
  - RViz Fixed Frame 设置为 `map`。
  - 检查 4 架 UAV marker、局部/全局 occupancy cloud 持续更新。

### Step 9：编译与运行验证

- 做什么：
  - 编译新增脚本安装和 launch/xacro 修改。
  - 运行 2、3、4 机配置。
- 修改文件路径：
  - `src/RACER/swarm_exploration/exploration_manager/CMakeLists.txt`
  - `src/RACER/swarm_exploration/exploration_manager/package.xml`
- 预期结果：
  - `catkin_make` 通过。
  - 2-4 架 UAV 都能自主运动。
- 验证方法：
  - `catkin_make`
  - `roslaunch exploration_manager searchmap1.launch drone_num:=2`
  - `roslaunch exploration_manager searchmap1.launch drone_num:=4`

## 7. 验收标准

- UAV 自主探索：
  - 关闭 `hovering_example` 后，UAV 仍能由 Racer 产生 `/uavN/planning/pos_cmd` 并运动。
  - `/gazebo/model_states` 中每架 UAV 位姿随时间变化。
- 地图持续更新：
  - `/sdf_map/occupancy_all_<id>`、`/sdf_map/unknown_<id>` 持续发布。
  - RViz 中 occupancy/unknown 区域随 UAV 运动变化。
- 无发散：
  - UAV 不出现快速坠落、飞出地图、姿态翻转。
  - `/uavN/command/motor_speed` 持续有合理数值。
- 多机无冲突：
  - `/uav0~3` topic 完全隔离。
  - TF 中没有多个 UAV 共用同一个 `base_link`、`imu_link` 或 camera frame。
  - UAV 间保持安全距离，Racer swarm topic 正常通信。
- 传感器满足要求：
  - `/uavN/depth/points` 或 depth image 为 20-30Hz。
  - `/uavN/imu/data` 至少 20Hz。
  - message header frame_id 与 TF 中 frame 可连通。

## 8. 排查 checklist

### TF 错误

- `rosrun tf tf_echo map uav0/base_link` 是否可用。
- `rosrun tf tf_echo map uav0/camera_depth_optical_center_link` 是否可用。
- 若 RViz 报 `No transform`：
  - 检查 `frameName` 是否包含 namespace。
  - 检查 `robot_state_publisher` 是否在 `/uavN` namespace 下。
  - 检查 odom TF broadcaster 是否发布 `uavN/odom -> uavN/base_link`。

### namespace 冲突

- `rostopic list | grep iris_`，Phase 2 正常情况下不应出现作为主链路的 `iris_1~4`。
- `rostopic list | grep '^/uav[0-3]/'`，每架 UAV 应有独立 sensor、odom、control topic。
- Gazebo model 名称应为 `uav0~3`。

### topic 不通

- cloud：
  - `rostopic hz /uav0/depth/points`
  - `rostopic echo -n 1 /uav0/depth/points/header`
- pose：
  - `rostopic hz /uav0/sensor_pose`
- odom：
  - `rostopic hz /uav0/odom`
- Racer map：
  - `rostopic hz /sdf_map/occupancy_all_1`
  - `rostopic hz /sdf_map/unknown_1`

### 控制无效

- 检查 Racer 是否输出：
  - `rostopic hz /uav0/planning/pos_cmd`
- 检查桥接是否输出：
  - `rostopic hz /uav0/command/trajectory`
- 检查 Lee 控制器是否输出：
  - `rostopic hz /uav0/command/motor_speed`
- 若 `/uav0/command/trajectory` 有数据但 UAV 不动：
  - 检查 `lee_position_controller_node` 的 odometry remap。
  - 检查 `controller_plugin_macro` 是否接收 `/uav0/command/motor_speed`。
  - 确认 Phase 2 中没有启动 `hovering_example` 与 Racer 抢控制。

### 传感器无数据

- 检查 xacro 是否实际生成 depth sensor：
  - `rosparam get /uav0/robot_description | grep camera_depth`
- 检查 Gazebo 插件是否加载失败：
  - 查看 `~/.ros/log/latest` 中 `libgazebo_ros_openni_kinect.so` 相关错误。
- 检查 topic frame：
  - `/uav0/depth/points/header/frame_id`
  - `/uav0/imu/data/header/frame_id`
- 若 cloud 有数据但地图不更新：
  - 检查 `/uav0/sensor_pose` 时间戳是否与 cloud 接近。
  - 检查 `single_drone_planner.xml` 的 `/map_ros/cloud` remap 是否指向 `/uav0/depth/points`。

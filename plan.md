# Phase 1：最小可运行闭环（重点详细写）

## 1. 当前状态评估

### 已复制 3 个包的作用

- `src/RACER/swarm_exploration/rotors_simulator`
  - 核心 Gazebo Classic 多旋翼仿真框架。
  - 主要子包：
    - `rotors_gazebo`：world、模型、示例 launch、hover/waypoint 示例节点。
    - `rotors_gazebo_plugins`：Gazebo 插件，包括 motor model、IMU、odometry、controller interface、ROS interface。
    - `rotors_description`：UAV xacro/urdf 模型与 rotor plugin 配置。
    - `rotors_control`：Lee position controller / attitude-rate controller，将轨迹或姿态命令转换为电机角速度。
    - `rotors_comm`：rotors 相关消息。
- `src/RACER/swarm_exploration/fuae_gazebo`
  - 从 Star-Searcher 迁移来的 Gazebo 资源包。
  - 当前包含：
    - `launch/spawn_mav.launch`：基于 `rotors_description` xacro 调用 `gazebo_ros/spawn_model`。
    - `worlds/MAP1.world`、`worlds/MAP2.world`：带静态结构的 Gazebo world。
    - `resource/*.yaml`：iris/ardrone 及 Lee controller 参数。
  - Phase 1 只允许作为 world/spawn 参考；不接入传感器。
- `src/RACER/swarm_exploration/gazebo_map_generator`
  - Gazebo 场景/地图生成相关包。
  - Phase 1 明确禁用，不作为 MVP 依赖，避免把“world 能加载、UAV 能动”的闭环复杂化。

### Racer 当前已有仿真/控制状态

- Racer 原始仿真不依赖 Gazebo：
  - `uav_simulator/so3_quadrotor_simulator/launch/simulator.launch`
  - `swarm_exploration/plan_manage/launch/simulator.xml`
  - `swarm_exploration/exploration_manager/launch/simulator_light.xml`
- Racer 当前控制链路：
  - `plan_manage/src/traj_server.cpp`
    - 订阅 `/odom_world`
    - 发布 `/position_cmd`，消息类型为 `quadrotor_msgs/PositionCommand`
  - `exploration_manager/launch/single_drone_exploration.xml`
    - 将 `/position_cmd` remap 到 `planning/pos_cmd_$(arg drone_id)`
    - 将 `/odom_world` remap 到 `$(arg odom_prefix)_$(arg drone_id)`，默认整体 odom 前缀在 `swarm_exploration.launch` 中是 `/state_ukf/odom`
  - `uav_simulator/so3_control/src/so3_control_nodelet.cpp`
    - 私有订阅 `~odom`、`~position_cmd`、`~imu`
    - 私有发布 `~so3_cmd`
  - `uav_simulator/poscmd_2_odom/src/poscmd_2_odom.cpp`
    - 私有订阅 `~command`
    - 私有发布 `~odometry`
  - 现有轻量仿真 `simulator_light.xml` 用 `poscmd_2_odom` 将 `/planning/pos_cmd_<id>` 直接转成 odom，是“运动学假闭环”，不是 Gazebo 物理闭环。

### Gazebo/rotors 当前输出与控制接口

- `rotors_gazebo/launch/mav_hovering_example.launch`
  - 启动 Gazebo world。
  - spawn UAV。
  - 启动 `rotors_control/lee_position_controller_node`。
  - 启动 `rotors_gazebo/hovering_example`。
- rotors 控制输入：
  - `rotors_control/src/nodes/lee_position_controller_node.cpp`
    - 订阅 `command/pose`
    - 订阅 `command/trajectory`
    - 订阅 `odometry`
    - 发布 `command/motor_speed`
  - 在 UAV namespace 为 `iris` 时，对应 topic 通常为：
    - `/iris/command/trajectory`
    - `/iris/command/pose`
    - `/iris/odometry_sensor1/odometry`
    - `/iris/command/motor_speed`
- Gazebo 插件输出：
  - `rotors_description/urdf/component_snippets.xacro`
    - IMU plugin 发布 `imu` 或 `ground_truth/imu`
    - odometry plugin 发布 `odometry`
  - `rotors_description/urdf/multirotor_base.xacro`
    - 每个 rotor 的 `librotors_gazebo_motor_model.so` 订阅 `gazebo/command/motor_speed`
    - controller interface 将 `command/motor_speed` 转发到 `gazebo/command/motor_speed`
- 关键差异：
  - Racer planner 输出 `quadrotor_msgs/PositionCommand`。
  - rotors Lee controller 输入 `trajectory_msgs/MultiDOFJointTrajectory` 或 `geometry_msgs/PoseStamped`。
  - Phase 1 最小代价不直接接 Racer planner；先用 rotors 自带 hover/trajectory 控制验证 Gazebo 物理闭环。

### 当前缺失组件（必须具体）

- 缺少面向 Racer 的 Gazebo MVP launch：
  - 当前不存在 `src/RACER/swarm_exploration/exploration_manager/launch/env_simulation.launch`
  - 当前不存在 `src/RACER/swarm_exploration/exploration_manager/launch/uav_simulation.launch`
- 缺少明确的 MVP world 选择：
  - Phase 1 应优先使用 `rotors_gazebo/worlds/basic.world`，或复制成 `fuae_gazebo/worlds/racer_mvp.world` 后只保留 ground、sun、少量静态障碍。
  - 暂不使用 `gazebo_map_generator`。
- 缺少 Racer topic 与 rotors topic 的最小桥接策略：
  - Gazebo odom：`/iris/odometry_sensor1/odometry` 或 `/iris/ground_truth/odometry`
  - Racer 常用 odom：`/state_ukf/odom`、`/visual_slam/odom`、多机时 `/state_ukf/odom_<id>`
  - Phase 1 只需要 remap/relay odom 到 RViz 或轻量验证节点，不修改 Racer 核心算法。
- 可能缺少系统/ROS 依赖：
  - `gazebo_ros`
  - `gazebo_plugins`
  - `xacro`
  - `mav_msgs`
  - `mavros`
  - `octomap`
  - `octomap_ros`
  - `cv_bridge`
  - `cmake_modules`
  - `protobuf-dev`
  - `libgoogle-glog-dev`
  - `yaml-cpp`
  - `joint_state_publisher`
  - `robot_state_publisher`
- 可能缺少构建层配置：
  - `rotors_gazebo_plugins` 需要正确链接 Gazebo Classic headers/libs。
  - copied package 只完成复制，尚未验证 catkin build。
- 缺少 plugin 加载验证机制：
  - 需要在运行时检查 `librotors_gazebo_motor_model.so`、`librotors_gazebo_controller_interface.so`、`librotors_gazebo_odometry_plugin.so`、`librotors_gazebo_imu_plugin.so` 是否被 Gazebo 成功加载。

## 2. 最小系统架构

Phase 1 只做一个单 UAV Gazebo 物理闭环：

```text
Gazebo world
  └── gazebo_ros + rotors_gazebo_ros_interface_plugin
        └── spawn_model 加载 iris/ardrone xacro
              └── UAV model
                    ├── multirotor_base_plugin
                    ├── motor_model plugins
                    ├── controller_interface plugin
                    ├── odometry plugin
                    └── imu plugin
                          ↓
                    /iris/odometry_sensor1/odometry
                    /iris/imu
                          ↓
rotors_control/lee_position_controller_node
  subscribe: /iris/odometry_sensor1/odometry
  subscribe: /iris/command/trajectory 或 /iris/command/pose
  publish:   /iris/command/motor_speed
                          ↓
controller_interface plugin
  /iris/command/motor_speed → /iris/gazebo/command/motor_speed
                          ↓
motor_model plugins
  电机力/力矩作用于 Gazebo 物理引擎
                          ↓
UAV 起飞/悬停/简单移动
```

必须使用的 package：

- `gazebo_ros`
  - 启动 Gazebo Classic。
  - 提供 `/clock`、`/gazebo/*` 服务、`spawn_model`。
- `rotors_gazebo`
  - 提供 `basic.world`、示例 launch、`hovering_example`。
- `rotors_description`
  - 提供 UAV xacro/urdf，推荐 Phase 1 先使用 `iris`，因为 `rotors_gazebo/models/rotors_description/urdf/iris_base.xacro`、controller yaml 和 world 示例都较完整。
- `rotors_gazebo_plugins`
  - 提供 motor、odometry、IMU、controller interface 等 Gazebo 插件。
- `rotors_control`
  - 提供 `lee_position_controller_node`，用于从 `command/trajectory` 生成 `command/motor_speed`。
- `robot_state_publisher`
  - 发布 UAV TF。
- `joint_state_publisher`
  - 提供 joint state，辅助 RViz 模型显示。
- `exploration_manager`
  - 作为 Racer 对外统一 launch 入口，只新增/封装 launch，不改核心算法。
- `odom_visualization` 或 `rviz`
  - Phase 1 只做状态可视化，不启动感知建图。

Phase 1 明确不使用：

- `gazebo_map_generator`
- `local_sensing_node/pcl_render_node`
- realsense
- velodyne
- Racer exploration/planning 主算法
- 多 UAV swarm launch

## 3. 逐步执行步骤（核心）

### Step 0：构建与依赖基线检查

- 做什么（具体操作）
  - 在 workspace 根目录检查 copied package 是否能被 catkin 识别。
  - 先只构建 Phase 1 必需包，避免一次性构建全量 Racer 干扰定位。
- 修改/涉及文件（路径级别）
  - 暂不修改文件。
  - 检查：
    - `src/RACER/swarm_exploration/rotors_simulator/*/package.xml`
    - `src/RACER/swarm_exploration/fuae_gazebo/package.xml`
    - `src/RACER/swarm_exploration/exploration_manager/package.xml`
- 为什么做
  - 当前 3 个包只是复制，最先要确认缺哪些 ROS/system 依赖。
  - 插件编译失败会导致后续 spawn 成功但 UAV 不动。
- 如何验证（必须可执行）

```bash
cd /home/jacob/racer_ws
source /opt/ros/$ROS_DISTRO/setup.bash
catkin_make --pkg rotors_comm rotors_gazebo_plugins rotors_description rotors_control rotors_gazebo fuae_gazebo exploration_manager
source devel/setup.bash
rospack find rotors_gazebo
rospack find rotors_description
rospack find rotors_control
rospack find fuae_gazebo
```

通过标准：

- `catkin_make --pkg ...` 成功。
- `rospack find` 能找到上述包。
- `devel/lib` 下存在 rotors Gazebo 插件：

```bash
ls /home/jacob/racer_ws/devel/lib/librotors_gazebo_*so
```

### Step 1：Gazebo world 单独启动

- 做什么（具体操作）
  - 新建 `exploration_manager/launch/env_simulation.launch`。
  - 只启动 Gazebo world，不 spawn UAV。
  - Phase 1 推荐先用 `rotors_gazebo/worlds/basic.world`，该 world 已包含：
    - ground plane
    - sun
    - `librotors_gazebo_ros_interface_plugin.so`
    - ODE physics
- 修改/涉及文件（路径级别）
  - 新增：
    - `src/RACER/swarm_exploration/exploration_manager/launch/env_simulation.launch`
  - 参考：
    - `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/launch/mav_hovering_example.launch`
    - `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/worlds/basic.world`
- 为什么做
  - 先把 world 与 Gazebo ROS 接口跑通，避免同时排查模型、插件、控制器。
  - 这是最小闭环的第一层。
- 建议 launch 内容

```xml
<launch>
  <arg name="world_name" default="basic"/>
  <arg name="gui" default="true"/>
  <arg name="paused" default="true"/>
  <arg name="debug" default="false"/>
  <arg name="verbose" default="true"/>

  <env name="GAZEBO_MODEL_PATH" value="${GAZEBO_MODEL_PATH}:$(find rotors_gazebo)/models"/>
  <env name="GAZEBO_RESOURCE_PATH" value="${GAZEBO_RESOURCE_PATH}:$(find rotors_gazebo)/models"/>

  <include file="$(find gazebo_ros)/launch/empty_world.launch">
    <arg name="world_name" value="$(find rotors_gazebo)/worlds/$(arg world_name).world"/>
    <arg name="gui" value="$(arg gui)"/>
    <arg name="paused" value="$(arg paused)"/>
    <arg name="debug" value="$(arg debug)"/>
    <arg name="verbose" value="$(arg verbose)"/>
  </include>
</launch>
```

- 如何验证（必须可执行）

```bash
cd /home/jacob/racer_ws
source devel/setup.bash
roslaunch exploration_manager env_simulation.launch world_name:=basic paused:=true verbose:=true
```

另开终端：

```bash
source /home/jacob/racer_ws/devel/setup.bash
rostopic echo -n 1 /clock
rosservice list | grep /gazebo
```

通过标准：

- Gazebo GUI 打开。
- world 正常显示 ground plane 和 sun。
- `/clock` 正常发布。
- `/gazebo/spawn_urdf_model`、`/gazebo/unpause_physics` 等服务存在。
- 终端没有 `Failed to load plugin librotors_gazebo_ros_interface_plugin.so`。

### Step 2：加载 rotors 仿真框架

- 做什么（具体操作）
  - 在 Step 1 的 world launch 基础上确认 rotors model/resource 路径、插件库路径正确。
  - 确保 `source devel/setup.bash` 后 Gazebo 能找到：
    - rotors models
    - rotors worlds
    - rotors plugins
- 修改/涉及文件（路径级别）
  - 检查/必要时补充：
    - `src/RACER/swarm_exploration/exploration_manager/launch/env_simulation.launch`
  - 不修改 Racer 核心算法。
- 为什么做
  - spawn_model 能加载 URDF 不代表 Gazebo 能加载模型 mesh 和插件。
  - 如果 `GAZEBO_MODEL_PATH` 或 catkin plugin path 缺失，后续会出现模型不完整、插件未加载。
- 如何验证（必须可执行）

```bash
source /home/jacob/racer_ws/devel/setup.bash
echo "$GAZEBO_MODEL_PATH" | tr ':' '\n' | grep rotors_gazebo
echo "$GAZEBO_RESOURCE_PATH" | tr ':' '\n' | grep rotors_gazebo
rospack plugins --attrib=plugin gazebo_ros
```

运行 Gazebo 后检查：

```bash
gz topic -l | head
rostopic list | grep -E '^/clock|^/gazebo'
```

通过标准：

- Gazebo 不报找不到 model/resource。
- `gz topic -l` 能返回 Gazebo transport topic。
- ROS 侧 `/clock`、`/gazebo/*` 正常。

### Step 3：UAV spawn 成功

- 做什么（具体操作）
  - 新建 `exploration_manager/launch/uav_simulation.launch`。
  - 只负责单 UAV spawn、状态发布、基础控制器加载。
  - 推荐先使用 `mav_name:=iris`。
- 修改/涉及文件（路径级别）
  - 新增：
    - `src/RACER/swarm_exploration/exploration_manager/launch/uav_simulation.launch`
  - 参考：
    - `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/launch/spawn_mav.launch`
    - `src/RACER/swarm_exploration/fuae_gazebo/launch/spawn_mav.launch`
    - `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/launch/mav_hovering_example.launch`
- 为什么做
  - 满足验收要求：`roslaunch exploration_manager uav_simulation.launch` 可显示无人机。
  - 与 world launch 解耦后，spawn 问题可以单独重试，不需要反复重启 Gazebo。
- 建议 launch 内容

```xml
<launch>
  <arg name="mav_name" default="iris"/>
  <arg name="namespace" default="$(arg mav_name)"/>
  <arg name="x" default="0.0"/>
  <arg name="y" default="0.0"/>
  <arg name="z" default="0.1"/>
  <arg name="enable_logging" default="false"/>
  <arg name="enable_ground_truth" default="true"/>

  <group ns="$(arg namespace)">
    <include file="$(find rotors_gazebo)/launch/spawn_mav.launch">
      <arg name="mav_name" value="$(arg mav_name)"/>
      <arg name="namespace" value="$(arg namespace)"/>
      <arg name="model" value="$(find rotors_description)/urdf/$(arg mav_name)_base.xacro"/>
      <arg name="x" value="$(arg x)"/>
      <arg name="y" value="$(arg y)"/>
      <arg name="z" value="$(arg z)"/>
      <arg name="enable_logging" value="$(arg enable_logging)"/>
      <arg name="enable_ground_truth" value="$(arg enable_ground_truth)"/>
    </include>

    <node name="robot_state_publisher" pkg="robot_state_publisher" type="robot_state_publisher"/>
    <node name="joint_state_publisher" pkg="joint_state_publisher" type="joint_state_publisher"/>
  </group>
</launch>
```

- 如何验证（必须可执行）

终端 1：

```bash
cd /home/jacob/racer_ws
source devel/setup.bash
roslaunch exploration_manager env_simulation.launch world_name:=basic paused:=true verbose:=true
```

终端 2：

```bash
source /home/jacob/racer_ws/devel/setup.bash
roslaunch exploration_manager uav_simulation.launch mav_name:=iris namespace:=iris x:=0 y:=0 z:=0.1
```

终端 3：

```bash
source /home/jacob/racer_ws/devel/setup.bash
rosservice call /gazebo/get_model_state '{model_name: iris, relative_entity_name: world}'
rostopic list | grep '^/iris'
```

通过标准：

- Gazebo 中出现 `iris` 模型。
- `/gazebo/get_model_state` 返回 `success: True`。
- 模型不穿模、不爆炸、不倒飞。
- 至少出现 `/iris/imu`、`/iris/odometry_sensor1/odometry` 或 `/iris/ground_truth/odometry`、`/iris/joint_states` 等 topic。

### Step 4：插件加载成功（动力学生效）

- 做什么（具体操作）
  - 在 `uav_simulation.launch` 中加入 `rotors_control/lee_position_controller_node`。
  - 使用 rotors 自带 yaml 参数。
  - 将 controller 的 `odometry` remap 到 UAV odometry plugin 输出。
- 修改/涉及文件（路径级别）
  - 修改：
    - `src/RACER/swarm_exploration/exploration_manager/launch/uav_simulation.launch`
  - 涉及：
    - `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/resource/lee_controller_iris.yaml`
    - `src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/resource/iris.yaml`
- 为什么做
  - UAV 能 spawn 只是模型加载成功；要“能动”，必须确认 controller、controller interface、motor model 三段都有效。
- 建议追加 launch 内容

```xml
<node name="lee_position_controller_node"
      pkg="rotors_control"
      type="lee_position_controller_node"
      output="screen">
  <rosparam command="load" file="$(find rotors_gazebo)/resource/lee_controller_$(arg mav_name).yaml"/>
  <rosparam command="load" file="$(find rotors_gazebo)/resource/$(arg mav_name).yaml"/>
  <remap from="odometry" to="odometry_sensor1/odometry"/>
</node>
```

该 node 必须放在 `<group ns="$(arg namespace)">` 内。

- 如何验证（必须可执行）

```bash
source /home/jacob/racer_ws/devel/setup.bash
rosnode list | grep lee_position_controller
rostopic info /iris/odometry_sensor1/odometry
rostopic info /iris/command/motor_speed
rostopic echo -n 1 /iris/odometry_sensor1/odometry
```

如果 `/iris/odometry_sensor1/odometry` 不存在，检查 ground truth odom：

```bash
rostopic list | grep odom
rostopic echo -n 1 /iris/ground_truth/odometry
```

通过标准：

- `lee_position_controller_node` 存在。
- `odometry` 输入有 publisher。
- `/iris/command/motor_speed` 有 publisher。
- Gazebo 终端没有以下错误：
  - `Failed to load plugin librotors_gazebo_motor_model.so`
  - `Failed to load plugin librotors_gazebo_controller_interface.so`
  - `Failed to load plugin librotors_gazebo_odometry_plugin.so`
  - `Failed to load plugin librotors_gazebo_imu_plugin.so`

### Step 5：简单控制输入（hover / command trajectory）

- 做什么（具体操作）
  - 首先使用 rotors 自带 `hovering_example` 发布一次 hover command。
  - 不接 Racer planner，不接传感器，不接地图。
  - 如果需要移动验证，再手动发布 `trajectory_msgs/MultiDOFJointTrajectory` 到 `/iris/command/trajectory`。
- 修改/涉及文件（路径级别）
  - 可选修改：
    - `src/RACER/swarm_exploration/exploration_manager/launch/uav_simulation.launch`
  - 推荐把 hovering example 做成可开关参数：

```xml
<arg name="start_hover" default="true"/>
<node if="$(arg start_hover)"
      name="hovering_example"
      pkg="rotors_gazebo"
      type="hovering_example"
      output="screen"/>
```

- 为什么做
  - `hovering_example` 已经和 rotors 的 `command/trajectory` 对齐，是验证物理闭环的最低成本方式。
  - 这一步证明 UAV 不是只被 spawn，而是能在物理引擎下响应控制。
- 如何验证（必须可执行）

终端 1：

```bash
source /home/jacob/racer_ws/devel/setup.bash
roslaunch exploration_manager env_simulation.launch world_name:=basic paused:=true verbose:=true
```

终端 2：

```bash
source /home/jacob/racer_ws/devel/setup.bash
roslaunch exploration_manager uav_simulation.launch mav_name:=iris namespace:=iris start_hover:=true
```

终端 3：

```bash
source /home/jacob/racer_ws/devel/setup.bash
rostopic echo -n 1 /iris/command/trajectory
rostopic echo -n 1 /iris/command/motor_speed
rostopic echo -n 1 /iris/odometry_sensor1/odometry
```

如 Gazebo 仍暂停：

```bash
rosservice call /gazebo/unpause_physics "{}"
```

通过标准：

- `/iris/command/trajectory` 收到 hover command。
- `/iris/command/motor_speed` 持续发布电机角速度。
- `/iris/odometry_sensor1/odometry` 的 z 值从初始高度向约 2m 变化，最终可悬停。
- Gazebo 中 UAV 能起飞或至少明显响应控制。

### Step 6：RViz 可视化验证

- 做什么（具体操作）
  - 启动 RViz 或 `odom_visualization`，只显示 UAV odom/TF。
  - 如果要沿用 Racer 的 odom 可视化习惯，将 Gazebo odom 最小代价 relay/remap 到 `/state_ukf/odom`。
- 修改/涉及文件（路径级别）
  - 优先不改核心算法。
  - 可新增一个只用于 Phase 1 的 launch：
    - `src/RACER/swarm_exploration/exploration_manager/launch/rviz_gazebo_mvp.launch`
  - 或复用已有：
    - `src/RACER/swarm_exploration/exploration_manager/launch/rviz.launch`
    - `src/RACER/uav_simulator/Utils/odom_visualization`
- 为什么做
  - Gazebo GUI 能显示模型，但 RViz 可以验证 ROS 侧 odom/TF 是否正常。
  - 后续接 Racer planner 时，`/state_ukf/odom` 是最小对接点。
- 如何验证（必须可执行）

```bash
source /home/jacob/racer_ws/devel/setup.bash
rosrun odom_visualization odom_visualization __name:=odom_visualization_iris _color/r:=0.0 _color/g:=1.0 _color/b:=0.0 _robot_scale:=1.0 /odom_visualization_iris/odom:=/iris/odometry_sensor1/odometry
```

或使用 `topic_tools` relay：

```bash
source /home/jacob/racer_ws/devel/setup.bash
rosrun topic_tools relay /iris/odometry_sensor1/odometry /state_ukf/odom
rostopic echo -n 1 /state_ukf/odom
```

再启动 RViz：

```bash
roslaunch exploration_manager rviz.launch
```

通过标准：

- RViz 中能看到 UAV odom 轨迹或模型。
- `rostopic echo -n 1 /state_ukf/odom` 有数据。
- `rosrun tf view_frames` 或 `rostopic echo -n 1 /tf` 能看到 UAV TF。

### Step 7：Phase 1 中 Racer 最小代价对接

- 做什么（具体操作）
  - Phase 1 不启动 Racer 核心 exploration/planning。
  - 只做 topic 级别兼容验证：
    - Gazebo odom relay 到 Racer 常用 odom 名称。
    - 简单控制继续使用 rotors `command/trajectory`。
  - 若必须验证 Racer `PositionCommand` 到 Gazebo 控制输入，则新增一个独立 adapter 节点，不改 `plan_manage`、`exploration_manager` 核心算法。
- 修改/涉及文件（路径级别）
  - 必选：
    - `src/RACER/swarm_exploration/exploration_manager/launch/uav_simulation.launch`
  - 可选新增：
    - `src/RACER/swarm_exploration/fuae_gazebo/src/position_cmd_to_rotors_trajectory.cpp`
    - `src/RACER/swarm_exploration/fuae_gazebo/CMakeLists.txt`
    - `src/RACER/swarm_exploration/fuae_gazebo/package.xml`
- 为什么做
  - Racer planner 输出 `quadrotor_msgs/PositionCommand`，rotors controller 需要 `trajectory_msgs/MultiDOFJointTrajectory`。
  - 直接改 Racer 核心算法风险高，违反 Phase 1 “最小系统跑通优先”原则。
  - 独立 adapter 是最小、可回滚、边界清晰的方案。
- 最小 topic 对接建议

```text
Gazebo odom:
  /iris/odometry_sensor1/odometry
    relay/remap →
  /state_ukf/odom

Gazebo imu:
  /iris/imu
    暂只验证 echo，不接入 Racer state estimator

Racer command（可选，不作为第一轮 MVP 必须项）:
  /planning/pos_cmd_1 或 /position_cmd
    adapter →
  /iris/command/trajectory
```

- 如何验证（必须可执行）

```bash
source /home/jacob/racer_ws/devel/setup.bash
rosrun topic_tools relay /iris/odometry_sensor1/odometry /state_ukf/odom
rostopic echo -n 1 /state_ukf/odom
rostopic echo -n 1 /iris/imu
```

如实现 adapter，再验证：

```bash
rostopic info /planning/pos_cmd_1
rostopic info /iris/command/trajectory
```

通过标准：

- Gazebo odom 能被 Racer 侧期望 topic 名称读取。
- 不需要启动 `swarm_exploration.launch` 或 `single_drone_exploration.xml`。
- 不引入 realsense、velodyne、`gazebo_map_generator`、`local_sensing_node/pcl_render_node`。

## 4. 最小运行命令（必须给）

### 启动 Gazebo

```bash
cd /home/jacob/racer_ws
source /opt/ros/$ROS_DISTRO/setup.bash
source devel/setup.bash
roslaunch exploration_manager env_simulation.launch world_name:=basic paused:=true gui:=true verbose:=true
```

### spawn UAV

另开终端：

```bash
cd /home/jacob/racer_ws
source devel/setup.bash
roslaunch exploration_manager uav_simulation.launch mav_name:=iris namespace:=iris x:=0 y:=0 z:=0.1 start_hover:=false
```

### 启动基础控制（hover）

如果 `uav_simulation.launch` 使用 `start_hover:=true`：

```bash
cd /home/jacob/racer_ws
source devel/setup.bash
roslaunch exploration_manager uav_simulation.launch mav_name:=iris namespace:=iris x:=0 y:=0 z:=0.1 start_hover:=true
```

如果已经 spawn，只单独发 hover command：

```bash
cd /home/jacob/racer_ws
source devel/setup.bash
ROS_NAMESPACE=iris rosrun rotors_gazebo hovering_example _x:=0.0 _y:=0.0 _z:=2.0 _yaw:=0.0
rosservice call /gazebo/unpause_physics "{}"
```

### 查看 Gazebo odom / imu

```bash
source /home/jacob/racer_ws/devel/setup.bash
rostopic echo -n 1 /iris/odometry_sensor1/odometry
rostopic echo -n 1 /iris/imu
rostopic echo -n 1 /iris/command/motor_speed
```

### 最小对接 Racer odom 命名

```bash
source /home/jacob/racer_ws/devel/setup.bash
rosrun topic_tools relay /iris/odometry_sensor1/odometry /state_ukf/odom
rostopic echo -n 1 /state_ukf/odom
```

### RViz 可视化

```bash
source /home/jacob/racer_ws/devel/setup.bash
roslaunch exploration_manager rviz.launch
```

或只启动 odom visualization：

```bash
source /home/jacob/racer_ws/devel/setup.bash
rosrun odom_visualization odom_visualization /odom_visualization/odom:=/iris/odometry_sensor1/odometry
```

## 5. Phase 1 验收标准（非常重要）

1. 环境可启动
   - 能通过以下命令一键启动 Gazebo：

```bash
roslaunch exploration_manager env_simulation.launch
```

   - Gazebo 无 fatal/error；允许不影响运行的 warning。
   - 指定 world 能正常加载。
   - `basic.world` 中 ground plane、sun、基础光照正常显示。
   - `/clock` 正常发布：

```bash
rostopic echo -n 1 /clock
```

2. 模型可正确加载
   - 能通过以下命令显示无人机：

```bash
roslaunch exploration_manager uav_simulation.launch
```

   - `iris` 或选定 UAV 在 Gazebo 中正确生成。
   - 模型不穿模、不散架、不倒飞。
   - 连杆、关节、碰撞体、惯性参数基本合理。
   - `/gazebo/get_model_state` 返回成功：

```bash
rosservice call /gazebo/get_model_state '{model_name: iris, relative_entity_name: world}'
```

3. 基础控制可用
   - 能通过 rotors `command/trajectory` 或 `command/pose` 驱动 UAV。
   - MVP 控制输入采用：

```bash
ROS_NAMESPACE=iris rosrun rotors_gazebo hovering_example _x:=0.0 _y:=0.0 _z:=2.0 _yaw:=0.0
```

   - `/iris/command/trajectory` 有消息。
   - `/iris/command/motor_speed` 有持续输出。
   - UAV 能起飞、悬停或执行简单位置变化。
   - Phase 1 不要求 `/cmd_vel`；若后续需要 `/cmd_vel`，应作为 adapter 输入转换到 `/iris/command/trajectory`，不能直接修改 Racer 核心算法。

4. 时钟与 TF 正常
   - `/clock` 正常发布。
   - 所有需要仿真时间的节点使用 `/use_sim_time:=true`。
   - TF 树至少包含：
     - `world`
     - `iris/base_link` 或等价 UAV base frame
     - `iris/imu_link` 或等价 IMU frame
   - 由于 Phase 1 禁止外部传感器，realsense/velodyne frame 不作为验收项。

5. Gazebo odom / imu 正常
   - Gazebo odom 可读：

```bash
rostopic echo -n 1 /iris/odometry_sensor1/odometry
```

   - Gazebo imu 可读：

```bash
rostopic echo -n 1 /iris/imu
```

   - 最小对接到 Racer odom 名称可用：

```bash
rosrun topic_tools relay /iris/odometry_sensor1/odometry /state_ukf/odom
rostopic echo -n 1 /state_ukf/odom
```

6. 基础场景闭环成立
   - UAV 能在场景中完成最基本动作：
     - 从地面附近起飞到约 2m。
     - 悬停保持。
     - 可通过新的 trajectory command 做小范围平移。
   - Phase 1 不要求导航链路、地图/定位/控制全链路。
   - 如果临时使用 Racer RViz/odom visualization，仅要求 odom 可视化闭环，不要求 exploration planner 跑通。

7. 良好的 launch 管理
   - 能通过以下命令打开 Gazebo 对应环境：

```bash
roslaunch exploration_manager env_simulation.launch
```

   - 能通过以下命令显示无人机：

```bash
roslaunch exploration_manager uav_simulation.launch
```

   - 两个 launch 均不启动：
     - realsense
     - velodyne
     - `gazebo_map_generator`
     - `local_sensing_node/pcl_render_node`
     - Racer exploration core

# Phase 2（简要规划）

目标：传感器配置完成，数据正常，具备完整建图、规划能力。

Phase 2 只在 Phase 1 全部验收通过后启动，建议拆为以下子阶段：

1. 传感器接入
   - 选择 UAV 模型挂载 realsense 或 velodyne。
   - 明确 sensor frame、update rate、噪声模型、Gazebo plugin。
   - 验证 `/camera/depth/*`、`/velodyne_points` 或对应点云 topic。
2. Gazebo 感知数据接入 Racer
   - 将 Gazebo depth/pointcloud 对接到 Racer 现有 `plan_env` / `local_sensing_node` / mapping 输入。
   - 统一 frame 与 timestamp，确保使用 `/clock`。
3. 建图闭环
   - 验证局部/全局 occupancy map 或 ESDF/TSDF 输入输出。
   - 再考虑是否启用 `gazebo_map_generator`。
4. 规划闭环
   - 将 Gazebo odom 接到 Racer planner。
   - 将 Racer `quadrotor_msgs/PositionCommand` 通过独立 adapter 转为 rotors `command/trajectory`，或实现 `PositionCommand -> motor/control` 的专用 Gazebo 控制桥。
5. 多机与复杂环境
   - 单机稳定后再扩展多 UAV namespace。
   - 最后再引入 Star-Searcher 复杂 world、随机地图、动态障碍。

# 常见错误排查（重点针对 Phase 1）

## world 加载失败

症状：

- Gazebo GUI 不打开。
- 终端出现 `Unable to find uri[model://...]`。
- 终端出现 `Failed to load plugin librotors_gazebo_ros_interface_plugin.so`。

排查：

```bash
source /home/jacob/racer_ws/devel/setup.bash
rospack find rotors_gazebo
echo "$GAZEBO_MODEL_PATH" | tr ':' '\n'
echo "$GAZEBO_RESOURCE_PATH" | tr ':' '\n'
ls /home/jacob/racer_ws/devel/lib/librotors_gazebo_ros_interface_plugin.so
```

处理：

- 确认已 `source devel/setup.bash`。
- 在 `env_simulation.launch` 中设置：

```xml
<env name="GAZEBO_MODEL_PATH" value="${GAZEBO_MODEL_PATH}:$(find rotors_gazebo)/models"/>
<env name="GAZEBO_RESOURCE_PATH" value="${GAZEBO_RESOURCE_PATH}:$(find rotors_gazebo)/models"/>
```

- 如果插件 so 不存在，重新构建：

```bash
cd /home/jacob/racer_ws
catkin_make --pkg rotors_gazebo_plugins rotors_gazebo
```

## spawn 失败

症状：

- `spawn_model` 报错。
- Gazebo 中没有 `iris`。
- `/gazebo/get_model_state` 返回 `success: False`。

排查：

```bash
source /home/jacob/racer_ws/devel/setup.bash
rosservice list | grep spawn
rosparam get /iris/robot_description >/tmp/iris.urdf
check_urdf /tmp/iris.urdf
rosservice call /gazebo/get_model_state '{model_name: iris, relative_entity_name: world}'
```

处理：

- 确认 Gazebo 已启动后再运行 `uav_simulation.launch`。
- 确认 xacro 可展开：

```bash
rosrun xacro xacro $(rospack find rotors_description)/urdf/iris_base.xacro mav_name:=iris namespace:=iris
```

- 若 `iris_base.xacro` 不完整，先退回 rotors 官方示例验证：

```bash
roslaunch rotors_gazebo mav_hovering_example.launch mav_name:=iris world_name:=basic
```

## plugin 未加载（最关键）

症状：

- UAV spawn 成功但像普通静态/自由落体模型一样，不响应控制。
- `/iris/command/motor_speed` 有消息但 UAV 不动。
- Gazebo 终端有 `Failed to load plugin`。

排查：

```bash
source /home/jacob/racer_ws/devel/setup.bash
ls devel/lib/librotors_gazebo_motor_model.so
ls devel/lib/librotors_gazebo_controller_interface.so
ls devel/lib/librotors_gazebo_odometry_plugin.so
ls devel/lib/librotors_gazebo_imu_plugin.so
rostopic info /iris/command/motor_speed
rostopic list | grep gazebo/command/motor_speed
```

处理：

- 重新构建插件：

```bash
cd /home/jacob/racer_ws
catkin_make --pkg rotors_gazebo_plugins rotors_description rotors_gazebo rotors_control
source devel/setup.bash
```

- 确认模型 xacro 中确实包含：
  - `controller_plugin_macro`
  - `librotors_gazebo_motor_model.so`
  - `librotors_gazebo_multirotor_base_plugin.so`
  - `librotors_gazebo_odometry_plugin.so`
  - `librotors_gazebo_imu_plugin.so`
- 确认 `lee_position_controller_node` 在 UAV namespace 内运行。

## UAV 不动

症状：

- UAV 正常 spawn。
- odom 正常。
- hover command 发出后 UAV 不起飞。

排查：

```bash
rostopic echo -n 1 /iris/command/trajectory
rostopic echo -n 1 /iris/odometry_sensor1/odometry
rostopic echo -n 1 /iris/command/motor_speed
rosservice call /gazebo/get_physics_properties
```

处理：

- 解除暂停：

```bash
rosservice call /gazebo/unpause_physics "{}"
```

- 确认 odom remap：
  - `lee_position_controller_node` 订阅的是 `odometry`
  - 在 `uav_simulation.launch` 内应 remap 到 `odometry_sensor1/odometry`
- 确认命令 topic namespace：

```bash
ROS_NAMESPACE=iris rosrun rotors_gazebo hovering_example _x:=0 _y:=0 _z:=2 _yaw:=0
```

- 确认电机命令有 subscriber：

```bash
rostopic info /iris/command/motor_speed
```

## topic 不通

症状：

- `rostopic echo` 无输出。
- controller 没有收到 odom。
- Racer RViz 看不到 odom。

排查：

```bash
rostopic list | sort | grep -E 'iris|odom|imu|command|clock|tf'
rostopic info /iris/odometry_sensor1/odometry
rostopic info /iris/command/trajectory
rostopic info /iris/command/motor_speed
rosnode info /iris/lee_position_controller_node
```

处理：

- namespace 必须一致：
  - UAV namespace：`iris`
  - controller 在 `/iris` group 内
  - hover command 用 `ROS_NAMESPACE=iris`
- 如果 Racer 侧需要 `/state_ukf/odom`：

```bash
rosrun topic_tools relay /iris/odometry_sensor1/odometry /state_ukf/odom
```

- Phase 1 不启动多机 remap，避免 `/state_ukf/odom_1`、`/state_ukf/odom`、`/iris/odometry_sensor1/odometry` 混用。

## Racer topic 与 Gazebo topic 对接总结

Racer 控制/规划侧：

```text
traj_server:
  subscribe /odom_world
  publish   /position_cmd                  quadrotor_msgs/PositionCommand

single_drone_exploration.xml:
  /odom_world    -> $(arg odom_prefix)_$(arg drone_id)
  /position_cmd  -> planning/pos_cmd_$(arg drone_id)

so3_control:
  subscribe ~odom
  subscribe ~position_cmd
  subscribe ~imu
  publish   ~so3_cmd

poscmd_2_odom:
  subscribe ~command
  publish   ~odometry
```

Gazebo/rotors 侧：

```text
lee_position_controller_node:
  subscribe /iris/command/pose
  subscribe /iris/command/trajectory
  subscribe /iris/odometry_sensor1/odometry
  publish   /iris/command/motor_speed

Gazebo plugins:
  publish /iris/odometry_sensor1/odometry
  publish /iris/imu
  consume /iris/gazebo/command/motor_speed
```

Phase 1 最小代价对接原则：

- 第一轮 MVP 不接 Racer planner，只用 rotors hover command。
- odom 只做 relay/remap：

```bash
rosrun topic_tools relay /iris/odometry_sensor1/odometry /state_ukf/odom
```

- 如必须让 Racer `PositionCommand` 驱动 Gazebo，则新增独立 adapter：

```text
/planning/pos_cmd_1 或 /position_cmd
  quadrotor_msgs/PositionCommand
    ↓
position_cmd_to_rotors_trajectory
    ↓
/iris/command/trajectory
  trajectory_msgs/MultiDOFJointTrajectory
```

- adapter 不属于第一轮 smoke test，必须在 world、spawn、plugin、hover 都通过后再做。

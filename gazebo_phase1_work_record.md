# Gazebo Phase 1 工作记录

## 完成内容

本次按照 `plan.md` 完成了 Phase 1 的 Gazebo Classic 最小可运行闭环配置，目标是：启动 `MAP1.world`、生成单架 UAV、加载 rotors Lee position controller、发布 hover 指令、驱动 Gazebo 电机模型，并把 Gazebo odom 最小对接到 Racer 常用 `/state_ukf/odom`。

## 修改与新增文件

### 新增 `exploration_manager/launch/env_simulation.launch`

路径：

```text
src/RACER/swarm_exploration/exploration_manager/launch/env_simulation.launch
```

功能：

- 启动 `gazebo_ros/empty_world.launch`。
- 默认加载 `fuae_gazebo/worlds/MAP1.world`。
- 设置 `GAZEBO_MODEL_PATH`、`GAZEBO_RESOURCE_PATH`，确保 Gazebo 能找到 rotors 模型与资源。
- 设置 `/use_sim_time=true`。
- 不 spawn UAV，不启动 Racer exploration/planning 核心节点。

### 新增 `exploration_manager/launch/uav_simulation.launch`

路径：

```text
src/RACER/swarm_exploration/exploration_manager/launch/uav_simulation.launch
```

功能：

- 默认生成单架 `iris` UAV。
- 默认出生点为 `x=-9.0, y=-4.5, z=0.1`，避开 `MAP1.world` 原点附近墙体。
- 默认模型使用：

```text
$(find rotors_gazebo)/models/rotors_description/urdf/iris_base.xacro
```

- 启动：
  - `rotors_gazebo/launch/spawn_mav.launch`
  - `rotors_control/lee_position_controller_node`
  - `robot_state_publisher`
  - `joint_state_publisher`
  - 可选 `rotors_gazebo/hovering_example`
- 默认将 Lee controller odom 输入 remap 到：

```text
/iris/ground_truth/odometry
```

- 默认 relay Gazebo odom 到 Racer 常用 topic：

```text
/iris/ground_truth/odometry -> /state_ukf/odom
```

- 默认自动调用 `/gazebo/unpause_physics`，避免需要手动 unpause。
- 默认 hover 目标绑定到出生点水平坐标，目标高度 `z=2.0`，避免无人机从出生点飞向 MAP1 原点墙体。

### 新增 `exploration_manager/launch/gazebo_phase1.launch`

路径：

```text
src/RACER/swarm_exploration/exploration_manager/launch/gazebo_phase1.launch
```

功能：

- 一键启动 Phase 1：
  - `MAP1.world`
  - 单架 `iris`
  - Lee controller
  - odom relay
  - hover command
- MAP1 加载较重，因此组合启动中使用延迟：
  - `spawn_delay:=45.0`
  - `unpause_delay:=50.0`
  - `hover_delay:=55.0`
- 这样可以避免 `spawn_model` 在 MAP1 尚未稳定时超时。

### 修改 `rotors_gazebo/launch/spawn_mav.launch`

路径：

```text
src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/launch/spawn_mav.launch
```

修改内容：

- 增加 spawn 姿态参数：
  - `roll`
  - `pitch`
  - `yaw`
- 增加 xacro 参数：
  - `enable_wind`
  - `rotors_description_dir`
- 在 `spawn_model` 参数中补齐 `-R/-P/-Y`。

原因：

- Phase 1 默认使用的 `iris_base.xacro` 位于 `rotors_gazebo/models/rotors_description/urdf`，需要显式传入 `rotors_description_dir`。
- 保留通用 spawn 能力，后续切换模型时可以通过 launch arg 复用。

### 修改 `rotors_gazebo/models/rotors_description/urdf/iris.xacro`

路径：

```text
src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/iris.xacro
```

修改内容：

```xml
<xacro:property name="namespace" value="$(arg namespace)" />
```

原因：

- 原文件将 `namespace` 硬编码为空，导致 Gazebo 插件发布到 `/imu`、`/ground_truth/odometry`、`/gazebo/command/motor_speed`。
- 修正后插件按 launch namespace 发布到 `/iris/...`，与 controller 和验收 topic 对齐。

### 修改 `rotors_gazebo/models/rotors_description/urdf/iris_base.xacro`

路径：

```text
src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/iris_base.xacro
```

修改内容：

```xml
<xacro:controller_plugin_macro namespace="${namespace}" imu_sub_topic="imu" />
```

原因：

- `iris_base.xacro` 原本没有 controller interface 插件。
- Lee controller 会发布 `/iris/command/motor_speed`，但 Gazebo motor model 订阅 `/iris/gazebo/command/motor_speed`。
- 补充 controller interface 后，电机速度命令可以正确转发，UAV 能在 Gazebo 物理引擎中起飞并悬停。

### 修改 `rotors_gazebo/models/rotors_description/urdf/multirotor_base.xacro`

路径：

```text
src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/urdf/multirotor_base.xacro
```

修改内容：

```xml
package://rotors_gazebo/models/rotors_description/meshes/...
```

原因：

- `iris` 的真实可视 mesh 位于 `rotors_gazebo/models/rotors_description/meshes`。
- 原 URI 指向 `package://rotors_description/meshes/...`，而当前 `rotors_description` 包没有 `iris.stl`、`iris_prop_ccw.dae`、`iris_prop_cw.dae`。
- 这会导致 Gazebo 里模型和话题存在、物理闭环正常，但 GUI 中机体 visual 不显示。
- 修正后新 spawn 的 `iris` 使用存在的 body 和 propeller mesh，GUI 可正常渲染无人机。

## 依赖处理

当前系统没有可用的 `ros-noetic-mav-msgs` apt 包，且 sudo 安装需要密码，因此加入源码依赖：

```text
src/mav_comm
```

该仓库提供 Phase 1 必需的 `mav_msgs/Actuators` 等消息，使 `rotors_control`、`rotors_gazebo_plugins`、`rotors_gazebo` 可构建和运行。

## 构建验证

已成功构建 Phase 1 运行所需包：

```bash
cd /home/jacob/racer_ws
source /opt/ros/noetic/setup.bash
catkin_make --pkg mav_msgs rotors_comm rotors_gazebo_plugins rotors_description rotors_control rotors_gazebo fuae_gazebo
```

已确认 rotors Gazebo 插件生成在：

```text
devel/lib/librotors_gazebo_motor_model.so
devel/lib/librotors_gazebo_controller_interface.so
devel/lib/librotors_gazebo_odometry_plugin.so
devel/lib/librotors_gazebo_imu_plugin.so
devel/lib/librotors_gazebo_ros_interface_plugin.so
```

说明：

- 单独构建 `exploration_manager` 的 C++ 节点时，当前代码库暴露既有依赖/消息生成问题：
  - `bspline/Bspline.h`
  - `lkh_tsp_solver/SolveTSP.h`
- Phase 1 新增的是 launch 入口，不依赖 `exploration_manager` C++ 节点；Gazebo Phase 1 闭环已单独验证通过。

## 运行命令

### 终端 1：启动 Gazebo world

```bash
cd /home/jacob/racer_ws
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch exploration_manager env_simulation.launch
```

可选 headless：

```bash
roslaunch exploration_manager env_simulation.launch gui:=false paused:=false verbose:=false
```

### 终端 2：spawn UAV 并启动 hover 闭环

```bash
cd /home/jacob/racer_ws
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch exploration_manager uav_simulation.launch
```

默认参数等价于：

```bash
roslaunch exploration_manager uav_simulation.launch mav_name:=iris namespace:=iris start_hover:=true
```

只 spawn 和启动 controller，不自动 hover：

```bash
roslaunch exploration_manager uav_simulation.launch start_hover:=false
```

## 验收结果

### Gazebo world

已验证：

```bash
rostopic echo -n 1 /clock
rosservice list | grep /gazebo
```

结果：

- `/clock` 正常发布。
- `/gazebo/spawn_urdf_model`、`/gazebo/unpause_physics` 等服务存在。
- `MAP1.world` 可加载。
- `/gazebo/get_world_properties` 可看到：

```text
20230316
window1
window2
window3
window4
iris
```

### UAV spawn

已验证：

```bash
rosservice call /gazebo/get_model_state '{model_name: iris, relative_entity_name: world}'
```

结果：

```text
success: True
```

### UAV visual mesh

已验证生成后的 `/iris/robot_description` 包含真实存在的可视 mesh：

```text
package://rotors_gazebo/models/rotors_description/meshes/iris.stl
package://rotors_gazebo/models/rotors_description/meshes/iris_prop_ccw.dae
package://rotors_gazebo/models/rotors_description/meshes/iris_prop_cw.dae
```

对应文件均存在于：

```text
src/RACER/swarm_exploration/rotors_simulator/rotors_gazebo/models/rotors_description/meshes
```

修复后已删除旧 `iris` 并重新启动 `uav_simulation.launch`，新 `iris` 状态：

```text
x ~= -8.874
y ~= -4.500
z ~= 1.978
success: True
```

### 控制闭环

已验证 topic：

```text
/iris/command/trajectory
/iris/command/motor_speed
/iris/gazebo/command/motor_speed
/iris/ground_truth/odometry
/iris/imu
/state_ukf/odom
```

关键结果：

```text
odom_z ~= 1.978 m
motor angular_velocities ~= [663, 663, 663, 663] rad/s
```

说明 UAV 已在 `MAP1.world` 中从 `(-9.0, -4.5, 0.1)` 附近起飞，并稳定悬停在约 2 m。

最终一键验证命令：

```bash
cd /home/jacob/racer_ws
source /opt/ros/noetic/setup.bash
source devel/setup.bash
roslaunch exploration_manager gazebo_phase1.launch
```

headless 验证结果：

```text
world models:
  - 20230316
  - window1
  - window2
  - window3
  - window4
  - iris
success: True

iris state:
  x ~= -8.874
  y ~= -4.500
  z ~= 1.978

topics:
  /clock
  /iris/command/motor_speed
  /iris/command/trajectory
  /iris/gazebo/command/motor_speed
  /iris/ground_truth/odometry
  /iris/imu
  /state_ukf/odom
```

### Gazebo odom / imu / Racer odom relay

已验证：

```bash
rostopic echo -n 1 /iris/ground_truth/odometry
rostopic echo -n 1 /iris/imu
rostopic echo -n 1 /state_ukf/odom
```

结果：

- `/iris/ground_truth/odometry` 有 Gazebo 发布者。
- `/iris/imu` 有 Gazebo 发布者。
- `/state_ukf/odom` 可收到 relay 后的 Gazebo odom。

### TF

已验证 `/tf` 包含：

```text
world
iris/base_link
iris/rotor_0
iris/rotor_1
iris/rotor_2
iris/rotor_3
```

## Phase 1 边界

本阶段没有启动或接入：

- `gazebo_map_generator`
- realsense
- velodyne
- `local_sensing_node/pcl_render_node`
- Racer exploration/planning 主算法
- 多 UAV swarm launch

当前 Phase 1 仅完成 Gazebo 物理闭环和最小 topic 级别兼容。

# Lab 12: pick and place in Gazebo (Kinova Gen3 + MoveIt 2)

A Kinova Gen3 arm with a Robotiq 2F-85 gripper on a table, a red cube, MoveIt 2 and RViz.
Your task: complete `lab12_pick_place/src/pick_place.cpp` so the arm picks the cube and leaves
it at the place spot. Same MoveIt API as Lab 11 (`go_to_pose`, `draw_square`).

Ubuntu 24.04 + ROS 2 Jazzy.

## 1. Install (once)

```bash
sudo apt update
sudo apt install ros-jazzy-moveit ros-jazzy-ros2-controllers ros-jazzy-rmw-cyclonedds-cpp \
  ros-jazzy-kinova-gen3-7dof-robotiq-2f-85-moveit-config ros-jazzy-kortex-description \
  ros-jazzy-ros-gz ros-jazzy-gz-ros2-control ros-jazzy-ros2controlcli
```

Keep ROS 2 and Gazebo inside your PC (otherwise you see your classmates' robots):

```bash
echo 'export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST' >> ~/.bashrc
echo 'export GZ_IP=127.0.0.1' >> ~/.bashrc
```

## 2. Build

```bash
mkdir -p ~/lab12_ws/src
cd ~/lab12_ws/src
git clone https://github.com/Gruzver/kinova-gazebo.git
cd ~/lab12_ws
colcon build --allow-overriding robotiq_description
```

`robotiq_description` in this repository replaces the older one installed by apt.

## 3. Run

```bash
# Terminal 1: Gazebo + robot + cube + MoveIt + RViz
source ~/lab12_ws/install/setup.bash
ros2 launch lab12_bringup lab12.launch.py

# Terminal 2: your node
source ~/lab12_ws/install/setup.bash
ros2 run lab12_pick_place pick_place
```

After editing the `.cpp`: `colcon build --packages-select lab12_pick_place`, then run again.
To start over, close terminal 1 (Ctrl+C) and launch it again: the cube goes back to its place.

## The scene

| | Position in `base_link` (m) |
|---|---|
| Table surface | z = 0 |
| Cube centre (5 cm cube) | (0.50, 0.00, 0.025) |
| Blue basket (place spot) | centre (0.50, -0.30), 18 cm inside, 5 cm high |

- Planning groups: `manipulator` (arm, tip `end_effector_link`) and `gripper`.
- Named poses: `Home` (arm), `Open` and `Close` (gripper).
- `Home`: gripper pointing down at about (0.40, -0.03, 0.30).
- Gripper pointing down: roll = π, pitch = 0, yaw = π (as in `Home`). The fingers close along x.
- Grasping: when the fingers stop on the cube while closing, the simulation holds the cube in the
  gripper and terminal 1 prints `Object detected: cube grasped`; opening the gripper releases it
  (like the object detection of the real Robotiq). `/gripper/object_detected` (`std_msgs/msg/Bool`)
  says whether the gripper is holding the cube.

## Depth cameras

| Camera | Topics | Frame |
|---|---|---|
| Wrist (the Gen3 vision module), looks where the gripper points; 320x240, 10 Hz | `/wrist_mounted_camera/...` | `camera_color_frame` |
| Scene, fixed, looks at the table from the front; 320x240, 5 Hz | `/scene_camera/...` | `scene_camera` |

Each camera publishes `image` (`sensor_msgs/msg/Image`, color), `depth_image` (`Image`, depth in
metres), `points` (`sensor_msgs/msg/PointCloud2`, colored) and `camera_info`. The frames have
x forward (along the camera view). The wrist camera measures depth from 0.15 m.

RViz shows both point clouds, the three camera images (wrist color, wrist depth, scene) and the
frames `world`, `end_effector_link`, `camera_color_frame` and `scene_camera`.

## If something fails

| Message | Fix |
|---|---|
| `Package 'lab12_bringup' not found` | `source ~/lab12_ws/install/setup.bash` in that terminal |
| `Planning failed` | pose out of reach or in collision: check x, y, z |
| `Only N % of the line` | the straight line is not reachable: move the points closer to (0.5, 0, 0.2) |
| No `Object detected` after closing | the fingers did not close around the cube: check x, y and `kGraspZ` |

`No 3D sensor plugin(s) defined for octomap updates` and `/recognize_objects not available`
are normal.

## Credits and licenses

This repository is BSD-3-Clause (`LICENSE`); files derived from other projects keep their headers.
`robotiq_description` is from [PickNikRobotics/ros2_robotiq_gripper](https://github.com/PickNikRobotics/ros2_robotiq_gripper)
(BSD-3-Clause, commit a74d007). Robot description, MoveIt configuration and launch files are based on
[Kinovarobotics/ros2_kortex](https://github.com/Kinovarobotics/ros2_kortex) 0.2.6.

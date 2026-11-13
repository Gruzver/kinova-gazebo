# Kinova Gen3 pick and place in Gazebo

[![ROS 2 Jazzy](https://img.shields.io/badge/ROS%202-Jazzy-22314E?logo=ros&logoColor=white)](https://docs.ros.org/en/jazzy/)
[![Gazebo Harmonic](https://img.shields.io/badge/Gazebo-Harmonic-F58113)](https://gazebosim.org/docs/harmonic/)
[![Ubuntu 24.04](https://img.shields.io/badge/Ubuntu-24.04-E95420?logo=ubuntu&logoColor=white)](https://releases.ubuntu.com/24.04/)
[![MoveIt 2](https://img.shields.io/badge/MoveIt-2-0A5DA4)](https://github.com/moveit/moveit2)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD--3--Clause-blue)](LICENSE)

Pick-and-place lab with ROS 2 Jazzy, Gazebo Harmonic and MoveIt 2: a Kinova Gen3 arm with a
Robotiq 2F-85 gripper picks a red cube and leaves it in a blue basket.

![Expected result: Gazebo (left) and RViz with the wrist and scene cameras (right)](docs/demo.gif)

## Requirements

Ubuntu 24.04 with [ROS 2 Jazzy](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
(desktop and `ros-dev-tools`).

## Installation

**1. Packages**

```bash
sudo apt update
sudo apt install ros-jazzy-moveit ros-jazzy-ros2-controllers ros-jazzy-rmw-cyclonedds-cpp \
  ros-jazzy-kinova-gen3-7dof-robotiq-2f-85-moveit-config ros-jazzy-kortex-description \
  ros-jazzy-ros-gz ros-jazzy-gz-ros2-control ros-jazzy-ros2controlcli
```

**2. Environment**: Cyclone DDS, and ROS 2 and Gazebo kept inside your PC so you don't see your
classmates' robots.

```bash
echo 'export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp' >> ~/.bashrc
echo 'export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST' >> ~/.bashrc
echo 'export GZ_IP=127.0.0.1' >> ~/.bashrc
```

Then close the terminal and open a new one.

**3. Clone and build**

```bash
mkdir -p ~/kinova_ws/src && cd ~/kinova_ws/src
git clone https://github.com/Gruzver/kinova-gazebo.git
cd ~/kinova_ws
colcon build --allow-overriding robotiq_description   # the repo ships a newer robotiq_description
```

## Run

```bash
# Terminal 1: Gazebo, MoveIt and RViz
source ~/kinova_ws/install/setup.bash
ros2 launch kinova_gazebo_bringup sim.launch.py

# Terminal 2: your node
source ~/kinova_ws/install/setup.bash
ros2 run kinova_pick_place pick_place
```

Your code goes in [`kinova_pick_place/src/pick_place.cpp`](kinova_pick_place/src/pick_place.cpp)
(TODO 2 to 7). After each change, rebuild and run it again:

```bash
cd ~/kinova_ws && colcon build --packages-select kinova_pick_place
```

To put the cube back, stop terminal 1 (Ctrl+C) and launch it again.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Package 'kinova_gazebo_bringup' not found` | Run `source ~/kinova_ws/install/setup.bash` in that terminal. |
| Classmates' robots appear, or the two terminals don't see each other | Check the three lines of step 2 in `~/.bashrc` and open new terminals. |
| `ros2 topic list` shows old topics after editing `~/.bashrc` | Run `ros2 daemon stop`. |
| `Planning failed` | The pose is out of reach or in collision: check x, y, z. |
| `Only N % of the line` | The straight line is not reachable: move the points closer to (0.5, 0, 0.2). |
| No `Object detected` after closing | The fingers missed the cube: check x, y and `kGraspZ`. |
| `No 3D sensor plugin(s) defined for octomap updates`, `/recognize_objects not available` | Normal, ignore them. |

## License

BSD-3-Clause, see [LICENSE](LICENSE). The launch files based on
[ros2_kortex](https://github.com/Kinovarobotics/ros2_kortex) keep their Apache-2.0 license
([LICENSE-APACHE](LICENSE-APACHE)). `robotiq_description` is a copy of
[ros2_robotiq_gripper](https://github.com/PickNikRobotics/ros2_robotiq_gripper) (BSD-3-Clause).

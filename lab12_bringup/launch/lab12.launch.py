# Lab 12: Kinova Gen3 + Robotiq 2F-85 in Gazebo (table + cube), with MoveIt and RViz.
#
# Based on kortex_bringup/launch/kortex_sim_control.launch.py
# Copyright (c) 2021 PickNik, Inc. Licensed under the Apache License, Version 2.0.
# Changed: Gen3 7-DoF + Robotiq 2F-85 + wrist camera only, lab12 world, gripper effort, grasp fix,
# starts MoveIt.

import os

import xacro
from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Fixes the cube to the gripper on /gripper/attach and releases it on /gripper/detach (see grasp_fix.py)
DETACHABLE_JOINT = """
  <gazebo>
    <plugin filename="gz-sim-detachable-joint-system" name="gz::sim::systems::DetachableJoint">
      <parent_link>bracelet_link</parent_link>
      <child_model>cube</child_model>
      <child_link>link</child_link>
      <attach_topic>/gripper/attach</attach_topic>
      <detach_topic>/gripper/detach</detach_topic>
      <suppress_child_warning>true</suppress_child_warning>
    </plugin>
  </gazebo>
"""


ROBOT_Z = 0.3  # robot base on top of the table
CAMERA_WIDTH, CAMERA_HEIGHT = 320, 240  # wrist camera; 640x480 point clouds are heavy for lab PCs


def configure_camera(robot_description):
    """Scale the wrist camera intrinsics (written for 640x480) and see from 15 cm."""
    # The world loads the Sensors system (ogre2); a second copy from the robot stalls rendering
    for plugin in robot_description.getElementsByTagName("plugin"):
        if plugin.getAttribute("filename") == "gz-sim-sensors-system":
            plugin.parentNode.removeChild(plugin)
    scale = CAMERA_WIDTH / 640
    for sensor in robot_description.getElementsByTagName("sensor"):
        for tag in ("fx", "fy", "p_fx", "p_fy"):
            for e in sensor.getElementsByTagName(tag):
                e.firstChild.data = str(554.25469 * scale)
        for tag, size in (("cx", CAMERA_WIDTH), ("p_cx", CAMERA_WIDTH), ("cy", CAMERA_HEIGHT), ("p_cy", CAMERA_HEIGHT)):
            for e in sensor.getElementsByTagName(tag):
                e.firstChild.data = str(size / 2 + 0.5)
        for depth in sensor.getElementsByTagName("depth_camera"):
            depth.getElementsByTagName("near")[0].firstChild.data = "0.15"
        # Gazebo writes the points in camera_color_frame (x forward) but labels them with the
        # optical frame, which is not in TF; without it the messages use camera_color_frame
        for optical in sensor.getElementsByTagName("optical_frame_id"):
            optical.parentNode.removeChild(optical)


def share(package):
    return get_package_share_directory(package)


def generate_launch_description():
    kortex = share("kortex_description")
    robot_description = xacro.process_file(
        os.path.join(kortex, "robots", "kinova.urdf.xacro"),
        mappings={
            "robot_ip": "xxx.yyy.zzz.www",
            "name": "gen3",
            "arm": "gen3",
            "dof": "7",
            "vision": "true",
            "camera_width": str(CAMERA_WIDTH),
            "camera_height": str(CAMERA_HEIGHT),
            "camera_fps": "10",
            "prefix": "",
            "sim_gazebo": "true",
            "gripper": "robotiq_2f_85",
            "simulation_controllers": os.path.join(
                share("lab12_bringup"), "config", "ros2_controllers.yaml"
            ),
        },
    )
    # Realistic grip: the default 50 N.m on the knuckles crushes the cube and overpowers the wrist
    for joint in robot_description.getElementsByTagName("joint"):
        limits = joint.getElementsByTagName("limit")  # skips the <joint> tags inside <ros2_control>
        if limits and joint.getAttribute("name") in ("robotiq_85_left_knuckle_joint", "robotiq_85_right_knuckle_joint"):
            limits[0].setAttribute("effort", "5")
    configure_camera(robot_description)
    robot_description = robot_description.toxml().replace("</robot>", DETACHABLE_JOINT + "</robot>")

    world = os.path.join(share("lab12_bringup"), "worlds", "lab12.sdf")
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(share("ros_gz_sim"), "launch", "gz_sim.launch.py")),
        launch_arguments={
            "gz_args": f"-r -v 3 {world} --physics-engine gz-physics-bullet-featherstone-plugin"
        }.items(),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[{"robot_description": robot_description, "use_sim_time": True}],
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=["-topic", "robot_description", "-name", "gen3", "-z", str(ROBOT_Z)],
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        output="screen",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/gripper/attach@std_msgs/msg/Empty]gz.msgs.Empty",
            "/gripper/detach@std_msgs/msg/Empty]gz.msgs.Empty",
            "/model/cube/pose@geometry_msgs/msg/PoseStamped[gz.msgs.Pose",
            "/wrist_mounted_camera/image@sensor_msgs/msg/Image[gz.msgs.Image",
            "/wrist_mounted_camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image",
            "/wrist_mounted_camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked",
            "/wrist_mounted_camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
        ],
    )

    grasp_fix = Node(
        package="lab12_bringup",
        executable="grasp_fix.py",
        output="screen",
        parameters=[{"use_sim_time": True, "base_z": ROBOT_Z}],
    )

    # The plugin attaches the cube when it is created; release it once at startup.
    # A detach sent before that first attach is ignored, hence the loop.
    release_cube = ExecuteProcess(
        cmd=[
            "bash",
            "-c",
            "for i in $(seq 20); do gz topic -t /gripper/detach -m gz.msgs.Empty -p 'unused: true'; sleep 0.2; done",
        ],
    )

    def spawner(controller):
        return Node(
            package="controller_manager",
            executable="spawner",
            arguments=[controller, "-c", "/controller_manager"],
        )

    joint_state_broadcaster = spawner("joint_state_broadcaster")

    moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(share("lab12_bringup"), "launch", "moveit.launch.py")),
        launch_arguments={"launch_rviz": LaunchConfiguration("launch_rviz")}.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            AppendEnvironmentVariable(
                "GZ_SIM_RESOURCE_PATH", os.path.join(get_package_prefix("robotiq_description"), "share")
            ),
            AppendEnvironmentVariable(
                "GZ_SIM_RESOURCE_PATH", os.path.join(get_package_prefix("kortex_description"), "share")
            ),
            gazebo,
            robot_state_publisher,
            spawn_robot,
            bridge,
            grasp_fix,
            joint_state_broadcaster,
            spawner("joint_trajectory_controller"),
            spawner("robotiq_gripper_controller"),
            RegisterEventHandler(OnProcessExit(target_action=spawn_robot, on_exit=[release_cube])),
            RegisterEventHandler(OnProcessExit(target_action=joint_state_broadcaster, on_exit=[moveit])),
        ]
    )

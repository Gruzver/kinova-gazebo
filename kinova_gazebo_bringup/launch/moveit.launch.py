# Based on kinova_gen3_7dof_robotiq_2f_85_moveit_config/launch/sim.launch.py
# Copyright (c) 2023 PickNik, Inc. Licensed under the Apache License, Version 2.0.
# Changed: wrist camera, kinova_gazebo_bringup's SRDF, moveit_controllers.yaml and RViz config,
# fix_start_state enabled.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    launch_rviz = LaunchConfiguration("launch_rviz")
    config_dir = os.path.join(get_package_share_directory("kinova_gazebo_bringup"), "config")

    moveit_config = (
        MoveItConfigsBuilder("gen3", package_name="kinova_gen3_7dof_robotiq_2f_85_moveit_config")
        .robot_description(
            mappings={
                "robot_ip": "xxx.yyy.zzz.www",
                "use_fake_hardware": "false",
                "gripper": "robotiq_2f_85",
                "dof": "7",
                "sim_gazebo": "true",
                "vision": "true",
            }
        )
        .robot_description_semantic(file_path=os.path.join(config_dir, "gen3.srdf"))
        .trajectory_execution(file_path=os.path.join(config_dir, "moveit_controllers.yaml"))
        .planning_scene_monitor(
            publish_robot_description=True, publish_robot_description_semantic=True
        )
        .planning_pipelines(pipelines=["ompl", "pilz_industrial_motion_planner"])
        .to_moveit_configs()
    )
    # Wrap continuous joints (joint_3 sits at +-pi) instead of rejecting the start state
    for pipeline in ("ompl", "pilz_industrial_motion_planner"):
        moveit_config.planning_pipelines[pipeline]["fix_start_state"] = True

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[moveit_config.to_dict(), {"use_sim_time": use_sim_time}],
        arguments=["--ros-args", "--log-level", "error"],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=[
            "-d",
            os.path.join(config_dir, "sim.rviz"),
        ],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.planning_pipelines,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
            {"use_sim_time": use_sim_time},
        ],
        condition=IfCondition(launch_rviz),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            move_group_node,
            rviz_node,
        ]
    )

#!/usr/bin/env python3
# Grasp fix for Gazebo (as gazebo_grasp_fix in Gazebo Classic): when the gripper fingers stop
# on the cube while closing, fix the cube to the gripper; release it when the gripper opens.

import math
from collections import deque

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from rclpy.time import Time
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, Empty
from tf2_ros import Buffer, TransformException, TransformListener

KNUCKLE = "robotiq_85_left_knuckle_joint"
FINGERTIPS = ("robotiq_85_left_finger_tip_link", "robotiq_85_right_finger_tip_link")
STALL_TIME = 0.1  # s without the fingers moving (the velocity reading is noisy in contact)
STALL_MOTION = 0.01  # rad


class GraspFix(Node):

    def __init__(self):
        super().__init__("grasp_fix")
        # Height of base_link in the Gazebo world (the robot is spawned there)
        self.base_z = self.declare_parameter("base_z", 0.3).value
        # Cube centre to the midpoint of the fingertips (m)
        self.max_distance = self.declare_parameter("max_distance", 0.05).value

        self.cube = None
        self.history = deque()  # (time, knuckle position) over the last STALL_TIME seconds
        self.attached = False
        self.attach_position = 0.0
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.attach_pub = self.create_publisher(Empty, "/gripper/attach", 10)
        self.detach_pub = self.create_publisher(Empty, "/gripper/detach", 10)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.detected_pub = self.create_publisher(Bool, "/gripper/object_detected", latched)
        self.detected_pub.publish(Bool(data=False))

        self.create_subscription(PoseStamped, "/model/cube/pose", self.on_cube, 10)
        self.create_subscription(JointState, "/joint_states", self.on_joints, 10)

    def on_cube(self, msg):
        p = msg.pose.position
        self.cube = (p.x, p.y, p.z - self.base_z)  # in base_link

    def cube_between_fingers(self):
        if self.cube is None:
            return False
        tips = []
        for name in FINGERTIPS:
            try:
                t = self.tf_buffer.lookup_transform("base_link", name, Time()).transform.translation
            except TransformException:
                return False
            tips.append((t.x, t.y, t.z))
        middle = [(tips[0][i] + tips[1][i]) / 2 for i in range(3)]
        return math.dist(middle, self.cube) < self.max_distance

    def on_joints(self, msg):
        if KNUCKLE not in msg.name:
            return
        position = msg.position[msg.name.index(KNUCKLE)]
        now = Time.from_msg(msg.header.stamp).nanoseconds * 1e-9
        self.history.append((now, position))
        while now - self.history[0][0] > STALL_TIME:
            self.history.popleft()
        recent = [p for _, p in self.history]
        stopped = now - self.history[0][0] > 0.8 * STALL_TIME and max(recent) - min(recent) < STALL_MOTION

        if not self.attached:
            # Fingers stopped part way (0 = open, 0.8 = closed) with the cube between them
            if 0.05 < position < 0.65 and stopped and self.cube_between_fingers():
                self.attach_pub.publish(Empty())
                self.attached = True
                self.attach_position = position
                self.detected_pub.publish(Bool(data=True))
                self.get_logger().info(f"Object detected: cube grasped (knuckle {position:.3f})")
        elif position < self.attach_position - 0.08:  # gripper opening (not a bounce)
            self.detach_pub.publish(Empty())
            self.attached = False
            self.detected_pub.publish(Bool(data=False))
            self.get_logger().info(f"Cube released (knuckle {position:.3f})")


def main():
    rclpy.init()
    rclpy.spin(GraspFix())


if __name__ == "__main__":
    main()

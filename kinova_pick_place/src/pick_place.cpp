#include <cmath>
#include <string>
#include <rclcpp/rclcpp.hpp>
#include <moveit/move_group_interface/move_group_interface.hpp>

using moveit::planning_interface::MoveGroupInterface;

// Positions in base_link (metres). The table surface is z = 0.
constexpr double kCubeX = 0.50, kCubeY = 0.00;    // red cube (5 cm)
constexpr double kPlaceX = 0.50, kPlaceY = -0.30;  // centre of the blue basket
constexpr double kGraspZ = 0.165;  // end_effector_link height with the fingers around the cube
constexpr double kAbove = 0.10;    // approach and leave 10 cm above
// Gripper pointing down, as in Home; the fingers close along x
constexpr double kRoll = M_PI, kPitch = 0.0, kYaw = M_PI;

// x, y, z in metres; roll, pitch, yaw in radians (same helper as in go_to_pose)
geometry_msgs::msg::Pose make_pose(double x, double y, double z,
                                   double r, double p, double yw)
{
  geometry_msgs::msg::Pose ps;
  ps.position.x = x;  ps.position.y = y;  ps.position.z = z;
  double cr = cos(r / 2),  sr = sin(r / 2);
  double cp = cos(p / 2),  sp = sin(p / 2);
  double cy = cos(yw / 2), sy = sin(yw / 2);
  ps.orientation.x = sr * cp * cy - cr * sp * sy;
  ps.orientation.y = cr * sp * cy + sr * cp * sy;
  ps.orientation.z = cr * cp * sy - sr * sp * cy;
  ps.orientation.w = cr * cp * cy + sr * sp * sy;
  return ps;
}

// Plan to the target already set on the group, then execute it
bool plan_and_execute(MoveGroupInterface & group, const rclcpp::Logger & logger,
                      const std::string & step)
{
  MoveGroupInterface::Plan plan;
  if (!group.plan(plan)) {
    RCLCPP_ERROR(logger, "Planning failed: %s", step.c_str());
    return false;
  }
  if (!group.execute(plan)) {
    RCLCPP_ERROR(logger, "Execution failed: %s", step.c_str());
    return false;
  }
  RCLCPP_INFO(logger, "Done: %s", step.c_str());
  return true;
}

// Straight line from the current pose to target (as in draw_square)
bool move_line(MoveGroupInterface & arm, const rclcpp::Logger & logger,
               const geometry_msgs::msg::Pose & target, const std::string & step)
{
  moveit_msgs::msg::RobotTrajectory traj;
  double fraction = arm.computeCartesianPath({target}, 0.01, traj);
  if (fraction < 0.99) {
    RCLCPP_ERROR(logger, "Only %.0f %% of the line: %s", fraction * 100, step.c_str());
    return false;
  }
  if (!arm.execute(traj)) {
    RCLCPP_ERROR(logger, "Execution failed: %s", step.c_str());
    return false;
  }
  RCLCPP_INFO(logger, "Done: %s", step.c_str());
  return true;
}

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  auto node = rclcpp::Node::make_shared("pick_place");
  auto logger = node->get_logger();

  // Planning groups from the SRDF: the arm and the Robotiq gripper
  MoveGroupInterface arm(node, "manipulator");
  MoveGroupInterface gripper(node, "gripper");
  arm.setMaxVelocityScalingFactor(0.3);

  // Start from Home, a known arm configuration. Named poses: Home (arm); Open, Close (gripper)
  arm.setNamedTarget("Home");
  bool ok = plan_and_execute(arm, logger, "Home");
  if (ok) {
    gripper.setNamedTarget("Open");
    ok = plan_and_execute(gripper, logger, "open gripper");
  }

  // 1. Above the cube (joint-space plan, as in go_to_pose)
  if (ok) {
    arm.setPoseTarget(make_pose(kCubeX, kCubeY, kGraspZ + kAbove, kRoll, kPitch, kYaw));
    ok = plan_and_execute(arm, logger, "above the cube");
  }

  // 2. TODO: go straight down to kGraspZ with move_line()

  // 3. TODO: close the gripper with the named target "Close"

  // 4. TODO: lift the cube straight up by kAbove

  // 5. TODO: move above the place spot (kPlaceX, kPlaceY)

  // 6. TODO: go down to kGraspZ + 0.005 and open the gripper

  // 7. TODO: leave straight up, then go to the named target "Home"

  rclcpp::shutdown();
  return ok ? 0 : 1;
}

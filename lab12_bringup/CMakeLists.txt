cmake_minimum_required(VERSION 3.8)
project(lab12_bringup)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch models worlds
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS scripts/grasp_fix.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()

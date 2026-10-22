# ROS 2 + Synapticon environment (sourced by the startdrives terminals)
source /opt/ros/lyrical/setup.bash
source /home/uexpj/ros2_ws/install/setup.bash

# Shortcuts for terminal 3
alias ctrls='ros2 control list_controllers'
velon()   { ros2 control switch_controllers --activate forward_velocity_controller; }
posvel()  { ros2 control switch_controllers --deactivate forward_velocity_controller --activate forward_position_controller; }
vel()     { ros2 topic pub --once /forward_velocity_controller/commands std_msgs/msg/Float64MultiArray "{data: [${1:-0.0}]}"; }
velstop() { vel 0.0; }
pos()     { ros2 topic pub --once /forward_position_controller/commands std_msgs/msg/Float64MultiArray "{data: [$1]}"; }
state()   { ros2 topic echo /joint_states --once; }
PS1="(ros-root) \w # "

# Start Synapticon EtherCAT + ROS 2 stack in one root tmux session (3 panes, one password).
# Every pane is logged to ~/ros2_ws/logs/<date_time>_T1/T2/T3.log
# Usage: startdrives [interface]   default enp3s0.  Zoom pane: Ctrl+b z.  Detach: Ctrl+b d.  Stop: stopdrives
startdrives() {
  sudo -v || return
  local ENV=/home/uexpj/ros2_ws/ros_env.sh
  local IFACE=${1:-enp3s0}
  local LOGDIR=/home/uexpj/ros2_ws/logs
  local STAMP=$(date +%Y%m%d_%H%M%S)
  mkdir -p "$LOGDIR"
  sudo tmux kill-session -t drives 2>/dev/null
  sudo tmux new-session -d -s drives "bash -c 'source $ENV; ros2 launch synapticon_ros2_control elevated_permissions_1_dof.launch.py; exec bash'"
  sudo tmux pipe-pane -t drives:0.0 -o "cat >> $LOGDIR/${STAMP}_T1.log"
  sleep 5
  sudo tmux split-window -h -t drives "bash -c 'source $ENV; ros2 launch synapticon_ros2_control single_dof.launch.py eth_device:=$IFACE gui:=false; exec bash'"
  sudo tmux pipe-pane -t drives:0.1 -o "cat >> $LOGDIR/${STAMP}_T2.log"
  sleep 3
  sudo tmux split-window -v -t drives "bash --rcfile $ENV"
  sudo tmux pipe-pane -t drives:0.2 -o "cat >> $LOGDIR/${STAMP}_T3.log"
  sudo tmux select-pane -t drives:0.2
  sudo tmux attach -t drives
}
stopdrives() { sudo tmux kill-session -t drives 2>/dev/null; sudo pkill -f ros2_control_node; sudo pkill -f "ros2 launch synapticon"; echo "drives stopped"; }
# Show the last lines of a pane log: panelog T2   (or T1, T3; optional line count: panelog T2 100)
panelog() { tail -n "${2:-40}" "$(ls -t /home/uexpj/ros2_ws/logs/*_"$1".log | head -1)"; }

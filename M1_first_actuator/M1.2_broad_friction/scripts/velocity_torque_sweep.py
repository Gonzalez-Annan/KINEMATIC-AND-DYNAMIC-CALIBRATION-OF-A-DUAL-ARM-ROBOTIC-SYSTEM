#!/usr/bin/env python3

import csv
import time
from pathlib import Path

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray


# ============================================================
# EXPERIMENT CONFIGURATION
# ============================================================

RATED_TORQUE_NM = 2.222
N_SWEEPS = 3

# Dense sampling close to zero to resolve Stribeck/stiction behavior.
VELOCITY_SEQUENCE = [
    0.0,

    # Very low-speed positive region
    0.01,
    0.02,
    0.03,
    0.05,
    0.075,
    0.10,
    0.15,
    0.20,
    0.30,
    0.40,
    0.50,

    # Medium / high positive region
    0.75,
    1.0,
    1.5,
    2.0,
    2.5,
    3.0,
    4.0,
    5.0,

    0.0,

    # Very low-speed negative region
    -0.01,
    -0.02,
    -0.03,
    -0.05,
    -0.075,
    -0.10,
    -0.15,
    -0.20,
    -0.30,
    -0.40,
    -0.50,

    # Medium / high negative region
    -0.75,
    -1.0,
    -1.5,
    -2.0,
    -2.5,
    -3.0,
    -4.0,
    -5.0,

    0.0,
]

COMMAND_TOPIC = "/forward_velocity_controller/commands"
JOINT_STATE_TOPIC = "/joint_states"

OUTPUT_DIR = Path(
    "/home/uexpj/ros2_ws/day2_velocity_torque_data"
)


# ============================================================
# VELOCITY-DEPENDENT TIMING
# ============================================================

def settling_time_for_velocity(v):
    a = abs(v)

    # Near zero we give the system more time to break away from
    # static friction and reach a stable low-speed regime.
    if a <= 0.10:
        return 5.0

    return 3.0


def recording_time_for_velocity(v):
    a = abs(v)

    # Zero itself does not need a long recording.
    if a < 1e-9:
        return 5.0

    # At very low speed the shaft travels only a small distance,
    # so record longer to observe friction over more motion.
    if a <= 0.05:
        return 15.0

    if a <= 0.20:
        return 10.0

    return 5.0


# ============================================================
# ROS NODE
# ============================================================

class VelocityTorqueExperiment(Node):

    def __init__(self):
        super().__init__("velocity_torque_experiment")

        self.publisher = self.create_publisher(
            Float64MultiArray,
            COMMAND_TOPIC,
            10,
        )

        self.subscription = self.create_subscription(
            JointState,
            JOINT_STATE_TOPIC,
            self.joint_state_callback,
            100,
        )

        self.recording = False
        self.current_command = 0.0
        self.current_sweep = 0
        self.current_point = 0

        self.samples = []

    def joint_state_callback(self, msg):

        if not self.recording:
            return

        if len(msg.name) == 0:
            return

        try:
            joint_index = msg.name.index("joint1")
        except ValueError:
            return

        position = msg.position[joint_index]
        velocity = msg.velocity[joint_index]
        torque_raw = msg.effort[joint_index]

        # Synapticon 0x6077:
        # per-thousand of motor rated torque (0x6076)
        torque_nm = (
            torque_raw / 1000.0
            * RATED_TORQUE_NM
        )

        self.samples.append({
            "wall_time_s": time.time(),

            "ros_time_s":
                msg.header.stamp.sec
                + msg.header.stamp.nanosec * 1e-9,

            "sweep": self.current_sweep,
            "point": self.current_point,

            "command_velocity_rad_s":
                self.current_command,

            "measured_position_rad":
                position,

            "measured_velocity_rad_s":
                velocity,

            "torque_raw_per_mille":
                torque_raw,

            "torque_Nm":
                torque_nm,
        })

    def publish_velocity(self, velocity):

        msg = Float64MultiArray()
        msg.data = [float(velocity)]

        self.current_command = velocity

        # Send several times so transition does not depend on
        # one isolated ROS message.
        for _ in range(5):
            self.publisher.publish(msg)
            rclpy.spin_once(
                self,
                timeout_sec=0.05,
            )

    def run_for(self, duration):

        end_time = time.monotonic() + duration

        while time.monotonic() < end_time:
            rclpy.spin_once(
                self,
                timeout_sec=0.05,
            )

    def run_experiment(self):

        print()
        print("==========================================")
        print("DAY 2 - VELOCITY / TORQUE CHARACTERIZATION")
        print("==========================================")
        print()

        print(
            f"Rated motor torque: "
            f"{RATED_TORQUE_NM:.3f} Nm"
        )
        print(
            "Timing: velocity dependent "
            "(longer close to zero)"
        )
        print(
            f"Sweeps: {N_SWEEPS}"
        )
        print()

        for sweep in range(1, N_SWEEPS + 1):

            print()
            print(
                f"========== SWEEP "
                f"{sweep}/{N_SWEEPS} =========="
            )

            self.current_sweep = sweep

            for point, velocity in enumerate(
                VELOCITY_SEQUENCE,
                start=1,
            ):

                self.current_point = point

                settling_time = (
                    settling_time_for_velocity(
                        velocity
                    )
                )

                recording_time = (
                    recording_time_for_velocity(
                        velocity
                    )
                )

                print()
                print(
                    f"[Sweep {sweep}] "
                    f"Point {point}: "
                    f"command = "
                    f"{velocity:+.3f} rad/s"
                )

                # --------------------------------------------
                # Command velocity
                # --------------------------------------------

                self.publish_velocity(
                    velocity
                )

                # --------------------------------------------
                # Settling
                # --------------------------------------------

                print(
                    f"  settling for "
                    f"{settling_time:.1f} s..."
                )

                self.recording = False

                self.run_for(
                    settling_time
                )

                # --------------------------------------------
                # Measurement
                # --------------------------------------------

                start_sample = len(
                    self.samples
                )

                print(
                    f"  recording for "
                    f"{recording_time:.1f} s..."
                )

                self.recording = True

                self.run_for(
                    recording_time
                )

                self.recording = False

                new_samples = (
                    self.samples[start_sample:]
                )

                if new_samples:

                    velocities = [
                        sample[
                            "measured_velocity_rad_s"
                        ]
                        for sample in new_samples
                    ]

                    torques = [
                        sample["torque_Nm"]
                        for sample in new_samples
                    ]

                    mean_velocity = (
                        sum(velocities)
                        / len(velocities)
                    )

                    mean_torque = (
                        sum(torques)
                        / len(torques)
                    )

                    print(
                        f"  samples:       "
                        f"{len(new_samples)}"
                    )

                    print(
                        f"  mean velocity: "
                        f"{mean_velocity:+.5f} "
                        f"rad/s"
                    )

                    print(
                        f"  mean torque:   "
                        f"{mean_torque:+.6f} "
                        f"Nm"
                    )

                else:

                    print(
                        "  WARNING: "
                        "no samples recorded!"
                    )

        # Always finish stopped
        print()
        print(
            "Experiment complete. "
            "Commanding 0 rad/s."
        )

        self.recording = False

        self.publish_velocity(
            0.0
        )

        self.run_for(
            1.0
        )


# ============================================================
# SAVE RAW DATA
# ============================================================

def save_csv(samples):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = time.strftime(
        "%Y%m%d_%H%M%S"
    )

    output_file = (
        OUTPUT_DIR
        / f"velocity_torque_raw_{timestamp}.csv"
    )

    fieldnames = [
        "wall_time_s",
        "ros_time_s",
        "sweep",
        "point",
        "command_velocity_rad_s",
        "measured_position_rad",
        "measured_velocity_rad_s",
        "torque_raw_per_mille",
        "torque_Nm",
    ]

    with output_file.open(
        "w",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(
            samples
        )

    return output_file


# ============================================================
# MAIN
# ============================================================

def main():

    rclpy.init()

    node = VelocityTorqueExperiment()

    try:

        node.run_experiment()

    except KeyboardInterrupt:

        print()
        print("Interrupted.")
        print(
            "Commanding 0 rad/s."
        )

        node.recording = False

        node.publish_velocity(
            0.0
        )

        node.run_for(
            0.5
        )

    finally:

        output_file = save_csv(
            node.samples
        )

        print()
        print(
            f"Saved "
            f"{len(node.samples)} samples to:"
        )

        print(
            output_file
        )

        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

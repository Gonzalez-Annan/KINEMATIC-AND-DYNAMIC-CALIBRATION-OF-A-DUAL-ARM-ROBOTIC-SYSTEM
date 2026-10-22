#!/usr/bin/env python3

import csv
import os
import time
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray


# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_DIR = Path(
    Path(__file__).resolve().parents[1] / "data" / "raw"
)

NUM_SWEEPS = 3

COMMAND_TOPIC = (
    "/forward_velocity_controller/commands"
)

JOINT_STATE_TOPIC = "/joint_states"


VELOCITY_SEQUENCE = [
    0.0,

    # positive direction
    0.0025,
    0.0050,
    0.0075,
    0.0100,
    0.0150,
    0.0200,
    0.0250,
    0.0300,
    0.0400,
    0.0500,
    0.0600,
    0.0750,
    0.1000,
    0.1250,
    0.1500,
    0.2000,

    0.0,

    # negative direction
    -0.0025,
    -0.0050,
    -0.0075,
    -0.0100,
    -0.0150,
    -0.0200,
    -0.0250,
    -0.0300,
    -0.0400,
    -0.0500,
    -0.0600,
    -0.0750,
    -0.1000,
    -0.1250,
    -0.1500,
    -0.2000,

    0.0,
]


# Motor rated torque read from Synapticon object 0x6076
RATED_TORQUE_NM = 2.222


# ============================================================
# TIMING
# ============================================================

def settling_time_for_velocity(v):
    a = abs(v)

    if a <= 0.02:
        return 8.0

    if a <= 0.05:
        return 6.0

    return 4.0


def recording_time_for_velocity(v):
    a = abs(v)

    if a < 1e-9:
        return 8.0

    if a <= 0.01:
        return 30.0

    if a <= 0.03:
        return 20.0

    if a <= 0.075:
        return 15.0

    return 10.0


# ============================================================
# ACQUISITION NODE
# ============================================================

class LowSpeedSweep(Node):

    def __init__(self):
        super().__init__(
            "day3_low_speed_sweep"
        )

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

        self.latest_joint_state = None

    def joint_state_callback(self, msg):
        self.latest_joint_state = msg

    def command_velocity(self, velocity):
        msg = Float64MultiArray()
        msg.data = [float(velocity)]

        self.publisher.publish(msg)

    def get_sample(self):
        if self.latest_joint_state is None:
            return None

        msg = self.latest_joint_state

        if not msg.position:
            return None

        position = msg.position[0]

        velocity = (
            msg.velocity[0]
            if msg.velocity
            else float("nan")
        )

        torque_raw = (
            msg.effort[0]
            if msg.effort
            else float("nan")
        )

        torque_nm = (
            torque_raw
            / 1000.0
            * RATED_TORQUE_NM
        )

        ros_time = (
            msg.header.stamp.sec
            + msg.header.stamp.nanosec
            * 1e-9
        )

        return (
            ros_time,
            position,
            velocity,
            torque_raw,
            torque_nm,
        )


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_file = OUTPUT_DIR / (
        f"day3_low_speed_raw_{timestamp}.csv"
    )

    print()
    print("========================================")
    print("DAY 3 LOW-SPEED FRICTION EXPERIMENT")
    print("========================================")
    print()
    print(f"Output file:")
    print(output_file)
    print()
    print(f"Number of sweeps: {NUM_SWEEPS}")
    print(
        f"Velocity points per sweep: "
        f"{len(VELOCITY_SEQUENCE)}"
    )
    print()

    rclpy.init()

    node = LowSpeedSweep()

    # Allow ROS subscription to populate
    print(
        "Waiting for joint-state data..."
    )

    wait_start = time.time()

    while (
        node.latest_joint_state is None
        and time.time() - wait_start < 10.0
    ):
        rclpy.spin_once(
            node,
            timeout_sec=0.1,
        )

    if node.latest_joint_state is None:
        print(
            "ERROR: No /joint_states received."
        )

        node.destroy_node()
        rclpy.shutdown()

        return

    print("Joint-state data received.")
    print()

    with open(
        output_file,
        "w",
        newline="",
    ) as csv_file:

        writer = csv.writer(
            csv_file
        )

        writer.writerow(
            [
                "wall_time_s",
                "ros_time_s",
                "sweep",
                "point",
                "previous_command_velocity_rad_s",
                "command_velocity_rad_s",
                "measured_position_rad",
                "measured_velocity_rad_s",
                "torque_raw_per_mille",
                "torque_Nm",
            ]
        )

        previous_command = 0.0

        try:

            for sweep in range(
                1,
                NUM_SWEEPS + 1,
            ):

                print()
                print(
                    "========================================"
                )
                print(
                    f"SWEEP {sweep}/{NUM_SWEEPS}"
                )
                print(
                    "========================================"
                )

                for point_index, command_velocity in enumerate(
                    VELOCITY_SEQUENCE,
                    start=1,
                ):

                    settle_time = (
                        settling_time_for_velocity(
                            command_velocity
                        )
                    )

                    record_time = (
                        recording_time_for_velocity(
                            command_velocity
                        )
                    )

                    print()
                    print(
                        f"Point "
                        f"{point_index}/"
                        f"{len(VELOCITY_SEQUENCE)}"
                    )

                    print(
                        f"Command velocity: "
                        f"{command_velocity:+.4f} rad/s"
                    )

                    print(
                        f"Previous velocity: "
                        f"{previous_command:+.4f} rad/s"
                    )

                    print(
                        f"Settling time: "
                        f"{settle_time:.1f} s"
                    )

                    print(
                        f"Recording time: "
                        f"{record_time:.1f} s"
                    )

                    node.command_velocity(
                        command_velocity
                    )

                    # -----------------------------
                    # SETTLING PERIOD
                    # -----------------------------

                    settle_start = time.time()

                    while (
                        time.time()
                        - settle_start
                        < settle_time
                    ):
                        rclpy.spin_once(
                            node,
                            timeout_sec=0.01,
                        )

                    # -----------------------------
                    # RECORDING PERIOD
                    # -----------------------------

                    record_start = time.time()

                    sample_count = 0

                    while (
                        time.time()
                        - record_start
                        < record_time
                    ):

                        rclpy.spin_once(
                            node,
                            timeout_sec=0.005,
                        )

                        sample = (
                            node.get_sample()
                        )

                        if sample is None:
                            continue

                        (
                            ros_time,
                            position,
                            velocity,
                            torque_raw,
                            torque_nm,
                        ) = sample

                        writer.writerow(
                            [
                                time.time(),
                                ros_time,
                                sweep,
                                point_index,
                                previous_command,
                                command_velocity,
                                position,
                                velocity,
                                torque_raw,
                                torque_nm,
                            ]
                        )

                        sample_count += 1

                    csv_file.flush()

                    print(
                        f"Recorded samples: "
                        f"{sample_count}"
                    )

                    previous_command = (
                        command_velocity
                    )

        except KeyboardInterrupt:

            print()
            print(
                "Experiment interrupted."
            )

        finally:

            print()
            print(
                "Stopping motor..."
            )

            node.command_velocity(
                0.0
            )

            for _ in range(20):
                rclpy.spin_once(
                    node,
                    timeout_sec=0.05,
                )

            node.destroy_node()

            rclpy.shutdown()

    print()
    print("========================================")
    print("EXPERIMENT COMPLETE")
    print("========================================")
    print()
    print(f"Saved:")
    print(output_file)
    print()


if __name__ == "__main__":
    main()

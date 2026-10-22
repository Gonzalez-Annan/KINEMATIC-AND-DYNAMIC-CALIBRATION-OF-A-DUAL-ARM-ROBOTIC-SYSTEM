#!/usr/bin/env python3

import csv
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
    "/home/uexpj/ros2_ws/day3_hysteresis_data"
)

COMMAND_TOPIC = (
    "/forward_velocity_controller/commands"
)

JOINT_STATE_TOPIC = "/joint_states"

RATED_TORQUE_NM = 2.222

NUM_SWEEPS = 3


# Same low-speed region, but now explicitly traversed
# both upward and downward.

POSITIVE_UP = [
    0.0,
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
]

POSITIVE_DOWN = [
    0.2000,
    0.1500,
    0.1250,
    0.1000,
    0.0750,
    0.0600,
    0.0500,
    0.0400,
    0.0300,
    0.0250,
    0.0200,
    0.0150,
    0.0100,
    0.0075,
    0.0050,
    0.0025,
    0.0,
]

NEGATIVE_DOWN = [
    0.0,
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
]

NEGATIVE_UP = [
    -0.2000,
    -0.1500,
    -0.1250,
    -0.1000,
    -0.0750,
    -0.0600,
    -0.0500,
    -0.0400,
    -0.0300,
    -0.0250,
    -0.0200,
    -0.0150,
    -0.0100,
    -0.0075,
    -0.0050,
    -0.0025,
    0.0,
]


SEQUENCES = [
    ("positive_up", POSITIVE_UP),
    ("positive_down", POSITIVE_DOWN),
    ("negative_down", NEGATIVE_DOWN),
    ("negative_up", NEGATIVE_UP),
]


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
        return 20.0

    if a <= 0.03:
        return 15.0

    if a <= 0.075:
        return 12.0

    return 8.0


# ============================================================
# ROS NODE
# ============================================================

class HysteresisSweep(Node):

    def __init__(self):
        super().__init__(
            "day3_hysteresis_sweep"
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
        f"day3_hysteresis_raw_{timestamp}.csv"
    )

    print()
    print("========================================")
    print("DAY 3 HYSTERESIS EXPERIMENT")
    print("========================================")
    print()
    print("Output:")
    print(output_file)
    print()
    print(f"Repeats: {NUM_SWEEPS}")
    print()

    rclpy.init()

    node = HysteresisSweep()

    print("Waiting for /joint_states...")

    start_wait = time.time()

    while (
        node.latest_joint_state is None
        and time.time() - start_wait < 10.0
    ):
        rclpy.spin_once(
            node,
            timeout_sec=0.1,
        )

    if node.latest_joint_state is None:
        print("ERROR: No joint states received.")
        node.destroy_node()
        rclpy.shutdown()
        return

    print("Joint states received.")
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
                "repeat",
                "sequence_name",
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

            for repeat in range(
                1,
                NUM_SWEEPS + 1,
            ):

                print()
                print(
                    "========================================"
                )
                print(
                    f"REPEAT {repeat}/{NUM_SWEEPS}"
                )
                print(
                    "========================================"
                )

                for (
                    sequence_name,
                    velocity_sequence,
                ) in SEQUENCES:

                    print()
                    print(
                        f"--- {sequence_name} ---"
                    )

                    for (
                        point_index,
                        command_velocity,
                    ) in enumerate(
                        velocity_sequence,
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
                            f"{sequence_name} "
                            f"{point_index}/"
                            f"{len(velocity_sequence)}"
                        )

                        print(
                            f"Previous: "
                            f"{previous_command:+.4f} rad/s"
                        )

                        print(
                            f"Command:  "
                            f"{command_velocity:+.4f} rad/s"
                        )

                        node.command_velocity(
                            command_velocity
                        )

                        # -----------------------------
                        # SETTLING
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
                        # RECORD
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
                                    repeat,
                                    sequence_name,
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
                            f"Recorded: "
                            f"{sample_count} samples"
                        )

                        previous_command = (
                            command_velocity
                        )

        except KeyboardInterrupt:

            print()
            print("Interrupted by user.")

        finally:

            print()
            print("Stopping motor...")

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
    print("HYSTERESIS EXPERIMENT COMPLETE")
    print("========================================")
    print()
    print("Saved:")
    print(output_file)
    print()


if __name__ == "__main__":
    main()


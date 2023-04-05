import os
import subprocess
import pandas as pd
import numpy as np
from io import StringIO
from typing import List
import sys
import argparse

COLUMN_NAMES = [
    "densidad",
    "volumen",
    "energia_potencial_media",
    "presion_media"
]

# MEAN_EPSILON_VALUES and STD_EPSILON_VALUES are the maximum allowed mean and
# standard deviation of the differences between the expected and actual output.
# They were computed by running the test script with the --mode=compute-statistics,
# and approximating that the error across outputs is normally distributed. The values
# were set to ~2 standard deviations from the mean, which should cover ~95% of the cases.
DEFAULT_MEAN_EPSILON_VALUES = [0, 0, 17, 0.3]
DEFAULT_STD_EPSILON_VALUES = [0, 0, 25, 0.2]
DEFAULT_NUM_RUNS = 20
DEFAULT_SUCCESS_THRESHOLD = 0.9


def run_tiny_md() -> str:
    result = subprocess.run(
        ["./tiny_md"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )

    return result.stdout


def parse_output(output: str) -> pd.DataFrame:
    lines = [line for line in output.split('\n') if not line.startswith('#')]
    cleaned_output = '\n'.join(lines)

    data = pd.read_csv(
        StringIO(cleaned_output),
        delim_whitespace=True,
        header=None
    )

    return data


def test_output(expected_output: pd.DataFrame, actual_output: pd.DataFrame, mean_epsilon_values: List[float], std_epsilon_values: List[float]) -> None:
    diff = np.abs(expected_output - actual_output)
    mean_diff = diff.mean(axis=0)
    std_diff = diff.std(axis=0)

    for col, (epsilon, std_epsilon) in enumerate(zip(mean_epsilon_values, std_epsilon_values)):
        assert mean_diff[col] <= epsilon, f"Mean difference of column {COLUMN_NAMES[col]} is too large: {mean_diff[col]}"
        assert std_diff[col] <= std_epsilon, f"Standard deviation of column {COLUMN_NAMES[col]} is too large: {std_diff[col]}"


def main(num_runs: int, success_threshold: float, mean_epsilon_values: List[float], std_epsilon_values: List[float]) -> None:
    print(f"Running test for tiny_md {num_runs} times...")

    with open(os.path.join("test", "expected_output.txt"), "r") as f:
        expected_output = parse_output(f.read())

    successful_runs = 0
    for i in range(num_runs):
        print(f"Run {i + 1}/{num_runs}...", end=" ")
        output = parse_output(run_tiny_md())

        try:
            test_output(
                expected_output,
                output,
                mean_epsilon_values,
                std_epsilon_values
            )

            print("OK")
            successful_runs += 1
        except AssertionError as e:
            print("ERROR: ", e)
            print("Expected output values:")
            print(expected_output)
            print("Actual output values:")
            print(output)

    success_rate = successful_runs / num_runs
    print(f"Success rate: {success_rate * 100:.1f}%")
    print(f"Success threshold: {success_threshold * 100:.1f}%")

    if success_rate >= success_threshold:
        print("FAIL")
        sys.exit(1)

    print("OK")


def compute_statistics(num_runs: int) -> None:
    print(f"Computing statistics for tiny_md after {num_runs} runs...")

    outputs = []
    for i in range(num_runs):
        print(f"Run {i + 1}/{num_runs}...", end=" ")
        outputs.append(parse_output(run_tiny_md()))
        print("OK")

    print("average output:")
    avg = np.mean(outputs, axis=0)
    for row in avg:
        print(" ".join([f"{x:.6f}" for x in row]))

    pairwise_diffs = np.array(
        [np.abs(outputs[i] - outputs[j])
         for i in range(num_runs) for j in range(i + 1, num_runs)]
    )

    mean_diffs = np.mean(pairwise_diffs, axis=0)
    print("mean of differences:")
    print("mean: ", np.mean(mean_diffs, axis=0).astype(float))
    print("std: ", np.std(mean_diffs, axis=0).astype(float))

    std_diffs = np.std(pairwise_diffs, axis=0)
    print("std of differences:")
    print("mean: ", np.mean(std_diffs, axis=0).astype(float))
    print("std: ", np.std(std_diffs, axis=0).astype(float))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test script for tiny_md")

    parser.add_argument(
        "--mode",
        choices=["test", "compute-statistics"],
        default="test",
        help="Mode of operation. Can be 'test' or 'compute-statistics'. Default is 'test'.",
    )
    parser.add_argument(
        "--num-runs",
        type=int,
        metavar="NUM_RUNS",
        default=DEFAULT_NUM_RUNS,
        help="Number of times to run tiny_md. Default is 20.",
    )
    parser.add_argument(
        "--success-threshold",
        type=float,
        metavar="SUCCESS_THRESHOLD",
        default=DEFAULT_SUCCESS_THRESHOLD,
        help="Success rate threshold for the test mode. Default is 0.9.",
    )
    parser.add_argument(
        "--mean-epsilon-values",
        nargs=4,
        type=float,
        metavar=tuple(COLUMN_NAMES),
        default=DEFAULT_MEAN_EPSILON_VALUES,
        help="Mean epsilon values for the test mode. Default is %s." % DEFAULT_MEAN_EPSILON_VALUES,
    )
    parser.add_argument(
        "--std-epsilon-values",
        nargs=4,
        type=float,
        metavar=tuple(COLUMN_NAMES),
        default=DEFAULT_STD_EPSILON_VALUES,
        help="Standard deviation epsilon values for the test mode. Default is %s." % DEFAULT_STD_EPSILON_VALUES,
    )

    args = parser.parse_args()

    if args.mode == "compute-statistics":
        compute_statistics(args.num_runs)
    else:
        main(args.num_runs, args.success_threshold,
             args.mean_epsilon_values, args.std_epsilon_values)

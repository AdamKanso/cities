"""Command line interface for the accessibility map project."""

from __future__ import annotations

import argparse
from pathlib import Path

from accessibility_map.analysis import (
    AccessibilityThresholds,
    TravelTimeThresholds,
)
from accessibility_map.map import build_map, save_map
from accessibility_map.workflow import run_analysis


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an interactive hospital accessibility map from OpenStreetMap data.",
    )
    parser.add_argument(
        "--place",
        default="Milan, Italy",
        help="City or place name recognized by OpenStreetMap.",
    )
    parser.add_argument(
        "--output",
        default="outputs/accessibility_map.html",
        help="Output HTML map path.",
    )
    parser.add_argument(
        "--good-threshold",
        type=float,
        default=750,
        help="Maximum distance in meters for good accessibility.",
    )
    parser.add_argument(
        "--medium-threshold",
        type=float,
        default=1500,
        help="Maximum distance in meters for medium accessibility.",
    )
    parser.add_argument(
        "--straight-line",
        action="store_true",
        help="Use straight-line distance instead of road-network distance.",
    )
    parser.add_argument(
        "--good-time-threshold",
        type=float,
        default=5,
        help="Maximum driving time in minutes for good accessibility.",
    )
    parser.add_argument(
        "--medium-time-threshold",
        type=float,
        default=10,
        help="Maximum driving time in minutes for medium accessibility.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    thresholds = AccessibilityThresholds(
        good_m=args.good_threshold,
        medium_m=args.medium_threshold,
    )
    time_thresholds = TravelTimeThresholds(
        good_minutes=args.good_time_threshold,
        medium_minutes=args.medium_time_threshold,
    )

    result = run_analysis(
        args.place,
        thresholds,
        time_thresholds,
        straight_line=args.straight_line,
        reporter=print,
    )

    print("Building interactive map...")
    fmap = build_map(
        result.boundary,
        result.areas,
        result.areas_with_clinics,
        result.excluded_areas,
        result.hospitals,
        result.clinics,
        result.graph,
    )
    output_path = save_map(fmap, Path(args.output))
    print(f"Saved map to {output_path.resolve()}")


if __name__ == "__main__":
    main()

"""Command line interface for the accessibility map project."""

from __future__ import annotations

import argparse
from pathlib import Path

from accessibility_map.analysis import (
    AccessibilityThresholds,
    TravelTimeThresholds,
    attach_accessibility_classes,
    attach_travel_time_classes,
    attach_priority_scores,
    attach_residential_density,
    nearest_hospital_by_network,
    nearest_hospital_travel_time_by_network,
    nearest_hospital_by_straight_line,
    representative_points,
)
from accessibility_map.map import build_map, save_map
from accessibility_map.osm_data import (
    download_candidate_areas,
    download_city_boundary,
    download_hospitals,
    download_residential_landuse,
    download_road_graph,
)


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
        default=1500,
        help="Maximum distance in meters for good accessibility.",
    )
    parser.add_argument(
        "--medium-threshold",
        type=float,
        default=3000,
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
        default=10,
        help="Maximum driving time in minutes for good accessibility.",
    )
    parser.add_argument(
        "--medium-time-threshold",
        type=float,
        default=20,
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

    print(f"Downloading city boundary for {args.place}...")
    boundary = download_city_boundary(args.place)

    print("Downloading hospitals and clinics...")
    hospitals = download_hospitals(args.place)

    print("Downloading residential or neighborhood areas...")
    areas = download_candidate_areas(args.place, boundary)
    area_points = representative_points(areas)

    print("Downloading residential land-use coverage...")
    residential_landuse = download_residential_landuse(args.place, boundary)

    print("Downloading road network...")
    graph = download_road_graph(args.place)

    if args.straight_line:
        print("Calculating straight-line distance to nearest hospital...")
        distances = nearest_hospital_by_straight_line(area_points, hospitals)
    else:
        print("Calculating road-network distance to nearest hospital...")
        distances = nearest_hospital_by_network(graph, area_points, hospitals)

    print("Calculating estimated driving time to nearest hospital...")
    travel_times = nearest_hospital_travel_time_by_network(graph, area_points, hospitals)

    print("Classifying accessibility...")
    classified_areas = attach_accessibility_classes(areas, distances, thresholds)
    classified_areas = attach_travel_time_classes(
        classified_areas,
        travel_times,
        time_thresholds,
    )
    classified_areas = attach_residential_density(
        classified_areas,
        residential_landuse,
    )
    classified_areas = attach_priority_scores(classified_areas)

    print("Building interactive map...")
    fmap = build_map(boundary, classified_areas, hospitals, graph)
    output_path = save_map(fmap, Path(args.output))
    print(f"Saved map to {output_path.resolve()}")


if __name__ == "__main__":
    main()

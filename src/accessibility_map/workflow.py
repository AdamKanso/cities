"""Reusable workflow for hospital accessibility analysis."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import geopandas as gpd
import pandas as pd

from accessibility_map.analysis import (
    AccessibilityThresholds,
    TravelTimeThresholds,
    apply_travel_time_multiplier,
    attach_accessibility_classes,
    attach_priority_scores,
    attach_residential_density,
    attach_travel_time_classes,
    filter_residential_areas,
    nearest_hospital_by_network,
    nearest_hospital_by_straight_line,
    nearest_hospital_travel_time_by_network,
    representative_points,
)
from accessibility_map.osm_data import (
    download_candidate_areas,
    download_clinics,
    download_city_boundary,
    download_hospitals,
    download_residential_landuse,
    download_road_graph,
)


@dataclass
class AnalysisResult:
    """All datasets needed to render an accessibility-map scenario."""

    boundary: gpd.GeoDataFrame
    areas: gpd.GeoDataFrame
    areas_with_clinics: gpd.GeoDataFrame
    excluded_areas: gpd.GeoDataFrame
    hospitals: gpd.GeoDataFrame
    clinics: gpd.GeoDataFrame
    graph: object


def run_analysis(
    place: str,
    distance_thresholds: AccessibilityThresholds,
    time_thresholds: TravelTimeThresholds,
    straight_line: bool = False,
    minimum_residential_coverage: float = 5,
    travel_time_multiplier: float = 1.0,
    reporter: Callable[[str], None] | None = None,
) -> AnalysisResult:
    """Run hospital-only and hospitals-plus-clinics accessibility scenarios."""
    _report(reporter, f"Downloading city boundary for {place}...")
    boundary = download_city_boundary(place)

    _report(reporter, "Downloading hospitals...")
    hospitals = download_hospitals(place)
    _report(reporter, "Downloading clinics for comparison...")
    clinics = download_clinics(place)
    facilities_with_clinics = gpd.GeoDataFrame(
        pd.concat([hospitals, clinics], ignore_index=True),
        geometry="geometry",
        crs="EPSG:4326",
    )

    _report(reporter, "Creating regular city analysis grid...")
    all_areas = download_candidate_areas(place, boundary)
    _report(reporter, "Downloading residential land-use coverage...")
    residential_landuse = download_residential_landuse(place, boundary)
    all_areas = attach_residential_density(all_areas, residential_landuse)
    excluded_areas = all_areas[
        all_areas["residential_coverage_percent"] < minimum_residential_coverage
    ].copy()
    areas = filter_residential_areas(all_areas, minimum_residential_coverage)
    _report(reporter, f"Analysing {len(areas)} residential grid cells...")
    area_points = representative_points(areas)

    _report(reporter, "Downloading road network...")
    graph = download_road_graph(place)

    if straight_line:
        _report(reporter, "Calculating straight-line distance to nearest hospital...")
        distances = nearest_hospital_by_straight_line(area_points, hospitals)
        distances_with_clinics = nearest_hospital_by_straight_line(
            area_points,
            facilities_with_clinics,
        )
    else:
        _report(reporter, "Calculating road-network distance to nearest hospital...")
        distances = nearest_hospital_by_network(graph, area_points, hospitals)
        _report(reporter, "Calculating distance with clinics included...")
        distances_with_clinics = nearest_hospital_by_network(
            graph,
            area_points,
            facilities_with_clinics,
        )

    _report(reporter, "Calculating estimated driving time to nearest hospital...")
    travel_times = nearest_hospital_travel_time_by_network(graph, area_points, hospitals)
    _report(reporter, "Calculating driving time with clinics included...")
    travel_times_with_clinics = nearest_hospital_travel_time_by_network(
        graph,
        area_points,
        facilities_with_clinics,
    )
    if travel_time_multiplier > 1:
        _report(
            reporter,
            "Applying the emergency response-time disruption scenario...",
        )
    travel_times = apply_travel_time_multiplier(
        travel_times,
        travel_time_multiplier,
    )
    travel_times_with_clinics = apply_travel_time_multiplier(
        travel_times_with_clinics,
        travel_time_multiplier,
    )

    _report(reporter, "Classifying accessibility...")
    classified_areas = _classify_scenario(
        areas,
        distances,
        travel_times,
        distance_thresholds,
        time_thresholds,
    )
    classified_areas_with_clinics = _classify_scenario(
        areas,
        distances_with_clinics,
        travel_times_with_clinics,
        distance_thresholds,
        time_thresholds,
    )

    return AnalysisResult(
        boundary=boundary,
        areas=classified_areas,
        areas_with_clinics=classified_areas_with_clinics,
        excluded_areas=excluded_areas,
        hospitals=hospitals,
        clinics=clinics,
        graph=graph,
    )


def _classify_scenario(
    areas: gpd.GeoDataFrame,
    distances: list[float | None],
    travel_times: list[float | None],
    distance_thresholds: AccessibilityThresholds,
    time_thresholds: TravelTimeThresholds,
) -> gpd.GeoDataFrame:
    classified = attach_accessibility_classes(areas, distances, distance_thresholds)
    classified = attach_travel_time_classes(classified, travel_times, time_thresholds)
    return attach_priority_scores(classified)


def _report(reporter: Callable[[str], None] | None, message: str) -> None:
    if reporter is not None:
        reporter(message)

"""Spatial analysis helpers for hospital accessibility."""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry import Point


@dataclass(frozen=True)
class AccessibilityThresholds:
    """Distance thresholds in meters for accessibility classes."""

    good_m: float = 750
    medium_m: float = 1500


@dataclass(frozen=True)
class TravelTimeThresholds:
    """Driving-time thresholds in minutes for accessibility classes."""

    good_minutes: float = 5
    medium_minutes: float = 10


def classify_accessibility(
    distance_m: float | None,
    good_threshold_m: float,
    medium_threshold_m: float,
) -> str:
    """Classify a distance to the nearest hospital."""
    if distance_m is None:
        return "unknown"
    if distance_m <= good_threshold_m:
        return "good"
    if distance_m <= medium_threshold_m:
        return "medium"
    return "poor"


def estimate_utm_crs(gdf: gpd.GeoDataFrame) -> str:
    """Return a projected CRS suitable for meter-based distance calculations."""
    return gdf.estimate_utm_crs().to_string()


def representative_points(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Create one point inside each polygon for network-distance analysis."""
    points = gdf.copy()
    points["geometry"] = points.geometry.representative_point()
    return points


def nearest_hospital_by_network(
    graph: nx.MultiDiGraph,
    origins: gpd.GeoDataFrame,
    hospitals: gpd.GeoDataFrame,
) -> list[float | None]:
    """Measure shortest drivable network distance from origins to hospitals."""
    if origins.empty:
        return []
    if hospitals.empty:
        return [None for _ in range(len(origins))]

    graph_crs = graph.graph.get("crs")
    origins_wgs84 = representative_points(origins).to_crs(graph_crs)
    hospitals_wgs84 = representative_points(hospitals).to_crs(graph_crs)

    hospital_nodes = list(ox.distance.nearest_nodes(
        graph,
        X=hospitals_wgs84.geometry.x,
        Y=hospitals_wgs84.geometry.y,
    ))
    origin_nodes = list(ox.distance.nearest_nodes(
        graph,
        X=origins_wgs84.geometry.x,
        Y=origins_wgs84.geometry.y,
    ))

    route_graph = graph.reverse(copy=False)
    try:
        lengths = nx.multi_source_dijkstra_path_length(
            route_graph,
            hospital_nodes,
            cutoff=None,
            weight="length",
        )
    except nx.NetworkXNoPath:
        lengths = {}

    distances: list[float | None] = []
    for origin_node in origin_nodes:
        distance = lengths.get(origin_node)
        distances.append(float(distance) if distance is not None else None)

    return distances


def nearest_hospital_travel_time_by_network(
    graph: nx.MultiDiGraph,
    origins: gpd.GeoDataFrame,
    hospitals: gpd.GeoDataFrame,
) -> list[float | None]:
    """Measure shortest estimated driving time in minutes to a hospital."""
    if origins.empty:
        return []
    if hospitals.empty:
        return [None for _ in range(len(origins))]

    travel_graph = ox.routing.add_edge_speeds(graph.copy())
    travel_graph = ox.routing.add_edge_travel_times(travel_graph)
    graph_crs = travel_graph.graph.get("crs")
    origins_wgs84 = representative_points(origins).to_crs(graph_crs)
    hospitals_wgs84 = representative_points(hospitals).to_crs(graph_crs)

    hospital_nodes = list(ox.distance.nearest_nodes(
        travel_graph,
        X=hospitals_wgs84.geometry.x,
        Y=hospitals_wgs84.geometry.y,
    ))
    origin_nodes = list(ox.distance.nearest_nodes(
        travel_graph,
        X=origins_wgs84.geometry.x,
        Y=origins_wgs84.geometry.y,
    ))

    route_graph = travel_graph.reverse(copy=False)
    lengths = nx.multi_source_dijkstra_path_length(
        route_graph,
        hospital_nodes,
        cutoff=None,
        weight="travel_time",
    )
    return [
        round(float(lengths[origin_node]) / 60, 2)
        if origin_node in lengths
        else None
        for origin_node in origin_nodes
    ]


def nearest_hospital_by_straight_line(
    origins: gpd.GeoDataFrame,
    hospitals: gpd.GeoDataFrame,
) -> list[float | None]:
    """Fallback straight-line distance from origins to nearest hospital."""
    if origins.empty:
        return []
    if hospitals.empty:
        return [None for _ in range(len(origins))]

    projected_crs = estimate_utm_crs(origins)
    origins_projected = origins.to_crs(projected_crs)
    hospitals_projected = hospitals.to_crs(projected_crs)

    hospital_union = hospitals_projected.geometry.union_all()
    distances: list[float | None] = []
    for geometry in origins_projected.geometry:
        if isinstance(geometry, Point):
            distance = geometry.distance(hospital_union)
        else:
            distance = geometry.representative_point().distance(hospital_union)
        distances.append(float(distance))
    return distances


def attach_accessibility_classes(
    areas: gpd.GeoDataFrame,
    distances_m: list[float | None],
    thresholds: AccessibilityThresholds,
) -> gpd.GeoDataFrame:
    """Attach distance and accessibility class columns to analysis areas."""
    result = areas.copy()
    result["nearest_hospital_m"] = distances_m
    result["accessibility"] = [
        classify_accessibility(distance, thresholds.good_m, thresholds.medium_m)
        for distance in distances_m
    ]
    return result


def attach_travel_time_classes(
    areas: gpd.GeoDataFrame,
    travel_times_minutes: list[float | None],
    thresholds: TravelTimeThresholds,
) -> gpd.GeoDataFrame:
    """Attach travel time and travel-time accessibility class columns."""
    result = areas.copy()
    result["nearest_hospital_minutes"] = travel_times_minutes
    result["travel_time_accessibility"] = [
        classify_accessibility(
            travel_time,
            thresholds.good_minutes,
            thresholds.medium_minutes,
        )
        for travel_time in travel_times_minutes
    ]
    return result


def apply_travel_time_multiplier(
    travel_times_minutes: list[float | None],
    multiplier: float,
) -> list[float | None]:
    """Apply a scenario multiplier to estimated driving times."""
    if multiplier < 1:
        raise ValueError("The travel-time multiplier must be at least 1.")
    return [
        round(travel_time * multiplier, 2) if travel_time is not None else None
        for travel_time in travel_times_minutes
    ]


def attach_residential_density(
    areas: gpd.GeoDataFrame,
    residential_landuse: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Measure residential land-use coverage as an area-density proxy."""
    result = areas.copy().reset_index(drop=True)
    projected_crs = estimate_utm_crs(result)
    projected_areas = result.to_crs(projected_crs).copy()
    projected_areas["_analysis_id"] = projected_areas.index
    projected_areas["area_km2"] = projected_areas.geometry.area / 1_000_000
    projected_areas["residential_landuse_km2"] = 0.0

    if not residential_landuse.empty:
        projected_residential = residential_landuse.to_crs(projected_crs)
        intersections = gpd.overlay(
            projected_areas[["_analysis_id", "geometry"]],
            projected_residential[["geometry"]],
            how="intersection",
            keep_geom_type=False,
        )
        if not intersections.empty:
            covered_km2 = (
                intersections.assign(_covered_km2=intersections.geometry.area / 1_000_000)
                .groupby("_analysis_id")["_covered_km2"]
                .sum()
            )
            projected_areas["residential_landuse_km2"] = (
                projected_areas["_analysis_id"].map(covered_km2).fillna(0.0)
            )

    projected_areas["residential_coverage_percent"] = (
        100
        * projected_areas["residential_landuse_km2"]
        / projected_areas["area_km2"]
    )
    result["area_km2"] = projected_areas["area_km2"]
    result["residential_landuse_km2"] = projected_areas["residential_landuse_km2"]
    result["residential_coverage_percent"] = (
        projected_areas["residential_coverage_percent"]
    )
    return result


def attach_priority_scores(areas: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Rank areas by access need and relative residential coverage."""
    result = areas.copy()
    maximum_coverage = result["residential_coverage_percent"].max()
    if maximum_coverage > 0:
        density_factor = result["residential_coverage_percent"] / maximum_coverage
    else:
        density_factor = 0.0
    access_weight = result["travel_time_accessibility"].map(
        {"good": 0, "medium": 1, "poor": 2}
    )
    result["priority_score"] = (access_weight * density_factor).round(2)
    result["priority"] = "low"
    result.loc[result["priority_score"] >= 0.2, "priority"] = "medium"
    result.loc[result["priority_score"] >= 1.34, "priority"] = "high"
    result.loc[access_weight.isna(), "priority"] = "unknown"
    return result


def filter_residential_areas(
    areas: gpd.GeoDataFrame,
    minimum_coverage_percent: float = 5,
) -> gpd.GeoDataFrame:
    """Keep analysis cells containing a meaningful amount of residential land use."""
    residential_areas = areas[
        areas["residential_coverage_percent"] >= minimum_coverage_percent
    ].copy()
    if residential_areas.empty:
        return areas.copy()
    return residential_areas.reset_index(drop=True)

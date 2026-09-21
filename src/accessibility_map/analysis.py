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

    good_m: float = 1500
    medium_m: float = 3000


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

    try:
        lengths = nx.multi_source_dijkstra_path_length(
            graph,
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

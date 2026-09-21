import geopandas as gpd
import networkx as nx
import pandas as pd
from shapely.geometry import Point
from shapely.geometry import box

from accessibility_map.analysis import (
    AccessibilityThresholds,
    TravelTimeThresholds,
    attach_accessibility_classes,
    attach_priority_scores,
    attach_residential_density,
    attach_travel_time_classes,
    classify_accessibility,
    nearest_hospital_by_network,
)


def test_classify_good_medium_poor():
    assert classify_accessibility(1000, 1500, 3000) == "good"
    assert classify_accessibility(2500, 1500, 3000) == "medium"
    assert classify_accessibility(4500, 1500, 3000) == "poor"


def test_classify_missing_distance():
    assert classify_accessibility(None, 1500, 3000) == "unknown"


def test_attach_accessibility_classes():
    areas = gpd.GeoDataFrame(
        {
            "name": ["Area A", "Area B", "Area C"],
            "geometry": [Point(0, 0), Point(1, 1), Point(2, 2)],
        },
        crs="EPSG:4326",
    )

    result = attach_accessibility_classes(
        areas,
        [800, 2200, None],
        AccessibilityThresholds(good_m=1500, medium_m=3000),
    )

    assert list(result["accessibility"]) == ["good", "medium", "unknown"]
    assert list(result["nearest_hospital_m"].iloc[:2]) == [800, 2200]
    assert pd.isna(result["nearest_hospital_m"].iloc[2])


def test_attach_travel_time_classes():
    areas = gpd.GeoDataFrame(
        {"geometry": [Point(0, 0), Point(1, 1), Point(2, 2)]},
        crs="EPSG:4326",
    )

    result = attach_travel_time_classes(
        areas,
        [8, 15, None],
        TravelTimeThresholds(good_minutes=10, medium_minutes=20),
    )

    assert list(result["travel_time_accessibility"]) == ["good", "medium", "unknown"]
    assert list(result["nearest_hospital_minutes"].iloc[:2]) == [8, 15]
    assert pd.isna(result["nearest_hospital_minutes"].iloc[2])


def test_attach_residential_density_measures_landuse_overlap():
    areas = gpd.GeoDataFrame(
        {"geometry": [box(0, 0, 0.01, 0.01), box(0.01, 0, 0.02, 0.01)]},
        crs="EPSG:4326",
    )
    residential = gpd.GeoDataFrame(
        {"geometry": [box(0, 0, 0.01, 0.01)]},
        crs="EPSG:4326",
    )

    result = attach_residential_density(areas, residential)

    assert result["residential_coverage_percent"].iloc[0] > 99
    assert result["residential_coverage_percent"].iloc[1] == 0


def test_attach_priority_scores_favors_poor_access_with_more_residential_coverage():
    areas = gpd.GeoDataFrame(
        {
            "travel_time_accessibility": ["poor", "poor", "good", "unknown"],
            "residential_coverage_percent": [90, 10, 100, 20],
            "geometry": [Point(0, 0), Point(1, 1), Point(2, 2), Point(3, 3)],
        },
        crs="EPSG:4326",
    )

    result = attach_priority_scores(areas)

    assert list(result["priority"]) == ["high", "medium", "low", "unknown"]


def test_network_distance_respects_one_way_roads_toward_hospitals():
    graph = nx.MultiDiGraph(crs="EPSG:4326")
    graph.add_node("home", x=9.0, y=45.0)
    graph.add_node("hospital", x=9.01, y=45.0)
    graph.add_edge("home", "hospital", length=600)
    origins = gpd.GeoDataFrame({"geometry": [Point(9.0, 45.0)]}, crs="EPSG:4326")
    hospitals = gpd.GeoDataFrame(
        {"geometry": [Point(9.01, 45.0)]},
        crs="EPSG:4326",
    )

    assert nearest_hospital_by_network(graph, origins, hospitals) == [600.0]

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from accessibility_map.analysis import (
    AccessibilityThresholds,
    TravelTimeThresholds,
    attach_accessibility_classes,
    attach_travel_time_classes,
    classify_accessibility,
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

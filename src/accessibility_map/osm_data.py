"""OpenStreetMap data download and preparation."""

from __future__ import annotations

import geopandas as gpd
import osmnx as ox
from shapely.geometry import Polygon, box


HOSPITAL_TAGS = {
    "amenity": ["hospital", "clinic"],
    "healthcare": ["hospital", "clinic"],
}

NEIGHBORHOOD_TAGS = {
    "place": ["neighbourhood", "quarter", "suburb"],
    "boundary": "administrative",
}

RESIDENTIAL_TAGS = {
    "landuse": "residential",
}


def download_city_boundary(place: str) -> gpd.GeoDataFrame:
    """Download the administrative boundary for a city."""
    boundary = ox.geocode_to_gdf(place)
    return boundary[["display_name", "geometry"]].to_crs("EPSG:4326")


def download_hospitals(place: str) -> gpd.GeoDataFrame:
    """Download hospital and clinic features from OpenStreetMap."""
    hospitals = ox.features_from_place(place, HOSPITAL_TAGS)
    hospitals = hospitals.reset_index()
    hospitals = hospitals[hospitals.geometry.notna()].copy()
    hospitals["name"] = hospitals.get("name", "Unnamed hospital")
    return hospitals[["name", "geometry"]].to_crs("EPSG:4326")


def download_road_graph(place: str):
    """Download a drivable road network for the selected place."""
    return ox.graph_from_place(place, network_type="drive", simplify=True)


def download_candidate_areas(place: str, boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Download neighborhood polygons, with residential areas as fallback."""
    neighborhoods = _download_polygons(place, NEIGHBORHOOD_TAGS, boundary)
    if not neighborhoods.empty:
        return neighborhoods

    residential = _download_polygons(place, RESIDENTIAL_TAGS, boundary)
    if not residential.empty:
        return residential

    return make_analysis_grid(boundary)


def _download_polygons(
    place: str,
    tags: dict[str, object],
    boundary: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    features = ox.features_from_place(place, tags).reset_index()
    if features.empty:
        return gpd.GeoDataFrame(columns=["name", "geometry"], crs="EPSG:4326")

    polygons = features[
        features.geometry.notna()
        & features.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    ].copy()
    if polygons.empty:
        return gpd.GeoDataFrame(columns=["name", "geometry"], crs="EPSG:4326")

    if "name" not in polygons.columns:
        polygons["name"] = None
    polygons["name"] = polygons["name"].fillna("Residential area")

    clipped = _keep_polygon_parts(
        gpd.clip(polygons[["name", "geometry"]].to_crs(boundary.crs), boundary)
    )
    clipped["area_id"] = [f"area-{index + 1}" for index in range(len(clipped))]
    return clipped[["area_id", "name", "geometry"]].to_crs("EPSG:4326")


def make_analysis_grid(
    boundary: gpd.GeoDataFrame,
    cell_size_m: int = 1200,
) -> gpd.GeoDataFrame:
    """Create a regular grid clipped to the city boundary."""
    projected_crs = boundary.estimate_utm_crs()
    boundary_projected = boundary.to_crs(projected_crs)
    minx, miny, maxx, maxy = boundary_projected.total_bounds

    cells: list[Polygon] = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            cells.append(box(x, y, x + cell_size_m, y + cell_size_m))
            y += cell_size_m
        x += cell_size_m

    grid = gpd.GeoDataFrame({"geometry": cells}, crs=projected_crs)
    clipped = _keep_polygon_parts(gpd.clip(grid, boundary_projected))
    clipped["area_id"] = [f"grid-{index + 1}" for index in range(len(clipped))]
    clipped["name"] = clipped["area_id"]
    return clipped[["area_id", "name", "geometry"]].to_crs("EPSG:4326")


def _keep_polygon_parts(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep polygon outputs after clipping and remove lines or points."""
    if gdf.empty:
        return gdf
    exploded = gdf.explode(index_parts=False).reset_index(drop=True)
    polygons = exploded[
        exploded.geometry.notna()
        & ~exploded.geometry.is_empty
        & exploded.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    ].copy()
    return polygons

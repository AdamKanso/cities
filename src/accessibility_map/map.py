"""Interactive Folium map rendering."""

from __future__ import annotations

from pathlib import Path

import folium
import geopandas as gpd
import osmnx as ox


ACCESSIBILITY_COLORS = {
    "good": "#2ca25f",
    "medium": "#fdae61",
    "poor": "#d7191c",
    "unknown": "#969696",
}


def build_map(
    boundary: gpd.GeoDataFrame,
    areas: gpd.GeoDataFrame,
    hospitals: gpd.GeoDataFrame,
    graph,
) -> folium.Map:
    """Build an interactive accessibility map."""
    center = boundary.geometry.iloc[0].centroid
    fmap = folium.Map(
        location=[center.y, center.x],
        zoom_start=12,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    _add_boundary(fmap, boundary)
    _add_roads(fmap, graph)
    _add_accessibility_areas(fmap, areas)
    _add_hospitals(fmap, hospitals)
    _add_legend(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap


def save_map(fmap: folium.Map, output_path: str | Path) -> Path:
    """Save the Folium map to an HTML file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(path)
    return path


def _add_boundary(fmap: folium.Map, boundary: gpd.GeoDataFrame) -> None:
    folium.GeoJson(
        boundary,
        name="City boundary",
        style_function=lambda _: {
            "color": "#1f2937",
            "weight": 2,
            "fillOpacity": 0,
        },
    ).add_to(fmap)


def _add_roads(fmap: folium.Map, graph) -> None:
    nodes, edges = ox.graph_to_gdfs(graph)
    if edges.empty:
        return
    road_layer = folium.FeatureGroup(name="Road network", show=False)
    folium.GeoJson(
        edges[["geometry"]].to_crs("EPSG:4326"),
        style_function=lambda _: {
            "color": "#64748b",
            "weight": 1,
            "opacity": 0.45,
        },
    ).add_to(road_layer)
    road_layer.add_to(fmap)


def _add_accessibility_areas(fmap: folium.Map, areas: gpd.GeoDataFrame) -> None:
    display = areas.copy()
    display["nearest_hospital_km"] = display["nearest_hospital_m"].apply(
        lambda value: round(value / 1000, 2) if value is not None else None
    )

    folium.GeoJson(
        display,
        name="Hospital accessibility",
        style_function=lambda feature: {
            "fillColor": ACCESSIBILITY_COLORS.get(
                feature["properties"].get("accessibility", "unknown"),
                ACCESSIBILITY_COLORS["unknown"],
            ),
            "color": "#334155",
            "weight": 0.7,
            "fillOpacity": 0.62,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "accessibility", "nearest_hospital_km"],
            aliases=["Area", "Accessibility", "Nearest hospital (km)"],
            localize=True,
            sticky=False,
        ),
    ).add_to(fmap)


def _add_hospitals(fmap: folium.Map, hospitals: gpd.GeoDataFrame) -> None:
    hospital_layer = folium.FeatureGroup(name="Hospitals and clinics")
    for _, hospital in hospitals.to_crs("EPSG:4326").iterrows():
        point = hospital.geometry.centroid
        folium.CircleMarker(
            location=[point.y, point.x],
            radius=5,
            color="#991b1b",
            fill=True,
            fill_color="#ef4444",
            fill_opacity=0.9,
            popup=hospital.get("name", "Hospital or clinic"),
        ).add_to(hospital_layer)
    hospital_layer.add_to(fmap)


def _add_legend(fmap: folium.Map) -> None:
    legend_html = """
    <div style="
        position: fixed;
        bottom: 28px;
        left: 28px;
        z-index: 9999;
        background: white;
        padding: 12px 14px;
        border: 1px solid #cbd5e1;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.18);
        font-size: 13px;
        line-height: 1.5;
    ">
        <strong>Hospital accessibility</strong><br>
        <span style="color:#2ca25f;">■</span> Good<br>
        <span style="color:#fdae61;">■</span> Medium<br>
        <span style="color:#d7191c;">■</span> Poor<br>
        <span style="color:#969696;">■</span> Unknown
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(legend_html))

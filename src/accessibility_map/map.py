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

PRIORITY_COLORS = {
    "high": "#dc2626",
    "medium": "#f59e0b",
    "low": "#16a34a",
    "unknown": "#969696",
}


def build_map(
    boundary: gpd.GeoDataFrame,
    areas: gpd.GeoDataFrame,
    areas_with_clinics: gpd.GeoDataFrame,
    excluded_areas: gpd.GeoDataFrame,
    hospitals: gpd.GeoDataFrame,
    clinics: gpd.GeoDataFrame,
    graph,
    selected_scenario: str = "Hospitals only",
    selected_metric: str = "Distance",
) -> folium.Map:
    """Build an interactive accessibility map."""
    center = boundary.geometry.iloc[0].centroid
    fmap = folium.Map(
        location=[center.y, center.x],
        zoom_start=12,
        tiles=None,
        control_scale=True,
    )
    folium.TileLayer(
        tiles=(
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Street_Map/MapServer/tile/{z}/{y}/{x}"
        ),
        attr="Tiles &copy; Esri",
        name="Street map",
        overlay=False,
        control=True,
    ).add_to(fmap)

    _add_boundary(fmap, boundary)
    _add_roads(fmap, graph)
    _add_excluded_areas(fmap, excluded_areas)
    _add_accessibility_areas(
        fmap,
        areas,
        "Distance: hospitals only",
        selected_scenario == "Hospitals only" and selected_metric == "Distance",
    )
    _add_accessibility_areas(
        fmap,
        areas_with_clinics,
        "Distance: hospitals + clinics",
        selected_scenario == "Hospitals + clinics" and selected_metric == "Distance",
    )
    _add_travel_time_areas(
        fmap,
        areas,
        "Driving time: hospitals only",
        selected_scenario == "Hospitals only" and selected_metric == "Driving time",
    )
    _add_travel_time_areas(
        fmap,
        areas_with_clinics,
        "Driving time: hospitals + clinics",
        selected_scenario == "Hospitals + clinics" and selected_metric == "Driving time",
    )
    _add_priority_areas(
        fmap,
        areas,
        "Priority: hospitals only",
        selected_scenario == "Hospitals only" and selected_metric == "Priority",
    )
    _add_priority_areas(
        fmap,
        areas_with_clinics,
        "Priority: hospitals + clinics",
        selected_scenario == "Hospitals + clinics" and selected_metric == "Priority",
    )
    _add_hospitals(fmap, hospitals)
    _add_clinics(fmap, clinics)
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


def _add_excluded_areas(fmap: folium.Map, areas: gpd.GeoDataFrame) -> None:
    """Show grid cells excluded because they lack enough residential land use."""
    if areas.empty:
        return
    display = areas.copy()
    display["analysis_status"] = "Not analysed"
    display["exclusion_reason"] = "Residential land-use coverage below 5%"
    excluded_layer = folium.FeatureGroup(name="Excluded low-residential cells", show=True)
    folium.GeoJson(
        display,
        style_function=lambda _: {
            "fillColor": "#94a3b8",
            "color": "#64748b",
            "weight": 0.7,
            "fillOpacity": 0.25,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "analysis_status", "exclusion_reason"],
            aliases=["Area", "Status", "Reason"],
            sticky=False,
        ),
    ).add_to(excluded_layer)
    excluded_layer.add_to(fmap)


def _add_accessibility_areas(
    fmap: folium.Map,
    areas: gpd.GeoDataFrame,
    layer_name: str,
    show: bool,
) -> None:
    display = areas.copy()
    display["nearest_hospital_km"] = display["nearest_hospital_m"].apply(
        lambda value: round(value / 1000, 2) if value is not None else None
    )

    distance_layer = folium.FeatureGroup(name=layer_name, show=show)
    folium.GeoJson(
        display,
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
    ).add_to(distance_layer)
    distance_layer.add_to(fmap)


def _add_travel_time_areas(
    fmap: folium.Map,
    areas: gpd.GeoDataFrame,
    layer_name: str,
    show: bool,
) -> None:
    """Add a toggleable layer for estimated driving-time accessibility."""
    display = areas.copy()
    travel_time_layer = folium.FeatureGroup(
        name=layer_name,
        show=show,
    )
    folium.GeoJson(
        display,
        style_function=lambda feature: {
            "fillColor": ACCESSIBILITY_COLORS.get(
                feature["properties"].get("travel_time_accessibility", "unknown"),
                ACCESSIBILITY_COLORS["unknown"],
            ),
            "color": "#334155",
            "weight": 0.7,
            "fillOpacity": 0.62,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "travel_time_accessibility", "nearest_hospital_minutes"],
            aliases=["Area", "Driving-time accessibility", "Estimated drive (min)"],
            localize=True,
            sticky=False,
        ),
    ).add_to(travel_time_layer)
    travel_time_layer.add_to(fmap)


def _add_priority_areas(
    fmap: folium.Map,
    areas: gpd.GeoDataFrame,
    layer_name: str,
    show: bool,
) -> None:
    """Add a toggleable layer identifying higher-priority underserved areas."""
    priority_layer = folium.FeatureGroup(
        name=layer_name,
        show=show,
    )
    folium.GeoJson(
        areas,
        style_function=lambda feature: {
            "fillColor": PRIORITY_COLORS.get(
                feature["properties"].get("priority", "unknown"),
                PRIORITY_COLORS["unknown"],
            ),
            "color": "#334155",
            "weight": 0.7,
            "fillOpacity": 0.62,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "name",
                "priority",
                "priority_score",
                "residential_coverage_percent",
                "nearest_hospital_minutes",
            ],
            aliases=[
                "Area",
                "Priority",
                "Priority score",
                "Residential coverage (%)",
                "Estimated drive (min)",
            ],
            localize=True,
            sticky=False,
        ),
    ).add_to(priority_layer)
    priority_layer.add_to(fmap)


def _add_hospitals(fmap: folium.Map, hospitals: gpd.GeoDataFrame) -> None:
    hospital_layer = folium.FeatureGroup(name="Hospitals")
    for _, hospital in hospitals.to_crs("EPSG:4326").iterrows():
        point = hospital.geometry.centroid
        folium.CircleMarker(
            location=[point.y, point.x],
            radius=5,
            color="#991b1b",
            fill=True,
            fill_color="#ef4444",
            fill_opacity=0.9,
            popup=hospital.get("name", "Hospital"),
        ).add_to(hospital_layer)
    hospital_layer.add_to(fmap)


def _add_clinics(fmap: folium.Map, clinics: gpd.GeoDataFrame) -> None:
    """Add clinics as a toggleable comparison layer."""
    clinic_layer = folium.FeatureGroup(name="Clinics", show=False)
    for _, clinic in clinics.to_crs("EPSG:4326").iterrows():
        point = clinic.geometry.centroid
        folium.CircleMarker(
            location=[point.y, point.x],
            radius=4,
            color="#6d28d9",
            fill=True,
            fill_color="#8b5cf6",
            fill_opacity=0.85,
            popup=clinic.get("name", "Clinic"),
        ).add_to(clinic_layer)
    clinic_layer.add_to(fmap)


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
    priority_legend_html = """
    <div style="
        position: fixed;
        bottom: 28px;
        left: 202px;
        z-index: 9999;
        background: white;
        padding: 12px 14px;
        border: 1px solid #cbd5e1;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.18);
        font-size: 13px;
        line-height: 1.5;
    ">
        <strong>Residential access priority</strong><br>
        <span style="color:#dc2626;">■</span> High<br>
        <span style="color:#f59e0b;">■</span> Medium<br>
        <span style="color:#16a34a;">■</span> Low<br>
        <span style="color:#969696;">■</span> Unknown
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(priority_legend_html))
    excluded_legend_html = """
    <div style="
        position: fixed;
        bottom: 174px;
        left: 28px;
        z-index: 9999;
        background: white;
        padding: 10px 12px;
        border: 1px solid #cbd5e1;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.18);
        font-size: 13px;
        line-height: 1.5;
    ">
        <strong>Grey grid cells</strong><br>
        Not analysed because residential<br>
        land-use coverage is below 5%.
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(excluded_legend_html))

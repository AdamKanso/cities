"""Streamlit interface for the Milan hospital accessibility analysis."""

from __future__ import annotations

import streamlit as st
from streamlit_folium import st_folium

from accessibility_map.analysis import AccessibilityThresholds, TravelTimeThresholds
from accessibility_map.map import build_map
from accessibility_map.workflow import AnalysisResult, run_analysis


st.set_page_config(
    page_title="Milan Hospital Accessibility",
    page_icon="M",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def load_analysis(
    distance_good: int,
    distance_medium: int,
    time_good: int,
    time_medium: int,
) -> AnalysisResult:
    """Cache the expensive OSM download and routing calculation per setting set."""
    return run_analysis(
        "Milan, Italy",
        AccessibilityThresholds(good_m=distance_good, medium_m=distance_medium),
        TravelTimeThresholds(good_minutes=time_good, medium_minutes=time_medium),
    )


def main() -> None:
    st.markdown(
        """
        <style>
            .block-container { max-width: 1600px; padding-top: 1.5rem; }
            [data-testid="stSidebar"] { background: #f6f7f9; }
            [data-testid="stMetric"] {
                border: 1px solid #d8dde5;
                border-radius: 6px;
                background: #ffffff;
                padding: 12px;
            }
            h1 { color: #172033; font-size: 2rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Analysis settings")
        st.text_input("City", value="Milan, Italy", disabled=True)
        scenario = st.radio(
            "Destinations",
            ["Hospitals only", "Hospitals + clinics"],
        )
        metric = st.radio(
            "View",
            ["Distance", "Driving time", "Priority"],
        )
        st.divider()
        st.subheader("Distance thresholds")
        distance_good = st.slider("Good access up to (m)", 250, 1500, 750, 50)
        distance_medium = st.slider("Medium access up to (m)", 500, 3000, 1500, 50)
        st.subheader("Driving-time thresholds")
        time_good = st.slider("Good access up to (min)", 2, 15, 5, 1)
        time_medium = st.slider("Medium access up to (min)", 3, 30, 10, 1)
        if st.button("Refresh OpenStreetMap data", use_container_width=True):
            load_analysis.clear()
            st.rerun()

    if distance_medium <= distance_good:
        st.error("The medium distance threshold must be greater than the good threshold.")
        return
    if time_medium <= time_good:
        st.error("The medium driving-time threshold must be greater than the good threshold.")
        return

    st.title("Milan Hospital Accessibility")
    st.caption("Residential grid analysis using OpenStreetMap road, hospital, clinic, and land-use data.")

    with st.spinner("Downloading OpenStreetMap data and calculating routes..."):
        result = load_analysis(
            distance_good,
            distance_medium,
            time_good,
            time_medium,
        )

    display_areas = (
        result.areas if scenario == "Hospitals only" else result.areas_with_clinics
    )
    category_column = {
        "Distance": "accessibility",
        "Driving time": "travel_time_accessibility",
        "Priority": "priority",
    }[metric]
    counts = display_areas[category_column].value_counts()

    labels = (
        ["Good", "Medium", "Poor", "Unknown"]
        if metric != "Priority"
        else ["High", "Medium", "Low", "Unknown"]
    )
    keys = [label.lower() for label in labels]
    metrics = st.columns(4)
    for column, label, key in zip(metrics, labels, keys, strict=True):
        column.metric(label, int(counts.get(key, 0)))

    fmap = build_map(
        result.boundary,
        result.areas,
        result.areas_with_clinics,
        result.excluded_areas,
        result.hospitals,
        result.clinics,
        result.graph,
        selected_scenario=scenario,
        selected_metric=metric,
    )
    map_key = (
        f"{scenario}-{metric}-{distance_good}-{distance_medium}-"
        f"{time_good}-{time_medium}"
    )
    st_folium(
        fmap,
        width=None,
        height=780,
        key=map_key,
        returned_objects=[],
    )

    with st.expander("Methodology and limitations"):
        st.write(
            "Accessibility is measured from residential 1 km grid cells to the nearest "
            "destination through the drivable road network. Driving time is estimated from "
            "OpenStreetMap road speeds; it is not live traffic data. Grey cells have less "
            "than 5% mapped residential land-use coverage and are excluded from scoring."
        )


if __name__ == "__main__":
    main()

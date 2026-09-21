# Interactive Accessibility Map

This project downloads OpenStreetMap data for a selected city, measures access from residential areas to hospitals, classifies areas as having good, medium, or poor accessibility, and exports an interactive Folium map.

The default example city is Milan, Italy, but the command line interface accepts any city name that can be geocoded by OpenStreetMap.

## Research Question

Which residential areas have poor access to hospitals?

## Methods

- Download city boundary, hospitals, roads, and neighborhood or residential area data from OpenStreetMap.
- Build a drivable road network with OSMnx.
- Estimate travel distance from each residential area centroid to the nearest hospital.
- Classify each area into accessibility classes.
- Display the result on an interactive Folium web map.

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Run

Generate the default Milan map:

```powershell
python -m accessibility_map --place "Milan, Italy" --output outputs/milan_accessibility.html
```

Open the generated HTML file in a browser.

## Output

The map shows:

- Hospitals as red markers.
- Residential or neighborhood areas colored by accessibility.
- A simplified road layer.
- Popups with estimated distance to the nearest hospital.

## Notes

OpenStreetMap data quality varies by city. If named neighborhood polygons are sparse, the project falls back to residential land-use areas and then to a regular analysis grid clipped to the city boundary.

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

## Step-by-Step Workflow

1. Create the project folder and initialize Git.

```powershell
git init
git remote add origin git@github.com:AdamKanso/Milano.git
```

2. Install the Python packages.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

3. Run the analysis for Milan.

```powershell
python -m accessibility_map --place "Milan, Italy" --output outputs/milan_accessibility.html
```

4. Run the tests.

```powershell
python -m pytest
```

5. Push the work to GitHub.

```powershell
git branch -M main
git push -u origin main
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

## Suggested Report Structure

1. Introduction and research question.
2. Why hospital accessibility matters in urban planning.
3. Data source: OpenStreetMap hospitals, roads, and residential or neighborhood polygons.
4. Method: city boundary download, residential area extraction, nearest hospital distance, classification thresholds, and Folium map visualization.
5. Results: describe which areas appear good, medium, or poor.
6. Limitations: OSM completeness, travel distance instead of live travel time, and simplified threshold choices.
7. Possible improvements: public transport, walking routes, population weighting, and emergency response times.

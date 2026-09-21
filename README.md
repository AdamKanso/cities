# Interactive Accessibility Map

This project downloads OpenStreetMap data for a selected city, measures access from residential grid cells to hospitals, classifies areas as having good, medium, or poor accessibility, and exports an interactive Folium map.

The default example city is Milan, Italy, but the command line interface accepts any city name that can be geocoded by OpenStreetMap.

## Research Question

Which residential areas have poor access to hospitals?

## Methods

- Download city boundary, hospitals, roads, and residential land-use data from OpenStreetMap.
- Create a regular 1 km grid inside the city boundary and keep cells with meaningful residential coverage.
- Build a drivable road network with OSMnx.
- Estimate road-network distance and driving time from each residential area to the nearest hospital.
- Classify each area using both distance and travel-time thresholds.
- Measure residential land-use coverage within every analysis area as a population-density proxy.
- Rank areas by their travel-time access need and relative residential coverage.
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
python -m pip install -e .
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
python -m pip install -e .
```

3. Run the analysis for Milan.

```powershell
python -m accessibility_map --place "Milan, Italy" --output outputs/milan_accessibility.html
```

Optional thresholds can be changed for a sensitivity analysis:

```powershell
python -m accessibility_map --place "Milan, Italy" --good-time-threshold 10 --medium-time-threshold 20
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

## Streamlit App

Run the local app:

```powershell
streamlit run app.py
```

Open the local address shown in the terminal, normally `http://localhost:8501`. The app provides selectable analyses for Milan, Rome, Zurich, Brussels, and Paris, plus controls for hospitals versus hospitals plus clinics, map metric, and accessibility thresholds. It downloads data only for the selected city.

## Output

The map shows:

- Hospitals as red markers.
- A distance-accessibility layer and an estimated driving-time accessibility layer.
- A residential access priority layer that highlights areas with poor travel-time access and greater residential coverage.
- Hospitals-only and hospitals-plus-clinics comparison layers, selectable from the top-right map control.
- A toggleable clinic marker layer to inspect the added facilities.
- Grey grid cells for places not analysed because residential land-use coverage is below 5%.
- A simplified road layer.
- Tooltips with distance, estimated driving time, residential coverage, and priority score.

## Notes

OpenStreetMap data quality varies by city. Residential land-use coverage is used to identify the grid cells most relevant to the analysis.

The default thresholds are 0.75 km and 1.5 km for distance, and 5 and 10 minutes for estimated driving time. They can be changed through the command-line options for sensitivity analysis.

## Comparing Clinics

The top-right layer control contains hospitals-only layers and hospitals-plus-clinics layers. Turn off the active hospitals-only layer, then turn on the matching hospitals-plus-clinics layer to compare how clinic availability changes the result. The `Clinics` layer shows the clinic locations in purple.

## Suggested Report Structure

1. Introduction and research question.
2. Why hospital accessibility matters in urban planning.
3. Data source: OpenStreetMap hospitals, roads, and residential or neighborhood polygons.
4. Method: city boundary download, residential grid creation, nearest hospital distance and travel time, classification thresholds, and Folium map visualization.
5. Results: describe which areas appear good, medium, or poor.
6. Limitations: OSM completeness, estimated rather than live travel time, residential land use as a population proxy, and simplified threshold choices.
7. Possible improvements: public transport, census population weighting, hospital capacity, and emergency response times.

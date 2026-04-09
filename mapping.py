"""
Mapping utilities for visualizing AI companies on an interactive map.

This module:
- Assigns marker colors based on founding year
- Builds popup content for each company
- Creates a Folium map with markers and legend
- Saves the final map as an HTML file

This is the "visualization" stage of the pipeline.
"""
import math
import os
import pandas as pd
import folium
from folium.plugins import Fullscreen, MarkerCluster

from config import OUTPUT_DIR
from utils import validate_columns, validate_not_empty

def marker_size(employees: float | int | None) -> float:
    """Scale marker radius using employee count."""
    if pd.isna(employees) or not employees:
        return 5

    # Log scaling keeps large companies from dominating the map
    radius = 2 + math.log10(float(employees)) * 2
    return max(4, min(14, radius))


def get_marker_color(founded: str | float | None) -> str:
    """Map founding year to a color bucket."""
    if pd.isna(founded):
        return "gray"

    try:
        year = int(founded)
    except ValueError:
        return "gray"

    if year < 2000:
        return "red"
    if year < 2010:
        return "orange"
    if year < 2020:
        return "yellow"
    return "green"


def build_popup_html(row: pd.Series) -> str:
    """Build HTML content for a company popup."""
    founded_display = row["founded"] if pd.notna(row["founded"]) else "Unknown"

    employees = row.get("employees")
    employees_display = (
        f"{int(employees):,}" if pd.notna(employees) else "Unknown"
    )

    popup_html = (
        f'<div style="font-family: Arial; font-size: 12px;">'
        f'<b>{row["name"]}</b><br>'
        f'{row["headquarters"]}<br>'
        f'Founded: {founded_display}<br>'
        f'Employees: {employees_display}<br><br>'
    )

    website = row.get("website")
    if pd.notna(website) and str(website).strip():
        popup_html += (
            f'<a href="{website}" target="_blank" style="color: #0066cc;">'
            f'Company Website</a> • '
        )

    popup_html += (
        f'<a href="{row["url"]}" target="_blank" style="color: #0066cc;">'
        f'Wikipedia</a></div>'
    )

    return popup_html


def add_legend(map_obj: folium.Map) -> None:
    """Add a custom legend to the Folium map."""
    legend_html = """
    <div style="
        position: fixed;
        bottom: 50px;
        left: 50px;
        width: 240px;
        background-color: white;
        border: 2px solid grey;
        border-radius: 8px;
        z-index: 9999;
        font-size: 14px;
        padding: 10px;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.15);
        line-height: 1.6;
    ">
      <div style="font-weight: 700; margin-bottom: 8px;">Region</div>
      <div><span style="color: blue;">●</span> North America</div>
      <div><span style="color: green;">●</span> Europe</div>
      <div><span style="color: red;">●</span> Asia / Middle East</div>
      <div><span style="color: gray;">●</span> Other</div>

      <div style="border-top: 1px solid #ddd; padding-top: 6px; margin-top: 8px; font-size: 13px;">
        Numbers = number of companies<br>
        Larger circles = more employees
      </div>
    </div>
    """
    map_obj.get_root().html.add_child(folium.Element(legend_html))


def region_from_country(country: str) -> str:
    """Map a country name to a broad region."""
    if pd.isna(country):
        return "Other"

    country = str(country).strip()

    if country in {"United States", "Canada"}:
        return "North America"
    if country in {
        "United Kingdom", "France", "Germany", "Sweden", "Netherlands",
        "Switzerland", "Ukraine", "Ireland", "Belgium", "Spain", "Italy",
        "Deutschland", "Sverige", "Україна"
    }:
        return "Europe"
    if country in {
        "China", "Taiwan", "Japan", "India", "South Korea", "Singapore",
        "Israel", "Saudi Arabia", "United Arab Emirates", "Hong Kong",
        "ישראל", "لسعودية", "中国", "日本", "대한민국"
    }:
        return "Asia / Middle East"

    return "Other"


def region_color(region: str) -> str:
    """Assign a marker color to each region."""
    colors = {
        "North America": "blue",
        "Europe": "green",
        "Asia / Middle East": "red",
        "Other": "gray",
    }
    return colors.get(region, "gray")


def make_cluster(color: str) -> MarkerCluster:
    """Create a MarkerCluster with a custom colored cluster icon."""
    js = f"""
    function(cluster) {{
        return L.divIcon({{
            html: '<div style="background:{color};color:white;border-radius:50%;'
                  + 'width:40px;height:40px;line-height:40px;text-align:center;'
                  + 'font-weight:bold;border:2px solid white;">'
                  + cluster.getChildCount() +
                  '</div>',
            className: 'marker-cluster-custom',
            iconSize: [40, 40]
        }});
    }}
    """
    return MarkerCluster(icon_create_function=js)


def make_map(companies_df: pd.DataFrame) -> None:
    """Build an interactive world map with clustered, region-colored markers."""
    validate_not_empty(companies_df, "make_map input")
    validate_columns(
        companies_df,
        ["name", "url", "headquarters", "lat", "lon", "country"],
        "make_map input",
    )

    valid = companies_df.dropna(subset=["lat", "lon"]).copy()
    print(f"Plotting {len(valid)} companies out of {len(companies_df)}")

    valid["region"] = valid["country"].apply(region_from_country)

    print("\nCountries classified as Other:")
    print(sorted(valid.loc[valid["region"] == "Other", "country"].dropna().unique()))

    m = folium.Map(
        location=[30, 0],
        zoom_start=3,
        tiles="CartoDB positron",
        min_zoom=2.5,
        world_copy_jump=False,
        max_bounds=True,
    )

    title_html = """
    <div style="
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        font-size: 18px;
        font-weight: 700;
        background-color: white;
        padding: 8px 14px;
        border-radius: 6px;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.15);
    ">
        Global AI Companies by Region and Size
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    layers = {
        "North America": folium.FeatureGroup(name="North America").add_to(m),
        "Europe": folium.FeatureGroup(name="Europe").add_to(m),
        "Asia / Middle East": folium.FeatureGroup(name="Asia / Middle East").add_to(m),
        "Other": folium.FeatureGroup(name="Other").add_to(m),
    }

    clusters = {
        "North America": make_cluster("blue").add_to(layers["North America"]),
        "Europe": make_cluster("green").add_to(layers["Europe"]),
        "Asia / Middle East": make_cluster("red").add_to(layers["Asia / Middle East"]),
        "Other": make_cluster("gray").add_to(layers["Other"]),
    }

    for _, row in valid.iterrows():
        region = row["region"]
        color = region_color(region)
        popup_html = build_popup_html(row)
        radius = marker_size(row.get("employees"))

        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    width:{radius * 2}px;
                    height:{radius * 2}px;
                    background:{color};
                    border:2px solid white;
                    border-radius:50%;
                    opacity:0.85;
                "></div>
                """
            ),
        ).add_to(clusters[region])

    add_legend(m)

    folium.LayerControl().add_to(m)
    Fullscreen().add_to(m)

    map_path = os.path.join(OUTPUT_DIR, "ai_companies_map.html")
    m.save(map_path)
    print(f"Map saved: {len(valid)} companies plotted → {map_path}")

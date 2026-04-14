"""
Mapping utilities for visualizing AI companies on an interactive map.
"""
import math
import os
import pandas as pd
import folium
from folium.plugins import Fullscreen, MarkerCluster

from config import OUTPUT_DIR


def marker_size(employees: float | int | None) -> float:
    """
    Scale marker radius using employee count.

    Uses logarithmic scaling to keep large companies from dominating the map.

    Args:
        employees (float | int | None): Number of employees, or None for unknown.

    Returns:
        float: Marker radius in pixels.
    """
    if pd.isna(employees) or not employees:
        return 5

    radius = math.log10(float(employees)) * 3
    return max(5, min(14, radius))


def build_popup_html(row: pd.Series) -> str:
    """
    Build HTML content for a company popup.

    Args:
        row (pd.Series): A DataFrame row containing company data.

    Returns:
        str: Formatted HTML string for display in a Folium popup.
    """
    if pd.notna(row["founded"]):
        founded_display = row["founded"]
        employees_display = f"{int(row.get('employees')):,}"
    else:
        founded_display = "Unknown"
        employees_display = "Unknown"

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
    """
    Add a custom legend to the Folium map.

    Args:
        map_obj (folium.Map): The Folium map object to add the legend to.

    Returns:
        None
    """
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
    """
    Map a country name to a broad region.

    Args:
        country (str): Country name to classify.

    Returns:
        str: Region name: "North America", "Europe", "Asia / Middle East", or "Other".
    """
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
    """
    Assign a marker color to each region.

    Args:
        region (str): Region name ("North America", "Europe", "Asia / Middle East", or "Other").

    Returns:
        str: Color name for map markers ("blue", "green", "red", or "gray").
    """
    colors = {
        "North America": "blue",
        "Europe": "green",
        "Asia / Middle East": "red",
        "Other": "gray",
    }
    return colors.get(region, "gray")


def make_cluster(color: str) -> MarkerCluster:
    """
    Create a MarkerCluster with a custom colored cluster icon.

    Args:
        color (str): Color name for the cluster icons (e.g., "blue", "green", "red", "gray").

    Returns:
        MarkerCluster: A Folium MarkerCluster object with custom styling.
    """
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
    """
    Build an interactive world map with clustered, region-colored markers.

    Creates a Folium map with regional layers, marker clusters, and legend.

    Args:
        companies_df (pd.DataFrame): DataFrame with company data including columns: 'name', 'url', 
            'headquarters', 'lat', 'lon', and 'country'.

    Returns:
        None. Saves map to disk at path specified by OUTPUT_DIR config.
    """
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

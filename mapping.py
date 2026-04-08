import os
import pandas as pd
import folium
from folium.plugins import Fullscreen

from config import OUTPUT_DIR
from utils import validate_columns, validate_not_empty

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

    popup_html = (
        f'<div style="font-family: Arial; font-size: 12px;">'
        f'<b>{row["name"]}</b><br>'
        f'{row["headquarters"]}<br>'
        f'Founded: {founded_display}<br><br>'
    )

    website = row.get("website")
    if website and str(website).strip() and str(website).strip() != "nan":
        popup_html += (
            f'<a href="{website}" target="_blank" style="color: #0066cc;">'
            f'Company Website</a> * '
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
        width: 210px;
        background-color: white;
        border: 2px solid grey;
        border-radius: 8px;
        z-index: 9999;
        font-size: 14px;
        padding: 10px;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.15);
        line-height: 1.6;
    ">
      <div style="font-weight: 700; margin-bottom: 8px;">Founded Year</div>
      <div style="display: flex; align-items: center; margin-bottom: 4px;">
        <span style="display: inline-block; width: 12px; height: 12px; margin-right: 8px; border-radius: 50%; background: red;"></span>
        Before 2000
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 4px;">
        <span style="display: inline-block; width: 12px; height: 12px; margin-right: 8px; border-radius: 50%; background: orange;"></span>
        2000-2009
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 4px;">
        <span style="display: inline-block; width: 12px; height: 12px; margin-right: 8px; border-radius: 50%; background: yellow; border: 1px solid #999;"></span>
        2010-2019
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 4px;">
        <span style="display: inline-block; width: 12px; height: 12px; margin-right: 8px; border-radius: 50%; background: green;"></span>
        2020+
      </div>
      <div style="display: flex; align-items: center;">
        <span style="display: inline-block; width: 12px; height: 12px; margin-right: 8px; border-radius: 50%; background: gray;"></span>
        Unknown
      </div>
    </div>
    """
    map_obj.get_root().html.add_child(folium.Element(legend_html))

def make_map(companies_df: pd.DataFrame) -> None:
    """Build an interactive world map and save it as an HTML file."""
    validate_not_empty(companies_df, "make_map input")
    validate_columns(
        companies_df,
        ["name", "url", "headquarters", "founded", "lat", "lon"],
        "make_map input",
    )

    m = folium.Map(
        location=[30, -30],
        zoom_start=2.5,
        tiles="CartoDB positron",
        min_zoom=2.5,
        world_copy_jump=False,
        max_bounds=True,
    )

    plotted = 0

    # Only plot companies with valid coordinates
    for _, row in companies_df.dropna(subset=["lat", "lon"]).iterrows():
        color = get_marker_color(row["founded"])
        popup_html = build_popup_html(row)

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=250),
        ).add_to(m)

        plotted += 1

    add_legend(m)
    Fullscreen().add_to(m)

    map_path = os.path.join(OUTPUT_DIR, "ai_companies_map.html")
    m.save(map_path)
    print(f"Map saved: {plotted} companies plotted → {map_path}")

"""
Scrape AI company headquarters from Wikipedia and plot them on a world map.

Usage:
    uv run python ai_companies.py                               # full run
    uv run python ai_companies.py --skip-scrape                 # skip to geocode
    uv run python ai_companies.py --skip-scrape --skip-geocode  # map only
"""

import os
import time
import re
import argparse

import requests
import pandas as pd
import folium
from folium.plugins import Fullscreen
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim

BASE = "https://en.wikipedia.org"
LIST_URL = f"{BASE}/wiki/List_of_artificial_intelligence_companies"
OUTPUT_DIR = "outputs"
CACHE_FILE = os.path.join(OUTPUT_DIR, "ai_companies.csv")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

HEADERS = {"User-Agent": USER_AGENT}

os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_company_links() -> list[dict[str, str]]:
    """Scrape the list page for company names and Wikipedia URLs."""
    resp = requests.get(LIST_URL, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(resp.text, "lxml")
    companies = []
    for link in soup.select("div.mw-parser-output li a[href^='/wiki/']"):
        name = link.text.strip()
        href = link["href"]

        if ":" not in href:  # skip Wikipedia meta-links
            # Skip links in navbox or see also
            if link.find_parent("div", class_="navbox") or "list of" in name.lower():
                continue
            companies.append({"name": name, "url": BASE + href})

    return companies


def get_company_info(url: str) -> dict[str, str | None]:
    """Fetch a company's Wikipedia page and extract its headquarters and founding year.

    Looks for 'Headquarters' and 'Founded' rows in the article's infobox table.
    Returns a dict with 'headquarters' and 'founded' keys, or None if not found.

    Args:
        url: Full URL of the company's Wikipedia article.

    Returns:
        A dict with 'headquarters' and 'founded' (year as string), or None for each if not found.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        infobox = soup.find("table", class_="infobox")
        if not infobox:
            return {"headquarters": None, "founded": None}
        hq = None
        founded = None
        for row in infobox.find_all("tr"):
            header = row.find("th")
            if not header:
                continue
            header_text = header.text.lower()
            cell = row.find("td")
            if not cell:
                continue
            if "headquarters" in header_text:
                hq = cell.get_text(separator=" ", strip=True)
            elif "founded" in header_text or "founding" in header_text:
                founded_text = cell.get_text(separator=" ", strip=True)
                # Extract the first 4-digit year
                year_match = re.search(r'\b(19|20)\d{2}\b', founded_text)
                if year_match:
                    founded = year_match.group(0)
        return {"headquarters": hq, "founded": founded}
    except Exception:  # pylint: disable=broad-exception-caught
        return {"headquarters": None, "founded": None}


def scrape_companies() -> pd.DataFrame:
    """Scrape company names, headquarters, and founding years from Wikipedia.

    Fetches the first 100 companies from the Wikipedia AI companies list,
    visits each article to extract headquarters and founding year data, and caches the
    results to CACHE_FILE as a CSV.

    Returns:
        A DataFrame with columns: 'name', 'headquarters', 'founded', 'url'.
    """
    companies = get_company_links()[:100]
    print(f"Found {len(companies)} companies")
    records = []
    for i, co in enumerate(companies):
        print(f"  [{i + 1}/{len(companies)}] {co['name']}")
        info = get_company_info(co["url"])
        records.append({"name": co["name"], **info, "url": co["url"]})
        time.sleep(0.5)  # be a good citizen
    company_df = pd.DataFrame(records)
    company_df.to_csv(CACHE_FILE, index=False)
    print(f"Saved to {CACHE_FILE}")
    return company_df


def geocode(companies_df: pd.DataFrame) -> pd.DataFrame:
    """Add latitude and longitude columns to the companies DataFrame.

    Geocodes each headquarters string using the Nominatim geocoder.
    Rows where headquarters is NaN or cannot be geocoded are assigned
    None for both lat and lon. Sleeps 1.1 seconds between requests to
    respect Nominatim's rate limit of one request per second.

    Args:
        companies_df: DataFrame with at least a 'headquarters' column.

    Returns:
        The same DataFrame with 'lat' and 'lon' columns appended.
    """
    geolocator = Nominatim(user_agent=USER_AGENT)
    lats: list[float | None] = []
    lons: list[float | None] = []
    countries: list[str] = []
    for hq in companies_df["headquarters"]:
        if pd.isna(hq):
            lats.append(None)
            lons.append(None)
            countries.append("Unknown")
            continue
        try:
            loc = geolocator.geocode(hq, timeout=10)
            if loc:
                lats.append(loc.latitude)
                lons.append(loc.longitude)
                # Extract country from address
                address_parts = loc.address.split(',') if loc.address else []
                country = address_parts[-1].strip() if address_parts else "Unknown"
                countries.append(country)
            else:
                lats.append(None)
                lons.append(None)
                countries.append("Unknown")
        except Exception:  # pylint: disable=broad-exception-caught
            lats.append(None)
            lons.append(None)
            countries.append("Unknown")
        time.sleep(1.1)  # Nominatim rate limit: 1 req/sec
    companies_df["lat"] = lats
    companies_df["lon"] = lons
    companies_df["country"] = countries
    return companies_df


def make_map(companies_df: pd.DataFrame) -> None:
    """Build an interactive world map and save it as an HTML file.

    Plots each company as a colored circle marker on a CartoDB Positron
    basemap. Markers are colored by founding year. Tooltips show the company name,
    headquarters, and founding year. Includes a legend for the color coding.

    Args:
        companies_df: DataFrame with 'name', 'headquarters', 'founded', 'lat',
            'lon', and 'country' columns. Rows missing lat or lon are skipped.
    """
    def get_color(founded):
        if pd.isna(founded):
            return 'gray'
        try:
            year = int(founded)
            if year < 2000:
                return 'red'
            elif 2000 <= year < 2010:
                return 'orange'
            elif 2010 <= year < 2020:
                return 'yellow'
            else:
                return 'green'
        except ValueError:
            return 'gray'

    m = folium.Map(
        location=[30, -30],
        zoom_start=2.5,
        tiles="CartoDB positron",
        min_zoom=2.5,
        world_copy_jump=False,
        max_bounds=True,
    )

    plotted = 0
    for _, row in companies_df.dropna(subset=["lat", "lon"]).iterrows():
        color = get_color(row['founded'])
        founded_display = row['founded'] if pd.notna(row['founded']) else 'Unknown'
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            tooltip=f"{row['name']} — Founded {founded_display}",
            popup=folium.Popup(
                f'<a href="{row["url"]}" target="_blank">{row["name"]}</a><br>{row["headquarters"]}<br><b>Founded: {founded_display}</b>',
                max_width=250,
            ),
        ).add_to(m)
        plotted += 1

    # Add legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 210px; background-color: white; border: 2px solid grey; border-radius: 8px; z-index: 9999; font-size: 14px; padding: 10px; box-shadow: 2px 2px 6px rgba(0,0,0,0.15); line-height: 1.6;">
      <div style="font-weight: 700; margin-bottom: 8px;">Founded Year</div>
      <div style="display: flex; align-items: center; margin-bottom: 4px;"><span style="display: inline-block; width: 12px; height: 12px; margin-right: 8px; border-radius: 50%; background: red;"></span>Before 2000</div>
      <div style="display: flex; align-items: center; margin-bottom: 4px;"><span style="display: inline-block; width: 12px; height: 12px; margin-right: 8px; border-radius: 50%; background: orange;"></span>2000-2009</div>
      <div style="display: flex; align-items: center; margin-bottom: 4px;"><span style="display: inline-block; width: 12px; height: 12px; margin-right: 8px; border-radius: 50%; background: yellow; border: 1px solid #999;"></span>2010-2019</div>
      <div style="display: flex; align-items: center; margin-bottom: 4px;"><span style="display: inline-block; width: 12px; height: 12px; margin-right: 8px; border-radius: 50%; background: green;"></span>2020+</div>
      <div style="display: flex; align-items: center;"><span style="display: inline-block; width: 12px; height: 12px; margin-right: 8px; border-radius: 50%; background: gray;"></span>Unknown</div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    map_path = os.path.join(OUTPUT_DIR, "ai_companies_map.html")
    Fullscreen().add_to(m)
    m.save(map_path)
    print(f"Map saved: {plotted} companies plotted → {map_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Map global AI companies from Wikipedia."
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Load from cache, skip scraping Wikipedia",
    )
    parser.add_argument(
        "--skip-geocode",
        action="store_true",
        help="Load from cache, skip geocoding",
    )
    args = parser.parse_args()

    if args.skip_scrape:
        print(f"Loading from {CACHE_FILE}")
        df = pd.read_csv(CACHE_FILE)
    else:
        df = scrape_companies()

    if not args.skip_geocode:
        df = geocode(df)
        df.to_csv(CACHE_FILE, index=False)

    make_map(df)

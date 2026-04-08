"""
Geocoding utilities for converting headquarters into coordinates.

This module enriches scraped company data by:
- Converting headquarters text into latitude/longitude
- Extracting country information
- Caching geocoding results to avoid repeated API calls

This is the "data enrichment" stage of the pipeline.
"""
import os
import time
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable

from config import GEOCODE_CACHE_FILE, USER_AGENT
from utils import validate_columns, validate_not_empty #, normalize_headquarters

def load_geocode_cache() -> dict[str, tuple[float | None, float | None, str]]:
    """Load geocoding results from disk into a dict keyed by headquarters string."""
    if not os.path.exists(GEOCODE_CACHE_FILE):
        return {}

    cache_df = pd.read_csv(GEOCODE_CACHE_FILE)
    cache: dict[str, tuple[float | None, float | None, str]] = {}

    for _, row in cache_df.iterrows():
        hq = row["headquarters"]
        lat = row["lat"] if pd.notna(row["lat"]) else None
        lon = row["lon"] if pd.notna(row["lon"]) else None
        country = row["country"] if pd.notna(row["country"]) else "Unknown"
        cache[hq] = (lat, lon, country)

    return cache


def save_geocode_cache(cache: dict[str, tuple[float | None, float | None, str]]) -> None:
    """Save geocoding cache to disk."""
    rows = []
    for headquarters, (lat, lon, country) in cache.items():
        rows.append({
            "headquarters": headquarters,
            "lat": lat,
            "lon": lon,
            "country": country,
        })

    cache_df = pd.DataFrame(rows)
    cache_df.to_csv(GEOCODE_CACHE_FILE, index=False)


def geocode(companies_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert headquarters strings into geographic coordinates.

    This demonstrates:
    - enriching scraped data with an external service
    - caching expensive operations
    - handling unreliable external APIs
    """
    validate_not_empty(companies_df, "geocode input")
    validate_columns(companies_df, ["name", "url", "headquarters"], "geocode input")

    geolocator = Nominatim(user_agent=USER_AGENT)
    geocode_cache = load_geocode_cache()

    lats = []
    lons = []
    countries = []

    for hq in companies_df["headquarters"]:
        if pd.isna(hq):
            lats.append(None)
            lons.append(None)
            countries.append("Unknown")
            continue

        # # Normalize string to improve cache hits
        # hq = normalize_headquarters(clean_headquarters_text(str(hq)))

        # Check cache first (avoid repeated API calls)
        if hq in geocode_cache:
            lat, lon, country = geocode_cache[hq]
            lats.append(lat)
            lons.append(lon)
            countries.append(country)
            continue

        try:
            # Call external geocoding service
            loc = geolocator.geocode(hq, timeout=10)

        except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError) as e:
            # External service failures are expected sometimes
            print(f"Geocoding failed for '{hq}': {e}")
            lat, lon, country = None, None, "Unknown"

        else:
            if loc:
                lat = loc.latitude
                lon = loc.longitude

                # Extract country from full address string
                parts = loc.address.split(",") if loc.address else []
                country = parts[-1].strip() if parts else "Unknown"
            else:
                lat, lon, country = None, None, "Unknown"

        # Save result to cache
        geocode_cache[hq] = (lat, lon, country)

        lats.append(lat)
        lons.append(lon)
        countries.append(country)

        # Respect Nominatim rate limits
        time.sleep(1.1)

    companies_df["lat"] = lats
    companies_df["lon"] = lons
    companies_df["country"] = countries

    # Persist cache for future runs
    save_geocode_cache(geocode_cache)

    return companies_df

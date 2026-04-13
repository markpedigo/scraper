"""
Geocode utilities for converting headquarters into coordinates.

This module:
- Converts headquarters text into latitude/longitude.
- Extracts country information.
- Caches geocoding results to avoid repeated API calls.
"""
import os
import time
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable

from config import GEOCODE_CACHE_FILE, USER_AGENT
from utils import validate_columns, validate_not_empty
from utils import simplify_headquarters, normalize_headquarters

def load_geocode_cache() -> dict[str, tuple[float | None, float | None, str]]:
    """
    Load geocoding results from disk into a dict keyed by headquarters string.

    Returns:
        dict[str, tuple[float | None, float | None, str]]: A dictionary that maps
            headquarters strings to tuples of (latitude, longitude, country).
            Latitude and longitude are None if geocoding failed.
    """
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
    """
    Save geocoding cache to disk.

    Args:
        cache (dict[str, tuple[float | None, float | None, str]]): A dictionary
            mapping headquarters strings to tuples of (latitude, longitude,
            country).

    Returns:
        None
    """
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

    This function:
    - validates the input DataFrame
    - cleans and simplifies headquarters strings
    - reuses cached geocoding results when available
    - calls Nominatim only when needed
    - appends lat, lon, and country columns

    Args:
        companies_df (pd.DataFrame): A DataFrame with columns 'name', 'url',
            and 'headquarters'. The 'headquarters' column contains location
            strings to geocode.

    Returns:
        pd.DataFrame: The input DataFrame with three new columns added:
            - 'lat' (float | None): Latitude of the headquarters location
            - 'lon' (float | None): Longitude of the headquarters location
            - 'country' (str): Country extracted from the geocoding result
    """
    validate_not_empty(companies_df, "geocode input")
    validate_columns(companies_df, ["name", "url", "headquarters"], "geocode input")

    geolocator = Nominatim(user_agent=USER_AGENT)
    geocode_cache = load_geocode_cache()

    lats: list[float | None] = []
    lons: list[float | None] = []
    countries: list[str] = []

    for hq in companies_df["headquarters"]:
        if pd.isna(hq):
            lats.append(None)
            lons.append(None)
            countries.append("Unknown")
            continue

        # Clean the raw headquarters text for geocoding.
        hq_clean = simplify_headquarters(str(hq))

        # Normalize the cleaned string so equivalent values reuse the same cache entry.
        key = normalize_headquarters(hq_clean)

        # Reuse cached result if we already geocoded this location.
        if key in geocode_cache:
            lat, lon, country = geocode_cache[key]
            lats.append(lat)
            lons.append(lon)
            countries.append(country)
            continue

        try:
            loc = geolocator.geocode(hq_clean, timeout=10)
        except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError) as e:
            print(f"Geocoding failed for '{hq_clean}': {e}")
            lat, lon, country = None, None, "Unknown"
        else:
            if loc:
                lat = loc.latitude
                lon = loc.longitude
                address_parts = loc.address.split(",") if loc.address else []
                country = address_parts[-1].strip() if address_parts else "Unknown"
            else:
                lat, lon, country = None, None, "Unknown"

        # Save the result under the normalized cache key.
        geocode_cache[key] = (lat, lon, country)

        lats.append(lat)
        lons.append(lon)
        countries.append(country)

        # Sleep only when we make a real API call.
        time.sleep(1.1)

    companies_df["lat"] = lats
    companies_df["lon"] = lons
    companies_df["country"] = countries

    save_geocode_cache(geocode_cache)
    return companies_df

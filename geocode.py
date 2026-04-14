"""
Geocode utilities for converting headquarters into coordinates.
"""
import time
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable
from config import USER_AGENT


def geocode_address(geolocator: Nominatim, hq: str) -> tuple[float | None, float | None, str]:
    """
    Geocode a single headquarters string to coordinates and country.

    Args:
        geolocator: Initialized Nominatim geolocator instance.
        hq: Headquarters location string (e.g., "San Francisco, U.S.").

    Returns:
        Tuple of (latitude, longitude, country). Latitude and longitude
        are None on failure; country is "Unknown" on failure.
    """
    try:
        loc = geolocator.geocode(hq, timeout=10)
    except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError) as e:
        print(f"Geocoding failed for '{hq}': {e}")
        return None, None, "Unknown"

    if not loc:
        return None, None, "Unknown"

    if loc.address:
        country = loc.address.split(",")[-1].strip()
    else:
        country = "Unknown"

    return loc.latitude, loc.longitude, country


def geocode_company_hq(companies_df: pd.DataFrame) -> pd.DataFrame:
    """
    Geocode the headquarters of each company in a DataFrame.

    Iterates over the 'headquarters' column, resolving each entry to
    latitude, longitude, and country via Nominatim. Sleeps 1.1 seconds
    between requests to comply with Nominatim's rate limit policy.

    Args:
        companies_df: DataFrame with a 'headquarters' column.

    Returns:
        The input DataFrame with 'lat', 'lon', and 'country' columns added.
    """
    geolocator = Nominatim(user_agent=USER_AGENT)

    results = []
    for hq in companies_df["headquarters"]:
        if pd.notna(hq):
            results.append(geocode_address(geolocator, hq))
            time.sleep(1.1)
        else:
            results.append((None, None, "Unknown"))

    companies_df["lat"], companies_df["lon"], companies_df["country"] = zip(*results)
    return companies_df

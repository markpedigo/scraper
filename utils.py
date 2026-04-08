"""
Shared utility functions used across the project.

Includes:
- HTTP helper for fetching and parsing HTML
- DataFrame validation helpers
- String normalization for consistent geocoding keys

These functions support multiple stages of the pipeline but are not
specific to scraping, geocoding, or mapping.
"""
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

from config import HEADERS


def fetch_soup(url: str) -> BeautifulSoup:
    """Fetch a URL and return a parsed BeautifulSoup object."""
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def validate_columns(df: pd.DataFrame, required: list[str], stage: str) -> None:
    """Raise an error if required columns are missing."""
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns at {stage}: {missing}. "
            f"Available columns: {list(df.columns)}"
        )


def validate_not_empty(df: pd.DataFrame, stage: str) -> None:
    """Raise an error if a DataFrame is empty."""
    if df.empty:
        raise ValueError(f"DataFrame is empty at {stage}.")


def clean_headquarters_text(hq: str) -> str:
    """Remove citation markers and normalize punctuation spacing."""
    hq = re.sub(r"\[\s*\d+\s*\]", "", hq)   # remove [1], [ 2 ], etc.
    hq = re.sub(r"\s+,", ",", hq)           # remove space before commas
    hq = re.sub(r"\s+", " ", hq)            # collapse repeated whitespace
    return hq.strip(" ,")

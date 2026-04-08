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


def normalize_headquarters(hq: str) -> str:
    """Normalize headquarters text for cache lookup."""
    return " ".join(hq.split()).strip()

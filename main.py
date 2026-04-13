"""
Command-line entry point for the AI companies pipeline.

This script orchestrates the full workflow:
1. Scrape company data (or load from cache)
2. Geocode headquarters (optional)
3. Generate an interactive map

Command-line flags allow skipping stages for faster iteration.
"""
import os
import argparse
import pandas as pd

from config import OUTPUT_DIR, CACHE_FILE
from scrape import scrape_companies
from geocode import geocode
from mapping import make_map
from utils import validate_columns, validate_not_empty


def main() -> None:
    """
    Run the AI companies data pipeline.

    This function orchestrates the full workflow:

    1. Scrape company data from Wikipedia (or load from cache)
    2. Geocode headquarters locations (optional)
    3. Generate an interactive map of company locations

    Command-line flags:
    --skip-scrape   Load cached data instead of scraping Wikipedia
    --skip-geocode  Skip geocoding and use existing coordinates

    The pipeline is designed for iterative development, allowing
    individual stages to be skipped when data is already available.
    """
    print("Pipeline: scrape → geocode → map\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

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
        validate_not_empty(df, "cache load")
        validate_columns(df, ["name", "url"], "cache load")
    else:
        df = scrape_companies()

    if not args.skip_geocode:
        df = geocode(df)
        df.to_csv(CACHE_FILE, index=False)

    make_map(df)

    # Summary table
    print(df["country"].value_counts().head(10))

    # Top N by employees
    print(
        df[["name", "employees", "country"]]
        .dropna(subset=["employees"])
        .sort_values("employees", ascending=False)
        .head(10)
    )

if __name__ == "__main__":
    main()

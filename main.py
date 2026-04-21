"""
Command-line entry point for the AI companies pipeline.

This script orchestrates the full workflow:
1. Scrape company data (or load from cache)
2. Geocode headquarters
3. Generate an interactive map

Command-line flags allow skipping stages for faster iteration.
    --skip-scrape:      Skips wikipedia page scrape, loads from cache.
    --skip-geocoding:   Skips geocoding, loads from cache.    
"""
import os
import argparse
import pandas as pd

from config import OUTPUT_DIR, SCRAPE_CACHE_FILE, GEOCODE_CACHE_FILE
from scrape import scrape_companies
from geocode import geocode_company_hq
from mapping import make_map
from utils import validate_columns, validate_not_empty


def main() -> None:
    """
    Run the AI companies data pipeline.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Pipeline: scrape → geocode → map\n")

    # Set up parser
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


    # Scrape
    print("Scrape company data...")
    if args.skip_scrape:
        print(f"Loading from {SCRAPE_CACHE_FILE}")
        companies_df = pd.read_csv(SCRAPE_CACHE_FILE)
        validate_not_empty(companies_df, "cache load")
        validate_columns(companies_df, ["name", "url"], "cache load")
    else:
        companies_df = scrape_companies()
        companies_df.to_csv(SCRAPE_CACHE_FILE, index=False)

    # Geocode
    print("\nGeocode headquarters...")
    if args.skip_geocode:
        print(f"Loading from {GEOCODE_CACHE_FILE}")
        companies_df = pd.read_csv(GEOCODE_CACHE_FILE)
    else:
        companies_df = geocode_company_hq(companies_df)
        companies_df.to_csv(GEOCODE_CACHE_FILE, index=False)

    # Generate map
    print("\nGenerate interactive html map...")
    make_map(companies_df)

    print("\nProgram complete.")

if __name__ == "__main__":
    main()

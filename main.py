import os
import argparse
import pandas as pd

from config import OUTPUT_DIR, CACHE_FILE
from scrape import scrape_companies
from geocode import geocode
from mapping import make_map
from utils import validate_columns, validate_not_empty


def main() -> None:
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


if __name__ == "__main__":
    main()
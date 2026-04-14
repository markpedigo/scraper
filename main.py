"""
Command-line entry point for the AI companies pipeline.

This script orchestrates the full workflow:
1. Scrape company data (or load from cache)
2. Geocode headquarters
3. Generate an interactive map
"""
import os

from config import OUTPUT_DIR  #, CSV_FILE
from scrape import scrape_companies
from geocode import geocode_company_hq
from mapping import make_map


def main() -> None:
    """
    Run the AI companies data pipeline.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Scrape company data...")
    companies_df = scrape_companies()

    print("\nGeocode headquarters...")
    companies_df = geocode_company_hq(companies_df)

    print("\nGenerate an interactive html map...")
    make_map(companies_df)

    print("Program complete.")

    # geocode_df.to_csv(CSV_FILE, index=False)


if __name__ == "__main__":
    main()

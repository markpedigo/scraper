# AI Companies Map

Scrapes AI company data from Wikipedia, geocodes headquarters, and plots an interactive world map.

## Usage

    uv run python main.py                               # full run
    uv run python main.py --skip-scrape                 # skip to geocode
    uv run python main.py --skip-scrape --skip-geocode  # map only

## Output

- `out/ai_companies.csv` — scraped and geocoded data
- `out/geocode_cache.csv` — geocoding cache
- `out/ai_companies_map.html` — interactive map

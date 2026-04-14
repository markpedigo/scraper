"""
Configuration constants.
"""
BASE_URL = "https://en.wikipedia.org"
ARTICLE_URL = f"{BASE_URL}/wiki/List_of_artificial_intelligence_companies"

OUTPUT_DIR = "out"
# CSV_FILE = os.path.join(OUTPUT_DIR, "ai_companies.csv")
# GEOCODE_CACHE_FILE = os.path.join(OUTPUT_DIR, "geocode_cache.csv")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

HEADERS = {"User-Agent": USER_AGENT}

NO_COMPANY_DATA = {"headquarters": None,
                   "founded": None,
                   "website": None,
                   "employees": None}

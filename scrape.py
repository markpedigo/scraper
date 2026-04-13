"""
Scraping logic for collecting AI company data from Wikipedia.

This module handles:
1. Extracting company links from the list page
2. Visiting each company page
3. Parsing infobox data (headquarters, founding year, website)
4. Returning structured data as a DataFrame

This is the "data collection" stage of the pipeline.
"""
import re
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup

from config import BASE_URL, LIST_URL, CACHE_FILE
from utils import fetch_soup, validate_columns, validate_not_empty, clean_headquarters_text

def get_company_links() -> list[dict[str, str]]:
    """
    Scrape the Wikipedia list page and return unique company links.

    Returns:
        list[dict[str, str]]: List of dictionaries with keys 'name' and 'url'
            for each company found on the Wikipedia AI companies list.
    """
    soup = fetch_soup(LIST_URL)

    companies = []
    seen_hrefs = set()

    candidate_links = soup.select("div.mw-parser-output ul li a[href^='/wiki/']")

    for link in candidate_links:
        name = link.get_text(strip=True)
        href = link.get("href", "")

        if ":" in href:
            continue

        if link.find_parent("div", class_="navbox"):
            continue

        if "list of" in name.lower():
            continue

        if href in seen_hrefs:
            continue

        seen_hrefs.add(href)
        companies.append({
            "name": name,
            "url": BASE_URL + href,
        })

    return companies


def parse_company_infobox(soup: BeautifulSoup) -> dict[str, str | None]:
    """
    Parse a Wikipedia company page and extract headquarters, founding year,
    and website from the infobox.

    Args:
        soup (BeautifulSoup): Parsed HTML of a Wikipedia company page.

    Returns:
        dict[str, str | None]: Dictionary with keys 'headquarters', 'founded',
            'website', and 'employees', with values as strings or None if not found.
    """
    infobox = soup.find("table", class_="infobox")
    if not infobox:
        return {"headquarters": None,
                "founded": None,
                "website": None,
                "employees": None}

    hq = None
    founded = None
    website = None
    employees = None

    for row in infobox.find_all("tr"):
        header = row.find("th")
        if not header:
            continue

        header_text = header.get_text(" ", strip=True).lower()
        cell = row.find("td")
        if not cell:
            continue

        if "headquarters" in header_text:
            for sup in cell.find_all("sup", class_="reference"):
                sup.decompose()
            hq = clean_headquarters_text(cell.get_text(separator=" ", strip=True))
        elif "founded" in header_text or "founding" in header_text:
            founded_text = cell.get_text(separator=" ", strip=True)
            match = re.search(r"\b(19|20)\d{2}\b", founded_text)
            if match:
                founded = match.group(0)
        elif "website" in header_text:
            link = cell.find("a", href=True)
            if link:
                website = link["href"]
                if not website.startswith("http"):
                    website = "https://" + website
        elif "employees" in header_text:
            employees_text = cell.get_text(separator=" ", strip=True)

            # Grab the first large integer-like value: 1,500 or 1500
            match = re.search(r"\b\d[\d,]*\b", employees_text)
            if match:
                employees = int(match.group(0).replace(",", ""))

    return {"headquarters": hq,
            "founded": founded,
            "website": website,
            "employees": employees}


def get_company_info(url: str) -> dict[str, str | None]:
    """
    Fetch a company's Wikipedia page and extract headquarters,
    founding year, and website.

    Args:
        url (str): Wikipedia URL of the company page.

    Returns:
        dict[str, str | None]: Dictionary with keys 'headquarters', 'founded',
            'website', and 'employees'. Returns all None values if the request fails.
    """
    try:
        soup = fetch_soup(url)
    except requests.RequestException as e:
        print(f"Request failed for {url}: {e}")
        return {"headquarters": None,
                "founded": None,
                "website": None,
                "employees": None}

    return parse_company_infobox(soup)


def scrape_companies() -> pd.DataFrame:
    """
    Scrape company names, headquarters, founding years, and websites from Wikipedia.

    Fetches companies from the Wikipedia AI companies list, visits each article
    to extract headquarters, founding year, website, and employee count data,
    deduplicates by URL, and caches results to CACHE_FILE as CSV.

    Returns:
        pd.DataFrame: DataFrame with columns 'name', 'headquarters', 'founded',
            'website', 'employees', and 'url'.
    """
    companies = get_company_links()
    print(f"Found {len(companies)} companies")
    records = []
    for i, co in enumerate(companies):
        print(f"  [{i + 1}/{len(companies)}] {co['name']}")
        info = get_company_info(co["url"])
        records.append({"name": co["name"], **info, "url": co["url"]})
        time.sleep(0.5)  # be a good citizen
    company_df = pd.DataFrame(records)
    company_df = company_df.drop_duplicates(subset="url")

    validate_not_empty(company_df, "scrape_companies")
    validate_columns(
        company_df,
        ["name", "headquarters", "founded", "website", "employees", "url"],
        "scrape_companies",
    )

    company_df.to_csv(CACHE_FILE, index=False)
    print(f"Saved to {CACHE_FILE}")
    return company_df

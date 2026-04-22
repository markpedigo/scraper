"""
Scraping logic for collecting AI company data from Wikipedia.
"""
import re
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup

from config import BASE_URL, ARTICLE_URL, NO_COMPANY_DATA
from utils import fetch_soup, clean_hq_text, validate_columns, validate_not_empty

def get_company_links() -> list[dict[str, str]]:
    """
    Scrape the Wikipedia list page and return unique company links.

    Returns:
        list[dict[str, str]]: List of dictionaries with keys 'name' and 'url'
                              for each company found on the Wikipedia AI companies list.
                              e.g., [{'name': 'BlueDot', 
                                      'url': 'https://en.wikipedia.org/wiki/BlueDot'},
                                     {'name': 'Cohere',
                                      'url': 'https://en.wikipedia.org/wiki/Cohere'}}]
    """
    # Get html code from article.
    soup = fetch_soup(ARTICLE_URL)

    # From article html code, select links that start with "/wiki/".
    wiki_links = soup.select("div.mw-parser-output ul li a[href^='/wiki/']")

    # Pull out legit hrefs from wiki_links.
    company_links = []
    seen_hrefs = set()  # don't add dup links; e.g., Hugging Face appears twice in article
    for wiki_link in wiki_links:
        name = wiki_link.get_text(strip=True)
        href = wiki_link.get("href", "")

        # If legit and not already in list, add link to company links list
        if ((href in seen_hrefs) or
            (":" in href) or
            (wiki_link.find_parent("div", class_="navbox")) or
            ("list of" in name.lower()) or
            ("lists of" in name.lower())):
            continue

        seen_hrefs.add(href)

        company_links.append({
            "name": name,
            "url": BASE_URL + href,
        })

    return company_links


def parse_company_infobox(soup: BeautifulSoup) -> dict[str, str | int | None]:
    """
    Extract key company fields from a Wikipedia infobox.

    Parses the first table with class 'infobox' on the page, returning
    headquarters, founding year, website, and employee count. Returns
    NO_COMPANY_DATA if no infobox is found.

    Args:
        soup: Parsed BeautifulSoup object of a Wikipedia company page.

    Returns:
        Dict with keys 'headquarters', 'founded', 'website', 'employees'.
        Any field not found in the infobox is None.
    """
    # Get info box from soup object.
    infobox = soup.find("table", class_="infobox")
    if not infobox:
        return NO_COMPANY_DATA

    # Parse info box.
    headquarters = year_founded = website = nbr_employees = None
    for row in infobox.find_all("tr"):
        label_element = row.find(class_="infobox-label")
        data_element  = row.find(class_="infobox-data")
        if not (label_element and data_element):
            continue

        label = label_element.get_text(strip=True).lower()
        data  = data_element.get_text(" ", strip=True)

        if "headquarters" in label:
            headquarters = clean_hq_text(data)
        elif "founded" in label:
            match = re.search(r'\b\d{4}\b', data)
            year_founded = match.group() if match else None
        elif "website" in label:
            link = data_element.find("a", href=True)
            if link:
                website = link["href"]
                if not website.startswith("http"):
                    website = "https://" + website
        elif "employees" in label:
            m = re.search(r'\d+', data)
            nbr_employees = int(m.group()) if m else None

    return {"headquarters": headquarters,
            "founded": year_founded,
            "website": website,
            "employees": nbr_employees}


def get_company_info(url: str) -> dict[str, str | int | None]:
    """
    Fetch a Wikipedia company page and extract infobox fields.

    Retrieves the page at the given URL, parses the infobox, and returns
    structured company data. Returns NO_COMPANY_DATA on request failure.

    Args:
        url: Full URL of a Wikipedia company page.

    Returns:
        Dict with keys 'headquarters', 'founded', 'website', 'employees'.
        Any field not found in the infobox is None.
    """
    try:
        soup = fetch_soup(url)
        return parse_company_infobox(soup)
    except requests.RequestException as e:
        print(f"Request failed for {url}: {e}")
        return NO_COMPANY_DATA


def scrape_companies() -> pd.DataFrame:
    """
    Scrape company names, headquarters, founding years, and websites from Wikipedia.

    Fetches companies from the Wikipedia AI companies list, visits each article
    to extract headquarters, founding year, website, and employee count data,
    and deduplicates by URL.

    Returns:
        pd.DataFrame: DataFrame with columns 'name', 'headquarters', 'founded',
            'website', 'employees', and 'url'.
    """
    # Get Wikipedia links to individual companies.
    companies = get_company_links()

    # Print # of companies.
    nbr_companies = len(companies)
    print(f"Found {nbr_companies} companies")

    # Get company info for each company.
    records = []
    for i, company in enumerate(companies):
        print(f"[{i + 1}/{nbr_companies}] {company['name']}")

        company_data = get_company_info(company["url"])
        records.append(
            {"name": company["name"],
             "url": company["url"],
             **company_data
            }
        )

        time.sleep(0.5)  # be a good citizen

    # Create a dataframe from the company records.
    company_df = pd.DataFrame(records)
    company_df = company_df.drop_duplicates(subset="url")

    # Validate dataframe
    validate_not_empty(company_df, "scrape_companies")
    validate_columns(
        company_df,
        ["name", "headquarters", "founded", "website", "employees", "url"],
        "scrape_companies",
    )

    return company_df

"""
HTML parsing and record normalization utilities for Books to Scrape.
"""

from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from typing import List, Optional, Tuple, Dict, Any
from .schema import RawBookRecord, NormalizedBookRecord

RATING_MAP = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5
}


def extract_catalogue_book_urls(html_text: str, base_url: str) -> List[str]:
    """Extract all product page absolute URLs from a catalogue page."""
    soup = BeautifulSoup(html_text, "html.parser")
    book_links = []
    
    # Target book articles in catalogue
    articles = soup.find_all("article", class_="product_pod")
    for article in articles:
        h3 = article.find("h3")
        if h3 and h3.find("a"):
            rel_href = h3.find("a").get("href", "")
            abs_url = urljoin(base_url, rel_href)
            book_links.append(abs_url)
            
    return book_links


def extract_next_page_url(html_text: str, current_page_url: str) -> Optional[str]:
    """Find the absolute URL of the 'next' catalogue page, if present."""
    soup = BeautifulSoup(html_text, "html.parser")
    next_li = soup.find("li", class_="next")
    if next_li and next_li.find("a"):
        href = next_li.find("a").get("href", "")
        return urljoin(current_page_url, href)
    return None


def extract_raw_book_details(
    html_text: str,
    product_url: str,
    source_page: str,
    fetched_at: str
) -> Dict[str, Any]:
    """Extract raw string fields and provenance from a book detail HTML page."""
    soup = BeautifulSoup(html_text, "html.parser")
    main_div = soup.find("div", class_="product_main") or soup
    
    # 1. Title
    h1 = main_div.find("h1")
    title = h1.get_text(strip=True) if h1 else "Unknown Title"
    
    # 2. Price text
    price_elem = main_div.find("p", class_="price_color")
    price_text = price_elem.get_text(strip=True) if price_elem else "£0.00"
    
    # 3. Availability text
    avail_elem = main_div.find("p", class_="instock")
    avail_text = avail_elem.get_text(" ", strip=True) if avail_elem else "Unknown"

    
    # 4. Rating text
    rating_elem = main_div.find("p", class_=re.compile(r"star-rating\s*"))
    rating_text = "Three"
    if rating_elem:
        classes = rating_elem.get("class", [])
        for c in classes:
            if c.lower() in RATING_MAP:
                rating_text = c.capitalize()
                break
                
    # 5. Description
    desc_elem = soup.find("div", id="product_description")
    description = None
    if desc_elem:
        p = desc_elem.find_next_sibling("p")
        if p:
            text = p.get_text(strip=True)
            if text:
                description = text

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": avail_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }


def normalize_price(price_text: str) -> float:
    """Turn raw price string like '£51.77' into numeric float 51.77."""
    match = re.search(r"(\d+(?:\.\d+)?)", price_text)
    if match:
        return float(match.group(1))
    return 0.0


def normalize_availability(avail_text: str) -> int:
    """Extract numeric in-stock quantity from text like 'In stock (22 available)'."""
    match = re.search(r"\((\d+)\s*available\)", avail_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    if "in stock" in avail_text.lower():
        return 1
    return 0


def normalize_rating(rating_text: str) -> int:
    """Convert rating word (e.g. 'Three') to integer 1-5."""
    return RATING_MAP.get(rating_text.lower().strip(), 3)


def normalize_book(raw: Dict[str, Any]) -> NormalizedBookRecord:
    """Transform raw dictionary into a schema-validated NormalizedBookRecord."""
    price_gbp = normalize_price(raw.get("price_text", "0"))
    available_qty = normalize_availability(raw.get("availability_text", ""))
    rating_stars = normalize_rating(raw.get("rating_text", "Three"))
    
    return NormalizedBookRecord(
        title=raw["title"],
        product_url=raw["product_url"],
        price_text=raw["price_text"],
        price_gbp=price_gbp,
        availability_text=raw["availability_text"],
        available_quantity=available_qty,
        rating_text=raw["rating_text"],
        rating_stars=rating_stars,
        description=raw.get("description"),
        source_page=raw["source_page"],
        fetched_at=raw["fetched_at"]
    )

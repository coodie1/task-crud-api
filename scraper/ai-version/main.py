"""
AI-generated version of the Books to Scrape polite scraper (Bonus Stage AI Rematch quarantine).
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin
from typing import List, Dict, Any

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/coodie1/task-crud-api)"
BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"


def scrape_books_ai(max_pages: int = 3) -> List[Dict[str, Any]]:
    headers = {"User-Agent": USER_AGENT}
    current_page = BASE_URL
    book_urls = []
    pages_crawled = 0

    while current_page and pages_crawled < max_pages:
        res = requests.get(current_page, headers=headers, timeout=5)
        if res.status_code != 200:
            break
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.select("article.product_pod h3 a"):
            book_urls.append(urljoin(current_page, a["href"]))
        
        next_btn = soup.select_one("li.next a")
        current_page = urljoin(current_page, next_btn["href"]) if next_btn else None
        pages_crawled += 1
        time.sleep(0.5)

    unique_urls = list(set(book_urls))
    books = []

    for url in unique_urls:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code != 200:
                continue
            s = BeautifulSoup(r.text, "html.parser")
            title = s.select_one("h1").get_text(strip=True)
            price_text = s.select_one("p.price_color").get_text(strip=True)
            price_num = float(price_text.replace("£", "").strip())
            avail = s.select_one("p.instock").get_text(strip=True)
            desc = s.select_one("#product_description ~ p")
            desc_text = desc.get_text(strip=True) if desc else None

            books.append({
                "title": title,
                "product_url": url,
                "price_text": price_text,
                "price_gbp": price_num,
                "availability": avail,
                "description": desc_text
            })
            time.sleep(0.5)
        except Exception:
            continue

    with open("ai_books.json", "w", encoding="utf-8") as f:
        json.dump(books, f, indent=2)

    return books


if __name__ == "__main__":
    scrape_books_ai()

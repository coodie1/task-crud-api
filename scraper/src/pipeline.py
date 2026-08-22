"""
Polite Scraper Engine & Data Pipeline for Books to Scrape.
"""

import os
import time
import json
import hashlib
import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from urllib.parse import urljoin
from .parser import (
    extract_catalogue_book_urls,
    extract_next_page_url,
    extract_raw_book_details,
    normalize_book
)
from .schema import NormalizedBookRecord, RunReport, FailedRecord

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/coodie1/task-crud-api)"
REQUEST_TIMEOUT = 10
REQUEST_DELAY_SECONDS = 0.55  # Polite delay >= 500ms
START_URL = "https://books.toscrape.com/catalogue/page-1.html"


class PoliteScraperPipeline:
    """Manages polite fetching, caching, parsing, schema validation, and reporting."""

    def __init__(
        self,
        cache_dir: str = "cache",
        output_dir: str = "output",
        user_agent: str = USER_AGENT,
        request_delay: float = REQUEST_DELAY_SECONDS
    ):
        self.cache_dir = cache_dir
        self.output_dir = output_dir
        self.user_agent = user_agent
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Metrics
        self.pages_fetched_live = 0
        self.cache_hits = 0
        self.failed_pages = 0
        self.errors: List[Dict[str, Any]] = []

    def _get_cache_path(self, url: str) -> str:
        """Derive a stable cache filename for a URL."""
        if "page-" in url:
            # e.g. catalogue-page-1.html
            page_part = url.split("/")[-1].replace(".html", "")
            return os.path.join(self.cache_dir, f"catalogue-{page_part}.html")
        
        # Product detail page: use clean slug or hash
        slug = url.split("/")[-2] if len(url.split("/")) >= 2 else "item"
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
        return os.path.join(self.cache_dir, f"book_{slug}_{url_hash}.html")

    def fetch_url(self, url: str) -> Tuple[Optional[str], bool]:
        """
        Fetch HTML with caching, polite headers, delay, and retry rules.
        Returns (html_content, was_cache_hit).
        """
        cache_path = self._get_cache_path(url)
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.cache_hits += 1
            return content, True

        # Polite rate-limiting before live network call
        time.sleep(self.request_delay)

        # Fetch with single retry for 5xx/timeouts; do NOT retry 404/403
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                if response.status_code == 200:
                    html_text = response.text
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(html_text)
                    self.pages_fetched_live += 1
                    return html_text, False
                elif response.status_code in (403, 404):
                    # Do not retry client/permission errors
                    self.failed_pages += 1
                    self.errors.append({
                        "url": url,
                        "status_code": response.status_code,
                        "error": f"HTTP {response.status_code} received (polite no-retry rule)"
                    })
                    return None, False
                elif response.status_code >= 500:
                    if attempt < max_attempts:
                        time.sleep(1.0)
                        continue
                    self.failed_pages += 1
                    self.errors.append({
                        "url": url,
                        "status_code": response.status_code,
                        "error": f"Server error {response.status_code}"
                    })
                    return None, False
                else:
                    self.failed_pages += 1
                    return None, False

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_attempts:
                    time.sleep(1.0)
                    continue
                self.failed_pages += 1
                self.errors.append({
                    "url": url,
                    "status_code": 0,
                    "error": f"Network exception: {str(e)}"
                })
                return None, False

        return None, False

    def crawl_catalogue(self, start_url: str = START_URL, max_pages: int = 3) -> Tuple[List[str], int]:
        """Crawl the first N catalogue pages and collect unique book URLs."""
        current_url = start_url
        discovered_urls: List[str] = []
        pages_crawled = 0

        while current_url and pages_crawled < max_pages:
            html_text, is_cache = self.fetch_url(current_url)
            if not html_text:
                break
            
            pages_crawled += 1
            book_urls = extract_catalogue_book_urls(html_text, current_url)
            discovered_urls.extend(book_urls)

            # Follow next link
            current_url = extract_next_page_url(html_text, current_url)

        # Deduplicate while preserving discovery order
        unique_urls = list(dict.fromkeys(discovered_urls))
        return unique_urls, pages_crawled

    def run(
        self,
        max_catalogue_pages: int = 3,
        inject_broken_url: bool = False
    ) -> Tuple[List[Dict[str, Any]], RunReport]:
        """Execute the end-to-end polite scraping pipeline."""
        start_time_iso = datetime.now(timezone.utc).isoformat()
        t0 = time.time()

        # Step 1: Discover catalogue pages
        unique_book_urls, catalogue_pages_count = self.crawl_catalogue(START_URL, max_pages=max_catalogue_pages)
        total_discovered = len(unique_book_urls)

        # Stage 5 requirement: Test handling of an intentionally broken URL
        if inject_broken_url:
            unique_book_urls.append("https://books.toscrape.com/catalogue/non_existent_book_9999/index.html")

        # Step 2: Visit each book page and extract raw details
        valid_records: List[NormalizedBookRecord] = []
        invalid_records: List[Dict[str, Any]] = []

        for idx, book_url in enumerate(unique_book_urls):
            html_text, is_cache = self.fetch_url(book_url)
            if not html_text:
                # Broken / skipped page handled gracefully
                continue

            fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            # Determine source page based on index
            source_page_num = (idx // 20) + 1
            source_page = f"https://books.toscrape.com/catalogue/page-{source_page_num}.html"

            raw_dict = extract_raw_book_details(html_text, book_url, source_page, fetched_at)

            # Step 3: Normalize and Validate with Pydantic Schema
            try:
                norm_record = normalize_book(raw_dict)
                valid_records.append(norm_record)
            except Exception as val_err:
                invalid_records.append({
                    "product_url": book_url,
                    "error": str(val_err),
                    "raw_data": raw_dict
                })

        # Step 4: Write Idempotent Storage Outputs
        books_output_path = os.path.join(self.output_dir, "books.json")
        errors_output_path = os.path.join(self.output_dir, "errors.json")
        report_output_path = os.path.join(self.output_dir, "run-report.json")

        # Deduplicate valid records by canonical product_url
        seen_urls = set()
        deduped_records = []
        for r in valid_records:
            if r.product_url not in seen_urls:
                seen_urls.add(r.product_url)
                deduped_records.append(r.model_dump())

        with open(books_output_path, "w", encoding="utf-8") as f:
            json.dump(deduped_records, f, indent=2, ensure_ascii=False)

        with open(errors_output_path, "w", encoding="utf-8") as f:
            json.dump(invalid_records + self.errors, f, indent=2)

        # Step 5: Generate Run Report
        duration = round(time.time() - t0, 3)
        end_time_iso = datetime.now(timezone.utc).isoformat()

        report = RunReport(
            start_time=start_time_iso,
            end_time=end_time_iso,
            duration_seconds=duration,
            catalogue_pages_discovered=catalogue_pages_count,
            books_discovered=total_discovered,
            books_unique=len(deduped_records),
            pages_fetched_live=self.pages_fetched_live,
            cache_hits=self.cache_hits,
            valid_records=len(deduped_records),
            invalid_records=len(invalid_records),
            failed_pages=self.failed_pages,
            output_file=books_output_path,
            status="SUCCESS" if len(deduped_records) == 60 else "COMPLETED_WITH_WARNINGS"
        )

        with open(report_output_path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)

        return deduped_records, report

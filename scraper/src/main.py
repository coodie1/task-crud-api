"""
Entry point for the Polite Scraper.
Usage: python src/main.py [--break-test]
"""

import sys
import os
import argparse

# Ensure parent directory is in path when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import PoliteScraperPipeline


def main():
    parser = argparse.ArgumentParser(description="Polite Scraper for Books to Scrape")
    parser.add_argument("--break-test", action="store_true", help="Inject a fake URL to test error survival")
    parser.add_argument("--pages", type=int, default=3, help="Number of catalogue pages to scrape (default: 3)")
    args = parser.parse_args()

    print("=" * 65)
    print("  The Polite Scraper — Books to Scrape Pipeline")
    print("=" * 65)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_dir = os.path.join(base_dir, "cache")
    output_dir = os.path.join(base_dir, "output")

    pipeline = PoliteScraperPipeline(cache_dir=cache_dir, output_dir=output_dir)
    books, report = pipeline.run(max_catalogue_pages=args.pages, inject_broken_url=args.break_test)

    print("\n--- Pipeline Execution Summary ---")
    print(f"  Catalogue Pages Crawled : {report.catalogue_pages_discovered}")
    print(f"  Total Books Discovered  : {report.books_discovered}")
    print(f"  Unique Valid Records    : {report.valid_records}")
    print(f"  Live Pages Fetched      : {report.pages_fetched_live}")
    print(f"  Local Cache Hits        : {report.cache_hits}")
    print(f"  Failed Pages Handled    : {report.failed_pages}")
    print(f"  Execution Duration      : {report.duration_seconds}s")
    print(f"  Output Saved To         : {report.output_file}")
    print(f"  Overall Status          : {report.status}")
    print("=" * 65)


if __name__ == "__main__":
    main()

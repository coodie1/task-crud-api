"""
Unit tests for the HTML parser and normalizer.
Run with: pytest tests/
"""

import pytest
import sys
import os

# Ensure scraper package is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parser import (
    normalize_price,
    normalize_availability,
    normalize_rating,
    extract_catalogue_book_urls,
    extract_raw_book_details,
    normalize_book
)
from src.schema import NormalizedBookRecord


SAMPLE_CATALOGUE_HTML = """
<ol class="row">
    <li class="col-xs-6 col-sm-4 col-md-3 col-lg-3">
        <article class="product_pod">
            <div class="image_container">
                <a href="a-light-in-the-attic_1000/index.html">
                    <img src="media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg" alt="A Light in the Attic" class="thumbnail">
                </a>
            </div>
            <p class="star-rating Three"></p>
            <h3><a href="a-light-in-the-attic_1000/index.html" title="A Light in the Attic">A Light in the ...</a></h3>
            <div class="product_price">
                <p class="price_color">£51.77</p>
                <p class="instock availability"><i class="icon-ok"></i> In stock</p>
            </div>
        </article>
    </li>
    <li class="col-xs-6 col-sm-4 col-md-3 col-lg-3">
        <article class="product_pod">
            <h3><a href="tipping-the-velvet_999/index.html" title="Tipping the Velvet">Tipping the Velvet</a></h3>
            <div class="product_price">
                <p class="price_color">£53.74</p>
            </div>
        </article>
    </li>
</ol>
"""


SAMPLE_BOOK_HTML_WITH_DESC = """
<div class="product_main">
    <h1>A Light in the Attic</h1>
    <p class="price_color">£51.77</p>
    <p class="instock availability"><i class="icon-ok"></i> In stock (22 available)</p>
    <p class="star-rating Three"></p>
</div>
<div id="product_description" class="sub-header">
    <h2>Product Description</h2>
</div>
<p>It's hard to imagine a world without A Light in the Attic. This classic collection of poetry has delighted readers for generations.</p>
"""

SAMPLE_BOOK_HTML_NO_DESC = """
<div class="product_main">
    <h1>Book Without Description</h1>
    <p class="price_color">£19.99</p>
    <p class="instock availability">In stock (5 available)</p>
    <p class="star-rating Five"></p>
</div>
"""

MALFORMED_HTML = """
<div>
    <h1>Broken Book</h1>
    <p class="price_color">Invalid Price String</p>
</div>
"""


def test_1_price_normalization():
    """Verify price string parsing to floating point numbers."""
    assert normalize_price("£51.77") == 51.77
    assert normalize_price("£0.99") == 0.99
    assert normalize_price("12.50") == 12.50
    assert normalize_price("Free") == 0.0


def test_2_relative_to_absolute_urls():
    """Verify relative catalogue URLs are properly resolved against base URL."""
    base = "https://books.toscrape.com/catalogue/page-1.html"
    urls = extract_catalogue_book_urls(SAMPLE_CATALOGUE_HTML, base)
    assert len(urls) == 2
    assert urls[0] == "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    assert urls[1] == "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html"


def test_3_missing_description_handling():
    """Ensure books with no description store None/null without crashing."""
    raw = extract_raw_book_details(
        SAMPLE_BOOK_HTML_NO_DESC,
        "https://books.toscrape.com/catalogue/book-no-desc/index.html",
        "https://books.toscrape.com/catalogue/page-1.html",
        "2026-08-21T21:00:00Z"
    )
    assert raw["description"] is None
    assert raw["title"] == "Book Without Description"
    
    norm = normalize_book(raw)
    assert norm.description is None
    assert norm.price_gbp == 19.99
    assert norm.rating_stars == 5


def test_4_duplicate_url_deduplication():
    """Ensure duplicate book URLs are filtered out."""
    base = "https://books.toscrape.com/catalogue/page-1.html"
    urls = extract_catalogue_book_urls(SAMPLE_CATALOGUE_HTML, base)
    # Duplicate
    duped = urls + urls
    unique = list(dict.fromkeys(duped))
    assert len(unique) == 2


def test_5_malformed_html_fixture_resilience():
    """Verify parser does not crash on malformed or incomplete HTML."""
    raw = extract_raw_book_details(
        MALFORMED_HTML,
        "https://books.toscrape.com/catalogue/broken/index.html",
        "https://books.toscrape.com/catalogue/page-1.html",
        "2026-08-21T21:00:00Z"
    )
    assert raw["title"] == "Broken Book"
    assert raw["price_text"] == "Invalid Price String"
    
    norm = normalize_book(raw)
    assert norm.price_gbp == 0.0
    assert norm.available_quantity == 0

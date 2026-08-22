"""
Schema definitions for raw and validated normalized book records.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any


class RawBookRecord(BaseModel):
    """Raw scraped record keeping original strings and provenance."""
    title: str
    product_url: str
    price_text: str
    availability_text: str
    rating_text: str
    description: Optional[str] = None
    source_page: str
    fetched_at: str


class NormalizedBookRecord(BaseModel):
    """Clean, schema-validated record ready for storage and downstream processing."""
    title: str = Field(..., min_length=1, description="Full book title")
    product_url: str = Field(..., description="Canonical absolute URL of product page")
    price_text: str = Field(..., description="Original raw price text (e.g. £51.77)")
    price_gbp: float = Field(..., ge=0.0, description="Cleaned numerical price in GBP")
    availability_text: str = Field(..., description="Original raw availability text")
    available_quantity: int = Field(default=0, ge=0, description="Parsed in-stock quantity")
    rating_text: str = Field(..., description="Original raw star rating word (e.g. Three)")
    rating_stars: int = Field(..., ge=1, le=5, description="Numerical star rating between 1 and 5")
    description: Optional[str] = Field(default=None, description="Book description paragraph or null")
    source_page: str = Field(..., description="Provenance catalogue page URL")
    fetched_at: str = Field(..., description="ISO 8601 UTC timestamp of fetch")


class FailedRecord(BaseModel):
    """Record that failed schema validation."""
    product_url: str
    error: str
    raw_data: Dict[str, Any]


class RunReport(BaseModel):
    """Run metrics and status report."""
    start_time: str
    end_time: str
    duration_seconds: float
    catalogue_pages_discovered: int
    books_discovered: int
    books_unique: int
    pages_fetched_live: int
    cache_hits: int
    valid_records: int
    invalid_records: int
    failed_pages: int
    output_file: str
    status: str

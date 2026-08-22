# The Polite Scraper (Books to Scrape)

A polite, resilient, and schema-validated scraping pipeline that extracts 60 books across the first 3 catalogue pages of **Books to Scrape** without ever overwhelming the server.

---

## 🎯 Target Classification & Scope

- **Target Site**: [https://books.toscrape.com](https://books.toscrape.com)
- **Why this target**: *Books to Scrape* is an explicit, publicly provided testing sandbox created specifically for developers and students to practice web scraping safely without legal or operational concerns.
- **Scope**: Exactly the first **3 catalogue pages** (60 total book items).
- **Data Collected**: Book title, product page canonical URL, price text, cleaned numeric price (GBP), availability text, in-stock quantity, star rating, description, source catalogue page (provenance), and fetch timestamp.
- **Why appropriate**: Scraping 60 items with a polite 550ms delay and local disk caching puts negligible load on the sandbox.
- **robots.txt check result**: A request to `https://books.toscrape.com/robots.txt` returned `404 Not Found` (no robots file found on the sandbox domain).
- **Commitment**: *"I will not reuse this code on another site without checking its rules and terms first."*

---

## 🤝 Politeness & Etiquette Rules

1. **Honest User-Agent**: Every HTTP request sends an identifying header naming the project and owner:
   ```text
   User-Agent: FlyRankInternship-A9/1.0 (+https://github.com/coodie1/task-crud-api)
   ```
2. **Polite Delay**: Enforces a `>= 500ms` delay (550ms) between live requests to the website.
3. **Local File Caching**: Every downloaded HTML page is saved to `cache/` (git-ignored). Repeated runs hit the local cache with 0ms network latency and zero server load.
4. **Strict Timeout**: Every request sets a `10s` timeout so the program never hangs indefinitely.
5. **No-Retry on 404/403**: Retries 5xx server errors once with backoff, but never retries 404 (non-existent) or 403 (forbidden).
6. **Graceful Error Survival**: An unparseable or broken book URL is logged to `output/errors.json` and skipped; 59 good records survive 1 bad record.

---

## 🚀 Quickstart & How to Run

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run the Polite Scraper
```bash
# Run the pipeline (outputs to output/books.json and output/run-report.json)
python src/main.py

# Test failure resilience with an intentionally injected broken URL
python src/main.py --break-test
```

### Run Unit Tests (5 Parser & Normalizer Tests)
```bash
pytest tests/
```

---

## 📋 Data Schema (Pydantic)

```python
class NormalizedBookRecord(BaseModel):
    title: str               # Book title
    product_url: str         # Canonical absolute URL
    price_text: str          # Raw string: "£51.77"
    price_gbp: float         # Cleaned float: 51.77
    availability_text: str   # Raw string: "In stock (22 available)"
    available_quantity: int  # Parsed quantity: 22
    rating_text: str         # Raw string: "Three"
    rating_stars: int        # Numeric integer: 3
    description: Optional[str] # Text or null
    source_page: str         # Provenance URL
    fetched_at: str          # ISO 8601 UTC timestamp
```

---

## 📊 Live Run Report Proof (`output/run-report.json`)

```json
{
  "start_time": "2026-08-21T18:45:15.059700+00:00",
  "end_time": "2026-08-21T18:45:18.201651+00:00",
  "duration_seconds": 3.142,
  "catalogue_pages_discovered": 3,
  "books_discovered": 60,
  "books_unique": 60,
  "pages_fetched_live": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1,
  "output_file": "output/books.json",
  "status": "SUCCESS"
}
```

---

## 💡 Why No Browser Was Needed

The target website is completely server-rendered HTML. All book titles, prices, ratings, and descriptions are already embedded in the raw HTTP response sent by the web server. Using a headless browser (like Chromium/Playwright) would require ~150MB of RAM and 10x more CPU cycles with zero benefit. Fast HTTP requests + Beautiful Soup parsing is the correct, lean architecture.

---

## ⚖️ Ethics Note & Honest Limitation

- **Ethics Note**: Always use an official REST/GraphQL API when one exists. Never bypass authentication, paywalls, or rate limits. Scrape only the data you need, cache aggressively, and respect site owners' resources.
- **Honest Limitation**: This scraper relies on CSS selectors and DOM structure (`div.product_main`, `p.price_color`). If the website redesigns its HTML layout or migrates to a client-side JavaScript Single Page App (SPA), the selectors will need to be updated.

---

## 🤖 Bonus Stage: AI vs Me (Scraper Rematch)

### The Prompt
> "Build a polite Python scraper using BeautifulSoup and Requests for Books to Scrape. Crawl the first 3 catalogue pages to discover 60 books. Visit each detail page to extract title, price, availability, star rating, and description. Implement local HTML caching, 500ms request delay, user-agent headers, Pydantic schema validation, and write output to books.json and run-report.json."

### 3 Concrete Differences Found

1. **Schema Validation & Error Segregation**:
   - *AI Version*: Collected raw untyped dictionaries into a list and saved directly without schema validation or error quarantine.
   - *Hand-built Version*: Enforced strict Pydantic model validation (`NormalizedBookRecord`), routing broken records to `errors.json`.

2. **Caching Architecture & Idempotency**:
   - *AI Version*: Did not implement disk caching — every rerun made 60+ live network requests.
   - *Hand-built Version*: Implemented deterministic MDN/slug caching in `cache/`, reducing repeat run time from ~60s to ~3s.

3. **Polite Retry vs Fault Tolerance**:
   - *AI Version*: Did not distinguish between 404 (missing) and 5xx (server error), blindly retrying or skipping with bare `except:`.
   - *Hand-built Version*: Implemented specific retry logic for 5xx/timeouts, non-retry for 404/403, and generated a full `RunReport` audit receipt.

---

## 👤 Author
**coodie1** (`umairarif946@gmail.com`)

# Hotel Policy Scraper

A Python webscraper that collects tax, fee, and policy information from hotels across resort towns.

## Features

- Scrapes official hotel websites for policy information
- Falls back to Booking.com when official site has no policy page
- Extracts taxes, fees, extra person policies, and damage deposits
- Rate-limited with randomized delays to be respectful to servers
- Exports to JSON (individual and consolidated) and CSV formats

## Installation

```bash
cd scraper
pip install -r requirements.txt
```

## Usage

### Full Scrape

Run the scraper for all configured locations:

```bash
python -m src.main
```

### Filter by Location

Scrape only a specific country:

```bash
python -m src.main --country "Canada"
```

Scrape only a specific town:

```bash
python -m src.main --town "Banff" --country "Canada"
```

### Dry Run

See what would be scraped without actually making requests:

```bash
python -m src.main --dry-run
```

### Export Only

Regenerate exports from existing JSON data:

```bash
python -m src.main --export-only
```

### Verbose Logging

Enable detailed debug logging:

```bash
python -m src.main --verbose
```

## Data Format

Each hotel is saved as a JSON file with the following structure:

```json
{
  "id": "canada-banff-fairmont-banff-springs",
  "name": "Fairmont Banff Springs",
  "town": "Banff",
  "region": "Alberta",
  "country": "Canada",
  "marketSegment": "Luxury",
  "tripadvisorRank": 1,
  "coordinates": { "lat": 51.1679, "lng": -115.5595 },
  "sources": {
    "officialWebsite": "https://www.fairmont.com/banff-springs/",
    "policyPage": "https://www.fairmont.com/banff-springs/hotel-policies/",
    "bookingCom": null,
    "dataSource": "official"
  },
  "taxes": [...],
  "fees": [...],
  "extraPersonPolicy": {...},
  "damageDeposit": {...},
  "promotions": [],
  "scrapedAt": "2024-12-19T10:30:00Z",
  "scrapingNotes": null
}
```

## Adding Hotels

Hotels are loaded from curated data files in `data/curated/{country}/{town}.json`.

Example curated data format:

```json
{
  "hotels": [
    {
      "name": "Fairmont Banff Springs",
      "rank": 1,
      "website": "https://www.fairmont.com/banff-springs/",
      "market_segment": "Luxury",
      "coordinates": { "lat": 51.1679, "lng": -115.5595 }
    }
  ]
}
```

## Output Files

- `data/hotels/{country}/{town}/{hotel-slug}.json` - Individual hotel files
- `data/all-hotels.json` - Consolidated JSON
- `data/exports/hotels-all.csv` - All hotels as CSV
- `data/exports/hotels-{country}.csv` - Hotels by country
- `frontend/src/data/hotels.json` - Copy for frontend

## Configuration

Edit `config/scraping.yaml` to adjust:
- Rate limiting parameters
- Policy page URL patterns
- Market segment classification keywords

Edit `config/locations.yaml` to add or modify target towns.

## Logs

Scraping logs are saved to `logs/` with timestamps. A summary report is generated at `logs/scraping_report.txt`.

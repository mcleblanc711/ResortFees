# Hotel Policy Explorer

**[View Live Dashboard](https://mcleblanc711.github.io/ResortFees/)**

A webscraper and visualization tool that collects tax, fee, and policy information from hotels across resort towns in Canada, the United States, Europe, and Australia.

**Current data:** 209 hotels across 21 resort towns in Canada, USA, and Australia.

## Overview

This project consists of two main components:

1. **Python Scraper** - Collects hotel policy data from official websites and Booking.com
2. **React Frontend** - Displays the data with filtering, searching, and 5 visual themes

## Features

### Scraper
- Scrapes official hotel websites for policy information
- Falls back to Booking.com when official site lacks policy data
- Extracts taxes, fees, extra person policies, and damage deposits
- Rate-limited with randomized delays for respectful scraping
- Exports to JSON and CSV formats

### Frontend
- 5 distinct visual themes:
  - **Dark** - Charcoal with electric blue accents
  - **Frutiger Aero** - Glossy glassmorphism with sky blues
  - **Flat** - Bold colors, no shadows, geometric shapes
  - **Cyberpunk** - Neon purples and pinks with glitch effects
  - **Modern** - Warm neutrals with elegant typography
- Filter by country, town, and market segment
- Search hotels by name
- Summary statistics panel
- Responsive design

## Quick Start

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

The development server will start at http://localhost:5173

### Production Build

```bash
cd frontend
npm run build
npm run preview
```

### Running the Scraper

```bash
cd scraper
pip install -r requirements.txt
python -m src.main --verbose
```

## Project Structure

```
hotel-policy-scraper/
├── scraper/
│   ├── src/
│   │   ├── main.py              # Entry point
│   │   ├── hotel_finder.py      # Hotel discovery
│   │   ├── policy_scraper.py    # Core scraping logic
│   │   ├── booking_fallback.py  # Booking.com fallback
│   │   ├── data_parser.py       # Data transformation
│   │   ├── exporters.py         # JSON/CSV export
│   │   └── utils/               # Utilities
│   ├── config/
│   │   ├── locations.yaml       # Target locations
│   │   └── scraping.yaml        # Scraping config
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/          # React components
│   │   ├── hooks/               # Custom hooks
│   │   ├── themes/              # CSS theme files
│   │   └── data/                # Hotel data JSON
│   ├── package.json
│   └── vite.config.js
│
├── data/
│   ├── hotels/                  # Individual hotel JSON
│   ├── all-hotels.json          # Consolidated data
│   └── exports/                 # CSV exports
│
├── .github/workflows/
│   └── deploy.yml               # GitHub Pages deployment
│
└── README.md
```

## Target Locations

### Canada
- Banff, Canmore, Jasper (Alberta)
- Whistler, Revelstoke (British Columbia)
- Mont-Tremblant (Quebec)
- Blue Mountain (Ontario)

### United States
- Aspen, Vail, Telluride (Colorado)
- Park City (Utah)
- Jackson Hole (Wyoming)
- Lake Tahoe, Mammoth Lakes (California)
- Stowe (Vermont)
- Big Sky (Montana)
- Sun Valley (Idaho)

### Europe
- Zermatt, St. Moritz, Verbier (Switzerland)
- Chamonix, Courchevel (France)
- Kitzbühel (Austria)

### Australia
- Thredbo, Perisher (New South Wales)
- Falls Creek, Mount Buller (Victoria)

## Data Schema

Each hotel entry includes:

- Basic info (name, location, market segment, TripAdvisor rank)
- Source URLs (official website, policy page, Booking.com)
- Taxes (name, amount, basis)
- Fees (name, amount, basis, what's included)
- Extra person policy (children free age, charges)
- Damage deposit information
- Promotions (when available)

## Deployment

The frontend automatically deploys to GitHub Pages when changes are pushed to the main branch. The GitHub Actions workflow handles the build and deployment.

## License

MIT License

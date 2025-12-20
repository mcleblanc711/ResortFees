# Hotel Policy Webscraper Project

## Project Overview

Build a webscraper that collects tax, fee, and policy information from hotels across resort towns in Canada, the United States, Europe, and Australia. The scraped data will be presented on a GitHub Pages site with multiple visual themes and interactive filtering.

---

## Target Locations

### Canada
- Banff, Alberta
- Canmore, Alberta
- Jasper, Alberta
- Whistler, British Columbia
- Revelstoke, British Columbia
- Mont-Tremblant, Quebec
- Blue Mountain, Ontario

### United States
- Aspen, Colorado
- Vail, Colorado
- Park City, Utah
- Jackson Hole, Wyoming
- Lake Tahoe, California/Nevada
- Mammoth Lakes, California
- Stowe, Vermont
- Telluride, Colorado
- Big Sky, Montana
- Sun Valley, Idaho

### Europe
- Zermatt, Switzerland
- Chamonix, France
- St. Moritz, Switzerland
- Courchevel, France
- Kitzbühel, Austria
- Verbier, Switzerland

### Australia
- Thredbo, New South Wales
- Falls Creek, Victoria
- Perisher, New South Wales
- Mount Buller, Victoria

---

## Hotel Selection Criteria

- **Quantity**: Top 30 hotels per town
- **Source**: TripAdvisor rankings as primary source
- **Verification**: Cross-reference with Google Maps/Places to confirm hotel exists and is operational
- **Market Segments** (classify each hotel):
  - Luxury
  - Upscale
  - Upper-Midscale
  - Midscale
  - Economy

---

## Data to Collect

### 1. Taxes & Fees (capture all listed)
Examples of what to look for:
- Tourism/destination levies
- Resort fees
- Service charges
- Parking fees (self-park vs valet)
- Pet fees
- Cleaning fees
- Early check-in / late check-out fees
- Cancellation fees
- Amenity fees
- Environmental fees
- Any other itemized charges

For each fee, capture:
- Fee name
- Amount (fixed or percentage)
- Whether it's per night, per stay, or per person
- Any conditions or exemptions

### 2. Extra Person Charges
- **Children policy**: Free threshold (e.g., "children under 12 stay free") vs. charge amount
- **Extra adult charge**: Amount per night/stay
- **Maximum occupancy notes** if available

### 3. Damage Deposit Policy
- Deposit amount
- Timing: Per stay vs. per night
- Method: Credit card hold, cash, or pre-authorization
- Refund timeline if mentioned

### 4. Promotions
- **Only from dedicated promotion/offers/deals pages** — do NOT scrape booking engines
- Promotion name/title
- Brief description
- Validity period if listed
- Any promo codes mentioned

### 5. Source Links
- **Required**: Include a direct URL to the policy page for every hotel
- If using Booking.com as fallback, note this in the data

---

## Scraping Priority

1. **Primary**: Hotel's official website → look for pages titled:
   - "Policies"
   - "Terms & Conditions"
   - "Hotel Policies"
   - "Guest Information"
   - "FAQ"
   - "Rates" (sometimes fees are listed here)

2. **Fallback**: Booking.com listing for that specific hotel
   - Use if official website has no policy information
   - Flag in the data that source is Booking.com

3. **Do NOT scrape**:
   - Booking engines or reservation systems
   - Dynamic pricing pages
   - Login-required content

---

## Data Output Format

Generate all three formats:

### 1. JSON (per hotel)
```
/data/hotels/{country}/{town}/{hotel-slug}.json
```

### 2. Consolidated JSON
```
/data/all-hotels.json
```

### 3. CSV
```
/data/exports/hotels-all.csv
/data/exports/hotels-by-country.csv (one per country)
```

### JSON Schema (per hotel)
```json
{
  "id": "unique-identifier",
  "name": "Hotel Name",
  "town": "Banff",
  "region": "Alberta",
  "country": "Canada",
  "marketSegment": "Luxury",
  "tripadvisorRank": 3,
  "coordinates": {
    "lat": 51.1784,
    "lng": -115.5708
  },
  "sources": {
    "officialWebsite": "https://...",
    "policyPage": "https://...",
    "bookingCom": "https://...",
    "dataSource": "official" | "booking.com"
  },
  "taxes": [
    {
      "name": "Tourism Levy",
      "amount": "4%",
      "basis": "per night",
      "notes": "Applied to room rate"
    }
  ],
  "fees": [
    {
      "name": "Resort Fee",
      "amount": "$35.00",
      "basis": "per night",
      "includes": ["WiFi", "Pool Access", "Fitness Center"],
      "notes": "Mandatory"
    }
  ],
  "extraPersonPolicy": {
    "childrenFreeAge": 12,
    "childCharge": {
      "amount": "$25.00",
      "basis": "per night"
    },
    "adultCharge": {
      "amount": "$40.00",
      "basis": "per night"
    },
    "maxOccupancy": "Varies by room type",
    "notes": "Cribs available free of charge"
  },
  "damageDeposit": {
    "amount": "$250.00",
    "basis": "per stay",
    "method": "Credit card pre-authorization",
    "refundTimeline": "Released within 7 business days",
    "notes": ""
  },
  "promotions": [
    {
      "name": "Stay 3, Pay 2",
      "description": "Book three nights and get the third night free",
      "validFrom": "2024-01-01",
      "validTo": "2024-03-31",
      "promoCode": "WINTER24",
      "sourceUrl": "https://..."
    }
  ],
  "scrapedAt": "2024-12-19T10:30:00Z",
  "scrapingNotes": "Any issues or observations during scraping"
}
```

---

## Frontend: GitHub Pages React App

### Architecture
- Lightweight React single-page application
- Static build deployed to GitHub Pages
- Data loaded from the consolidated JSON file
- No backend required

### Core Features

#### Theme Selector (top of page)
Implement 5 distinct themes, switchable via a dropdown or toggle buttons:

1. **Dark Theme**
   - Deep charcoal/near-black backgrounds (#0a0a0a to #1a1a1a)
   - High contrast text (off-white, not pure white)
   - Accent color: electric blue or amber
   - Subtle glow effects on interactive elements
   - Typography: Clean geometric sans-serif (e.g., Outfit, Syne, or Manrope)

2. **Frutiger Aero Theme**
   - Glossy, translucent surfaces with glass-morphism effects
   - Soft gradients: sky blues, aqua greens, gentle whites
   - Bubble-like UI elements with subtle reflections
   - Light drop shadows creating depth
   - Rounded corners everywhere
   - Typography: Friendly, rounded sans-serif (e.g., Nunito, Quicksand)
   - Nature imagery or abstract bubble/water motifs as accents

3. **Flat Design Theme**
   - Bold, solid colors with no gradients or shadows
   - Strong primary palette: vibrant blue, coral, teal
   - Clean geometric shapes
   - Generous whitespace
   - Typography: Bold headlines, minimal decoration (e.g., DM Sans, Work Sans)
   - Icon-forward UI with simple line icons

4. **Cyberpunk Theme**
   - Dark purple/deep blue base (#0d0221, #1a0a2e)
   - Neon accent colors: hot pink (#ff00ff), cyan (#00ffff), electric yellow
   - Glitch effects, scan lines, or CRT-style distortions
   - Angular, aggressive shapes
   - Monospace or tech-style typography (e.g., Share Tech Mono, Orbitron)
   - Optional: subtle animated elements (flickering, pulsing glows)

5. **Modern Theme**
   - Warm neutrals: soft beige, warm gray, cream
   - Subtle accent: terracotta, sage green, or muted gold
   - Elegant serif headings paired with clean sans-serif body
   - Refined spacing and typography hierarchy
   - Minimal but intentional shadows
   - Editorial/magazine-inspired layout
   - Typography: Serif for headings (e.g., Playfair Display, Fraunces), sans for body (e.g., Plus Jakarta Sans)

### Filtering & Interaction

#### Filter Controls
- **By Location**: 
  - Dropdown/multi-select for Country
  - Dropdown/multi-select for Town (filters based on country selection)
- **By Market Segment**: 
  - Checkbox or pill toggles for Luxury / Upscale / Upper-Midscale / Midscale / Economy
- **Search**: 
  - Text search across hotel names
- **Clear Filters** button

#### Data Display
- Card-based layout for hotel listings
- Each card shows:
  - Hotel name
  - Town, Country
  - Market segment badge
  - Summary of fees count (e.g., "4 taxes & fees")
  - TripAdvisor rank
- Click card to expand/modal showing full details:
  - All taxes with amounts
  - All fees with amounts and notes
  - Extra person policy breakdown
  - Damage deposit details
  - Current promotions
  - **Direct link to source policy page** (prominently displayed)

#### Summary Statistics (top of page or sidebar)
- Total hotels scraped
- Breakdown by country
- Breakdown by market segment
- Average resort fee by segment
- Most common fee types

### Technical Requirements
- React 18+ with hooks
- CSS-in-JS or CSS Modules for theme management
- CSS custom properties (variables) for easy theme switching
- Responsive design (mobile-friendly)
- Accessible (ARIA labels, keyboard navigation, color contrast)
- Fast initial load (lazy load hotel details)

---

## Project Structure

```
hotel-policy-scraper/
├── scraper/
│   ├── src/
│   │   ├── main.py              # Entry point
│   │   ├── hotel_finder.py      # TripAdvisor + Google Maps lookup
│   │   ├── policy_scraper.py    # Core scraping logic
│   │   ├── booking_fallback.py  # Booking.com fallback scraper
│   │   ├── data_parser.py       # Extract structured data from pages
│   │   ├── exporters.py         # JSON/CSV output
│   │   └── utils/
│   │       ├── rate_limiter.py
│   │       ├── user_agents.py
│   │       └── logging.py
│   ├── config/
│   │   ├── locations.yaml       # Town definitions
│   │   └── scraping.yaml        # Scraping parameters
│   ├── requirements.txt
│   └── README.md
│
├── data/
│   ├── hotels/
│   │   ├── canada/
│   │   │   ├── banff/
│   │   │   └── ...
│   │   ├── usa/
│   │   ├── europe/
│   │   └── australia/
│   ├── all-hotels.json
│   └── exports/
│       ├── hotels-all.csv
│       └── ...
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ThemeSelector.jsx
│   │   │   ├── FilterPanel.jsx
│   │   │   ├── HotelCard.jsx
│   │   │   ├── HotelDetail.jsx
│   │   │   ├── StatsPanel.jsx
│   │   │   └── Layout.jsx
│   │   ├── themes/
│   │   │   ├── dark.css
│   │   │   ├── frutiger-aero.css
│   │   │   ├── flat.css
│   │   │   ├── cyberpunk.css
│   │   │   └── modern.css
│   │   ├── hooks/
│   │   │   ├── useTheme.js
│   │   │   └── useFilters.js
│   │   └── data/
│   │       └── hotels.json      # Copied from /data at build time
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
├── .github/
│   └── workflows/
│       └── deploy.yml           # GitHub Pages deployment
│
└── README.md
```

---

## Scraper Implementation Notes

### Rate Limiting
- Minimum 2-3 second delay between requests
- Randomize delays to appear more human
- Respect robots.txt where possible
- Implement exponential backoff on failures

### User Agent Rotation
- Rotate through realistic browser user agents
- Include common browser headers

### Error Handling
- Log all failures with URL and error type
- Continue processing other hotels if one fails
- Generate a scraping report at the end with success/failure counts

### Market Segment Classification
Use these heuristics if not explicitly stated:
- **Luxury**: 5-star, "luxury" in name/description, rates typically $400+/night
- **Upscale**: 4-star, boutique hotels, rates typically $200-400/night
- **Upper-Midscale**: 3.5-star, quality chains, rates typically $150-250/night
- **Midscale**: 3-star, standard chains, rates typically $100-175/night
- **Economy**: 2-star and below, budget options, rates typically under $100/night

### Data Validation
- Ensure all required fields are present
- Validate URLs are properly formatted
- Flag suspicious data (e.g., unusually high fees)
- Normalize currency symbols and formats

---

## Deliverables Checklist

- [ ] Working Python scraper with all modules
- [ ] Configuration files for locations and scraping parameters
- [ ] Complete dataset in JSON format (per-hotel and consolidated)
- [ ] CSV exports
- [ ] React frontend with all 5 themes implemented
- [ ] Theme switcher working correctly
- [ ] Filtering by location and market segment working
- [ ] Hotel detail view with policy link
- [ ] Summary statistics displayed
- [ ] GitHub Actions workflow for Pages deployment
- [ ] README with setup and usage instructions
- [ ] Scraping report/log documenting any issues

---

## Additional Notes

- This is a one-time scrape, but structure the code cleanly enough that it could be re-run if needed
- Prioritize data accuracy over speed — better to scrape fewer hotels correctly than many with errors
- If a hotel has no findable policy information from either source, include it in the dataset but mark the policy fields as null with a note explaining the situation
- For the frontend, ensure the policy source link is prominent and clickable — this is critical for users who want to verify the information

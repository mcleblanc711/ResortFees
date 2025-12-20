# CLAUDE.md - Hotel Policy Scraper Project

> This file provides persistent context for Claude Code working on this repository.

## Project Purpose

A webscraper that collects tax, fee, and policy information from hotels across resort towns in Canada, the US, Europe, and Australia. Data is presented on a GitHub Pages React app with multiple visual themes and filtering capabilities.

**Primary stakeholder use case**: Revenue management analysis for mountain resort hotels — comparing policies, fees, and charges across competitive markets.

---

## Critical Requirements (Never Violate)

1. **Every hotel entry MUST include a source link** to the policy page. This is non-negotiable.

2. **Never scrape booking engines or reservation systems.** Only scrape static policy/info pages and dedicated promotion pages.

3. **Data schema is a contract.** Both scraper and frontend depend on the JSON schema defined in the main prompt. Any schema changes must be reflected in both.

4. **Rate limiting is mandatory.** Minimum 2-3 seconds between requests, randomized. No exceptions.

5. **Policy source must be flagged.** Always indicate whether data came from the official website or Booking.com fallback.

---

## Architecture Decisions

### Scraper (Python)
- **Language**: Python 3.11+
- **HTTP**: `httpx` for async requests (preferred) or `requests`
- **Parsing**: `beautifulsoup4` with `lxml` parser
- **Rate limiting**: Custom implementation with randomized delays
- **Output**: Write individual JSON files per hotel, then consolidate

### Frontend (React)
- **Framework**: React 18+ with Vite
- **Styling**: CSS Modules with CSS custom properties for theming
- **State**: React hooks only (no Redux needed for this scale)
- **Build target**: Static files for GitHub Pages

### Theme System
Themes are implemented via CSS custom properties. The approach:
```css
/* Each theme file sets these variables */
:root[data-theme="dark"] {
  --color-bg-primary: #0a0a0a;
  --color-text-primary: #f0f0f0;
  /* ... etc */
}
```

Theme files: `dark.css`, `frutiger-aero.css`, `flat.css`, `cyberpunk.css`, `modern.css`

Switching themes = changing `data-theme` attribute on `<html>` element.

---

## Data Schema (Canonical Reference)

```json
{
  "id": "string (kebab-case: country-town-hotel-name)",
  "name": "string",
  "town": "string",
  "region": "string",
  "country": "string (Canada | USA | Switzerland | France | Austria | Australia)",
  "marketSegment": "string (Luxury | Upscale | Upper-Midscale | Midscale | Economy)",
  "tripadvisorRank": "number (1-30)",
  "coordinates": { "lat": "number", "lng": "number" },
  "sources": {
    "officialWebsite": "string (URL)",
    "policyPage": "string (URL) — REQUIRED",
    "bookingCom": "string (URL) | null",
    "dataSource": "string (official | booking.com)"
  },
  "taxes": [{
    "name": "string",
    "amount": "string (e.g., '5%' or '$25.00')",
    "basis": "string (per night | per stay | per person | per room)",
    "notes": "string | null"
  }],
  "fees": [{
    "name": "string",
    "amount": "string",
    "basis": "string",
    "includes": ["string"] | null,
    "notes": "string | null"
  }],
  "extraPersonPolicy": {
    "childrenFreeAge": "number | null",
    "childCharge": { "amount": "string", "basis": "string" } | null,
    "adultCharge": { "amount": "string", "basis": "string" } | null,
    "maxOccupancy": "string | null",
    "notes": "string | null"
  },
  "damageDeposit": {
    "amount": "string",
    "basis": "string (per stay | per night)",
    "method": "string | null",
    "refundTimeline": "string | null",
    "notes": "string | null"
  } | null,
  "promotions": [{
    "name": "string",
    "description": "string",
    "validFrom": "string (ISO date) | null",
    "validTo": "string (ISO date) | null",
    "promoCode": "string | null",
    "sourceUrl": "string (URL)"
  }],
  "scrapedAt": "string (ISO datetime)",
  "scrapingNotes": "string | null"
}
```

**If a field cannot be found, use `null` — never omit required fields or invent data.**

---

## Common Commands

### Scraper
```bash
# Install dependencies
cd scraper && pip install -r requirements.txt

# Run full scrape (all locations)
python src/main.py

# Run single town (for testing)
python src/main.py --town "Banff" --country "Canada"

# Run with verbose logging
python src/main.py --verbose

# Generate exports only (from existing JSON)
python src/exporters.py
```

### Frontend
```bash
# Install dependencies
cd frontend && npm install

# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Deployment
```bash
# GitHub Actions handles this automatically on push to main
# Manual build outputs to frontend/dist/
```

---

## File Locations

| What | Where |
|------|-------|
| Individual hotel JSON | `data/hotels/{country}/{town}/{hotel-slug}.json` |
| Consolidated JSON | `data/all-hotels.json` |
| CSV exports | `data/exports/` |
| Frontend data (copy) | `frontend/src/data/hotels.json` |
| Scraping logs | `scraper/logs/` |
| Theme CSS files | `frontend/src/themes/` |

---

## Market Segment Classification

Use these heuristics when classifying hotels:

| Segment | Stars | Typical Rate | Indicators |
|---------|-------|--------------|------------|
| Luxury | 5★ | $400+/night | "Luxury", "5-star", premium amenities, famous brand names (Four Seasons, Ritz-Carlton) |
| Upscale | 4★ | $200-400/night | "Boutique", upscale chains (Marriott, Hilton flagship), design hotels |
| Upper-Midscale | 3.5★ | $150-250/night | Quality chains (Courtyard, Hyatt Place), well-reviewed independents |
| Midscale | 3★ | $100-175/night | Standard chains (Holiday Inn, Best Western), basic independents |
| Economy | 1-2★ | <$100/night | Budget chains (Motel 6, Super 8), hostels, basic motels |

When uncertain, check TripAdvisor's "Hotel Class" or look at average nightly rates.

---

## Scraping Guidelines

### Page Discovery Priority
1. Look for links containing: `policy`, `policies`, `terms`, `conditions`, `faq`, `guest-info`, `hotel-info`
2. Check footer navigation (policies often linked there)
3. Check "About" or "Hotel" sections
4. If nothing found on official site → use Booking.com listing

### What to Capture
- **Taxes**: Government levies, tourism taxes, GST/VAT notes, city taxes
- **Fees**: Resort fees, parking, pets, cleaning, amenity fees, service charges
- **Extra person**: Children free age, child charge, adult charge, rollaway/crib fees
- **Damage deposit**: Amount, per-stay vs per-night, hold method, refund timing
- **Promotions**: Only from dedicated promo pages, never from booking engine

### What NOT to Do
- Don't scrape booking engines or availability calendars
- Don't make more than 1 request per 2 seconds to any single domain
- Don't ignore robots.txt directives (check and log if blocked)
- Don't fabricate data — if not found, mark as null with a note

---

## Frontend Reminders

### Theme Characteristics

| Theme | Key Visual Elements |
|-------|---------------------|
| Dark | Charcoal bg, high contrast, electric blue/amber accents, subtle glows |
| Frutiger Aero | Glassmorphism, soft gradients, sky blue/aqua, rounded everything, bubble motifs |
| Flat | Bold solid colors, no shadows/gradients, geometric, lots of whitespace |
| Cyberpunk | Deep purple/blue, neon pink/cyan, glitch effects, angular, monospace type |
| Modern | Warm neutrals, elegant serifs, editorial layout, refined spacing, minimal shadows |

### Must-Have UI Elements
- Theme selector (persistent, saves to localStorage)
- Country filter (multi-select)
- Town filter (dependent on country selection)
- Market segment filter (checkboxes or pills)
- Hotel name search
- Clear all filters button
- Stats summary (totals, averages)
- Hotel cards with expandable details
- **Prominent policy source link on every hotel detail view**

### Accessibility
- All interactive elements keyboard accessible
- ARIA labels on custom controls
- Sufficient color contrast (WCAG AA minimum)
- Focus indicators visible in all themes

---

## Troubleshooting

### Scraper Issues
- **403 Forbidden**: Rotate user agent, add delay, check if IP blocked
- **Timeout**: Increase timeout, try again later, log and skip
- **Missing data**: Check if page uses JavaScript rendering (may need Playwright)
- **Encoding issues**: Force UTF-8, handle special characters in hotel names

### Frontend Issues
- **Theme not applying**: Check `data-theme` attribute on `<html>`, verify CSS variable names
- **Filters not working**: Verify data shape matches expected schema
- **Slow initial load**: Implement virtualization if hotel count is very high

---

## Future Considerations (Out of Scope for V1)

- Automated periodic re-scraping
- Historical price tracking
- Email alerts for policy changes
- Comparison tool for side-by-side hotel analysis
- Map view of hotels
- PDF export of policy summaries

---

## Contact / Context

This project supports revenue management analysis for a 15-property mountain resort hotel group operating primarily in Banff and Canmore, Alberta. The data helps benchmark policies against competitors across North American and international resort markets.

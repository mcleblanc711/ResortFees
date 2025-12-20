"""Hotel finder module - discovers hotels from TripAdvisor and verifies with Google Maps."""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup

from .utils import RateLimiter, get_headers, get_logger

logger = get_logger(__name__)


@dataclass
class HotelInfo:
    """Basic hotel information from discovery."""
    name: str
    town: str
    region: str
    country: str
    tripadvisor_rank: int
    tripadvisor_url: Optional[str] = None
    official_website: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    market_segment: str = "Midscale"


class HotelFinder:
    """Finds and ranks hotels from various sources."""

    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers=get_headers()
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def find_hotels(
        self,
        town: str,
        region: str,
        country: str,
        limit: int = 30
    ) -> List[HotelInfo]:
        """
        Find top hotels in a given town.

        This is a framework method - actual implementation would require
        TripAdvisor API access or authorized scraping. For now, it returns
        a placeholder structure that can be populated manually or via
        authorized data sources.

        Args:
            town: Town name
            region: Region/state/province
            country: Country name
            limit: Maximum number of hotels to return

        Returns:
            List of HotelInfo objects
        """
        logger.info(f"Finding hotels in {town}, {region}, {country}")

        # In a production environment, this would:
        # 1. Query TripAdvisor API (requires partnership/API key)
        # 2. Or use authorized data providers
        # 3. Or process manually curated hotel lists

        # For demonstration, we return an empty list that can be populated
        # from a curated data file
        hotels = self._load_curated_hotels(town, region, country)

        if not hotels:
            logger.warning(
                f"No curated hotel data found for {town}. "
                "Please add hotels to data/curated/{country}/{town}.json"
            )

        return hotels[:limit]

    def _load_curated_hotels(
        self,
        town: str,
        region: str,
        country: str
    ) -> List[HotelInfo]:
        """Load hotels from curated data files."""
        import json
        from pathlib import Path

        # Normalize names for file paths
        country_slug = country.lower().replace(" ", "-")
        town_slug = town.lower().replace(" ", "-")

        # Get path relative to project root (one level up from scraper/)
        project_root = Path(__file__).parent.parent.parent
        curated_path = project_root / "data" / "curated" / country_slug / f"{town_slug}.json"

        if not curated_path.exists():
            return []

        try:
            with open(curated_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            hotels = []
            for idx, hotel_data in enumerate(data.get("hotels", []), start=1):
                hotels.append(HotelInfo(
                    name=hotel_data["name"],
                    town=town,
                    region=region,
                    country=country,
                    tripadvisor_rank=hotel_data.get("rank", idx),
                    tripadvisor_url=hotel_data.get("tripadvisor_url"),
                    official_website=hotel_data.get("website"),
                    coordinates=hotel_data.get("coordinates"),
                    market_segment=hotel_data.get("market_segment", "Midscale")
                ))

            logger.info(f"Loaded {len(hotels)} hotels from curated data for {town}")
            return hotels

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading curated data for {town}: {e}")
            return []

    def classify_market_segment(
        self,
        hotel_name: str,
        description: str = "",
        star_rating: Optional[float] = None
    ) -> str:
        """
        Classify a hotel into a market segment based on available information.

        Args:
            hotel_name: Hotel name
            description: Hotel description if available
            star_rating: Star rating if available

        Returns:
            Market segment string
        """
        text = f"{hotel_name} {description}".lower()

        # Check by star rating first
        if star_rating:
            if star_rating >= 4.5:
                return "Luxury"
            elif star_rating >= 4.0:
                return "Upscale"
            elif star_rating >= 3.5:
                return "Upper-Midscale"
            elif star_rating >= 3.0:
                return "Midscale"
            else:
                return "Economy"

        # Check by brand/keywords
        luxury_brands = [
            "four seasons", "ritz-carlton", "st. regis", "fairmont",
            "mandarin oriental", "aman", "park hyatt", "waldorf",
            "peninsula", "rosewood"
        ]
        for brand in luxury_brands:
            if brand in text:
                return "Luxury"

        upscale_brands = [
            "marriott", "hilton", "hyatt regency", "westin", "sheraton",
            "intercontinental", "kimpton", "w hotel", "le meridien"
        ]
        for brand in upscale_brands:
            if brand in text:
                return "Upscale"

        midscale_brands = [
            "holiday inn", "best western", "ramada", "wyndham",
            "quality inn", "comfort inn"
        ]
        for brand in midscale_brands:
            if brand in text:
                return "Midscale"

        economy_brands = [
            "motel 6", "super 8", "days inn", "travelodge",
            "econo lodge", "red roof"
        ]
        for brand in economy_brands:
            if brand in text:
                return "Economy"

        # Check keywords
        if any(kw in text for kw in ["5-star", "five star", "luxury", "exclusive"]):
            return "Luxury"
        if any(kw in text for kw in ["4-star", "four star", "boutique", "upscale"]):
            return "Upscale"
        if any(kw in text for kw in ["budget", "hostel", "motel"]):
            return "Economy"

        # Default to midscale
        return "Midscale"

    def generate_hotel_id(self, country: str, town: str, hotel_name: str) -> str:
        """Generate a unique kebab-case ID for a hotel."""
        # Normalize and slugify
        def slugify(text: str) -> str:
            text = text.lower()
            text = re.sub(r"[^\w\s-]", "", text)
            text = re.sub(r"[-\s]+", "-", text)
            return text.strip("-")

        country_slug = slugify(country)
        town_slug = slugify(town)
        name_slug = slugify(hotel_name)

        return f"{country_slug}-{town_slug}-{name_slug}"

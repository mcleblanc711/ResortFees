"""Booking.com fallback scraper for hotels without policy pages on their official sites."""

import re
import time
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, quote_plus, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .policy_scraper import (
    DamageDeposit,
    ExtraPersonPolicy,
    FeeInfo,
    ScrapedPolicy,
    TaxInfo,
)
from .utils import RateLimiter, get_headers, get_logger

logger = get_logger(__name__)

# Try to import Playwright (optional dependency)
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.info("Playwright not available - Booking.com fallback may be limited")


def normalize_hotel_name(name: str) -> str:
    """Normalize hotel name for comparison."""
    # Remove common suffixes and prefixes
    name = name.lower()
    remove_terms = [
        "hotel", "resort", "spa", "lodge", "inn", "suites", "motel",
        "the", "&", "and", "by", "a", "an"
    ]
    words = name.split()
    words = [w for w in words if w not in remove_terms]
    return " ".join(words)


def similarity_score(name1: str, name2: str) -> float:
    """Calculate similarity between two hotel names."""
    n1 = normalize_hotel_name(name1)
    n2 = normalize_hotel_name(name2)
    return SequenceMatcher(None, n1, n2).ratio()


class BookingFallbackScraper:
    """Fallback scraper that extracts policy information from Booking.com listings."""

    BASE_URL = "https://www.booking.com"

    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def scrape_hotel_policies(
        self,
        booking_url: str,
        hotel_name: str
    ) -> Optional[ScrapedPolicy]:
        """
        Scrape policy information from a Booking.com hotel page.

        Args:
            booking_url: Direct Booking.com URL for the hotel
            hotel_name: Hotel name for logging

        Returns:
            ScrapedPolicy object or None if scraping fails
        """
        logger.info(f"Scraping Booking.com fallback for {hotel_name}")

        # Try HTTP first, fall back to Playwright if blocked
        html = None

        self.rate_limiter.wait(booking_url)

        try:
            response = self.client.get(booking_url, headers=get_headers())
            if response.status_code == 200 and len(response.text) > 10000:
                html = response.text
                self.rate_limiter.record_success(booking_url)
            else:
                logger.debug(f"HTTP response indicates bot challenge, trying Playwright")
        except httpx.HTTPError as e:
            logger.debug(f"HTTP request failed: {e}")

        # If HTTP failed, try Playwright
        if not html and PLAYWRIGHT_AVAILABLE:
            html = self._fetch_page_playwright(booking_url, hotel_name)

        if not html:
            logger.error(f"Failed to fetch Booking.com page for {hotel_name}")
            return None

        soup = BeautifulSoup(html, "lxml")
        raw_text = self._extract_policy_section(soup)

        policy = ScrapedPolicy(
            policy_url=booking_url,
            data_source="booking.com",
            raw_text=raw_text
        )

        # Extract structured data from Booking.com's format
        policy.taxes = self._extract_taxes(soup, raw_text)
        policy.fees = self._extract_fees(soup, raw_text)
        policy.extra_person_policy = self._extract_extra_person_policy(soup, raw_text)
        policy.damage_deposit = self._extract_damage_deposit(soup, raw_text)

        policy.scraping_notes = "Data sourced from Booking.com listing"

        return policy

    def _fetch_page_playwright(self, url: str, hotel_name: str) -> Optional[str]:
        """Fetch a page using Playwright (handles JavaScript rendering)."""
        logger.info(f"Fetching Booking.com page with Playwright: {hotel_name}")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                page = context.new_page()

                page.goto(url, wait_until="networkidle", timeout=30000)

                # Wait for policy section to potentially load
                time.sleep(2)

                # Try to scroll to trigger lazy loading
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(1)

                html = page.content()
                browser.close()

                if len(html) > 10000:
                    return html
                else:
                    logger.warning(f"Playwright response too small ({len(html)} bytes)")
                    return None

        except Exception as e:
            logger.error(f"Playwright fetch failed: {e}")
            return None

    def _extract_policy_section(self, soup: BeautifulSoup) -> str:
        """Extract the policy/fine print section from Booking.com page."""
        text_parts = []

        # Strategy 1: Look for data-testid attributes (modern Booking.com)
        policy_testids = [
            "property-policies",
            "PropertyPoliciesOverview",
            "house-rules",
            "HouseRules",
            "fine-print",
            "FinePrint",
            "important-info",
            "children-policy",
            "pet-policy",
            "deposit-policy",
        ]
        for testid in policy_testids:
            sections = soup.find_all(attrs={"data-testid": lambda x: x and testid.lower() in str(x).lower()})
            for section in sections:
                text_parts.append(section.get_text(separator="\n", strip=True))

        # Strategy 2: Look for class-based sections
        class_keywords = [
            "policy", "policies", "fine-print", "fineprint",
            "house-rules", "houserules", "important-info",
            "children", "child-policy", "extra-bed", "deposit"
        ]
        for keyword in class_keywords:
            sections = soup.find_all(
                ["div", "section", "article"],
                class_=lambda x: x and keyword in str(x).lower()
            )
            for section in sections:
                text = section.get_text(separator="\n", strip=True)
                if text and text not in text_parts:
                    text_parts.append(text)

        # Strategy 3: Look for ID-based sections
        id_keywords = ["policies", "fine_print", "house_rules", "important"]
        for keyword in id_keywords:
            sections = soup.find_all(id=lambda x: x and keyword in str(x).lower())
            for section in sections:
                text = section.get_text(separator="\n", strip=True)
                if text and text not in text_parts:
                    text_parts.append(text)

        # Strategy 4: Look for headers and their following content
        headers = soup.find_all(["h2", "h3", "h4"], string=lambda x: x and any(
            kw in x.lower() for kw in ["fine print", "house rules", "policies", "children", "extra bed", "deposit"]
        ))
        for header in headers:
            # Get the parent container or next siblings
            parent = header.find_parent(["div", "section"])
            if parent:
                text = parent.get_text(separator="\n", strip=True)
                if text and text not in text_parts:
                    text_parts.append(text)

        # Strategy 5: Look for the specific "The fine print" landmark section
        fine_print_section = soup.find(id="hp_policies_cont") or soup.find(id="policies")
        if fine_print_section:
            text = fine_print_section.get_text(separator="\n", strip=True)
            if text:
                text_parts.append(text)

        return "\n\n".join(text_parts)

    def _extract_taxes(
        self,
        soup: BeautifulSoup,
        text: str
    ) -> List[TaxInfo]:
        """Extract tax information from Booking.com listing."""
        taxes = []
        seen = set()

        # Comprehensive tax patterns
        patterns = [
            # Standard percentage taxes
            r"(?P<name>[\w\s]+(?:tax|VAT|GST|HST|PST|levy))\s*[:\-]?\s*(?:of\s*)?(?P<amount>\d+(?:\.\d+)?%)",
            r"(?P<amount>\d+(?:\.\d+)?%)\s+(?P<name>[\w\s]*(?:tax|VAT|levy))",
            # Fixed amount taxes with various currencies
            r"(?P<name>(?:city|tourism|destination|lodging|occupancy|local|resort)\s+(?:tax|levy|fee))\s*[:\-]?\s*(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            # Tax mentioned with "per night" context
            r"(?P<name>[\w\s]+tax)\s+(?:is\s+)?(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)\s*(?:per|/)\s*(?:night|room|person)",
            # VAT included/excluded patterns
            r"(?P<amount>\d+(?:\.\d+)?%)\s*VAT\s*(?P<name>included|excluded)?",
            # Swiss-style taxes (Kurtaxe, etc.)
            r"(?P<name>(?:Kurtaxe|Beherbergungsabgabe|tourist\s+tax|city\s+tax))\s*[:\-]?\s*(?P<amount>CHF\s*[\d,]+(?:\.\d{2})?|\d+(?:\.\d+)?)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groupdict()
                name = groups.get("name", "").strip()
                amount = groups.get("amount", "").strip()

                if not name or name.lower() in ["included", "excluded"]:
                    name = "VAT"
                if not amount:
                    continue

                # Normalize name
                name = name.title()

                # Determine basis from context
                basis = "per night"
                context = text[max(0, match.start() - 100):match.end() + 100].lower()
                if "per stay" in context or "one-time" in context:
                    basis = "per stay"
                elif "per person" in context or "per guest" in context:
                    basis = "per person per night"
                elif "per room" in context:
                    basis = "per room per night"

                # Deduplicate
                key = (name.lower(), amount.lower())
                if key not in seen:
                    seen.add(key)
                    taxes.append(TaxInfo(
                        name=name,
                        amount=amount,
                        basis=basis,
                        notes="As listed on Booking.com"
                    ))

        return taxes

    def _extract_fees(
        self,
        soup: BeautifulSoup,
        text: str
    ) -> List[FeeInfo]:
        """Extract fee information from Booking.com listing."""
        fees = []
        seen = set()

        # Comprehensive fee patterns for Booking.com
        patterns = [
            # Resort/amenity fees
            r"(?P<name>(?:resort|amenity|facility|destination|daily)\s+fee)\s*[:\-]?\s*(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            # Cleaning fees
            r"(?P<name>cleaning\s+(?:fee|charge))\s*[:\-]?\s*(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            # Service charges
            r"(?P<name>service\s+charge)\s*[:\-]?\s*(?P<amount>\d+(?:\.\d+)?%|[$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            # Parking - various formats
            r"(?P<name>(?:self[- ]?parking|valet\s+parking|parking|car\s+park))\s*[:\-]?\s*(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            r"(?P<name>parking)\s+(?:costs?|charges?|fees?|is)\s*(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            r"(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)\s*(?:per\s+(?:day|night))?\s*(?:for\s+)?(?P<name>parking)",
            # Pet fees
            r"(?P<name>pet\s+(?:fee|charge))\s*[:\-]?\s*(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            r"(?P<name>pets?)\s+(?:are\s+)?(?:allowed|welcome).*?(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)\s*(?:per|each)",
            # Early check-in / late check-out
            r"(?P<name>(?:early\s+check[- ]?in|late\s+check[- ]?out))\s*[:\-]?\s*(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            # Extra bed fees
            r"(?P<name>(?:extra|additional)\s+bed)\s*[:\-]?\s*(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            r"(?P<name>(?:rollaway|cot|crib))\s*[:\-]?\s*(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            # Breakfast fees
            r"(?P<name>breakfast)\s*[:\-]?\s*(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)\s*(?:per\s+(?:person|guest))?",
            # WiFi fees (if not free)
            r"(?P<name>(?:wi-?fi|internet))\s*[:\-]?\s*(?P<amount>[$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            # Swiss-specific fees
            r"(?P<name>(?:Kurtaxe|Ortstaxe|visitor'?s?\s+tax))\s*[:\-]?\s*(?P<amount>CHF\s*[\d,]+(?:\.\d{2})?)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                groups = match.groupdict()
                name = groups.get("name", "").strip()
                amount = groups.get("amount", "").strip()

                if not name or not amount:
                    continue

                # Skip if amount is 0 or "free"
                if amount.lower() in ["free", "0", "0.00"] or re.match(r"^[$€£CHF\s]*0+(?:\.0+)?$", amount):
                    continue

                # Normalize name
                name = name.title()

                # Determine basis from context
                basis = "per night"
                context = text[max(0, match.start() - 100):match.end() + 100].lower()
                if "per stay" in context or "one-time" in context or "per reservation" in context:
                    basis = "per stay"
                elif "per person" in context or "per guest" in context:
                    if "per night" in context or "per day" in context:
                        basis = "per person per night"
                    else:
                        basis = "per person"
                elif "per room" in context:
                    basis = "per room per night"
                elif "per day" in context:
                    basis = "per day"

                # Deduplicate
                key = (name.lower(), amount.lower())
                if key not in seen:
                    seen.add(key)
                    fees.append(FeeInfo(
                        name=name,
                        amount=amount,
                        basis=basis,
                        notes="As listed on Booking.com"
                    ))

        return fees

    def _extract_extra_person_policy(
        self,
        soup: BeautifulSoup,
        text: str
    ) -> Optional[ExtraPersonPolicy]:
        """Extract extra person policy from Booking.com listing."""
        policy = ExtraPersonPolicy()
        has_data = False
        notes_parts = []

        # Children free age - various patterns
        child_patterns = [
            r"children\s+(?:up to|under)\s+(\d+)\s+(?:years?\s+(?:old\s+)?)?(?:stay\s+)?free",
            r"children\s+(\d+)\s+and\s+(?:under|younger)\s+stay\s+free",
            r"children\s+(?:aged?\s+)?(\d+)\s+(?:years?\s+)?and\s+under\s+(?:stay\s+)?free",
            r"free\s+(?:for\s+)?children\s+(?:under|up to)\s+(\d+)",
            r"children\s+(\d+)[-–](\d+)\s+(?:years?\s+)?(?:stay\s+)?free",  # age range
            r"(?:kids|infants?)\s+(?:under|up to)\s+(\d+)\s+(?:stay\s+)?free",
        ]

        for pattern in child_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Handle age range - take the higher number
                groups = match.groups()
                if len(groups) > 1 and groups[1]:
                    policy.children_free_age = int(groups[1])
                else:
                    policy.children_free_age = int(groups[0])
                has_data = True
                break

        # Extra bed/adult charges
        extra_adult_patterns = [
            r"extra\s+(?:bed|adult)\s*[:\-]?\s*([$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            r"additional\s+(?:person|adult|guest)\s*[:\-]?\s*([$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            r"([$€£CHF\s]*[\d,]+(?:\.\d{2})?)\s*(?:per\s+(?:night|person))?\s*(?:for\s+)?(?:extra|additional)\s+(?:adult|person|guest)",
        ]

        for pattern in extra_adult_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group(1).strip()
                if amount and not re.match(r"^[$€£CHF\s]*0+(?:\.0+)?$", amount):
                    policy.adult_charge = {
                        "amount": amount,
                        "basis": "per night"
                    }
                    has_data = True
                    break

        # Extra child charges
        extra_child_patterns = [
            r"(?:extra|additional)\s+child\s*[:\-]?\s*([$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            r"child(?:ren)?\s+(?:charge|fee)\s*[:\-]?\s*([$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
        ]

        for pattern in extra_child_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group(1).strip()
                if amount and not re.match(r"^[$€£CHF\s]*0+(?:\.0+)?$", amount):
                    policy.child_charge = {
                        "amount": amount,
                        "basis": "per night"
                    }
                    has_data = True
                    break

        # Maximum occupancy
        occupancy_patterns = [
            r"(?:maximum|max)\s+(?:occupancy|capacity)\s*[:\-]?\s*(\d+)\s*(?:guests?|persons?|people)?",
            r"(?:accommodates?|sleeps?)\s+(?:up to\s+)?(\d+)\s*(?:guests?|persons?|people)?",
        ]

        for pattern in occupancy_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                policy.max_occupancy = f"{match.group(1)} guests"
                has_data = True
                break

        # Crib/cot info
        crib_match = re.search(r"crib|cot|baby\s+bed", text, re.IGNORECASE)
        if crib_match:
            context = text[max(0, crib_match.start() - 50):crib_match.end() + 100].lower()
            if any(kw in context for kw in ["free", "complimentary", "no charge", "available"]):
                notes_parts.append("Cribs available")
            elif any(kw in context for kw in ["not available", "unavailable"]):
                notes_parts.append("Cribs not available")

        # Rollaway bed info
        rollaway_match = re.search(r"rollaway|extra\s+bed", text, re.IGNORECASE)
        if rollaway_match:
            context = text[max(0, rollaway_match.start() - 50):rollaway_match.end() + 100].lower()
            if "available" in context and "not" not in context:
                notes_parts.append("Rollaway beds available")

        if notes_parts:
            policy.notes = "; ".join(notes_parts)
            has_data = True

        return policy if has_data else None

    def _extract_damage_deposit(
        self,
        soup: BeautifulSoup,
        text: str
    ) -> Optional[DamageDeposit]:
        """Extract damage deposit info from Booking.com listing."""
        patterns = [
            r"(?:damage|security|incidental)\s+deposit\s*(?:of)?\s*([$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            r"([$€£CHF\s]*[\d,]+(?:\.\d{2})?)\s+(?:damage|security|incidental)\s+deposit",
            r"(?:pre[- ]?authorization|credit\s+card\s+(?:hold|authorization))\s*(?:of)?\s*([$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
            r"(?:refundable\s+)?deposit\s+(?:of\s+)?([$€£CHF\s]*[\d,]+(?:\.\d{2})?)\s*(?:is\s+)?required",
            r"deposit\s*[:\-]?\s*([$€£CHF\s]*[\d,]+(?:\.\d{2})?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group(1).strip()

                # Skip if amount is 0
                if not amount or re.match(r"^[$€£CHF\s]*0+(?:\.0+)?$", amount):
                    continue

                # Determine basis from context
                context = text[max(0, match.start() - 100):match.end() + 150].lower()
                basis = "per stay"  # Default for deposits
                if "per night" in context:
                    basis = "per night"

                # Look for method
                method = None
                if "credit card" in context or "pre-authorization" in context or "pre authorization" in context:
                    method = "Credit card pre-authorization"
                elif "cash" in context and "credit" not in context:
                    method = "Cash deposit"
                elif "card" in context:
                    method = "Credit card hold"

                # Look for refund timeline
                refund_timeline = None
                refund_patterns = [
                    r"(?:refund|release)(?:ed|able)?\s+(?:within\s+)?(\d+)\s*(?:business\s+)?days?",
                    r"(\d+)\s*(?:business\s+)?days?\s+(?:to|for)\s+(?:refund|release)",
                    r"(?:returned|refunded)\s+(?:within\s+)?(\d+)\s*(?:business\s+)?days?",
                ]
                for refund_pattern in refund_patterns:
                    refund_match = re.search(refund_pattern, context)
                    if refund_match:
                        refund_timeline = f"Within {refund_match.group(1)} days"
                        break

                return DamageDeposit(
                    amount=amount,
                    basis=basis,
                    method=method,
                    refund_timeline=refund_timeline,
                    notes="As listed on Booking.com"
                )

        return None

    # Country code mapping for Booking.com URLs
    COUNTRY_CODES = {
        "canada": "ca",
        "usa": "us",
        "united states": "us",
        "switzerland": "ch",
        "france": "fr",
        "austria": "at",
        "australia": "au",
        "germany": "de",
        "italy": "it",
        "spain": "es",
        "uk": "gb",
        "united kingdom": "gb",
    }

    def _generate_url_slugs(self, hotel_name: str, town: str) -> List[str]:
        """Generate possible Booking.com URL slugs for a hotel name."""
        slugs = []

        # Normalize name
        name = hotel_name.lower()

        # Remove common suffixes that might not be in URL
        for suffix in [" hotel", " resort", " spa", " & spa", " and spa", " lodge"]:
            name = name.replace(suffix, "")

        # Generate slug variations
        # Basic slug: replace spaces with dashes
        base_slug = re.sub(r'[^a-z0-9\s-]', '', name)
        base_slug = re.sub(r'\s+', '-', base_slug.strip())
        slugs.append(base_slug)

        # With town appended
        town_slug = re.sub(r'[^a-z0-9\s-]', '', town.lower())
        town_slug = re.sub(r'\s+', '-', town_slug.strip())
        slugs.append(f"{base_slug}-{town_slug}")

        # Common variations
        # Remove "the" prefix
        if base_slug.startswith("the-"):
            slugs.append(base_slug[4:])

        # Try without hyphens (some hotels use no separator)
        slugs.append(base_slug.replace("-", ""))

        return slugs

    def find_booking_url(
        self,
        hotel_name: str,
        town: str,
        country: str
    ) -> Optional[str]:
        """
        Find the Booking.com URL for a hotel.

        First tries to construct URLs based on naming patterns, then falls back to search.

        Args:
            hotel_name: Hotel name
            town: Town name
            country: Country name

        Returns:
            Booking.com URL or None
        """
        logger.info(f"Finding Booking.com URL for: {hotel_name} in {town}, {country}")

        # Get country code
        country_code = self.COUNTRY_CODES.get(country.lower(), country.lower()[:2])

        # Try constructing URLs directly
        slugs = self._generate_url_slugs(hotel_name, town)

        for slug in slugs:
            url = f"{self.BASE_URL}/hotel/{country_code}/{slug}.html"
            logger.debug(f"Trying URL: {url}")

            self.rate_limiter.wait(url)

            try:
                response = self.client.head(url, headers=get_headers(), follow_redirects=True)
                if response.status_code == 200:
                    # Verify it's actually a hotel page (not a redirect to search)
                    final_url = str(response.url)
                    if "/hotel/" in final_url:
                        logger.info(f"Found Booking.com URL via direct construction: {final_url}")
                        self.rate_limiter.record_success(url)
                        return final_url
            except httpx.HTTPError:
                pass

        # If direct construction fails, try search
        logger.debug(f"Direct URL construction failed, trying search...")

        # Try Playwright-based search first (handles JavaScript challenges)
        if PLAYWRIGHT_AVAILABLE:
            search_result = self._search_booking_url_playwright(hotel_name, town, country)
            if search_result:
                return search_result

        # Fall back to HTTP-based search (may fail due to bot detection)
        search_result = self._search_booking_url(hotel_name, town, country)
        if search_result:
            return search_result

        logger.warning(f"Could not find Booking.com URL for {hotel_name}")
        return None

    def _search_booking_url_playwright(
        self,
        hotel_name: str,
        town: str,
        country: str
    ) -> Optional[str]:
        """
        Search Booking.com for a hotel URL using Playwright (handles JavaScript).

        This is the preferred method as it can handle Booking.com's bot detection.
        """
        search_query = f"{hotel_name} {town}"
        search_url = f"{self.BASE_URL}/searchresults.html?ss={quote_plus(search_query)}"

        logger.info(f"Searching Booking.com with Playwright: {hotel_name}")

        try:
            with sync_playwright() as p:
                # Launch browser in headless mode
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                page = context.new_page()

                # Navigate to search page
                page.goto(search_url, wait_until="networkidle", timeout=30000)

                # Wait for results to load
                try:
                    page.wait_for_selector('[data-testid="property-card"]', timeout=10000)
                except PlaywrightTimeout:
                    logger.debug("No property cards found, page may be blocked or empty")
                    browser.close()
                    return None

                # Get page content
                html = page.content()
                browser.close()

        except Exception as e:
            logger.error(f"Playwright search failed: {e}")
            return None

        # Parse results
        soup = BeautifulSoup(html, "lxml")
        hotel_links = self._extract_search_results(soup)

        if not hotel_links:
            logger.debug("No hotel links found in Playwright results")
            return None

        # Score results by name similarity
        best_match = None
        best_score = 0.0

        for result_name, result_url in hotel_links:
            score = similarity_score(hotel_name, result_name)
            logger.debug(f"Playwright result: '{result_name}' score={score:.2f}")

            if score > best_score:
                best_score = score
                best_match = result_url

        if best_score >= 0.5:
            logger.info(f"Found Booking.com match via Playwright (score={best_score:.2f}): {best_match}")
            return best_match

        return None

    def _search_booking_url(
        self,
        hotel_name: str,
        town: str,
        country: str
    ) -> Optional[str]:
        """
        Search Booking.com for a hotel URL.

        Note: This may fail due to bot detection (JavaScript challenge).
        """
        search_query = f"{hotel_name} {town} {country}"
        search_url = f"{self.BASE_URL}/searchresults.html?ss={quote_plus(search_query)}"

        self.rate_limiter.wait(search_url)

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            }

            with httpx.Client(timeout=30.0, follow_redirects=True) as search_client:
                response = search_client.get(search_url, headers=headers)

            # Check for bot detection (JavaScript challenge)
            if response.status_code == 202 or len(response.text) < 10000:
                logger.debug("Booking.com returned bot challenge page, skipping search")
                return None

            if response.status_code != 200:
                return None

            self.rate_limiter.record_success(search_url)

        except httpx.HTTPError as e:
            logger.debug(f"Search request failed: {e}")
            return None

        soup = BeautifulSoup(response.text, "lxml")
        hotel_links = self._extract_search_results(soup)

        if not hotel_links:
            return None

        # Score results by name similarity
        best_match = None
        best_score = 0.0

        for result_name, result_url in hotel_links:
            score = similarity_score(hotel_name, result_name)
            logger.debug(f"Booking.com result: '{result_name}' score={score:.2f}")

            if score > best_score:
                best_score = score
                best_match = result_url

        if best_score >= 0.5:
            logger.info(f"Found Booking.com match via search (score={best_score:.2f}): {best_match}")
            return best_match

        return None

    def _extract_search_results(self, soup: BeautifulSoup) -> List[Tuple[str, str]]:
        """Extract hotel names and URLs from Booking.com search results."""
        results = []

        # Strategy 1: Look for property cards with data-testid (modern layout) - PREFERRED
        property_cards = soup.find_all(attrs={"data-testid": "property-card"})
        for card in property_cards:
            title_link = card.find(attrs={"data-testid": "title-link"})
            if title_link:
                name_elem = title_link.find(attrs={"data-testid": "title"})
                name = name_elem.get_text(strip=True) if name_elem else None
                url = title_link.get("href", "")
                if name and url and len(name) > 2:
                    if not url.startswith("http"):
                        url = urljoin(self.BASE_URL, url)
                    results.append((name, url))

        # If Strategy 1 found results, use only those (cleanest data)
        if results:
            return self._deduplicate_results(results)

        # Strategy 2: Look for sr-hotel__name class (older layout)
        hotel_cards = soup.find_all(class_="sr-hotel__name")
        for card in hotel_cards:
            link = card.find("a") or card.find_parent("a")
            if link:
                name = card.get_text(strip=True)
                url = link.get("href", "")
                if name and url and len(name) > 2:
                    if not url.startswith("http"):
                        url = urljoin(self.BASE_URL, url)
                    results.append((name, url))

        if results:
            return self._deduplicate_results(results)

        # Strategy 3: Extract from URL slugs only (fallback - avoids messy text extraction)
        seen_slugs = set()
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if "/hotel/" in href and "booking.com" in href:
                # Extract hotel slug from URL like /hotel/ca/fairmont-banff-springs.html
                slug_match = re.search(r'/hotel/[a-z]{2}/([^/?#]+)', href)
                if slug_match:
                    slug = slug_match.group(1).replace('.html', '')
                    if slug not in seen_slugs:
                        seen_slugs.add(slug)
                        # Convert slug to readable name
                        name = slug.replace('-', ' ').title()
                        if not href.startswith("http"):
                            href = urljoin(self.BASE_URL, href)
                        results.append((name, href))

        return self._deduplicate_results(results)

    def _deduplicate_results(self, results: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Deduplicate results by URL, keeping the entry with the best name."""
        url_to_entry = {}
        for name, url in results:
            base_url = url.split("?")[0]
            # Prefer longer names that don't contain garbage (numbers, reviews, etc.)
            is_clean = not re.search(r'\d{3,}|reviews?|superb|good|fabulous', name.lower())
            existing = url_to_entry.get(base_url)
            if not existing or (is_clean and len(name) >= len(existing[0])):
                url_to_entry[base_url] = (name, url)

        return list(url_to_entry.values())

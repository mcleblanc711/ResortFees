"""Booking.com fallback scraper for hotels without policy pages on their official sites."""

import re
from typing import Dict, List, Optional
from urllib.parse import quote, urljoin

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

        self.rate_limiter.wait(booking_url)

        try:
            response = self.client.get(booking_url, headers=get_headers())
            response.raise_for_status()
            self.rate_limiter.record_success(booking_url)
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch Booking.com page for {hotel_name}: {e}")
            self.rate_limiter.record_failure(booking_url)
            return None

        soup = BeautifulSoup(response.text, "lxml")
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

    def _extract_policy_section(self, soup: BeautifulSoup) -> str:
        """Extract the policy/fine print section from Booking.com page."""
        text_parts = []

        # Look for the "Fine print" or "House rules" section
        policy_sections = soup.find_all(
            ["div", "section"],
            class_=lambda x: x and any(
                kw in str(x).lower()
                for kw in ["policy", "fine-print", "house-rules", "important-info"]
            )
        )

        for section in policy_sections:
            text_parts.append(section.get_text(separator="\n", strip=True))

        # Also look for data attributes that might contain policy info
        policy_divs = soup.find_all(attrs={"data-testid": lambda x: x and "policy" in str(x).lower()})
        for div in policy_divs:
            text_parts.append(div.get_text(separator="\n", strip=True))

        return "\n\n".join(text_parts)

    def _extract_taxes(
        self,
        soup: BeautifulSoup,
        text: str
    ) -> List[TaxInfo]:
        """Extract tax information from Booking.com listing."""
        taxes = []

        # Booking.com often lists taxes in a specific format
        patterns = [
            r"(?P<name>[\w\s]+(?:tax|VAT|levy))\s*(?:of)?\s*(?P<amount>\d+(?:\.\d+)?%|\€[\d,]+(?:\.\d{2})?|\$[\d,]+(?:\.\d{2})?)",
            r"(?P<amount>\d+(?:\.\d+)?%)\s+(?P<name>[\w\s]+(?:tax|VAT))",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.group("name").strip()
                amount = match.group("amount").strip()

                # Skip if amount seems like a percentage of something else
                if "%" in amount:
                    taxes.append(TaxInfo(
                        name=name.title(),
                        amount=amount,
                        basis="per night",
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

        # Common Booking.com fee patterns
        patterns = [
            r"(?P<name>cleaning\s+fee|resort\s+fee|service\s+charge|facility\s+fee)\s*[:\-]?\s*(?P<amount>[\€\$][\d,]+(?:\.\d{2})?|\d+(?:\.\d+)?%)",
            r"(?P<name>parking)\s*(?:is)?\s*(?P<amount>[\€\$][\d,]+(?:\.\d{2})?)\s*per\s*(?P<basis>day|night)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.group("name").strip()
                amount = match.group("amount").strip()
                basis = match.groupdict().get("basis", "per night")
                if basis in ["day", "night"]:
                    basis = f"per {basis}"

                fees.append(FeeInfo(
                    name=name.title(),
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

        # Booking.com often has specific child policy sections
        child_patterns = [
            r"children\s+(?:up to|under)\s+(\d+)\s+(?:years?\s+)?(?:stay\s+)?free",
            r"children\s+(\d+)\s+and\s+(?:under|younger)\s+stay\s+free",
        ]

        for pattern in child_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                policy.children_free_age = int(match.group(1))
                has_data = True
                break

        # Extra bed/person charges
        extra_patterns = [
            r"extra\s+bed\s*[:\-]?\s*([\€\$][\d,]+(?:\.\d{2})?)",
            r"additional\s+(?:person|adult)\s*[:\-]?\s*([\€\$][\d,]+(?:\.\d{2})?)",
        ]

        for pattern in extra_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                policy.adult_charge = {
                    "amount": match.group(1),
                    "basis": "per night"
                }
                has_data = True
                break

        # Crib/cot info
        if re.search(r"crib|cot|baby\s+bed", text, re.IGNORECASE):
            if re.search(r"free\s+(?:of\s+charge)?|complimentary|no\s+charge", text, re.IGNORECASE):
                policy.notes = "Cribs available free of charge"
                has_data = True

        return policy if has_data else None

    def _extract_damage_deposit(
        self,
        soup: BeautifulSoup,
        text: str
    ) -> Optional[DamageDeposit]:
        """Extract damage deposit info from Booking.com listing."""
        patterns = [
            r"(?:damage|security)\s+deposit\s*(?:of)?\s*([\€\$][\d,]+(?:\.\d{2})?)",
            r"([\€\$][\d,]+(?:\.\d{2})?)\s+(?:damage|security)\s+deposit",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group(1)

                # Look for method
                method = None
                if "credit card" in text.lower():
                    method = "Credit card"
                elif "cash" in text.lower():
                    method = "Cash"

                return DamageDeposit(
                    amount=amount,
                    basis="per stay",
                    method=method,
                    notes="As listed on Booking.com"
                )

        return None

    def find_booking_url(
        self,
        hotel_name: str,
        town: str,
        country: str
    ) -> Optional[str]:
        """
        Attempt to find the Booking.com URL for a hotel.

        Note: This is a framework method. In production, you would either:
        1. Use Booking.com's affiliate API
        2. Use a curated mapping of hotel names to Booking.com URLs
        3. Manually compile Booking.com URLs

        Args:
            hotel_name: Hotel name
            town: Town name
            country: Country name

        Returns:
            Booking.com URL or None
        """
        # This would require either API access or manual curation
        # For now, return None and rely on curated data
        logger.debug(f"Booking.com URL lookup not implemented for {hotel_name}")
        return None

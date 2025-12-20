"""Core policy scraper - extracts tax, fee, and policy information from hotel websites."""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from .utils import RateLimiter, get_headers, get_logger

logger = get_logger(__name__)


@dataclass
class TaxInfo:
    """Tax information extracted from a hotel page."""
    name: str
    amount: str
    basis: str
    notes: Optional[str] = None


@dataclass
class FeeInfo:
    """Fee information extracted from a hotel page."""
    name: str
    amount: str
    basis: str
    includes: Optional[List[str]] = None
    notes: Optional[str] = None


@dataclass
class ExtraPersonPolicy:
    """Extra person policy information."""
    children_free_age: Optional[int] = None
    child_charge: Optional[Dict[str, str]] = None
    adult_charge: Optional[Dict[str, str]] = None
    max_occupancy: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class DamageDeposit:
    """Damage deposit information."""
    amount: str
    basis: str
    method: Optional[str] = None
    refund_timeline: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class ScrapedPolicy:
    """Complete scraped policy data for a hotel."""
    policy_url: str
    data_source: str
    taxes: List[TaxInfo] = field(default_factory=list)
    fees: List[FeeInfo] = field(default_factory=list)
    extra_person_policy: Optional[ExtraPersonPolicy] = None
    damage_deposit: Optional[DamageDeposit] = None
    raw_text: str = ""
    scraping_notes: Optional[str] = None


class PolicyScraper:
    """Scrapes policy information from hotel websites."""

    # URL patterns that typically contain policy information
    POLICY_PATTERNS = [
        "/policies", "/policy", "/terms", "/conditions",
        "/terms-and-conditions", "/hotel-policies", "/guest-information",
        "/guest-info", "/faq", "/info", "/about-the-hotel", "/hotel-info"
    ]

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
        base_url: str,
        hotel_name: str
    ) -> Optional[ScrapedPolicy]:
        """
        Scrape policy information from a hotel's website.

        Args:
            base_url: Hotel's main website URL
            hotel_name: Hotel name for logging

        Returns:
            ScrapedPolicy object or None if scraping fails
        """
        logger.info(f"Scraping policies for {hotel_name} from {base_url}")

        # First, find the policy page
        policy_url = self._find_policy_page(base_url)

        if not policy_url:
            logger.warning(f"No policy page found for {hotel_name}")
            return None

        # Scrape the policy page
        self.rate_limiter.wait(policy_url)
        try:
            response = self.client.get(policy_url, headers=get_headers(base_url))
            response.raise_for_status()
            self.rate_limiter.record_success(policy_url)
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch policy page for {hotel_name}: {e}")
            self.rate_limiter.record_failure(policy_url)
            return None

        # Parse the page
        soup = BeautifulSoup(response.text, "lxml")
        raw_text = self._extract_text_content(soup)

        # Extract policy information
        policy = ScrapedPolicy(
            policy_url=policy_url,
            data_source="official",
            raw_text=raw_text
        )

        policy.taxes = self._extract_taxes(soup, raw_text)
        policy.fees = self._extract_fees(soup, raw_text)
        policy.extra_person_policy = self._extract_extra_person_policy(raw_text)
        policy.damage_deposit = self._extract_damage_deposit(raw_text)

        # Add notes if data is incomplete
        if not policy.taxes and not policy.fees:
            policy.scraping_notes = "No taxes or fees found on policy page"

        return policy

    def _find_policy_page(self, base_url: str) -> Optional[str]:
        """Find the policy page URL by checking common patterns."""
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # Try common policy page patterns
        for pattern in self.POLICY_PATTERNS:
            url = urljoin(base, pattern)
            self.rate_limiter.wait(url)
            try:
                response = self.client.head(
                    url,
                    headers=get_headers(),
                    follow_redirects=True
                )
                if response.status_code == 200:
                    self.rate_limiter.record_success(url)
                    return str(response.url)
            except httpx.HTTPError:
                continue

        # If no direct pattern works, try to find links on the homepage
        return self._find_policy_link_on_page(base_url)

    def _find_policy_link_on_page(self, page_url: str) -> Optional[str]:
        """Search for policy links on a given page."""
        self.rate_limiter.wait(page_url)
        try:
            response = self.client.get(page_url, headers=get_headers())
            response.raise_for_status()
        except httpx.HTTPError:
            return None

        soup = BeautifulSoup(response.text, "lxml")

        # Look for links containing policy-related keywords
        policy_keywords = [
            "policy", "policies", "terms", "conditions", "faq",
            "guest info", "hotel info"
        ]

        for link in soup.find_all("a", href=True):
            link_text = link.get_text().lower()
            href = link["href"].lower()

            for keyword in policy_keywords:
                if keyword in link_text or keyword in href:
                    full_url = urljoin(page_url, link["href"])
                    return full_url

        return None

    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract readable text content from the page."""
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()

        # Get text
        text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    def _extract_taxes(
        self,
        soup: BeautifulSoup,
        text: str
    ) -> List[TaxInfo]:
        """Extract tax information from page content."""
        taxes = []

        # Common tax patterns
        patterns = [
            # Percentage-based taxes
            r"(?P<name>[\w\s]+(?:tax|levy|GST|VAT|HST|PST))\s*[:\-]?\s*(?P<amount>\d+(?:\.\d+)?%)",
            # Fixed amount taxes
            r"(?P<name>[\w\s]+(?:tax|levy))\s*[:\-]?\s*(?P<amount>\$[\d,]+(?:\.\d{2})?)",
            # Tourism/destination levies
            r"(?P<name>(?:tourism|destination|city|lodging|occupancy)\s+(?:levy|tax|fee))\s*[:\-]?\s*(?P<amount>\d+(?:\.\d+)?%|\$[\d,]+(?:\.\d{2})?)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.group("name").strip()
                amount = match.group("amount").strip()

                # Determine basis
                basis = "per night"  # Default
                context = text[max(0, match.start() - 50):match.end() + 50].lower()
                if "per stay" in context:
                    basis = "per stay"
                elif "per person" in context:
                    basis = "per person"

                taxes.append(TaxInfo(
                    name=name.title(),
                    amount=amount,
                    basis=basis
                ))

        # Remove duplicates
        seen = set()
        unique_taxes = []
        for tax in taxes:
            key = (tax.name.lower(), tax.amount)
            if key not in seen:
                seen.add(key)
                unique_taxes.append(tax)

        return unique_taxes

    def _extract_fees(
        self,
        soup: BeautifulSoup,
        text: str
    ) -> List[FeeInfo]:
        """Extract fee information from page content."""
        fees = []

        # Common fee patterns
        patterns = [
            # Resort/amenity fees
            r"(?P<name>(?:resort|amenity|facility|destination)\s+fee)\s*[:\-]?\s*(?P<amount>\$[\d,]+(?:\.\d{2})?)",
            # Parking fees
            r"(?P<name>(?:self[- ]?park(?:ing)?|valet|parking))\s*[:\-]?\s*(?P<amount>\$[\d,]+(?:\.\d{2})?)",
            # Pet fees
            r"(?P<name>pet\s+fee)\s*[:\-]?\s*(?P<amount>\$[\d,]+(?:\.\d{2})?)",
            # Service charges
            r"(?P<name>service\s+charge)\s*[:\-]?\s*(?P<amount>\d+(?:\.\d+)?%|\$[\d,]+(?:\.\d{2})?)",
            # Early/late fees
            r"(?P<name>(?:early\s+check[- ]?in|late\s+check[- ]?out)\s*(?:fee)?)\s*[:\-]?\s*(?P<amount>\$[\d,]+(?:\.\d{2})?)",
            # Cleaning fees
            r"(?P<name>cleaning\s+fee)\s*[:\-]?\s*(?P<amount>\$[\d,]+(?:\.\d{2})?)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.group("name").strip()
                amount = match.group("amount").strip()

                # Determine basis
                basis = "per night"
                context = text[max(0, match.start() - 50):match.end() + 50].lower()
                if "per stay" in context:
                    basis = "per stay"
                elif "per person" in context:
                    basis = "per person"
                elif "per room" in context:
                    basis = "per room"

                # Try to find included items for resort fees
                includes = None
                if "resort" in name.lower() or "amenity" in name.lower():
                    includes = self._extract_fee_includes(text, match.start())

                fees.append(FeeInfo(
                    name=name.title(),
                    amount=amount,
                    basis=basis,
                    includes=includes
                ))

        # Remove duplicates
        seen = set()
        unique_fees = []
        for fee in fees:
            key = (fee.name.lower(), fee.amount)
            if key not in seen:
                seen.add(key)
                unique_fees.append(fee)

        return unique_fees

    def _extract_fee_includes(
        self,
        text: str,
        position: int
    ) -> Optional[List[str]]:
        """Extract what's included in a resort/amenity fee."""
        # Look for bullet points or comma-separated lists after the fee mention
        context = text[position:position + 500]

        # Common included items
        include_keywords = [
            "wifi", "wi-fi", "internet", "pool", "fitness", "gym",
            "breakfast", "parking", "spa", "shuttle", "newspaper",
            "coffee", "water", "resort credit"
        ]

        found = []
        context_lower = context.lower()
        for keyword in include_keywords:
            if keyword in context_lower:
                found.append(keyword.replace("-", " ").title())

        return found if found else None

    def _extract_extra_person_policy(self, text: str) -> Optional[ExtraPersonPolicy]:
        """Extract extra person/child policy information."""
        policy = ExtraPersonPolicy()
        has_data = False

        # Children free age
        match = re.search(
            r"children\s+(?:under|up to)\s+(\d+)\s+(?:stay\s+)?free",
            text,
            re.IGNORECASE
        )
        if match:
            policy.children_free_age = int(match.group(1))
            has_data = True

        # Alternative pattern: "kids 12 and under free"
        match = re.search(
            r"(?:kids|children)\s+(\d+)\s+and\s+under\s+(?:stay\s+)?free",
            text,
            re.IGNORECASE
        )
        if match and not policy.children_free_age:
            policy.children_free_age = int(match.group(1))
            has_data = True

        # Extra adult charge
        match = re.search(
            r"(?:extra|additional)\s+adult\s*[:\-]?\s*\$?([\d,]+(?:\.\d{2})?)",
            text,
            re.IGNORECASE
        )
        if match:
            amount = match.group(1)
            if not amount.startswith("$"):
                amount = f"${amount}"
            policy.adult_charge = {"amount": amount, "basis": "per night"}
            has_data = True

        # Extra child charge
        match = re.search(
            r"(?:extra|additional)\s+child\s*[:\-]?\s*\$?([\d,]+(?:\.\d{2})?)",
            text,
            re.IGNORECASE
        )
        if match:
            amount = match.group(1)
            if not amount.startswith("$"):
                amount = f"${amount}"
            policy.child_charge = {"amount": amount, "basis": "per night"}
            has_data = True

        # Max occupancy
        match = re.search(
            r"(?:maximum|max)\s+occupancy\s*[:\-]?\s*(\d+(?:\s+(?:guests|persons|people))?)",
            text,
            re.IGNORECASE
        )
        if match:
            policy.max_occupancy = match.group(1).strip()
            has_data = True

        return policy if has_data else None

    def _extract_damage_deposit(self, text: str) -> Optional[DamageDeposit]:
        """Extract damage/security deposit information."""
        # Look for damage/security deposit patterns
        patterns = [
            r"(?:damage|security|incidental)\s+deposit\s*[:\-]?\s*\$?([\d,]+(?:\.\d{2})?)",
            r"(?:pre[- ]?authorization|credit\s+card\s+hold)\s*(?:of)?\s*\$?([\d,]+(?:\.\d{2})?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group(1)
                if not amount.startswith("$"):
                    amount = f"${amount}"

                # Determine basis
                context = text[max(0, match.start() - 100):match.end() + 100].lower()
                basis = "per stay"  # Default for deposits
                if "per night" in context:
                    basis = "per night"

                # Look for method
                method = None
                if "credit card" in context or "pre-authorization" in context:
                    method = "Credit card pre-authorization"
                elif "cash" in context:
                    method = "Cash deposit"

                # Look for refund timeline
                refund = None
                refund_match = re.search(
                    r"(?:refund|release)(?:ed)?\s+(?:within)?\s*(\d+)\s*(?:business\s+)?days?",
                    context
                )
                if refund_match:
                    refund = f"Within {refund_match.group(1)} days"

                return DamageDeposit(
                    amount=amount,
                    basis=basis,
                    method=method,
                    refund_timeline=refund
                )

        return None

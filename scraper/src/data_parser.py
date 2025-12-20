"""Data parser module - converts scraped data to the canonical JSON schema."""

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .hotel_finder import HotelInfo
from .policy_scraper import ScrapedPolicy
from .utils import get_logger

logger = get_logger(__name__)


@dataclass
class HotelData:
    """Complete hotel data conforming to the project schema."""
    id: str
    name: str
    town: str
    region: str
    country: str
    market_segment: str
    tripadvisor_rank: int
    coordinates: Optional[Dict[str, float]]
    sources: Dict[str, Optional[str]]
    taxes: List[Dict[str, Any]]
    fees: List[Dict[str, Any]]
    extra_person_policy: Optional[Dict[str, Any]]
    damage_deposit: Optional[Dict[str, Any]]
    promotions: List[Dict[str, Any]]
    scraped_at: str
    scraping_notes: Optional[str]


class DataParser:
    """Parses and validates scraped data into the canonical schema."""

    def __init__(self, datetime_format: str = "%Y-%m-%dT%H:%M:%SZ"):
        self.datetime_format = datetime_format

    def create_hotel_data(
        self,
        hotel_info: HotelInfo,
        scraped_policy: Optional[ScrapedPolicy],
        promotions: Optional[List[Dict[str, Any]]] = None
    ) -> HotelData:
        """
        Create a complete hotel data object from scraped information.

        Args:
            hotel_info: Basic hotel information
            scraped_policy: Scraped policy data (may be None)
            promotions: List of promotions (optional)

        Returns:
            HotelData object conforming to the schema
        """
        hotel_id = self._generate_id(
            hotel_info.country,
            hotel_info.town,
            hotel_info.name
        )

        # Build sources dict
        sources = {
            "officialWebsite": hotel_info.official_website,
            "policyPage": scraped_policy.policy_url if scraped_policy else None,
            "bookingCom": None,  # Will be populated if using Booking.com fallback
            "dataSource": scraped_policy.data_source if scraped_policy else "unknown"
        }

        if scraped_policy and scraped_policy.data_source == "booking.com":
            sources["bookingCom"] = scraped_policy.policy_url

        # Convert taxes
        taxes = []
        if scraped_policy:
            for tax in scraped_policy.taxes:
                taxes.append({
                    "name": tax.name,
                    "amount": tax.amount,
                    "basis": tax.basis,
                    "notes": tax.notes
                })

        # Convert fees
        fees = []
        if scraped_policy:
            for fee in scraped_policy.fees:
                fees.append({
                    "name": fee.name,
                    "amount": fee.amount,
                    "basis": fee.basis,
                    "includes": fee.includes,
                    "notes": fee.notes
                })

        # Convert extra person policy
        extra_person = None
        if scraped_policy and scraped_policy.extra_person_policy:
            epp = scraped_policy.extra_person_policy
            extra_person = {
                "childrenFreeAge": epp.children_free_age,
                "childCharge": epp.child_charge,
                "adultCharge": epp.adult_charge,
                "maxOccupancy": epp.max_occupancy,
                "notes": epp.notes
            }

        # Convert damage deposit
        damage_deposit = None
        if scraped_policy and scraped_policy.damage_deposit:
            dd = scraped_policy.damage_deposit
            damage_deposit = {
                "amount": dd.amount,
                "basis": dd.basis,
                "method": dd.method,
                "refundTimeline": dd.refund_timeline,
                "notes": dd.notes
            }

        # Scraping notes
        notes = None
        if scraped_policy and scraped_policy.scraping_notes:
            notes = scraped_policy.scraping_notes
        elif not scraped_policy:
            notes = "No policy data could be scraped"

        return HotelData(
            id=hotel_id,
            name=hotel_info.name,
            town=hotel_info.town,
            region=hotel_info.region,
            country=hotel_info.country,
            market_segment=hotel_info.market_segment,
            tripadvisor_rank=hotel_info.tripadvisor_rank,
            coordinates=hotel_info.coordinates,
            sources=sources,
            taxes=taxes,
            fees=fees,
            extra_person_policy=extra_person,
            damage_deposit=damage_deposit,
            promotions=promotions or [],
            scraped_at=datetime.utcnow().strftime(self.datetime_format),
            scraping_notes=notes
        )

    def _generate_id(self, country: str, town: str, name: str) -> str:
        """Generate a unique kebab-case ID for a hotel."""
        def slugify(text: str) -> str:
            text = text.lower()
            text = re.sub(r"[^\w\s-]", "", text)
            text = re.sub(r"[-\s]+", "-", text)
            return text.strip("-")

        return f"{slugify(country)}-{slugify(town)}-{slugify(name)}"

    def to_dict(self, hotel_data: HotelData) -> Dict[str, Any]:
        """Convert HotelData to a dictionary matching the JSON schema."""
        return {
            "id": hotel_data.id,
            "name": hotel_data.name,
            "town": hotel_data.town,
            "region": hotel_data.region,
            "country": hotel_data.country,
            "marketSegment": hotel_data.market_segment,
            "tripadvisorRank": hotel_data.tripadvisor_rank,
            "coordinates": hotel_data.coordinates,
            "sources": hotel_data.sources,
            "taxes": hotel_data.taxes,
            "fees": hotel_data.fees,
            "extraPersonPolicy": hotel_data.extra_person_policy,
            "damageDeposit": hotel_data.damage_deposit,
            "promotions": hotel_data.promotions,
            "scrapedAt": hotel_data.scraped_at,
            "scrapingNotes": hotel_data.scraping_notes
        }

    def validate_hotel_data(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate hotel data against the schema.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Required fields
        required_fields = ["id", "name", "town", "region", "country", "marketSegment"]
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")

        # Sources must have policyPage
        if "sources" in data:
            if not data["sources"].get("policyPage"):
                errors.append("Missing required field: sources.policyPage")
        else:
            errors.append("Missing required field: sources")

        # Market segment must be valid
        valid_segments = ["Luxury", "Upscale", "Upper-Midscale", "Midscale", "Economy"]
        if data.get("marketSegment") not in valid_segments:
            errors.append(f"Invalid market segment: {data.get('marketSegment')}")

        # Country must be valid
        valid_countries = ["Canada", "USA", "Switzerland", "France", "Austria", "Australia"]
        if data.get("country") not in valid_countries:
            errors.append(f"Invalid country: {data.get('country')}")

        # Validate taxes structure
        if "taxes" in data and data["taxes"]:
            for i, tax in enumerate(data["taxes"]):
                if not tax.get("name"):
                    errors.append(f"Tax {i} missing name")
                if not tax.get("amount"):
                    errors.append(f"Tax {i} missing amount")

        # Validate fees structure
        if "fees" in data and data["fees"]:
            for i, fee in enumerate(data["fees"]):
                if not fee.get("name"):
                    errors.append(f"Fee {i} missing name")
                if not fee.get("amount"):
                    errors.append(f"Fee {i} missing amount")

        return errors

    def normalize_amount(self, amount: str) -> str:
        """Normalize currency amounts to consistent format."""
        if not amount:
            return amount

        # Remove spaces
        amount = amount.strip()

        # Ensure proper currency symbol format
        if re.match(r"^\d", amount):
            # Amount starts with number, check if percentage
            if "%" not in amount:
                amount = f"${amount}"

        # Normalize decimal places for currency
        match = re.match(r"([\$\€\£])([\d,]+)(?:\.(\d{1,2}))?", amount)
        if match:
            symbol = match.group(1)
            whole = match.group(2)
            decimal = match.group(3) or "00"
            if len(decimal) == 1:
                decimal += "0"
            amount = f"{symbol}{whole}.{decimal}"

        return amount

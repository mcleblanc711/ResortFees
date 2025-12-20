"""LLM-based parser for extracting structured fee data from raw text."""

import json
import os
from typing import Optional

from .policy_scraper import (
    DamageDeposit,
    ExtraPersonPolicy,
    FeeInfo,
    ScrapedPolicy,
    TaxInfo,
)
from .utils import get_logger

logger = get_logger(__name__)

# Extraction prompt for Claude
EXTRACTION_PROMPT = """You are a data extraction assistant. Extract hotel fee and policy information from the provided text.

Return a JSON object with the following structure (use null for missing values, empty arrays for no items):

{
  "taxes": [
    {"name": "Tax Name", "amount": "5%" or "$25.00", "basis": "per night|per stay|per person", "notes": "optional note"}
  ],
  "fees": [
    {"name": "Fee Name", "amount": "$XX.XX", "basis": "per night|per stay|per person", "includes": ["item1", "item2"] or null, "notes": "optional note"}
  ],
  "extraPersonPolicy": {
    "childrenFreeAge": 12 or null,
    "childCharge": {"amount": "$XX.XX", "basis": "per night"} or null,
    "adultCharge": {"amount": "$XX.XX", "basis": "per night"} or null,
    "maxOccupancy": "4 guests" or null,
    "notes": "optional note" or null
  } or null,
  "damageDeposit": {
    "amount": "$XXX.XX",
    "basis": "per stay|per night",
    "method": "Credit card pre-authorization" or null,
    "refundTimeline": "Within 7 days" or null,
    "notes": "optional note" or null
  } or null
}

Look for:
- TAXES: GST, HST, PST, VAT, tourism levy, lodging tax, city tax, occupancy tax
- FEES: Resort fee, destination fee, amenity fee, parking (self/valet), pet fee, cleaning fee, service charge, early check-in, late check-out
- EXTRA PERSON: Children free under age X, extra adult/child charges, rollaway/crib fees, max occupancy
- DAMAGE DEPOSIT: Security deposit, incidental hold, credit card authorization

Important:
- Only extract explicitly stated amounts (don't infer or estimate)
- Use the exact amounts as written (preserve currency symbols)
- If no relevant information is found, return empty arrays/null values
- Return ONLY the JSON object, no other text

Text to analyze:
"""


class LLMParser:
    """Uses Claude to extract structured fee data from raw text."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LLM parser.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None

    @property
    def client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "No API key provided. Set ANTHROPIC_API_KEY environment variable "
                    "or pass api_key to LLMParser."
                )
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package not installed. Run: pip install anthropic"
                )
        return self._client

    def is_available(self) -> bool:
        """Check if LLM parsing is available (API key set)."""
        return bool(self.api_key)

    def parse_policy_text(
        self,
        raw_text: str,
        hotel_name: str,
        max_text_length: int = 15000
    ) -> Optional[dict]:
        """
        Parse raw text to extract structured fee data.

        Args:
            raw_text: Raw text content from the policy page
            hotel_name: Hotel name for logging
            max_text_length: Maximum text length to send to API

        Returns:
            Dictionary with extracted data or None if parsing fails
        """
        if not self.is_available():
            logger.debug("LLM parsing not available (no API key)")
            return None

        # Truncate text if too long
        if len(raw_text) > max_text_length:
            raw_text = raw_text[:max_text_length] + "\n[Text truncated...]"

        # Skip if text is too short to be useful
        if len(raw_text) < 100:
            logger.debug(f"Text too short for {hotel_name}, skipping LLM parsing")
            return None

        try:
            logger.info(f"Using LLM to parse policy text for {hotel_name}")

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": EXTRACTION_PROMPT + raw_text
                    }
                ]
            )

            response_text = message.content[0].text.strip()

            # Parse JSON response
            # Handle potential markdown code blocks
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])

            data = json.loads(response_text)
            logger.info(f"LLM extracted data for {hotel_name}: "
                       f"{len(data.get('taxes', []))} taxes, "
                       f"{len(data.get('fees', []))} fees")
            return data

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON for {hotel_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM parsing error for {hotel_name}: {e}")
            return None

    def enhance_policy(self, policy: ScrapedPolicy, hotel_name: str) -> ScrapedPolicy:
        """
        Enhance a scraped policy with LLM-extracted data.

        Uses LLM parsing to fill in missing data that regex didn't catch.

        Args:
            policy: Existing ScrapedPolicy object
            hotel_name: Hotel name for logging

        Returns:
            Enhanced ScrapedPolicy object
        """
        # Only use LLM if we didn't find data with regex
        if policy.taxes and policy.fees:
            logger.debug(f"Skipping LLM for {hotel_name}, already has data")
            return policy

        llm_data = self.parse_policy_text(policy.raw_text, hotel_name)
        if not llm_data:
            return policy

        # Merge LLM data with existing data (don't overwrite existing)
        if not policy.taxes and llm_data.get("taxes"):
            policy.taxes = [
                TaxInfo(
                    name=t["name"],
                    amount=t["amount"],
                    basis=t.get("basis", "per night"),
                    notes=t.get("notes")
                )
                for t in llm_data["taxes"]
            ]

        if not policy.fees and llm_data.get("fees"):
            policy.fees = [
                FeeInfo(
                    name=f["name"],
                    amount=f["amount"],
                    basis=f.get("basis", "per night"),
                    includes=f.get("includes"),
                    notes=f.get("notes")
                )
                for f in llm_data["fees"]
            ]

        if not policy.extra_person_policy and llm_data.get("extraPersonPolicy"):
            epp = llm_data["extraPersonPolicy"]
            policy.extra_person_policy = ExtraPersonPolicy(
                children_free_age=epp.get("childrenFreeAge"),
                child_charge=epp.get("childCharge"),
                adult_charge=epp.get("adultCharge"),
                max_occupancy=epp.get("maxOccupancy"),
                notes=epp.get("notes")
            )

        if not policy.damage_deposit and llm_data.get("damageDeposit"):
            dd = llm_data["damageDeposit"]
            policy.damage_deposit = DamageDeposit(
                amount=dd["amount"],
                basis=dd.get("basis", "per stay"),
                method=dd.get("method"),
                refund_timeline=dd.get("refundTimeline"),
                notes=dd.get("notes")
            )

        # Update scraping notes
        if policy.taxes or policy.fees:
            policy.scraping_notes = "Data extracted using LLM parsing"

        return policy

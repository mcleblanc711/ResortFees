"""Export module - generates JSON and CSV outputs."""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import get_logger

logger = get_logger(__name__)


class HotelExporter:
    """Exports hotel data to various formats."""

    def __init__(
        self,
        data_dir: str = "data",
        json_indent: int = 2
    ):
        self.data_dir = Path(data_dir)
        self.json_indent = json_indent

        # Ensure directories exist
        self.hotels_dir = self.data_dir / "hotels"
        self.exports_dir = self.data_dir / "exports"
        self.hotels_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def save_hotel(self, hotel_data: Dict[str, Any]) -> Path:
        """
        Save a single hotel to its individual JSON file.

        Args:
            hotel_data: Hotel data dictionary

        Returns:
            Path to the saved file
        """
        # Determine file path based on country and town
        def slugify(text: str) -> str:
            text = text.lower()
            text = re.sub(r"[^\w\s-]", "", text)  # Remove special chars like periods
            text = re.sub(r"[-\s]+", "-", text)   # Replace spaces/dashes with single dash
            return text.strip("-")

        country = slugify(hotel_data["country"])
        town = slugify(hotel_data["town"])
        hotel_slug = hotel_data["id"].split("-", 2)[-1]  # Get hotel name part of ID

        # Map country names to directory names
        country_dirs = {
            "usa": "usa",
            "canada": "canada",
            "switzerland": "europe",
            "france": "europe",
            "austria": "europe",
            "australia": "australia"
        }
        country_dir = country_dirs.get(country, country)

        # Create directory if needed
        hotel_dir = self.hotels_dir / country_dir / town
        hotel_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = hotel_dir / f"{hotel_slug}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(hotel_data, f, indent=self.json_indent, ensure_ascii=False)

        logger.debug(f"Saved hotel data to {file_path}")
        return file_path

    def consolidate_hotels(self) -> Path:
        """
        Consolidate all individual hotel JSON files into one file.

        Returns:
            Path to the consolidated file
        """
        all_hotels = []

        # Walk through all hotel JSON files
        for json_file in self.hotels_dir.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    hotel = json.load(f)
                    all_hotels.append(hotel)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error reading {json_file}: {e}")

        # Sort by country, town, then rank
        all_hotels.sort(key=lambda h: (
            h.get("country", ""),
            h.get("town", ""),
            h.get("tripadvisorRank", 999)
        ))

        # Save consolidated file
        output_path = self.data_dir / "all-hotels.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_hotels, f, indent=self.json_indent, ensure_ascii=False)

        logger.info(f"Consolidated {len(all_hotels)} hotels to {output_path}")
        return output_path

    def export_csv_all(self, hotels: Optional[List[Dict[str, Any]]] = None) -> Path:
        """
        Export all hotels to a single CSV file.

        Args:
            hotels: List of hotel data (will load from consolidated JSON if not provided)

        Returns:
            Path to the CSV file
        """
        if hotels is None:
            consolidated_path = self.data_dir / "all-hotels.json"
            if consolidated_path.exists():
                with open(consolidated_path, "r", encoding="utf-8") as f:
                    hotels = json.load(f)
            else:
                hotels = []

        output_path = self.exports_dir / "hotels-all.csv"
        self._write_csv(hotels, output_path)

        logger.info(f"Exported {len(hotels)} hotels to {output_path}")
        return output_path

    def export_csv_by_country(
        self,
        hotels: Optional[List[Dict[str, Any]]] = None
    ) -> List[Path]:
        """
        Export hotels grouped by country to separate CSV files.

        Args:
            hotels: List of hotel data

        Returns:
            List of paths to CSV files
        """
        if hotels is None:
            consolidated_path = self.data_dir / "all-hotels.json"
            if consolidated_path.exists():
                with open(consolidated_path, "r", encoding="utf-8") as f:
                    hotels = json.load(f)
            else:
                hotels = []

        # Group by country
        by_country: Dict[str, List[Dict[str, Any]]] = {}
        for hotel in hotels:
            country = hotel.get("country", "Unknown")
            if country not in by_country:
                by_country[country] = []
            by_country[country].append(hotel)

        # Export each country
        output_paths = []
        for country, country_hotels in by_country.items():
            country_slug = country.lower().replace(" ", "-")
            output_path = self.exports_dir / f"hotels-{country_slug}.csv"
            self._write_csv(country_hotels, output_path)
            output_paths.append(output_path)
            logger.info(f"Exported {len(country_hotels)} hotels to {output_path}")

        return output_paths

    def _write_csv(self, hotels: List[Dict[str, Any]], output_path: Path) -> None:
        """Write hotels to a CSV file with flattened structure."""
        if not hotels:
            return

        # Define CSV columns (flattened from nested structure)
        fieldnames = [
            "id", "name", "town", "region", "country", "marketSegment",
            "tripadvisorRank", "latitude", "longitude",
            "officialWebsite", "policyPage", "bookingCom", "dataSource",
            "taxCount", "feeCount", "resortFee", "parkingFee",
            "childrenFreeAge", "adultCharge", "damageDeposit",
            "scrapedAt", "scrapingNotes"
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for hotel in hotels:
                # Flatten the hotel data
                coords = hotel.get("coordinates") or {}
                sources = hotel.get("sources") or {}
                extra_person = hotel.get("extraPersonPolicy") or {}
                damage = hotel.get("damageDeposit") or {}

                # Find specific fees
                resort_fee = None
                parking_fee = None
                for fee in hotel.get("fees", []):
                    if "resort" in fee.get("name", "").lower():
                        resort_fee = fee.get("amount")
                    if "parking" in fee.get("name", "").lower():
                        parking_fee = fee.get("amount")

                row = {
                    "id": hotel.get("id"),
                    "name": hotel.get("name"),
                    "town": hotel.get("town"),
                    "region": hotel.get("region"),
                    "country": hotel.get("country"),
                    "marketSegment": hotel.get("marketSegment"),
                    "tripadvisorRank": hotel.get("tripadvisorRank"),
                    "latitude": coords.get("lat"),
                    "longitude": coords.get("lng"),
                    "officialWebsite": sources.get("officialWebsite"),
                    "policyPage": sources.get("policyPage"),
                    "bookingCom": sources.get("bookingCom"),
                    "dataSource": sources.get("dataSource"),
                    "taxCount": len(hotel.get("taxes", [])),
                    "feeCount": len(hotel.get("fees", [])),
                    "resortFee": resort_fee,
                    "parkingFee": parking_fee,
                    "childrenFreeAge": extra_person.get("childrenFreeAge"),
                    "adultCharge": (extra_person.get("adultCharge") or {}).get("amount"),
                    "damageDeposit": damage.get("amount"),
                    "scrapedAt": hotel.get("scrapedAt"),
                    "scrapingNotes": hotel.get("scrapingNotes"),
                }

                writer.writerow(row)

    def copy_to_frontend(self, frontend_data_dir: str = None) -> Path:
        """
        Copy consolidated JSON to the frontend data directory.

        Args:
            frontend_data_dir: Path to frontend data directory (auto-detected if None)

        Returns:
            Path to the copied file
        """
        import shutil

        source = self.data_dir / "all-hotels.json"
        if not source.exists():
            logger.error("Consolidated JSON file not found. Run consolidate_hotels first.")
            raise FileNotFoundError(source)

        # Auto-detect frontend path relative to repo root
        if frontend_data_dir is None:
            repo_root = Path(__file__).parent.parent.parent
            dest_dir = repo_root / "frontend" / "src" / "data"
        else:
            dest_dir = Path(frontend_data_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest = dest_dir / "hotels.json"
        shutil.copy2(source, dest)

        logger.info(f"Copied hotel data to {dest}")
        return dest


def generate_exports(data_dir: str = "data") -> None:
    """
    Generate all export files from existing JSON data.

    This can be run standalone to regenerate exports without re-scraping.
    """
    exporter = HotelExporter(data_dir=data_dir)

    # Consolidate individual JSON files
    exporter.consolidate_hotels()

    # Generate CSVs
    exporter.export_csv_all()
    exporter.export_csv_by_country()

    # Copy to frontend
    try:
        exporter.copy_to_frontend()
    except FileNotFoundError:
        logger.warning("Could not copy to frontend - consolidated file not found")

    logger.info("Export generation complete")


if __name__ == "__main__":
    from .utils import setup_logging
    setup_logging()
    generate_exports()

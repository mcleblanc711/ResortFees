#!/usr/bin/env python3
"""
Hotel Policy Scraper - Main Entry Point

Scrapes tax, fee, and policy information from hotels across resort towns.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

import yaml

from .booking_fallback import BookingFallbackScraper
from .data_parser import DataParser
from .exporters import HotelExporter
from .hotel_finder import HotelFinder, HotelInfo
from .policy_scraper import PolicyScraper
from .utils import RateLimiter, ScrapingReport, get_logger, setup_logging

logger = get_logger(__name__)


def load_config(config_dir: str = "config") -> dict:
    """Load configuration from YAML files."""
    config_path = Path(config_dir)

    # Load scraping config
    scraping_config = {}
    scraping_file = config_path / "scraping.yaml"
    if scraping_file.exists():
        with open(scraping_file, "r") as f:
            scraping_config = yaml.safe_load(f)

    # Load locations
    locations = {}
    locations_file = config_path / "locations.yaml"
    if locations_file.exists():
        with open(locations_file, "r") as f:
            locations = yaml.safe_load(f)

    return {
        "scraping": scraping_config,
        "locations": locations
    }


def get_locations(
    config: dict,
    country_filter: Optional[str] = None,
    town_filter: Optional[str] = None
) -> List[dict]:
    """Get list of locations to scrape based on filters."""
    locations = []

    for region_key, towns in config.get("locations", {}).items():
        for town_data in towns:
            if country_filter and town_data["country"].lower() != country_filter.lower():
                continue
            if town_filter and town_data["town"].lower() != town_filter.lower():
                continue
            locations.append(town_data)

    return locations


def scrape_hotel(
    hotel: HotelInfo,
    policy_scraper: PolicyScraper,
    booking_scraper: BookingFallbackScraper,
    data_parser: DataParser,
    exporter: HotelExporter,
    report: ScrapingReport
) -> Optional[dict]:
    """Scrape a single hotel and save the data."""
    logger.info(f"Processing: {hotel.name} ({hotel.town}, {hotel.country})")

    scraped_policy = None

    # Try official website first
    if hotel.official_website:
        scraped_policy = policy_scraper.scrape_hotel_policies(
            hotel.official_website,
            hotel.name
        )

    # Fall back to Booking.com if needed
    if not scraped_policy:
        logger.info(f"Trying Booking.com fallback for {hotel.name}")
        booking_url = booking_scraper.find_booking_url(
            hotel.name,
            hotel.town,
            hotel.country
        )
        if booking_url:
            scraped_policy = booking_scraper.scrape_hotel_policies(
                booking_url,
                hotel.name
            )

    # Create hotel data object
    hotel_data = data_parser.create_hotel_data(hotel, scraped_policy)
    hotel_dict = data_parser.to_dict(hotel_data)

    # Validate
    errors = data_parser.validate_hotel_data(hotel_dict)
    if errors:
        logger.warning(f"Validation issues for {hotel.name}: {errors}")
        if not scraped_policy:
            report.record_failure(hotel.name, hotel.town, "No policy data scraped")
            return None
        else:
            report.record_partial(hotel.name, hotel.town, "; ".join(errors))
    else:
        report.record_success(hotel.name, hotel.town)

    # Save individual JSON
    exporter.save_hotel(hotel_dict)

    return hotel_dict


def main():
    """Main entry point for the scraper."""
    parser = argparse.ArgumentParser(
        description="Hotel Policy Scraper - Collects tax and fee information from hotels"
    )
    parser.add_argument(
        "--config-dir",
        default="config",
        help="Path to configuration directory"
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Path to data output directory"
    )
    parser.add_argument(
        "--country",
        help="Filter to specific country (e.g., 'Canada')"
    )
    parser.add_argument(
        "--town",
        help="Filter to specific town (e.g., 'Banff')"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List hotels to scrape without actually scraping"
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Only generate exports from existing data"
    )

    args = parser.parse_args()

    # Setup logging
    import logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_dir="logs", log_level=log_level)

    logger.info("Hotel Policy Scraper starting")

    # Load configuration
    config = load_config(args.config_dir)
    scraping_config = config.get("scraping", {})

    # If export-only mode, just generate exports and exit
    if args.export_only:
        from .exporters import generate_exports
        generate_exports(args.data_dir)
        logger.info("Export generation complete")
        return

    # Get locations to process
    locations = get_locations(config, args.country, args.town)
    if not locations:
        logger.error("No locations found matching filters")
        sys.exit(1)

    logger.info(f"Processing {len(locations)} locations")

    # Initialize components
    rate_limit_config = scraping_config.get("rate_limiting", {})
    rate_limiter = RateLimiter(
        min_delay=rate_limit_config.get("min_delay_seconds", 2),
        max_delay=rate_limit_config.get("max_delay_seconds", 4),
        backoff_factor=rate_limit_config.get("backoff_factor", 2),
        max_retries=rate_limit_config.get("max_retries", 3)
    )

    hotels_per_town = scraping_config.get("hotels_per_town", 30)

    # Dry run - just list what would be scraped
    if args.dry_run:
        logger.info("DRY RUN - Hotels that would be processed:")
        with HotelFinder(rate_limiter) as finder:
            for location in locations:
                hotels = finder.find_hotels(
                    location["town"],
                    location["region"],
                    location["country"],
                    limit=hotels_per_town
                )
                for hotel in hotels:
                    print(f"  - {hotel.name} ({location['town']}, {location['country']})")
        return

    # Initialize scrapers and exporters
    report = ScrapingReport()
    report.start()

    data_parser = DataParser()
    exporter = HotelExporter(data_dir=args.data_dir)

    all_hotels = []

    with HotelFinder(rate_limiter) as finder, \
         PolicyScraper(rate_limiter) as policy_scraper, \
         BookingFallbackScraper(rate_limiter) as booking_scraper:

        for location in locations:
            logger.info(f"Processing {location['town']}, {location['country']}")

            # Find hotels for this location
            hotels = finder.find_hotels(
                location["town"],
                location["region"],
                location["country"],
                limit=hotels_per_town
            )

            if not hotels:
                logger.warning(f"No hotels found for {location['town']}")
                continue

            logger.info(f"Found {len(hotels)} hotels in {location['town']}")

            # Scrape each hotel
            for hotel in hotels:
                try:
                    hotel_data = scrape_hotel(
                        hotel,
                        policy_scraper,
                        booking_scraper,
                        data_parser,
                        exporter,
                        report
                    )
                    if hotel_data:
                        all_hotels.append(hotel_data)
                except Exception as e:
                    logger.exception(f"Error scraping {hotel.name}: {e}")
                    report.record_failure(hotel.name, hotel.town, str(e))

    # Generate consolidated outputs
    report.finish()

    if all_hotels:
        exporter.consolidate_hotels()
        exporter.export_csv_all()
        exporter.export_csv_by_country()

        try:
            exporter.copy_to_frontend()
        except FileNotFoundError:
            logger.warning("Could not copy to frontend directory")

    # Print report
    print(report.generate_report())

    # Save report to file
    report_path = Path("logs") / "scraping_report.txt"
    with open(report_path, "w") as f:
        f.write(report.generate_report())

    logger.info("Scraping complete")


if __name__ == "__main__":
    main()

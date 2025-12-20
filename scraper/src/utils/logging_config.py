"""Logging configuration for the scraper."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(
    log_dir: str = "logs",
    log_level: int = logging.INFO,
    console_output: bool = True
) -> None:
    """
    Set up logging configuration with file and optional console output.

    Args:
        log_dir: Directory for log files
        log_level: Logging level
        console_output: Whether to also output to console
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"scraper_{timestamp}.log"

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_formatter = logging.Formatter(
        "%(levelname)-8s | %(message)s"
    )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers = []

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Log startup message
    root_logger.info(f"Logging initialized. Log file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class ScrapingReport:
    """Tracks and reports on scraping results."""

    def __init__(self):
        self.total_hotels = 0
        self.successful = 0
        self.failed = 0
        self.partial = 0  # Hotels with incomplete data
        self.errors: list = []
        self.warnings: list = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def start(self) -> None:
        """Mark the start of scraping."""
        self.start_time = datetime.now()

    def finish(self) -> None:
        """Mark the end of scraping."""
        self.end_time = datetime.now()

    def record_success(self, hotel_name: str, town: str) -> None:
        """Record a successful scrape."""
        self.total_hotels += 1
        self.successful += 1

    def record_failure(self, hotel_name: str, town: str, error: str) -> None:
        """Record a failed scrape."""
        self.total_hotels += 1
        self.failed += 1
        self.errors.append({
            "hotel": hotel_name,
            "town": town,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    def record_partial(self, hotel_name: str, town: str, warning: str) -> None:
        """Record a partial scrape (incomplete data)."""
        self.total_hotels += 1
        self.partial += 1
        self.warnings.append({
            "hotel": hotel_name,
            "town": town,
            "warning": warning,
            "timestamp": datetime.now().isoformat()
        })

    def generate_report(self) -> str:
        """Generate a summary report."""
        duration = ""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            minutes = delta.seconds // 60
            seconds = delta.seconds % 60
            duration = f"Duration: {minutes}m {seconds}s"

        report = f"""
================================================================================
                         HOTEL POLICY SCRAPER REPORT
================================================================================

Summary
-------
Total Hotels Processed: {self.total_hotels}
Successful:            {self.successful}
Partial (incomplete):  {self.partial}
Failed:                {self.failed}

Success Rate: {(self.successful / self.total_hotels * 100) if self.total_hotels > 0 else 0:.1f}%
{duration}

"""
        if self.errors:
            report += "Errors\n------\n"
            for err in self.errors[:20]:  # Limit to first 20
                report += f"  - {err['hotel']} ({err['town']}): {err['error']}\n"
            if len(self.errors) > 20:
                report += f"  ... and {len(self.errors) - 20} more errors\n"
            report += "\n"

        if self.warnings:
            report += "Warnings\n--------\n"
            for warn in self.warnings[:20]:
                report += f"  - {warn['hotel']} ({warn['town']}): {warn['warning']}\n"
            if len(self.warnings) > 20:
                report += f"  ... and {len(self.warnings) - 20} more warnings\n"

        report += "\n================================================================================"
        return report

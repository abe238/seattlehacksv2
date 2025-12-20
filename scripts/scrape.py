#!/usr/bin/env python3
"""
SeattleHacks Event Scraper - Aggregates Seattle tech events from multiple sources.

This is the main scraper script that:
1. Loads event sources from data/sources.json
2. Crawls each source using Crawl4AI (a headless browser automation library)
3. Parses events using source-specific parsers (Lu.ma, Eventbrite, 10times, etc.)
4. Deduplicates events using a hash-based ID
5. Separates future events (events.json) from past events (archive.json)
6. Generates both JSON and iCal outputs for consumption

Architecture:
    sources.json → Scraper → Parsers → Deduplication → events.json + archive.json
                                                     ↓
                                               events.ics (iCal)

For AI Coding Learners:
    - This script uses async/await for concurrent web scraping
    - Each source type has its own parser in the parsers/ directory
    - Events are deduplicated using SHA256 hash of key fields
    - The archive system preserves historical data for analytics
"""

import asyncio
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Crawl4AI is an open-source web scraping library that uses Playwright
# to render JavaScript-heavy pages (like Lu.ma which uses Next.js)
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

# Import our parser factory - each source type (luma, eventbrite, etc.)
# has its own parser class that knows how to extract events from that site's HTML
from parsers import get_parser

# Configure logging to stdout so we can see progress during scraping
# This is especially useful when running via cron or in Docker
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# =============================================================================
# FILE PATHS - All relative to the project root
# =============================================================================
DATA_DIR = Path(__file__).parent.parent / "data"           # Configuration files
DOCS_DATA_DIR = Path(__file__).parent.parent / "docs" / "data"  # Output for GitHub Pages
SOURCES_FILE = DATA_DIR / "sources.json"                   # Event source definitions
EVENTS_FILE = DOCS_DATA_DIR / "events.json"                # Upcoming events (main output)
ARCHIVE_FILE = DOCS_DATA_DIR / "archive.json"              # Past events (for history)
ICAL_FILE = DOCS_DATA_DIR / "events.ics"                   # iCal feed for calendar apps


def generate_event_id(title: str, start_time: str, address: str) -> str:
    """
    Generate a deterministic event ID using SHA256 hash.

    This allows us to identify the same event across multiple scrape runs,
    even if it appears on multiple source sites. Two events with the same
    title, start time, and address are considered duplicates.

    Args:
        title: Event title/name
        start_time: ISO format start datetime
        address: Event location address

    Returns:
        16-character hex string (first 16 chars of SHA256 hash)

    Example:
        >>> generate_event_id("Build Day #4", "2026-01-27T16:00:00", "2801 Alaskan Way")
        'a1b2c3d4e5f6g7h8'
    """
    # Normalize inputs: lowercase and strip whitespace for consistent hashing
    raw = f"{title}{start_time}{address}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def load_sources() -> list[dict]:
    """
    Load event sources from sources.json configuration file.

    Only returns sources where enabled=true (or enabled is not set).
    This allows temporarily disabling sources without removing them.

    Returns:
        List of source configurations, each with:
        - id: Unique identifier (e.g., "luma-aihouse")
        - name: Human-readable name
        - type: Parser type (luma, eventbrite, tentimes, generic)
        - url: URL to scrape
        - tags: Categories for event categorization
    """
    with open(SOURCES_FILE) as f:
        data = json.load(f)
    return [s for s in data["sources"] if s.get("enabled", True)]


def load_existing_events() -> tuple[list[dict], list[dict]]:
    """
    Load existing events from both events.json and archive.json.

    This is called before scraping to:
    1. Preserve events that may have been manually added
    2. Move past events from events.json to archive
    3. Avoid losing historical data

    Returns:
        Tuple of (current_events, archived_events)
    """
    current = []
    archived = []

    # Load current events if file exists
    if EVENTS_FILE.exists():
        try:
            with open(EVENTS_FILE) as f:
                data = json.load(f)
                current = data.get("events", [])
        except (json.JSONDecodeError, KeyError):
            current = []

    # Load archived events if file exists
    if ARCHIVE_FILE.exists():
        try:
            with open(ARCHIVE_FILE) as f:
                data = json.load(f)
                archived = data.get("events", [])
        except (json.JSONDecodeError, KeyError):
            archived = []

    return current, archived


class SeattleHacksScraper:
    """
    Main scraper class that orchestrates the entire scraping process.

    Workflow:
    1. Load existing events and archive
    2. Scrape each enabled source
    3. Parse events using source-specific parsers
    4. Deduplicate across all sources
    5. Separate into future (events.json) and past (archive.json)
    6. Generate iCal feed

    Attributes:
        events: List of all scraped events
        seen_ids: Set of event IDs for deduplication
        sources: List of enabled source configurations
        archive: List of past events to preserve
    """

    def __init__(self):
        """Initialize scraper with empty collections."""
        self.events: list[dict] = []
        self.seen_ids: set[str] = set()
        self.sources = load_sources()
        self.archive: list[dict] = []

    async def scrape_source(self, source: dict) -> list[dict]:
        """
        Scrape a single event source.

        Uses Crawl4AI to:
        1. Navigate to the source URL with a headless browser
        2. Wait for JavaScript to render (important for React/Next.js sites)
        3. Scroll to trigger lazy loading
        4. Extract the rendered HTML
        5. Pass HTML to the appropriate parser

        Args:
            source: Source configuration dict with url, type, name, tags

        Returns:
            List of parsed event dictionaries
        """
        logger.info(f"Scraping {source['name']} ({source['type']})")

        # Configure the crawler:
        # - BYPASS cache to always get fresh data
        # - Execute JS to scroll and wait (triggers lazy loading)
        # - 60 second timeout for slow-loading sites
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code="""
                // Scroll to bottom to trigger lazy loading of event cards
                window.scrollTo(0, document.body.scrollHeight);
                // Wait 2 seconds for content to load
                await new Promise(r => setTimeout(r, 2000));
            """,
            page_timeout=60000,
        )

        try:
            # AsyncWebCrawler manages a headless browser instance
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=source["url"], config=config)

                if not result.success:
                    logger.warning(f"Failed to crawl {source['url']}: {result.error_message}")
                    return []

                # Get the appropriate parser based on source type
                # e.g., "luma" → LumaParser, "tentimes" → TenTimesParser
                parser_class = get_parser(source["type"])
                parser = parser_class()

                # Parse the HTML into event dictionaries
                events = parser.parse(result, source)

                logger.info(f"  Found {len(events)} events from {source['name']}")
                return events

        except Exception as e:
            logger.error(f"Error scraping {source['name']}: {e}")
            return []

    def deduplicate_event(self, event: dict) -> bool:
        """
        Check if event is a duplicate and add ID if not.

        Uses the generate_event_id function to create a deterministic ID
        based on title, start time, and address. If we've seen this ID
        before, the event is a duplicate.

        Args:
            event: Event dictionary (will be mutated to add 'id' field)

        Returns:
            True if event is new, False if duplicate
        """
        event_id = generate_event_id(
            event.get("title", ""),
            event.get("startTime", ""),
            event.get("location", {}).get("address", "")
        )
        event["id"] = event_id

        if event_id in self.seen_ids:
            return False

        self.seen_ids.add(event_id)
        return True

    def separate_past_events(self) -> list[dict]:
        """
        Separate past events from current events.

        Past events (startTime < now) are moved to the archive.
        Only future events remain in self.events.

        Returns:
            List of past events to be archived
        """
        now = datetime.now(timezone.utc)
        past_events = []
        future_events = []

        for event in self.events:
            if self._parse_time(event.get("startTime", "")) <= now:
                past_events.append(event)
            else:
                future_events.append(event)

        self.events = future_events
        return past_events

    def _parse_time(self, time_str: str) -> datetime:
        """
        Parse ISO format datetime string to datetime object.

        Handles various formats:
        - "2025-01-27T16:00:00-08:00" (with timezone)
        - "2025-01-27T16:00:00Z" (UTC)
        - "2025-01-27T16:00:00" (naive, treated as UTC)

        Args:
            time_str: ISO format datetime string

        Returns:
            Timezone-aware datetime object (UTC if no timezone specified)
        """
        try:
            # Replace 'Z' with explicit UTC offset for fromisoformat
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            # Ensure timezone-aware (naive datetimes get UTC)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, AttributeError):
            # Return minimum datetime for invalid/missing dates
            # This ensures they sort to the beginning
            return datetime.min.replace(tzinfo=timezone.utc)

    def sort_events(self) -> None:
        """Sort events by start time, earliest first."""
        self.events.sort(key=lambda e: self._parse_time(e.get("startTime", "")))

    async def run(self) -> None:
        """
        Main entry point - orchestrates the entire scraping process.

        Steps:
        1. Load existing events and archive (preserves historical data)
        2. Move any past events from existing events to archive
        3. Scrape all enabled sources
        4. Deduplicate new events
        5. Separate past events from scraped events
        6. Merge with archive (with deduplication)
        7. Write outputs (JSON, iCal)
        """
        logger.info(f"Starting scrape of {len(self.sources)} sources")

        # Load existing data to preserve history
        existing_events, existing_archive = load_existing_events()

        # Add existing archived events to our archive
        self.archive = existing_archive
        archive_ids = {e.get("id") for e in self.archive}

        # Move past events from existing events to archive
        now = datetime.now(timezone.utc)
        for event in existing_events:
            event_id = event.get("id")
            if self._parse_time(event.get("startTime", "")) <= now:
                # Past event - add to archive if not already there
                if event_id and event_id not in archive_ids:
                    self.archive.append(event)
                    archive_ids.add(event_id)
            else:
                # Future event - preserve it AND add to seen_ids
                if event_id:
                    self.seen_ids.add(event_id)
                    self.events.append(event)

        # Scrape each enabled source
        for source in self.sources:
            events = await self.scrape_source(source)
            for event in events:
                if self.deduplicate_event(event):
                    self.events.append(event)

        # Separate any past events from newly scraped data
        new_past_events = self.separate_past_events()

        # Add new past events to archive (with deduplication)
        for event in new_past_events:
            event_id = event.get("id")
            if event_id and event_id not in archive_ids:
                self.archive.append(event)
                archive_ids.add(event_id)

        # Sort by date
        self.sort_events()
        self.archive.sort(key=lambda e: self._parse_time(e.get("startTime", "")), reverse=True)

        logger.info(f"Total unique future events: {len(self.events)}")
        logger.info(f"Total archived events: {len(self.archive)}")

        # Ensure output directory exists
        DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Write all outputs
        self.write_json()
        self.write_archive()
        self.write_ical()

    def write_json(self) -> None:
        """
        Write upcoming events to events.json.

        Output format includes metadata for the frontend:
        - version: API version for compatibility
        - generatedAt: Timestamp for cache invalidation
        - eventCount: Total count for display
        - events: Array of event objects
        """
        output = {
            "version": "1.0",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "eventCount": len(self.events),
            "events": self.events
        }

        with open(EVENTS_FILE, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Wrote {len(self.events)} events to {EVENTS_FILE}")

    def write_archive(self) -> None:
        """
        Write past events to archive.json.

        The archive preserves historical data for:
        - Analytics (which events were popular)
        - Historical browsing
        - Data integrity (no lost events)
        """
        output = {
            "version": "1.0",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "eventCount": len(self.archive),
            "events": self.archive
        }

        with open(ARCHIVE_FILE, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Wrote {len(self.archive)} events to {ARCHIVE_FILE}")

    def write_ical(self) -> None:
        """
        Generate iCal feed for calendar app subscriptions.

        Users can subscribe to events.ics in Google Calendar, Apple Calendar,
        Outlook, etc. to automatically see SeattleHacks events.

        Uses the icalendar library to generate RFC 5545 compliant output.
        """
        try:
            from icalendar import Calendar, Event as ICalEvent
        except ImportError:
            logger.warning("icalendar not installed, skipping iCal generation")
            return

        # Create calendar with metadata
        cal = Calendar()
        cal.add("prodid", "-//SeattleHacks//seattlehacks.com//EN")
        cal.add("version", "2.0")
        cal.add("x-wr-calname", "SeattleHacks Events")

        # Add each event to the calendar
        for event in self.events:
            ical_event = ICalEvent()
            ical_event.add("uid", f"{event['id']}@seattlehacks.com")
            ical_event.add("summary", event.get("title", ""))

            # Add start/end times if valid
            start = self._parse_time(event.get("startTime", ""))
            end = self._parse_time(event.get("endTime", ""))
            if start != datetime.min.replace(tzinfo=timezone.utc):
                ical_event.add("dtstart", start)
            if end != datetime.min.replace(tzinfo=timezone.utc):
                ical_event.add("dtend", end)

            # Add location if available
            loc = event.get("location", {})
            if loc.get("address"):
                ical_event.add("location", loc["address"])

            # Add URL and description
            ical_event.add("url", event.get("sourceUrl", ""))
            ical_event.add("description", f"Organizer: {event.get('organizer', 'Unknown')}")

            cal.add_component(ical_event)

        # Write binary iCal output
        with open(ICAL_FILE, "wb") as f:
            f.write(cal.to_ical())

        logger.info(f"Wrote {len(self.events)} events to {ICAL_FILE}")


async def main():
    """Entry point for the scraper."""
    scraper = SeattleHacksScraper()
    await scraper.run()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

#!/usr/bin/env python3
"""SeattleHacks Event Scraper - Aggregates Seattle tech events from multiple sources."""

import asyncio
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

from parsers import get_parser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
SOURCES_FILE = DATA_DIR / "sources.json"
EVENTS_FILE = DATA_DIR / "events.json"
ICAL_FILE = DATA_DIR / "events.ics"


def generate_event_id(title: str, start_time: str, address: str) -> str:
    raw = f"{title}{start_time}{address}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def load_sources() -> list[dict]:
    with open(SOURCES_FILE) as f:
        data = json.load(f)
    return [s for s in data["sources"] if s.get("enabled", True)]


class SeattleHacksScraper:
    def __init__(self):
        self.events: list[dict] = []
        self.seen_ids: set[str] = set()
        self.sources = load_sources()

    async def scrape_source(self, source: dict) -> list[dict]:
        logger.info(f"Scraping {source['name']} ({source['type']})")

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code="window.scrollTo(0, document.body.scrollHeight);",
            wait_for="networkidle",
            page_timeout=30000,
        )

        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=source["url"], config=config)

                if not result.success:
                    logger.warning(f"Failed to crawl {source['url']}: {result.error_message}")
                    return []

                parser_class = get_parser(source["type"])
                parser = parser_class()
                events = parser.parse(result, source)

                logger.info(f"  Found {len(events)} events from {source['name']}")
                return events

        except Exception as e:
            logger.error(f"Error scraping {source['name']}: {e}")
            return []

    def deduplicate_event(self, event: dict) -> bool:
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

    def filter_future_events(self) -> None:
        now = datetime.now(timezone.utc)
        self.events = [
            e for e in self.events
            if self._parse_time(e.get("startTime", "")) > now
        ]

    def _parse_time(self, time_str: str) -> datetime:
        try:
            return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.min.replace(tzinfo=timezone.utc)

    def sort_events(self) -> None:
        self.events.sort(key=lambda e: self._parse_time(e.get("startTime", "")))

    async def run(self) -> None:
        logger.info(f"Starting scrape of {len(self.sources)} sources")

        for source in self.sources:
            events = await self.scrape_source(source)
            for event in events:
                if self.deduplicate_event(event):
                    self.events.append(event)

        self.filter_future_events()
        self.sort_events()

        logger.info(f"Total unique future events: {len(self.events)}")

        self.write_json()
        self.write_ical()

    def write_json(self) -> None:
        output = {
            "version": "1.0",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "eventCount": len(self.events),
            "events": self.events
        }

        with open(EVENTS_FILE, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Wrote {len(self.events)} events to {EVENTS_FILE}")

    def write_ical(self) -> None:
        try:
            from icalendar import Calendar, Event as ICalEvent
        except ImportError:
            logger.warning("icalendar not installed, skipping iCal generation")
            return

        cal = Calendar()
        cal.add("prodid", "-//SeattleHacks//seattlehacks.com//EN")
        cal.add("version", "2.0")
        cal.add("x-wr-calname", "SeattleHacks Events")

        for event in self.events:
            ical_event = ICalEvent()
            ical_event.add("uid", f"{event['id']}@seattlehacks.com")
            ical_event.add("summary", event.get("title", ""))

            start = self._parse_time(event.get("startTime", ""))
            end = self._parse_time(event.get("endTime", ""))
            if start != datetime.min.replace(tzinfo=timezone.utc):
                ical_event.add("dtstart", start)
            if end != datetime.min.replace(tzinfo=timezone.utc):
                ical_event.add("dtend", end)

            loc = event.get("location", {})
            if loc.get("address"):
                ical_event.add("location", loc["address"])

            ical_event.add("url", event.get("sourceUrl", ""))
            ical_event.add("description", f"Organizer: {event.get('organizer', 'Unknown')}")

            cal.add_component(ical_event)

        with open(ICAL_FILE, "wb") as f:
            f.write(cal.to_ical())

        logger.info(f"Wrote {len(self.events)} events to {ICAL_FILE}")


async def main():
    scraper = SeattleHacksScraper()
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())

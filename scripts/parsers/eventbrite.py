"""Eventbrite event parser - extracts events from Eventbrite organizer pages."""

import json
import re
from typing import Any


class EventbriteParser:
    def parse(self, result: Any, source: dict) -> list[dict]:
        events = []
        html = result.html or ""

        json_ld_matches = re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html,
            re.DOTALL | re.IGNORECASE
        )

        for match in json_ld_matches:
            try:
                data = json.loads(match.strip())
                if isinstance(data, list):
                    for item in data:
                        event = self._parse_event(item, source)
                        if event:
                            events.append(event)
                elif isinstance(data, dict):
                    if data.get("@type") == "Event":
                        event = self._parse_event(data, source)
                        if event:
                            events.append(event)
            except json.JSONDecodeError:
                continue

        if not events:
            events = self._parse_html_fallback(html, source)

        return events

    def _parse_event(self, data: dict, source: dict) -> dict | None:
        if data.get("@type") != "Event":
            return None

        title = data.get("name", "")
        if not title:
            return None

        location = data.get("location", {})
        loc_data = {"name": "", "address": "", "city": "Seattle"}

        if isinstance(location, dict):
            loc_data["name"] = location.get("name", "")
            address = location.get("address", {})
            if isinstance(address, dict):
                street = address.get("streetAddress", "")
                city = address.get("addressLocality", "Seattle")
                state = address.get("addressRegion", "WA")
                postal = address.get("postalCode", "")
                loc_data["address"] = f"{street}, {city}, {state} {postal}".strip(", ")
                loc_data["city"] = city
            elif isinstance(address, str):
                loc_data["address"] = address

        offers = data.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price = 0
        if isinstance(offers, dict):
            low = offers.get("lowPrice", offers.get("price", 0))
            price = float(low) if low else 0
        cost_type = "free" if price == 0 else "paid"

        return {
            "title": title,
            "organizer": data.get("organizer", {}).get("name", source.get("name", "")),
            "category": self._categorize(title, source.get("tags", [])),
            "startTime": data.get("startDate", ""),
            "endTime": data.get("endDate", ""),
            "location": loc_data,
            "cost": {"type": cost_type, "amount": price if cost_type == "paid" else None},
            "sourceUrl": data.get("url", source.get("url", "")),
            "sourceId": source.get("id", "")
        }

    def _parse_html_fallback(self, html: str, source: dict) -> list[dict]:
        events = []

        event_links = re.findall(
            r'href="(https://www\.eventbrite\.com/e/[^"]+)"[^>]*>\s*<[^>]+>([^<]+)',
            html
        )

        for url, title in event_links[:10]:
            title = title.strip()
            if title and len(title) > 5:
                events.append({
                    "title": title,
                    "organizer": source.get("name", ""),
                    "category": self._categorize(title, source.get("tags", [])),
                    "startTime": "",
                    "endTime": "",
                    "location": {"name": "", "address": "", "city": "Seattle"},
                    "cost": {"type": "free", "amount": None},
                    "sourceUrl": url.split("?")[0],
                    "sourceId": source.get("id", "")
                })

        return events

    def _categorize(self, title: str, tags: list) -> str:
        title_lower = title.lower()

        if any(w in title_lower for w in ["summit", "conference", "forum"]):
            return "conference"
        if any(w in title_lower for w in ["hackathon", "hack"]):
            return "hackathon"
        if any(w in title_lower for w in ["ai", "ml", "machine learning"]):
            return "ai"
        if any(w in title_lower for w in ["workshop", "bootcamp"]):
            return "workshop"

        if "conference" in tags or "tech" in tags:
            return "conference"

        return "networking"

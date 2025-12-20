"""Meetup event parser - extracts events from Meetup group pages."""

import json
import re
from typing import Any


class MeetupParser:
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
            if location.get("@type") == "Place":
                loc_data["name"] = location.get("name", "")
                address = location.get("address", {})
                if isinstance(address, dict):
                    street = address.get("streetAddress", "")
                    city = address.get("addressLocality", "Seattle")
                    state = address.get("addressRegion", "WA")
                    loc_data["address"] = f"{street}, {city}, {state}".strip(", ")
                    loc_data["city"] = city
            elif location.get("@type") == "VirtualLocation":
                loc_data["name"] = "Online"
                loc_data["address"] = location.get("url", "Online")

        offers = data.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price = 0
        if isinstance(offers, dict):
            price = offers.get("price", 0)
        cost_type = "free" if price == 0 or price == "0" else "paid"

        return {
            "title": title,
            "organizer": data.get("organizer", {}).get("name", source.get("name", "")),
            "category": self._categorize(title, source.get("tags", [])),
            "startTime": data.get("startDate", ""),
            "endTime": data.get("endDate", ""),
            "location": loc_data,
            "cost": {"type": cost_type, "amount": float(price) if cost_type == "paid" else None},
            "sourceUrl": data.get("url", source.get("url", "")),
            "sourceId": source.get("id", "")
        }

    def _parse_html_fallback(self, html: str, source: dict) -> list[dict]:
        events = []

        event_links = re.findall(
            r'href="(https://www\.meetup\.com/[^/]+/events/\d+[^"]*)"[^>]*>([^<]+)',
            html
        )

        for url, title in event_links[:10]:
            if title.strip():
                events.append({
                    "title": title.strip(),
                    "organizer": source.get("name", ""),
                    "category": self._categorize(title, source.get("tags", [])),
                    "startTime": "",
                    "endTime": "",
                    "location": {"name": "", "address": "", "city": "Seattle"},
                    "cost": {"type": "free", "amount": None},
                    "sourceUrl": url,
                    "sourceId": source.get("id", "")
                })

        return events

    def _categorize(self, title: str, tags: list) -> str:
        title_lower = title.lower()

        if any(w in title_lower for w in ["hackathon", "hack night"]):
            return "hackathon"
        if any(w in title_lower for w in ["ai", "ml", "machine learning", "llm"]):
            return "ai"
        if any(w in title_lower for w in ["workshop", "tutorial", "hands-on"]):
            return "workshop"

        if "python" in tags or "javascript" in tags or "rust" in tags or "go" in tags:
            return "workshop"

        return "networking"

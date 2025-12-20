"""Lu.ma event parser - extracts events from Lu.ma calendar pages."""

import json
import re
from typing import Any


class LumaParser:
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
                    elif data.get("@type") == "ItemList":
                        for item in data.get("itemListElement", []):
                            if item.get("@type") == "Event":
                                event = self._parse_event(item, source)
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
        if isinstance(location, dict):
            loc_data = {
                "name": location.get("name", ""),
                "address": "",
                "city": "Seattle"
            }
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
        else:
            loc_data = {"name": str(location), "address": "", "city": "Seattle"}

        offers = data.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price = offers.get("price", 0) if isinstance(offers, dict) else 0
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
        event_blocks = re.findall(
            r'data-event-id="([^"]+)".*?class="[^"]*event-title[^"]*"[^>]*>([^<]+)',
            html,
            re.DOTALL
        )

        for event_id, title in event_blocks:
            events.append({
                "title": title.strip(),
                "organizer": source.get("name", ""),
                "category": self._categorize(title, source.get("tags", [])),
                "startTime": "",
                "endTime": "",
                "location": {"name": "", "address": "", "city": "Seattle"},
                "cost": {"type": "free", "amount": None},
                "sourceUrl": f"https://lu.ma/{event_id}",
                "sourceId": source.get("id", "")
            })

        return events

    def _categorize(self, title: str, tags: list) -> str:
        title_lower = title.lower()

        if any(w in title_lower for w in ["hackathon", "hack day", "build day"]):
            return "hackathon"
        if any(w in title_lower for w in ["ai", "ml", "machine learning", "llm", "gpt"]):
            return "ai"
        if any(w in title_lower for w in ["workshop", "tutorial", "hands-on", "lab"]):
            return "workshop"
        if any(w in title_lower for w in ["meetup", "mixer", "happy hour", "social"]):
            return "networking"

        if "ai" in tags:
            return "ai"
        if "hackathon" in tags:
            return "hackathon"
        if "workshop" in tags:
            return "workshop"

        return "networking"

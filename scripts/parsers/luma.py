"""Lu.ma event parser - extracts events from Lu.ma calendar pages via __NEXT_DATA__."""

import json
import re
from typing import Any


class LumaParser:
    def parse(self, result: Any, source: dict) -> list[dict]:
        events = []
        html = result.html or ""

        next_data = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            html,
            re.DOTALL
        )

        if next_data:
            try:
                data = json.loads(next_data.group(1))
                initial_data = data.get("props", {}).get("pageProps", {}).get("initialData", {}).get("data", {})
                featured_items = initial_data.get("featured_items", [])

                for item in featured_items:
                    event = self._parse_featured_item(item, source)
                    if event:
                        events.append(event)
            except (json.JSONDecodeError, KeyError):
                pass

        return events

    def _parse_featured_item(self, item: dict, source: dict) -> dict | None:
        event_data = item.get("event", {})
        if not event_data:
            return None

        title = event_data.get("name", "")
        if not title:
            return None

        geo_info = event_data.get("geo_address_info", {})
        address_json = event_data.get("geo_address_json", {})

        loc_data = {
            "name": geo_info.get("place_name", ""),
            "address": address_json.get("full_address", geo_info.get("address", "")),
            "city": geo_info.get("city", "Seattle")
        }

        ticket_info = item.get("ticket_info", {})
        price = ticket_info.get("price_cents", 0) or 0
        cost_type = "free" if price == 0 else "paid"

        event_url = event_data.get("url", "")
        full_url = f"https://lu.ma/{event_url}" if event_url else source.get("url", "")

        hosts = item.get("hosts", [])
        organizer = hosts[0].get("name", source.get("name", "")) if hosts else source.get("name", "")

        return {
            "title": title,
            "organizer": organizer,
            "category": self._categorize(title, source.get("tags", [])),
            "startTime": event_data.get("start_at", ""),
            "endTime": event_data.get("end_at", ""),
            "location": loc_data,
            "cost": {"type": cost_type, "amount": price / 100 if cost_type == "paid" else None},
            "sourceUrl": full_url,
            "sourceId": source.get("id", "")
        }

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

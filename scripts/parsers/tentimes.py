"""10times.com event parser - extracts events from 10times event listings."""

import json
import re
from typing import Any


class TenTimesParser:
    def parse(self, result: Any, source: dict) -> list[dict]:
        events = []
        html = result.html or ""

        json_ld = re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html,
            re.DOTALL
        )

        for block in json_ld:
            try:
                data = json.loads(block.strip())
                items_to_process = [data] if isinstance(data, dict) else data
                for obj in items_to_process:
                    if not isinstance(obj, dict):
                        continue
                    if obj.get('@type') == 'ItemList':
                        for item in obj.get('itemListElement', []):
                            event = self._parse_item(item.get('item', {}), source)
                            if event:
                                events.append(event)
                    elif obj.get('@type') == 'Event':
                        event = self._parse_item(obj, source)
                        if event:
                            events.append(event)
            except json.JSONDecodeError:
                continue

        return events

    def _parse_item(self, item: dict, source: dict) -> dict | None:
        if not item.get('name'):
            return None

        location = item.get('location', {})
        if isinstance(location, list):
            location = location[0] if location else {}
        address = location.get('address', {}) if isinstance(location, dict) else {}
        if isinstance(address, list):
            address = address[0] if address else {}
        if isinstance(address, str):
            address = {"streetAddress": address}

        loc_data = {
            "name": location.get('name', '') if isinstance(location, dict) else '',
            "address": address.get('streetAddress', '') if isinstance(address, dict) else str(address),
            "city": address.get('addressLocality', 'Seattle') if isinstance(address, dict) else 'Seattle'
        }

        organizer = item.get('organizer', {})
        if isinstance(organizer, list):
            organizer = organizer[0] if organizer else {}
        org_name = organizer.get('name', source.get('name', '')) if isinstance(organizer, dict) else source.get('name', '')

        return {
            "title": item.get('name', ''),
            "organizer": org_name,
            "category": self._categorize(item.get('name', ''), source.get('tags', [])),
            "startTime": item.get('startDate', ''),
            "endTime": item.get('endDate', ''),
            "location": loc_data,
            "cost": {"type": "free", "amount": None},
            "sourceUrl": item.get('url', source.get('url', '')),
            "sourceId": source.get('id', '')
        }

    def _categorize(self, title: str, tags: list) -> str:
        title_lower = title.lower()

        if any(w in title_lower for w in ["hackathon", "hack"]):
            return "hackathon"
        if any(w in title_lower for w in ["ai", "ml", "machine learning", "data science"]):
            return "ai"
        if any(w in title_lower for w in ["workshop", "training", "course", "masterclass"]):
            return "workshop"
        if any(w in title_lower for w in ["conference", "summit", "expo"]):
            return "conference"
        if any(w in title_lower for w in ["meetup", "networking", "social"]):
            return "networking"

        return "conference"

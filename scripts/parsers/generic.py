"""Generic event parser - fallback for sites without structured data."""

import re
from typing import Any


class GenericParser:
    def parse(self, result: Any, source: dict) -> list[dict]:
        events = []
        html = result.html or ""
        markdown = result.markdown or ""

        events = self._parse_event_patterns(html, markdown, source)

        return events

    def _parse_event_patterns(self, html: str, markdown: str, source: dict) -> list[dict]:
        events = []

        event_patterns = [
            r'class="[^"]*event[^"]*"[^>]*>.*?<[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)',
            r'<h[23][^>]*class="[^"]*event[^"]*"[^>]*>([^<]+)',
            r'<a[^>]*href="([^"]+)"[^>]*class="[^"]*event[^"]*"[^>]*>([^<]+)',
        ]

        for pattern in event_patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for match in matches[:5]:
                title = match[-1] if isinstance(match, tuple) else match
                title = title.strip()
                if title and len(title) > 3 and len(title) < 200:
                    url = match[0] if isinstance(match, tuple) and len(match) > 1 else source.get("url", "")
                    events.append(self._create_event(title, url, source))

        if not events and markdown:
            events = self._parse_markdown(markdown, source)

        return events

    def _parse_markdown(self, markdown: str, source: dict) -> list[dict]:
        events = []

        lines = markdown.split("\n")
        for line in lines:
            if re.match(r'^#+\s+', line):
                title = re.sub(r'^#+\s+', '', line).strip()
                if self._looks_like_event(title):
                    events.append(self._create_event(title, source.get("url", ""), source))
                    if len(events) >= 10:
                        break

        return events

    def _looks_like_event(self, title: str) -> bool:
        if len(title) < 5 or len(title) > 150:
            return False

        event_keywords = [
            "meetup", "event", "workshop", "talk", "demo", "hackathon",
            "conference", "summit", "mixer", "social", "session"
        ]
        title_lower = title.lower()
        return any(kw in title_lower for kw in event_keywords)

    def _create_event(self, title: str, url: str, source: dict) -> dict:
        return {
            "title": title,
            "organizer": source.get("name", ""),
            "category": self._categorize(title, source.get("tags", [])),
            "startTime": "",
            "endTime": "",
            "location": {"name": "", "address": "", "city": "Seattle"},
            "cost": {"type": "free", "amount": None},
            "sourceUrl": url,
            "sourceId": source.get("id", "")
        }

    def _categorize(self, title: str, tags: list) -> str:
        title_lower = title.lower()

        if any(w in title_lower for w in ["hackathon", "hack day"]):
            return "hackathon"
        if any(w in title_lower for w in ["ai", "ml", "machine learning"]):
            return "ai"
        if any(w in title_lower for w in ["workshop", "tutorial", "demo"]):
            return "workshop"

        if tags:
            return tags[0]

        return "networking"

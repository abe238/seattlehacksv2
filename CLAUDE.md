# CLAUDE.md - SeattleHacks v2

Seattle Tech Events Aggregator with automated scraping and GitHub Pages frontend.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GITHUB PAGES                              │
│  docs/index.html → Tailwind dark theme, event filters           │
│  docs/app.js → fetch events.json, render cards                  │
│  data/events.json → generated event data                        │
│  data/events.ics → iCal subscription feed                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │ git push (weekly)
┌───────────────────────────┴─────────────────────────────────────┐
│                    VPS (72.60.28.52)                            │
│  scripts/scrape.py → Crawl4AI main scraper                      │
│  scripts/parsers/*.py → Platform-specific parsers               │
│  data/sources.json → Curated source configuration               │
│  run-scraper.sh → Cron entry point                              │
│  Cron: Sunday 10pm PST (Monday 6am UTC)                         │
└─────────────────────────────────────────────────────────────────┘
```

## Event Schema

```json
{
  "id": "a1b2c3d4e5f6",
  "title": "Build Day #4",
  "organizer": "AI2 Incubator",
  "category": "hackathon|ai|networking|workshop",
  "startTime": "2026-01-27T16:00:00-08:00",
  "endTime": "2026-01-27T18:00:00-08:00",
  "location": {
    "name": "AI House",
    "address": "2801 Alaskan Way, Seattle, WA 98121",
    "city": "Seattle"
  },
  "cost": {"type": "free|paid", "amount": null},
  "sourceUrl": "https://luma.com/1z8sj980",
  "sourceId": "luma-aihouse"
}
```

## Source Types

| Type | URL Pattern | Data Format |
|------|-------------|-------------|
| luma | luma.com/{calendar}?k=c | JSON-LD structured data |
| meetup | meetup.com/{group}/events/ | Schema.org |
| eventbrite | eventbrite.com/o/{org} | Schema.org |
| generic | any | CSS selector fallback |

## Commands

```bash
# Development
python3 -m venv venv && source venv/bin/activate
pip install crawl4ai icalendar
crawl4ai-setup  # Install Playwright browsers

# Run scraper locally
python scripts/scrape.py

# View tasks
task-master list
task-master next

# Deploy
git push origin main  # Triggers GitHub Pages
```

## Directory Structure

```
seattlehacksv2/
├── CLAUDE.md
├── data/
│   ├── sources.json      # Curated event sources
│   ├── events.json       # Generated: all events
│   └── events.ics        # Generated: iCal feed
├── docs/                  # GitHub Pages root
│   ├── index.html        # Main page
│   └── app.js            # Frontend logic
├── scripts/
│   ├── scrape.py         # Main scraper
│   └── parsers/
│       ├── __init__.py
│       ├── luma.py
│       ├── meetup.py
│       ├── eventbrite.py
│       └── generic.py
├── run-scraper.sh        # VPS cron script
├── setup.sh              # VPS one-time setup
└── logs/                 # Scrape logs
```

## VPS Deployment

```bash
# One-time setup on VPS
ssh hostinger-vps-auto
cd /var/www && git clone git@github.com:abe238/seattlehacksv2.git seattlehacks
cd seattlehacks && ./setup.sh

# Cron entry (run as root)
# 0 6 * * 1 /var/www/seattlehacks/run-scraper.sh
```

## Event ID Generation

Deterministic IDs using SHA256 hash of normalized key fields:
```python
raw = f"{title}{start_time}{address}".lower().strip()
event_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
```

## Deduplication

Events matched by ID across sources. If same event on multiple sources, keep first encountered. sources.json order determines priority.

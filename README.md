# SeattleHacks v2

**Seattle Tech Events Aggregator** - Automated event scraping reigniting what [crtr0/seattlehacks](https://github.com/crtr0/seattlehacks) had built.

This project aggregates Seattle tech events from multiple sources into a single, fast-loading website with calendar subscription support. It's also designed as an **educational resource for learning AI-assisted coding**.

**Live Site:** [seattlehacks.com](https://abe238.github.io/seattlehacksv2/)

---

## The Story

Back in the day, [crtr0/seattlehacks](https://github.com/crtr0/seattlehacks) was the go-to resource for Seattle's tech community to discover local events. It aggregated hackathons, meetups, and tech gatherings in one place.

This project reignites that mission with modern tools:
- **AI-assisted development** using Claude Code
- **Automated web scraping** with Crawl4AI (handles JavaScript-heavy sites)
- **Zero-cost hosting** via GitHub Pages
- **Calendar integration** with iCal feeds

The entire codebase is documented for learners who want to build similar projects using AI coding assistants.

---

## Features

- **Multi-source aggregation**: Lu.ma, Meetup, Eventbrite, 10times, and more
- **Smart deduplication**: Same event on multiple sites? We only show it once
- **Category filtering**: Hackathons, AI/ML, Workshops, Networking, Conferences
- **Calendar subscription**: Subscribe in Google Calendar, Apple Calendar, Outlook
- **Archive system**: Past events preserved for historical browsing
- **Dark theme**: Easy on the eyes, developer-friendly aesthetic
- **Fast loading**: Optimized for performance with minimal dependencies

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     GITHUB PAGES (Frontend)                      │
│  docs/index.html    → Tailwind dark theme, event filters        │
│  docs/archive.html  → Past events browsing                      │
│  docs/app.js        → Fetch events.json, render cards           │
│  docs/data/         → Generated JSON + iCal feeds               │
└───────────────────────────────┬─────────────────────────────────┘
                                │ git push (automated weekly)
┌───────────────────────────────┴─────────────────────────────────┐
│                       VPS (Scraper)                              │
│  scripts/scrape.py       → Main orchestrator                    │
│  scripts/parsers/*.py    → Platform-specific extractors         │
│  data/sources.json       → Curated source configuration         │
│  Cron: Weekly (Sunday 10pm PST)                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key Design Decisions:**
- **Two-file split**: `events.json` (upcoming) + `archive.json` (past) keeps the site fast
- **Static hosting**: No server costs, GitHub Pages handles everything
- **Deterministic IDs**: SHA256 hash of title+time+location for deduplication

---

## Quick Start (For Learners)

### 1. Clone the Repository

```bash
git clone https://github.com/abe238/seattlehacksv2.git
cd seattlehacksv2
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install crawl4ai icalendar beautifulsoup4

# Install browser for JavaScript rendering
crawl4ai-setup
```

### 3. Run the Scraper Locally

```bash
python scripts/scrape.py
```

This will:
- Fetch events from all enabled sources in `data/sources.json`
- Parse HTML using platform-specific parsers
- Deduplicate events using hash-based IDs
- Separate future events from past events
- Write `docs/data/events.json`, `docs/data/archive.json`, and `docs/data/events.ics`

### 4. View the Website Locally

```bash
# Simple way - just open the file
open docs/index.html

# Or use a local server (recommended for proper asset loading)
cd docs && python3 -m http.server 8000
# Then visit http://localhost:8000
```

---

## Adding a New Event Source

Want to add a new source? Here's how:

### Step 1: Add to sources.json

```json
{
  "id": "your-source-id",
  "name": "Human Readable Name",
  "type": "luma|meetup|eventbrite|tentimes|generic",
  "url": "https://example.com/events",
  "enabled": true,
  "tags": ["ai", "workshop"],
  "priority": 10
}
```

### Step 2: Choose a Parser Type

| Type | Best For | Data Format |
|------|----------|-------------|
| `luma` | Lu.ma calendar pages | JSON-LD embedded in page |
| `meetup` | Meetup.com groups | Schema.org structured data |
| `eventbrite` | Eventbrite organizer pages | Schema.org structured data |
| `tentimes` | 10times.com listings | JSON-LD EducationEvent |
| `generic` | Any HTML page | CSS selector fallback |

### Step 3: Create a Custom Parser (if needed)

If the existing parsers don't work, create a new one in `scripts/parsers/`:

```python
# scripts/parsers/myparser.py
from bs4 import BeautifulSoup

class MyParser:
    """
    Parser for MyEventSite.com

    This parser extracts events from the site's HTML structure.
    Each method is documented for learning purposes.
    """

    def parse(self, result, source):
        """
        Main entry point - called by the scraper.

        Args:
            result: Crawl4AI result with .html property
            source: Source config from sources.json

        Returns:
            List of event dictionaries matching our schema
        """
        soup = BeautifulSoup(result.html, 'html.parser')
        events = []

        # Find event elements (customize this selector)
        for card in soup.select('.event-card'):
            event = {
                'title': card.select_one('.title').text.strip(),
                'startTime': card.get('data-date'),
                'location': {
                    'name': card.select_one('.venue').text,
                    'city': 'Seattle'
                },
                'sourceUrl': card.select_one('a')['href'],
                'sourceId': source['id'],
                'organizer': source['name'],
                'category': self._detect_category(card.text),
                'cost': {'type': 'free', 'amount': None}
            }
            events.append(event)

        return events

    def _detect_category(self, text):
        """Simple keyword-based category detection."""
        text = text.lower()
        if 'hackathon' in text: return 'hackathon'
        if 'ai' in text or 'machine learning' in text: return 'ai'
        if 'workshop' in text: return 'workshop'
        return 'networking'
```

Then register it in `scripts/parsers/__init__.py`:

```python
from .myparser import MyParser

PARSERS = {
    'luma': LumaParser,
    'myparser': MyParser,  # Add your parser
    # ...
}
```

---

## Project Structure

```
seattlehacksv2/
├── README.md              # You are here!
├── CLAUDE.md              # AI assistant context (for Claude Code)
├── data/
│   └── sources.json       # Event source configurations
├── docs/                  # GitHub Pages root (public website)
│   ├── index.html         # Main event listing page
│   ├── archive.html       # Past events page
│   ├── app.js             # Frontend JavaScript (heavily commented)
│   └── data/
│       ├── events.json    # Upcoming events (generated)
│       ├── archive.json   # Past events (generated)
│       └── events.ics     # iCal feed (generated)
├── scripts/
│   ├── scrape.py          # Main scraper (heavily commented)
│   └── parsers/           # Platform-specific parsers
│       ├── __init__.py    # Parser registry
│       ├── luma.py        # Lu.ma parser
│       ├── meetup.py      # Meetup.com parser
│       ├── eventbrite.py  # Eventbrite parser
│       ├── tentimes.py    # 10times.com parser
│       └── generic.py     # Fallback HTML parser
├── run-scraper.sh         # VPS cron entry point
└── setup.sh               # VPS one-time setup
```

---

## Event Schema

Every event follows this structure:

```json
{
  "id": "a1b2c3d4e5f6g7h8",
  "title": "Build Day #4: A developer hiring event",
  "organizer": "AI2 Incubator",
  "category": "hackathon",
  "startTime": "2026-01-28T00:00:00.000Z",
  "endTime": "2026-01-28T02:00:00.000Z",
  "location": {
    "name": "AI House",
    "address": "2801 Alaskan Way, Seattle, WA 98121",
    "city": "Seattle"
  },
  "cost": {
    "type": "free",
    "amount": null
  },
  "sourceUrl": "https://lu.ma/1z8sj980",
  "sourceId": "luma-aihouse"
}
```

**Field Notes:**
- `id`: SHA256 hash of title+startTime+address (first 16 chars) - ensures deduplication
- `category`: One of `hackathon`, `ai`, `workshop`, `networking`, `conference`
- `cost.type`: Either `free` or `paid`
- `sourceId`: Links back to the source in `sources.json`

---

## Key Concepts for Learners

### 1. Async/Await Pattern

The scraper uses Python's `asyncio` for concurrent web requests:

```python
async def scrape_source(self, source):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=source["url"])
        # Process result...
```

This allows scraping multiple sources efficiently without blocking.

### 2. Deduplication with Hashing

Same event on multiple sites? We detect it:

```python
def generate_event_id(title, start_time, address):
    raw = f"{title}{start_time}{address}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

If two events produce the same ID, we keep only the first one.

### 3. XSS Prevention

The frontend escapes all user-supplied content:

```javascript
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
```

This prevents malicious event titles from executing JavaScript.

### 4. Event Delegation

Instead of adding click handlers to each filter button, we use one handler on the parent:

```javascript
document.getElementById('filters').addEventListener('click', (e) => {
  if (e.target.classList.contains('filter-btn')) {
    // Handle the click
  }
});
```

More efficient and works for dynamically added buttons.

---

## Deployment

### GitHub Pages (Frontend)

1. Push changes to `main` branch
2. GitHub Pages automatically deploys from `docs/` folder
3. Visit your site at `https://yourusername.github.io/seattlehacksv2/`

### VPS (Scraper)

For automated weekly updates:

```bash
# SSH to your server
ssh your-server

# Clone and setup
cd /var/www
git clone git@github.com:yourusername/seattlehacksv2.git seattlehacks
cd seattlehacks
./setup.sh

# Add to crontab (runs every Sunday at 10pm PST)
crontab -e
# Add: 0 6 * * 1 /var/www/seattlehacks/run-scraper.sh
```

---

## Contributing

### Adding Events Sources
1. Find a reliable Seattle tech event source
2. Add it to `data/sources.json`
3. Test with `python scripts/scrape.py`
4. Submit a PR!

### Improving Parsers
- Each parser handles a specific site type
- Add comments explaining the HTML structure
- Handle edge cases gracefully

### Frontend Improvements
- Keep it simple and fast
- Maintain the dark theme aesthetic
- Test on mobile devices

---

## API Endpoints

The site exposes static JSON that anyone can use:

| Endpoint | Description |
|----------|-------------|
| `/data/events.json` | Upcoming events (updated weekly) |
| `/data/archive.json` | Past events (historical) |
| `/data/events.ics` | iCal feed for calendar apps |

Example usage:
```javascript
fetch('https://abe238.github.io/seattlehacksv2/data/events.json')
  .then(r => r.json())
  .then(data => console.log(data.events));
```

---

## Tech Stack

- **Frontend**: Vanilla JavaScript, Tailwind CSS (via CDN)
- **Scraping**: Python, Crawl4AI (Playwright-based), BeautifulSoup
- **Hosting**: GitHub Pages (free)
- **Automation**: Cron on VPS
- **Calendar**: icalendar library for iCal generation

---

## Lessons Learned

Building this with AI assistance (Claude Code) taught us:

1. **Start simple**: Static JSON + vanilla JS beats complex frameworks for this use case
2. **Embrace constraints**: GitHub Pages' static hosting forced clean architecture
3. **Document as you go**: Comments help both humans and AI understand the code
4. **Iterate quickly**: AI can prototype features fast; refine what works
5. **Handle edge cases**: Web scraping is messy; expect malformed data

---

## License

MIT License - Use this code to build your own event aggregators!

---

## Credits

- Original inspiration: [crtr0/seattlehacks](https://github.com/crtr0/seattlehacks)
- Built with: [Claude Code](https://claude.ai/code) AI assistant
- Event sources: Lu.ma, Meetup, Eventbrite, 10times, and Seattle's amazing tech community

---

*Seattle's tech events, aggregated with love.*

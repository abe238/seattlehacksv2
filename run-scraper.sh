#!/bin/bash
# SeattleHacks Scraper Runner
# Called by cron weekly to scrape events and push to GitHub

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/scrape-$(date +%Y%m%d).log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

cd "$SCRIPT_DIR"

log "=== Starting SeattleHacks Scrape ==="

# Activate virtual environment
source venv/bin/activate

# Run scraper
log "Running scraper..."
python scripts/scrape.py 2>&1 | tee -a "$LOG_FILE"

# Check if files changed
if git diff --quiet data/events.json data/events.ics 2>/dev/null; then
  log "No changes to event data. Skipping commit."
  exit 0
fi

# Stage and commit
log "Changes detected. Committing..."
git add data/events.json data/events.ics docs/

git commit -m "chore: update events $(date +%Y-%m-%d)

Automated weekly scrape run.
" || { log "Commit failed"; exit 1; }

# Push to GitHub
log "Pushing to GitHub..."
git push origin main || { log "Push failed"; exit 1; }

log "=== Scrape Complete ==="

# Cleanup old logs (keep last 30 days)
find "$SCRIPT_DIR/logs" -name "scrape-*.log" -mtime +30 -delete 2>/dev/null || true

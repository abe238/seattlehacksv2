#!/bin/bash
# SeattleHacks VPS Setup Script
# Run once on VPS to set up the scraper environment

set -e

INSTALL_DIR="/var/www/seattlehacks"

echo "=== SeattleHacks VPS Setup ==="

# Create virtual environment
echo "[1/4] Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

# Install dependencies
echo "[2/4] Installing Python dependencies..."
pip install --upgrade pip
pip install crawl4ai icalendar

# Install Playwright browsers for Crawl4AI
echo "[3/4] Installing Playwright browsers..."
crawl4ai-setup

# Create logs directory
echo "[4/4] Creating logs directory..."
mkdir -p "$INSTALL_DIR/logs"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Add SSH deploy key to GitHub repo (Settings → Deploy Keys)"
echo "   Public key: $(cat ~/.ssh/seattlehacks-deploy.pub 2>/dev/null || echo 'Generate with: ssh-keygen -t ed25519 -f ~/.ssh/seattlehacks-deploy -N \"\"')"
echo ""
echo "2. Configure git to use deploy key:"
echo "   git config core.sshCommand 'ssh -i ~/.ssh/seattlehacks-deploy'"
echo ""
echo "3. Add cron job:"
echo "   crontab -e"
echo "   # Add: 0 6 * * 1 $INSTALL_DIR/run-scraper.sh >> $INSTALL_DIR/logs/cron.log 2>&1"
echo ""
echo "4. Test scraper:"
echo "   cd $INSTALL_DIR && ./run-scraper.sh"

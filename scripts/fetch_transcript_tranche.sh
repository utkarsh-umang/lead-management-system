#!/usr/bin/env bash
# Cron wrapper for fetch_transcript_tranche.py — fetch one daily tranche of
# Podscan episode transcripts into the LMS. Safe to run often: it grabs a day's
# allotment right after the free key's quota resets and does nothing (exits in
# ~1s) the rest of the day. See the .py for scope/env details.
#
# Install (runs every 3h; drains the backlog ~100 episodes/day):
#   ( crontab -l 2>/dev/null; echo "0 */3 * * * $PWD/scripts/fetch_transcript_tranche.sh >> \$HOME/lms-transcript-tranche.log 2>&1" ) | crontab -
# Remove:
#   crontab -l | grep -v fetch_transcript_tranche.sh | crontab -
set -euo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
echo "=== $(date '+%Y-%m-%d %H:%M:%S %z') tranche run ==="
docker compose exec -T backend python /app/scripts/fetch_transcript_tranche.py

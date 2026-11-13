#!/usr/bin/env bash
# Pulls the VPS backups to this machine. Read-only on the VPS side (forced rrsync command).
# A deletion on the VPS never deletes anything here; old files are rotated locally.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
VPS_HOST=${VPS_HOST:-5.61.89.187}
VPS_USER=${VPS_USER:-deploy}
KEY=${KEY:-$HOME/.ssh/vps_backup}
DEST=${DEST:-$HOME/backups/web_foundation}
KEEP_DAYS_DB=${KEEP_DAYS_DB:-60}
KEEP_DAYS_MEDIA=${KEEP_DAYS_MEDIA:-14}
KEEP_DAYS_WEEKLY=${KEEP_DAYS_WEEKLY:-365}
MAX_AGE_HOURS=${MAX_AGE_HOURS:-36}

umask 077
mkdir -p "$DEST/daily" "$DEST/weekly"

SSH="ssh -i $KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$ROOT/deploy/known_hosts"

for dir in daily weekly; do
  rsync -a --partial --exclude='.*' -e "$SSH" "$VPS_USER@$VPS_HOST:/$dir/" "$DEST/$dir/"
done

# Rotation by file age (rsync -a keeps each file's age identical to the VPS copy)
find "$DEST/daily"  -name 'db_*.sql.gz'    -mtime +"$KEEP_DAYS_DB"     -delete
find "$DEST/daily"  -name 'media_*.tar.gz' -mtime +"$KEEP_DAYS_MEDIA"  -delete
find "$DEST/weekly" -name 'db_*.sql.gz'    -mtime +"$KEEP_DAYS_WEEKLY" -delete

# Verify the newest copies
latest_db=$(ls -t "$DEST"/daily/db_*.sql.gz 2>/dev/null | sed -n 1p)
[ -n "$latest_db" ] || { echo "No database backup found in $DEST/daily" >&2; exit 1; }
gzip -t "$latest_db"
zcat "$latest_db" | tail -n 5 | grep -q "PostgreSQL database dump complete"

latest_media=$(ls -t "$DEST"/daily/media_*.tar.gz 2>/dev/null | sed -n 1p)
[ -z "$latest_media" ] || gzip -t "$latest_media"

age_hours=$(( ( $(date +%s) - $(stat -c %Y "$latest_db") ) / 3600 ))
echo "$(date -Is) pull ok: $latest_db (${age_hours}h old)"
if [ "$age_hours" -gt "$MAX_AGE_HOURS" ]; then
  echo "WARNING: the newest database backup is older than ${MAX_AGE_HOURS} hours. Is the nightly backup on the VPS running?" >&2
  exit 2
fi

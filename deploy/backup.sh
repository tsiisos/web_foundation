#!/usr/bin/env bash
# Nightly PostgreSQL backup. Runs on the VPS as the "deploy" user (cron + before each deploy).
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

APP_DIR=/opt/web_foundation
BACKUP_DIR=${BACKUP_DIR:-/var/backups/web_foundation}
KEEP_DAYS=14
KEEP_WEEKS=8

cd "$APP_DIR"
COMPOSE="docker compose --env-file .env.prod -f docker/compose.prod.yml"

mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly"
stamp=$(date +%Y%m%d_%H%M%S)
tmp="$BACKUP_DIR/.db_${stamp}.sql.gz.part"
out="$BACKUP_DIR/daily/db_${stamp}.sql.gz"
trap 'rm -f "$tmp"' EXIT

$COMPOSE exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip -9 > "$tmp"

# A backup only counts if it is a valid archive that ends with pg_dump's completion marker
gzip -t "$tmp"
zcat "$tmp" | tail -n 5 | grep -q "PostgreSQL database dump complete"

mv "$tmp" "$out"
chmod 600 "$out"

# Keep one copy of each Sunday's backup for longer
if [ "$(date +%u)" = "7" ]; then
  cp "$out" "$BACKUP_DIR/weekly/"
fi

# Rotation
find "$BACKUP_DIR/daily"  -name 'db_*.sql.gz' -mtime +"$KEEP_DAYS" -delete
find "$BACKUP_DIR/weekly" -name 'db_*.sql.gz' -mtime +"$((KEEP_WEEKS * 7))" -delete

echo "$(date -Is) backup ok: $out ($(du -h "$out" | cut -f1))"

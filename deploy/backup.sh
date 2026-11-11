#!/usr/bin/env bash
# Nightly backup of PostgreSQL and uploaded media. Runs on the VPS as "deploy" (cron + before each deploy).
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

APP_DIR=/opt/web_foundation
BACKUP_DIR=${BACKUP_DIR:-/var/backups/web_foundation}
KEEP_DAYS=14
KEEP_DAYS_MEDIA=7
KEEP_WEEKS=8

cd "$APP_DIR"
COMPOSE="docker compose --env-file .env.prod -f docker/compose.prod.yml"

mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly"
stamp=$(date +%Y%m%d_%H%M%S)
tmp="$BACKUP_DIR/.db_${stamp}.sql.gz.part"
media_tmp="$BACKUP_DIR/.media_${stamp}.tar.gz.part"
out="$BACKUP_DIR/daily/db_${stamp}.sql.gz"
media_out="$BACKUP_DIR/daily/media_${stamp}.tar.gz"
trap 'rm -f "$tmp" "$media_tmp"' EXIT

# ---- database ----
$COMPOSE exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip -9 > "$tmp"

# A backup only counts if it is a valid archive that ends with pg_dump's completion marker
gzip -t "$tmp"
zcat "$tmp" | tail -n 5 | grep -q "PostgreSQL database dump complete"

mv "$tmp" "$out"
chmod 600 "$out"

# Keep one copy of each Sunday's database backup for longer
if [ "$(date +%u)" = "7" ]; then
  cp "$out" "$BACKUP_DIR/weekly/"
fi

# ---- media files (a failure here must not hide a good database backup) ----
if $COMPOSE exec -T backend tar -C /app -czf - media > "$media_tmp" 2>/dev/null && gzip -t "$media_tmp"; then
  mv "$media_tmp" "$media_out"
  chmod 600 "$media_out"
  echo "$(date -Is) media backup ok: $media_out ($(du -h "$media_out" | cut -f1))"
else
  rm -f "$media_tmp"
  echo "$(date -Is) WARNING: media backup failed (or there is no media volume yet)" >&2
fi

# ---- rotation ----
find "$BACKUP_DIR/daily"  -name 'db_*.sql.gz'     -mtime +"$KEEP_DAYS"       -delete
find "$BACKUP_DIR/daily"  -name 'media_*.tar.gz'  -mtime +"$KEEP_DAYS_MEDIA" -delete
find "$BACKUP_DIR/weekly" -name 'db_*.sql.gz'     -mtime +"$((KEEP_WEEKS * 7))" -delete

echo "$(date -Is) database backup ok: $out ($(du -h "$out" | cut -f1))"

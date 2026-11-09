#!/usr/bin/env bash
# Usage:
#   restore.sh <backup.sql.gz>            replace the LIVE database (asks for confirmation)
#   restore.sh <backup.sql.gz> <scratch>  restore into a separate scratch database, to test a backup
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

APP_DIR=/opt/web_foundation
cd "$APP_DIR"
COMPOSE="docker compose --env-file .env.prod -f docker/compose.prod.yml"

FILE=${1:?Usage: restore.sh <backup.sql.gz> [scratch_db_name]}
SCRATCH=${2:-}

[ -f "$FILE" ] || { echo "File not found: $FILE"; exit 1; }
gzip -t "$FILE"

if [ -n "$SCRATCH" ]; then
  [[ "$SCRATCH" =~ ^[a-zA-Z0-9_]+$ ]] || { echo "Invalid scratch database name"; exit 1; }
  $COMPOSE exec -T db sh -c "dropdb -U \"\$POSTGRES_USER\" --if-exists $SCRATCH && createdb -U \"\$POSTGRES_USER\" $SCRATCH"
  gunzip -c "$FILE" | $COMPOSE exec -T db sh -c "psql -q -v ON_ERROR_STOP=1 -U \"\$POSTGRES_USER\" -d $SCRATCH" > /dev/null
  echo "Restored into scratch database '$SCRATCH'. Tables in the public schema:"
  $COMPOSE exec -T db sh -c "psql -U \"\$POSTGRES_USER\" -d $SCRATCH -Atc \"select count(*) from information_schema.tables where table_schema='public'\""
  exit 0
fi

echo "This REPLACES the live database with: $FILE"
read -r -p "Type 'restore' to continue: " answer
[ "$answer" = "restore" ] || { echo "Aborted."; exit 1; }

$COMPOSE stop backend
$COMPOSE exec -T db sh -c 'dropdb -U "$POSTGRES_USER" --force --if-exists "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" -O "$POSTGRES_USER" "$POSTGRES_DB"'
gunzip -c "$FILE" | $COMPOSE exec -T db sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > /dev/null
$COMPOSE start backend
echo "Restore complete."

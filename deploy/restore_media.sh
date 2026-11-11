#!/usr/bin/env bash
# Usage: restore_media.sh <media_backup.tar.gz>
# REPLACES every file in the live media volume with the contents of the backup.
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

APP_DIR=/opt/web_foundation
cd "$APP_DIR"
COMPOSE="docker compose --env-file .env.prod -f docker/compose.prod.yml"

FILE=${1:?Usage: restore_media.sh <media_backup.tar.gz>}
[ -f "$FILE" ] || { echo "File not found: $FILE"; exit 1; }
gzip -t "$FILE"

echo "This REPLACES all uploaded files with: $FILE"
read -r -p "Type 'restore' to continue: " answer
[ "$answer" = "restore" ] || { echo "Aborted."; exit 1; }

$COMPOSE exec -T backend sh -c 'find /app/media -mindepth 1 -delete'
$COMPOSE exec -T backend tar -C /app -xzf - < "$FILE"
echo "Media restore complete."

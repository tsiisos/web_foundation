#!/usr/bin/env bash
# Dev helper: upload a sample video, wait for the worker, print links to open in a browser.
# Usage: ./scripts/video_check.sh [private|public]
set -uo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8080
BROWSER_BASE=${BROWSER_BASE:-http://192.168.1.64:8080}
VISIBILITY=${1:-private}
DC="docker compose --env-file backend/.env -f docker/compose.dev.yml"

if [ ! -f backend/sample.mp4 ]; then
  echo "Creating backend/sample.mp4 ..."
  $DC exec -T backend ffmpeg -nostdin -loglevel error -y \
    -f lavfi -i testsrc=size=640x360:rate=25 -f lavfi -i sine=frequency=440 \
    -t 5 -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest /app/sample.mp4 || exit 1
fi

read -r -p "Email: " EMAIL
read -rs -p "Password: " PASS; echo
TOKEN=$(curl -s -X POST "$BASE/api/v1/auth/token/" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | sed -nE 's/.*"access":"([^"]+)".*/\1/p')
unset PASS
[ -n "$TOKEN" ] || { echo "Login failed."; exit 1; }

RESP=$(curl -s -X POST "$BASE/api/v1/media/" -H "Authorization: Bearer $TOKEN" \
  -F "file=@backend/sample.mp4" -F "visibility=$VISIBILITY")
ID=$(echo "$RESP" | sed -nE 's/.*"id":"([^"]+)".*/\1/p')
[ -n "$ID" ] || { echo "Upload failed:"; echo "$RESP"; exit 1; }
echo "Uploaded ($VISIBILITY). Waiting for the worker ..."

STATUS=processing
for _ in $(seq 1 30); do
  DETAIL=$(curl -s "$BASE/api/v1/media/$ID/" -H "Authorization: Bearer $TOKEN")
  STATUS=$(echo "$DETAIL" | sed -nE 's/.*"status":"([^"]+)".*/\1/p')
  [ "$STATUS" != "processing" ] && break
  sleep 2
done
echo "Status: $STATUS"

if [ "$STATUS" != "ready" ]; then
  echo "$DETAIL"
  [ "$STATUS" = "processing" ] && echo "Still processing: check 'make worker-logs'."
  exit 1
fi

URL=$(echo "$DETAIL" | grep -o '"url":"[^"]*"' | head -1 | cut -d'"' -f4)
THUMB=$(echo "$DETAIL" | grep -o '"thumbnail_url":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "Range request (needed for seeking): $(curl -s -o /dev/null -w '%{http_code}' -H 'Range: bytes=0-99' "$BASE$URL")  (expect 206)"
echo
echo "Raw link:  $BROWSER_BASE$URL"
echo "Player:    $BROWSER_BASE/video-test.html#$URL"
echo "Thumbnail: $BROWSER_BASE$THUMB"
echo

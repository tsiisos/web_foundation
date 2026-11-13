#!/usr/bin/env bash
# Dev helper: log in, upload a private image, print a fresh link and test it from the server.
set -uo pipefail
cd "$(dirname "$0")/.."

BASE=${BASE:-http://localhost:8080}
BROWSER_BASE=${BROWSER_BASE:-http://192.168.1.64:8080}

SAMPLE=$(ls backend/media/public/*.jpg 2>/dev/null | head -1)
[ -n "$SAMPLE" ] || { echo "No sample .jpg found in backend/media/public/"; exit 1; }

read -r -p "Email: " EMAIL
read -rs -p "Password: " PASS; echo

TOKEN=$(curl -s -X POST "$BASE/api/v1/auth/token/" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | sed -nE 's/.*"access":"([^"]+)".*/\1/p')
unset PASS
[ -n "$TOKEN" ] || { echo "Login failed."; exit 1; }

RESP=$(curl -s -X POST "$BASE/api/v1/media/" -H "Authorization: Bearer $TOKEN" \
  -F "file=@$SAMPLE" -F "visibility=private")
URL=$(echo "$RESP" | grep -o '"url":"[^"]*"' | head -1 | cut -d'"' -f4)
[ -n "$URL" ] || { echo "Upload failed:"; echo "$RESP"; exit 1; }

echo "Upload ok."
echo "With the signed link:     $(curl -s -o /dev/null -w '%{http_code}' "$BASE$URL")  (expect 200)"
echo "Without the signature:    $(curl -s -o /dev/null -w '%{http_code}' "$BASE${URL%%\?*}")  (expect 404)"
echo
echo "Open this in your Windows browser:"
echo
echo "$BROWSER_BASE$URL"
echo

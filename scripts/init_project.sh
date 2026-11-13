#!/usr/bin/env bash
# One-time setup for a NEW project created from this template.
# Usage: ./scripts/init_project.sh <slug> ["Display Name"] [dev_ip] [vps_ip]
#   slug          lowercase letters, digits, underscore (e.g. rentals): folders, containers, server paths
#   Display Name  shown on the website and in emails (default: the slug)
#   dev_ip        address of the dev machine as seen from your browser (e.g. 192.168.1.50)
#   vps_ip        address of the production server
set -euo pipefail
cd "$(dirname "$0")/.."

OLD_SLUG=web_foundation
SLUG=${1:-}
DISPLAY_NAME=${2:-}
DEV_IP=${3:-}
VPS_IP=${4:-}

SLUG_RE='^[a-z][a-z0-9_]{1,30}$'
NAME_RE='^[A-Za-z0-9 .-]{1,40}$'
IP_RE='^[0-9]{1,3}(\.[0-9]{1,3}){3}$'
EXCLUDE=(':!scripts/init_project.sh' ':!deploy/known_hosts')

die() { echo "Error: $*" >&2; exit 1; }
secret() { openssl rand -hex 32; }

command -v openssl >/dev/null || die "openssl is required."
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "run this inside the git repository."
[[ "$SLUG" =~ $SLUG_RE ]] || die "slug: 2-31 characters, lowercase letters, digits and underscore, starting with a letter."
[ "$SLUG" != "$OLD_SLUG" ] || die "choose a name different from the template's."
[[ -z "$DISPLAY_NAME" || "$DISPLAY_NAME" =~ $NAME_RE ]] || die "display name: up to 40 letters, digits, spaces, dots and dashes."
[[ -z "$DEV_IP" || "$DEV_IP" =~ $IP_RE ]] || die "dev_ip must look like 192.168.1.50"
[[ -z "$VPS_IP" || "$VPS_IP" =~ $IP_RE ]] || die "vps_ip must look like 203.0.113.10"

if [ -z "${FORCE:-}" ] && [ -n "$(git status --porcelain)" ]; then
  die "uncommitted changes found. Commit or stash them first (or run with FORCE=1)."
fi
git grep -qIF "$OLD_SLUG" -- . "${EXCLUDE[@]}" || die "nothing to rename: this project was already initialised."

echo "==> Renaming $OLD_SLUG to $SLUG"
git grep -lIF "$OLD_SLUG" -- . "${EXCLUDE[@]}" | xargs -r sed -i "s/$OLD_SLUG/$SLUG/g"

if [ -n "$DISPLAY_NAME" ]; then
  echo "==> Display name: $DISPLAY_NAME"
  sed -i "s|^export const SITE_NAME = .*|export const SITE_NAME = \"$DISPLAY_NAME\";|" frontend/src/lib/config.ts
  git grep -lIF "$SLUG <noreply" -- . "${EXCLUDE[@]}" | xargs -r sed -i "s|$SLUG <noreply|$DISPLAY_NAME <noreply|g" || true
fi

if [ -n "$DEV_IP" ]; then
  echo "==> Dev machine address: $DEV_IP"
  git grep -lI -e '192\.168\.1\.64' -e '192\.168\.1\.105' -- . "${EXCLUDE[@]}" \
    | xargs -r sed -i -e "s/192\.168\.1\.64/$DEV_IP/g" -e "s/192\.168\.1\.105/$DEV_IP/g" || true
fi
if [ -n "$VPS_IP" ]; then
  echo "==> Server address: $VPS_IP"
  git grep -lI -e '5\.61\.89\.187' -- . "${EXCLUDE[@]}" | xargs -r sed -i "s/5\.61\.89\.187/$VPS_IP/g" || true
fi

# The template's host keys belong to the old server
cat > deploy/known_hosts <<'KH'
# Host keys of the production server. Create them once the server exists:
#   ssh-keyscan -t ed25519,rsa SERVER_IP > deploy/known_hosts
# then compare with "ssh-keygen -lf /etc/ssh/ssh_host_*_key.pub" run on the server.
KH

echo "==> Environment files"
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env && chmod 600 backend/.env
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(secret)|" backend/.env
  sed -i "s|^MEDIA_SIGNED_URL_SECONDS=.*|MEDIA_SIGNED_URL_SECONDS=3600|" backend/.env
  [ -z "$DEV_IP" ] || sed -i "s|^FRONTEND_URL=.*|FRONTEND_URL=http://$DEV_IP:8080|" backend/.env
  echo "    created backend/.env"
fi
if [ ! -f frontend/.env ]; then
  cp frontend/.env.example frontend/.env && chmod 600 frontend/.env
  echo "    created frontend/.env"
fi
if [ ! -f .env.prod ]; then
  cp .env.prod.example .env.prod && chmod 600 .env.prod
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(secret)|" .env.prod
  sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$(secret)|" .env.prod
  echo "    created .env.prod (local rehearsal only; the server gets its own)"
fi

cat <<NEXT

Done. Next steps:
  1. Review the changes:   git diff --stat
  2. Commit them:          git add -A && git commit -m "Initialise $SLUG"
  3. Start the dev stack:  make up   (then: make superuser)
  4. Rename the roles in backend/users/models.py and the register/profile pages, if needed.
  5. Set up the server and the deploy secrets: see the README.
NEXT

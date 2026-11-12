#!/usr/bin/env bash
# Runs on the VPS as the "deploy" user. GitHub Actions calls it over SSH.
set -euo pipefail

APP_DIR=/opt/web_foundation
COMPOSE="docker compose --env-file .env.prod -f docker/compose.prod.yml"

main() {
  cd "$APP_DIR"

  # Only one deploy at a time
  exec 9>/tmp/web_foundation_deploy.lock
  if ! flock -n 9; then
    echo "Another deploy is already running, aborting."
    exit 1
  fi

  echo "==> Updating code"
  git fetch --prune origin main
  git reset --hard origin/main
  git log -1 --oneline
  echo "==> Backing up database"
  ./deploy/backup.sh || echo "WARNING: backup failed, continuing deploy"

  echo "==> Building and starting containers"
  $COMPOSE up -d --build --remove-orphans

  echo "==> Recreating nginx (picks up config changes)"
  $COMPOSE up -d --force-recreate --no-deps nginx

  echo "==> Waiting for the app to become healthy"
  port=$(grep -E '^HTTP_PORT=' .env.prod | cut -d= -f2 || true)
  port=${port:-80}
  for _ in $(seq 1 30); do
    if curl -fsS "http://localhost:${port}/api/v1/health/" >/dev/null; then
      echo "Healthy."
      docker image prune -f >/dev/null
      echo "==> Deploy finished"
      return 0
    fi
    sleep 4
  done

  echo "Health check failed. Recent logs:"
  $COMPOSE logs --tail=50
  return 1
}

# One line on purpose: bash must read it fully before the script file can change under it
main "$@"; exit $?

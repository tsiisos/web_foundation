# web_foundation

Template for web projects: a **Django REST Framework** API, a **Next.js** frontend, **PostgreSQL**, **Redis + Celery** and **Nginx**, everything in Docker. A push to `main` runs the tests and deploys to the server.

## What is included

- **Accounts:** email login, customer/provider role flags, registration, email verification, password reset and change, account deletion. JWT with the refresh token in an httpOnly cookie; logout revokes tokens.
- **Media:** images (EXIF removed, thumbnails), MP4 video (H.264, checked with ffmpeg, processed in the background), PDFs. Public files are served by Nginx, private files through short-lived signed links.
- **Background jobs:** Celery worker with beat (emails, video processing, token cleanup).
- **Frontend:** register, login, verify email, forgot/reset password, profile, media library.
- **CI/CD:** GitHub Actions runs the backend tests and the frontend build, then deploys over SSH with a restricted key.
- **Backups:** nightly database and media backups on the server, a nightly pull to a second machine, restore scripts.
- **Security:** rate limits, security headers, an `HTTPS_ENABLED` switch for secure cookies and HSTS.

## Layout

    backend/    Django project (config/) and apps: users, uploads, api
    frontend/   Next.js app (src/app pages, src/lib helpers)
    docker/     compose.dev.yml, compose.prod.yml, nginx/
    deploy/     deploy.sh, backup.sh, restore.sh, restore_media.sh, known_hosts
    scripts/    init_project.sh, pull_backups.sh, media_check.sh, video_check.sh
    .github/    workflows/deploy.yml
    Makefile    all everyday commands (run them from the project root)

## Daily work

| Command | What it does |
|---|---|
| `make up` / `make down` | start / stop the dev stack |
| `make logs`, `make worker-logs` | follow the logs |
| `make test` | backend tests |
| `make fe-lint`, `make fe-typecheck` | frontend checks |
| `make makemigrations`, `make migrate` | database migrations |
| `make superuser` | create an admin user |
| `make fe-add PKG=name` | add a frontend package |
| `make worker-restart` | restart the worker after changing task code |
| `make prod-up`, `make prod-ps`, `make prod-logs` | the production stack (a rehearsal on the dev machine, the real thing on the server) |

Dev site `http://DEV_IP:8080`, Mailpit (all dev emails) `http://DEV_IP:8025`, admin `/api/admin/`.

## Start a new project

1. On GitHub open this repository, click **Use this template**, create a private repository and clone it on the dev machine.
2. Run the one-time setup:

        make init NAME=rentals TITLE="Rentals" DEV_IP=192.168.1.50 VPS_IP=203.0.113.10

   It renames the project everywhere (containers, server paths, site name, email sender), replaces the addresses, resets `deploy/known_hosts`, and creates `backend/.env`, `frontend/.env` and `.env.prod` with fresh secrets.
3. Review with `git diff --stat`, then commit.
4. `make up`, `make superuser`, open the dev site.
5. Rename the roles (`is_customer` / `is_provider`) in `backend/users/models.py` and the register and profile pages if the project needs other words.
6. Set up the server (below).

## Server setup (once per project)

Debian 13, a user called `deploy`, project slug `SLUG`.

1. As root: update the system, install the basics, add 2 GB of swap on small servers, create an admin user and `deploy`.

        apt update && apt upgrade -y
        apt install -y sudo git curl ca-certificates make nano ufw rsync
        adduser ADMIN && usermod -aG sudo ADMIN
        adduser --disabled-password --gecos "" deploy

2. Install your public key for ADMIN, test the login, then harden SSH (key login only, no root login):

        printf 'PermitRootLogin no\nPasswordAuthentication no\nKbdInteractiveAuthentication no\nPubkeyAuthentication yes\n' > /etc/ssh/sshd_config.d/00-hardening.conf
        sshd -t && systemctl reload ssh

3. Firewall: `ufw default deny incoming`, `ufw default allow outgoing`, `ufw allow OpenSSH`, `ufw allow 80/tcp`, `ufw allow 443/tcp`, `ufw enable`.
4. Install Docker Engine from Docker's apt repository (docs.docker.com/engine/install/debian), then:

        usermod -aG docker deploy
        mkdir -p /opt/SLUG /var/backups/SLUG
        chown deploy:deploy /opt/SLUG /var/backups/SLUG
        chmod 700 /var/backups/SLUG

5. As `deploy`: create a key (`ssh-keygen -t ed25519 -N "" -C vps-deploy`), add `~/.ssh/id_ed25519.pub` to the GitHub repository as a **read-only deploy key**, then `git clone git@github.com:USER/REPO.git /opt/SLUG`.
6. In `/opt/SLUG`: `cp .env.prod.example .env.prod` and edit it (random `SECRET_KEY` and `DB_PASSWORD`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `FRONTEND_URL`, `GUNICORN_WORKERS=2` on one CPU). `chmod 600 .env.prod`, then `make prod-up` and `make prod-superuser`.
7. CI key, as `deploy`:

        ssh-keygen -t ed25519 -N "" -C github-actions -f ~/.ssh/gha_deploy
        echo "command=\"/opt/SLUG/deploy/deploy.sh\",restrict $(cat ~/.ssh/gha_deploy.pub)" >> ~/.ssh/authorized_keys
        cat ~/.ssh/gha_deploy

   Copy the private key straight into the GitHub secret `SSH_KEY` (never paste it anywhere else), add `SSH_HOST` and `SSH_USER` (= `deploy`), then `shred -u ~/.ssh/gha_deploy ~/.ssh/gha_deploy.pub`.
8. Host key: on the dev machine run `ssh-keyscan -t ed25519,rsa SERVER_IP > deploy/known_hosts`, compare the fingerprints with `ssh-keygen -lf /etc/ssh/ssh_host_*_key.pub` on the server, commit and push.
9. Backups: as `deploy`, `crontab -e`, add `15 3 * * * /opt/SLUG/deploy/backup.sh >> /var/backups/SLUG/backup.log 2>&1`. Run it once, then **test a restore** into a scratch database: `./deploy/restore.sh FILE.sql.gz restore_test`, and drop it afterwards.
10. Off-site copy, on a second machine: create a key, add its public key to the server's `deploy` user as `command="/usr/bin/rrsync -ro /var/backups/SLUG",restrict ssh-ed25519 AAAA...`, run `scripts/pull_backups.sh` (override `KEY`, `VPS_HOST`, `DEST` with environment variables if needed), then install a systemd service and timer for it (`OnCalendar=*-*-* 04:30:00`, `Persistent=true`).

## HTTPS (when you have a domain)

Not part of the template yet. Plan: point an A record at the server, add port 443 and Let's Encrypt to Nginx, redirect HTTP to HTTPS there, then set `HTTPS_ENABLED=true` and `COOKIE_SECURE=true` in `.env.prod` and change `CSRF_TRUSTED_ORIGINS` and `FRONTEND_URL` to `https://` addresses. Until then do not use real passwords on the server.

## Things learned the hard way

- The frontend runs with `--webpack` (dev and build). Turbopack exited in Docker, and webpack needs `frontend/postcss.config.mjs` for Tailwind.
- Nginx reads its config from a bind-mounted file, so `deploy.sh` recreates the container instead of reloading it.
- Never edit tracked files on the server: every deploy runs `git reset --hard`. Only `.env.prod` is local.
- Docker bypasses UFW for published ports, so only Nginx publishes one.
- iPhones record HEVC by default. The upload expects H.264 MP4 ("Most Compatible" in the camera settings).
- Redis is required: login rate limits, the queue and the cache depend on it.
- Run commands from the project root, paste one block at a time into the terminal, and never put passwords or private keys into commands or chats.

## Known limits

- Logout and password changes revoke refresh tokens, but an access token stays valid for up to 30 minutes.
- Media backups are full daily copies. Move to incremental backups when media grows past a few GB.
- Backups are not encrypted at rest.

# syntax=docker/dockerfile:1
FROM node:22-slim AS base
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm install -g pnpm@10
WORKDIR /app

# ---------- dependencies ----------
FROM base AS deps
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml* ./
RUN pnpm install --frozen-lockfile

# ---------- development ----------
FROM base AS dev
ENV NODE_ENV=development
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
# Run next directly (no pnpm wrapper process)
CMD ["node_modules/.bin/next", "dev", "--webpack", "--hostname", "0.0.0.0", "--port", "3000"]

# The production stage is added in Phase 5.

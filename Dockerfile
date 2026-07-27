# Two languages in one repo (Vite/React frontend + Python pipeline) — a
# Dockerfile gives explicit control over both instead of relying on
# Nixpacks' single-language auto-detection.

FROM node:20-slim AS frontend-build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

# The pipeline scripts use datetime.today() (no explicit timezone) to date
# each day's report, and the frontend asks for a report matching the
# browser's local calendar date. Debian's base image defaults to UTC, which
# is 8 hours behind Taiwan — during Taiwan's 00:00-08:00 window "today" on
# the two sides wouldn't agree, and the site would show no data for that
# report even though the pipeline ran successfully. Installing tzdata and
# setting TZ makes the container's "today" match Taiwan's.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*
ENV TZ=Asia/Taipei

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=frontend-build /app/dist ./dist

CMD ["python", "server.py"]

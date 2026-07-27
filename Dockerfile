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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=frontend-build /app/dist ./dist

CMD ["python", "server.py"]

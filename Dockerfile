FROM node:20-slim AS frontend-builder

WORKDIR /build
COPY landing/package*.json ./
RUN npm ci --no-audit
COPY landing/ ./
RUN npm run build

# ─── Python backend ───
FROM python:3.11-slim

WORKDIR /app

# Python deps
COPY requirements-fly.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy Next.js static build output
COPY --from=frontend-builder /build/out ./landing/out/

# Copy legacy frontend (preserved for /legacy route)
COPY legacy-frontend/ ./legacy-frontend/

# Data dir — mounted as Fly volume at /app/data
ENV DATA_DIR=/app/data
RUN mkdir -p /app/data/uploads /app/data/summaries /app/data/context_packs /app/data/backups

# Expose port
EXPOSE 8000

# Run
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

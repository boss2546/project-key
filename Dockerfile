# ─── Python backend + legacy frontend ───
FROM python:3.11-slim

WORKDIR /app

# Python deps
COPY requirements-fly.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy frontend
COPY legacy-frontend/ ./legacy-frontend/

# Data dir — mounted as Fly volume at /app/data
ENV DATA_DIR=/app/data
RUN mkdir -p /app/data/uploads /app/data/summaries /app/data/context_packs /app/data/backups

# Expose port
EXPOSE 8000

# Run
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

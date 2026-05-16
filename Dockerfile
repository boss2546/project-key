# ─── Python backend + legacy frontend (v5.2 — OCR support · v11.0.0 build tools) ───
FROM python:3.11-slim

WORKDIR /app

# System deps for OCR (Tesseract + poppler for pdf2image)
# + v11.0.0: build-essential + gfortran สำหรับ compile hdbscan/umap-learn (C extensions)
#   หลัง pip install เสร็จ → apt-get remove build tools เพื่อ keep image lean
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-tha \
    tesseract-ocr-eng \
    poppler-utils \
    build-essential \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Python deps
# v11.0.0 — hdbscan + umap-learn ต้อง compile, ใช้เวลา 1-2 นาทีตอน build
COPY requirements-fly.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# v11.0.0 — Remove build tools หลัง install เสร็จ (keep image lean)
# build-essential + gfortran รวม ~250MB → ลบทิ้งเหลือเฉพาะ runtime
RUN apt-get update && apt-get purge -y --auto-remove \
    build-essential \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

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

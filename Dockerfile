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

# v10.0.30-hotfix — Healthcheck (Docker-level awareness · Fly probe ยังเป็นตัว gate หลัก)
# Note: USER non-root deferred ไป backlog เพราะ Fly volume permission ต้อง entrypoint script (gosu)
#       และ Fly machine = firecracker VM อยู่แล้ว (host isolation จากตัว container)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import httpx,sys; r=httpx.get('http://127.0.0.1:8000/health', timeout=4.0); sys.exit(0 if r.status_code==200 else 1)" || exit 1

# Run
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

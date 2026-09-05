# ── The Witness Network – Backend Dockerfile ──
# Lightweight Python image for the FastAPI backend

FROM python:3.12-slim

# Prevent .pyc files & enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for numpy / scikit-learn
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python deps first (cache-friendly layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (excluding venv, db, etc. via .dockerignore)
COPY . .

# Expose the Uvicorn port
EXPOSE 8000

# Health check against the /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run in production mode (no --reload in container)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

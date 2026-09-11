# =============================================================================
# Stage 1: Build & Dependency Stage
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /install

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies into a wheel directory or virtualenv
COPY requirements.txt .

# Install dependencies into /install/packages to easily copy into runtime stage
RUN pip install --no-cache-dir --prefix=/install/packages -r requirements.txt \
    && pip install --no-cache-dir --prefix=/install/packages gunicorn flasgger flask-cors flask-limiter python-dotenv qrcode reportlab

# =============================================================================
# Stage 2: Production Slim Runtime Stage
# =============================================================================
FROM python:3.11-slim AS runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/install/packages/bin:$PATH" \
    PYTHONPATH="/app/src:/app:$PYTHONPATH" \
    PORT=5000 \
    DATABASE_TYPE=sqlite \
    DATABASE_URL=sqlite:///data/inspections.db

WORKDIR /app

# Install minimal OS runtime libraries for OpenCV (headless image processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /install/packages /usr/local

# Create non-root application user for container security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Copy application files
COPY . /app

# Ensure directories for persistence, logs, and uploads exist with proper permissions
RUN mkdir -p /app/data /app/uploads /app/outputs/reports /app/logs /app/models \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose production port
EXPOSE 5000

# Container Health Check (Prompt 14 & 17)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Production WSGI server execution with gunicorn (4 workers, 120s timeout)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "src.app:app"]

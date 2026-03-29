# ── Stage 1: Build & Dependencies ──
FROM python:3.11-slim as builder

# Set standard environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Create a virtual environment and install dependencies
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Production Image ──
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

WORKDIR /app

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy python dependencies from builder
COPY --from=builder /opt/venv /opt/venv

# Copy local source code and ensure permissions
COPY --chown=appuser:appuser . .

# Secure the chroma_db and data directories if they exist
RUN mkdir -p chroma_db data && chown -R appuser:appuser chroma_db data

USER appuser

EXPOSE 8000

# Alembic migrations run automatically on startup then uvicorn starts
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"]
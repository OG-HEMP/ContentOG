# --- Build Stage ---
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build
ENV PATH="/root/.local/bin:${PATH}"

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
# First copy only requirements to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir --user --upgrade pip setuptools wheel Cython
RUN pip install --no-cache-dir --user -r requirements.txt

# Now copy the rest of the code
COPY . .

# --- Production Stage ---
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH=/home/contentog/.local/bin:$PATH

# Install runtime dependencies ONLY
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Security: Create and use a non-root user
RUN useradd -m contentog
USER contentog
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/contentog/.local

# Copy application code
COPY --chown=contentog:contentog . .

# Entrypoint for Cloud Run
EXPOSE 8080
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8080"]

# === Stage 1: Build ===
FROM python:3.11-slim AS builder

WORKDIR /app

# 新增：替换 Debian 源为阿里云镜像（加速 apt）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# === Stage 2: Runtime ===
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN useradd -m appuser && \
    mkdir -p /app/data /app/data/avatars /app/data/logs && \
    chown -R appuser:appuser /app/data

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY app/ ./app/

# Set permissions
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

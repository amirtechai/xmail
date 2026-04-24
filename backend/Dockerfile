FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY pyproject.toml ./
RUN /root/.local/bin/uv pip install --system --no-cache -r pyproject.toml

# Runtime stage
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Install Playwright browsers (needed for scraping)
RUN pip install --no-cache-dir playwright==1.50.0 && playwright install --with-deps chromium

COPY . .

# Non-root user for security
RUN useradd -m -u 1001 xmail && chown -R xmail:xmail /app
USER xmail

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

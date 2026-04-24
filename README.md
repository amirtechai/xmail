# Xmail — Agentic Outreach Bot for PriceONN.com

Autonomous email discovery, validation, and campaign management for global financial industry outreach.

## Features

- **Agentic Intelligence:** LangGraph state machine with multi-stage LLM reasoning
- **60+ Audience Categories:** Forex bloggers, crypto analysts, financial journalists, brokers, institutions, and more
- **Autonomous Discovery:** Scrapes, validates, enriches contacts from public sources only
- **Daily Reports:** PDF + XML summaries delivered at 09:00 UTC+3
- **GDPR/CAN-SPAM Compliant:** Automatic footer injection, unsubscribe handling, audit logs
- **Zero Duplicates:** Bloom filter + DB deduplication guarantee
- **Low Cost:** ~$50-70/month infrastructure (no SaaS fees)
- **Fully Self-Hosted:** Docker Compose, single command deploy

## Quick Start

### Prerequisites

- Docker & Docker Compose v2+
- 4GB RAM minimum (8GB recommended)

### Setup

```bash
# Clone repo
git clone https://github.com/amirtech/xmail.git
cd xmail

# Copy environment template
cp backend/.env.example backend/.env
# Edit backend/.env — set SECRET_KEY, ADMIN_PASSWORD_HASH at minimum

# Start all services
docker-compose up -d

# Wait for postgres to be healthy, then run migrations
docker-compose exec backend alembic upgrade head

# Seed 60 audience types
docker-compose exec backend python -m scripts.seed_audience_types

# Access dashboard
open http://localhost:3000
# Default login: patron@amirtech.ai / (password set in .env)
```

### First-time Configuration (Dashboard)

1. **Settings → SMTP** — Add your outreach email account
2. **Settings → LLM Providers** — Add API key (OpenRouter recommended)
3. **Bot Control** — Select audience categories, click "Run Now"
4. Wait for discovery run to complete (~30 min for first run)
5. **Daily Lists** — Review discovered contacts
6. **Compose** — Draft and send your first campaign

## Architecture

```
User Dashboard (React + Vite)
        ↓
FastAPI Backend (Python 3.12, async)
        ↓
LangGraph Agent (Discovery → Validation → Enrichment → Deduplication)
        ├─ Firecrawl API (primary scraping)
        ├─ Playwright (JS-heavy sites)
        └─ Scrapy (bulk crawling)
        ↓
PostgreSQL 16 + pgvector    Redis 7
        ↓
Celery Beat (scheduled tasks)
        ↓
Daily Reports (PDF + XML) → User Email at 09:00 UTC+3
        ↓
Campaign Management (user reviews → approves → sends)
        ↓
SMTP (user-configured, with GDPR compliance footer)
```

## Compliance

- GDPR: physical address, unsubscribe link, LIA assessment per campaign
- CAN-SPAM: one-click unsubscribe, clear sender disclosure
- CASL: legitimate business interest documented and logged
- All emails require explicit user approval before sending
- Global suppression list (unsubscribed/bounced/complained)

## Cost Estimate

| Service | Cost |
|---------|------|
| Hetzner CX32 (4 vCPU, 8GB) | ~€7/month |
| LLM (Claude Haiku planner + Sonnet enricher) | ~$15-30/month |
| Firecrawl Pro | $29/month |
| Domain + Cloudflare | ~$1/month |
| **Total** | **~$50-70/month** |

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Setup Guide](docs/SETUP.md)
- [Agent Guide](docs/AGENT_GUIDE.md)
- [Compliance](docs/COMPLIANCE.md)
- [Security](docs/SECURITY.md)
- [Runbook](docs/RUNBOOK.md)

## Support

Contact: support@amirtech.ai

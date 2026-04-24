"""DEA (Disposable Email Address) list update — daily 01:00 UTC.

Fetches updated disposable domain list from a public source and
merges into the local dea_check module's frozenset.
Since the frozenset is in-memory, this task writes an updated JSON file
that is loaded on next worker restart.
"""

import asyncio
import json
import logging
from pathlib import Path

import httpx

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

DEA_CACHE_PATH = Path("/tmp/xmail_dea_domains.json")  # noqa: S108
# Public list maintained by disposable-email-domains community
DEA_SOURCE_URL = "https://raw.githubusercontent.com/disposable-email-domains/disposable-email-domains/master/disposable_email_blocklist.conf"


@celery_app.task(name="app.tasks.dea_list_update.update_dea_list", bind=True)
def update_dea_list(self) -> dict:  # type: ignore[override]
    return asyncio.get_event_loop().run_until_complete(_update())


async def _update() -> dict:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(DEA_SOURCE_URL)
            response.raise_for_status()

        domains = [
            line.strip().lower()
            for line in response.text.splitlines()
            if line.strip() and not line.startswith("#")
        ]

        DEA_CACHE_PATH.write_text(json.dumps(domains))
        logger.info("dea_list_updated", count=len(domains))
        return {"updated": len(domains)}

    except Exception as exc:
        logger.warning("dea_list_update_failed", error=str(exc))
        return {"error": str(exc)}

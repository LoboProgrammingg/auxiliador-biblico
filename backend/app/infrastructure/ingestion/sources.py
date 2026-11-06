import asyncio
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

TRANSLATION_URL = "https://raw.githubusercontent.com/thiagobodruk/bible/master/json/pt_{code}.json"
STEPBIBLE_BASE = "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master"
CROSSREF_URL = "https://a.openbible.info/data/cross-references.zip"


async def download(
    url: str,
    dest: Path,
    client: httpx.AsyncClient | None = None,
    attempts: int = 3,
    backoff: float = 2.0,
) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=60, follow_redirects=True)
    try:
        for attempt in range(1, attempts + 1):
            try:
                response = await http.get(url)
                response.raise_for_status()
                part.write_bytes(response.content)
                part.replace(dest)
                return dest
            except (httpx.HTTPError, OSError) as exc:
                logger.warning("download falhou (%s/%s) %s: %s", attempt, attempts, url, type(exc).__name__)
                if attempt == attempts:
                    raise
                await asyncio.sleep(backoff * 2 ** (attempt - 1))
    finally:
        part.unlink(missing_ok=True)
        if owns_client:
            await http.aclose()
    return dest

"""PDF pelo Chrome do sistema em modo headless: sem serviço externo, sem custo."""

import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)
CANDIDATES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
TIMEOUT_S = 90
_RUNNING = asyncio.Semaphore(2)


class PdfUnavailable(Exception):
    pass


class PageMissing(Exception):
    pass


def find_chrome(configured: str | None) -> str | None:
    for name in ([configured] if configured else []) + list(CANDIDATES):
        if path := shutil.which(name):
            return path
    return None


class ChromePdf:
    def __init__(self, chrome_bin: str | None, client: httpx.AsyncClient | None = None) -> None:
        self._bin = find_chrome(chrome_bin)
        self._client = client

    async def _check_page(self, url: str) -> None:
        """Abre a página antes: assim um erro (404/500) nunca vira um PDF da página de erro."""
        http = self._client or httpx.AsyncClient(timeout=120)
        try:
            response = await http.get(url)
        except httpx.HTTPError as exc:
            raise PdfUnavailable("a interface não respondeu (ela está aberta na porta 3000?)") from exc
        finally:
            if self._client is None:
                await http.aclose()
        if response.status_code == 404:
            raise PageMissing(url)
        if response.status_code != 200:
            raise PdfUnavailable(f"a página de impressão respondeu {response.status_code}")

    async def render(self, url: str) -> bytes:
        if self._bin is None:
            raise PdfUnavailable("Chrome não encontrado")
        await self._check_page(url)
        async with _RUNNING:
            return await self._run(self._bin, url)

    async def _run(self, chrome: str, url: str) -> bytes:
        with tempfile.TemporaryDirectory(prefix="biblia-pdf-") as tmp:
            out = Path(tmp) / "saida.pdf"
            proc = await asyncio.create_subprocess_exec(
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "--no-pdf-header-footer",
                "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=20000",
                f"--user-data-dir={tmp}/perfil",
                f"--print-to-pdf={out}",
                url,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, err = await asyncio.wait_for(proc.communicate(), TIMEOUT_S)
            except TimeoutError as exc:
                proc.kill()
                await proc.wait()
                raise PdfUnavailable("o Chrome demorou demais para gerar o PDF") from exc
            data = await asyncio.to_thread(out.read_bytes) if await asyncio.to_thread(out.exists) else b""
            if proc.returncode != 0 or not data.startswith(b"%PDF"):
                logger.warning("chrome falhou (%s): %s", proc.returncode, err.decode(errors="replace")[-300:])
                raise PdfUnavailable("o Chrome não conseguiu gerar o PDF")
            return data

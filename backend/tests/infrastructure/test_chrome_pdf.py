import httpx
import pytest

from app.infrastructure.pdf.chrome import ChromePdf, PageMissing, PdfUnavailable


def client(status: int) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(lambda _r: httpx.Response(status, text="x")))


async def test_missing_page_is_not_printed() -> None:
    pdf = ChromePdf("sh", client=client(404))
    with pytest.raises(PageMissing):
        await pdf.render("http://127.0.0.1:3000/imprimir/conversa/x")


async def test_broken_page_is_not_printed() -> None:
    pdf = ChromePdf("sh", client=client(500))
    with pytest.raises(PdfUnavailable):
        await pdf.render("http://127.0.0.1:3000/imprimir/conversa/x")


async def test_without_chrome_is_unavailable() -> None:
    pdf = ChromePdf("nao-existe-este-binario", client=client(200))
    pdf._bin = None
    with pytest.raises(PdfUnavailable):
        await pdf.render("http://x")

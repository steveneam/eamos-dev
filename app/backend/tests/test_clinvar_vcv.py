from __future__ import annotations

import pytest

from app.services import clinvar_vcv


class _FakeStream:
    def __init__(self, response) -> None:
        self.response = response

    def __enter__(self):
        return self.response

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False


class _FakeResponse:
    def __init__(
        self, *, content_length: str | None = None, chunks: tuple[bytes, ...] = ()
    ) -> None:
        self.headers = {}
        if content_length is not None:
            self.headers["content-length"] = content_length
        self.encoding = "utf-8"
        self.chunks = chunks
        self.iterated = False

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self):
        self.iterated = True
        yield from self.chunks


def test_streaming_client_rejects_declared_oversize_before_body_iteration(monkeypatch) -> None:
    response = _FakeResponse(content_length="65", chunks=(b"<ClinVarResult-Set />",))

    def fake_stream(*_args, **_kwargs):
        return _FakeStream(response)

    monkeypatch.setattr(clinvar_vcv.httpx, "stream", fake_stream)
    client = clinvar_vcv.EutilsClinVarVcvClient(
        base_url="https://example.test/eutils",
        max_xml_bytes=64,
    )

    with pytest.raises(clinvar_vcv.ClinVarVcvSizeLimitError) as exc:
        client.fetch_vcv_xml("2356")

    assert exc.value.observed_bytes == 65
    assert response.iterated is False


def test_streaming_client_rejects_chunked_oversize_response(monkeypatch) -> None:
    response = _FakeResponse(chunks=(b"a" * 40, b"b" * 30))

    def fake_stream(*_args, **_kwargs):
        return _FakeStream(response)

    monkeypatch.setattr(clinvar_vcv.httpx, "stream", fake_stream)
    client = clinvar_vcv.EutilsClinVarVcvClient(
        base_url="https://example.test/eutils",
        max_xml_bytes=64,
    )

    with pytest.raises(clinvar_vcv.ClinVarVcvSizeLimitError) as exc:
        client.fetch_vcv_xml("2356")

    assert exc.value.observed_bytes == 70
    assert response.iterated is True

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any, Literal

import httpx

DEFAULT_CLINVAR_VCV_MAX_XML_BYTES = 5 * 1024 * 1024
_PARSE_RESULT_CACHE_KEY = "_eamos_clinvar_vcv_parse_result"
_VCV_XML_CACHE_KEY = "vcv_xml"
_TARGET_TAGS = frozenset({"Comment", "Attribute", "Description"})

ClinVarVcvParseErrorCode = Literal["xml_too_large", "parse_failed"]


class ClinVarVcvSizeLimitError(ValueError):
    def __init__(self, *, max_bytes: int, observed_bytes: int | None = None) -> None:
        self.max_bytes = max_bytes
        self.observed_bytes = observed_bytes
        detail = (
            f"ClinVar VCV XML exceeds {max_bytes} bytes"
            if observed_bytes is None
            else f"ClinVar VCV XML is {observed_bytes} bytes; limit is {max_bytes}"
        )
        super().__init__(detail)


@dataclass(frozen=True)
class ClinVarVcvExtraction:
    comment_texts: tuple[str, ...]
    attribute_texts: tuple[str, ...]
    description_texts: tuple[str, ...]

    def texts_for(self, tag_names: Iterable[str]) -> tuple[str, ...]:
        texts: list[str] = []
        for tag_name in tag_names:
            if tag_name == "Comment":
                texts.extend(self.comment_texts)
            elif tag_name == "Attribute":
                texts.extend(self.attribute_texts)
            elif tag_name == "Description":
                texts.extend(self.description_texts)
        return tuple(texts)


@dataclass(frozen=True)
class ClinVarVcvParseResult:
    extraction: ClinVarVcvExtraction | None = None
    error_code: ClinVarVcvParseErrorCode | None = None
    max_xml_bytes: int = DEFAULT_CLINVAR_VCV_MAX_XML_BYTES


class EutilsClinVarVcvClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 12.0,
        max_xml_bytes: int = DEFAULT_CLINVAR_VCV_MAX_XML_BYTES,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_xml_bytes = _effective_max_xml_bytes(max_xml_bytes)

    def fetch_vcv_xml(self, variation_id: str) -> str:
        with httpx.stream(
            "GET",
            f"{self.base_url}/efetch.fcgi",
            params={
                "db": "clinvar",
                "id": variation_id,
                "rettype": "vcv",
                "is_variationid": "true",
                "from_esearch": "true",
            },
            timeout=self.timeout_seconds,
        ) as response:
            response.raise_for_status()
            return read_capped_response_text(response, max_bytes=self.max_xml_bytes)


def read_capped_response_text(response: httpx.Response, *, max_bytes: int) -> str:
    max_bytes = _effective_max_xml_bytes(max_bytes)
    content_length = response.headers.get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError:
            declared_length = None
        if declared_length is not None and declared_length > max_bytes:
            raise ClinVarVcvSizeLimitError(
                max_bytes=max_bytes,
                observed_bytes=declared_length,
            )

    observed = 0
    buffer = io.BytesIO()
    for chunk in response.iter_bytes():
        observed += len(chunk)
        if observed > max_bytes:
            raise ClinVarVcvSizeLimitError(max_bytes=max_bytes, observed_bytes=observed)
        buffer.write(chunk)
    return buffer.getvalue().decode(response.encoding or "utf-8", errors="replace")


def clinvar_vcv_xml_from_raw(raw: Any) -> str | None:
    if isinstance(raw, str) and "<ClinVarResult-Set" in raw:
        return raw
    if isinstance(raw, Mapping):
        xml_text = raw.get(_VCV_XML_CACHE_KEY)
        if isinstance(xml_text, str) and xml_text.strip():
            return xml_text
    return None


def store_clinvar_vcv_xml(raw: Any, xml_text: str) -> None:
    if isinstance(raw, MutableMapping) and xml_text.strip():
        raw[_VCV_XML_CACHE_KEY] = xml_text


def clinvar_vcv_parse_result(
    raw: Any,
    *,
    xml_text: str | None = None,
    max_xml_bytes: int = DEFAULT_CLINVAR_VCV_MAX_XML_BYTES,
) -> ClinVarVcvParseResult:
    max_xml_bytes = _effective_max_xml_bytes(max_xml_bytes)
    if isinstance(raw, MutableMapping):
        cached = raw.get(_PARSE_RESULT_CACHE_KEY)
        if isinstance(cached, ClinVarVcvParseResult) and cached.max_xml_bytes == max_xml_bytes:
            return cached

    text = xml_text or clinvar_vcv_xml_from_raw(raw)
    if not text:
        return ClinVarVcvParseResult()

    result = _parse_result_from_text(text, max_xml_bytes=max_xml_bytes)
    if isinstance(raw, MutableMapping):
        raw[_PARSE_RESULT_CACHE_KEY] = result
    return result


def _parse_result_from_text(
    xml_text: str,
    *,
    max_xml_bytes: int,
) -> ClinVarVcvParseResult:
    max_xml_bytes = _effective_max_xml_bytes(max_xml_bytes)
    if len(xml_text) > max_xml_bytes:
        return ClinVarVcvParseResult(
            error_code="xml_too_large",
            max_xml_bytes=max_xml_bytes,
        )
    if len(xml_text.encode("utf-8")) > max_xml_bytes:
        return ClinVarVcvParseResult(
            error_code="xml_too_large",
            max_xml_bytes=max_xml_bytes,
        )
    try:
        extraction = _parse_vcv_texts(xml_text)
    except ET.ParseError:
        return ClinVarVcvParseResult(
            error_code="parse_failed",
            max_xml_bytes=max_xml_bytes,
        )
    return ClinVarVcvParseResult(extraction=extraction, max_xml_bytes=max_xml_bytes)


def _parse_vcv_texts(xml_text: str) -> ClinVarVcvExtraction:
    buckets: dict[str, list[str]] = {tag: [] for tag in _TARGET_TAGS}
    target_depth = 0
    for event, elem in ET.iterparse(io.StringIO(xml_text), events=("start", "end")):
        tag_name = _local_name(elem.tag)
        if event == "start":
            if target_depth > 0 or tag_name in _TARGET_TAGS:
                target_depth += 1
            continue

        if tag_name in _TARGET_TAGS:
            text = "".join(elem.itertext()).strip()
            if text:
                buckets[tag_name].append(text)
        if target_depth > 0:
            target_depth -= 1
        if target_depth == 0:
            elem.clear()

    return ClinVarVcvExtraction(
        comment_texts=tuple(buckets["Comment"]),
        attribute_texts=tuple(buckets["Attribute"]),
        description_texts=tuple(buckets["Description"]),
    )


def _effective_max_xml_bytes(max_xml_bytes: int) -> int:
    return max_xml_bytes if max_xml_bytes > 0 else DEFAULT_CLINVAR_VCV_MAX_XML_BYTES


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]

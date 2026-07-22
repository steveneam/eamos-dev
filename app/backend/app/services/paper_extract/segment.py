"""Deterministic page section and bounded evidence-window segmentation."""

from __future__ import annotations

import re
from dataclasses import dataclass

_KNOWN_HEADINGS = {
    "abstract": "Abstract",
    "introduction": "Introduction",
    "background": "Background",
    "methods": "Methods",
    "materials and methods": "Methods",
    "patients and methods": "Methods",
    "results": "Results",
    "discussion": "Discussion",
    "conclusion": "Conclusion",
    "conclusions": "Conclusion",
    "references": "References",
    "bibliography": "References",
    "supplementary methods": "Supplementary Methods",
    "supplementary results": "Supplementary Results",
}
_HEADING_RE = re.compile(r"(?m)^[ \t]*(?P<label>[A-Za-z][A-Za-z &-]{1,48})[ \t]*:?\s*$")
_CITATION_LINE_RE = re.compile(r"(?m)^[ \t]*(?:\[?\d{1,3}\]?\.?|[A-Z][A-Za-z'-]+,?\s+[A-Z])\s+")
_CAPTION_LINE_RE = re.compile(
    r"(?mi)^[ \t]*(?P<label>(?:supplementary[ \t]+)?(?:fig(?:ure)?\.?|table))"
    r"[ \t]+(?:[A-Z]?[0-9]{1,4}|[IVXLC]{1,8})\b[^\r\n]*(?:\r?\n|$)"
)


@dataclass(frozen=True, slots=True)
class SectionSpan:
    label: str
    start: int
    end: int


def segment_page(text: str) -> tuple[SectionSpan, ...]:
    headings: list[tuple[int, int, str]] = []
    for match in _HEADING_RE.finditer(text):
        canonical = _KNOWN_HEADINGS.get(match.group("label").strip().lower())
        if canonical:
            headings.append((match.start(), match.end(), canonical))

    if not any(label == "References" for _start, _end, label in headings):
        reference_start = _headerless_reference_start(text)
        if reference_start is not None:
            headings.append((reference_start, reference_start, "References"))
            headings.sort()

    if not headings:
        base_spans = (SectionSpan(label="Body", start=0, end=len(text)),)
        return _overlay_caption_lines(text, base_spans)

    spans: list[SectionSpan] = []
    first_start = headings[0][0]
    if first_start > 0:
        spans.append(SectionSpan(label="Body", start=0, end=first_start))
    for index, (_start, heading_end, label) in enumerate(headings):
        next_start = headings[index + 1][0] if index + 1 < len(headings) else len(text)
        spans.append(SectionSpan(label=label, start=heading_end, end=next_start))
    return _overlay_caption_lines(
        text,
        tuple(span for span in spans if span.start <= span.end),
    )


def section_at(spans: tuple[SectionSpan, ...], position: int) -> SectionSpan:
    for span in spans:
        if span.start <= position <= span.end:
            return span
    return spans[-1] if spans else SectionSpan(label="Body", start=0, end=0)


def sentence_window(text: str, start: int, end: int, section: SectionSpan) -> tuple[int, int]:
    lower_bound = max(section.start, start - 320)
    upper_bound = min(section.end, end + 320)
    before = text[lower_bound:start]
    after = text[end:upper_bound]

    sentence_start = lower_bound
    for match in re.finditer(r"(?:[.!?]\s+|\n+)", before):
        sentence_start = lower_bound + match.end()
    sentence_end = upper_bound
    boundary = re.search(r"(?:[.!?](?:\s+|$)|\n+)", after)
    if boundary:
        sentence_end = end + boundary.end()
    return sentence_start, sentence_end


def bounded_quote(
    text: str,
    start: int,
    end: int,
    section: SectionSpan,
    *,
    max_characters: int = 180,
) -> str:
    sentence_start, sentence_end = sentence_window(text, start, end, section)
    left_budget = min(24, max(0, (max_characters - (end - start)) // 2))
    quote_start = max(sentence_start, start - left_budget)
    quote_end = min(sentence_end, end + left_budget, quote_start + max_characters)
    if quote_end < end:
        quote_end = end
        quote_start = max(sentence_start, quote_end - max_characters)
    return text[quote_start:quote_end].strip()


def _headerless_reference_start(text: str) -> int | None:
    candidates = [match.start() for match in _CITATION_LINE_RE.finditer(text)]
    if len(candidates) < 3:
        return None
    threshold = int(len(text) * 0.55)
    tail = [position for position in candidates if position >= threshold]
    return tail[0] if len(tail) >= 3 else None


def _overlay_caption_lines(
    text: str,
    base_spans: tuple[SectionSpan, ...],
) -> tuple[SectionSpan, ...]:
    captions = [
        SectionSpan(
            label=(
                "Table caption" if "table" in match.group("label").lower() else "Figure caption"
            ),
            start=match.start(),
            end=match.end(),
        )
        for match in _CAPTION_LINE_RE.finditer(text)
    ]
    if not captions:
        return base_spans

    spans: list[SectionSpan] = []
    for base in base_spans:
        if base.label == "References":
            spans.append(base)
            continue
        cursor = base.start
        for caption in captions:
            caption_start = max(base.start, caption.start)
            caption_end = min(base.end, caption.end)
            if caption_start >= caption_end:
                continue
            if cursor < caption_start:
                spans.append(SectionSpan(label=base.label, start=cursor, end=caption_start))
            spans.append(
                SectionSpan(
                    label=caption.label,
                    start=caption_start,
                    end=caption_end,
                )
            )
            cursor = caption_end
        if cursor <= base.end:
            spans.append(SectionSpan(label=base.label, start=cursor, end=base.end))
    return tuple(spans)

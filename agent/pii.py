from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_FLAGS = re.IGNORECASE | re.UNICODE

_BANK_CONTEXT = re.compile(
    r"(?:\bstk\b|\bs[oố]\s*t[aà]i\s*kho[aả]n\b|\bso\s*tk\b|\bt[aà]i\s*kho[aả]n\b|\bacc(?:ount)?(?:\s*(?:no|number|num))?\b)"
    r"[^\d\n]{0,15}?(?P<v>\d(?:[ -]?\d){7,15})(?!\d)",
    _FLAGS,
)
_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}", _FLAGS)
_CCCD = re.compile(r"(?<![\d])\d{12}(?!\d)")
_PHONE = re.compile(r"(?<![\w+])(?:\+84(?:[\s.-]?\d){9}|0(?:[\s.-]?\d){9})(?!\d)")
_BANK = re.compile(r"(?<!\d)\d{9,16}(?!\d)")

_TYPE_MAP = {
    "CCCD": "VN_CCCD",
    "PHONE": "VN_PHONE",
    "BANK_ACCOUNT": "VN_BANK_ACCOUNT",
    "EMAIL": "EMAIL",
}
_REVERSE_MAP = {v: k for k, v in _TYPE_MAP.items()}


def _overlaps(start: int, end: int, spans: List[tuple]) -> bool:
    return any(start < e and s < end for s, e in spans)


def detect(text: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    taken: List[tuple] = []

    def add(kind: str, start: int, end: int, confidence: float) -> None:
        if _overlaps(start, end, taken):
            return
        taken.append((start, end))
        results.append(
            {
                "pattern_type": kind,
                "type": _TYPE_MAP[kind],
                "start": start,
                "end": end,
                "value": text[start:end],
                "confidence": confidence,
            }
        )

    for m in _BANK_CONTEXT.finditer(text):
        add("BANK_ACCOUNT", m.start("v"), m.end("v"), 0.95)
    for m in _EMAIL.finditer(text):
        add("EMAIL", m.start(), m.end(), 0.99)
    for m in _CCCD.finditer(text):
        add("CCCD", m.start(), m.end(), 0.9)
    for m in _PHONE.finditer(text):
        add("PHONE", m.start(), m.end(), 0.9)
    for m in _BANK.finditer(text):
        add("BANK_ACCOUNT", m.start(), m.end(), 0.6)

    results.sort(key=lambda d: d["start"])
    return results


def redact(text: str, detections: Optional[List[Dict[str, Any]]] = None) -> str:
    if detections is None:
        detections = detect(text)
    ordered = sorted(detections, key=lambda d: d["start"], reverse=True)
    last_start = len(text) + 1
    for d in ordered:
        if d["end"] > last_start:
            continue
        kind = d.get("pattern_type") or _REVERSE_MAP.get(d.get("type", ""), d.get("type", "PII"))
        text = text[: d["start"]] + f"[REDACTED-{kind}]" + text[d["end"] :]
        last_start = d["start"]
    return text

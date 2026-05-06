"""Analiza transkrypcji przez OpenAI GPT — port z gui/ai_worker.py."""
from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """\
Jesteś ekspertem od tworzenia viralowych YouTube Shorts dla kanału motoryzacyjnego @AUTOmatyczni.

Poniżej masz transkrypcję materiału wideo z dokładnymi znacznikami czasu.
Przeanalizuj całą treść i wybierz od 3 do 6 najlepszych fragmentów nadających się na Shorts (15–60 sekund każdy).

KRYTERIA WYBORU:
- Emocjonalne momenty: zaskoczenie, śmiech, szok, napięcie
- Konkretna, kompletna informacja / ciekawostka / porada — ma sens BEZ kontekstu całego materiału
- Mocny początek: pierwsze 3 sekundy muszą zatrzymać przewijanie
- Akcja na ekranie: dynamiczna jazda, efekt, zmiana tempa
- Unikaj: fragmentów urwanych w połowie zdania, wstępów, pożegnań, reklam

TRANSKRYPCJA (format: [MM:SS] tekst):
{transcript}

Odpowiedz WYŁĄCZNIE w formacie JSON (bez żadnego tekstu przed ani po):
{{
  "proposals": [
    {{
      "title": "Krótka nazwa robocza (max 60 znaków)",
      "start_s": 12.5,
      "end_s": 47.0,
      "reason": "Jedno zdanie dlaczego ten fragment będzie viralowy"
    }}
  ]
}}

Upewnij się że start_s i end_s to liczby dziesiętne (sekundy), a każdy fragment trwa 15–60 sekund.
"""


def build_transcript_text(segments: List[dict]) -> str:
    lines = []
    for seg in segments:
        start = seg.get("start", 0)
        text = seg.get("text", "").strip()
        mm = int(start) // 60
        ss = int(start) % 60
        lines.append(f"[{mm:02d}:{ss:02d}] {text}")
    return "\n".join(lines)


async def analyze_transcript(
    segments: List[dict],
    api_key: str,
    model: str = "gpt-4o-mini",
    progress_fn=None,
) -> List[dict]:
    """Wysyła transkrypcję do OpenAI i zwraca listę propozycji."""
    from openai import AsyncOpenAI

    transcript_text = build_transcript_text(segments)
    if not transcript_text.strip():
        return []

    prompt = PROMPT_TEMPLATE.format(transcript=transcript_text)

    if progress_fn:
        await progress_fn(f"Analizuję transkrypcję przez OpenAI {model}…")

    client = AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000,
    )

    raw = response.choices[0].message.content or ""
    proposals = _parse_proposals(raw)
    return proposals


def _parse_proposals(raw: str) -> List[dict]:
    for attempt in (_parse_plain, _parse_fence, _parse_regex):
        result = attempt(raw)
        if result:
            return result
    logger.warning("Nie udało się sparsować odpowiedzi AI: %s", raw[:200])
    return []


def _parse_plain(raw: str) -> List[dict]:
    try:
        return _validate(json.loads(raw).get("proposals", []))
    except Exception:
        return []


def _parse_fence(raw: str) -> List[dict]:
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        try:
            return _validate(json.loads(m.group(1)).get("proposals", []))
        except Exception:
            pass
    return []


def _parse_regex(raw: str) -> List[dict]:
    m = re.search(r'\{"proposals".*\}', raw, re.DOTALL)
    if m:
        try:
            return _validate(json.loads(m.group(0)).get("proposals", []))
        except Exception:
            pass
    return []


def _validate(raw_list: list) -> List[dict]:
    valid = []
    for item in raw_list:
        try:
            start = float(item["start_s"])
            end = float(item["end_s"])
            duration = end - start
            if duration < 5 or duration > 120 or start < 0 or end <= start:
                continue
            valid.append({
                "title": str(item.get("title", f"Fragment {len(valid)+1}"))[:80],
                "start_s": start,
                "end_s": end,
                "duration_s": duration,
                "reason": str(item.get("reason", ""))[:300],
            })
        except (KeyError, ValueError, TypeError):
            continue
    return valid

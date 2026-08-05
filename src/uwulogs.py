from __future__ import annotations

import csv
from pathlib import Path
from typing import Any
import re
import unicodedata
from urllib.parse import quote

import requests

from models import ParseResult


EXCLUDED_BOSS_TERMS = (
    "toravon",
    "halion",
    "anub",
    "valithria",
    "valy",
)

EXCLUDED_BOSS_IDS = {38433, 39863, 34564, 36789}

# UwULogs class_i order follows c_player_classes.py:
# 0 DK, 1 Druid, 2 Hunter, 3 Mage, 4 Paladin, 5 Priest,
# 6 Rogue, 7 Shaman, 8 Warlock, 9 Warrior.
# Only these specializations are relevant for this report.
ALLOWED_SPECIALIZATIONS: dict[tuple[int, int], str] = {
    (0, 3): "Unholy",
    (1, 1): "Balance",
    (1, 2): "Feral DPS",
    (2, 2): "Marksmanship",
    (3, 2): "Fire",
    (4, 3): "Retribution",
    (5, 3): "Shadow",
    (6, 2): "Combat",
    (8, 2): "Demonology",
    (9, 2): "Fury",
}

SPEC_ALIASES = {
    "fwar": "Fury",
    "fury": "Fury",
    "fury warrior": "Fury",
    "combat": "Combat",
    "ret": "Retribution",
    "retribution": "Retribution",
    "uh": "Unholy",
    "unholy": "Unholy",
    "feraldps": "Feral DPS",
    "feral dps": "Feral DPS",
    "feral combat": "Feral DPS",
    "magefeu": "Fire",
    "feu": "Fire",
    "fire": "Fire",
    "boomie": "Balance",
    "balance": "Balance",
    "sp": "Shadow",
    "shadow": "Shadow",
    "demono": "Demonology",
    "demonology": "Demonology",
    "mm": "Marksmanship",
    "marksmanship": "Marksmanship",
}


def _normalized_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _canonical_spec_name(value: object) -> str | None:
    normalized = _normalized_text(value)
    compact = normalized.replace(" ", "")
    return SPEC_ALIASES.get(normalized) or SPEC_ALIASES.get(compact)


def _is_excluded_boss(key: object, boss_data: dict[str, Any]) -> bool:
    numeric_candidates = [key, boss_data.get("id"), boss_data.get("npc_id"), boss_data.get("boss_id")]
    for candidate in numeric_candidates:
        try:
            if int(candidate) in EXCLUDED_BOSS_IDS:
                return True
        except (TypeError, ValueError):
            pass

    text_candidates = [
        key,
        boss_data.get("name"),
        boss_data.get("boss"),
        boss_data.get("boss_name"),
        boss_data.get("encounter"),
        boss_data.get("encounter_name"),
    ]
    combined = " ".join(_normalized_text(value) for value in text_candidates)
    return any(term in combined for term in EXCLUDED_BOSS_TERMS)


class UwULogsClient:
    def __init__(self, base_url: str = "https://uwu-logs.xyz", timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def character_url(self, server: str, name: str, spec: int) -> str:
        return (
            f"{self.base_url}/character?"
            f"name={quote(name)}&server={quote(server)}&spec={spec}"
        )

    def fetch_character(self, server: str, name: str, spec: int) -> dict[str, Any]:
        endpoint = (
            f"{self.base_url}/character/"
            f"{quote(server, safe='')}/{quote(name, safe='')}/{spec}"
        )
        response = requests.get(
            endpoint,
            timeout=self.timeout,
            headers={"User-Agent": "RaidPresenceReporter/0.1.3"},
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Réponse UwULogs invalide")
        return data

    @staticmethod
    def _normalize_parse(value: float | int | None) -> float | None:
        if value is None:
            return None

        result = float(value)
        if abs(result) > 100:
            result = result / 100.0
        return round(result, 1)

    @classmethod
    def _number(cls, data: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = data.get(key)
            if isinstance(value, (int, float)):
                return cls._normalize_parse(value)
        return None

    def _result_from_data(
        self,
        main: str,
        character: str,
        server: str,
        spec: int,
        spec_name: str,
        data: dict[str, Any],
    ) -> ParseResult:
        bosses = data.get("bosses")
        bosses = bosses if isinstance(bosses, dict) else {}

        rank = data.get("overall_rank")
        rank = int(rank) if isinstance(rank, (int, float)) else None

        included_parses: list[float] = []
        for boss_key, boss_data in bosses.items():
            if not isinstance(boss_data, dict):
                continue
            if _is_excluded_boss(boss_key, boss_data):
                continue
            candidate = self._number(
                boss_data,
                "points",
                "parse",
                "rank_percent",
                "dps_percent",
            )
            if candidate is not None:
                included_parses.append(candidate)

        parse_average = (
            round(sum(included_parses) / len(included_parses), 1)
            if included_parses else None
        )
        best_parse = max(included_parses) if included_parses else None

        return ParseResult(
            main=main,
            character=character,
            spec=spec_name,
            overall_points=parse_average,
            overall_rank=rank,
            best_parse=best_parse,
            boss_count=len(included_parses),
            source_url=self.character_url(server, character, spec),
            status="OK" if included_parses else "Aucun parse ICC retenu",
        )

    def best_for_character(
        self,
        main: str,
        character: str,
        server: str,
    ) -> ParseResult:
        results: list[ParseResult] = []
        errors: list[str] = []
        detected_class: int | None = None

        # We query the three tree indexes, but keep only the selected tree for
        # the detected class. This is robust even when UwULogs' default spec differs.
        for spec in (1, 2, 3):
            try:
                data = self.fetch_character(server, character, spec)
                class_i_raw = data.get("class_i")
                class_i = int(class_i_raw) if isinstance(class_i_raw, (int, float, str)) else None
                if class_i is not None:
                    detected_class = class_i

                spec_name = ALLOWED_SPECIALIZATIONS.get((class_i, spec)) if class_i is not None else None
                if not spec_name:
                    continue

                results.append(
                    self._result_from_data(
                        main,
                        character,
                        server,
                        spec,
                        spec_name,
                        data,
                    )
                )

            except Exception as exc:
                errors.append(f"spec {spec}: {exc}")

        if results:
            return max(
                results,
                key=lambda result: (
                    result.overall_points
                    if result.overall_points is not None
                    else result.best_parse
                    if result.best_parse is not None
                    else -1
                ),
            )

        if detected_class is not None:
            return ParseResult(
                main=main,
                character=character,
                status="Spécialisation ignorée pour cette classe",
            )

        return ParseResult(
            main=main,
            character=character,
            source_url=self.character_url(server, character, 1),
            status="Indisponible - " + " | ".join(errors[:2]),
        )


def load_manual_csv(path: str | Path) -> list[ParseResult]:
    if not path:
        return []

    results: list[ParseResult] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            canonical_spec = _canonical_spec_name(row.get("spec"))
            if not canonical_spec:
                continue

            def number(name: str) -> float | None:
                raw = (row.get(name) or "").strip().replace(",", ".")
                try:
                    if not raw:
                        return None
                    value = float(raw)
                    if abs(value) > 100:
                        value = value / 100.0
                    return round(value, 1)
                except ValueError:
                    return None

            def integer(name: str) -> int | None:
                raw = (row.get(name) or "").strip()
                try:
                    return int(float(raw)) if raw else None
                except ValueError:
                    return None

            results.append(
                ParseResult(
                    main=(row.get("main") or "").strip(),
                    character=(row.get("character") or "").strip(),
                    spec=canonical_spec,
                    overall_points=number("overall_points"),
                    overall_rank=integer("overall_rank"),
                    best_parse=number("best_parse"),
                    source_url=(row.get("source_url") or "").strip(),
                    status="Import CSV",
                )
            )
    return results

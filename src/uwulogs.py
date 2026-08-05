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

# Identifiants connus, utilisés seulement lorsque UwULogs fournit un ID numérique.
EXCLUDED_BOSS_IDS = {38433, 39863, 34564, 36789}


def _normalized_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


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
            headers={"User-Agent": "RaidPresenceReporter/0.1.2"},
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _normalize_parse(value: float | int | None) -> float | None:
        if value is None:
            return None

        result = float(value)

        # UwULogs renvoie parfois les pourcentages multipliés par 100
        # (ex. 8934.18 pour un parse de 89.34).
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

    def best_for_character(
        self,
        main: str,
        character: str,
        server: str,
    ) -> ParseResult:
        best: ParseResult | None = None
        errors: list[str] = []

        for spec in (1, 2, 3):
            try:
                data = self.fetch_character(server, character, spec)
                bosses = data.get("bosses") if isinstance(data, dict) else {}
                bosses = bosses if isinstance(bosses, dict) else {}

                points = self._number(data, "overall_points", "points")
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

                # Le score du personnage est recalculé uniquement avec les boss retenus.
                parse_average = (
                    round(sum(included_parses) / len(included_parses), 1)
                    if included_parses else None
                )
                best_parse = max(included_parses) if included_parses else None

                result = ParseResult(
                    main=main,
                    character=character,
                    spec=str(spec),
                    overall_points=parse_average,
                    overall_rank=rank,
                    best_parse=best_parse,
                    boss_count=len(included_parses),
                    source_url=self.character_url(server, character, spec),
                    status="OK",
                )

                score = (
                    result.overall_points if result.overall_points is not None
                    else result.best_parse if result.best_parse is not None
                    else -1
                )
                previous = (
                    best.overall_points if best and best.overall_points is not None
                    else best.best_parse if best and best.best_parse is not None
                    else -1
                )
                if best is None or score > previous:
                    best = result

            except Exception as exc:
                errors.append(f"spec {spec}: {exc}")

        if best:
            return best

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
                value = number(name)
                return int(value) if value is not None else None

            results.append(
                ParseResult(
                    main=(row.get("main") or "").strip(),
                    character=(row.get("character") or "").strip(),
                    spec=(row.get("spec") or "").strip(),
                    overall_points=number("overall_points"),
                    overall_rank=integer("overall_rank"),
                    best_parse=number("best_parse"),
                    source_url=(row.get("source_url") or "").strip(),
                    status="Import CSV",
                )
            )
    return results

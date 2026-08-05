from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


DIFFICULTIES = {
    1: "10 Normal",
    2: "25 Normal",
    3: "10 Heroic",
    4: "25 Heroic",
    5: "5 Normal",
    6: "5 Heroic",
}


@dataclass
class BossKill:
    raid_id: str
    npc_id: int
    date: datetime
    instance: str
    difficulty_id: int | None
    difficulty: str
    temporary: bool


@dataclass
class Attendance:
    raid_id: str
    npc_id: int
    main: str
    character: str
    date: datetime


@dataclass
class ParseResult:
    main: str
    character: str
    spec: str = ""
    overall_points: float | None = None
    overall_rank: int | None = None
    best_parse: float | None = None
    boss_count: int = 0
    source_url: str = ""
    status: str = ""


@dataclass
class ReportData:
    bosses: list[BossKill] = field(default_factory=list)
    attendance: list[Attendance] = field(default_factory=list)
    characters_by_main: dict[str, set[str]] = field(default_factory=dict)
    parses: list[ParseResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

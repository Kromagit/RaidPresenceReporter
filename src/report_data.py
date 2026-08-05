from __future__ import annotations

from datetime import datetime
from typing import Any

from models import Attendance, BossKill, DIFFICULTIES, ReportData


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_report_data(db: dict[str, Any], include_tests: bool = False) -> ReportData:
    output = ReportData()
    raids = db.get("raids", {})
    if not isinstance(raids, dict):
        return output

    for raid_id, raid in raids.items():
        if not isinstance(raid, dict):
            continue

        temporary = bool(
            raid.get("temporary") is True
            or raid.get("sessionType") == "DUNGEON_TEST"
        )
        if temporary and not include_tests:
            continue

        instance = str(raid.get("instance") or "")
        raid_ts = _as_int(raid.get("date")) or 0
        bosses = raid.get("bosses", {})

        if isinstance(bosses, dict):
            for npc_raw, boss in bosses.items():
                npc_id = _as_int(npc_raw)
                if npc_id is None:
                    continue

                if boss is True:
                    boss = {}
                if not isinstance(boss, dict):
                    boss = {}

                timestamp = _as_int(boss.get("timestamp")) or raid_ts
                difficulty_id = _as_int(boss.get("difficulty"))

                output.bosses.append(
                    BossKill(
                        raid_id=str(raid_id),
                        npc_id=npc_id,
                        date=datetime.fromtimestamp(timestamp),
                        instance=instance,
                        difficulty_id=difficulty_id,
                        difficulty=DIFFICULTIES.get(difficulty_id, "Inconnue"),
                        temporary=temporary,
                    )
                )

        players = raid.get("players", {})
        if not isinstance(players, dict):
            continue

        for main_name, player in players.items():
            if not isinstance(player, dict):
                continue

            main = str(player.get("main") or main_name)
            chars = output.characters_by_main.setdefault(main, set())

            characters = player.get("characters", {})
            if isinstance(characters, dict):
                chars.update(str(c) for c, present in characters.items() if present)

            attendance = player.get("attendance", {})
            if not isinstance(attendance, dict):
                continue

            for npc_raw, presence in attendance.items():
                npc_id = _as_int(npc_raw)
                if npc_id is None:
                    continue

                if isinstance(presence, dict):
                    character = str(presence.get("character") or main)
                    timestamp = _as_int(presence.get("timestamp")) or raid_ts
                else:
                    character = main
                    timestamp = raid_ts

                chars.add(character)
                output.attendance.append(
                    Attendance(
                        raid_id=str(raid_id),
                        npc_id=npc_id,
                        main=main,
                        character=character,
                        date=datetime.fromtimestamp(timestamp),
                    )
                )

    output.bosses.sort(key=lambda row: (row.date, row.raid_id, row.npc_id))
    output.attendance.sort(key=lambda row: (row.date, row.main, row.npc_id))
    return output

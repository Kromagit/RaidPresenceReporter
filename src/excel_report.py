from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

import xlsxwriter

from models import ParseResult, ReportData


def _best_parse_by_main(parses: Iterable[ParseResult]) -> dict[str, ParseResult]:
    best: dict[str, ParseResult] = {}
    for row in parses:
        score = (
            row.overall_points if row.overall_points is not None
            else row.best_parse if row.best_parse is not None
            else -1
        )
        previous = best.get(row.main)
        previous_score = (
            previous.overall_points if previous and previous.overall_points is not None
            else previous.best_parse if previous and previous.best_parse is not None
            else -1
        )
        if previous is None or score > previous_score:
            best[row.main] = row
    return best


def create_excel(
    output_path: str | Path,
    data: ReportData,
    start_date: date,
    end_date: date,
    include_tests: bool,
) -> None:
    bosses = [b for b in data.bosses if start_date <= b.date.date() <= end_date]
    boss_keys = {(b.raid_id, b.npc_id) for b in bosses}
    attendance = [
        a for a in data.attendance
        if start_date <= a.date.date() <= end_date
        and (a.raid_id, a.npc_id) in boss_keys
    ]

    mains = sorted(
        set(data.characters_by_main)
        | {a.main for a in attendance}
        | {p.main for p in data.parses}
    )

    present_by_main: dict[str, set[tuple[str, int]]] = defaultdict(set)
    char_used: dict[str, set[str]] = defaultdict(set)
    for row in attendance:
        present_by_main[row.main].add((row.raid_id, row.npc_id))
        char_used[row.main].add(row.character)

    best_parse = _best_parse_by_main(data.parses)
    total_bosses = len(boss_keys)

    workbook = xlsxwriter.Workbook(str(output_path))
    workbook.set_properties({
        "title": "Rapport RaidPresence",
        "subject": "Présences et parses UwULogs",
        "author": "RaidPresence Reporter",
    })

    fmt_title = workbook.add_format({
        "bold": True, "font_size": 18, "font_color": "#FFFFFF",
        "bg_color": "#203864", "align": "center", "valign": "vcenter"
    })
    fmt_header = workbook.add_format({
        "bold": True, "font_color": "#FFFFFF", "bg_color": "#4472C4",
        "border": 1, "align": "center", "valign": "vcenter"
    })
    fmt_cell = workbook.add_format({"border": 1, "valign": "top"})
    fmt_center = workbook.add_format({"border": 1, "align": "center"})
    fmt_pct = workbook.add_format({"border": 1, "num_format": "0.0%"})
    fmt_date = workbook.add_format({"border": 1, "num_format": "dd/mm/yyyy hh:mm"})
    fmt_kpi = workbook.add_format({
        "bold": True, "font_size": 14, "align": "center",
        "bg_color": "#D9EAF7", "border": 1
    })
    fmt_note = workbook.add_format({"italic": True, "font_color": "#666666"})
    fmt_link = workbook.add_format({"font_color": "blue", "underline": True, "border": 1})

    # Tableau de bord
    ws = workbook.add_worksheet("Tableau de bord")
    ws.hide_gridlines(2)
    ws.merge_range("A1:H2", "RaidPresence Reporter", fmt_title)
    ws.write("A4", "Période", fmt_header)
    ws.write("B4", f"{start_date:%d/%m/%Y} au {end_date:%d/%m/%Y}", fmt_cell)
    ws.write("A5", "Sessions de test incluses", fmt_header)
    ws.write("B5", "Oui" if include_tests else "Non", fmt_cell)
    ws.write("A7", "Boss enregistrés", fmt_header)
    ws.write("B7", total_bosses, fmt_kpi)
    ws.write("D7", "Mains", fmt_header)
    ws.write("E7", len(mains), fmt_kpi)
    ws.write("G7", "Présences", fmt_header)
    ws.write("H7", len(attendance), fmt_kpi)

    summary_start = 10
    headers = ["Main", "Boss présents", "Boss total", "Présence", "Meilleur personnage", "Points UwU", "Best parse", "Statut"]
    for col, value in enumerate(headers):
        ws.write(summary_start, col, value, fmt_header)

    for idx, main in enumerate(mains, summary_start + 1):
        p = best_parse.get(main)
        count = len(present_by_main.get(main, set()))
        ws.write(idx, 0, main, fmt_cell)
        ws.write(idx, 1, count, fmt_center)
        ws.write(idx, 2, total_bosses, fmt_center)
        ws.write_formula(idx, 3, f'=IF(C{idx+1}=0,0,B{idx+1}/C{idx+1})', fmt_pct)
        ws.write(idx, 4, p.character if p else "", fmt_cell)
        ws.write(idx, 5, p.overall_points if p and p.overall_points is not None else "", fmt_center)
        ws.write(idx, 6, p.best_parse if p and p.best_parse is not None else "", fmt_center)
        ws.write(idx, 7, p.status if p else "Aucune donnée", fmt_cell)

    if mains:
        ws.conditional_format(summary_start + 1, 3, summary_start + len(mains), 3, {
            "type": "3_color_scale",
            "min_color": "#F8696B", "mid_color": "#FFEB84", "max_color": "#63BE7B"
        })
        chart = workbook.add_chart({"type": "column"})
        chart.add_series({
            "name": "Présence",
            "categories": ["Tableau de bord", summary_start + 1, 0, summary_start + len(mains), 0],
            "values": ["Tableau de bord", summary_start + 1, 3, summary_start + len(mains), 3],
            "data_labels": {"value": True, "num_format": "0%"},
        })
        chart.set_title({"name": "Taux de présence par main"})
        chart.set_y_axis({"num_format": "0%", "min": 0, "max": 1})
        chart.set_legend({"none": True})
        ws.insert_chart("J4", chart, {"x_scale": 1.25, "y_scale": 1.15})

    ws.set_column("A:A", 20)
    ws.set_column("B:D", 14)
    ws.set_column("E:E", 22)
    ws.set_column("F:G", 13)
    ws.set_column("H:H", 34)
    ws.freeze_panes(summary_start + 1, 0)

    # Présences
    ws = workbook.add_worksheet("Présences")
    headers = ["Main", "Personnage(s)", "Boss présents", "Boss total", "Présence", "Meilleur perso UwU", "Points", "Best parse"]
    for col, value in enumerate(headers):
        ws.write(0, col, value, fmt_header)
    for row_idx, main in enumerate(mains, 1):
        p = best_parse.get(main)
        characters = sorted(data.characters_by_main.get(main, set()) | char_used.get(main, set()))
        ws.write(row_idx, 0, main, fmt_cell)
        ws.write(row_idx, 1, ", ".join(characters), fmt_cell)
        ws.write(row_idx, 2, len(present_by_main.get(main, set())), fmt_center)
        ws.write(row_idx, 3, total_bosses, fmt_center)
        ws.write_formula(row_idx, 4, f'=IF(D{row_idx+1}=0,0,C{row_idx+1}/D{row_idx+1})', fmt_pct)
        ws.write(row_idx, 5, p.character if p else "", fmt_cell)
        ws.write(row_idx, 6, p.overall_points if p and p.overall_points is not None else "", fmt_center)
        ws.write(row_idx, 7, p.best_parse if p and p.best_parse is not None else "", fmt_center)
    ws.autofilter(0, 0, max(len(mains), 1), len(headers) - 1)
    ws.freeze_panes(1, 0)
    ws.set_column("A:A", 20)
    ws.set_column("B:B", 45)
    ws.set_column("C:E", 14)
    ws.set_column("F:F", 22)
    ws.set_column("G:H", 13)

    # Boss
    ws = workbook.add_worksheet("Boss")
    headers = ["Date", "Instance", "NPC ID", "Difficulté", "Présents", "Session", "Temporaire"]
    for col, value in enumerate(headers):
        ws.write(0, col, value, fmt_header)
    attendance_count = defaultdict(int)
    for a in attendance:
        attendance_count[(a.raid_id, a.npc_id)] += 1
    for idx, boss in enumerate(bosses, 1):
        ws.write_datetime(idx, 0, boss.date, fmt_date)
        ws.write(idx, 1, boss.instance, fmt_cell)
        ws.write(idx, 2, boss.npc_id, fmt_center)
        ws.write(idx, 3, boss.difficulty, fmt_cell)
        ws.write(idx, 4, attendance_count[(boss.raid_id, boss.npc_id)], fmt_center)
        ws.write(idx, 5, boss.raid_id, fmt_cell)
        ws.write(idx, 6, "Oui" if boss.temporary else "Non", fmt_center)
    ws.autofilter(0, 0, max(len(bosses), 1), len(headers) - 1)
    ws.freeze_panes(1, 0)
    ws.set_column("A:A", 19)
    ws.set_column("B:B", 25)
    ws.set_column("C:C", 10)
    ws.set_column("D:D", 16)
    ws.set_column("E:E", 10)
    ws.set_column("F:F", 55)
    ws.set_column("G:G", 11)

    # Historique
    ws = workbook.add_worksheet("Historique")
    headers = ["Date", "Main", "Personnage", "Instance", "NPC ID", "Difficulté", "Session"]
    for col, value in enumerate(headers):
        ws.write(0, col, value, fmt_header)
    boss_lookup = {(b.raid_id, b.npc_id): b for b in bosses}
    history = [a for a in attendance if (a.raid_id, a.npc_id) in boss_lookup]
    for idx, row in enumerate(history, 1):
        boss = boss_lookup[(row.raid_id, row.npc_id)]
        ws.write_datetime(idx, 0, row.date, fmt_date)
        ws.write(idx, 1, row.main, fmt_cell)
        ws.write(idx, 2, row.character, fmt_cell)
        ws.write(idx, 3, boss.instance, fmt_cell)
        ws.write(idx, 4, row.npc_id, fmt_center)
        ws.write(idx, 5, boss.difficulty, fmt_cell)
        ws.write(idx, 6, row.raid_id, fmt_cell)
    ws.autofilter(0, 0, max(len(history), 1), len(headers) - 1)
    ws.freeze_panes(1, 0)
    ws.set_column("A:A", 19)
    ws.set_column("B:C", 20)
    ws.set_column("D:D", 25)
    ws.set_column("E:E", 10)
    ws.set_column("F:F", 16)
    ws.set_column("G:G", 55)

    # Parses
    ws = workbook.add_worksheet("Parses UwULogs")
    headers = ["Main", "Personnage", "Spé", "Points globaux", "Rang global", "Best parse", "Boss connus", "Statut", "Source"]
    for col, value in enumerate(headers):
        ws.write(0, col, value, fmt_header)
    for idx, row in enumerate(data.parses, 1):
        ws.write(idx, 0, row.main, fmt_cell)
        ws.write(idx, 1, row.character, fmt_cell)
        ws.write(idx, 2, row.spec, fmt_center)
        ws.write(idx, 3, row.overall_points if row.overall_points is not None else "", fmt_center)
        ws.write(idx, 4, row.overall_rank if row.overall_rank is not None else "", fmt_center)
        ws.write(idx, 5, row.best_parse if row.best_parse is not None else "", fmt_center)
        ws.write(idx, 6, row.boss_count, fmt_center)
        ws.write(idx, 7, row.status, fmt_cell)
        if row.source_url:
            ws.write_url(idx, 8, row.source_url, fmt_link, "Ouvrir")
        else:
            ws.write(idx, 8, "", fmt_cell)
    ws.autofilter(0, 0, max(len(data.parses), 1), len(headers) - 1)
    ws.freeze_panes(1, 0)
    ws.set_column("A:B", 20)
    ws.set_column("C:C", 10)
    ws.set_column("D:G", 14)
    ws.set_column("H:H", 40)
    ws.set_column("I:I", 12)

    # Personnages
    ws = workbook.add_worksheet("Personnages")
    ws.write_row(0, 0, ["Main", "Personnage"], fmt_header)
    row_idx = 1
    for main in sorted(data.characters_by_main):
        for character in sorted(data.characters_by_main[main]):
            ws.write(row_idx, 0, main, fmt_cell)
            ws.write(row_idx, 1, character, fmt_cell)
            row_idx += 1
    ws.autofilter(0, 0, max(row_idx - 1, 1), 1)
    ws.freeze_panes(1, 0)
    ws.set_column("A:B", 24)

    workbook.close()

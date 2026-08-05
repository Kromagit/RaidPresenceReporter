from __future__ import annotations

import calendar
import sys
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from excel_report import create_excel
from lua_savedvars import load_saved_variables
from report_data import build_report_data
from uwulogs import UwULogsClient, load_manual_csv


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RaidPresence Reporter v0.1.1")
        self.geometry("820x600")
        self.minsize(760, 560)

        today = date.today()
        self.lua_path = tk.StringVar()
        self.output_path = tk.StringVar(
            value=str(Path.home() / f"Rapport_RaidPresence_{today:%Y-%m}.xlsx")
        )
        self.csv_path = tk.StringVar()
        self.server = tk.StringVar(value="Icecrown")
        self.period = tk.StringVar(value="Mois en cours")
        self.start_date = tk.StringVar(value=today.replace(day=1).isoformat())
        self.end_date = tk.StringVar(
            value=date(today.year, today.month, calendar.monthrange(today.year, today.month)[1]).isoformat()
        )
        self.include_tests = tk.BooleanVar(value=False)
        self.download_uwu = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Prêt.")

        self._build()

    def _build(self):
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="RaidPresence Reporter", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 16)
        )

        self._path_row(frame, 1, "RaidPresence.lua", self.lua_path, self._pick_lua)
        self._path_row(frame, 2, "Fichier Excel", self.output_path, self._pick_output)
        self._path_row(frame, 3, "CSV UwULogs (optionnel)", self.csv_path, self._pick_csv)

        ttk.Label(frame, text="Serveur UwULogs").grid(row=4, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.server, width=34).grid(row=4, column=1, sticky="ew", pady=6)

        ttk.Label(frame, text="Période").grid(row=5, column=0, sticky="w", pady=6)
        period_box = ttk.Combobox(
            frame,
            textvariable=self.period,
            state="readonly",
            values=[
                "Mois en cours",
                "1re quinzaine",
                "2e quinzaine",
                "Dates personnalisées",
            ],
        )
        period_box.grid(row=5, column=1, sticky="ew", pady=6)
        period_box.bind("<<ComboboxSelected>>", lambda _e: self._update_period())

        ttk.Label(frame, text="Date début (AAAA-MM-JJ)").grid(row=6, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.start_date).grid(row=6, column=1, sticky="ew", pady=6)
        ttk.Label(frame, text="Date fin (AAAA-MM-JJ)").grid(row=7, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.end_date).grid(row=7, column=1, sticky="ew", pady=6)

        ttk.Checkbutton(
            frame,
            text="Télécharger les données publiques UwULogs",
            variable=self.download_uwu,
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(12, 4))

        ttk.Checkbutton(
            frame,
            text="Inclure les sessions temporaires de donjon",
            variable=self.include_tests,
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=4)

        ttk.Button(frame, text="Générer Excel", command=self.generate).grid(
            row=10, column=0, columnspan=2, sticky="ew", pady=(20, 10), ipady=8
        )

        log_frame = ttk.LabelFrame(frame, text="Journal", padding=8)
        log_frame.grid(row=11, column=0, columnspan=3, sticky="nsew", pady=8)
        self.log = tk.Text(log_frame, height=13, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)

        ttk.Label(frame, textvariable=self.status).grid(
            row=12, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(11, weight=1)

    def _path_row(self, frame, row, label, variable, command):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=6)
        ttk.Button(frame, text="Parcourir", command=command).grid(row=row, column=2, padx=(8, 0), pady=6)

    def _pick_lua(self):
        path = filedialog.askopenfilename(filetypes=[("Lua", "*.lua"), ("Tous", "*.*")])
        if path:
            self.lua_path.set(path)

    def _pick_output(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if path:
            self.output_path.set(path)

    def _pick_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("Tous", "*.*")])
        if path:
            self.csv_path.set(path)

    def _update_period(self):
        today = date.today()
        last = calendar.monthrange(today.year, today.month)[1]
        if self.period.get() == "Mois en cours":
            start, end = today.replace(day=1), today.replace(day=last)
        elif self.period.get() == "1re quinzaine":
            start, end = today.replace(day=1), today.replace(day=15)
        elif self.period.get() == "2e quinzaine":
            start, end = today.replace(day=16), today.replace(day=last)
        else:
            return
        self.start_date.set(start.isoformat())
        self.end_date.set(end.isoformat())

    def _write_log(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def generate(self):
        try:
            lua_path = Path(self.lua_path.get())
            if not lua_path.is_file():
                raise ValueError("Sélectionne un fichier RaidPresence.lua valide.")

            output = Path(self.output_path.get())
            start = datetime.strptime(self.start_date.get(), "%Y-%m-%d").date()
            end = datetime.strptime(self.end_date.get(), "%Y-%m-%d").date()
            if end < start:
                raise ValueError("La date de fin doit être après la date de début.")

            self.status.set("Lecture du fichier...")
            self._write_log(f"Lecture : {lua_path}")
            db = load_saved_variables(lua_path)
            data = build_report_data(db, include_tests=self.include_tests.get())
            self._write_log(
                f"{len(data.bosses)} boss/créatures et {len(data.attendance)} présences chargés."
            )

            manual = []
            if self.csv_path.get():
                manual = load_manual_csv(self.csv_path.get())
                self._write_log(f"{len(manual)} ligne(s) UwULogs importée(s) depuis CSV.")

            manual_keys = {(p.main.casefold(), p.character.casefold()) for p in manual}
            data.parses.extend(manual)

            if self.download_uwu.get():
                server = self.server.get().strip()
                if not server:
                    raise ValueError("Renseigne le serveur UwULogs.")

                client = UwULogsClient()
                characters_total = sum(len(v) for v in data.characters_by_main.values())
                done = 0
                for main, characters in sorted(data.characters_by_main.items()):
                    for character in sorted(characters):
                        done += 1
                        if (main.casefold(), character.casefold()) in manual_keys:
                            continue
                        self.status.set(f"UwULogs {done}/{characters_total} : {character}")
                        self._write_log(f"UwULogs : {character} ({main})")
                        data.parses.append(client.best_for_character(main, character, server))

            output.parent.mkdir(parents=True, exist_ok=True)
            self.status.set("Création du fichier Excel...")
            create_excel(
                output,
                data,
                start,
                end,
                include_tests=self.include_tests.get(),
            )
            self._write_log(f"Fichier créé : {output}")
            self.status.set("Terminé.")
            messagebox.showinfo("RaidPresence Reporter", f"Rapport créé :\n{output}")

        except Exception as exc:
            self.status.set("Erreur.")
            self._write_log(f"ERREUR : {exc}")
            messagebox.showerror("Erreur", str(exc))


if __name__ == "__main__":
    App().mainloop()

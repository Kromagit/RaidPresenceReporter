@echo off
py -m PyInstaller --noconfirm --onefile --windowed --name RaidPresenceReporter src\app.py
pause

@echo off
chcp 65001 > nul
title MOXXI 3.0 — Discord Bot (moxxidc)
echo ===================================================
echo   Запуск автономного бота MOXXI для Discord...
echo ===================================================

if exist "..\бот2.0\venv\Scripts\python.exe" (
    "..\бот2.0\venv\Scripts\python.exe" main.py
) else (
    python main.py
)

pause

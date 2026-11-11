@echo off
chcp 65001 > nul
title MOXXI 3.0 — Discord Bot (moxxidc)
echo ===================================================
echo   Запуск автономного бота MOXXI для Discord...
echo   Авто-перезапуск при сбоях ВКЛЮЧЕН!
echo ===================================================

set PYTHON_EXE=..\бот2.0\venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=C:\Users\eiema\OneDrive\Desktop\бот2.0\venv\Scripts\python.exe
)

:loop
echo [%date% %time%] Запуск процесса MOXXI Discord...
"%PYTHON_EXE%" main.py
echo.
echo [!] MOXXI Discord завершился или произошел сетевой сбой (%date% %time%).
echo [!] Автоматический перезапуск через 5 секунд... (Ctrl+C для остановки)
timeout /t 5 > nul
goto loop

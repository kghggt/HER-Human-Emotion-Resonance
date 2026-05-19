@echo off
cd /d "%~dp0"
echo HER v1.0 — Human Emotion Resonance
echo.
echo Starting...
python assistant.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start. Check assistant.log
    pause
)

@echo off
chcp 65001 >nul
title Xiaowei Eval Toolkit
cd /d "%~dp0"

set SUITE=%1
if "%SUITE%"=="" set SUITE=A

echo ============================================================
echo   Xiaowei AI Assistant Eval Toolkit
echo   2026 Software Testing Contest - WeChat Xiaowei Track
echo ============================================================
echo.
echo   Working dir: %cd%
echo   Suite: %SUITE%
echo.

echo [1/4] Self check...
echo.
python selftest.py
if errorlevel 1 (
    echo.
    echo [ERROR] Self check failed. Please send the log above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Self check PASSED. Starting collection.
echo.
echo   For each instruction:
echo     1. Read the instruction shown below
echo     2. Switch to WeChat on phone -> tap the green dots (top-left)
echo        -> paste -> send
echo     3. Wait for the reply -> long press it -> copy
echo     4. Switch back here -> Ctrl+V -> Enter
echo.
echo   Type SKIP + Enter to skip, QUIT + Enter to stop.
echo   IMPORTANT: after each case, long-press the conversation
echo   to DELETE it, so the next case starts with clean context.
echo ============================================================
echo.

python pipeline.py run --suite %SUITE% --mode manual

echo.
echo ============================================================
echo   Collection finished. Now generate the report:
echo.
echo     python pipeline.py report --raw data\raw_%SUITE%.jsonl --suite %SUITE% --docx
echo.
echo   Report will be in: data\reports\
echo ============================================================
pause

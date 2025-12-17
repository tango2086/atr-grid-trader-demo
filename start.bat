@echo off
chcp 65001 >nul
title BIAS-ATR-Grid-Trader 智能交易系统

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║         🤖 BIAS-ATR-Grid-Trader 智能交易系统                  ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"
python run.py

pause

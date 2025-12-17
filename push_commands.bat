@echo off
echo ATR Grid Trader - 推送到 GitHub
echo ================================

echo.
echo [1/3] 设置远程仓库...
git remote add origin https://github.com/tango2086/atr-grid-trader-demo.git

echo.
echo [2/3] 设置主分支...
git branch -M main

echo.
echo [3/3] 推送代码到 GitHub...
git push -u origin main

echo.
echo 完成！请访问 https://github.com/tango2086/atr-grid-trader-demo 查看
echo.
pause
@echo off
echo ========================================
echo Lowe's Scraper - Clean Version
echo ========================================
echo.
echo This scraper uses temporary browser profiles
echo that auto-delete when the browser closes.
echo No disk bloat!
echo.
echo Starting scraper for WA and OR stores...
echo Logs: logs\
echo Output: output\
echo.
python run.py --state WA,OR --workers 5
echo.
echo Done!
pause

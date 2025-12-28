@echo off
echo ========================================
echo PARALLEL Lowe's Scraper
echo ========================================
echo.
echo Runs locally on YOUR computer.
echo No proxies, no Apify needed.
echo.
echo States: WA and OR
echo Stores: 49 total
echo Categories: 605 (optimized list)
echo Workers: 5 browsers in parallel
echo.
echo Output will be in: output\
echo Logs in: logs\
echo Progress saved in: checkpoints\
echo Status files in: status\
echo.
echo Features:
echo   - Auto-resume from checkpoints
echo   - Blocking detection with 5min cooldown
echo   - Human-like mouse movement
echo.
echo Press any key to start...
pause >nul
echo.
echo Starting...
python orchestrator.py --state WA,OR --max-workers 5
echo.
echo Done!
pause

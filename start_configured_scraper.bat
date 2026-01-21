@echo off
echo Starting Configured Intelligent Scraper...
echo Reading configuration from apps/coordinator/data/store_config.json...
set PYTHONIOENCODING=utf-8
REM No --state arg passed, so it will read from config
start "Intelligent Scraper Supervisor" /B cmd /c "python intelligent_scraper.py --max-workers 8 --use-ai > scraper_console_configured.log 2>&1"
echo Scraper started in background.
echo Check scraper_console_configured.log for progress.
python -c "import time; print('Monitoring startup for 5 seconds...'); time.sleep(5)"

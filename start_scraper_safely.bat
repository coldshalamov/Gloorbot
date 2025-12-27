@echo off
echo Starting Intelligent Scraper Orchestrator...
echo Logs will be written to scraper_orchestrator.log
set PYTHONIOENCODING=utf-8
start "Intelligent Scraper Supervisor" /B cmd /c "python intelligent_scraper.py --state WA,OR --max-workers 5 --use-ai > scraper_console.log 2>&1"
echo Scraper started in background.
echo Check scraper_orchestrator.log for progress.
python -c "import time; print('Monitoring startup for 10 seconds...'); time.sleep(10)"

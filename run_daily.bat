@echo off
REM Daily AI News Scraper — Windows Task Scheduler script
REM Add this to Task Scheduler to run automatically every morning

cd /d "%~dp0"
python scraper.py >> output\scraper.log 2>&1

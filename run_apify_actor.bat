@echo off
REM Apify Actor Runner Script for Windows
REM Usage: run_apify_actor.bat [actor_name] [input_file]

setlocal enabledelayedexpansion

set APIFY_TOKEN=apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM
set ACTOR_NAME=%1
if "%ACTOR_NAME%"=="" set ACTOR_NAME=lowes-cheapskate
set INPUT_FILE=%2
if "%INPUT_FILE%"=="" set INPUT_FILE=input.json

if not exist "%INPUT_FILE%" (
    echo Creating default input.json...
    (
        echo {
        echo   "stores": [{"store_id": "0004", "name": "Test Store", "zip": "98144"}],
        echo   "categories": [{"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"}],
        echo   "max_pages_per_category": 2
        echo }
    ) > input.json
    set INPUT_FILE=input.json
)

echo Running actor: one-api/%ACTOR_NAME%
echo Input: %INPUT_FILE%
echo.

curl -X POST -H "Authorization: Bearer %APIFY_TOKEN%" -H "Content-Type: application/json" -d @%INPUT_FILE% "https://api.apify.com/v2/acts/one-api~%ACTOR_NAME%/runs" > response.json

echo.
echo Actor started! Check response.json for run details.
echo.
echo To check status, use:
echo curl -H "Authorization: Bearer %APIFY_TOKEN%" https://api.apify.com/v2/actor-runs/RUN_ID

endlocal

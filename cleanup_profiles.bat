@echo off
echo Cleaning up old playwright profiles...
rmdir /S /Q ".playwright-profiles" 2>nul
rmdir /S /Q "apify_actor_seed\.playwright-profiles" 2>nul
echo.
echo Looking for other profile directories...
for /d %%i in (*playwright*) do (
    echo Removing: %%i
    rmdir /S /Q "%%i" 2>nul
)
echo.
echo Cleanup complete!
pause

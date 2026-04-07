@echo off
setlocal
cd /d "%~dp0"

set PYTHON=C:\Users\Howard\anaconda3\envs\ML\python.exe
set LOG_DIR=%~dp0logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

for /f "tokens=1-3 delims=/- " %%a in ("%DATE%") do set TODAY=%%c-%%a-%%b
set LOGFILE=%LOG_DIR%\pipeline_%TODAY%.log

echo [%DATE% %TIME%] Starting Druckenmiller pipeline >> "%LOGFILE%"

echo Running liquidity-regime...
"%PYTHON%" "liquidity-regime\scripts\liquidity_regime.py" --output-dir public\reports\ >> "%LOGFILE%" 2>&1
if errorlevel 1 (echo [WARN] liquidity-regime failed >> "%LOGFILE%")

echo Running forward-earnings...
"%PYTHON%" "forward-earnings\scripts\forward_earnings.py" --output-dir public\reports\ >> "%LOGFILE%" 2>&1
if errorlevel 1 (echo [WARN] forward-earnings failed >> "%LOGFILE%")

echo Running market-breadth...
"%PYTHON%" "market-breadth\scripts\market_breadth.py" --output-dir public\reports\ >> "%LOGFILE%" 2>&1
if errorlevel 1 (echo [WARN] market-breadth failed >> "%LOGFILE%")

echo Running price-signal...
"%PYTHON%" "price-signal\scripts\price_signal.py" --output-dir public\reports\ >> "%LOGFILE%" 2>&1
if errorlevel 1 (echo [WARN] price-signal failed >> "%LOGFILE%")

echo Running conviction-synthesizer...
"%PYTHON%" "conviction-synthesizer\scripts\conviction_synthesizer.py" --reports-dir public\reports\ --output-dir public\reports\ >> "%LOGFILE%" 2>&1
if errorlevel 1 (echo [ERROR] conviction-synthesizer failed >> "%LOGFILE%")

echo [%DATE% %TIME%] Pipeline complete >> "%LOGFILE%"

echo Pushing reports to GitHub...
git add public\reports\ >> "%LOGFILE%" 2>&1
git diff --cached --quiet >nul 2>&1 || (
    git commit -m "chore: daily conviction report %TODAY%" >> "%LOGFILE%" 2>&1
    git push >> "%LOGFILE%" 2>&1
    echo Pushed to GitHub.
)

echo Done. Log: %LOGFILE%
endlocal

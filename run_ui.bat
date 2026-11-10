@echo off
rem Double-click to open the Payroll Sentinel web UI. Close this window to stop it.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. In a terminal, run once:
    echo     python -m venv .venv
    echo     .venv\Scripts\python -m pip install -e ".[dev,ui]"
    pause
    exit /b 1
)

rem Open the browser after a few seconds, while the server starts below.
start "" /b cmd /c "ping -n 5 127.0.0.1 >nul & start http://localhost:8501"
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501
pause

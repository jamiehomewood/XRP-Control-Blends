@echo off
REM Starts the Glenda scene server: serves this folder and relays the remote control's Yes/No buttons.
REM Leave this window open while the scene is running.
cd /d "%~dp0"
where python >nul 2>nul && (python server.py & goto :eof)
where py >nul 2>nul && (py server.py & goto :eof)
echo Python was not found. Install it from python.org (tick "Add python.exe to PATH"), then run this again.
pause

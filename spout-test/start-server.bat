@echo off
setlocal
title Glenda scene server
REM Starts the Glenda scene server: serves this folder and relays the phone remotes' button presses.
REM Leave this window open while the scene is running.

REM pushd (not cd) also works when this folder is on a network drive (\\server\share\...)
pushd "%~dp0" || (echo Could not open the folder "%~dp0". & goto :fail)
if not exist server.py (echo server.py is missing from "%CD%". & goto :fail)

REM Find a Python that really runs. The "python" Microsoft Store shortcut is skipped.
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY python --version >nul 2>nul && set "PY=python"
if not defined PY python3 --version >nul 2>nul && set "PY=python3"
if not defined PY (
  echo Python was not found on this PC.
  echo Install it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^),
  echo or ask IT for Python 3. Then run this file again.
  goto :fail
)

echo Using: %PY%
%PY% server.py
echo.
echo The server stopped ^(exit code %ERRORLEVEL%^). Any error is shown above.
goto :fail

:fail
echo.
pause
popd
endlocal

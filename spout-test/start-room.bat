@echo off
setlocal
REM ===========================================================================================
REM  Starts the Glenda room: the scene server (if not already running) and OBS, minimised.
REM  OBS shows stage.html, so the facilitator picks the scene on the remote.
REM  One-time OBS setup (see README): Browser source URL http://localhost:8000/stage.html,
REM  4096 x 2048, and Tools > Spout Output Settings > tick "AutoStart".
REM  Can be launched from an Igloo Core Engine layer. Close everything with stop-room.bat.
REM ===========================================================================================

REM ---- change these if OBS lives somewhere else, or to force a scene collection / profile ----
set "OBS_DIR=C:\Program Files\obs-studio\bin\64bit"
set "OBS_COLLECTION="
set "OBS_PROFILE="
REM ---- optional: the first scene to show, e.g.  start-room.bat modern  ----
set "FIRST_SCENE=%~1"

pushd "%~dp0" || goto :fail

REM 1. scene server (skip if it is already answering)
curl -s -o nul -m 2 http://localhost:8000/api/scenes && (echo Scene server already running.) || call :start_server

REM 2. pick the first scene if one was given
if defined FIRST_SCENE (
  curl -s -o nul -m 3 -X POST -H "Content-Type: application/json" -d "{\"id\":\"%FIRST_SCENE%\",\"name\":\"start-room.bat\"}" http://localhost:8000/api/scene
)

REM 3. OBS (skip if it is already open)
tasklist /FI "IMAGENAME eq obs64.exe" | find /I "obs64.exe" >nul && (echo OBS already running.& goto :done)
if not exist "%OBS_DIR%\obs64.exe" (echo OBS not found in "%OBS_DIR%" - edit OBS_DIR at the top of this file.& goto :fail)
set "OBS_ARGS=--disable-shutdown-check --disable-updater --minimize-to-tray"
if defined OBS_COLLECTION set "OBS_ARGS=%OBS_ARGS% --collection "%OBS_COLLECTION%""
if defined OBS_PROFILE set "OBS_ARGS=%OBS_ARGS% --profile "%OBS_PROFILE%""
REM OBS must be started from its own folder
start "" /D "%OBS_DIR%" obs64.exe %OBS_ARGS%
echo OBS started.
goto :done

:start_server
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY python --version >nul 2>nul && set "PY=python"
if not defined PY (echo Python was not found - install it from python.org.& goto :eof)
start "Glenda scene server" /MIN cmd /c "%PY% server.py"
REM wait (up to ~10 s) for it to answer
for /L %%i in (1,1,20) do (
  curl -s -o nul -m 1 http://localhost:8000/api/scenes && goto :eof
  timeout /t 1 /nobreak >nul
)
echo The scene server did not start - run start-server.bat to see why.
goto :eof

:fail
echo.
pause
:done
popd
endlocal

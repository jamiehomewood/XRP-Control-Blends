@echo off
setlocal
REM ===========================================================================================
REM  Closes the Glenda room: OBS (forced if it hangs) and the scene server.
REM ===========================================================================================

REM 1. ask OBS to close; force it after 10 s (it often hangs on exit on the Igloo PC)
tasklist /FI "IMAGENAME eq obs64.exe" | find /I "obs64.exe" >nul || goto :server
taskkill /IM obs64.exe >nul 2>nul
for /L %%i in (1,1,10) do (
  tasklist /FI "IMAGENAME eq obs64.exe" | find /I "obs64.exe" >nul || goto :browsers
  timeout /t 1 /nobreak >nul
)
echo OBS did not close - forcing it.
taskkill /F /IM obs64.exe >nul 2>nul
:browsers
taskkill /F /IM obs-browser-page.exe >nul 2>nul

:server
REM 2. stop the scene server (clean shutdown; force its window closed if it does not answer)
curl -s -o nul -m 3 -X POST http://localhost:8000/api/shutdown || taskkill /F /FI "WINDOWTITLE eq Glenda scene server*" >nul 2>nul
timeout /t 1 /nobreak >nul
taskkill /F /FI "WINDOWTITLE eq Glenda scene server*" >nul 2>nul
echo Glenda room stopped.
endlocal

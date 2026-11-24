@echo off
if exist "%~dp0AnYCore.exe" (
  "%~dp0AnYCore.exe" member-ui
) else (
  "%~dp0AnY.exe" member-ui
)
if errorlevel 1 pause

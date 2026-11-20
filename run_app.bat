@echo off
rem Double-click to start the Agent Gatekeeper. Close this window to stop it.
cd /d "%~dp0"
set PY=
where py >nul 2>&1 && set PY=py
if not defined PY set PY=python
%PY% app.py
pause

@echo off
rem Double-click to check Python and run all automated tests.
cd /d "%~dp0"
set PY=
where py >nul 2>&1 && set PY=py
if not defined PY set PY=python
> test_output.txt echo Using: %PY%
%PY% --version >> test_output.txt 2>&1
>> test_output.txt echo.
%PY% -m unittest -v >> test_output.txt 2>&1
>> test_output.txt echo Exit code: %errorlevel%
type test_output.txt
pause

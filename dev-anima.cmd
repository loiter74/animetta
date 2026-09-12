@echo off
setlocal
cd /d "%~dp0"
py -3.13 -c "import sys; assert sys.version_info >= (3, 13)"
if errorlevel 1 goto failed
py -3.13 scripts/runtime_lifecycle.py anima-dev --wait --open %*
if errorlevel 1 goto failed
exit /b 0
:failed
echo Animetta development startup failed. See the lifecycle evidence above.
pause
exit /b 1

@echo off
cd /d C:\Users\30262\Project\Anima
if not exist logs mkdir logs
set PYTHONPATH=src
echo Starting bot at %date% %time% > logs\mc_bot2.log
C:\Users\30262\miniconda3\python.exe scripts\start_mc_bot.py >> logs\mc_bot2.log 2>&1
pause

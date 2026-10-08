@echo off
rem Thu nghiem giao dien menu doc ben trai (de so sanh voi thanh nut phia tren)
cd /d "%~dp0"
start "" .venv\Scripts\pythonw chay.py --menu-trai %*

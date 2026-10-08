@echo off
chcp 65001 >nul
rem Chay bo kiem thu tu dong (ca cua so phan mem, che do an). Ket qua chi tiet: KIEM_THU_log.txt
cd /d "%~dp0"
echo Dang kiem thu, vui long doi...
set QT_QPA_PLATFORM=offscreen
.venv\Scripts\python -m unittest discover -s tests -t . -v > KIEM_THU_log.txt 2>&1
set QT_QPA_PLATFORM=
type KIEM_THU_log.txt | findstr /C:"Ran " /C:"OK" /C:"FAIL" /C:"ERROR"
echo.
echo Chi tiet: KIEM_THU_log.txt  (cua so tu dong sau 30 giay)
timeout /t 30 >nul

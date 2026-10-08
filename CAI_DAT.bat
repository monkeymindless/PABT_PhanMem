@echo off
chcp 65001 >nul
rem Cai dat lan dau: tao moi truong Python rieng (.venv) cho PABT va cai thu vien
cd /d "%~dp0"
where py >nul 2>nul || (echo Chua co Python. Tai Python 3.14 64-bit tai https://www.python.org/downloads/ va tick "Add python.exe to PATH". > CAI_DAT_log.txt & type CAI_DAT_log.txt & pause & exit /b 1)
echo Dang cai dat, mat vai phut (tai PySide6 khoang 100 MB). Vui long doi...
(
  echo === %date% %time%
  py -3 --version
  if not exist .venv\Scripts\python.exe py -3 -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\python -m pip install -r requirements.txt
  echo === KIEM THU
  set QT_QPA_PLATFORM=offscreen
  .venv\Scripts\python -m unittest discover -s tests -t . -v
  set QT_QPA_PLATFORM=
  echo === XONG
) > CAI_DAT_log.txt 2>&1
type CAI_DAT_log.txt | findstr /C:"Python 3" /C:"Successfully" /C:"Ran " /C:"OK" /C:"FAILED" /C:"ERROR" /C:"=== "
echo.
echo Chi tiet: CAI_DAT_log.txt. Bam dup CHAY_PABT.bat de mo phan mem.
pause

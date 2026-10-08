@echo off
chcp 65001 >nul
rem Moi truong dung bo cai Windows 7 / 8: Python 3.8.10 32-bit + Qt5 (PySide2) - chuong trinh 32-bit chay ca Win 32-bit lan 64-bit
rem Dat o %LOCALAPPDATA%\PABT_dev\venv38_32 (duong dan khong dau: Python 3.8 / Qt5 / PyInstaller 5 loi voi chu Unicode)
rem Can Python 3.8.10 32-bit: https://www.python.org/ftp/python/3.8.10/python-3.8.10.exe (cai vao Python38-32)
cd /d "%~dp0"
set V38=%LOCALAPPDATA%\PABT_dev\venv38_32
set PY38=%LOCALAPPDATA%\Programs\Python\Python38-32\python.exe
if not exist "%PY38%" (echo Chua co Python 3.8.10 32-bit tai %PY38% & pause & exit /b 1)
if not exist "%V38%\Scripts\python.exe" "%PY38%" -m venv "%V38%"
"%V38%\Scripts\python" -m pip install --upgrade pip
"%V38%\Scripts\python" -m pip install -r requirements38.txt
set QT_QPA_PLATFORM=offscreen
"%V38%\Scripts\python" -m unittest discover -s tests -t .
echo.
pause

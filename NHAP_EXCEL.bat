@echo off
chcp 65001 >nul
rem Nhap file Excel va xuat bao cao doi chieu (khong can mo cua so). Cach dung: keo file .xlsm tha vao file nay
cd /d "%~dp0"
if "%~1"=="" (
    echo Keo tha file Excel ^(.xlsx / .xlsm^) vao file NHAP_EXCEL.bat de nhap. Khong mo truc tiep file nay.
    pause
    exit /b 2
)
if not exist "%~1" (
    echo Khong thay file: %~1
    pause
    exit /b 1
)
.venv\Scripts\python chay.py nhap "%~1"
pause

@echo off
chcp 65001 >nul
rem Dung ban .exe Windows 10 / 11 (thu muc dist\PABT) bang PyInstaller 6 - ban Windows 7 / 8: bo_cai_win\dung_exe38.py
cd /d "%~dp0"
.venv\Scripts\python -m pip install "pyinstaller>=6.10"
rem tuy chon dung (du lieu kem theo, bieu tuong, module loai tru) chi ghi MOT noi: PABT.spec
.venv\Scripts\python -m PyInstaller --noconfirm --clean PABT.spec || (pause & exit /b 1)
rem bo thu vien Qt khong dung, roi tu kiem PABT.exe
.venv\Scripts\python bo_cai_win\rut_gon.py dist\PABT || (pause & exit /b 1)
echo.
echo Ban chay: dist\PABT\PABT.exe
pause

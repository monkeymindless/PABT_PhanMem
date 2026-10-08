@echo off
chcp 65001 >nul
rem Dung 2 bo cai trong thu muc bo_cai (IExpress co san trong Windows):
rem   PABT_CaiDat_<phien ban>_Win10-11.exe : Python 3.14 + Qt6 (PyInstaller 6, moi truong .venv)
rem   PABT_CaiDat_<phien ban>_Win7-8.exe   : Python 3.8 + Qt5 (PyInstaller 5, moi truong tao bang CAI_DAT_PHAT_HANH.bat)
cd /d "%~dp0"
.venv\Scripts\python -m pip install -q "pyinstaller>=6.10" || (echo Khong cai duoc PyInstaller & pause & exit /b 1)
rem --- ban Windows 10 / 11 -> dist\PABT
rem tuy chon dung (du lieu kem theo, bieu tuong, module loai tru) chi ghi MOT noi: PABT.spec
.venv\Scripts\python -m PyInstaller --noconfirm --clean PABT.spec || (pause & exit /b 1)
.venv\Scripts\python bo_cai_win\rut_gon.py dist\PABT || (pause & exit /b 1)
rem --- ban Windows 7 / 8 -> dist\PABT_Win7
.venv\Scripts\python bo_cai_win\dung_exe38.py || (pause & exit /b 1)
.venv\Scripts\python bo_cai_win\rut_gon.py dist\PABT_Win7 || (pause & exit /b 1)
rem --- dong goi 2 bo cai
.venv\Scripts\python bo_cai_win\dung_bo_cai_win.py || (pause & exit /b 1)
echo.
pause

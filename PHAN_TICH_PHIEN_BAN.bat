@echo off
chcp 65001 >nul
rem PHAN TICH PHIEN BAN (chay moi lan sua phien ban): toc do mo / tat, mo du an, luu + tai lai, lenh dong lenh; nap module,
rem ma lap lai; so voi goi cap nhat moi nhat trong bo_cai\ (hoac: PHAN_TICH_PHIEN_BAN.bat --so-sanh <file .pabtcn / thu muc>)
rem Ket qua: ket_qua_kiem_tra\PhanTich_<phien ban>_<ngay gio>.md
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo Chua co moi truong .venv: chay CAI_DAT.bat truoc.
    pause
    exit /b 1
)
.venv\Scripts\python -W ignore phan_tich_phien_ban.py %*
echo.
pause

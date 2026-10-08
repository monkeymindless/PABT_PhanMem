@echo off
chcp 65001 >nul
rem KIEM TRA GIAO DIEN TU DONG: bam moi nut, go moi o nhap, chon moi muc chon, chuyen moi the, sua o bang cua moi cua so / hop thoai
rem (tren BAN SAO du an; khong in, khong mo Excel / Word, khong goi mang). Ghi loi, cho cham / do, treo.
rem   KIEM_TRA_GIAO_DIEN.bat                       du an gia lap 12 ho
rem   KIEM_TRA_GIAO_DIEN.bat --du-an "<file.pabt>"  chay tren ban sao file du an that
rem Ket qua: ket_qua_kiem_tra\GiaoDien_<phien ban>_<ngay gio>.md
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo Chua co moi truong .venv: chay CAI_DAT.bat truoc.
    pause
    exit /b 1
)
.venv\Scripts\python -W ignore kiem_tra_giao_dien.py %*
echo.
pause

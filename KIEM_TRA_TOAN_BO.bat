@echo off
chcp 65001 >nul
rem KIEM TRA TOAN BO PABT khi co loi: kiem thu tu dong (Qt6 + Qt5 32-bit), chay thu voi file mau PABT_CHUAN, ban dung dist\,
rem bo cai + goi cap nhat trong bo_cai\, ban da cai tren may, ban cap nhat dang dung, may chu LAN.
rem   KIEM_TRA_TOAN_BO.bat            kiem tra day du (khoang 3-5 phut)
rem   KIEM_TRA_TOAN_BO.bat --nhanh    bo qua Qt5 32-bit va ban dung dist\ (khoang 1 phut)
rem   KIEM_TRA_TOAN_BO.bat --cai-thu  them buoc cai im lang bo cai moi nhat roi tu kiem tra ban vua cai
rem Ket qua: ket_qua_kiem_tra\KiemTra_<ngay gio>.txt
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo Chua co moi truong .venv: chay CAI_DAT.bat truoc.
    pause
    exit /b 1
)
.venv\Scripts\python -W ignore kiem_tra_toan_bo.py %*
set MA=%ERRORLEVEL%
echo.
pause
exit /b %MA%

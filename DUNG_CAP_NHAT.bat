@echo off
chcp 65001 >nul
rem Tao goi cap nhat bo_cai\PABT_CapNhat_<phien ban>.pabtcn tu ma nguon hien tai (nho tang __version__ truoc)
cd /d "%~dp0"
set /p MOTA=Noi dung cap nhat (sua loi / tinh nang): 
.venv\Scripts\python tao_cap_nhat.py --mo-ta "%MOTA%"
echo.
pause

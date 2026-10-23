@echo off
chcp 65001 >nul
rem Dung bo cai BAN TRUNG TINH (khong co ten don vi / dia phuong nao) de ban cho don vi khac -> bo_cai\trung_tinh\
rem Bo cai cua chinh ban (cung so phien ban) duoc cat tam roi tra lai. Xem dung_ban_trung_tinh.py.
cd /d "%~dp0"
.venv\Scripts\python tao_ho_so_trung_tinh.py || (pause & exit /b 1)
.venv\Scripts\python dung_ban_trung_tinh.py
echo.
pause

@echo off
chcp 65001 >nul
rem Cai tu dong Bo Dieu Phoi Truy Tim & Cong Gac Khep Kin cho Claude Code (.claude\agents, commands, skills).
rem Dung:  CAI_DAT_BO_DIEU_PHOI.bat            cai / cap nhat (sao luu ban da sua tay)
rem        CAI_DAT_BO_DIEU_PHOI.bat --kiem-tra chi kiem tra, khong ghi
rem        CAI_DAT_BO_DIEU_PHOI.bat --go       go bo dieu phoi
rem        CAI_DAT_BO_DIEU_PHOI.bat --cach-ly-skill  chuyen skill de trung vao _luu_tru_don_dep (khong xoa)
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" cai_dat_bo_dieu_phoi_claude.py %*
) else (
  py -3 cai_dat_bo_dieu_phoi_claude.py %*
)
echo.
pause

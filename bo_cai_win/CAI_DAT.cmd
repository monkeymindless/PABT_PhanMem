@echo off
rem PABT - cai dat cho nguoi dung hien tai (khong can quyen quan tri). Dung chung cho bo cai .exe (IExpress) va goi .zip:
rem   CAI_DAT.cmd            cua so cai dat
rem   CAI_DAT.cmd -Im        cai im lang
rem Chay cai_dat.ps1 bang PowerShell -Command (doc file thanh khoi lenh): khong bi chinh sach ExecutionPolicy / Group Policy
rem chan nhu -File. PowerShell 2.0 (Windows 7) tro len. File nay chi dung chu ASCII (cmd doc theo bang ma OEM).
setlocal
set "PABT_GOC=%~dp0"
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"
"%PS%" -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -Command "& ([scriptblock]::Create([IO.File]::ReadAllText($env:PABT_GOC + 'cai_dat.ps1', [Text.Encoding]::UTF8))) %*; exit $LASTEXITCODE"
exit /b %ERRORLEVEL%

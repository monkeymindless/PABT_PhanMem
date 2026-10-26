@echo off
chcp 65001 >nul
rem Dung ung dung dien thoai LARC Field Mobile: bo_cai\LARC_FieldMobile_<phien ban>.apk (Android) + bo_cai\LARC_FieldMobile_PWA_<phien ban>.zip (iPhone)
rem Cong cu Android o ..\cong_cu_android (bien PABT_ANDROID), khoa ky o ..\khoa_android (bien PABT_KHOA_APK) - GIU KY khoa ky
cd /d "%~dp0"
.venv\Scripts\python bo_cai_win\dung_di_dong.py %*
echo.
pause

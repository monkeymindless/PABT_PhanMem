@echo off
chcp 65001 >nul
rem Dung ung dung dien thoai LARC Mobile (du an rieng trong thu muc di_dong\, khong dung ma cua LARC ban may tinh):
rem   bo_cai\LARC_Mobile_<phien ban>.apk (Android) + bo_cai\LARC_Mobile_PWA_<phien ban>.zip (iPhone)
rem Cong cu Android o ..\..\cong_cu_android (bien LARC_ANDROID), khoa ky o ..\..\khoa_android (bien LARC_KHOA_APK) - GIU KY khoa ky
cd /d "%~dp0.."
.venv\Scripts\python di_dong\dung.py %*
echo.
pause

# -*- mode: python ; coding: utf-8 -*-
# Bản Windows 10/11 (dist\PABT). NGUỒN DUY NHẤT của tùy chọn PyInstaller: DUNG_EXE.bat và DUNG_BO_CAI.bat đều chạy
#   .venv\Scripts\python -m PyInstaller --noconfirm --clean PABT.spec
# Thêm file dữ liệu cho gói pabt -> sửa `datas` ở đây (KHÔNG chạy PyInstaller với tùy chọn dòng lệnh: sẽ ghi đè file này).
# upx=False: nén UPX làm hỏng / bị diệt virus báo nhầm DLL Qt.


a = Analysis(
    ['chay.py'],
    pathex=[],
    binaries=[],
    datas=[('pabt/schema.sql', 'pabt'), ('pabt/bo_don_gia.sqlite', 'pabt'), ('pabt/bang_gia_nq28.json', 'pabt'), ('pabt/bieu_tuong.png', 'pabt'), ('mau_in', 'mau_in')],
    hiddenimports=['html.parser', 'urllib.request', 'difflib'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pabt.cap_nhat_web', 'pabt.man_hinh_quet_web'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PABT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['pabt/bieu_tuong.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PABT',
)

# -*- mode: python ; coding: utf-8 -*-
# Bản Windows 10/11 (dist\PABT). NGUỒN DUY NHẤT của tùy chọn PyInstaller: DUNG_EXE.bat và DUNG_BO_CAI.bat đều chạy
#   .venv\Scripts\python -m PyInstaller --noconfirm --clean PABT.spec
# Thêm file dữ liệu cho gói pabt -> sửa `datas` ở đây (KHÔNG chạy PyInstaller với tùy chọn dòng lệnh: sẽ ghi đè file này).
# upx=False: nén UPX làm hỏng / bị diệt virus báo nhầm DLL Qt.


# máy yếu (16/10/2026): bản vẽ CAD .dxf đọc bằng pabt.dxf_thuan (Python thuần) - KHÔNG đóng ezdxf và numpy (+ libopenblas, fontTools,
# PIL kéo theo: ~35 MB); thư viện chỉ dùng lúc phát triển / kiểm thử cũng loại
LOAI_TRU = ['numpy', 'scipy', 'matplotlib', 'PIL', 'tkinter', 'unittest', 'pydoc', 'doctest', 'ezdxf', 'fontTools']

a = Analysis(
    ['chay.py'],
    pathex=[],
    binaries=[],
    # 1.0.20: KHÔNG đóng thư mục mau_in - bảng tổng hợp dựng bằng mã (pabt/mau_bang_tong_hop.py), mẫu Word (chi tiết / bổ sung / điều chỉnh) dựng bằng
    # mã + thông số ban_in.mau_word của pabt_profile.json
    datas=[('pabt/schema.sql', 'pabt'), ('pabt/bo_don_gia.sqlite', 'pabt'), ('pabt/bang_gia_nq28.json', 'pabt'), ('pabt/he_so_k_qd03.json', 'pabt'), ('pabt/bieu_tuong.png', 'pabt'),
           ('pabt/pabt_profile.json', 'pabt'), ('HUONG_DAN.md', '.')],
    hiddenimports=['pabt.mau_bang_tong_hop', 'pabt.in_word', 'html.parser','urllib.request', 'difflib', 'PySide6.QtPdfWidgets', 'PySide6.QtPrintSupport'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # cap_nhat_web đi cùng bản cài từ 0.9.49 (nút Tải từ web của bảng giá đất). man_hinh_quet_web vẫn để gói .pabtcn.
    excludes=['pabt.man_hinh_quet_web'] + LOAI_TRU,
    noarchive=False,
    optimize=0,
)
# DLL lấy nhầm từ PATH của máy dựng (dựng trong Git Bash: C:\Program Files\Git\mingw64\bin\libssl-3-x64.dll,
# libcrypto-3-x64.dll - OpenSSL của Git, +6,5 MB, không dùng: Python đã kèm libssl-3.dll / libcrypto-3.dll của nó)
a.binaries = [b for b in a.binaries if not any(k in b[1].replace('/', '\\').lower() for k in ('\\git\\', '\\mingw64\\', '\\msys64\\'))]
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

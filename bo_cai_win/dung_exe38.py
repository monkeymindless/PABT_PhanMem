"""Dựng bản PABT cho Windows 7 SP1 / 8 / 8.1 (32-bit, chạy cả máy 64-bit) -> dist\\PABT_Win7.

Dùng môi trường %LOCALAPPDATA%\\PABT_dev\\venv38_32 (Python 3.8.10 32-bit + PySide2 5.15 + PyInstaller 5, tạo bằng
CAI_DAT_PHAT_HANH.bat). Python 3.8 / Qt5 / PyInstaller 5 lỗi với đường dẫn có dấu / NFD: mã nguồn được chép sang
%LOCALAPPDATA%\\PABT_dev\\nguon38 rồi dựng ở đó. Gọi từ thư mục gốc dự án (DUNG_BO_CAI.bat):

    .venv\\Scripts\\python bo_cai_win\\dung_exe38.py
"""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
DEV = Path(os.environ['LOCALAPPDATA']) / 'PABT_dev'
PY38 = DEV / 'venv38_32' / 'Scripts' / 'python.exe'
TAM = DEV / 'nguon38'
RA = GOC / 'dist' / 'PABT_Win7'
CHEP = ('chay.py', 'nap_cap_nhat.py', 'pabt', 'mau_in', 'HUONG_DAN.md')
DU_LIEU = ('pabt/schema.sql', 'pabt/bo_don_gia.sqlite', 'pabt/bang_gia_nq28.json', 'pabt/he_so_k_qd03.json', 'pabt/bieu_tuong.png', 'pabt/pabt_profile.json')
# cập nhật đơn giá từ trang web phát hành riêng bằng gói .pabtcn: không đóng vào exe, nhưng giữ thư viện chuẩn nó cần
# cap_nhat_web đóng trong bản cài từ 0.9.49. Màn hình quét web đầy đủ vẫn để gói .pabtcn.
LOAI_TRU_WEB = ['--exclude-module', 'pabt.man_hinh_quet_web',
                '--hidden-import', 'html.parser', '--hidden-import', 'urllib.request', '--hidden-import', 'difflib', '--hidden-import', 'pabt.mau_in_nhung']


def main() -> int:
    if not PY38.exists():
        print(f'Chưa có môi trường Python 3.8 32-bit ({PY38}): chạy CAI_DAT_PHAT_HANH.bat trước.')
        return 1
    if TAM.exists():
        shutil.rmtree(TAM)
    TAM.mkdir(parents=True)
    for x in CHEP:
        nguon = GOC / x
        if x == 'mau_in':                               # chỉ mẫu .xlsx / .xml (không đóng PDF tham khảo, file khác người dùng để)
            (TAM / x).mkdir(parents=True, exist_ok=True)
            for f in nguon.iterdir():
                if f.is_file() and f.suffix.lower() in ('.xlsx', '.xml'):
                    shutil.copy2(f, TAM / x / f.name)
        elif nguon.is_dir():
            shutil.copytree(nguon, TAM / x, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(nguon, TAM / x)
    lenh = [str(PY38), '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed', '--name', 'PABT',
            '--distpath', str(TAM / 'dist'), '--workpath', str(TAM / 'build'), '--specpath', str(TAM),
            '--icon', str(TAM / 'pabt' / 'bieu_tuong.ico'), '--log-level', 'WARN',
            # Qt6 không có trong môi trường này; mã nhận PySide2 qua bí danh (pabt._qt5_lam_qt6)
            '--exclude-module', 'PySide6', *LOAI_TRU_WEB,
            # máy yếu (16/10/2026): bản vẽ CAD đọc bằng pabt.dxf_thuan - không đóng ezdxf / numpy / thư viện chỉ dùng lúc phát triển
            *[x for m in ['numpy', 'scipy', 'matplotlib', 'PIL', 'tkinter', 'unittest', 'pydoc', 'doctest', 'ezdxf', 'fontTools'] for x in ('--exclude-module', m)]]
    for f in DU_LIEU:
        lenh += ['--add-data', f'{TAM / f};pabt']
    # HUONG_DAN.md: Trợ giúp -> Hướng dẫn sử dụng (F1) đọc trong _internal (0.9.23)
    lenh += ['--add-data', f'{TAM / "mau_in"};mau_in', '--add-data', f'{TAM / "HUONG_DAN.md"};.', str(TAM / 'chay.py')]
    # PATH của máy dựng có thư mục Git / mingw (dựng trong Git Bash): PyInstaller lấy nhầm DLL OpenSSL... của Git vào bản dựng
    env = dict(os.environ, PATH=os.pathsep.join(x for x in os.environ.get('PATH', '').split(os.pathsep)
                                                if not any(k in x.lower() for k in ('\\git\\', 'mingw', 'msys'))))
    kq = subprocess.run(lenh, cwd=str(TAM), env=env)
    if kq.returncode:
        print('PyInstaller (Python 3.8) lỗi.')
        return kq.returncode
    if RA.exists():
        shutil.rmtree(RA)
    shutil.copytree(TAM / 'dist' / 'PABT', RA)
    # UCRT đóng kèm (app-local): chạy trên Windows 7 / 8 chưa cài Visual C++ / KB2999226, không cần quyền quản trị
    from ucrt_win7 import chep_ucrt
    print(f'UCRT Windows 7: {chep_ucrt(RA)} file')
    print(f'Bản Windows 7 / 8: {RA}')
    return 0


if __name__ == '__main__':
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    sys.exit(main())

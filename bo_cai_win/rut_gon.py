"""Rút gọn bản PyInstaller (dist\\PABT hoặc dist\\PABT_Win7): bỏ thư viện Qt không dùng (Quick / QML / OpenGL / bàn phím ảo /
bản dịch...), rồi chạy `PABT.exe tu-kiem` - phải ra `KET QUA: DAT`.

    python bo_cai_win\\rut_gon.py dist\\PABT

Giữ theo danh sách (không theo danh sách bỏ): phiên bản Qt mới thêm thư viện thì tự bị bỏ, tự kiểm tra sẽ báo nếu thiếu.
PABT dùng QtCore / QtGui / QtWidgets, QtPdf (Qt6: đọc PDF), QtSvg (biểu tượng), QtNetwork (QtPdf cần).
Chỉ dùng thư viện chuẩn (chạy được bằng Python 3.8 lẫn 3.14).
"""
from __future__ import annotations
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GIU_MODULE = ('Core', 'Gui', 'Widgets', 'Network', 'Pdf', 'Svg')
GIU_MODULE_QT5 = GIU_MODULE + ('Qml',)          # pyside2.abi3.dll (PySide2 5.15) liên kết cứng Qt5Qml: thiếu thì PABT.exe treo
# thư mục plugin -> tên file giữ (None = giữ cả thư mục)
GIU_PLUGIN = {
    'platforms': ('qwindows', 'qoffscreen'),
    'imageformats': None,
    'iconengines': None,
    'styles': None,
    'generic': None,
    'tls': None,
    'networkinformation': None,
    'bearer': None,                                 # Qt5: mạng
}
BO_FILE = ('opengl32sw.dll', 'd3dcompiler_47.dll', 'libEGL.dll', 'libGLESv2.dll')


def _qt_dll_giu(ten: str, giu=GIU_MODULE) -> bool:
    m = re.fullmatch(r'Qt[56](\w+?)d?\.dll', ten, re.I)
    return m is None or m.group(1) in giu


def _qt_pyd_giu(ten: str, giu=GIU_MODULE) -> bool:
    m = re.fullmatch(r'Qt(\w+)\.(pyd|abi3\.pyd)', ten, re.I)
    return m is None or m.group(1) in giu


def rut_gon(dist: Path) -> int:
    noi = dist / '_internal'
    if not noi.is_dir():
        noi = dist                                  # PyInstaller 5: file nằm ngay cạnh exe
    qt = next((noi / x for x in ('PySide6', 'PySide2') if (noi / x).is_dir()), None)
    if qt is None:
        raise SystemExit(f'Không thấy thư mục PySide6 / PySide2 trong {noi}')
    giu = GIU_MODULE_QT5 if qt.name == 'PySide2' else GIU_MODULE
    bo = []
    for f in qt.iterdir():
        if f.is_file() and (not _qt_dll_giu(f.name, giu) or not _qt_pyd_giu(f.name, giu) or f.name in BO_FILE):
            bo.append(f)
    for ten in ('translations', 'qml', 'resources', 'examples'):
        if (qt / ten).exists():
            bo.append(qt / ten)
    pl = qt / 'plugins'
    if pl.is_dir():
        for d in pl.iterdir():
            if d.name not in GIU_PLUGIN:
                bo.append(d)
            elif GIU_PLUGIN[d.name] is not None:
                bo += [f for f in d.iterdir() if f.stem not in GIU_PLUGIN[d.name]]
    truoc = sum(f.stat().st_size for f in dist.rglob('*') if f.is_file())
    for x in bo:
        if x.is_dir():
            shutil.rmtree(x)
        else:
            x.unlink()
    sau = sum(f.stat().st_size for f in dist.rglob('*') if f.is_file())
    print(f'Rút gọn {dist}: bỏ {len(bo)} mục, {truoc / 2**20:.0f} MB -> {sau / 2**20:.0f} MB')
    return len(bo)


def tu_kiem(dist: Path) -> str:
    exe = dist / 'PABT.exe'
    with tempfile.TemporaryDirectory() as td:
        ra = Path(td) / 'tu_kiem.txt'
        pr = subprocess.Popen([str(exe), 'tu-kiem', str(ra)])
        try:
            pr.wait(180)
        except subprocess.TimeoutExpired:                # thường do thiếu DLL (bỏ nhầm khi rút gọn): Windows không báo lỗi
            pr.kill()
            pr.wait()
            return 'KET QUA: PABT.exe treo quá 180 giây (thiếu thư viện?)'
        kq = ra.read_text(encoding='utf-8') if ra.exists() else 'KET QUA: không chạy được PABT.exe'
    return kq


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 2
    dist = Path(argv[0]).resolve()
    rut_gon(dist)
    kq = tu_kiem(dist)
    print(kq)
    if 'KET QUA: DAT' not in kq:
        print('TỰ KIỂM TRA KHÔNG ĐẠT: không dùng bản này để đóng gói.')
        return 1
    return 0


if __name__ == '__main__':
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    sys.exit(main(sys.argv[1:]))

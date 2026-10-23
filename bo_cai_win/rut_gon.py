"""Rút gọn bản PyInstaller (dist\\PABT hoặc dist\\PABT_Win7): bỏ thư viện Qt không dùng (Quick / QML / OpenGL / bàn phím ảo /
bản dịch...), rồi chạy `PABT.exe tu-kiem` - phải ra `KET QUA: DAT`.

    python bo_cai_win\\rut_gon.py dist\\PABT

Giữ theo danh sách (không theo danh sách bỏ): phiên bản Qt mới thêm thư viện thì tự bị bỏ, tự kiểm tra sẽ báo nếu thiếu.
PABT dùng QtCore / QtGui / QtWidgets, QtPdf (Qt6: đọc PDF), QtPrintSupport (Qt6: hộp in), QtNetwork (QtPdf cần, chỉ Qt6).
Chỉ dùng thư viện chuẩn (chạy được bằng Python 3.8 lẫn 3.14).
"""
from __future__ import annotations
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

# PdfWidgets (0.9.84): QPdfView của khung xem trước tài liệu (xem_truoc_tai_lieu) - thiếu thì khung vẽ trang bằng QPdfDocument
# 1.0.27 (rà soát dung lượng): PrintSupport = hộp chọn máy in (chỉ Qt 6); PDF / Svg của Qt 5 không dùng (PySide2 không có QtPdf, phần mềm không import
# QtSvg). Qt5Network.dll / Qt6Network.dll GIỮ (Qt5Qml / QtPdf liên kết tới) nhưng không giữ QtNetwork.pyd (phần mềm không import). kiem_dll + tu-kiem báo nếu thiếu.
GIU_MODULE = ('Core', 'Gui', 'Widgets', 'Network', 'Pdf', 'PdfWidgets', 'PrintSupport')
GIU_MODULE_QT5 = ('Core', 'Gui', 'Widgets', 'Network', 'Qml')   # pyside2.abi3.dll (PySide2 5.15) liên kết cứng Qt5Qml: thiếu thì PABT.exe treo
# thư mục plugin -> tên file giữ (None = giữ cả thư mục); thư mục không có trong danh sách bị bỏ
# imageformats: ảnh người dùng chọn (jpg, tif, webp, gif, ico); png / bmp nằm sẵn trong QtGui. Không giữ svg / icns / tga / wbmp / pdf.
# bỏ: tls, networkinformation (Qt không làm HTTPS - Python làm), styles (ứng dụng ép Fusion), iconengines (svg), generic (cảm ứng TUIO), bearer
_ANH = ('qjpeg', 'qtiff', 'qwebp', 'qgif', 'qico')
GIU_PLUGIN = {'platforms': ('qwindows', 'qoffscreen'), 'imageformats': _ANH}
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
    giu_pyd = tuple(x for x in giu if x != 'Network')       # binding Python QtNetwork không dùng
    bo = []
    for f in qt.iterdir():
        if f.is_file() and (not _qt_dll_giu(f.name, giu) or not _qt_pyd_giu(f.name, giu_pyd) or f.name in BO_FILE):
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


# ---------------------------------------------------------------- tiêu chuẩn: mọi DLL cần có trong bản dựng hoặc trong Windows đích
# DLL hệ thống có trên MỌI máy Windows 7 SP1 (bản Win7-8 32-bit); bản Win10-11 cần Windows 10 1809 (build 17763) trở lên.
# DLL nào khác (Visual C++, UCRT, OpenSSL…) phải nằm trong bản dựng - không dựa vào việc máy người dùng đã cài gì.
HE_THONG_WIN7 = {
    'advapi32', 'bcrypt', 'comctl32', 'comdlg32', 'crypt32', 'd3d11', 'd3d9', 'dnsapi', 'dwmapi', 'dxgi', 'gdi32', 'imm32',
    'iphlpapi', 'kernel32', 'mpr', 'msimg32', 'netapi32', 'ntdll', 'ole32', 'oleaut32', 'psapi', 'rpcrt4', 'secur32',
    'setupapi', 'shell32', 'shlwapi', 'user32', 'userenv', 'uxtheme', 'version', 'winhttp', 'wininet', 'winmm', 'winspool.drv',
    'ws2_32', 'wtsapi32', 'opengl32', 'glu32', 'normaliz', 'ncrypt', 'propsys', 'authz', 'credui', 'cryptui', 'wldap32',
    # thư viện C của Windows (có từ XP): openblas của numpy (đi kèm ezdxf - bản vẽ CAD, 0.9.87) bản MinGW liên kết tới
    'msvcrt',
}
HE_THONG_WIN10 = HE_THONG_WIN7 | {'d3d12', 'dwrite', 'uiautomationcore', 'icuuc', 'icuin', 'shcore', 'windowscodecs',
                                  'dcomp', 'd2d1', 'bluetoothapis', 'wevtapi'}


def _nhap_dll(f: Path) -> tuple:
    """(DLL nhập thường, DLL nhập trễ) của một file PE; ((), ()) nếu không phải PE."""
    b = f.read_bytes()
    if b[:2] != b'MZ':
        return (), ()
    pe = struct.unpack_from('<I', b, 0x3C)[0]
    if b[pe:pe + 4] != b'PE\0\0':
        return (), ()
    magic = struct.unpack_from('<H', b, pe + 24)[0]
    dd = pe + 24 + (96 if magic == 0x10B else 112)
    nsec, sopt = struct.unpack_from('<H', b, pe + 6)[0], struct.unpack_from('<H', b, pe + 20)[0]
    secs = [struct.unpack_from('<8sIIII', b, pe + 24 + sopt + 40 * i) for i in range(nsec)]

    def off(r):
        for _, vs, va, rs, ra in secs:
            if va <= r < va + max(vs, rs):
                return r - va + ra
        return None
    kq = []
    for idx, buoc, o_ten in ((1, 20, 12), (13, 32, 4)):           # bảng nhập, bảng nhập trễ
        rva = struct.unpack_from('<I', b, dd + 8 * idx)[0]
        i, ds = (off(rva) if rva else None), []
        while i is not None and i + buoc <= len(b):
            ten = struct.unpack_from('<I', b, i + o_ten)[0]
            o = off(ten) if ten else None
            if o is None:
                break
            ds.append(b[o:b.index(b'\0', o)].decode('latin1').lower())
            i += buoc
        kq.append(tuple(ds))
    return tuple(kq)


# nhóm API lõi có trong lược đồ API của Windows 7 (ucrtbase bản Win 7 cần) - liệt kê cụ thể: không phải mọi "-l1-1-0" đều có
# trên Windows 7 (api-ms-win-core-path-l1-1-0 chỉ từ Windows 8)
API_WIN7 = {f'api-ms-win-core-{x}-l1-1-0.dll' for x in (
    'console', 'datetime', 'debug', 'delayload', 'errorhandling', 'fibers', 'file', 'handle', 'heap', 'interlocked', 'io',
    'libraryloader', 'localization', 'localregistry', 'memory', 'misc', 'namedpipe', 'processenvironment', 'processthreads',
    'profile', 'rtlsupport', 'string', 'synch', 'sysinfo', 'threadpool', 'util', 'xstate')}


def _api_win7(d: str) -> bool:
    return d in API_WIN7


def kiem_dll(dist: Path, win7: bool) -> list:
    """DLL được nhập (thường) mà không có trong bản dựng lẫn Windows đích -> [(dll, file cần)]. Rỗng = đạt tiêu chuẩn."""
    co = {f.name.lower() for f in dist.rglob('*') if f.is_file()}
    he = HE_THONG_WIN7 if win7 else HE_THONG_WIN10
    thieu = {}
    for f in dist.rglob('*'):
        if f.is_file() and f.suffix.lower() in ('.dll', '.pyd', '.exe'):
            for d in _nhap_dll(f)[0]:
                goc = d[:-4] if d.endswith('.dll') else d
                if d in co or goc in he or (not win7 and d.startswith(('api-ms-win-', 'ext-ms-'))) or _api_win7(d):
                    continue
                thieu.setdefault(d, str(f.relative_to(dist)))
    return sorted(thieu.items())


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
    # Tesseract OCR đóng kèm (16/10/2026: đọc PDF ảnh / ảnh scan thay Windows OCR) - cạnh PABT.exe, kiểm DLL cùng bản dựng
    from chuan_bi_tesseract import chep_vao
    if not chep_vao(dist):
        print('THIẾU bo_cai_win\\tesseract (Tesseract OCR đóng kèm): chạy bo_cai_win\\chuan_bi_tesseract.py trước khi dựng.')
        return 1
    win7 = (dist / 'python38.dll').exists() or (dist / 'PySide2').is_dir()
    thieu = kiem_dll(dist, win7)
    if thieu:
        print(f'THIẾU THƯ VIỆN (bản {"Win7-8" if win7 else "Win10-11"} sẽ không chạy trên máy chưa cài sẵn):')
        for d, f in thieu:
            print(f'  {d}  (cần cho {f})')
        return 1
    print(f'Thư viện: đủ - chỉ cần DLL có sẵn của Windows {"7 SP1" if win7 else "10 (1809+)"}.')
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

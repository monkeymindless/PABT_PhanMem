"""Thư viện C chung (UCRT) cho bản Win7-8: đóng thẳng vào thư mục chương trình (app-local) để PABT chạy trên máy Windows 7 /
8 / 8.1 CHƯA cài Visual C++ Redistributable hay bản cập nhật KB2999226 - không cần quyền quản trị.

Lấy từ chính gói `vc_redist_win7.x86.exe` (Microsoft Visual C++ 14.29 x86, đã có trong bo_cai_win): gói WiX Burn mang các bản cập
nhật UCRT; bản cho Windows 7 (Windows6.1-KB2999226-x86.msu, UCRT 10.0.10240) chứa ucrtbase.dll + api-ms-win-*.dll bản 32-bit.
Giải nén bằng expand.exe của Windows, không tải gì từ mạng. Trên Windows 10/11 các api-ms-win-crt-* luôn trỏ về UCRT của hệ
thống (apiset) nên bản đóng kèm không ảnh hưởng.

    .venv\\Scripts\\python bo_cai_win\\ucrt_win7.py dist\\PABT_Win7      (dung_exe38.py tự gọi)
"""
from __future__ import annotations
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

GOC = Path(__file__).resolve().parent
VC = GOC / 'vc_redist_win7.x86.exe'
EXPAND = Path(r'C:\Windows\System32\expand.exe')
MSU = 'Windows6.1-KB2999226-x86.msu'


def _expand(cab: Path, ten: str, dich: Path) -> None:
    dich.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(EXPAND), f'-F:{ten}', str(cab), str(dich)], check=True, stdout=subprocess.DEVNULL)


def _cab_dinh_kem(exe: bytes) -> bytes:
    """Container đính kèm của gói Burn: tệp CAB ('MSCF') lớn nằm sau phần mã chương trình."""
    vi_tri = 0
    while True:
        i = exe.find(b'MSCF\0\0\0\0', vi_tri)
        if i < 0:
            raise RuntimeError('Không tìm thấy gói CAB trong vc_redist.')
        co = struct.unpack_from('<I', exe, i + 8)[0]
        if co > 1_000_000 and i + co <= len(exe):
            return exe[i:i + co]
        vi_tri = i + 4


def _ma_goi(exe: bytes) -> str:
    """Mã tệp (a0, a1…) của gói MSU Windows 7 x86 trong container, đọc từ bản kê khai Burn (container giao diện)."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # container giao diện (UX) là CAB đầu tiên sau phần mã: tệp '0' trong đó là bản kê khai
        i = exe.find(b'MSCF\0\0\0\0')
        co = struct.unpack_from('<I', exe, i + 8)[0]
        (td / 'ux.cab').write_bytes(exe[i:i + co])
        _expand(td / 'ux.cab', '0', td / 'ux')
        kk = (td / 'ux' / '0').read_text(encoding='utf-8', errors='replace')
    m = re.search(r'FilePath="[^"]*\\' + re.escape(MSU) + r'"[^>]*SourcePath="(a\d+)"', kk)
    if not m:
        raise RuntimeError(f'vc_redist không có {MSU}.')
    return m.group(1)


def lay_dll(tam: Path) -> list:
    """Giải nén UCRT Windows 7 x86 vào thư mục tạm; trả danh sách DLL (bản phiên bản cao nhất của mỗi tên)."""
    exe = VC.read_bytes()
    ma = _ma_goi(exe)
    (tam / 'a.cab').write_bytes(_cab_dinh_kem(exe))
    _expand(tam / 'a.cab', ma, tam / 'a')
    _expand(tam / 'a' / ma, '*', tam / 'msu')
    _expand(tam / 'msu' / MSU.replace('.msu', '.cab'), '*', tam / 'k')
    chon = {}
    for f in (tam / 'k').rglob('*.dll'):
        m = re.search(r'_(\d+)\.(\d+)\.(\d+)\.(\d+)_', f.parent.name)
        pb = tuple(int(x) for x in m.groups()) if m else (0,)
        ten = f.name.lower()
        if ten not in chon or pb > chon[ten][0]:
            chon[ten] = (pb, f)
    ds = [f for _, f in chon.values()]
    if not any(f.name.lower() == 'ucrtbase.dll' for f in ds):
        raise RuntimeError('Không lấy được ucrtbase.dll.')
    return ds


def chep_ucrt(dich) -> int:
    """Chép UCRT vào thư mục chương trình (cạnh python38.dll). Trả số file đã chép."""
    dich = Path(dich)
    with tempfile.TemporaryDirectory() as td:
        ds = lay_dll(Path(td))
        for f in ds:
            shutil.copy2(f, dich / f.name)
    return len(ds)


if __name__ == '__main__':
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    n = chep_ucrt(sys.argv[1] if len(sys.argv) > 1 else GOC.parent / 'dist' / 'PABT_Win7')
    print(f'Đã chép {n} file UCRT (Windows 7, x86).')

"""Chuẩn bị Tesseract OCR đóng kèm bộ cài (người dùng 16/10/2026: đọc PDF ảnh / ảnh scan bằng Tesseract, thay Windows OCR).

    .venv\\Scripts\\python bo_cai_win\\chuan_bi_tesseract.py <thư mục Tesseract đã giải nén> <thư mục có vie / osd.traineddata>

Nguồn (tải tay, không đưa vào git): bộ cài Windows 64-bit của UB Mannheim (github.com/UB-Mannheim/tesseract/releases, giải nén
bằng 7-Zip - KHÔNG chạy bộ cài), dữ liệu tiếng Việt / xoay trang từ github.com/tesseract-ocr/tessdata. Ra `bo_cai_win\\tesseract\\`:
chỉ tesseract.exe + các DLL nó nạp (dò theo bảng import PE - bỏ công cụ huấn luyện, pango / cairo / ICU), cắt các section .debug_*
cuối file (libtesseract-5.dll 101 MB -> ~3 MB; mã chạy giữ nguyên), tessdata\\ (vie, osd, configs\\tsv), giấy phép Apache 2.0.
rut_gon.py chép thư mục này cạnh PABT.exe của cả hai bản dựng (pabt.ocr tìm `tesseract\\` cạnh exe). Bản 64-bit chạy trên Windows
64-bit từ 7 SP1 (không nhập hàm nào chỉ có từ Windows 8); Windows 32-bit không chạy được (pabt.ocr báo rõ).
"""
from __future__ import annotations

import hashlib
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rut_gon import _nhap_dll  # noqa: E402

DICH = Path(__file__).resolve().parent / 'tesseract'
DU_LIEU = ('vie.traineddata', 'osd.traineddata')
CAU_HINH = ('tsv', 'txt')                       # tessdata\configs: đầu ra TSV (toạ độ từng từ -> gom hàng / cột như bảng)


def _ten_section(b: bytes, pe: int, i: int, sopt: int) -> str:
    o = pe + 24 + sopt + 40 * i
    ten = b[o:o + 8].rstrip(b'\0').decode('latin1')
    if ten.startswith('/'):                     # tên dài: vị trí trong bảng chuỗi sau bảng ký hiệu COFF
        psym, nsym = struct.unpack_from('<II', b, pe + 12)
        k = psym + 18 * nsym + int(ten[1:])
        ten = b[k:b.index(b'\0', k)].decode('latin1')
    return ten


def cat_debug(f: Path) -> int:
    """Bỏ các section .debug_* nằm CUỐI file PE (DWARF của MinGW) + bảng ký hiệu COFF. Trả số byte bớt (0 = không đổi)."""
    b = bytearray(f.read_bytes())
    if b[:2] != b'MZ':
        return 0
    pe = struct.unpack_from('<I', b, 0x3C)[0]
    nsec, sopt = struct.unpack_from('<H', b, pe + 6)[0], struct.unpack_from('<H', b, pe + 20)[0]
    ten = [_ten_section(bytes(b), pe, i, sopt) for i in range(nsec)]
    giu = nsec
    while giu and ten[giu - 1].startswith('.debug'):
        giu -= 1
    if giu == nsec or any(t.startswith('.debug') for t in ten[:giu]):
        return 0                                # không có / không nằm cuối: không đụng
    sec = [struct.unpack_from('<8sIIII', b, pe + 24 + sopt + 40 * i) for i in range(nsec)]
    het = max(ra + rs for _, _, _, rs, ra in sec[:giu])
    if any(sec[i][4] and sec[i][4] < het for i in range(giu, nsec)):
        return 0                                # dữ liệu debug xen giữa: không cắt
    canh = struct.unpack_from('<I', b, pe + 24 + 32)[0]                 # SectionAlignment
    _, vs, va, rs, _ = sec[giu - 1]
    cuoi = va + max(vs, rs)
    struct.pack_into('<I', b, pe + 24 + 56, (cuoi + canh - 1) // canh * canh)   # SizeOfImage
    struct.pack_into('<I', b, pe + 24 + 64, 0)                           # CheckSum (chỉ trình điều khiển cần)
    struct.pack_into('<H', b, pe + 6, giu)
    struct.pack_into('<II', b, pe + 12, 0, 0)                            # bảng ký hiệu COFF
    for i in range(giu, nsec):
        o = pe + 24 + sopt + 40 * i
        b[o:o + 40] = bytes(40)
    bot = len(b) - het
    f.write_bytes(bytes(b[:het]))
    return bot


def can_dll(goc: Path) -> list:
    """tesseract.exe + mọi DLL (trong thư mục goc) nó nạp, đệ quy."""
    co = {f.name.lower(): f for f in goc.iterdir() if f.is_file()}
    can, cho = [], ['tesseract.exe']
    while cho:
        x = cho.pop()
        if x in can:
            continue
        can.append(x)
        thuong, tre = _nhap_dll(co[x])
        cho += [d for d in thuong + tre if d in co]
    return sorted(co[x].name for x in can)


def chuan_bi(goc: Path, du_lieu: Path, dich: Path = DICH) -> Path:
    if dich.exists():
        shutil.rmtree(dich)
    (dich / 'tessdata' / 'configs').mkdir(parents=True)
    bot = 0
    for ten in can_dll(goc):
        shutil.copy2(goc / ten, dich / ten)
        bot += cat_debug(dich / ten)
    for ten in DU_LIEU:
        shutil.copy2(du_lieu / ten, dich / 'tessdata' / ten)
    for ten in CAU_HINH:
        shutil.copy2(goc / 'tessdata' / 'configs' / ten, dich / 'tessdata' / 'configs' / ten)
    for ten in ('LICENSE', 'AUTHORS'):
        if (goc / 'doc' / ten).is_file():
            shutil.copy2(goc / 'doc' / ten, dich / f'{ten}.txt')
    dong = [f'{f.relative_to(dich).as_posix()}\t{f.stat().st_size}\t{hashlib.sha256(f.read_bytes()).hexdigest()}'
            for f in sorted(dich.rglob('*')) if f.is_file()]
    (dich / 'NGUON.txt').write_text(
        'Tesseract OCR (Apache 2.0) - ban Windows 64-bit cua UB Mannheim, du lieu tessdata (tesseract-ocr).\r\n'
        'Chi giu tesseract.exe + DLL can thiet, cat section .debug_*. Dung bang bo_cai_win\\chuan_bi_tesseract.py\r\n\r\n'
        + '\r\n'.join(dong) + '\r\n', encoding='ascii')
    tong = sum(f.stat().st_size for f in dich.rglob('*') if f.is_file())
    print(f'{dich}: {len(dong)} file, {tong / 2**20:.1f} MB (bớt {bot / 2**20:.0f} MB debug)')
    return dich


def chep_vao(dist: Path) -> bool:
    """Chép bo_cai_win\\tesseract cạnh PABT.exe (rut_gon gọi cho cả hai bản dựng). Chưa chuẩn bị -> False (báo, không dừng)."""
    if not (DICH / 'tesseract.exe').is_file():
        return False
    if (dist / 'tesseract').exists():
        shutil.rmtree(dist / 'tesseract')
    shutil.copytree(DICH, dist / 'tesseract')
    return True


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    chuan_bi(Path(sys.argv[1]), Path(sys.argv[2]))

"""Tạo PDF có lớp chữ bằng tay (Helvetica, chữ ASCII) - mỗi ô một đối tượng chữ như PDF xuất từ Word / Excel."""
from __future__ import annotations


def tao_pdf(trang: list, rong: float = 842, cao: float = 595) -> bytes:
    """trang: danh sách trang; mỗi trang là danh sách (x, y, cỡ chữ, chữ) - y tính từ ĐÁY trang (PDF)."""
    obj = []
    obj.append(b'<< /Type /Catalog /Pages 2 0 R >>')
    kids = ' '.join(f'{4 + 2 * i} 0 R' for i in range(len(trang)))
    obj.append(f'<< /Type /Pages /Kids [{kids}] /Count {len(trang)} >>'.encode())
    obj.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    for i, cac in enumerate(trang):
        nd = []
        for x, y, co, chu in cac:
            chu = chu.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            nd.append(f'BT /F1 {co} Tf {x:.1f} {y:.1f} Td ({chu}) Tj ET')
        noi_dung = '\n'.join(nd).encode('latin-1', 'replace')
        obj.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {rong} {cao}] /Contents {5 + 2 * i} 0 R '
                   f'/Resources << /Font << /F1 3 0 R >> >> >>'.encode())
        obj.append(b'<< /Length %d >>\nstream\n' % len(noi_dung) + noi_dung + b'\nendstream')
    kq = bytearray(b'%PDF-1.4\n')
    vt = []
    for i, o in enumerate(obj, start=1):
        vt.append(len(kq))
        kq += f'{i} 0 obj\n'.encode() + o + b'\nendobj\n'
    xr = len(kq)
    kq += f'xref\n0 {len(obj) + 1}\n0000000000 65535 f \n'.encode()
    for v in vt:
        kq += f'{v:010d} 00000 n \n'.encode()
    kq += f'trailer\n<< /Size {len(obj) + 1} /Root 1 0 R >>\nstartxref\n{xr}\n%%EOF\n'.encode()
    return bytes(kq)


def bang_pdf(tieu_de: list, hang: list, xs: list, so_dong_moi_trang: int = 14, co: float = 10, cach: float = 14,
             can_giua: bool = False, chan_trang: str = 'Nguoi lap bieu') -> bytes:
    """tieu_de: tên cột; hang: mỗi hàng là danh sách ô, ô có thể là chuỗi hoặc danh sách dòng (ô xuống nhiều dòng); xs: vị trí x từng cột.
    can_giua: ô căn giữa theo chiều dọc (như Excel); không: căn trên. Mỗi trang lặp lại dòng tiêu đề."""
    trang, cac, y, dem = [], [], 540.0, 0

    def moi_trang():
        nonlocal cac, y, dem
        if cac:
            trang.append(cac)
        cac, y, dem = ([(xs[0], 570, 12, 'DANH SACH HO BI ANH HUONG')] if not trang else []), 540.0, 0
        for x, t in zip(xs, tieu_de):
            cac.append((x, y, co, t))
        y -= cach * 1.6
    moi_trang()
    for h in hang:
        o = [[c] if isinstance(c, str) else list(c) for c in h]
        n = max(len(c) for c in o)
        if dem + n > so_dong_moi_trang:
            moi_trang()
        for x, c in zip(xs, o):
            bd = (n - len(c)) / 2 if can_giua else 0
            for k, dong in enumerate(c):
                if dong:
                    cac.append((x, y - (bd + k) * cach, co, dong))
        y -= n * cach
        dem += n
    cac.append((xs[0], y - cach, co, chan_trang))
    trang.append(cac)
    return tao_pdf(trang)

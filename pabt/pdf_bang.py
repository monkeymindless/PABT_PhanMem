"""Tách bảng danh sách hộ kèm quyết định (PDF xuất từ Excel / Word: có lớp chữ) theo vị trí cột.

Ô họ tên, địa chỉ trong bảng thường xuống nhiều dòng (một phần nằm trên, một phần dưới dòng số liệu), nên không đọc theo dòng
chữ được. Cách làm: lấy chữ của trang giữ nguyên bố cục (pypdf, extraction_mode='layout'), tìm hàng đánh số cột "1 2 3 … N"
dưới tiêu đề bảng -> vị trí tâm từng cột; chữ tiêu đề phía trên -> ý nghĩa cột (tổng cộng, đất, nhà / vật kiến trúc, cây, hỗ trợ,
thưởng); dòng có số thứ tự ở cột đầu là dòng số liệu của một hộ; các dòng chữ còn lại gán vào hộ gần nhất (họ tên, địa chỉ).
Phân loại cột dùng chung cho bảng Excel / Word (loai_cot).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .lap_pa import bo_dau
from .tien import D, KHONG

# Đọc PDF quyết định MỘT lần (0.9.87): đọc / xem lại cùng một file (dien_so_ky, doc_bang_pdf, mở lại hộp Trạng thái…) dùng lại
# PdfReader và kết quả theo (đường dẫn, mtime_ns, cỡ) - file đổi thì đọc lại. Giữ tối đa _NHO_TOI_DA file.
_NHO = {}
_NHO_TOI_DA = 4


def _khoa_file(file):
    import os
    st = os.stat(file)
    return str(Path(file).resolve()), st.st_mtime_ns, st.st_size


def _nho(file, loai: str, tao):
    """Giá trị tao() của file nhớ theo loại ('reader' / 'layout' / 'ky'); file không đọc được: tao() như thường."""
    try:
        k = _khoa_file(file)
    except OSError:
        return tao()
    muc = _NHO.get(k[0])
    if muc is None or muc[0] != k[1:]:
        if len(_NHO) >= _NHO_TOI_DA:
            _NHO.pop(next(iter(_NHO)))
        muc = _NHO[k[0]] = (k[1:], {})
    if loai not in muc[1]:
        muc[1][loai] = tao()
    return muc[1][loai]


def xoa_nho() -> None:
    _NHO.clear()


def _reader(file):
    from pypdf import PdfReader
    return _nho(file, 'reader', lambda: PdfReader(str(file)))

# loại cột tiền theo chữ tiêu đề (không dấu); thứ tự kiểm tra quan trọng ("bồi thường" có chữ "thường")
_LOAI = [
    ('dien_tich', r'dien tich|\(m2\)|m2\b'),
    ('so_tien', r'tong cong|tong gia tri|tong so tien|tong kinh phi|cong gia tri|thanh tien'),
    ('tien_thuong', r'(?<!boi )thuong (di doi|ban giao|chap hanh|tien do)|^thuong\b'),
    ('tien_cay', r'cay trong|\bcay\b|vat nuoi'),
    ('tien_tai_san', r'nha o|\bnha\b|vat kien truc|cong trinh|tai san'),
    ('tien_dat', r'(boi thuong|ho tro|gia tri).{0,20}\bdat\b|\bve dat\b|tien dat'),
    ('tien_ho_tro', r'ho tro|on dinh|dao tao|chuyen doi nghe|chinh sach|thue nha'),
]


def loai_cot(tieu_de: str) -> str:
    """Khóa tiền (so_tien, tien_dat, tien_tai_san, tien_cay, tien_ho_tro, tien_thuong) theo chữ tiêu đề cột; '' nếu không phải
    cột tiền; 'dien_tich' cho cột diện tích."""
    t = bo_dau(tieu_de)
    for k, m in _LOAI:
        if re.search(m, t):
            return k
    return ''


@dataclass
class DongBang:
    stt: int
    ten: str
    dia_chi: str = ''
    tien: dict = field(default_factory=dict)       # so_tien, tien_dat, tien_tai_san, tien_cay, tien_ho_tro, tien_thuong
    chu: str = ''                                  # toàn bộ chữ của hộ (để hiện / tìm)

    @property
    def khop_tong(self) -> bool | None:
        """Các cột thành phần cộng lại = cột tổng cộng (None nếu không có cột tổng / không có thành phần)."""
        if 'so_tien' not in self.tien:
            return None
        tp = [v for k, v in self.tien.items() if k != 'so_tien']
        return sum(tp, KHONG) == self.tien['so_tien'] if tp else None


def dong_layout(file) -> list:
    """Các dòng chữ giữ bố cục của mọi trang PDF (pypdf); [] nếu không có pypdf / không đọc được. Nhớ theo file (_nho)."""
    return list(_nho(file, 'layout', lambda: _dong_layout(file)))


def _dong_layout(file) -> list:
    try:
        import pypdf  # noqa: F401
    except ImportError:
        return []
    try:
        kq = []
        for trang in _reader(file).pages:
            try:
                t = trang.extract_text(extraction_mode='layout')
            except TypeError:                              # pypdf cũ không có chế độ bố cục
                return []
            kq += (t or '').splitlines()
        return kq
    except Exception:                                      # pypdf báo nhiều loại lỗi khác nhau với file hỏng
        return []


_DOAN = re.compile(r'\S+(?: \S+)*')                        # đoạn chữ: các từ cách nhau một dấu cách (2+ dấu cách = sang ô khác)


def _doan(dong: str) -> list:
    """[(chữ, vị trí giữa)] các đoạn chữ của dòng."""
    return [(m.group(0), (m.start() + m.end() - 1) / 2) for m in _DOAN.finditer(dong)]


def _hang_so_cot(dong: str):
    """Dòng chỉ gồm các số 1, 2, 3, … N liên tiếp (N ≥ 5) -> [vị trí tâm cột]; không phải thì None."""
    so = [(m.group(0), (m.start() + m.end() - 1) / 2) for m in re.finditer(r'\S+', dong)]
    if len(so) < 5 or [x for x, _ in so] != [str(i) for i in range(1, len(so) + 1)]:
        return None
    return [p for _, p in so]


def _so_tien(s: str):
    s = s.strip()
    if s in ('-', '–', '—', '0'):
        return KHONG
    if re.fullmatch(r'\d{1,3}(\.\d{3})+', s) or re.fullmatch(r'\d+', s):
        return D(s.replace('.', ''))
    if re.fullmatch(r'\d{1,3}(,\d{3})+', s):
        return D(s.replace(',', ''))
    return None


def _cot_gan(tam: list, x: float) -> int:
    return min(range(len(tam)), key=lambda i: abs(tam[i] - x))


_TIEU_DE_COT = re.compile(r'ho (va )?ten|dia chi|dien tich|nong nghiep|kien truc|gia tri boi|^\s*st\s*$|^\s*t\s+ho')


def _gom_cot(chu_dong: dict, du_lieu: list, so_dong: int) -> dict:
    """Chữ của một cột (họ tên / địa chỉ) theo từng dòng -> {dòng số liệu: chữ của ô}. Ô Excel xuống nhiều dòng, căn giữa
    theo chiều dọc quanh dòng số liệu; giữa hai ô thường có dòng trống trong cột. Khối liền (không dòng trống) chứa nhiều dòng
    số liệu: phần giữa hai dòng số liệu chia theo căn giữa (dưới dòng số liệu ≈ số dòng phía trên, ít nhất 1)."""
    kq = {d: [] for d in du_lieu}
    co = set(du_lieu)
    k = 0
    while k < so_dong:
        if not chu_dong.get(k) and k not in co:
            k += 1
            continue
        dau = k
        while k < so_dong and (chu_dong.get(k) or k in co):
            k += 1
        khoi = list(range(dau, k))
        dl = [x for x in khoi if x in co]
        if not dl:                                         # khối không có dòng số liệu: gán dòng số liệu gần nhất
            if du_lieu:
                gan = min(du_lieu, key=lambda d: abs(d - (dau + k - 1) / 2))
                kq[gan] += [chu_dong[x] for x in khoi if chu_dong.get(x)]
            continue
        tren = [x for x in khoi if x < dl[0]]
        kq[dl[0]] += [chu_dong[x] for x in tren if chu_dong.get(x)]
        so_tren = len(tren)
        for i, d in enumerate(dl):
            if chu_dong.get(d):
                kq[d].append(chu_dong[d])
            sau = dl[i + 1] if i + 1 < len(dl) else k
            giua = list(range(d + 1, sau))
            n = len(giua) if i + 1 == len(dl) else min(len(giua), max(so_tren, 1))
            kq[d] += [chu_dong[x] for x in giua[:n] if chu_dong.get(x)]
            if i + 1 < len(dl):
                kq[dl[i + 1]] += [chu_dong[x] for x in giua[n:] if chu_dong.get(x)]
                so_tren = len(giua) - n
    return {d: ' '.join(' '.join(v).split()) for d, v in kq.items()}


def tach_bang(dong: list) -> list:
    """[DongBang] của các bảng có hàng đánh số cột trong các dòng giữ bố cục."""
    kq = []
    stt_cuoi = 0
    i = 0
    while i < len(dong):
        tam = _hang_so_cot(dong[i])
        if tam is None:
            i += 1
            continue
        # tiêu đề cột: các dòng phía trên tới dòng "(Kèm theo ...)" / tên bảng / dòng trống (tối đa 8 dòng)
        nhan = [''] * len(tam)
        for j in range(i - 1, max(-1, i - 9), -1):
            t = bo_dau(dong[j])
            if not dong[j].strip() or 'kem theo' in t or 'bang tong hop' in t or 'danh sach' in t:
                break
            for chu, x in _doan(dong[j]):
                c = _cot_gan(tam, x)
                nhan[c] = (chu + ' ' + nhan[c]).strip()
        loai = [loai_cot(x) for x in nhan]
        c_ten = next((c for c, x in enumerate(nhan) if re.search(r'ho (va )?ten|ten chu|chu su dung|ten to chuc', bo_dau(x))), 1)
        c_dc = next((c for c, x in enumerate(nhan) if 'dia chi' in bo_dau(x)), None)
        # các dòng tới hàng đánh số cột kế tiếp (bảng sang trang lặp lại tiêu đề: bỏ các dòng tiêu đề)
        j = i + 1
        than = []
        while j < len(dong) and _hang_so_cot(dong[j]) is None:
            if dong[j].strip() and not _TIEU_DE_COT.search(bo_dau(dong[j])):
                than.append(dong[j])
            j += 1
        du_lieu = {}                                       # chỉ số dòng -> (stt, {cột: số})
        het = False
        for k, d in enumerate(than):
            ds = _doan(d)
            if not ds:
                continue
            dau, x0 = ds[0]
            if re.match(r'\s*(tong cong|cong)\b', bo_dau(dau)):
                het = True
            if het:
                break
            m = re.match(r'(\d{1,4})(?: |$)', dau)
            if not m or _cot_gan(tam, x0 - (len(dau) - len(m.group(1))) / 2) != 0:
                continue
            stt = int(m.group(1))
            if stt != stt_cuoi + 1 and not (stt == 1 and not du_lieu):
                continue                                   # dòng tổng / mục ghi chú dưới bảng có số đầu dòng
            gia = {}
            for chu, x in (ds[1:] if dau == m.group(1) else ds):
                c = _cot_gan(tam, x)
                if loai[c] and loai[c] != 'dien_tich':
                    for tu in chu.split():
                        v = _so_tien(tu)
                        if v is not None:
                            gia[c] = gia.get(c, KHONG) + v
            if gia:
                du_lieu[k] = (stt, gia)
                stt_cuoi = stt
        if du_lieu:
            cuoi = min(len(than), max(du_lieu) + 8)
            for k in range(max(du_lieu) + 1, cuoi):         # hết bảng: dòng "Cộng", các mục tổng "1. …", chữ ký
                if re.match(r'\s*((tong )?cong\b|\d+(\.\d+)*\. |nguoi lap|tm\.)', bo_dau(than[k])):
                    cuoi = k
                    break
            ten, dc = {}, {}
            for k, d in enumerate(than[:cuoi]):
                for chu, x in _doan(d):
                    c = _cot_gan(tam, x)
                    if c == 0:
                        if k in du_lieu and re.fullmatch(r'\d{1,4}', chu):
                            continue
                        if re.match(r'\d{1,4} ', chu) and k in du_lieu:
                            chu = chu.split(' ', 1)[1]
                        c = c_ten                           # chữ lệch trái vào cột STT hẹp: thuộc cột họ tên
                    if c == c_ten:
                        ten[k] = (ten.get(k, '') + ' ' + chu).strip()
                    elif c_dc is not None and c == c_dc:
                        dc[k] = (dc.get(k, '') + ' ' + chu).strip()
            ds_dl = sorted(du_lieu)
            ten_o = _gom_cot(ten, ds_dl, min(cuoi, len(than)))
            dc_o = _gom_cot(dc, ds_dl, min(cuoi, len(than)))
            for k in ds_dl:
                stt, gia = du_lieu[k]
                tien = {}
                for c, v in gia.items():
                    tien[loai[c]] = tien.get(loai[c], KHONG) + v
                kq.append(DongBang(stt, ten_o[k], dc_o[k], tien, f'{ten_o[k]} - {dc_o[k]}'))
        i = j
    return kq


def chu_chu_ky(file) -> list:
    """Chữ đóng kèm chữ ký số (số văn bản, ngày, tháng do phần mềm ký số điền lúc ký, nằm trong hình hiển thị của ô chữ ký -
    không thuộc lớp chữ của trang): [(trang, x giữa, y giữa, rộng trang, chữ)]. Nhớ theo file (_nho)."""
    return list(_nho(file, 'ky', lambda: _chu_chu_ky(file)))


def _chu_chu_ky(file) -> list:
    try:
        from pypdf import PageObject
        from pypdf.generic import NameObject
    except ImportError:
        return []
    kq = []
    try:
        doc = _reader(file)
        for i, trang in enumerate(doc.pages):
            rong = float(trang.mediabox.width)
            for a in trang.get('/Annots') or []:
                o = a.get_object()
                if o.get('/Subtype') != '/Widget' or o.get('/FT') != '/Sig':
                    continue
                n = (o.get('/AP') or {}).get('/N')
                if n is None:
                    continue
                n = n.get_object()
                x0, y0, x1, y1 = (float(v) for v in o['/Rect'])
                if x1 - x0 <= 1 or y1 - y0 <= 1:
                    continue
                p = PageObject.create_blank_page(width=x1 - x0, height=y1 - y0)
                if n.get('/Resources') is not None:
                    p[NameObject('/Resources')] = n.get('/Resources')
                p.replace_contents(n)
                chu = ' '.join((p.extract_text() or '').split())
                if chu:
                    kq.append((i, (x0 + x1) / 2, (y0 + y1) / 2, rong, chu))
    except Exception:                                      # chữ ký hỏng / pypdf cũ: bỏ qua
        return []
    return kq


def dien_so_ky(dong: list, file) -> list:
    """Điền số văn bản, ngày, tháng đóng kèm chữ ký số vào các chỗ trống của văn bản ("Số: /QĐ-UBND", "ngày tháng năm 2026",
    "Kèm theo Quyết định số: /QĐ-UBND"). dong: [[chữ]] (nhap_don_gia.doc_bang). Trả danh sách dòng mới."""
    ky = [x for x in chu_chu_ky(file) if re.fullmatch(r'\d{1,6}', x[4])]
    if not ky:
        return dong
    trai = sorted((x for x in ky if x[1] < x[3] / 2), key=lambda x: (x[0], -x[2]))     # bên trái: số văn bản
    phai = [x for x in ky if x[1] >= x[3] / 2]
    so = trai[0][4] if trai else ''
    # ngày, tháng: các số bên phải cùng hàng (gần nhau theo chiều dọc), xếp trái sang phải
    ngay = []
    if phai:
        dau = sorted(phai, key=lambda x: (x[0], -x[2]))[0]
        ngay = [x[4] for x in sorted((x for x in phai if x[0] == dau[0] and abs(x[2] - dau[2]) < 12), key=lambda x: x[1])]
    kq = []
    for r in dong:
        r2 = []
        for o in r:
            t = str(o)
            if so:
                t = re.sub(r'(?i)(s[ốo]\s*:?)\s*(/\s*Q[ĐD])', lambda m: f'{m.group(1)} {so}{m.group(2)}', t, count=1)
            if len(ngay) >= 2:
                t = re.sub(r'(?i)ng[àa]y\s+th[áa]ng\s+n[ăa]m', f'ngày {ngay[0]} tháng {ngay[1]} năm', t, count=1)
            r2.append(t)
        kq.append(r2)
    return kq


def doc_bang_pdf(file) -> list:
    """[DongBang] của file PDF có lớp chữ (rỗng nếu không thấy bảng có hàng đánh số cột)."""
    return tach_bang(dong_layout(file))

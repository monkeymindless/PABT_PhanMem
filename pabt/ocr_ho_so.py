"""Quét giấy tờ hộ dân (0.9.87 - người dùng 14/10/2026): Giấy chứng nhận quyền sử dụng đất (sổ đỏ / sổ hồng, mẫu cũ và mẫu 2024),
biên bản kiểm kê / kiểm đếm thực địa - từ PDF có chữ, PDF scan hoặc ẢNH CHỤP điện thoại (.jpg / .png… chép từ điện thoại / Zalo).
Không Qt.

Nhận dạng chữ: lớp chữ của PDF nếu có, không thì Tesseract (ocr.py - tiếng Việt, chạy trên máy, KHÔNG gửi giấy tờ ra ngoài - Nghị định
13/2023; người dùng chọn 14/10/2026 thay PaddleOCR / API thị giác máy tính). Tesseract đọc CHỮ IN; chữ viết tay (biên bản điền tay) đọc
không được / sai nhiều - người dùng soát lại trên bảng trước khi điền.

Bóc tách (boc_tach, theo nhãn của mẫu giấy tờ, không phụ thuộc vị trí):
- chủ sử dụng: họ tên sau "Ông / Bà / Hộ ông (bà) / Họ và tên (chủ hộ)", số CCCD / CMND / định danh (9 hoặc 12 chữ số), địa chỉ
  ("Địa chỉ thường trú / Địa chỉ / Thường trú");
- thửa đất: "Thửa đất số", "Tờ bản đồ số", "Diện tích", loại đất từ "Mục đích sử dụng / Loại đất" (tên loại -> mã theo danh mục Luật Đất
  đai 2024, có sẵn mã thì giữ); nhiều thửa trong một giấy -> nhiều dòng;
- tài sản (biên bản kiểm kê): các dòng bảng sau tiêu đề có "Tên tài sản / Hạng mục / Loại cây" tới dòng "Tổng / Cộng" hoặc phần ký tên ->
  bỏ STT -> phan_loai_tai_san.doc_danh_sach (cùng bộ đọc với "Dán danh sách tài sản": Tên ĐVT Số lượng, phân loại nhà / cây / vật nuôi).
"""
from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


DUOI = ('.pdf',) + ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp')


@dataclass
class KetQuaOcr:
    loai: str = 'khac'                       # gcn / bien_ban / khac
    ho_ten: str = ''
    so_cccd: str = ''
    dia_chi: str = ''
    thua: list = field(default_factory=list)          # [{'so_to', 'so_thua', 'dt_thu_hoi', 'loai_dat', 'dia_chi_thua'}]
    tai_san: list = field(default_factory=list)       # [{'ten', 'dvt', 'so_luong', 'ty_le', 'ghi_chu'}] (doc_danh_sach)
    dong_tai_san: list = field(default_factory=list)  # dòng chữ gốc của bảng tài sản (đưa vào "Dán danh sách tài sản")
    canh_bao: list = field(default_factory=list)


# ---------------------------------------------------------------- đọc file
def doc_chu(file, bao_tien_do=None, cho=None) -> tuple:
    """(chữ toàn văn, đã phải OCR?) của PDF / ảnh. Lỗi -> ocr.LoiOCR / LoiNhap (thông báo tiếng Việt)."""
    from .quan_ly import doc_van_ban
    dong, da_ocr = doc_van_ban(Path(file), bao_tien_do, cho)
    chu = '\n'.join(' '.join(str(o) for o in d if str(o or '').strip()) for d in dong)
    return chu, da_ocr


# ---------------------------------------------------------------- tiện ích chữ
def _bo_dau(s: str) -> str:
    s = unicodedata.normalize('NFD', str(s or '')).replace('đ', 'd').replace('Đ', 'D')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()


def _vi_tri(chu: str, mau: str, tu: int = 0):
    """Tìm mẫu (viết không dấu, regex) trên chữ không dấu - trả (đầu, cuối) theo chữ gốc (bỏ dấu giữ nguyên độ dài khi NFC)."""
    m = re.compile(mau, re.I).search(_bo_dau_giu_do_dai(chu), tu)
    return (m.start(), m.end()) if m else None


def _bo_dau_giu_do_dai(s: str) -> str:
    """Bỏ dấu từng ký tự (giữ số ký tự - để vị trí khớp chữ gốc)."""
    kq = []
    for c in unicodedata.normalize('NFC', s):
        b = _bo_dau(c)
        kq.append(b[0] if b else c)
    return ''.join(kq)


def _sau_nhan(chu: str, mau: str, het: str = r'[\n;]') -> str:
    """Giá trị sau nhãn (tới hết dòng / dấu chấm phẩy)."""
    c = unicodedata.normalize('NFC', chu)
    vt = _vi_tri(c, mau)
    if not vt:
        return ''
    m = re.compile(het).search(c, vt[1])
    return c[vt[1]:m.start() if m else len(c)].strip(' :.-\t')


def _chuan_ho_ten(s: str) -> str:
    s = re.split(r',|\bnăm sinh\b|\bsinh năm\b|\bsinh ngày\b|\bngày sinh\b|\bCCCD\b|\bCMND\b|\bsố định danh\b', s, flags=re.I)[0]
    s = ' '.join(re.sub(r'[^\wÀ-ỹ\s]', ' ', s).split())
    return ' '.join(w[:1].upper() + w[1:].lower() for w in s.split()) if s.isupper() or s.islower() else s


_RE_CCCD = re.compile(r'(?<!\d)(\d[\d .]{7,16}\d)(?!\d)')


def _so_cccd(chu: str) -> str:
    c = unicodedata.normalize('NFC', chu)
    vt = _vi_tri(c, r'(cccd|can cuoc|cmnd|chung minh nhan dan|so dinh danh|dinh danh ca nhan)')
    vung = c[vt[1]:vt[1] + 80] if vt else c
    for m in _RE_CCCD.finditer(vung):
        s = re.sub(r'\D', '', m.group(1))
        if len(s) in (12, 9):
            return s
    return ''


def _so(s: str):
    from .tien import doc_so_vn
    s = (s or '').replace('m2', '').replace('m²', '').strip()
    m = re.search(r'\d[\d.,]*', s)
    if not m:
        return None
    try:
        return doc_so_vn(m.group(0).rstrip('.,'))
    except Exception:                                    # noqa: BLE001
        return None


# loại đất: tên (không dấu) -> mã, theo danh mục loai_dat (Luật Đất đai 2024, TT 08/2024) + tên quen dùng trên GCN mẫu cũ
_TEN_LOAI_THEM = {'dat o tai nong thon': 'ONT', 'dat o tai do thi': 'ODT', 'dat trong cay lau nam': 'CLN',
                  'dat trong lua': 'LUA', 'dat chuyen trong lua nuoc': 'LUC', 'dat trong cay hang nam khac': 'HNK',
                  'dat bang trong cay hang nam khac': 'BHK', 'dat nuoi trong thuy san': 'NTS', 'dat rung san xuat': 'RSX',
                  'dat co so san xuat phi nong nghiep': 'SKC', 'dat thuong mai dich vu': 'TMD'}


def ma_loai_dat(chu: str) -> str:
    """Mã loại đất từ chữ "Mục đích sử dụng" ("Đất ở tại nông thôn" -> ONT; "ONT" giữ nguyên; nhiều loại -> "ONT+CLN")."""
    from .loai_dat import LOAI_DAT
    co_ma = {x[0].upper() for x in LOAI_DAT}
    ma = [t for t in re.findall(r'\b[A-Z]{3}\b', chu or '') if t in co_ma]
    if ma:
        return '+'.join(dict.fromkeys(ma))
    k = _bo_dau(chu)
    ten = dict(_TEN_LOAI_THEM)
    ten.update({_bo_dau(x[1]): x[0] for x in LOAI_DAT})
    # tên dài trước; tên ngắn nằm trong đoạn đã khớp tên dài thì bỏ ("Đất ở" trong "Đất ở tại nông thôn")
    phu, tim = [], []
    for t, m in sorted(ten.items(), key=lambda x: -len(x[0])):
        for mm in re.finditer(re.escape(t), k) if t else ():
            a, b = mm.span()
            if not any(a < y and x < b for x, y in phu):
                phu.append((a, b))
                tim.append((a, m))
    da, kq = set(), []
    for _, m in sorted(tim):
        if m not in da:
            da.add(m)
            kq.append(m)
    return '+'.join(kq[:3])


# ---------------------------------------------------------------- bóc tách
_NHAN_HO_TEN = (r'(?:ho va ten chu ho|ho ten chu ho|ten chu su dung|chu su dung dat|ho va ten|ho ten|ho ong \(ba\)|ho ong/ba)\s*:?'
                r'|\b(?:ong \(ba\)|ong/ba|ong|ba)\b\s*:')          # "Ông:" / "Bà:" phải là từ riêng có dấu hai chấm


def _thua(chu: str) -> list:
    """Các thửa: mỗi lần xuất hiện "Thửa đất số" mở một thửa; tờ / diện tích / loại đất lấy trong đoạn tới thửa kế tiếp."""
    c = unicodedata.normalize('NFC', chu)
    k = _bo_dau_giu_do_dai(c)
    dau = [m.start() for m in re.finditer(r'thua dat so|thua so', k)]
    kq = []
    for i, d in enumerate(dau):
        doan = c[d:dau[i + 1] if i + 1 < len(dau) else len(c)]
        kd = _bo_dau_giu_do_dai(doan)
        m = re.search(r'thua (?:dat )?so\s*:?\s*([0-9A-Za-z]+)', kd)
        so_thua = m.group(1) if m else ''
        m = re.search(r'to ban do so\s*:?\s*([0-9A-Za-z]+)', kd)
        so_to = m.group(1) if m else ''
        if not so_to:                                     # "Tờ bản đồ số" đứng trước "Thửa đất số" (một số mẫu)
            m = list(re.finditer(r'to ban do so\s*:?\s*([0-9A-Za-z]+)', _bo_dau_giu_do_dai(c[max(0, d - 120):d])))
            so_to = m[-1].group(1) if m else ''
        m = re.search(r'dien tich(?: thu hoi)?\s*:?\s*([\d.,]+)', kd)
        dt = _so(m.group(1)) if m else None
        vt = re.search(r'(muc dich su dung|loai dat)\s*:?', kd)
        loai = ''
        if vt:
            het = re.search(r'\n\s*(?:[a-h]\)|thoi han|nguon goc)', kd[vt.end():])
            loai = ma_loai_dat(doan[vt.end():vt.end() + (het.start() if het else 200)])
        m = re.search(r'dia chi(?: thua dat)?\s*:?', kd)
        dc = ''
        if m:
            dc = doan[m.end():].split('\n')[0].strip(' :;.')
        if so_thua:
            kq.append(dict(so_to=so_to.lstrip('0') or so_to, so_thua=so_thua.lstrip('0') or so_thua, dt_thu_hoi=dt, loai_dat=loai,
                           dia_chi_thua=dc))
    return kq


_RE_TIEU_DE_TS = re.compile(r'ten tai san|hang muc|loai tai san|ten cay|loai cay|vat kien truc|cong trinh', re.I)
_RE_HET_TS = re.compile(r'^\s*(tong cong|tong so|cong:|cong\b|dai dien|nguoi lap|can bo|chu ho|xac nhan|ghi chu:)', re.I)


def _dong_tai_san(chu: str) -> list:
    """Dòng bảng tài sản của biên bản kiểm kê (đã bỏ STT), theo thứ tự."""
    dong = [x.strip() for x in unicodedata.normalize('NFC', chu).split('\n')]
    kq, trong_bang = [], False
    for x in dong:
        kd = _bo_dau(x)
        if not trong_bang:
            if _RE_TIEU_DE_TS.search(kd) and re.search(r'dvt|don vi|so luong|khoi luong|kich thuoc', kd):
                trong_bang = True
            continue
        if not x:
            continue
        if _RE_HET_TS.search(kd):
            if kq:
                trong_bang = False
            continue
        if re.fullmatch(r'[IVX]+\.?.*|[A-Z]\..*|[0-9]+\.\s*[A-ZĐ][^0-9]*', x) and not re.search(r'\d+[.,]?\d*\s*$', x):
            continue                                       # tiêu đề nhóm ("I. NHÀ, CÔNG TRÌNH", "2. Cây trồng")
        x = re.sub(r'^\s*\d{1,3}(?:\.\d{1,2})?[.)]?\s+', '', x)       # STT "1", "1.2", "3)"
        if re.search(r'[A-Za-zÀ-ỹ]', x) and re.search(r'\d', x):
            kq.append(' '.join(x.split()))
    return kq


def boc_tach(chu: str) -> KetQuaOcr:
    """Thông tin chủ sử dụng, thửa đất, tài sản từ chữ của giấy tờ (đã OCR hoặc lớp chữ PDF)."""
    c = unicodedata.normalize('NFC', chu or '')
    k = _bo_dau(c)
    kq = KetQuaOcr()
    if 'giay chung nhan' in k and ('quyen su dung dat' in k or 'quyen so huu' in k):
        kq.loai = 'gcn'
    elif re.search(r'bien ban (kiem ke|kiem dem|dieu tra|xac minh)', k):
        kq.loai = 'bien_ban'
    ten = _sau_nhan(c, _NHAN_HO_TEN, r'[\n;,]|\bnăm sinh|\bsinh năm|\bCCCD|\bCMND')
    kq.ho_ten = _chuan_ho_ten(ten)[:80] if ten and len(ten) < 120 else ''
    kq.so_cccd = _so_cccd(c)
    kq.dia_chi = _sau_nhan(c, r'(dia chi thuong tru|noi thuong tru|thuong tru tai|dia chi)\s*:?')[:200]
    kq.thua = _thua(c)
    kq.dong_tai_san = _dong_tai_san(c)
    if kq.dong_tai_san:
        from .phan_loai_tai_san import doc_danh_sach
        try:
            kq.tai_san = doc_danh_sach('\n'.join(kq.dong_tai_san))
        except Exception:                                  # noqa: BLE001 - dòng lạ: vẫn giữ chữ gốc để người dùng sửa
            kq.tai_san = []
    if not kq.ho_ten:
        kq.canh_bao.append('Không tìm thấy họ tên chủ sử dụng (nhãn "Ông / Bà / Họ và tên…").')
    if not kq.so_cccd:
        kq.canh_bao.append('Không tìm thấy số CCCD / CMND (12 hoặc 9 chữ số sau nhãn).')
    if not kq.thua and kq.loai == 'gcn':
        kq.canh_bao.append('Không tìm thấy "Thửa đất số" - ảnh mờ / nghiêng: chụp lại thẳng, đủ sáng hoặc nhập tay.')
    for t in kq.thua:
        if t['dt_thu_hoi'] is None:
            kq.canh_bao.append(f'Thửa {t["so_thua"]}: không đọc được diện tích.')
    return kq


def doc_va_boc_tach(file, bao_tien_do=None, cho=None) -> tuple:
    """(KetQuaOcr, chữ toàn văn, đã OCR?) của một file."""
    chu, da_ocr = doc_chu(file, bao_tien_do, cho)
    return boc_tach(chu), chu, da_ocr


def gop(ds: list) -> KetQuaOcr:
    """Gộp kết quả nhiều file (mặt trước / sau GCN, nhiều trang biên bản): lấy giá trị đầu tiên có, thửa / tài sản nối tiếp."""
    kq = KetQuaOcr()
    for x in ds:
        for k in ('ho_ten', 'so_cccd', 'dia_chi'):
            if not getattr(kq, k) and getattr(x, k):
                setattr(kq, k, getattr(x, k))
        if kq.loai == 'khac':
            kq.loai = x.loai
        da = {(t['so_to'], t['so_thua']) for t in kq.thua}
        kq.thua += [t for t in x.thua if (t['so_to'], t['so_thua']) not in da]
        kq.tai_san += x.tai_san
        kq.dong_tai_san += x.dong_tai_san
    if kq.ho_ten and kq.so_cccd:
        kq.canh_bao = [w for x in ds for w in x.canh_bao if 'họ tên' not in w and 'CCCD' not in w]
    else:
        kq.canh_bao = [w for x in ds for w in x.canh_bao]
    return kq


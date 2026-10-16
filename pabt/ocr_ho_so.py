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
    # 0.9.95: phương án chi tiết của hộ đã số hóa (loai 'pa_chi_tiet')
    nhan_khau: int | None = None
    nguon_goc: str = ''
    tai_dinh_cu: str = ''


# ---------------------------------------------------------------- đọc file
def doc_chu(file, bao_tien_do=None, cho=None) -> tuple:
    """(chữ toàn văn, đã phải OCR?) của PDF / ảnh. Lỗi -> ocr.LoiOCR / LoiNhap (thông báo tiếng Việt)."""
    from .quan_ly import doc_van_ban
    dong, da_ocr = doc_van_ban(Path(file), bao_tien_do, cho)
    # 0.9.95: ô của một hàng nối bằng Tab (giữ cột bảng phương án chi tiết: Tên \t ĐVT \t Số lượng \t Đơn giá…)
    chu = '\n'.join('\t'.join(str(o).strip() for o in d if str(o or '').strip()) for d in dong)
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
    """Giá trị sau nhãn (tới hết dòng / dấu chấm phẩy / ô kế - Tab). Dấu cách / Tab / ":" ngay sau nhãn bỏ qua trước (ô giá trị
    của bảng nằm sau nhãn một Tab)."""
    c = unicodedata.normalize('NFC', chu)
    vt = _vi_tri(c, mau)
    if not vt:
        return ''
    dau = vt[1]
    while dau < len(c) and c[dau] in ' \t:.-':
        dau += 1
    m = re.compile(het).search(c, dau)
    return c[dau:m.start() if m else len(c)].strip(' :.-\t')


def _chuan_ho_ten(s: str) -> str:
    s = re.split(r',|\bnăm sinh\b|\bsinh năm\b|\bsinh ngày\b|\bngày sinh\b|\bCCCD\b|\bCMND\b|\bsố định danh\b', s, flags=re.I)[0]
    s = ' '.join(re.sub(r'[^\wÀ-ỹ\s]', ' ', s).split())
    return ' '.join(w[:1].upper() + w[1:].lower() for w in s.split()) if s.isupper() or s.islower() else s


_RE_CCCD = re.compile(r'(?<!\d)(\d[\d .]{7,16}\d)(?!\d)')


def _sua_so_ocr(s: str) -> str:
    """Lỗi nhận dạng hay gặp trong dãy số: O / o -> 0, l / I / | -> 1 (chỉ trong cụm >= 6 ký tự toàn số / các chữ đó)."""
    return re.sub(r'(?<![A-Za-zÀ-ỹ])[\dOoIl|][\dOoIl| .]{5,}[\dOoIl|](?![A-Za-zÀ-ỹ])',
                  lambda m: m.group(0).translate(str.maketrans('OoIl|', '00111')) if sum(ch.isdigit() for ch in m.group(0)) >= 4
                  else m.group(0), s)


def _so_cccd(chu: str) -> str:
    c = unicodedata.normalize('NFC', chu)
    vt = _vi_tri(c, r'(cccd|can cuoc|cmnd|chung minh nhan dan|so dinh danh|dinh danh ca nhan)')
    vung = _sua_so_ocr(c[vt[1]:vt[1] + 80] if vt else c)
    for m in _RE_CCCD.finditer(vung):
        s = re.sub(r'\D', '', m.group(1))
        if len(s) in (12, 11, 9, 8):
            from .nhap_excel import chuan_cccd                 # 11 số (mất số 0 đầu khi qua Excel / OCR) -> 12; CMND 8 -> 9
            s = chuan_cccd(s)
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
                r'|\b(?:ong \(ba\)|ong/ba|ong|ba|chu ho|to chuc)\b\s*:')   # "Ông:" / "Bà:" / "Tổ chức:" - từ riêng có dấu hai chấm


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


# ---------------------------------------------------------------- phương án chi tiết của hộ đã số hóa (0.9.95)
# bản in IN_CHITIET (in_an.lap_chi_tiet): "I. … Họ và tên / Số CCCD / Địa chỉ", "II. Thông tin (vị trí,) nguồn gốc đất", "III. Bảng tính
# toán bồi thường, hỗ trợ" (STT | Tên tài sản | ĐVT | Số lượng | Đơn giá | Tỷ lệ | Thành tiền | Ghi chú; mục 1 đất … 6 thưởng),
# "TỔNG CỘNG", "IV. Phương án tái định cư: …". Chữ có thể từ lớp chữ PDF (ô bị ngắt dòng, "m²" thành "m" + "2") hoặc OCR (ô cách nhau
# bằng Tab - ocr.gom_dong) - đọc theo DÒNG LOGIC: dòng mới bắt đầu bằng STT (1, 1.2, 2.10, -), dòng khác nối vào dòng trước.
_RE_STT = re.compile(r'^\s*(\d{1,2}(?:\.\d{1,3})?|-)(?=[\s\t])')
_RE_DVT_PA = re.compile(r'^(m\s*2|m²|m2|m\s*3|m³|m3|md|m|cây|cay|cái|cai|con|kg|ha|ha/vụ|bụi|bui|bộ|bo|hộ|ho|người|nguoi|nhân khẩu|'
                        r'khẩu|khau|tháng|thang|đồng|dong|ngôi|mộ|cụm|gốc|lần|chiếc|trụ|hố|giếng|hệ thống|công trình|%)$', re.I)
_RE_SO_O = re.compile(r'^-?[\d.,]+%?$|^-$')
_RE_KET_THUC_BANG = re.compile(r'tong cong|bang chu|lap bieu|nguoi lap|kiem tra|giam doc|phuong an tai dinh cu', re.I)
# tiêu đề mục (dòng STT số nguyên): số in -> mục nội bộ (bản in: 4 vật nuôi, 5 hỗ trợ, 6 thưởng)
# thứ tự quan trọng: "Bồi thường, hỗ trợ về nhà…" có chữ "hỗ trợ"; "bồi thường" có chữ "thường"
_MUC_THEO_TEN = (('ban giao mat bang', 'thuong'), ('thuong chap hanh', 'thuong'), ('vat nuoi', 'vn'), ('cay', 'cay'),
                 ('ve nha', 'nha'), ('cong trinh', 'nha'), ('vat kien truc', 'nha'), ('tai san', 'nha'), ('ho tro', 'ho_tro'),
                 ('dat', 'dat'))
_RE_CACH_TINH = re.compile(r'\s\d[\d.,]*\s*(?:nhân khẩu|khẩu|người|tháng|m²|m2|ha|lần)\b.*\sx\s', re.I)


def _dong_logic(chu: str) -> list:
    """Dòng của bảng III (từ tiêu đề cột "STT" tới "TỔNG CỘNG"), nối các dòng bị ngắt vào dòng có STT."""
    dong = [x.rstrip() for x in unicodedata.normalize('NFC', chu).split('\n')]
    kq, trong = [], False
    for x in dong:
        kd = _bo_dau(x)
        if not trong:
            if re.match(r'^\s*stt\b', kd) and ('ten' in kd or 'tai san' in kd or 'dvt' in kd):
                trong = True
            continue
        if _RE_KET_THUC_BANG.search(kd) and not _RE_STT.match(x):
            break
        if not x.strip() or re.match(r'^\s*(\(%\)|\(dong\)|thanh tien|ghi chu|don gia|so luong|ty le)\s*', kd) and not kq:
            continue
        noi_m2 = kq and re.search(r'\bm$', kq[-1]) and re.match(r'^\s*[23]\b', x)     # "m" + "2" của m² bị ngắt dòng
        if (_RE_STT.match(x) and not noi_m2) or not kq:
            kq.append(x.strip())
        elif noi_m2:
            kq[-1] += x.strip()[0] + ' ' + x.strip()[1:].strip()
        else:
            kq[-1] += ('\t' if '\t' in x else ' ') + x.strip()
    return kq


def _o_dong(dong: str) -> tuple:
    """(stt, tên, ĐVT, [các ô số]) của một dòng logic. Có Tab: theo ô; không Tab: tên = chữ trước ĐVT, sau ĐVT là các số."""
    m = _RE_STT.match(dong)
    stt = m.group(1) if m else ''
    con = dong[m.end():] if m else dong
    if '\t' in con:
        o = [x.strip() for x in con.split('\t') if x.strip()]
    else:
        o = con.split()
    # gộp "m 2" (chỉ số trên của m² tách ra khi lấy chữ PDF)
    gon = []
    for x in o:
        if gon and re.fullmatch(r'[23]', x) and gon[-1].lower() == 'm':
            gon[-1] = 'm²' if x == '2' else 'm³'
        else:
            gon.append(x)
    o = gon
    i_dvt = next((i for i, x in enumerate(o) if i > 0 and _RE_DVT_PA.match(x.strip())), None)
    if '\t' in con and i_dvt is None:                   # ô tên chứa luôn ĐVT ở cuối ("Nhà tạm m2")
        ten = o[0] if o else ''
        so = [x for x in o[1:] if _RE_SO_O.match(x)]
        return stt, ten, '', so
    if i_dvt is None:
        ten = ' '.join(x for x in o if not _RE_SO_O.match(x))
        return stt, ten, '', [x for x in o if _RE_SO_O.match(x)]
    ten = ' '.join(o[:i_dvt])
    so = []
    for x in o[i_dvt + 1:]:
        if _RE_SO_O.match(x):
            so.append(x)
        elif so:                                         # tới ô Ghi chú (chữ): thôi
            break
    return stt, ten, o[i_dvt].replace('m2', 'm²'), so


def _muc_tieu_de(stt: str, ten: str):
    if not re.fullmatch(r'\d{1,2}', stt or ''):
        return None
    k = _bo_dau(ten)
    for tu, muc in _MUC_THEO_TEN:
        if tu in k:
            return muc
    return None


def _bang_pa(chu: str) -> tuple:
    """(thửa mục 1, dòng tài sản mục 2-5 "Tên\\tĐVT\\tSố lượng[\\tTỷ lệ %]", nhân khẩu từ dòng ĐVT khẩu) của bảng III."""
    from .tien import doc_so_vn
    thua, ts, nk = [], [], None
    muc = None
    for d in _dong_logic(chu):
        stt, ten, dvt, so = _o_dong(d)
        m = _muc_tieu_de(stt, ten)
        if m:
            muc = m
            continue
        if not stt or stt == '-' or not ten.strip():
            continue
        if muc == 'dat' or re.search(r'thua (dat )?so', _bo_dau(ten)):
            kd = _bo_dau_giu_do_dai(ten)
            a = re.search(r'thua (?:dat )?so\s*:?\s*([0-9A-Za-z-]+)', kd)
            b = re.search(r'to (?:ban do )?so\s*:?\s*([0-9A-Za-z-]+)', kd)
            so_thua = (a.group(1) if a else '').strip('-')
            so_to = (b.group(1) if b else '').strip('-')
            ld = re.search(r'loai dat\s*:?\s*([A-Za-z+]{2,})', kd)
            loai = ma_loai_dat(ten[ld.start(1):ld.end(1)].upper()) if ld else ma_loai_dat(ten)
            dt = gia = None
            try:
                dt = doc_so_vn(so[0]) if so and so[0] != '-' else None
                gia = doc_so_vn(so[1]) if len(so) > 1 and so[1] != '-' else None
            except Exception:                            # noqa: BLE001 - số lạ: để trống cho người dùng sửa
                pass
            if so_thua or so_to:
                thua.append(dict(so_to=so_to, so_thua=so_thua, dt_thu_hoi=dt, loai_dat=loai, dia_chi_thua='', don_gia=gia))
            continue
        if muc == 'thuong':                              # thưởng bàn giao mặt bằng: phần mềm tự tính theo biểu thưởng
            continue
        ct = _RE_CACH_TINH.search(' ' + d.replace('\t', ' '))
        if muc == 'ho_tro' and ct:
            # chính sách hỗ trợ in kèm câu cách tính ("5 nhân khẩu x 30kg gạo x 6 tháng…"): chỉ lấy tên - số lượng, đơn giá do
            # phần mềm tự tính theo hồ sơ hộ (nhân khẩu, diện tích); nhân khẩu lấy từ câu cách tính
            ten_cs = re.split(r'\s\d', ' ' + re.sub(r'^\s*\S+\s+', '', d.replace('\t', ' ')), maxsplit=1)[0].strip()
            ts.append(ten_cs)
            m = re.search(r'(\d{1,3})\s*(?:nhân khẩu|khẩu)', d)
            if m and nk is None:
                nk = int(m.group(1))
            continue
        if not so or so[0] == '-':
            continue
        tl = ''
        if len(so) >= 4:                                 # Số lượng, Đơn giá, Tỷ lệ, Thành tiền: tỷ lệ là ô thứ 3
            v = _so(so[2].rstrip('%'))
            if v is not None and 0 < v <= 500:
                v = v * 100 if not so[2].endswith('%') and v <= 5 else v       # ô Excel định dạng %: 1 = 100%
                if v != 100:
                    tl = f'{v.normalize():f}%'.replace('.', ',')
        dong = '\t'.join(x for x in (ten.strip(), dvt, so[0], tl) if x)
        ts.append(dong)
        if re.search(r'khau', _bo_dau(dvt)) and nk is None:
            try:
                nk = int(doc_so_vn(so[0]))
            except Exception:                            # noqa: BLE001
                pass
    return thua, ts, nk


def _doan_sau_tieu_de(chu: str, mau: str, het: str) -> str:
    """Đoạn chữ sau tiêu đề (không dấu, regex) tới tiêu đề kế tiếp - nối các dòng thành đoạn, giữ gạch đầu dòng."""
    c = unicodedata.normalize('NFC', chu)
    vt = _vi_tri(c, mau)
    if not vt:
        return ''
    m = re.compile(het, re.I | re.M).search(_bo_dau_giu_do_dai(c), vt[1])
    doan = c[vt[1]:m.start() if m else len(c)].lstrip(' :.\t\n').rstrip()       # giữ dấu chấm cuối đoạn
    dong = [' '.join(x.replace('\t', ' ').split()) for x in doan.split('\n')]
    kq = []
    for x in dong:
        if not x:
            continue
        if kq and not re.match(r'^([-–+•*]|\d+[.)]|[a-z]\))\s', x):
            kq[-1] += ' ' + x
        else:
            kq.append(x)
    return '\n'.join(kq)[:6000]


def boc_tach(chu: str) -> KetQuaOcr:
    """Thông tin chủ sử dụng, thửa đất, tài sản từ chữ của giấy tờ (đã OCR hoặc lớp chữ PDF)."""
    c = unicodedata.normalize('NFC', chu or '')
    k = _bo_dau(c)
    kq = KetQuaOcr()
    if re.search(r'phuong an chi tiet|bang tinh toan boi thuong', k):
        kq.loai = 'pa_chi_tiet'
    elif 'giay chung nhan' in k and ('quyen su dung dat' in k or 'quyen so huu' in k):
        kq.loai = 'gcn'
    elif re.search(r'bien ban (kiem ke|kiem dem|dieu tra|xac minh)', k):
        kq.loai = 'bien_ban'
    ten = _sau_nhan(c, _NHAN_HO_TEN, r'[\n\t;,]|\bnăm sinh|\bsinh năm|\bCCCD|\bCMND')
    kq.ho_ten = _chuan_ho_ten(ten)[:80] if ten and len(ten) < 120 and not re.match(r'(?i)(số|địa chỉ|cccd)', ten) else ''
    kq.so_cccd = _so_cccd(c)
    kq.dia_chi = _sau_nhan(c, r'(dia chi thuong tru|noi thuong tru|thuong tru tai|dia chi)\s*:?', r'[\n\t;]')[:200]
    if re.match(r'(?i)(số điện thoại|ii\.)', kq.dia_chi):
        kq.dia_chi = ''
    m = re.search(r'(?:so nhan khau|nhan khau)\s*:?\s*(\d{1,3})\b|\b(\d{1,3})\s*nhan khau', k)
    if m:
        kq.nhan_khau = int(m.group(1) or m.group(2))
    kq.nguon_goc = _doan_sau_tieu_de(c, r'(ii\.?\s*thong tin (?:vi tri, )?nguon goc (?:su dung )?dat|nguon goc su dung dat)\s*:?',
                                     r'^\s*(iii\.?|stt\b)')
    kq.tai_dinh_cu = _sau_nhan(c, r'(?:phuong an )?tai dinh cu\s*:', r'\n')[:300]     # bản in: "Tái định cư: …" (có dấu ":")
    if kq.loai == 'pa_chi_tiet':
        thua, ts, nk = _bang_pa(c)
        kq.thua = thua or _thua(c)
        kq.dong_tai_san = ts
        if kq.nhan_khau is None:
            kq.nhan_khau = nk
    else:
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
        for k in ('ho_ten', 'so_cccd', 'dia_chi', 'nhan_khau', 'nguon_goc', 'tai_dinh_cu'):
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


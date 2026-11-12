"""Nhập danh sách hộ / thửa từ MỘT FILE BẤT KỲ (không theo mẫu PABT) vào file dự án .pabt.

Đọc được: Excel (.xlsx, .xlsm, .xls), CSV, Word, PDF có chữ (văn bản ký hoặc chưa ký), PDF ảnh scan và file ảnh (nhận dạng chữ) - xem
`nguon_luoi`. Mọi nguồn đều thành lưới ô rồi đi chung một đường: tự tìm sheet và dòng tiêu đề (kể cả tiêu đề 2-4 dòng có ô gộp), tự
nhận cột theo tên (họ tên, địa chỉ, tờ, thửa, diện tích thu hồi, loại đất, CCCD, điện thoại, ghi chú...); cột không có tiêu đề nhận ra
thì đoán theo NỘI DUNG (số CCCD, số điện thoại, ký hiệu loại đất, họ tên, địa chỉ); cột phần mềm có mà file không có thì bỏ qua. Bỏ dòng
trống / dòng cộng / dòng đánh số cột, gom các dòng cùng người (CCCD, hoặc họ tên + địa chỉ) thành một hộ, mỗi dòng có tờ / thửa là một
thửa. Không nhận ra cột: người dùng ghép cột bằng tay (`doc(..., bo_cot=BoCot(...))`).

Ghi vào file .pabt: XÓA TRẮNG hồ sơ cũ (hộ, thửa, phương án, tổng Excel, thông tin dự án, nhật ký) nhưng
GIỮ danh mục đơn giá, tham số, biểu thưởng của file; tất cả trong một giao dịch.
"""
from __future__ import annotations
import re
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import openpyxl

from . import csdl, nhap_excel
from .loi import LoiNhap
from .nguon_luoi import DONG_TIM_COT, TRONG_LIEN_TIEP, Nguon, _co_chu, chuan_luoi, lay_nguon  # noqa: F401 (TRONG_LIEN_TIEP: tên cũ)
from .nhap_excel import BaoCaoNhap, _txt, chuan_cccd, chuan_hoa
from .tien import D, chuoi, doc_so_vn, la_cong_thuc, tinh_cong_thuc

# trường -> [(mẫu regex trên tiêu đề đã chuẩn hóa, điểm)]; mẫu loại trừ đặt trong LOAI_TRU
MAU_COT = {
    'stt': [(r'^(stt|tt|so tt|so thu tu|thu tu)$', 10)],
    'ho_ten': [(r'\bho (va )?ten\b', 10), (r'\bten (chu|nguoi|ho)\b', 9), (r'\bchu (su dung|so huu|ho|dat)\b', 9),
               (r'\bnguoi (su dung|bi thu hoi|co dat|bi anh huong)\b', 8), (r'^ten$', 6), (r'\bho so kiem (dem|ke)\b', 5),
               (r'\bten (to chuc|ca nhan)\b', 8), (r'\bto chuc\b.*\bca nhan\b', 7), (r'^(doi tuong|chu)$', 5)],
    'dia_chi': [(r'\bdia chi\b', 10), (r'\bnoi (cu tru|o|thuong tru)\b', 9), (r'\bthuong tru\b', 8), (r'\bcho o\b', 6)],
    'so_cccd': [(r'\b(cccd|cmnd|cmt)\b', 10), (r'\bcan cuoc\b', 10), (r'\bdinh danh\b', 9), (r'\bchung minh\b', 9),
                (r'\bso giay to\b', 6)],
    'ngay_cap': [(r'\bngay cap\b', 10)],
    'noi_cap': [(r'\bnoi cap\b', 10)],
    'dien_thoai': [(r'\bdien thoai\b', 10), (r'\b(sdt|so dt|dt lien he)\b', 9), (r'^dt$', 6)],
    'so_to': [(r'\bto (ban do|bd|so)\b', 10), (r'\bso (hieu )?to\b', 10), (r'^to$', 9), (r'\bto\b', 5)],
    'so_thua': [(r'\bthua (dat )?so\b', 10), (r'\bso (hieu )?thua\b', 10), (r'^thua( dat)?$', 9), (r'\bthua\b', 5)],
    'to_thua': [(r'\bto\s*(ban do\s*)?[/,&-]\s*(so\s*)?thua\b', 12), (r'\bto\s*(ban do\s*)?va\s*(so\s*)?thua\b', 12),
                (r'\bthua\s*[/,&-]\s*to\b', 11)],
    'dt_thu_hoi': [(r'\b(dien tich|dt)\b.*\bthu hoi\b', 10), (r'\bthu hoi\b.*\b(dien tich|dt|m2)\b', 9),
                   (r'\b(dien tich|dt)\b.*\b(trong|thuoc) (du an|ranh|pham vi)\b', 10),
                   (r'\b(dien tich|dt)\b.*\b(anh huong|boi thuong|giai toa)\b', 9),
                   (r'^(dien tich|dt)( \(?m2\)?)?$', 6), (r'\bdien tich\b', 4)],
    'dt_ban_do': [(r'\b(dien tich|dt)\b.*\bban do\b', 11)],
    'loai_dat': [(r'\bloai dat\b', 10), (r'\bmuc dich( su dung)?\b', 9), (r'\bmdsd\b', 9), (r'\bky hieu\b', 6)],
    'nguon_goc': [(r'\bnguon goc\b', 10)],
    'vi_tri': [(r'\bvi tri\b', 10)],
    'ghi_chu': [(r'\bghi chu\b', 10)],
    'nhan_khau': [(r'\b(so )?nhan khau\b', 10), (r'\bso (khau|nguoi)\b', 8)],
}
LOAI_TRU = {
    'ho_ten': r'\bdia chi\b|\bdat\b.*\bloai\b',
    'so_to': r'\btong\b|\bdan pho\b|\bdia chi\b|\bho ten\b',
    'so_thua': r'\bdien tich\b|\bdt\b|\bloai\b|\bthu hoi\b',
    'dt_thu_hoi': r'\bban do\b|\bcon lai\b|\bngoai\b|\bthua dat\b.*\btong\b|\btong\b.*\bthua( dat)?\b|\bdien tich thua\b',
    'dia_chi': r'\bthua\b|\bdat\b',
}
BAT_BUOC = ('ho_ten',)
CAN_MOT = ('so_to', 'so_thua', 'dt_thu_hoi')        # phải có ít nhất một trong số này
NHOM_THUA = CAN_MOT + ('to_thua',)
# "Tổng cộng", "Cộng: 25 hộ"... nhưng không bắt họ Tống ("tong van a")
DONG_CONG = re.compile(r'^(tong cong|cong tong|tong so|tong|cong)\s*[:.]?\s*(\d.*|\(.*|(so )?(ho|thua|dien tich|dt)\b.*)?$')
# chữ cuối văn bản (chữ ký, nơi nhận...): không nối vào dòng dữ liệu phía trên khi gộp dòng gãy của PDF / bản scan
_RE_CUOI_VB = re.compile(r'^(nguoi lap|nguoi kiem|tm\.|kt\.|giam doc|pho giam doc|truong phong|ngay \d|noi nhan|ghi chu\s*:|tong cong|'
                         r'cong\s*:|ket luan|\(?kem theo)')

# tiêu đề nhận dạng sai chữ (bản scan): so gần đúng với các cụm chuẩn
_CUM_CHUAN = {
    'ho_ten': ('ho va ten', 'ho ten', 'ten chu su dung', 'chu su dung dat', 'ten chu ho'),
    'dia_chi': ('dia chi', 'dia chi thuong tru'), 'so_cccd': ('so cccd', 'cccd cmnd', 'cmnd cccd', 'so cmnd'),
    'dien_thoai': ('dien thoai', 'so dien thoai'), 'so_to': ('so to', 'to ban do', 'to ban do so'),
    'so_thua': ('so thua', 'thua dat so', 'thua dat'), 'loai_dat': ('loai dat', 'muc dich su dung', 'loai dat thu hoi'),
    'dt_thu_hoi': ('dien tich thu hoi', 'dien tich', 'dt thu hoi'), 'nguon_goc': ('nguon goc', 'nguon goc dat'),
    'ghi_chu': ('ghi chu',), 'vi_tri': ('vi tri',), 'nhan_khau': ('nhan khau', 'so nhan khau'), 'stt': ('stt',),
}
DIEM_GAN_DUNG = 7
NGUONG_GAN_DUNG = 0.84


@dataclass
class BoCot:
    sheet: str
    dong_tieu_de: list                 # số dòng (1-based) của khối tiêu đề; [0] = file không có dòng tiêu đề
    cot: dict                          # trường -> chỉ số cột (0-based)
    tieu_de: dict = field(default_factory=dict)   # trường -> tên cột gốc
    diem: int = 0
    td: list = field(default_factory=list)         # tiêu đề đã chuẩn hóa của từng cột
    suy: set = field(default_factory=set)          # trường đoán theo nội dung (không nhận ra tiêu đề)
    thu_cong: bool = False                         # người dùng tự ghép cột


# tên trường viết liền của bảng thuộc tính bản đồ / file xuất từ phần mềm địa chính (gCadas, ArcGIS, MapInfo, Famis, TMV.Map...: SOTO,
# SHTHUA, DIENTICH, MDSD, TENCHU, Ten_Chu...) -> cụm chuẩn để MAU_COT nhận (1.0.98). Khóa: tiêu đề đã chuẩn hóa, bỏ dấu cách / _ / . / -
_TEN_GON = {
    **dict.fromkeys(('soto', 'shto', 'sohieuto', 'tobando', 'shbando', 'sobando', 'tobd', 'sotobd', 'sotobando', 'toso'), 'so to'),
    **dict.fromkeys(('sothua', 'shthua', 'sohieuthua', 'thuaso', 'thuadat', 'sothuadat', 'thuadatso'), 'so thua'),
    **dict.fromkeys(('dientich', 'dtich', 'dtichthua'), 'dien tich'),
    **dict.fromkeys(('dtthuhoi', 'dientichthuhoi', 'dtth', 'dtichthuhoi', 'dtthuhoim2'), 'dien tich thu hoi'),
    **dict.fromkeys(('dtbando', 'dientichbando', 'dtbd'), 'dien tich ban do'),
    **dict.fromkeys(('loaidat', 'mdsd', 'khmdsd', 'kyhieumdsd', 'mucdich', 'mucdichsd', 'mucdichsudung', 'khloaidat', 'maloaidat',
                     'loaidatsd', 'kyhieuloaidat'), 'loai dat'),
    **dict.fromkeys(('tenchu', 'chusudung', 'chusd', 'tenchusd', 'hoten', 'hotenchu', 'tenchusudung', 'tenchuho', 'chuhoso',
                     'hotenchusd', 'tennguoisd', 'tenchu1'), 'ho ten'),
    **dict.fromkeys(('diachi', 'diachichu', 'dcchu', 'diachithuongtru', 'diachichusd'), 'dia chi'),
    **dict.fromkeys(('socmnd', 'cmnd', 'cccd', 'socccd', 'cmndcccd', 'sogiayto', 'sogt', 'sodinhdanh'), 'so cccd'),
    **dict.fromkeys(('dienthoai', 'sdt', 'sodienthoai'), 'dien thoai'),
    **dict.fromkeys(('nguongoc', 'nguongocsd', 'nguongocsudung'), 'nguon goc'),
    'ghichu': 'ghi chu', 'vitri': 'vi tri', 'nhankhau': 'nhan khau', 'sonhankhau': 'so nhan khau',
}


def _diem_cot(text: str, gan_dung: bool = False):
    """Tiêu đề một cột -> {trường: điểm}. gan_dung: bản scan nhận dạng sai chữ - so gần đúng khi không khớp mẫu."""
    kq = {}
    if not text:
        return kq
    text = _TEN_GON.get(re.sub(r'[\s_.\-]+', '', text), text)
    for truong, mau in MAU_COT.items():
        if truong in LOAI_TRU and re.search(LOAI_TRU[truong], text) and truong != 'dt_ban_do':
            continue
        d = max((dm for m, dm in mau if re.search(m, text)), default=0)
        if d:
            kq[truong] = d
    if gan_dung and not kq:
        tu = text.split()
        for truong, cum in _CUM_CHUAN.items():
            for c in cum:
                n = len(c.split())
                if len(c) < 3 or len(tu) < max(1, n - 1):
                    continue
                for i in range(0, max(1, len(tu) - n + 2)):
                    if SequenceMatcher(None, ' '.join(tu[i:i + n]), c).ratio() >= NGUONG_GAN_DUNG:
                        kq[truong] = DIEM_GAN_DUNG
                        break
                if truong in kq:
                    break
    return kq


def _gan_cot(tieu_de: list, gan_dung: bool = False, bo_cot: set = frozenset()):
    """Gán mỗi trường một cột (điểm cao trước, mỗi cột một trường); bo_cot: các cột không xét (cột trống)."""
    ung = sorted(((d, -j, truong, j) for j, t in enumerate(tieu_de) if j not in bo_cot
                  for truong, d in _diem_cot(t, gan_dung).items()), reverse=True)
    cot, da_dung = {}, set()
    for d, _, truong, j in ung:
        if truong not in cot and j not in da_dung:
            cot[truong] = j
            da_dung.add(j)
    return cot


def _tieu_de_khoi(luoi, gop, rong, dau: int, so_dong: int):
    """Ghép tiêu đề cột của khối dòng dau..dau+so_dong-1 (bỏ ô gộp rộng như tên bảng)."""
    td = []
    for j in range(rong):
        phan = []
        for i in range(dau, dau + so_dong):
            if gop.get((i, j + 1), 1) > max(3, rong * 0.6):
                continue
            t = chuan_hoa(luoi[i - 1][j]) if luoi[i - 1][j] is not None else ''
            if t and t not in phan:
                phan.append(t)
        td.append(' '.join(phan))
    return td


def _dat_yeu_cau(cot: dict) -> bool:
    """Khối tiêu đề đủ để coi là bảng danh sách: ít nhất 2 cột nhận ra, trong đó có họ tên hoặc tờ / thửa / diện tích."""
    return len(cot) >= 2 and ('ho_ten' in cot or any(k in cot for k in NHOM_THUA))


def _diem_khoi(td: list, cot: dict, so_dong: int, gan_dung: bool) -> int:
    diem = sum(_diem_cot(td[j], gan_dung)[k] for k, j in cot.items()) - so_dong        # ưu tiên khối ngắn khi bằng điểm
    if 'ho_ten' in cot and any(k in cot for k in NHOM_THUA):
        diem += 6                                                                       # bảng đủ họ tên + thửa hơn bảng chỉ có một phần
    return diem


def _do_day_cot(luoi: list, dau0: int, j: int, toi_da: int = 200) -> float:
    """Tỷ lệ ô có chữ của cột j trong các dòng dữ liệu (dau0 = chỉ số dòng 0-based đầu tiên dưới tiêu đề)."""
    mau = luoi[dau0:dau0 + toi_da]
    if not mau:
        return 1.0
    return sum(1 for r in mau if j < len(r) and _co_chu(r[j]) and not _TRONG.match(str(r[j]).strip())) / len(mau)


def ung_vien(n: Nguon, so_dong_quet: int = 30, toi_da: int = 4) -> list:
    """Các khối tiêu đề có thể là tiêu đề bảng của nguồn n, điểm cao trước (tối đa toi_da). Khối trống dữ liệu (cột họ tên toàn trống
    mà có cột khác cùng tên đọc được) được chuyển sang cột còn dữ liệu."""
    luoi, gop, rong = n.luoi, n.gop, n.rong
    gan_dung = n.co_chu_in
    quet = so_dong_quet if not n.co_chu_in and n.loai != 'word' else max(so_dong_quet, 80)
    ds = []
    for dau in range(1, min(quet, len(luoi)) + 1):
        if max(sum(1 for v in r if isinstance(v, str) and v.strip()) for r in luoi[dau - 1:dau + 3]) < 2:
            continue                                                     # vùng ít chữ: không phải dòng tiêu đề cột
        for so_dong in (1, 2, 3, 4):
            if dau + so_dong - 1 > len(luoi):
                break
            td = _tieu_de_khoi(luoi, gop, rong, dau, so_dong)
            cot = _gan_cot(td, gan_dung)
            if not _dat_yeu_cau(cot):
                continue
            ds.append(BoCot(n.ten, list(range(dau, dau + so_dong)), cot, {}, _diem_khoi(td, cot, so_dong, gan_dung), td))
    ds.sort(key=lambda b: -b.diem)
    kq = []
    for b in ds[:toi_da * 3]:
        b = _chinh_theo_du_lieu(n, b)
        if b is not None and not any(x.dong_tieu_de == b.dong_tieu_de for x in kq):
            kq.append(b)
        if len(kq) >= toi_da:
            break
    return kq


def _chinh_theo_du_lieu(n: Nguon, b: BoCot):
    """Bỏ cột nhận ra theo tiêu đề nhưng KHÔNG có dữ liệu; thử cột khác cùng tên có dữ liệu. Trả BoCot (hoặc None khi hết đủ yêu cầu)."""
    dau0 = b.dong_tieu_de[-1]                               # chỉ số 0-based của dòng dữ liệu đầu
    trong = {j for j in b.cot.values() if _do_day_cot(n.luoi, dau0, j) < 0.03}
    if trong:
        cot = _gan_cot(b.td, n.co_chu_in, trong)
        if not _dat_yeu_cau(cot):
            return None
        b.cot = cot
        b.diem = _diem_khoi(b.td, cot, len(b.dong_tieu_de), n.co_chu_in)
    b.tieu_de = {k: ' '.join(' '.join(str(n.luoi[i - 1][j] or '') for i in b.dong_tieu_de).split()) for k, j in b.cot.items()}
    return b


# ---------------------------------------------------------------- đoán cột theo nội dung
def _mau_cot(luoi: list, dau0: int, j: int, toi_da: int = 300) -> list:
    kq = []
    for r in luoi[dau0:dau0 + toi_da]:
        if j < len(r) and _co_chu(r[j]):
            s = _txt(r[j])
            if s and not _TRONG.match(s):
                kq.append(s)
    return kq


def _la_cccd(s: str) -> bool:
    return bool(re.fullmatch(r'0\d{11}|\d{9}|\d{12}|\d{11}', re.sub(r'[\s.\-]', '', s)))


def _la_sdt(s: str) -> bool:
    return bool(re.fullmatch(r'(\+84|0)\d{9,10}', re.sub(r'[\s.\-()]', '', s)))


def _la_loai_dat(s: str) -> bool:
    from .loai_dat import LOAI_DAT
    ma = {m for m, _, _ in LOAI_DAT}
    ds = [x for x in re.split(r'[+,;/\s]+', s.strip().upper()) if x]
    return bool(ds) and len(ds) <= 4 and all(x in ma for x in ds)


def _la_ten_nguoi(s: str) -> bool:
    s = s.strip()
    tu = s.split()
    if not 4 <= len(s) <= 70 or not 2 <= len(tu) <= 9 or re.search(r'\d', s):
        return False
    chu = sum(1 for ch in s if ch.isalpha() or ch in " .-()'")
    hoa = sum(1 for w in tu if w[:1].isupper())
    return chu >= 0.95 * len(s) and hoa >= 0.7 * len(tu)


_RE_DIA_CHI = re.compile(r'\b(ấp|khu phố|kp|xã|phường|thị trấn|tổ|thôn|đường|huyện|quận|tp|thành phố|khóm|khu vực)\b', re.I)


def _la_dia_chi(s: str) -> bool:
    return len(s) >= 8 and (',' in s or bool(_RE_DIA_CHI.search(s)))


def _la_so_nguyen(s: str) -> bool:
    return bool(re.fullmatch(r'\d{1,5}', s.strip()))


def _la_so_thuc(s: str) -> bool:
    try:
        v = doc_so_vn(re.sub(r'(m2|m²)\s*$', '', s.strip(), flags=re.I))
    except ValueError:
        return False
    return 0 < v < 10 ** 8


def suy_cot(luoi: list, dau0: int, rong: int, cot: dict, tat_ca_so: bool = False, td: list = ()) -> dict:
    """Các cột CHƯA gán trường -> {trường: cột} đoán theo nội dung (đủ chắc: >= 70% ô khớp dạng). tat_ca_so: đoán cả cột số (tờ, thửa,
    diện tích) - chỉ dùng khi file không có dòng tiêu đề."""
    dung = set(cot.values())
    ung = [j for j in range(rong) if j not in dung]
    mau = {j: _mau_cot(luoi, dau0, j) for j in ung}
    kq = {}

    def chon(truong, kiem, nguong, toi_thieu=3, cot_tran=None):
        if truong in cot or truong in kq:
            return
        tot = None
        for j in ung:
            v = mau[j]
            if j in kq.values() or len(v) < toi_thieu or (cot_tran is not None and not cot_tran(j)):
                continue
            t = sum(1 for x in v if kiem(x)) / len(v)
            if t >= nguong and (tot is None or t > tot[0] + 0.05):
                tot = (t, j)
        if tot:
            kq[truong] = tot[1]
    chon('so_cccd', _la_cccd, 0.7)
    chon('dien_thoai', _la_sdt, 0.7)
    chon('loai_dat', _la_loai_dat, 0.6)
    chon('ho_ten', _la_ten_nguoi, 0.7)
    chon('dia_chi', lambda s: _la_dia_chi(s), 0.5, cot_tran=lambda j: not (j < len(td) and td[j]))
    if tat_ca_so:
        so_nguyen = []
        for j in ung:
            v = mau[j]
            if j in kq.values() or len(v) < 3 or sum(1 for x in v if _la_so_nguyen(x)) < 0.85 * len(v):
                continue
            gt = [int(x) for x in v if _la_so_nguyen(x)]
            if len(set(gt)) == len(gt) and gt == sorted(gt) and gt[0] <= 2:
                continue                                                # cột số thứ tự
            so_nguyen.append((j, len(set(gt))))
        if len(so_nguyen) >= 2 and not any(k in cot for k in ('so_to', 'so_thua', 'to_thua')):
            (j1, u1), (j2, u2) = so_nguyen[0], so_nguyen[1]
            kq['so_to'], kq['so_thua'] = (j1, j2) if u1 <= u2 else (j2, j1)
    if 'dt_thu_hoi' not in cot and (tat_ca_so or any(k in cot or k in kq for k in ('so_to', 'so_thua', 'to_thua'))):
        for j in ung:                                                   # cột diện tích: số có phần lẻ, bên phải cột tờ / thửa
            v = mau[j]
            if j in kq.values() or len(v) < 3 or sum(1 for x in v if _la_so_thuc(x)) < 0.8 * len(v):
                continue
            if any(re.search(r'[.,]\d', x) for x in v) and j > min([c for k, c in {**cot, **kq}.items() if k in ('so_to', 'so_thua', 'to_thua')] or [-1]):
                kq['dt_thu_hoi'] = j
                break
    return kq


@dataclass
class KetQuaDoc:
    bo_cot: BoCot | None
    ho: list = field(default_factory=list)
    thua: list = field(default_factory=list)
    loi: list = field(default_factory=list)
    canh_bao: list = field(default_factory=list)
    tieu_de_bang: str = ''
    nguons: list = field(default_factory=list)      # các nguồn (sheet / bảng) của file - để ghép cột bằng tay
    thong_bao: list = field(default_factory=list)   # lưu ý khi đọc (bản scan, công thức chưa tính, bảng khác trong file...)
    loai: str = 'excel'                             # excel | word | csv | pdf | scan
    da_bo: dict = field(default_factory=dict)       # lý do bỏ dòng -> số dòng (chẩn đoán khi không ra hộ nào)


def _la_dong_danh_so(r) -> bool:
    """Dòng đánh số cột (1), (2), (3)... hoặc 1, 2, 3... ngay dưới tiêu đề."""
    so = []
    for v in r:
        if v in (None, ''):
            continue
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        m = re.fullmatch(r'\(?(\d{1,2})\)?', str(v).strip())
        if not m:
            return False
        so.append(int(m.group(1)))
    # 1, 2, … tăng dần, cho phép thiếu vài số (cột ẩn / cột công thức "11 = 8 + 9" bỏ trống)
    return len(so) >= 3 and so == sorted(set(so)) and so[-1] - so[0] <= 2 * len(so)


_TRONG = re.compile(r'^(nan|none|null|-+|–+|—+|\.+|…|x+)$', re.I)


def _khong_gia_tri(s: str) -> str:
    """Ô 'NaN' / '--' / '-' (file xuất từ phần mềm khác, dòng tiếp của cùng hộ) = trống."""
    return '' if _TRONG.match(s.strip()) else s


def _ma_so(v) -> str:
    """Số tờ / số thửa: 35 -> '35'; '382\\n(164 cũ)' -> '382 (164 cũ)'; '--' -> ''."""
    return _khong_gia_tri(' '.join(_txt(v).split()))


def _doc_dt(v):
    """Diện tích: số, '1.070,5', '215,1 m2' -> Decimal; rỗng -> None; không đọc được -> ValueError."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, (int, float)):
        return D(v)
    s = re.sub(r'(m2|m²|ha)\s*$', '', str(v).strip(), flags=re.I).strip()
    if la_cong_thuc(s):                             # 1.0.98: ô ghi phép tính ("=12*3,5", "120+35,5") - như ô số lượng phương án
        from .lap_pa import lam_tron_cong_thuc
        return lam_tron_cong_thuc(tinh_cong_thuc(s), 'm2')
    return doc_so_vn(s)                             # '1.070' = 1.070 m² (trước đây đọc thành 1,07)


_RE_TO_THUA = re.compile(r'^\D*?(\d+[a-z]?)\s*(?:[/,;&-]|\s)\s*(?:th[ửu]a(?:\s+đất)?(?:\s+s[ốo])?\s*[:.]?\s*)?(\d.*)$', re.I)


def _tach_to_thua(v) -> tuple:
    """Ô "Tờ / Thửa": '35/394', '35 - 394', 'Tờ 35, thửa 394' -> ('35', '394'); không tách được -> ('', cả chữ)."""
    s = ' '.join(_txt(v).split())
    if not s:
        return '', ''
    m = _RE_TO_THUA.match(s)
    return (m.group(1), m.group(2).strip()) if m else ('', _khong_gia_tri(s))


def _noi_dong(dong: list, rong: int) -> list:
    """Các dòng chữ (một ô xuống nhiều dòng của PDF / bản scan) -> một dòng: chữ từng cột nối theo thứ tự trên xuống."""
    kq = [None] * rong
    for r in dong:
        for j, v in enumerate(r[:rong]):
            if _co_chu(v):
                kq[j] = (str(kq[j]).strip() + ' ' + str(v).strip()) if _co_chu(kq[j]) else v
    return kq


def _giong_tieu_de(r, td: list) -> bool:
    """Dòng lặp lại tiêu đề cột (bảng in nhiều trang; tiêu đề xuống nhiều dòng): mọi ô có chữ trùng / nằm trong chữ tiêu đề cột đó
    (>= 2 ô, hoặc 1 ô dài từ 4 ký tự)."""
    dem = 0
    for j, v in enumerate(r):
        if not _co_chu(v):
            continue
        t = chuan_hoa(v)
        if not isinstance(v, str) or j >= len(td) or not td[j] or len(t) < 2 or not (t in td[j] or td[j] in t):
            return False
        dem += 1 if len(t) >= 4 or dem else 0.5
    return dem >= 1


def _gom_nhom_stt(khoi: list, rong: int, cot_ho: tuple = ()):
    """Một khối dòng liên tục của bảng PDF / bản scan [(số dòng, dòng, loại)] (loại: 'S' có số thứ tự, 'N' có số tờ / thửa / diện tích, 'T'
    chỉ chữ) -> (số dòng, dòng) theo từng hộ. Số thứ tự là điểm neo của hộ; ô họ tên, địa chỉ… gộp ô theo chiều dọc và căn giữa nên dòng chữ
    nằm giữa các dòng thửa: hộ có chữ nằm phía TRÊN neo bằng số dòng phía dưới neo (chia các dòng giữa hai neo theo số dòng phía trên neo của hộ
    trước); bảng căn trên (chưa thấy dòng nào phía trên neo đầu và neo nào cũng có số liệu): mọi dòng sau neo thuộc hộ đó. Dòng thửa vẫn
    giữ riêng từng dòng; chữ các dòng không có số liệu nối vào dòng thửa đầu tiên của hộ."""
    neo = [k for k, (_, _, tp) in enumerate(khoi) if 'S' in tp]
    if not neo:
        for i, r, _ in khoi:
            yield i, r
        return
    giua = neo[0] > 0 or any('N' not in khoi[k][2] for k in neo)
    bat_dau = [0] * len(neo)
    if not giua:
        for i, r, _ in khoi[:neo[0]]:
            yield i, r
        bat_dau[0] = neo[0]
    for g, a in enumerate(neo):
        co_tiep = g + 1 < len(neo)
        nxt = neo[g + 1] if co_tiep else len(khoi)
        if co_tiep:
            m = nxt - a - 1
            ket = a + 1 + (min(m, a - bat_dau[g]) if giua else m)
            bat_dau[g + 1] = ket
        else:
            ket = len(khoi)
        dong = khoi[bat_dau[g]:ket]
        so = [x for x in dong if 'N' in x[2]]
        if not so:
            yield dong[0][0], _noi_dong([x[1] for x in dong], rong)
            continue
        dau = so[0]
        chu = [x[1] for x in dong if 'N' not in x[2] or x is dau]
        dong_dau = _noi_dong(chu, rong) if len(chu) > 1 else list(dau[1])
        sau = []
        for x in so[1:]:                                     # dòng thửa thứ 2 trở đi: chữ của ô cấp hộ (họ tên, địa chỉ…) là phần nối tiếp
            r = list(x[1])
            for j in cot_ho:
                if j < len(r) and j < len(dong_dau) and _co_chu(r[j]):
                    dong_dau[j] = (str(dong_dau[j]).strip() + ' ' + str(r[j]).strip()) if _co_chu(dong_dau[j]) else r[j]
                    r[j] = None
            sau.append((x[0], r))
        yield dau[0], dong_dau
        yield from sau


def _dong_du_lieu(n: Nguon, bc: BoCot, bo: Counter):
    """(số dòng gốc 1-based, dòng) dưới khối tiêu đề. PDF / bản scan: ô xuống nhiều dòng (họ tên, địa chỉ, nguồn gốc… nằm trên / dưới
    dòng số liệu) được nối về hộ - có cột số thứ tự: theo từng hộ (_gom_nhom_stt); không có: ô căn giữa theo chiều dọc: dòng chữ giữa hai
    dòng số liệu chia cho hai dòng theo số dòng phía trên của dòng trước; ô căn trên: mọi dòng chữ thuộc dòng phía trên."""
    luoi, c = n.luoi, bc.cot
    dau = bc.dong_tieu_de[-1] + 1
    if not n.co_chu_in:
        for i in range(dau, len(luoi) + 1):
            yield i, luoi[i - 1]
        return
    cot_so = [c[k] for k in ('so_to', 'so_thua', 'dt_thu_hoi', 'to_thua') if k in c]
    j_stt = c.get('stt')

    def loai(r):
        if not any(_co_chu(v) for v in r):
            return 'trong'
        if _la_dong_danh_so(r):
            return 'khac'
        if _giong_tieu_de(r, bc.td):
            bo['dòng tiêu đề lặp lại (trang sau)'] += 1
            return 'cat'
        if any(isinstance(v, str) and _RE_CUOI_VB.match(chuan_hoa(v)) for v in r):
            bo['dòng chữ ký / ghi chú cuối bảng'] += 1
            return 'cat'
        co_so = any(j < len(r) and re.search(r'\d', _txt(r[j])) for j in cot_so)
        co_stt = j_stt is not None and j_stt < len(r) and bool(re.fullmatch(r'\(?\d{1,4}\)?\.?', _txt(r[j_stt])))
        return ('S' if co_stt else '') + ('N' if co_so else '') or 'T'
    if j_stt is not None:
        khoi, ra = [], []
        for i in range(dau, len(luoi) + 1):
            r = luoi[i - 1]
            k = loai(r)
            if k == 'trong':
                continue
            if k in ('khac', 'cat'):
                if khoi:
                    ra.append(('khoi', khoi))
                    khoi = []
                if k == 'khac':
                    ra.append(('khac', i, r))
                continue
            khoi.append((i, r, k))
        if khoi:
            ra.append(('khoi', khoi))
        if sum(1 for x in ra if x[0] == 'khoi' for y in x[1] if 'S' in y[2]) >= 3:
            for x in ra:
                if x[0] == 'khac':
                    yield x[1], x[2]
                else:
                    yield from _gom_nhom_stt(x[1], n.rong, tuple(c[k] for k in ('ho_ten', 'dia_chi', 'cccd', 'dien_thoai') if k in c))
            return
    ban_ghi = []                                             # {'i', 'r', 'tren': [dòng], 'duoi': [dòng]}
    cho = []                                                 # dòng chữ thuộc ô nhiều dòng, chưa biết của dòng số liệu nào
    can_giua = None
    ra = []                                                  # thứ tự đầu ra: ('ghi', ban ghi) | ('khac', i, r)

    def xong(ds):
        if ban_ghi and ds:
            ban_ghi[-1]['duoi'] += ds
    for i in range(dau, len(luoi) + 1):
        r = luoi[i - 1]
        k = loai(r)
        if k == 'trong':
            continue
        if k == 'T':
            cho.append(r)
            continue
        if k in ('khac', 'cat'):
            xong(cho)
            cho = []
            if k == 'khac':
                ra.append(('khac', i, r))
            continue
        if not ban_ghi:
            tren, can_giua = cho, bool(cho)
        elif can_giua:
            so_duoi = min(len(cho), len(ban_ghi[-1]['tren']))
            xong(cho[:so_duoi])
            tren = cho[so_duoi:]
        else:
            xong(cho)
            tren = []
        cho = []
        ban_ghi.append(dict(i=i, r=r, tren=tren, duoi=[]))
        ra.append(('ghi', ban_ghi[-1]))
    xong(cho)
    for x in ra:
        if x[0] == 'khac':
            yield x[1], x[2]
        else:
            b = x[1]
            yield b['i'], (_noi_dong(b['tren'] + [b['r']] + b['duoi'], n.rong) if (b['tren'] or b['duoi']) else b['r'])


def _phan_tich(n: Nguon, bc: BoCot, long: bool = False) -> KetQuaDoc:
    """Đọc các dòng dưới khối tiêu đề của nguồn n theo cách ghép cột bc -> hộ, thửa, cảnh báo. long: chế độ nới lỏng - không bỏ dòng
    'cộng / tổng', tiêu đề lặp, chữ gộp ngang, dòng nhóm (dùng khi chế độ thường không ra hộ nào: dòng thừa xóa trên bảng)."""
    kq = KetQuaDoc(bc, loai=n.loai)
    luoi = n.luoi
    c = bc.cot
    bo = Counter()
    # tên bảng (dòng chữ phía trên tiêu đề) -> tên dự án: ưu tiên dòng có chữ "dự án"
    dong_tren = []
    for i in range(1, bc.dong_tieu_de[0]):
        chu = [' '.join(str(v).split()) for v in luoi[i - 1] if isinstance(v, str) and v.strip()]
        if chu and chu[0] not in dong_tren:
            dong_tren.append(chu[0])
    kq.tieu_de_bang = next((t for t in dong_tren if 'du an' in chuan_hoa(t)), dong_tren[0] if dong_tren else '')
    g = lambda r, k: r[c[k]] if k in c and c[k] < len(r) else None
    co_ten_cot = 'ho_ten' in c
    ten_tam = False

    theo_khoa, truoc = {}, None
    for i, r in _dong_du_lieu(n, bc, bo):
        if not any(v not in (None, '') and str(v).strip() for v in r):
            continue
        if _la_dong_danh_so(r):
            bo['dòng đánh số cột'] += 1
            continue
        ten = _khong_gia_tri(' '.join(_txt(g(r, 'ho_ten')).split()))
        to, thua, dt_tho = _ma_so(g(r, 'so_to')), _ma_so(g(r, 'so_thua')), g(r, 'dt_thu_hoi')
        if 'to_thua' in c and not (to and thua):
            t1, t2 = _tach_to_thua(g(r, 'to_thua'))
            to, thua = to or t1, thua or t2
        if isinstance(dt_tho, str) and _TRONG.match(dt_tho.strip()):
            dt_tho = None
        if not long and any(DONG_CONG.match(chuan_hoa(v)) for v in r if isinstance(v, str)):
            bo['dòng cộng / tổng'] += 1
            continue
        # tiêu đề lặp lại giữa bảng (bảng in nhiều trang): họ tên / tờ / thửa / diện tích trùng chữ tiêu đề
        if not long and sum(1 for k in ('ho_ten', 'so_to', 'so_thua', 'dt_thu_hoi', 'dia_chi') if k in c and bc.tieu_de.get(k)
                            and chuan_hoa(_txt(g(r, k))) == chuan_hoa(bc.tieu_de[k])) >= (1 if ten else 2):
            bo['dòng tiêu đề lặp lại'] += 1
            continue
        # dòng chữ gộp ngang nhiều cột ("Kinh phí đảm bảo…", "Trong đó:"): cùng một chữ ở ô họ tên và ô STT / tờ / thửa / địa chỉ
        if not long and ten and any(k in c and c[k] != c['ho_ten'] and _txt(g(r, k)).strip() == _txt(g(r, 'ho_ten')).strip()
                                    for k in ('stt', 'so_to', 'so_thua', 'dia_chi')):
            bo['dòng chữ gộp ngang'] += 1
            continue
        co_thua = bool(to or thua or _txt(dt_tho))
        if not co_ten_cot:                                                    # file không có cột họ tên: mỗi thửa một hộ tạm
            if not co_thua:
                bo['dòng không có tờ / thửa / diện tích'] += 1
                continue
            ten = f'Hộ tờ {to} thửa {thua}'.strip() if (to or thua) else f'Hộ dòng {i}'
            ten_tam = True
            cccd = chuan_cccd(g(r, 'so_cccd'))
            dc = ' '.join(_txt(g(r, 'dia_chi')).split())
            khoa = ('cccd', cccd) if cccd else ('dong', i)
            h = theo_khoa.get(khoa)
            if h is None:
                h = dict(ma_ho=len(kq.ho) + 1, ho_ten=ten, so_cccd=cccd, ngay_cap=_txt(g(r, 'ngay_cap')),
                         noi_cap=_txt(g(r, 'noi_cap')), dia_chi=dc, dien_thoai=_txt(g(r, 'dien_thoai')),
                         nhan_khau=_txt(g(r, 'nhan_khau')), ghi_chu=[], dong=i)
                theo_khoa[khoa] = h
                kq.ho.append(h)
        elif not ten:
            if co_thua and truoc is not None:                                # dòng tiếp theo của hộ phía trên
                h = truoc
            else:
                bo['dòng không có họ tên' if not co_thua else 'dòng thửa đầu bảng chưa có họ tên'] += 1
                continue
        else:
            stt = _txt(g(r, 'stt'))
            if not long and not co_thua and not _txt(g(r, 'dia_chi')) and stt and not stt.isdigit():
                bo['dòng nhóm (I, A, Ấp…)'] += 1
                continue                                                     # dòng nhóm: "I", "A", "Ấp 8"...
            cccd = chuan_cccd(g(r, 'so_cccd'))
            dc = ' '.join(_txt(g(r, 'dia_chi')).split())
            khoa = ('cccd', cccd) if cccd else ('ten', chuan_hoa(ten), chuan_hoa(dc))
            h = theo_khoa.get(khoa)
            if h is None:
                h = dict(ma_ho=len(kq.ho) + 1, ho_ten=ten, so_cccd=cccd, ngay_cap=_txt(g(r, 'ngay_cap')),
                         noi_cap=_txt(g(r, 'noi_cap')), dia_chi=dc, dien_thoai=_txt(g(r, 'dien_thoai')),
                         nhan_khau=_txt(g(r, 'nhan_khau')), ghi_chu=[], dong=i)
                theo_khoa[khoa] = h
                kq.ho.append(h)
            else:
                h['dien_thoai'] = h['dien_thoai'] or _txt(g(r, 'dien_thoai'))
        truoc = h
        gc = ' '.join(_txt(g(r, 'ghi_chu')).split())
        if gc and gc not in h['ghi_chu']:
            h['ghi_chu'].append(gc)
        if not co_thua:
            kq.canh_bao.append(f'Dòng {i}: {h["ho_ten"]} - không có tờ, thửa, diện tích (chỉ tạo hộ, chưa có thửa).')
            continue
        try:
            dt = _doc_dt(dt_tho)
        except ValueError:
            kq.canh_bao.append(f'Dòng {i}: {h["ho_ten"]} - không đọc được diện tích {_txt(dt_tho)!r}, ghi 0.')
            dt = None
        dt_bd = None
        try:
            dt_bd = _doc_dt(g(r, 'dt_ban_do'))
        except ValueError:
            pass
        if dt is None and dt_bd is not None:
            dt = dt_bd
            kq.canh_bao.append(f'Dòng {i}: {h["ho_ten"]} tờ {to} thửa {thua} - không có DT thu hồi, lấy DT bản đồ {chuoi(dt_bd)}.')
        elif dt_bd is not None and dt_bd != dt:
            h['ghi_chu'].append(f'Tờ {to} thửa {thua}: DT thu hồi bản đồ {chuoi(dt_bd)} m²')
        if dt is None:
            kq.canh_bao.append(f'Dòng {i}: {h["ho_ten"]} tờ {to} thửa {thua} - chưa có diện tích thu hồi (ghi 0).')
        loai = re.sub(r'\s*\+\s*', '+', ' '.join(_txt(g(r, 'loai_dat')).split()))
        if not loai:
            kq.canh_bao.append(f'Dòng {i}: {h["ho_ten"]} tờ {to} thửa {thua} - chưa có loại đất.')
        if not to or not thua:
            kq.canh_bao.append(f'Dòng {i}: {h["ho_ten"]} - thiếu {"số tờ" if not to else "số thửa"}.')
        kq.thua.append(dict(ma_thua=len(kq.thua) + 1, ma_ho=h['ma_ho'], so_to=to, so_thua=thua, loai_dat=loai,
                            dt_thu_hoi=chuoi(dt) if dt is not None else '0', nguon_goc=_txt(g(r, 'nguon_goc')),
                            vi_tri=' '.join(_txt(g(r, 'vi_tri')).split()), thu_tu=len(kq.thua) + 1, dong=i))

    kq.da_bo = dict(bo)
    if ten_tam:
        kq.canh_bao.insert(0, 'File không có cột họ tên: mỗi thửa là một hộ tạm "Hộ tờ … thửa …" - sửa họ tên ngay trên bảng.')
    # kiểm tra
    if not kq.ho:
        kq.loi.append(_giai_thich_khong_ho(n, bc, bo))
    theo_ten = {}
    for h in kq.ho:
        theo_ten.setdefault(chuan_hoa(h['ho_ten']), []).append(h)
    for ds in theo_ten.values():
        if len(ds) > 1 and len({chuan_hoa(h['dia_chi']) for h in ds}) > 1 and co_ten_cot:
            kq.canh_bao.append(f'{ds[0]["ho_ten"]}: cùng họ tên, khác địa chỉ -> tách {len(ds)} hộ (mã '
                               + ', '.join(str(h['ma_ho']) for h in ds) + '); gộp lại nếu là một người.')
    theo_thua = {}
    for t in kq.thua:
        if t['so_to'] and t['so_thua']:
            theo_thua.setdefault((t['so_to'], t['so_thua']), []).append(t)
    ten = {h['ma_ho']: h['ho_ten'] for h in kq.ho}
    for (to, so), ds in theo_thua.items():
        if len({t['ma_ho'] for t in ds}) > 1:
            kq.canh_bao.append(f'Tờ {to} thửa {so} có {len(ds)} hộ: ' + ', '.join(ten[t['ma_ho']] for t in ds)
                               + ' (đồng sử dụng hoặc trùng - xem lại).')
    return kq


def _ten_cot(j: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA."""
    s = ''
    j += 1
    while j:
        j, d = divmod(j - 1, 26)
        s = chr(65 + d) + s
    return s


def _giai_thich_khong_ho(n: Nguon, bc: BoCot, bo: Counter) -> str:
    dong = bc.dong_tieu_de[-1]
    tong = max(0, len(n.luoi) - dong)
    tin = [f'Sheet "{bc.sheet}": không có dòng hộ nào dưới tiêu đề (dòng {dong}).' if n.loai == 'excel'
           else f'{bc.sheet}: không có dòng hộ nào dưới tiêu đề (dòng {dong}).']
    if tong == 0:
        tin.append('Dưới dòng tiêu đề không còn dòng dữ liệu nào (file trống, hoặc công thức chưa có giá trị đã lưu - mở bằng Excel, '
                   'lưu lại rồi nhập lại).')
    else:
        if 'ho_ten' in bc.cot:
            j = bc.cot['ho_ten']
            co = _do_day_cot(n.luoi, dong, j)
            tin.append(f'Cột họ tên đang nhận: cột {_ten_cot(j)} "{bc.tieu_de.get("ho_ten", "")}" - có chữ ở {co * 100:.0f}% số dòng.')
        if bo:
            tin.append('Các dòng bị bỏ: ' + '; '.join(f'{v} {k}' for k, v in bo.most_common()) + '.')
    tin.append('Dùng "Chỉnh cột…" để chọn lại sheet, dòng tiêu đề và cột họ tên / tờ / thửa / diện tích bằng tay.')
    return ' '.join(tin)


def _khong_tieu_de(n: Nguon):
    """File không có dòng tiêu đề: đoán cột theo nội dung từ dòng đầu. Trả BoCot hoặc None."""
    if len(n.luoi) < 3 or n.rong < 2:
        return None
    cot = suy_cot(n.luoi, 0, n.rong, {}, tat_ca_so=True)
    if not _dat_yeu_cau(cot) or 'ho_ten' not in cot or not any(k in cot for k in NHOM_THUA):
        return None
    bo = BoCot(n.ten, [0], dict(cot), {k: f'cột {_ten_cot(j)}' for k, j in cot.items()}, 0, [''] * n.rong, set(cot))
    return bo


def _bo_sung_theo_noi_dung(n: Nguon, bc: BoCot) -> None:
    """Cột chưa nhận ra theo tiêu đề nhưng nội dung rõ (CCCD, điện thoại, loại đất, họ tên, địa chỉ): thêm vào bc."""
    if bc.thu_cong:
        return
    them = suy_cot(n.luoi, bc.dong_tieu_de[-1], n.rong, bc.cot, td=bc.td)
    for k, j in them.items():
        bc.cot[k] = j
        bc.suy.add(k)
        bc.tieu_de[k] = f'cột {_ten_cot(j)}'


def doc_nguon(nguons: list, bo_cot: BoCot | None = None) -> KetQuaDoc:
    """Đọc các nguồn (sheet / bảng) của một file: bo_cot (ghép tay) thì đọc đúng sheet đó; không thì thử lần lượt các khối tiêu đề điểm
    cao nhất cho tới khi có hộ; không có tiêu đề thì đoán cột theo nội dung."""
    if not nguons:
        kq = KetQuaDoc(None)
        kq.loi.append('Không đọc được dữ liệu nào trong file (file trống).')
        return kq
    if bo_cot is not None:
        n = next((x for x in nguons if x.ten == bo_cot.sheet), nguons[0])
        kq = _phan_tich(n, bo_cot)
        return _hoan_tat(kq, nguons, n)
    ung = []
    for n in nguons:
        ung += [(b.diem, n, b) for b in ung_vien(n)]
    ung.sort(key=lambda x: -x[0])
    kq_tot_nhat = None
    for _, n, b in ung:
        _bo_sung_theo_noi_dung(n, b)
        kq = _phan_tich(n, b)
        if kq.ho:
            return _hoan_tat(kq, nguons, n)
        if kq_tot_nhat is None:
            kq_tot_nhat = (kq, n)
    for n in nguons:                                                 # không có dòng tiêu đề: đoán theo nội dung
        b = _khong_tieu_de(n)
        if b is not None:
            kq = _phan_tich(n, b)
            if kq.ho:
                kq.thong_bao.append('File không có dòng tiêu đề nhận ra được: cột đoán theo nội dung - xem lại các cột trên bảng.')
                return _hoan_tat(kq, nguons, n)
    for _, n, b in ung[:3]:                                           # nới lỏng bộ lọc dòng: có dòng bị bỏ mà không ra hộ nào
        kq = _phan_tich(n, b, True)
        if kq.ho:
            kq.canh_bao.insert(0, 'Chế độ nới lỏng: các dòng giống dòng cộng / tiêu đề / dòng nhóm cũng được lấy - xóa dòng thừa trên bảng.')
            return _hoan_tat(kq, nguons, n)
    if kq_tot_nhat is not None:
        kq, n = kq_tot_nhat
        return _hoan_tat(kq, nguons, n)
    kq = KetQuaDoc(None)
    kq.loi.append('Không tìm thấy bảng có cột HỌ TÊN và cột TỜ / THỬA / DIỆN TÍCH THU HỒI trong file. Dùng "Chỉnh cột…" để ghép cột bằng tay.')
    kq.nguons = nguons
    kq.thong_bao += [x for n in nguons for x in n.ghi_chu]
    kq.loai = nguons[0].loai
    return kq


def _hoan_tat(kq: KetQuaDoc, nguons: list, n: Nguon) -> KetQuaDoc:
    kq.nguons = nguons
    kq.loai = n.loai
    kq.thong_bao += n.ghi_chu
    khac = [x.ten for x in nguons if x is not n and x.loai == 'excel' and len(x.luoi) > 1]
    if kq.ho and khac and kq.bo_cot is not None and not kq.bo_cot.thu_cong:
        kq.thong_bao.append(f'Đã lấy từ sheet "{n.ten}"; file còn {len(khac)} sheet khác ({", ".join(khac[:6])}'
                            + ('…' if len(khac) > 6 else '') + ') - "Chỉnh cột…" để chọn sheet khác.')
    if kq.bo_cot is not None and kq.bo_cot.suy and not kq.bo_cot.thu_cong:
        ten = dict(ho_ten='họ tên', dia_chi='địa chỉ', so_cccd='CCCD', dien_thoai='điện thoại', loai_dat='loại đất', so_to='tờ',
                   so_thua='thửa', dt_thu_hoi='diện tích')
        kq.thong_bao.append('Cột đoán theo nội dung (tiêu đề không rõ): ' + ', '.join(
            f'{ten.get(k, k)} = cột {_ten_cot(kq.bo_cot.cot[k])}' for k in sorted(kq.bo_cot.suy, key=lambda k: kq.bo_cot.cot[k])) + '.')
    return kq


def doc(file_excel, bo_cot: BoCot | None = None, nguons: list | None = None, bao_tien_do=None, cho=None, scan: bool = False) -> KetQuaDoc:
    """Đọc file bất kỳ (Excel .xlsx / .xls, Word, CSV, PDF có chữ hoặc bản scan, ảnh) -> danh sách hộ, thửa (chưa ghi gì).
    bo_cot: cách ghép cột do người dùng chọn; nguons: các nguồn đã đọc sẵn (đổi cách ghép không phải đọc / nhận dạng lại)."""
    p = Path(file_excel)
    if nguons is None:
        nguons = lay_nguon(p, bao_tien_do, cho, scan)
    kq = doc_nguon(nguons, bo_cot)
    if not kq.ho and bo_cot is None and nguons and all(x.loai == 'scan' for x in nguons) and len(nguons) == 1:
        try:                                                              # bản scan không có khung kẻ: chế độ đọc khối chữ đều (psm 6)
            kq2 = doc_nguon(lay_nguon(p, bao_tien_do, cho, True, psm=6))
        except LoiNhap:
            kq2 = None
        if kq2 is not None and kq2.ho:
            return kq2
    # PDF có lớp chữ nhưng không ra bảng (chữ chỉ là con dấu, nội dung là ảnh): thử nhận dạng chữ
    if (not kq.ho and bo_cot is None and not scan and nguons and all(x.loai == 'pdf' for x in nguons)):
        try:
            n2 = lay_nguon(p, bao_tien_do, cho, True)
        except LoiNhap as e:
            kq.thong_bao.append(f'Thử nhận dạng chữ trên ảnh không được: {e}')
        else:
            kq2 = doc_nguon(n2)
            if kq2.ho:
                return kq2
    return kq


def la_file_pabt(file_excel) -> bool:
    """File theo mẫu PABT Excel (.xlsm có DB_HO, DB_THUA...) thì nhập bằng nhap_excel, còn lại nhập bằng module này."""
    if Path(file_excel).suffix.lower() not in ('.xlsx', '.xlsm'):
        return False
    __import__('pabt.an_toan').an_toan.kiem_excel(file_excel)
    wb = openpyxl.load_workbook(str(file_excel), read_only=True)
    try:
        return all(s in wb.sheetnames for s in ('DB_HO', 'DB_THUA', 'DB_DATCT'))
    finally:
        wb.close()


def mo_ta_cot(bo: BoCot) -> str:
    ten = dict(stt='STT', ho_ten='Họ tên', dia_chi='Địa chỉ', so_cccd='CCCD', ngay_cap='Ngày cấp', noi_cap='Nơi cấp',
               dien_thoai='Điện thoại', so_to='Tờ', so_thua='Thửa', to_thua='Tờ / Thửa', dt_thu_hoi='DT thu hồi',
               dt_ban_do='DT bản đồ', loai_dat='Loại đất', nguon_goc='Nguồn gốc', vi_tri='Vị trí', ghi_chu='Ghi chú',
               nhan_khau='Nhân khẩu')
    dau = (f'tiêu đề dòng {bo.dong_tieu_de[0]}' + (f'-{bo.dong_tieu_de[-1]}' if len(bo.dong_tieu_de) > 1 else '')
           if bo.dong_tieu_de[0] else 'không có dòng tiêu đề (cột đoán theo nội dung)')
    return (f'sheet "{bo.sheet}", {dau}: '
            + '; '.join(f'{ten.get(k, k)} = "{bo.tieu_de[k]}"' + (' (đoán)' if k in bo.suy else '')
                        for k in sorted(bo.cot, key=bo.cot.get)))


def dia_ban_tu_ten(ten: str) -> tuple:
    """'Dự án đường số 9 đoạn qua xã Bàu Hàm' -> ('Xã', 'Bàu Hàm'); không thấy thì ('Phường', '')."""
    m = re.search(r'\b(xã|phường|thị trấn)\s+([^,;()\n]+)', ten, re.I)
    if not m:
        return 'Phường', ''
    return m.group(1).capitalize(), ' '.join(m.group(2).split())


DU_LIEU_HO = ('doi_thoai_ho', 'y_kien_du_thao', 'dot_du_thao', 'qd_ho', 'quyet_dinh', 'ct_dat', 'ct_khoan', 'thua', 'ho',
              'tong_excel', 'nhat_ky', 'tho_nhap', 'dot_trinh')


TRUONG_DON_VI = csdl.TRUONG_DON_VI


def xoa_trang(con) -> None:
    """Xóa toàn bộ hồ sơ dự án (hộ, thửa, phương án, tổng Excel, nhật ký, thông tin dự án);
    giữ danh mục, tham số và thông tin đơn vị lập, người ký."""
    giu = TRUONG_DON_VI + ('phien_ban_gia',)          # thông tin đơn vị, người ký, phiên bản bộ đơn giá đang áp
    dv = con.execute(f'SELECT {", ".join(giu)} FROM du_an WHERE id = 1').fetchone()
    from . import van_dong
    van_dong.xoa_het(con)                              # sổ nhật ký vận động (bảng tạo khi cần) - xóa trước hộ
    for b in DU_LIEU_HO:
        con.execute(f'DELETE FROM {b}')
    con.execute('DELETE FROM du_an')
    con.execute('INSERT INTO du_an (id) VALUES (1)')
    if dv is not None:
        con.execute(f'UPDATE du_an SET {", ".join(k + " = ?" for k in giu)} WHERE id = 1', tuple(dv))


def nhap(file_excel, file_pabt, ten_du_an: str = '', danh_muc=None) -> BaoCaoNhap:
    """Đọc file Excel bất kỳ và ghi vào file_pabt (xóa trắng hồ sơ cũ, giữ danh mục).

    file_pabt chưa có: tạo mới; nếu có danh_muc (một file .pabt khác) thì chép danh mục, tham số từ đó.
    Có lỗi chặn thì không ghi gì.
    """
    kq = doc(file_excel)
    bc = BaoCaoNhap(file_excel=str(file_excel), file_pabt=str(file_pabt), loi=kq.loi, canh_bao=kq.canh_bao)
    if kq.loi:
        return bc
    p = Path(file_pabt)
    moi = not p.exists()
    con = csdl.mo(p, tao=True)
    try:
        if moi and danh_muc:
            _chep_danh_muc(con, danh_muc)
        elif moi:
            from . import don_gia
            from .to_chuc import MAC_DINH
            don_gia.ap_vao_du_an(con)
            with con:
                con.execute(f'UPDATE du_an SET {", ".join(k + " = ?" for k in MAC_DINH)} WHERE id = 1', tuple(MAC_DINH.values()))
        with con:
            xoa_trang(con)
            ten = ten_du_an or kq.tieu_de_bang or Path(file_excel).stem
            cap, dia_ban = dia_ban_tu_ten(ten)
            con.execute('UPDATE du_an SET ten=?, ten_day_du=?, cap_dia_ban=?, ten_dia_ban=?, nguon_nhap=?, ngay_nhap=? WHERE id=1',
                        (ten, ten, cap, dia_ban, Path(file_excel).name, datetime.now().isoformat(timespec='seconds')))
            for i, h in enumerate(kq.ho, start=1):
                con.execute('''INSERT INTO ho (ma_ho, thu_tu, ho_ten, so_cccd, ngay_cap, noi_cap, dia_chi, dien_thoai, ghi_chu)
                               VALUES (?,?,?,?,?,?,?,?,?)''',
                            (h['ma_ho'], i, h['ho_ten'], h['so_cccd'], h['ngay_cap'], h['noi_cap'], h['dia_chi'],
                             h['dien_thoai'], '; '.join(h['ghi_chu'])))
            con.executemany('''INSERT INTO thua (ma_thua, ma_ho, so_to, so_thua, loai_dat, dt_thu_hoi, nguon_goc, vi_tri, thu_tu)
                               VALUES (:ma_thua,:ma_ho,:so_to,:so_thua,:loai_dat,:dt_thu_hoi,:nguon_goc,:vi_tri,:thu_tu)''', kq.thua)
            bo = kq.bo_cot
            csdl.ghi_nhat_ky(con, 'Nhập danh sách Excel (tự nhận cột)',
                             f'{Path(file_excel).name}: {len(kq.ho)} hộ, {len(kq.thua)} thửa; {mo_ta_cot(bo)}')
    finally:
        con.close()
    bc.so_ho, bc.so_thua = len(kq.ho), len(kq.thua)
    bc.so_dong = {1: 0, 2: 0, 3: 0, 4: 0}
    bc.nhan_cot = mo_ta_cot(kq.bo_cot)
    return bc


DANH_MUC = csdl.DANH_MUC
_chep_danh_muc = csdl.chep_danh_muc


def nap_danh_muc(file_pabt, file_excel) -> dict:
    """Nạp danh mục đơn giá, tham số, biểu thưởng, giá đất… từ một file PABT Excel (.xlsm) vào file dự án:
    thay danh mục cũ, GIỮ NGUYÊN hồ sơ hộ, thửa, phương án. Trả số mục từng danh mục."""
    if not la_file_pabt(file_excel):
        raise LoiNhap('File không theo mẫu PABT Excel (cần các sheet DM_HOTRO, DG_NHANUOC, THAM_SO…).')
    with tempfile.TemporaryDirectory() as td:
        tam = Path(td) / 'danh_muc.pabt'
        bc = nhap_excel.nhap(file_excel, tam)
        if bc.loi:
            raise LoiNhap('Không đọc được danh mục:\n' + '\n'.join(bc.loi))
        con = csdl.mo(file_pabt)
        try:
            from . import don_gia_rieng
            rieng = don_gia_rieng.doc_rieng(con)           # quy ước / đơn giá thẩm định riêng của dự án: giữ (như áp bộ đơn giá)
            _chep_danh_muc(con, tam, don_vi=False)
            with con, csdl.mo_khoa_danh_muc(con):
                don_gia_rieng.tra_rieng(con, rieng)
            dem = {b: con.execute(f'SELECT COUNT(*) FROM {b}').fetchone()[0] for b in DANH_MUC}
            with con:
                csdl.ghi_nhat_ky(con, 'Nạp danh mục đơn giá', f'{Path(file_excel).name}: ' +
                                 ', '.join(f'{b} {n}' for b, n in dem.items()))
        finally:
            con.close()
    return dem

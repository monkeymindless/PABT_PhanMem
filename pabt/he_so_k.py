"""Hệ số điều chỉnh giá đất (hệ số K) theo Quyết định số 03/2026/QĐ-UBND ngày 11/5/2026 của UBND thành phố Đồng Nai.

Văn bản (Điều 3): giá đất = giá trong bảng giá đất (NQ 28/2025/NQ-HĐND) nhân lần lượt các hệ số: Phụ lục I - hệ số điều chỉnh mức
biến động thị trường (I.1 đất phi nông nghiệp: 3 cột đất ở / TMDV / cơ sở SX phi NN + khoáng sản; I.2 đất nông nghiệp: một cột; I.3
đất NN / PNN còn lại: lấy theo loại tương ứng), Phụ lục II - theo quy hoạch (hệ số sử dụng đất của dự án), Phụ lục III - yếu tố khác.
Phần mềm tự áp hệ số của PHỤ LỤC I; II, III tùy trường hợp (người dùng nhân thêm ở ô Hệ số K). Bảng Phụ lục I mỗi xã / phường một
bảng, mỗi TT một dòng - TRÙNG số TT với bảng giá NQ 28 (mặt tiền, T1-T3, K1-K3 của từng đoạn đường).

Bảng gắn sẵn `pabt/he_so_k_qd03.json`: 4 địa bàn của bảng giá gắn sẵn (Trị An, Tân An, Phú Lý, Tân Triều), đọc từ PDF Phụ lục I.1 /
I.2 bằng `doc_phu_luc` + `noi_bang_gia` (tên đường / điểm đầu / cuối / vị trí lấy theo dòng cùng TT của bảng giá). Người dùng nhập
thêm / thay -> `<thư mục máy>\\he_so_k.json` (dùng thay bảng gắn sẵn; xóa file = dùng lại). Không đổi lược đồ CSDL.

Mỗi dòng: địa bàn, tt (số TT bảng giá; '' = dòng chung), loại đất (nhóm cột bảng giá NQ 28 - `gia_dat_nq28.COT`, nhóm chung 'nn' /
'pnn', hoặc mã 'ONT,ODT'; '' = mọi loại), vị trí ('MT', 'T1'…'K3', 'VT1', 'KV1'; '' = mọi), tuyến đường, điểm đầu, điểm cuối, hệ số
(chuỗi Decimal), ghi chú. `tra` chọn dòng khớp cụ thể nhất (TT > tuyến + đoạn > vị trí > loại đất > địa bàn).
`phan_tich` (bảng / chữ của văn bản khác: tiêu đề có "Hệ số" hoặc mỗi cột một loại đất; chữ "Xã …", "Vị trí 1: 1,2") vẫn dùng khi
file không phải mẫu Phụ lục I.
"""
from __future__ import annotations

import json
import os
import re
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

from .lap_pa import bo_dau, cung_dia_ban, khoa_dia_ban, trung_dia_ban

TEN_FILE = 'he_so_k.json'
FILE_GAN_SAN = 'he_so_k_qd03.json'
VAN_BAN = 'Quyết định số 03/2026/QĐ-UBND ngày 11/5/2026 của UBND thành phố Đồng Nai'
TRUONG = ('dia_ban', 'tt', 'loai_dat', 'vi_tri', 'tuyen_duong', 'diem_dau', 'diem_cuoi', 'he_so', 'ghi_chu')
NHAN_TRUONG = {'dia_ban': 'Địa bàn', 'tt': 'TT', 'loai_dat': 'Loại đất', 'vi_tri': 'Vị trí', 'tuyen_duong': 'Tuyến đường / khu vực',
               'diem_dau': 'Từ', 'diem_cuoi': 'Đến', 'he_so': 'Hệ số K', 'ghi_chu': 'Ghi chú'}
# nhóm loại đất: khóa cột bảng giá NQ 28 + hai nhóm chung
NHOM = [('dat_o', 'Đất ở'), ('tmdv', 'Đất thương mại, dịch vụ'), ('sxkd', 'Đất SX-KD phi NN, khoáng sản'),
        ('nn_cay', 'Đất trồng cây lâu năm, cây hằng năm'), ('nn_rung_nts', 'Đất rừng sản xuất, nuôi trồng thủy sản'),
        ('nn', 'Đất nông nghiệp (mọi loại)'), ('pnn', 'Đất phi NN không phải đất ở')]
TEN_NHOM = dict(NHOM)
NHOM_CHUNG = {'nn': ('nn_cay', 'nn_rung_nts'), 'pnn': ('tmdv', 'sxkd')}
# chữ trong văn bản -> nhóm (thứ tự quan trọng: "không phải đất ở" trước "đất ở", "nuôi trồng thủy sản" trước "trồng")
_CHU_NHOM = [
    (('khong phai dat o', 'phi nong nghiep khong'), 'pnn'),
    (('thuong mai', 'dich vu', 'tmdv', 'tmd'), 'tmdv'),
    (('san xuat kinh doanh', 'sxkd', 'khoang san', 'co so san xuat'), 'sxkd'),
    (('dat o', 'o tai nong thon', 'o tai do thi', 'ont', 'odt'), 'dat_o'),
    (('rung', 'thuy san', 'nts', 'rsx'), 'nn_rung_nts'),
    (('cay lau nam', 'cay hang nam', 'trong lua', 'dat lua', 'chuyen trong lua', 'cln', 'hnk', 'bhk', 'luc'), 'nn_cay'),
    (('nong nghiep',), 'nn'),
]
TEN_VT = {'MT': 'Mặt tiền', 'T1': 'T1', 'T2': 'T2', 'T3': 'T3', 'K1': 'K1', 'K2': 'K2', 'K3': 'K3'}


class LoiHeSoK(ValueError):
    """File hệ số K không đọc được / không có dòng hệ số."""


# ---------------------------------------------------------------- lưu trữ
def file_he_so() -> Path:
    from .may_chu import thu_muc_may
    return thu_muc_may() / TEN_FILE


def file_gan_san() -> Path:
    from . import tai_nguyen
    return tai_nguyen(FILE_GAN_SAN)


def _nguon() -> tuple:
    """(file đang dùng, đã thay bảng gắn sẵn?)."""
    p = file_he_so()
    if p.is_file():
        return p, True
    return file_gan_san(), False


def _mo_rong(dong) -> list:
    """Dòng gọn {..., 'k': {nhóm: hệ số}} (một TT nhiều loại đất) -> mỗi loại đất một dòng."""
    kq = []
    for r in dong or ():
        if not isinstance(r, dict):
            continue
        if isinstance(r.get('k'), dict):
            for ld, k in r['k'].items():
                kq.append(chuan_dong(dict(r, loai_dat=ld, he_so=k)))
        else:
            kq.append(chuan_dong(r))
    return kq


def _gon(dong: list) -> list:
    """Ngược với _mo_rong: các dòng cùng TT (cùng địa bàn, vị trí, tuyến, đoạn, ghi chú) gộp một dòng 'k'."""
    kq, cho = [], {}
    for r in dong:
        if r['tt'] == '' or r['loai_dat'] not in TEN_NHOM:
            kq.append({k: v for k, v in r.items() if v != ''})
            continue
        khoa = tuple(r[t] for t in TRUONG if t not in ('loai_dat', 'he_so'))
        if khoa not in cho:
            g = {k: v for k, v in r.items() if v != '' and k not in ('loai_dat', 'he_so')}
            g['k'] = {}
            cho[khoa] = g
            kq.append(g)
        cho[khoa]['k'][r['loai_dat']] = r['he_so']
    return kq


@lru_cache(maxsize=4)
def _doc(duong: str, mtime: int) -> tuple:
    try:
        data = json.loads(Path(duong).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return (), '', ''
    if not isinstance(data, dict):
        return (), '', ''
    dong = tuple(r for r in _mo_rong(data.get('dong')) if r['he_so'])
    return dong, str(data.get('van_ban') or ''), str(data.get('nguon') or '')


NHO_GIAY = 2.0              # kiểm lại file hệ số K (stat 2 file) tối đa mỗi chừng này giây - tự lập phương án tra mỗi thửa một lần
_NHO_DOC = {'t': -1e9, 'khoa': None, 'gt': None}


def _da_doc() -> tuple:
    """(dòng, văn bản, nguồn) của bảng đang dùng. Nhớ NHO_GIAY giây (trước: mỗi lần tra stat 2 file - Dự án mới 3.000 hộ / 4.500 thửa
    tốn ~0,7 s); ghi / xóa bảng trong phần mềm đặt lại ngay; đổi thư mục máy (PABT_THU_MUC_MAY, kiểm thử) cũng đọc lại."""
    import time
    khoa = os.environ.get('PABT_THU_MUC_MAY', '')
    bay_gio = time.monotonic()
    if _NHO_DOC['khoa'] == khoa and bay_gio - _NHO_DOC['t'] < NHO_GIAY:
        return _NHO_DOC['gt']
    p, _ = _nguon()
    try:
        m = p.stat().st_mtime_ns
    except OSError:
        gt = ((), '', '')
    else:
        gt = _doc(str(p), m)
    _NHO_DOC.update(t=bay_gio, khoa=khoa, gt=gt)
    return gt


def _quen() -> None:
    _NHO_DOC['t'] = -1e9


def tat_ca() -> list:
    return [dict(r) for r in _da_doc()[0]]


def co_du_lieu() -> bool:
    return bool(_da_doc()[0])


def dang_thay() -> bool:
    """True: máy đang dùng bảng hệ số người dùng nhập (không còn bảng gắn sẵn)."""
    return _nguon()[1]


def van_ban() -> str:
    return _da_doc()[1] or VAN_BAN


def van_ban_ngan(vb: str = '') -> str:
    """'Quyết định số 03/2026/QĐ-UBND …' -> 'QĐ 03/2026/QĐ-UBND'."""
    vb = vb or van_ban()
    m = re.search(r'(\d{1,4}/\d{4}/Q[ĐD]-UBND)', vb, re.I)
    return f'QĐ {m.group(1)}' if m else vb


def can_cu(vb: str = '') -> str:
    """Chữ ghi ở cột Ghi chú / căn cứ: 'Hệ số K theo QĐ 03/2026/QĐ-UBND'."""
    return f'Hệ số K theo {van_ban_ngan(vb)}'


def tom_tat() -> str:
    ds = _da_doc()[0]
    if not ds:
        return f'Chưa nhập hệ số K ({van_ban_ngan(VAN_BAN)}): mục Đất dùng hệ số 1 hoặc hệ số trong bảng giá dự án.'
    xa = list(dict.fromkeys(r['dia_ban'] or 'Toàn tỉnh' for r in ds))
    return (f'{van_ban_ngan()}{" (bảng đã nhập)" if dang_thay() else " (bảng gắn sẵn)"}: {len(ds)} dòng hệ số K - '
            f'{", ".join(xa[:6])}{"…" if len(xa) > 6 else ""}')


def ghi(dong: list, vb: str = '', nguon: str = '') -> Path:
    """Ghi bảng hệ số K của máy (ghi file tạm rồi os.replace). Dòng không có hệ số hợp lệ bị bỏ. 1.0.56: cần quyền quản trị."""
    from . import quan_tri_bo
    quan_tri_bo.kiem_quyen('cập nhật hệ số K')
    ds = []
    for r in dong:
        r = chuan_dong(r)
        if r['he_so']:
            ds.append(r)
    if not ds:
        raise LoiHeSoK('Không có dòng nào có hệ số K hợp lệ (số lớn hơn 0).')
    p = file_he_so()
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_suffix('.json.tmp')
    tam.write_text(json.dumps({'van_ban': vb or VAN_BAN, 'nguon': str(nguon or ''), 'dong': _gon(ds)}, ensure_ascii=False,
                              separators=(',', ':')).replace('},{', '},\n{'), encoding='utf-8')
    os.replace(tam, p)
    _quen()
    quan_tri_bo.sau_khi_sua()
    return p


def xoa() -> bool:
    from . import quan_tri_bo
    quan_tri_bo.kiem_quyen('đổi bảng hệ số K')
    p = file_he_so()
    _quen()
    if not p.is_file():
        return False
    p.unlink()
    quan_tri_bo.sau_khi_sua()
    return True


# ---------------------------------------------------------------- chuẩn hóa
def doc_he_so(chu) -> str:
    """'1,2' / '1.20' / '1,15 lần' / 1.2 -> '1.2' (chuỗi Decimal); không phải hệ số hợp lệ (0 < K <= 20) -> ''."""
    if chu is None:
        return ''
    if isinstance(chu, (int, float, Decimal)) and not isinstance(chu, bool):
        s = str(chu)
    else:
        s = str(chu).strip().lower()
        s = re.sub(r'\s*(lan|lần|x)$', '', s).strip()
        s = s.replace(' ', '')
        if not re.fullmatch(r'\d{1,2}(?:[.,]\d{1,4})?', s):
            return ''
        s = s.replace(',', '.')
    try:
        k = Decimal(s)
    except InvalidOperation:
        return ''
    if not (0 < k <= 20):
        return ''
    k = k.normalize()
    return format(k, 'f')


def nhom_tu_chu(chu: str) -> str:
    """'Đất ở tại nông thôn' -> 'dat_o'; mã 'CLN' -> 'nn_cay'; khóa nhóm giữ nguyên; không nhận ra -> ''."""
    s = str(chu or '').strip()
    if not s:
        return ''
    if s in TEN_NHOM:
        return s
    for k, t in NHOM:
        if bo_dau(t) == bo_dau(s):
            return k
    from .gia_dat_nq28 import cot_cua_loai
    c = cot_cua_loai(s)
    if c:
        return c
    b = ' ' + ' '.join(re.sub(r'[^a-z0-9]+', ' ', bo_dau(s)).split()) + ' '
    for mau, k in _CHU_NHOM:
        if any(f' {m} ' in b for m in mau):
            return k
    return ''


def chuan_loai_dat(chu: str) -> str:
    """Ô loại đất của một dòng hệ số: khóa nhóm, hoặc danh sách mã loại đất 'ONT,ODT', hoặc ''."""
    s = str(chu or '').strip()
    if not s:
        return ''
    ma = [x for x in re.split(r'[\s,;+/]+', s.upper()) if x]
    if ma and all(re.fullmatch(r'[A-Z]{3}', x) for x in ma):
        return ','.join(ma)
    return nhom_tu_chu(s) or s


def chuan_vi_tri(chu: str) -> str:
    """Mã vị trí: 'Mặt tiền…' -> MT, 'Đường đấu nối trực tiếp - mức 1' -> T1, 'K2' -> K2, 'Vị trí 1' / '1' -> VT1,
    'Khu vực 2' -> KV2; không có -> ''."""
    s = str(chu or '').strip()
    if not s:
        return ''
    b = bo_dau(s)
    if b.startswith('mat tien') or re.fullmatch(r'mt', b):
        return 'MT'
    m = re.match(r'duong (khong )?dau noi truc tiep - muc ([1-3])', b)
    if m:
        return ('K' if m.group(1) else 'T') + m.group(2)
    m = re.fullmatch(r'\s*([tk])\s*([1-3])\s*', b)
    if m:
        return m.group(1).upper() + m.group(2)
    m = re.search(r'\b(?:khu vuc|kv)\s*[:.]?\s*(\d+)', b)
    if m:
        return 'KV' + m.group(1)
    m = re.search(r'\b(?:vi tri|vt)\s*[:.]?\s*(\d+)', b)
    if m:
        return 'VT' + m.group(1)
    if s.isdigit():
        return 'VT' + s
    m = re.search(r'\b(mt|[tk][1-3])\b', b)
    if m:
        return m.group(1).upper()
    return ''


def _so_tt(x):
    s = str(x if x is not None else '').strip()
    return int(s) if s.isdigit() else ''


def chuan_dong(r: dict) -> dict:
    o = (lambda k: str(r.get(k) or '').strip())
    return {'dia_ban': o('dia_ban'), 'tt': _so_tt(r.get('tt')), 'loai_dat': chuan_loai_dat(r.get('loai_dat')),
            'vi_tri': chuan_vi_tri(r.get('vi_tri')), 'tuyen_duong': o('tuyen_duong'), 'diem_dau': o('diem_dau'),
            'diem_cuoi': o('diem_cuoi'), 'he_so': doc_he_so(r.get('he_so')), 'ghi_chu': o('ghi_chu')}


def nhom_cho_ma(loai_dat: str) -> str:
    """Nhóm hệ số của một loại đất trên phương án (Phụ lục I.3 QĐ 03/2026): cột bảng giá NQ 28 nếu có; đất NN khác (chăn nuôi, NN
    khác) = cây lâu năm, rừng phòng hộ / đặc dụng = rừng sản xuất; đất PNN còn lại (công cộng, tôn giáo, nghĩa trang, mặt nước
    chuyên dùng PNN…) = cơ sở SX phi NN; quốc phòng / an ninh tùy trường hợp -> '' (không tự áp)."""
    s = str(loai_dat or '').strip()
    if not s:
        return ''
    n = nhom_tu_chu(s)
    if n:
        return n
    from .loai_dat import LOAI_DAT
    nhom = {ma: nh for ma, _, nh in LOAI_DAT}
    for ma in re.split(r'[\s,;+/]+', s.upper()):
        if ma == 'OTC':
            return 'dat_o'
        if ma in ('RPH', 'RDD', 'LNP'):
            return 'nn_rung_nts'
        if ma in ('CQP', 'CAN'):
            return ''
        if nhom.get(ma) == 'Nông nghiệp':
            return 'nn_cay'
        if nhom.get(ma) == 'Phi nông nghiệp':
            return 'sxkd'
    return ''


def ten_loai_dat(ld: str) -> str:
    return TEN_NHOM.get(ld, ld)


def _ten_xa(s: str) -> str:
    return re.sub(r'^(xa|phuong|thi tran|dac khu)\s+', '', bo_dau(s or '').strip()).strip()


def khop_dia_ban(dong_xa: str, xa: str) -> bool:
    """1.0.90: so nguyên chữ, giữ dấu khi hai bên cùng có dấu (trước: chuỗi con không dấu - "An Lộc" khớp "Xuân Lộc")."""
    return cung_dia_ban(dong_xa, xa)


def _dung_xa(ds, dia_ban: str, cm) -> list:
    """Chỉ mục khóa theo tên KHÔNG dấu: "Lộc Thành" và "Lộc Thạnh" chung một ô. Bảng có đúng tên (giữ dấu) của xã hỏi thì chỉ lấy
    dòng của xã đó; không có (gõ không dấu, chữ PDF mất dấu) thì giữ cả ô như trước."""
    if not ds or khoa_dia_ban(dia_ban) not in cm.khoa_co_dau:
        return list(ds)
    return [r for r in ds if trung_dia_ban(r['dia_ban'], dia_ban)]


# ---------------------------------------------------------------- tra cứu
class _ChiMuc:
    """Chỉ mục tra cứu dựng một lần cho một bảng: dòng có TT theo (xã, TT) và (xã, vị trí); dòng chung (không TT) duyệt hết."""

    def __init__(self, ds):
        self.theo_tt, self.theo_vt, self.chung = {}, {}, []
        self.vt_xa = {}                                 # {vị trí: [(xã, dòng)]} - nhánh "thửa thuộc xã khác" không duyệt hết bảng
        self.khoa_co_dau = {khoa_dia_ban(x) for x in {r['dia_ban'] for r in ds}}
        for r in ds:
            if r['tt'] != '':
                x = _ten_xa(r['dia_ban'])
                self.theo_tt.setdefault((x, r['tt']), []).append(r)
                self.theo_vt.setdefault((x, r['vi_tri']), []).append(r)
                self.vt_xa.setdefault(r['vi_tri'], []).append((x, r))
            else:
                self.chung.append(r)


_CHI_MUC = {}


def _chi_muc(ds) -> _ChiMuc:
    cm = _CHI_MUC.get(id(ds))
    if cm is None or cm[0] is not ds:
        if len(_CHI_MUC) > 4:
            _CHI_MUC.clear()
        cm = _CHI_MUC[id(ds)] = (ds, _ChiMuc(ds))
    return cm[1]


def _diem_loai(r, nhom: str, ma: list) -> int:
    """Điểm khớp loại đất; -1 = không khớp."""
    ld = r['loai_dat']
    if not ld:
        return 0
    if ld in TEN_NHOM:
        if ld == nhom:
            return 4
        return 2 if nhom in NHOM_CHUNG.get(ld, ()) else -1
    return 5 if ma and set(ld.split(',')) & set(ma) else -1


def _co_doan(r, td: str) -> bool:
    """Tên đường + điểm đầu + điểm cuối của dòng đều có trong chữ vị trí (mô tả do chon_vi_tri_nq28 ghi)."""
    return bool(r['tuyen_duong']) and all(bo_dau(x) in td for x in (r['tuyen_duong'], r['diem_dau'], r['diem_cuoi']) if x)


def tra(dia_ban: str = '', loai_dat: str = '', vi_tri: str = '', tuyen_duong: str = '', ds: list | None = None,
        tt=None) -> tuple:
    """Hệ số K của (địa bàn, loại đất (mã hoặc nhóm), vị trí, tuyến đường[, số TT bảng giá]). Trả (Decimal, dòng) / (None, None).
    Có TT: dòng cùng xã + TT. Không TT: dòng có TT khớp vị trí + tên đường + đoạn trong chữ vị trí (xã dự án trước, rồi xã khác),
    rồi dòng chung: trống một trường = áp dụng mọi giá trị; nhiều dòng khớp -> dòng cụ thể nhất."""
    ds = _da_doc()[0] if ds is None else ds             # không chép dòng: tự lập phương án gọi một lần mỗi thửa
    if not ds:
        return None, None
    cm = _chi_muc(ds)
    ma = [x for x in re.split(r'[\s,;+/]+', (loai_dat or '').upper()) if x]
    nhom = nhom_cho_ma(loai_dat) if loai_dat else ''
    vt = chuan_vi_tri(vi_tri)
    td = bo_dau(' '.join((tuyen_duong or '', vi_tri or '')))
    x = _ten_xa(dia_ban)

    def tot_nhat(dong, them):
        tot, diem_tot = None, -1
        for r in dong:
            d = _diem_loai(r, nhom, ma)
            if d >= 0 and d + them > diem_tot:
                tot, diem_tot = r, d + them
        return tot

    r = None
    if _so_tt(tt) != '':
        r = tot_nhat(_dung_xa(cm.theo_tt.get((x, _so_tt(tt)), ()), dia_ban, cm), 64)
    if r is None and vt and cm.theo_vt:
        r = tot_nhat([d for d in _dung_xa(cm.theo_vt.get((x, vt), ()), dia_ban, cm) if _co_doan(d, td)], 32)
        if r is None:                                   # thửa thuộc xã khác của dự án (mô tả vị trí ghi đủ tên đường + đoạn)
            r = tot_nhat([d for xa, d in cm.vt_xa.get(vt, ()) if xa != x and _co_doan(d, td)], 32)
    if r is None:
        tot, diem_tot = None, -1
        for d in cm.chung:
            diem = 0
            if d['dia_ban']:
                if not khop_dia_ban(d['dia_ban'], dia_ban):
                    continue
                diem += 1
            dl = _diem_loai(d, nhom, ma)
            if dl < 0:
                continue
            diem += dl
            if d['vi_tri']:
                if d['vi_tri'] != vt:
                    continue
                diem += 8
            if d['tuyen_duong']:
                if not td or bo_dau(d['tuyen_duong']) not in td:
                    continue
                diem += 16
            if diem > diem_tot:
                tot, diem_tot = d, diem
        r = tot
    if r is None:
        return None, None
    return Decimal(r['he_so']), dict(r)


# ---------------------------------------------------------------- phân tích văn bản
_RE_XA = re.compile(r'^\s*(?:[\dIVXLC]+\s*[.)/-]?\s*)?((?:xã|xa|phường|phuong|thị trấn|thi tran|đặc khu|dac khu)\s+[^\d:;,()]{2,40}?)'
                    r'\s*:?\s*$', re.I)
_RE_SO_VB = re.compile(r'(\d{1,4}/\d{4}/Q[ĐD]-UBND)', re.I)
_RE_SO = re.compile(r'(?<![\d.,/])(\d{1,2}(?:[.,]\d{1,4})?)(?![\d/]|[.,]\d)')


def _o(chu) -> str:
    return re.sub(r'\s+', ' ', str(chu or '')).strip()


def _tieu_de_xa(dong: str) -> str:
    m = _RE_XA.match(dong)
    if not m:
        return ''
    t = m.group(1).strip()
    return t[:1].upper() + t[1:]


def _vai_cot(chu: str) -> str:
    """Vai trò của ô tiêu đề: 'db' / 'ld' / 'vt' / 'td' / 'k' / 'stt' / 'gc' / nhóm loại đất / ''."""
    b = bo_dau(chu)
    if not b:
        return ''
    if b in ('stt', 'tt', 'so tt') or b.startswith('so thu tu'):
        return 'stt'
    if 'ghi chu' in b:
        return 'gc'
    if 'he so' in b:
        return nhom_tu_chu(re.sub(r'(?i)h[ệe]\s*s[ốo]\s*k?', ' ', chu)) or 'k'
    if 'loai dat' in b or b in ('muc dich su dung', 'loai'):
        return 'ld'
    if 'vi tri' in b or 'khu vuc' in b:
        return 'vt'
    if any(x in b for x in ('ten duong', 'tuyen duong', 'doan duong', 'tuyen, doan', 'ten tuyen')):
        return 'td'
    if re.search(r'\b(xa|phuong|dia ban|don vi hanh chinh|dvhc)\b', b) and len(b) < 40:
        return 'db'
    n = nhom_tu_chu(chu)
    return n if n else ''


def _tim_tieu_de(o: list) -> tuple:
    """(chỉ số dòng tiêu đề, {cột: vai}) hoặc (-1, {}). Tiêu đề hai tầng ("Hệ số K" gộp trên "Đất ở | Đất NN") ghép lại."""
    for i, dong in enumerate(o[:200]):
        if any(re.search(r'\d[.,]\d', x) for x in dong):
            continue                                    # dòng có số lẻ là dòng số liệu, không phải tiêu đề
        vai = {c: v for c, v in ((c, _vai_cot(x)) for c, x in enumerate(dong)) if v}
        nhom = [c for c, v in vai.items() if v in TEN_NHOM]
        co_k = 'k' in vai.values()
        if not co_k and len(nhom) < 2:
            continue
        if co_k and len(nhom) < 2 and i + 1 < len(o) and not any(re.search(r'\d[.,]\d', x) for x in o[i + 1]):
            duoi = {c: v for c, v in ((c, _vai_cot(x)) for c, x in enumerate(o[i + 1])) if v}
            nd = {c: v for c, v in duoi.items() if v in TEN_NHOM}
            if len(nd) >= 2:
                gop = {c: v for c, v in vai.items() if v != 'k'}
                gop.update(nd)
                for c, v in duoi.items():
                    if v in ('db', 'ld', 'vt', 'td', 'stt', 'gc'):
                        gop.setdefault(c, v)
                return i + 1, gop
        if len(nhom) >= 2:
            vai = {c: v for c, v in vai.items() if v != 'k'}
        return i, vai
    return -1, {}


def _dong_tu_bang(o: list, i0: int, vai: dict, dia_ban: str) -> list:
    kq = []
    xa = dia_ban
    cot = {v: c for c, v in sorted(vai.items(), reverse=True)}
    nhom_cot = [(c, v) for c, v in sorted(vai.items()) if v in TEN_NHOM]
    ld_truoc = ''
    for dong in o[i0 + 1:]:
        dong = [_o(x) for x in dong]
        co_chu = [x for x in dong if x]
        if not co_chu:
            continue
        if len(co_chu) == 1 or (len(co_chu) == 2 and re.fullmatch(r'[\dIVXLC]+\.?', co_chu[0])):
            t = _tieu_de_xa(' '.join(co_chu))
            if t:
                xa = t
                continue
            n = nhom_tu_chu(co_chu[-1])
            if n and not doc_he_so(co_chu[-1]):
                ld_truoc = n
                continue
        lay = (lambda k: dong[cot[k]] if k in cot and cot[k] < len(dong) else '')
        db = lay('db')
        if db and not doc_he_so(db):
            xa = db if not _tieu_de_xa(db) else _tieu_de_xa(db)
        ld = chuan_loai_dat(lay('ld')) or ld_truoc
        vt, td, gc = chuan_vi_tri(lay('vt')), lay('td'), lay('gc')
        if lay('vt') and not vt and not td:
            td = lay('vt')                          # "khu vực trung tâm…" không có số: ghi như tuyến / khu vực
        if nhom_cot:
            for c, n in nhom_cot:
                k = doc_he_so(dong[c]) if c < len(dong) else ''
                if k:
                    kq.append(chuan_dong(dict(dia_ban=xa, loai_dat=n, vi_tri=vt, tuyen_duong=td, he_so=k, ghi_chu=gc)))
        else:
            k = doc_he_so(lay('k'))
            if k:
                kq.append(chuan_dong(dict(dia_ban=xa, loai_dat=ld, vi_tri=vt, tuyen_duong=td, he_so=k, ghi_chu=gc)))
    return kq


def _so_cuoi(dong: str) -> str:
    """Hệ số trên một dòng chữ: bỏ STT đầu dòng, mã / chữ vị trí, khu vực; lấy số có phần lẻ cuối cùng, không có thì số cuối."""
    s = re.sub(r'^\s*[\dIVXLC]{1,4}\s*[.)]\s+', '', dong)
    s = re.sub(r'(?i)\b(?:v[iị]\s*tr[ií]|vt|khu\s*v[ựu]c|kv)\s*[:.]?\s*\d+', ' ', s)
    s = re.sub(r'(?i)\b(?:mt|[tk][1-3])\b', ' ', s)
    s = re.sub(r'\d{1,4}/\d{4}', ' ', s)
    so = _RE_SO.findall(s)
    if not so:
        return ''
    le = [x for x in so if re.search(r'[.,]', x)]
    return doc_he_so((le or so)[-1])


def _dong_tu_chu(o: list, dia_ban: str) -> list:
    kq = []
    xa, ld_truoc = dia_ban, ''
    for dong in o:
        chu = _o(' '.join(str(x) for x in dong))
        if not chu:
            continue
        t = _tieu_de_xa(chu)
        if t:
            xa = t
            continue
        b = bo_dau(chu)
        if 'he so' not in b and (re.search(r'\d{1,3}(?:[.,]\d{3})+(?!\d)', chu) or re.search(r'\bdong\b|\bm2\b|m²', b)):
            continue                                # dòng giá tiền / diện tích ("1.500.000 đồng/m2"), không phải hệ số
        k = _so_cuoi(chu)
        goc = re.sub(r'^\s*[\dIVXLC]{1,4}\s*[.)]\s+', '', chu)
        n = nhom_tu_chu(re.split(r'\d', goc)[0])
        if n:
            ld_truoc = n
        if not k:
            continue
        if 'he so' not in b and not n and not ld_truoc and not chuan_vi_tri(chu):
            continue                                # dòng có số nhưng không nói gì về hệ số / loại đất / vị trí
        vt = chuan_vi_tri(chu) if re.search(r'(?i)v[iị]\s*tr[ií]|\bvt|khu\s*v[ựu]c|\bkv|\bmt\b|\b[tk][1-3]\b|m[ặa]t\s*ti[ềe]n', chu) \
            else ''
        kq.append(chuan_dong(dict(dia_ban=xa, loai_dat=n or ld_truoc, vi_tri=vt, he_so=k)))
    return kq


def phan_tich(o: list, dia_ban: str = '') -> list:
    """Các dòng ô chữ (bảng Excel / Word / PDF, hoặc dòng nhận dạng chữ đã tách cột) -> [dòng hệ số K]. dia_ban: địa bàn mặc
    định khi văn bản không ghi."""
    o = [[_o(x) for x in (d if isinstance(d, (list, tuple)) else [d])] for d in o]
    i, vai = _tim_tieu_de(o)
    kq = _dong_tu_bang(o, i, vai, dia_ban) if i >= 0 else []
    if not kq:
        kq = _dong_tu_chu(o, dia_ban)
    # bỏ dòng trùng hệt
    da, ra = set(), []
    for r in kq:
        k = tuple(r[t] for t in TRUONG)
        if k not in da:
            da.add(k)
            ra.append(r)
    return ra


def tach_o(chu: str) -> list:
    """Chữ dán / chữ nhận dạng -> dòng ô: tách cột ở Tab hoặc từ 2 dấu cách."""
    kq = []
    for d in str(chu or '').splitlines():
        if not d.strip():
            continue
        kq.append([x.strip() for x in re.split(r'\t|\s{2,}', d.strip()) if x.strip()])
    return kq


def tim_van_ban(o: list) -> str:
    for d in o[:60]:
        chu = ' '.join(str(x) for x in (d if isinstance(d, (list, tuple)) else [d]))
        m = _RE_SO_VB.search(chu)
        if m:
            return f'Quyết định số {m.group(1).replace("QD", "QĐ").replace("qd", "QĐ")}'
    return ''


def doc_chu(chu: str, dia_ban: str = '') -> tuple:
    """Chữ dán (hoặc chữ nhận dạng) -> (dòng, văn bản)."""
    o = tach_o(chu)
    return phan_tich(o, dia_ban), tim_van_ban(o)


# ---------------------------------------------------------------- mẫu Phụ lục I QĐ 03/2026 (mỗi xã một bảng, mỗi TT một dòng)
_RE_BANG = re.compile(r'^\s*Bảng\s+(\d+)\s*\.\s*((?:Xã|Phường|Đặc khu|Thị trấn)\s+.+?)\s*$')
# hệ số trong Phụ lục I luôn ghi 2 chữ số lẻ (1,24 / 1,30): số 1 chữ số lẻ cuối dòng là chữ của tên đoạn ("Khu tái định cư 3,8 ha")
_RE_SO_CUOI = re.compile(r'((?:\s+|^)\d,\d{2})+\s*$')
_RE_DOAN = re.compile(r'(?:trực tiếp ra|thông ra)\s+(.+?)(?:\s+đoạn từ\s+(.+?)\s+đến\s+(.+?))?\s+có hiện trạng', re.S)


def la_phu_luc(trang: list) -> bool:
    """Chữ các trang có dạng Phụ lục I (tiêu đề "Bảng N. Xã / Phường …" + "Hệ số điều chỉnh")?"""
    co_bang = co_he_so = False
    for t in trang:
        if not co_bang and any(_RE_BANG.match(d) for d in t.splitlines()):
            co_bang = True
        if not co_he_so and 'he so dieu chinh' in bo_dau(t):
            co_he_so = True
        if co_bang and co_he_so:
            return True
    return False


def _cot_bang(dau: str) -> list:
    b = bo_dau(dau)
    if 'thi truong dat o' in b or ('dat o' in b and 'thuong mai' in b):
        return ['dat_o', 'tmdv', 'sxkd']
    if 'nong nghiep' in b:
        return ['nn']
    return []


def _hang_bang(khoi: list, so_cot: int, canh_bao: list, ten: str) -> list:
    """Dòng chữ của một bảng -> [dict(tt, chu, so)] (số TT tăng dần từ 1; hệ số ở cuối dòng, có thể sang dòng sau)."""
    hang, cho_tt, cur = [], 1, None
    for d in khoi:
        s = d.strip()
        m = re.match(r'(\d{1,4})(?:\s+(.*))?$', s)
        if m and int(m.group(1)) == cho_tt and not re.fullmatch(r'\d,\d{2}', s):
            if cur is not None and len(cur['so']) < so_cot:
                canh_bao.append(f'{ten}: TT {cur["tt"]} thiếu hệ số.')
            cur = dict(tt=cho_tt, chu='', so=[])
            hang.append(cur)
            cho_tt += 1
            s = m.group(2) or ''
        if cur is None or len(cur['so']) >= so_cot:
            continue
        mc = _RE_SO_CUOI.search(s)
        if mc:
            cur['so'] += re.findall(r'\d,\d{2}', mc.group(0))
            s = s[:mc.start()]
        cur['chu'] = (cur['chu'] + ' ' + s).strip()
    if cur is not None and len(cur['so']) < so_cot:
        canh_bao.append(f'{ten}: TT {cur["tt"]} thiếu hệ số.')
    return hang


def doc_phu_luc(trang: list, ds_xa=None) -> tuple:
    """Chữ từng trang (pypdf / nhận dạng chữ) của Phụ lục I.1 / I.2 -> (dòng hệ số, cảnh báo). ds_xa: chỉ lấy các xã / phường này
    (so tên bỏ chữ Xã / Phường: "Phường Trị An" = "Xã Trị An"); None / rỗng = mọi bảng."""
    can = [x for x in (ds_xa or ()) if _ten_xa(x)]
    dong_chu = []
    for t in trang:
        ls = (t or '').splitlines()
        while ls and (not ls[0].strip() or ls[0].strip().isdigit()):     # số trang đầu trang
            ls.pop(0)
        dong_chu += ls
    dau = [(i, m) for i, d in enumerate(dong_chu) for m in [_RE_BANG.match(d)] if m]
    kq, canh_bao = [], []
    for j, (i, m) in enumerate(dau):
        ten = re.sub(r'\s+', ' ', m.group(2)).strip()
        if can and not any(trung_dia_ban(ten, x) for x in can):
            continue
        khoi = dong_chu[i + 1:(dau[j + 1][0] if j + 1 < len(dau) else len(dong_chu))]
        cot = _cot_bang(' '.join(khoi[:30]))
        if not cot:
            canh_bao.append(f'Bảng {m.group(1)} ({ten}): không nhận ra cột hệ số.')
            continue
        hang = _hang_bang(khoi, len(cot), canh_bao, f'Bảng {m.group(1)} ({ten})')
        loai, muc = '', 0
        for h in hang:
            b = bo_dau(h['chu'])
            if 'cac tuyen duong' in b and 'dau noi truc tiep' in b:
                l = 'K' if 'khong dau noi' in b else 'T'
                muc = muc + 1 if l == loai else 1
                loai = l
                h['vi_tri'] = f'{l}{min(muc, 3)}'
                md = _RE_DOAN.search(h['chu'])
                h['doan'] = [x.strip() if x else '' for x in md.groups()] if md else [h['chu'][:120], '', '']
            else:
                loai, muc = '', 0
                h['vi_tri'] = 'MT'
                h['doan'] = None
        for k, h in enumerate(hang):
            if h['doan'] is None:                       # mặt tiền: tên đường / đoạn lấy theo dòng T1 kế tiếp
                sau = hang[k + 1] if k + 1 < len(hang) else None
                h['doan'] = sau['doan'] if sau and sau['vi_tri'] == 'T1' else [h['chu'], '', '']
            for c, so in zip(cot, h['so']):
                kq.append(chuan_dong(dict(dia_ban=ten, tt=h['tt'], loai_dat=c, vi_tri=h['vi_tri'], tuyen_duong=h['doan'][0],
                                          diem_dau=h['doan'][1], diem_cuoi=h['doan'][2], he_so=so)))
    return kq, canh_bao


def noi_bang_gia(dong: list, bang_gia=None) -> tuple:
    """Dòng có TT của các xã có trong bảng giá NQ 28: lấy tên xã, tên đường, điểm đầu / cuối, vị trí theo dòng cùng TT của bảng
    giá (tra theo chữ vị trí do chon_vi_tri_nq28 ghi). Trả (dòng, cảnh báo lệch tên đường / vị trí / thiếu TT)."""
    if bang_gia is None:
        from . import gia_dat_nq28 as nq
        bang_gia = nq.tat_ca()
    theo = {(_ten_xa(r['xa']), int(r['tt'])): r for r in bang_gia if str(r.get('tt', '')).isdigit()}
    canh_bao, lech = [], 0
    co = {}
    for r in dong:
        g = theo.get((_ten_xa(r['dia_ban']), r['tt'])) if r['tt'] != '' else None
        if g is None:
            continue
        co.setdefault(g['xa'], set()).add(r['tt'])
        # tên đường trong chữ PDF hay bị cắt / xuống dòng: chỉ báo khi lệch vị trí hoặc không chung từ nào (ngoài "đường")
        tu_a = set(re.findall(r'\w{3,}', bo_dau(g['ten_duong']))) - {'duong'}
        tu_b = set(re.findall(r'\w{3,}', bo_dau(r['tuyen_duong'])))
        if r['vi_tri'] != g['vi_tri'] or (tu_a and not tu_a & tu_b):
            lech += 1
            if lech <= 20:
                canh_bao.append(f'{g["xa"]} TT {r["tt"]}: văn bản ghi "{r["tuyen_duong"]}" {r["vi_tri"]}, bảng giá "{g["ten_duong"]}" '
                                f'{g["vi_tri"]}.')
        r.update(dia_ban=g['xa'], vi_tri=g['vi_tri'], tuyen_duong=g['ten_duong'], diem_dau=g['diem_dau'], diem_cuoi=g['diem_cuoi'])
    for xa, tts in co.items():
        thieu = sorted(int(r['tt']) for r in bang_gia if r['xa'] == xa and int(r['tt']) not in tts)
        if thieu:
            canh_bao.append(f'{xa}: {len(thieu)} TT của bảng giá chưa có hệ số ({", ".join(map(str, thieu[:10]))}'
                            f'{"…" if len(thieu) > 10 else ""}).')
    if lech > 20:
        canh_bao.append(f'… và {lech - 20} dòng lệch khác.')
    return dong, canh_bao


def _chu_trang_pdf(p: Path, bao=None, cho=None) -> list:
    from pypdf import PdfReader
    r = PdfReader(str(p))
    kq = []
    n = len(r.pages)
    for i, tr in enumerate(r.pages):
        if cho and cho():
            break
        if bao and (i % 5 == 0 or i + 1 == n):
            bao(i + 1, n)
        try:
            kq.append(tr.extract_text() or '')
        except Exception:
            kq.append('')
    return kq


def doc_file(file, dia_ban: str = '', bao=None, cho=None) -> tuple:
    """PDF mẫu Phụ lục I (có chữ hoặc bản quét - nhận dạng chữ): `doc_phu_luc` chỉ các xã trong dia_ban (nhiều xã cách nhau dấu
    phẩy; trống = các địa bàn của bảng giá đang dùng) rồi `noi_bang_gia`. File khác: Excel / Word / PDF / CSV qua
    nhap_don_gia.doc_bang + `phan_tich`; ảnh: nhận dạng chữ. bao(i, n) tiến độ, cho() True = dừng. Trả (dòng, văn bản, câu mô tả)."""
    from . import ocr
    from .nhap_don_gia import LoiPdfScan, doc_bang
    p = Path(file)
    if not p.is_file():
        raise LoiHeSoK(f'Không thấy file {p.name}.')
    tat_ca = dia_ban.strip() == '*'                     # 1.1.06: đọc mọi xã của file - màn hình cho người dùng tích chọn xã sau
    if tat_ca:
        ds_xa, dia_ban = None, ''
    elif dia_ban.strip():
        ds_xa = [x.strip() for x in dia_ban.split(',') if x.strip()]
    else:
        from . import gia_dat_nq28 as nq
        ds_xa = nq.ds_xa()
    trang, da_ocr = [], False
    if p.suffix.lower() == '.pdf':
        try:
            trang = _chu_trang_pdf(p, bao, cho)
        except Exception:
            trang = []
        if sum(len(t.strip()) for t in trang) < 50 * max(1, min(len(trang), 5)):       # PDF ảnh: nhận dạng chữ
            trang = []
            da_ocr = True
            try:
                for t in ocr.tung_trang(p, bao, cho):
                    trang.append('\n'.join(ocr.sua_so(x) for x in t.splitlines()))
                    if cho and cho():
                        break
            except ocr.DaHuy:
                pass
            except Exception as e:
                raise LoiHeSoK(str(e)) from None
        if la_phu_luc(trang):
            dong, cb = doc_phu_luc(trang, ds_xa)
            if not dong:
                raise LoiHeSoK(f'"{p.name}" không có bảng của {", ".join(ds_xa) if ds_xa else "xã / phường nào"} '
                               '(hoặc không đọc được hệ số).')
            dong, cb2 = noi_bang_gia(dong)
            vb = tim_van_ban([[t[:3000]] for t in trang[:3]])
            xa = ', '.join(dict.fromkeys(r['dia_ban'] for r in dong))
            cach = f'Phụ lục hệ số điều chỉnh: {xa}.' + (' Cần xem: ' + ' '.join(cb + cb2) if cb or cb2 else '')
            return dong, vb, cach
    scan = p.suffix.lower() in ocr.DUOI_ANH
    o = []
    if da_ocr:                                          # PDF quét đã nhận dạng nhưng không phải mẫu Phụ lục I
        o = tach_o('\n'.join(trang))
        cach = 'Nhận dạng chữ từ bản quét - kiểm tra lại từng hệ số trước khi lưu.'
    elif not scan:
        try:
            if p.suffix.lower() == '.txt':
                o = tach_o(p.read_text(encoding='utf-8', errors='replace'))
            else:
                o = doc_bang(p)
        except LoiPdfScan:
            scan = True
        except Exception as e:
            raise LoiHeSoK(str(e)) from None
    if scan:
        chu = []
        try:
            for trang in ocr.tung_trang(p, bao, cho):
                chu.append(trang)
                if cho and cho():
                    break
        except ocr.DaHuy:
            pass
        except Exception as e:
            raise LoiHeSoK(str(e)) from None
        o = tach_o('\n'.join(ocr.sua_so(x) for x in '\n'.join(chu).splitlines()))
        cach = 'Nhận dạng chữ từ bản quét - kiểm tra lại từng hệ số trước khi lưu.'
    elif not da_ocr:
        cach = 'Đọc bảng trong file.'
    dong = phan_tich(o, dia_ban)
    if not dong:
        raise LoiHeSoK(f'Không nhận ra bảng hệ số K trong "{p.name}". Cần dòng tiêu đề có "Hệ số" (hoặc các cột loại đất) và các '
                       'dòng hệ số dạng 1,2 / 1,15. Có thể dán chữ vào ô "Dán chữ" rồi sửa trên bảng.')
    return dong, tim_van_ban(o), cach

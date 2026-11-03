"""Khu vực giá nhà, công trình (1.0.57 - người dùng 04/11/2026: QĐ 18/2026 hợp nhất có Phụ lục I áp dụng khu vực 1, Phụ lục II áp dụng
khu vực 2 - cùng tên tài sản hai đơn giá; "xã có dự án thuộc khu vực nào thì áp phụ lục đó, phụ lục kia tự khóa ẩn"). Không Qt.

Lưu trong bảng tham_so của bộ đơn giá (đi theo bộ sang từng dự án khi áp bộ đơn giá; KHÔNG đổi lược đồ CSDL - file / phần mềm cũ mở được):
- 'KVMUC:<mã>' = khu vực của mục (dm_taisan) - mục không có dòng này dùng ở mọi khu vực;
- 'KVXA:<tên xã bỏ dấu>' = khu vực của xã / phường (tên đầy đủ ở cột ten) - đọc từ "Khu vực I bao gồm các phường, xã: …" của văn bản;
- 'KVTEN:<khu vực>' = tên phụ lục ("Phụ lục II") để hiện.
Dự án: khu vực = cai_dat KHU_VUC_GIA (người dùng chọn) hoặc khu vực của xã dự án (du_an.ten_dia_ban); không xác định được -> None
(không lọc - hiện đủ, nhắc chọn)."""
from __future__ import annotations

import re

from .lap_pa import bo_dau

TIEN_TO_MUC, TIEN_TO_XA, TIEN_TO_TEN = 'KVMUC:', 'KVXA:', 'KVTEN:'
KHOA_CAI_DAT = 'KHU_VUC_GIA'
LA_MA = {'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5'}
_RE_KV_DAU = re.compile(r'khu vuc\s+([ivx]+|\d+)\s+bao gom', re.I)
_RE_DS = re.compile(r'^[-–•+]?\s*(?:cac\s+)?(phuong|xa|thi tran|dac khu)\s*:\s*(.+)$')
_RE_PHU_LUC_KV = re.compile(r'PH[UỤ]\s*L[UỤ]C\s+([IVX]+)\b.*?KHU V[UỰ]C\s+(\d+)', re.I)


def so_kv(x: str) -> str:
    x = str(x or '').strip().lower()
    return LA_MA.get(x, x)


def khoa_xa(ten: str) -> str:
    """'Phường Bình Phước' / 'xã Bù Đăng' / 'Bù Đăng' -> 'bu dang' (bỏ cấp, bỏ dấu)."""
    k = ' '.join(bo_dau(ten).replace('.', ' ').split())
    return re.sub(r'^(phuong|xa|thi tran|dac khu|tt\.?|p\.?|x\.?)\s+', '', k).strip()


def doc_ds_xa(dong: list) -> dict:
    """{khu vực: [tên phường / xã]} từ phần ghi chú "Khu vực I bao gồm các phường, xã: - Các phường: a, b. - Các xã: c, d." của văn
    bản (dòng chữ hoặc ô bảng; danh sách xuống nhiều dòng nối lại)."""
    kq, kv, cap, gom = {}, None, '', []

    def chot():
        if kv and gom:
            ten = ' '.join(gom)
            for t in re.split(r'[,;]|\s+và\s+', ten):
                t = t.strip(' .:')
                if 2 <= len(t) <= 40 and not re.search(r'\d', t):
                    kq.setdefault(kv, []).append(t)
    for r in dong:
        o = [str(c) for c in (r if not isinstance(r, str) else [r]) if str(c or '').strip()]
        if len(o) >= 2 and gom:                         # dòng bảng (nhiều ô): hết danh sách xã
            chot()
            gom, cap = [], ''
        for s in (o[:1] if len(o) == 1 else o):
            s = ' '.join(s.split())
            k = bo_dau(s)
            m = _RE_KV_DAU.search(k)
            if m:
                chot()
                kv, gom, cap = so_kv(m.group(1)), [], ''
                continue
            if kv is None or re.fullmatch(r'[\d\W]+', s):     # số trang lẫn giữa danh sách (PDF)
                continue
            md = _RE_DS.match(k)
            if md:
                chot()
                gom, cap = [s[s.index(':') + 1:]], md.group(1)
                continue
            if gom and cap and not re.match(r'^(\d+\.|[a-z]\)|phu luc|ghi chu|stt)', k) and len(s) < 300 \
                    and not gom[-1].rstrip().endswith('.') and not re.search(r'\d{1,3}(?:[.,]\d{3})+', s):
                gom.append(s)                           # danh sách xuống dòng
                continue
            chot()
            gom, cap = [], ''
            if re.match(r'^(phu luc|\d+\.\s)', k):
                kv = None if re.match(r'^phu luc', k) else kv
    chot()
    return {k: list(dict.fromkeys(v)) for k, v in kq.items()}


def ten_phu_luc_kv(dong: list) -> dict:
    """{khu vực: 'Phụ lục II'} từ tiêu đề "PHỤ LỤC II … KHU VỰC 2" (một dòng hoặc hai dòng liền nhau)."""
    kq, truoc = {}, ''
    for r in dong:
        s = ' '.join(' '.join(str(c) for c in (r if not isinstance(r, str) else [r]) if c).split())
        m = re.match(r'(?i)^ph[uụ] l[uụ]c\s+([IVX]+)\s*$', s)
        if m:
            truoc = m.group(1).upper()
            continue
        mk = re.search(r'KHU VỰC\s+(\d+)', s)
        if mk and truoc:
            kq.setdefault(mk.group(1), f'Phụ lục {truoc}')
            truoc = ''
        elif s and not mk and truoc and len(s) > 120:
            truoc = ''
    return kq


# ---------------------------------------------------------------- đọc / ghi trong bộ đơn giá, dự án
def doc(con_hoac_ts) -> dict:
    """{'muc': {mã: kv}, 'xa': {khóa xã: (kv, tên)}, 'ten': {kv: tên phụ lục}} - từ kết nối hoặc dict tham_so {ma: gia_tri}."""
    kq = dict(muc={}, xa={}, ten={})
    if isinstance(con_hoac_ts, dict):
        rows = [(m, '', g) for m, g in con_hoac_ts.items() if str(m).startswith('KV')]
    else:
        try:
            rows = con_hoac_ts.execute("SELECT ma, ten, gia_tri FROM tham_so WHERE ma LIKE 'KV%:%'").fetchall()
        except Exception:                               # noqa: BLE001 - file không có tham_so
            return kq
    for ma, ten, gt in rows:
        ma, gt = str(ma), str(gt or '')
        if ma.startswith(TIEN_TO_MUC):
            kq['muc'][ma[len(TIEN_TO_MUC):]] = gt
        elif ma.startswith(TIEN_TO_XA):
            kq['xa'][ma[len(TIEN_TO_XA):]] = (gt, ten or ma[len(TIEN_TO_XA):])
        elif ma.startswith(TIEN_TO_TEN):
            kq['ten'][ma[len(TIEN_TO_TEN):]] = gt
    return kq


def co_khu_vuc(kv_dl: dict) -> bool:
    return len(set(kv_dl['muc'].values())) >= 2


def ten_kv(kv_dl: dict, kv: str) -> str:
    pl = kv_dl['ten'].get(kv) or ''
    return f'{pl} - Khu vực {kv}' if pl else f'Khu vực {kv}'


def ghi(con, muc: dict, xa: dict | None = None, ten: dict | None = None, can_cu: str = '') -> int:
    """Ghi (trong giao dịch + mo_khoa_danh_muc của nơi gọi): muc {mã: kv}, xa {kv: [tên xã]}, ten {kv: 'Phụ lục II'}. Trả số dòng."""
    n = 0
    for ma, kv in muc.items():
        con.execute('INSERT OR REPLACE INTO tham_so (ma, ten, gia_tri, dvt, can_cu, trang_thai) VALUES (?,?,?,?,?,?)',
                    (TIEN_TO_MUC + str(ma), 'Khu vực giá của mục', str(kv), '', can_cu, 'Khu vực giá'))
        n += 1
    for kv, ds in (xa or {}).items():
        for t in ds:
            con.execute('INSERT OR REPLACE INTO tham_so (ma, ten, gia_tri, dvt, can_cu, trang_thai) VALUES (?,?,?,?,?,?)',
                        (TIEN_TO_XA + khoa_xa(t), t, str(kv), '', can_cu, 'Khu vực giá'))
            n += 1
    for kv, t in (ten or {}).items():
        con.execute('INSERT OR REPLACE INTO tham_so (ma, ten, gia_tri, dvt, can_cu, trang_thai) VALUES (?,?,?,?,?,?)',
                    (TIEN_TO_TEN + str(kv), 'Phụ lục của khu vực', t, '', can_cu, 'Khu vực giá'))
        n += 1
    return n


def khu_vuc_cua_xa(kv_dl: dict, ten_xa: str) -> str | None:
    """Khu vực của xã / phường; tên địa bàn ghi dài ("xã Bù Đăng, tỉnh Đồng Nai", "Phường Bình Phước - Đồng Nai"): tên xã dài nhất
    có trong chuỗi (đủ chữ). Không thấy -> None."""
    x = kv_dl['xa'].get(khoa_xa(ten_xa))
    if x:
        return x[0]
    for phan in re.split(r'[,;\-–()/]', ten_xa or ''):
        x = kv_dl['xa'].get(khoa_xa(phan))
        if x:
            return x[0]
    k = ' ' + ' '.join(re.sub(r'[^\w ]', ' ', bo_dau(ten_xa or '')).split()) + ' '
    for kx in sorted(kv_dl['xa'], key=len, reverse=True):
        if len(kx) >= 4 and f' {kx} ' in k:
            return kv_dl['xa'][kx][0]
    return None


def khu_vuc_du_an(con, kv_dl: dict | None = None) -> str | None:
    """Khu vực giá của dự án: người dùng đã chọn (cai_dat KHU_VUC_GIA) hoặc theo xã dự án. None: bộ không chia khu vực / chưa xác định."""
    kv_dl = kv_dl if kv_dl is not None else doc(con)
    if not co_khu_vuc(kv_dl):
        return None
    try:
        r = con.execute('SELECT gia_tri FROM cai_dat WHERE ma = ?', (KHOA_CAI_DAT,)).fetchone()
        if r and str(r[0]).strip():
            return str(r[0]).strip()
    except Exception:                                   # noqa: BLE001 - file không có cai_dat (bộ đơn giá)
        pass
    try:
        r = con.execute('SELECT ten_dia_ban FROM du_an WHERE id = 1').fetchone()
    except Exception:                                   # noqa: BLE001
        r = None
    return khu_vuc_cua_xa(kv_dl, r[0]) if r and r[0] else None


def dat_khu_vuc_du_an(con, kv: str | None) -> None:
    from . import csdl
    with csdl.giao_dich(con):
        con.execute('INSERT OR REPLACE INTO cai_dat (ma, gia_tri) VALUES (?, ?)', (KHOA_CAI_DAT, str(kv or '')))
        csdl.ghi_nhat_ky(con, 'Chọn khu vực giá nhà, công trình', f'khu vực {kv}' if kv else 'theo xã dự án')


def dung_duoc(kv_dl: dict, ma: str, kv: str | None) -> bool:
    """Mục ma dùng được ở khu vực kv (mục không gắn khu vực: dùng mọi nơi; kv None: không lọc)."""
    if kv is None:
        return True
    k = kv_dl['muc'].get(ma)
    return k is None or k == kv

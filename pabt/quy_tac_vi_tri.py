"""Giá đất vị trí 2, 3, 4 ghi trong LỜI VĂN của Nghị quyết bảng giá đất (người dùng 30/10/2026: "Nghị quyết có ghi hướng dẫn, cách
thức tính và bổ sung vị trí 2, vị trí 3 hoặc vị trí 4 không nằm chung trong bảng đơn giá").

Nhiều tỉnh chỉ lập bảng giá VỊ TRÍ 1 theo tuyến đường; giá các vị trí sau ghi ở điều khoản, ví dụ:
  "Vị trí 2 bằng 70% giá đất vị trí 1; vị trí 3 bằng 50% giá đất vị trí 1"
  "Giá đất vị trí 2, vị trí 3, vị trí 4 lần lượt bằng 60%, 40%, 30% giá đất vị trí 1"
  "Vị trí 3 được tính bằng 80% giá đất vị trí 2, nhưng không thấp hơn 150.000 đồng/m²"
  "Vị trí 2 tính bằng hệ số 0,7 so với vị trí 1"
doc_quy_tac đọc các câu đó (theo loại đất của câu / tiêu đề đứng trước: "Đối với đất nông nghiệp:") -> [QuyTac]; ap_quy_tac dựng dòng
vị trí còn thiếu từ dòng vị trí 1 của bảng (giá nghìn đồng/m² như gia_dat_nq28). Không Qt. Người dùng xem / sửa / thêm quy tắc ở thẻ
"Cập nhật, bổ sung giá đất" của cửa sổ Bảng giá đất trước khi ghi."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .lap_pa import bo_dau

COT_GIA = ('dat_o', 'tmdv', 'sxkd', 'nn_cay', 'nn_rung_nts')        # = gia_dat_nq28.COT (không nhập để module không cần dữ liệu)
LOAI = {'': 'Mọi loại đất', 'dat_o': 'Đất ở', 'tmdv': 'Đất thương mại, dịch vụ', 'sxkd': 'Đất sản xuất, kinh doanh phi nông nghiệp',
        'phi_nn': 'Đất phi nông nghiệp không phải đất ở', 'nn': 'Đất nông nghiệp'}
COT_CUA_LOAI = {'': COT_GIA, 'dat_o': ('dat_o',), 'tmdv': ('tmdv',), 'sxkd': ('sxkd',), 'phi_nn': ('tmdv', 'sxkd'),
                'nn': ('nn_cay', 'nn_rung_nts')}
VI_TRI_TOI_DA = 5
_SO_CHU = {'nhat': 1, 'mot': 1, 'hai': 2, 'ba': 3, 'bon': 4, 'tu': 4, 'nam': 5}


@dataclass
class QuyTac:
    vi_tri: int                     # vị trí được tính (2..5)
    ty_le: Decimal                  # 0.7 = 70%
    so_voi: int = 1                 # tính theo giá vị trí này
    loai: str = ''                  # khóa LOAI ('' = mọi loại đất)
    toi_thieu: int = 0              # nghìn đồng/m²: giá không thấp hơn (0 = không có)
    cau: str = ''                   # câu trong văn bản (người dùng đối chiếu)

    @property
    def ma(self) -> str:
        return f'VT{self.vi_tri}'

    def mo_ta(self) -> str:
        pt = (self.ty_le * 100).normalize()
        chu = f'Vị trí {self.vi_tri} = {format(pt, "f").replace(".", ",")}% giá vị trí {self.so_voi}'
        if self.loai:
            chu += f' ({LOAI.get(self.loai, self.loai).lower()})'
        if self.toi_thieu:
            chu += ', không thấp hơn ' + f'{self.toi_thieu * 1000:,}'.replace(',', '.') + ' đồng/m²'
        return chu


def _loai(k: str) -> str:
    """Loại đất nhắc tới trong đoạn chữ không dấu ('' = không nói)."""
    if 'phi nong nghiep' in k:
        if 'thuong mai' in k and 'san xuat' not in k:
            return 'tmdv'
        if 'san xuat' in k and 'thuong mai' not in k:
            return 'sxkd'
        return 'phi_nn' if not re.search(r'\bdat o\b', k) else 'dat_o'
    if 'thuong mai' in k:
        return 'tmdv'
    if 'san xuat kinh doanh' in k:
        return 'sxkd'
    if re.search(r'nong nghiep|cay lau nam|cay hang nam|trong lua|\brung\b|nuoi trong thuy san', k):
        return 'nn'
    if re.search(r'\bdat o\b', k):
        return 'dat_o'
    return ''


def _chuan(chu: str) -> str:
    k = bo_dau(chu or '').lower()
    k = re.sub(r'\bvt\s*\.?\s*(\d)', r'vi tri \1', k)                       # "VT2", "vt.2"
    k = re.sub(r'vi tri\s+(?:so\s+)?(?:thu\s+)?(nhat|mot|hai|ba|bon|tu|nam)\b', lambda m: f'vi tri {_SO_CHU[m.group(1)]}', k)
    k = re.sub(r'vi tri\s+(?:so|thu)\s+(\d)', r'vi tri \1', k)
    return ' '.join(k.split())


_RE_TOKEN = re.compile(
    r'vi tri (?P<vt>\d)\b'
    r'|(?P<pt>\d{1,3}(?:[.,]\d+)?)\s*%'
    r'|(?:he so|bang)\s*(?P<hs>0[.,]\d+)'
    r'|(?P<hs2>0[.,]\d+)\s*lan\b')
_RE_TOI_THIEU = re.compile(r'khong (?:duoc )?thap hon\s*(?:muc\s*)?(?:gia\s*)?(?:toi thieu\s*)?(?:la\s*)?'
                           r'(?P<so>\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*(?P<dv>trieu|nghin|ngan)?\s*(?:dong|d\b|vnd)')


def _so(chu: str) -> Decimal | None:
    try:
        return Decimal(chu.replace(',', '.'))
    except InvalidOperation:
        return None


def _nghin(so: str, dv: str | None) -> int:
    """Số tiền trong câu "không thấp hơn …" -> nghìn đồng."""
    t = so
    if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+', t):                          # 150.000 / 1,200,000: dấu ngăn nghìn
        n = Decimal(re.sub(r'[.,]', '', t))
    else:
        n = _so(t) or Decimal(0)
    if dv == 'trieu':
        n *= 1000
    elif dv in ('nghin', 'ngan'):
        pass
    else:
        n /= 1000
    return int(n.to_integral_value(ROUND_HALF_UP))


def _cau(cac_dong) -> list:
    """Chuỗi các câu / vế câu (giữ thứ tự) từ dòng chữ của văn bản."""
    chu = '\n'.join(' '.join(str(x) for x in (d if isinstance(d, (list, tuple)) else [d]) if str(x or '').strip())
                    for d in cac_dong)
    ra = []
    for doan in re.split(r'\n+', chu):
        doan = doan.strip()
        if doan:
            ra += [x.strip() for x in re.split(r'(?<=[.;])\s+(?=\D)|;', doan) if x.strip()]
    return ra


def doc_quy_tac(cac_dong) -> list:
    """Quy tắc vị trí trong lời văn. cac_dong: chuỗi văn bản, danh sách dòng chữ, hoặc danh sách dòng ô (như nhap_don_gia.doc_bang)."""
    if isinstance(cac_dong, str):
        cac_dong = cac_dong.splitlines()
    ra, ngu_canh = [], ''
    for goc in _cau(cac_dong):
        k = _chuan(goc)
        tok = [(m.start(), m) for m in _RE_TOKEN.finditer(k)]
        co_quy_tac = False
        i = 0
        while i < len(tok):
            # nhóm vị trí được tính -> nhóm tỷ lệ -> vị trí gốc (không có thì vị trí 1)
            dich, so = [], []
            while i < len(tok) and tok[i][1].group('vt'):
                dich.append((tok[i][0], int(tok[i][1].group('vt'))))
                i += 1
            while i < len(tok) and not tok[i][1].group('vt'):
                m = tok[i][1]
                v = _so(m.group('pt')) / 100 if m.group('pt') else _so(m.group('hs') or m.group('hs2'))
                if v is not None:
                    so.append(v)
                i += 1
            if not dich:
                continue
            if not so:
                continue
            goc_vt, vi_tri_goc = 1, None
            if i < len(tok) and tok[i][1].group('vt'):
                vi_tri_goc = tok[i][0]
                goc_vt = int(tok[i][1].group('vt'))
                i += 1
            if len(so) == 1:
                so = so * len(dich)
            if len(so) != len(dich):
                continue
            truoc = k[:dich[0][0]]
            loai = _loai(truoc[-160:]) or ngu_canh
            sau = k[vi_tri_goc or dich[-1][0]:]
            mt = _RE_TOI_THIEU.search(sau[:200])
            toi_thieu = _nghin(mt.group('so'), mt.group('dv')) if mt else 0
            for (_, vt), tl in zip(dich, so):
                if not (goc_vt < vt <= VI_TRI_TOI_DA) or not (Decimal('0') < tl <= Decimal('1')):
                    continue
                ra.append(QuyTac(vt, tl.normalize(), goc_vt, loai, toi_thieu, goc[:300]))
                co_quy_tac = True
        if not co_quy_tac:
            l = _loai(k)
            if l and len(k) < 140:                       # tiêu đề / câu dẫn ngắn: "b) Đối với đất nông nghiệp:" -> ngữ cảnh câu sau
                ngu_canh = l
            elif re.match(r'^(?:dieu \d+|chuong|phu luc|\d+\.)', k) and not l:      # sang điều / khoản khác: hết ngữ cảnh
                ngu_canh = ''
    return gon(ra)


def gon(ds: list) -> list:
    """Bỏ quy tắc trùng (vị trí, so với, loại) - giữ quy tắc đọc trước."""
    da, ra = set(), []
    for q in ds:
        khoa = (q.vi_tri, q.so_voi, q.loai)
        if khoa not in da:
            da.add(khoa)
            ra.append(q)
    return ra


def _ma_vt(chu: str) -> int:
    """Số vị trí của mã dòng bảng giá: 'VT2' -> 2; ''/'MT'/'1' -> 1 khi được coi là vị trí 1; khác (T1, K2, KV1-VT2…) -> 0."""
    t = str(chu or '').strip().upper()
    m = re.fullmatch(r'(?:VT|VỊ TRÍ|VI TRI)?\s*([1-5])', t)
    if m:
        return int(m.group(1))
    return 1 if t in ('', 'MT') else 0


def ap_quy_tac(dong: list, ds: list) -> tuple:
    """Dựng dòng vị trí còn thiếu theo quy tắc. Trả (dòng mới - giữ thứ tự, dòng sinh ra đứng sau dòng cùng tuyến, số dòng thêm).
    Một tuyến (xã, tên đường, điểm đầu, điểm cuối) chỉ có một dòng không ghi vị trí / 'MT' / 'VT1' và không có mức T / K -> dòng đó là
    vị trí 1 (đổi mã thành VT1). Vị trí đã có trong bảng giữ nguyên giá văn bản; dòng sinh ra có 'tinh_tu' (cách tính) và đánh dấu
    'sinh_tu_quy_tac'. Dòng sinh ra từ lần áp trước bị bỏ trước khi áp lại (sửa quy tắc rồi tính lại)."""
    dong = [r for r in dong if not r.get('sinh_tu_quy_tac')]
    if not ds:
        return [dict(r) for r in dong], 0
    nhom, thu_tu = {}, []
    for r in dong:
        k = (r.get('xa', ''), r.get('ten_duong', ''), r.get('diem_dau', ''), r.get('diem_cuoi', ''))
        if k not in nhom:
            nhom[k] = []
            thu_tu.append(k)
        nhom[k].append(dict(r))
    # vị trí nhỏ trước (chuỗi "vị trí 3 = 80% vị trí 2"); cùng vị trí: quy tắc riêng một loại đất trước quy tắc chung (cột đã có giá
    # thì quy tắc sau bỏ qua)
    theo_vt = sorted(ds, key=lambda q: (q.vi_tri, q.loai == '', q.so_voi))
    ra, them = [], 0
    for k in thu_tu:
        cac = nhom[k]
        ma = [_ma_vt(r.get('vi_tri')) for r in cac]
        if 0 in ma or ma.count(1) != 1:                   # có mức T / K, KV…, hoặc nhiều dòng "vị trí 1": không đoán
            ra += cac
            continue
        co = {vt: r for vt, r in zip(ma, cac)}
        goc = co[1]
        if str(goc.get('vi_tri') or '').upper() != 'VT1':
            goc['vi_tri'] = 'VT1'
        moi = {}
        for q in theo_vt:
            if q.vi_tri in co and q.vi_tri not in moi:     # văn bản đã ghi giá vị trí này trong bảng
                continue
            nguon = moi.get(q.so_voi) or co.get(q.so_voi)
            if nguon is None:
                continue
            r = moi.get(q.vi_tri)
            if r is None:
                r = dict(goc)
                for c in COT_GIA:
                    r[c] = 0
                r.update(vi_tri=q.ma, sinh_tu_quy_tac=True, tinh_tu=[], dieu_kien='')
                moi[q.vi_tri] = r
            for c in COT_CUA_LOAI.get(q.loai, COT_GIA):
                g = int(nguon.get(c) or 0)
                if not g or r.get(c):
                    continue
                v = int((Decimal(g) * q.ty_le).to_integral_value(ROUND_HALF_UP))
                r[c] = max(v, q.toi_thieu) if q.toi_thieu else v
            if q.mo_ta() not in r['tinh_tu']:
                r['tinh_tu'].append(q.mo_ta())
        ra += cac
        for vt in sorted(moi):
            r = moi[vt]
            if any(r.get(c) for c in COT_GIA):
                r['tinh_tu'] = '; '.join(r['tinh_tu'])
                ra.append(r)
                them += 1
    return ra, them


def tom_tat(ds: list) -> str:
    return '; '.join(q.mo_ta() for q in ds)

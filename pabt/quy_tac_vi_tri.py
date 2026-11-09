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


# ---------------------------------------------------------------- 1.0.81: toàn văn Nghị quyết bảng giá đất (Điều 1 -> 10)
TEN_FILE_TOAN_VAN = 'quy_tac_toan_van_nq28.json'          # trong thư mục máy
_RE_DIEU = re.compile(r'^dieu\s+(\d{1,2})\s*[.:]?\s*(.*)$')
_RE_KHOAN = re.compile(r'^(\d{1,2})\s*[.)]\s+(.*)$')
_RE_PT = re.compile(r'(\d{1,3}(?:[.,]\d+)?)\s*%')
_RE_HS = re.compile(r'he so\s*(?:dieu chinh\s*)?(?:la\s*|bang\s*)?(\d+[.,]\d+)')
_RE_MET = re.compile(r'(\d{1,3}(?:[.,]\d{3})*|\d+)\s*(?:m\b|met\b)')


def _dong_chu(cac_dong) -> list:
    if isinstance(cac_dong, str):
        cac_dong = cac_dong.splitlines()
    ra = []
    for d in cac_dong:
        chu = ' '.join(str(x) for x in (d if isinstance(d, (list, tuple)) else [d]) if str(x or '').strip())
        ra += [x.strip() for x in chu.splitlines() if x.strip()]
    return ra


def la_van_ban_toan_van_nq28(cac_dong) -> bool:
    """Toàn văn nghị quyết bảng giá đất: phần đầu (40 dòng) có "Nghị quyết" + "giá đất", thân có từ 5 điều khác nhau (Điều 1, 2…)."""
    dong = _dong_chu(cac_dong)
    dau = bo_dau(' '.join(dong[:40])).lower()
    if 'nghi quyet' not in dau or 'gia dat' not in dau:
        return False
    so = {m.group(1) for m in (_RE_DIEU.match(bo_dau(x).lower()) for x in dong) if m}
    return len(so) >= 5


def doc_toan_van_nghi_quyet(cac_dong, luu: bool = False) -> dict:
    """Bóc tách toàn văn: {'dieu': [{so, ten, khoan: [{so, noi_dung}]}], 'quy_tac': [{dieu, khoan, noi_dung, ty_le, he_so, khoang_cach_m,
    loai}], 'file'}. Quy tắc = khoản / đoạn có tỷ lệ %, hệ số hoặc khoảng cách (m) - phạm vi chiều sâu 50/100/200 m, giá đất tái định cư,
    trường hợp cụ thể Điều 8-10. luu: ghi <thư mục máy>/quy_tac_toan_van_nq28.json (người dùng đối chiếu, màn hình giá TĐC đọc lại)."""
    dieu, hien, khoan = [], None, None
    for goc in _dong_chu(cac_dong):
        k = bo_dau(goc).lower().strip()
        m = _RE_DIEU.match(k)
        if m:
            hien = dict(so=int(m.group(1)), ten=goc.split('.', 1)[-1].strip() if '.' in goc[:12] else goc, khoan=[])
            dieu.append(hien)
            khoan = None
            continue
        if hien is None:
            continue
        m = _RE_KHOAN.match(k)
        if m:
            khoan = dict(so=int(m.group(1)), noi_dung=goc)
            hien['khoan'].append(khoan)
        elif khoan is not None:
            khoan['noi_dung'] += ' ' + goc
        else:
            khoan = dict(so=0, noi_dung=goc)
            hien['khoan'].append(khoan)
    quy_tac = []
    for d in dieu:
        for kh in d['khoan']:
            for cau in re.split(r'(?<=[.;:])\s+(?=[a-zđ]\)|[-+])', kh['noi_dung']):
                k = bo_dau(cau).lower()
                pt = [x.replace(',', '.') for x in _RE_PT.findall(k)]
                hs = [x.replace(',', '.') for x in _RE_HS.findall(k)]
                met = [x.replace('.', '').replace(',', '') for x in _RE_MET.findall(k)]
                if not (pt or hs or met):
                    continue
                quy_tac.append(dict(dieu=d['so'], khoan=kh['so'], noi_dung=cau.strip()[:400], ty_le=pt, he_so=hs, khoang_cach_m=met,
                                    loai=_loai(k)))
    kq = dict(dieu=[dict(so=d['so'], ten=d['ten'][:200], so_khoan=len(d['khoan'])) for d in dieu], quy_tac=quy_tac, file='')
    if luu:
        import json
        from .may_chu import thu_muc_may
        f = thu_muc_may() / TEN_FILE_TOAN_VAN
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(dict(dieu=dieu, quy_tac=quy_tac), ensure_ascii=False, indent=1), encoding='utf-8')
        kq['file'] = str(f)
        from .quan_tri_bo import bao_doi
        bao_doi()                                       # 1.0.82: Bảng tính giá đất đang mở dùng ngay hệ số của toàn văn
    return kq


def so_dieu_toan_van_da_luu() -> int:
    """Số điều của toàn văn đã lưu trên máy (0: chưa lưu / file hỏng)."""
    import json
    from .may_chu import thu_muc_may
    try:
        return len(json.loads((thu_muc_may() / TEN_FILE_TOAN_VAN).read_text(encoding='utf-8')).get('dieu') or [])
    except (OSError, ValueError, AttributeError):
        return 0


def doc_quy_tac_toan_van_da_luu() -> list:
    """Quy tắc toàn văn đã lưu trên máy (doc_toan_van_nghi_quyet(luu=True)); chưa có / hỏng: []."""
    import json
    from .may_chu import thu_muc_may
    f = thu_muc_may() / TEN_FILE_TOAN_VAN
    try:
        return list(json.loads(f.read_text(encoding='utf-8')).get('quy_tac') or [])
    except (OSError, ValueError, AttributeError):
        return []


# ---------------------------------------------------------------- 1.0.81: giá đất tái định cư + trường hợp cụ thể Điều 8-10
# Mọi tỷ lệ / hệ số đọc từ gói dữ liệu (gia_dat_qd03.json, khóa quy_tac_nq28) - không viết cố định quy tắc pháp lý vào mã.
class LoiQuyTac(ValueError):
    """Thiếu số liệu / trường hợp không có trong gói quy tắc (thông báo tiếng Việt)."""


def _khoan_dieu(can_cu: str):
    m = re.search(r'Kho\u1ea3n\s+(\d+)\s+\u0110i\u1ec1u\s+(\d+)', can_cu or '')
    return (int(m.group(2)), int(m.group(1))) if m else None


def _he_so_cua_cau(q: dict) -> list:
    """Hệ số trong một quy tắc toàn văn: 'hệ số 0,8' -> 0.8; '80%' -> 0.8 (bỏ 100% nói về phạm vi chung)."""
    ra = [Decimal(x) for x in q.get('he_so') or []]
    return ra or [Decimal(x) / 100 for x in q.get('ty_le') or []]


def quy_tac_nq28() -> dict:
    """Quy tắc NQ 28 của gói (gia_dat_qd03.json, khóa quy_tac_nq28) + (1.0.82) hệ số đọc từ TOÀN VĂN đã nạp trên máy: khoản của
    Điều 8 trùng căn cứ của trường hợp và có đúng một hệ số / tỷ lệ thì dùng số của văn bản, ghi 'nguon' (câu văn bản). Bản chép sâu."""
    import copy
    from .goi_gia_dat import du_lieu_goc
    q = du_lieu_goc().get('quy_tac_nq28')
    if not q:
        raise LoiQuyTac('Gói dữ liệu chưa có quy tắc NQ 28 (khóa quy_tac_nq28 của gia_dat_qd03.json).')
    q = copy.deepcopy(q)
    tv = doc_quy_tac_toan_van_da_luu()
    if not tv:
        return q
    theo = {}
    for x in tv:
        theo.setdefault((x.get('dieu'), x.get('khoan')), []).append(x)
    for x in q['truong_hop']:
        k = _khoan_dieu(x.get('can_cu'))
        ds = [(c, hs) for c in theo.get(k, ()) for hs in [_he_so_cua_cau(c)] if len(hs) == 1 and 0 < hs[0] <= 2]
        if len(ds) == 1:
            x['he_so'], x['nguon'] = str(ds[0][1][0]), ds[0][0].get('noi_dung', '')
    mt = q['nhieu_mat_tien']
    for c in theo.get(_khoan_dieu(mt.get('can_cu')), ()):
        hs = [h for h in _he_so_cua_cau(c) if 1 < h <= 2]
        if len(hs) == 2:
            mt['hai_duong_pl_vii'], mt['mot_pl_vii_va_duong_khac'] = str(max(hs)), str(min(hs))
            mt['nguon'] = c.get('noi_dung', '')
            break
    return q


def _D(x, ten: str) -> Decimal:
    if isinstance(x, Decimal):
        return x
    if x is None or str(x).strip() == '':
        raise LoiQuyTac(f'Thiếu {ten}.')
    try:
        from .tien import doc_so_vn
        return doc_so_vn(str(x)) if not isinstance(x, int) else Decimal(x)
    except (ValueError, ArithmeticError):
        raise LoiQuyTac(f'{ten}: "{x}" không phải số.') from None


def cac_truong_hop() -> list:
    """[(mã, tên, căn cứ)] mọi trường hợp tinh_gia_tai_dinh_cu_va_truong_hop_cu_the nhận (cho ô chọn của màn hình)."""
    q = quy_tac_nq28()
    tdc = q['tai_dinh_cu']
    ra = [('tdc_' + m['ma'], 'Tái định cư - ' + m['ten'], tdc['can_cu']) for m in tdc['muc']]
    ra += [('tdc_tmdv', 'Tái định cư - Đất thương mại, dịch vụ trong Khu TĐC', tdc['can_cu']),
           ('tdc_sxkd', 'Tái định cư - Đất SXKD trong Khu TĐC', tdc['can_cu']),
           ('chenh_lech_suat_tdc', 'Hỗ trợ chênh lệch suất tái định cư tối thiểu', tdc['can_cu'])]
    pv = q['pham_vi']
    ra += [(f'pham_vi_{n}_{ma}', f'Phạm vi - {"Đất nông nghiệp" if n == "nn" else "Đất phi nông nghiệp"} {ma}', pv['can_cu'])
           for n in ('nn', 'pnn') for ma in pv[n] if ma != 'san']
    mt = q['nhieu_mat_tien']
    ra += [('mat_tien_2_pl_vii', f'PNN từ 2 mặt tiền - ít nhất 2 đường Phụ lục VII (lớp {mt["lop_m"]} m)', mt['can_cu']),
           ('mat_tien_1_pl_vii', f'PNN từ 2 mặt tiền - 1 đường Phụ lục VII + đường khác (lớp {mt["lop_m"]} m)', mt['can_cu'])]
    ra += [(x['ma'], x['ten'], x['can_cu']) for x in q['truong_hop']]
    ra += [('giap_ranh', 'Đất giáp ranh tỉnh khác', q['giap_ranh']['can_cu']),
           ('thoi_han', f'Đất có thời hạn (quy đổi chuẩn {q["thoi_han"]["nam_chuan"]} năm)', q['thoi_han']['can_cu'])]
    return ra


def tinh_gia_tai_dinh_cu_va_truong_hop_cu_the(truong_hop: str, gia=None, **ts) -> dict:
    """Giá đất (đồng/m², Decimal, làm tròn tien.lam_tron 0 chữ số = ROUND_HALF_UP) theo trường hợp NQ 28. Trả {gia, he_so, giai_trinh,
    can_cu} (chenh_lech_suat_tdc: gia = số tiền hỗ trợ). gia: giá gốc đồng/m² (giá đường / giá đất ở TĐC / giá 70 năm…). Tham số riêng:
      tdc_gan_duong: khoang_cach_m, do_thi (bool) - xa hơn ngưỡng thì tính như KDC còn lại;
      chenh_lech_suat_tdc: dt_suat (m²), gia_tdc (đ/m²), tien_bt_dat_o (đ);
      pham_vi_<nn|pnn>_<mã>: san (đ/m², không bắt buộc - giá không thấp hơn sàn);
      nga_ba: gia_cac_duong (danh sách giá các đường, lấy cao nhất);
      giap_ranh: gia_tinh_ban (đ/m²);  thoi_han: so_nam."""
    from .tien import lam_tron
    q = quy_tac_nq28()
    th = str(truong_hop or '').strip()

    def ra(g, hs, giai, cc, nguon=''):
        return dict(gia=lam_tron(g, 0), he_so=hs, giai_trinh=giai, can_cu=cc,
                    nguon=('hệ số theo toàn văn đã nạp: "' + nguon[:160] + '"') if nguon else 'hệ số theo gói quy tắc')

    def vnd(x):
        return f'{lam_tron(x, 0):,}'.replace(',', '.')

    if th == 'chenh_lech_suat_tdc':
        dt, g, bt = _D(ts.get('dt_suat'), 'DT suất tối thiểu'), _D(ts.get('gia_tdc'), 'Giá đất TĐC'), _D(ts.get('tien_bt_dat_o'),
                                                                                                         'Tiền bồi thường đất ở')
        v = max(Decimal(0), dt * g - bt)
        return ra(v, None, f'max(0; {dt} m² x {vnd(g)} - {vnd(bt)}) = {vnd(v)} đồng', q['tai_dinh_cu']['can_cu'])
    if th == 'nga_ba':
        ds = [_D(x, 'Giá đường') for x in (ts.get('gia_cac_duong') or [])] + ([_D(gia, 'Giá đường')] if gia not in (None, '') else [])
        if not ds:
            raise LoiQuyTac('Ngã ba, ngã tư: nhập giá các đường.')
        x = next(x for x in q['truong_hop'] if x['ma'] == 'nga_ba')
        hs = Decimal(x['he_so'])
        return ra(max(ds) * hs, hs, f'Giá đường cao nhất {vnd(max(ds))} x {hs}', x['can_cu'])
    g = _D(gia, 'Giá gốc (đồng/m²)')
    if th.startswith('tdc_'):
        tdc = q['tai_dinh_cu']
        ma = th[4:]
        if ma in ('tmdv', 'sxkd'):
            hs = Decimal(tdc[ma])
            return ra(g * hs, hs, f'{hs} x giá đất ở TĐC {vnd(g)}', tdc['can_cu'])
        m = next((x for x in tdc['muc'] if x['ma'] == ma), None)
        if m is None:
            raise LoiQuyTac(f'Không có trường hợp tái định cư "{ma}".')
        if ma == 'gan_duong':
            kc = _D(ts.get('khoang_cach_m'), 'Khoảng cách tới đường Phụ lục VII (m)')
            nguong = Decimal(m['cach_do_thi_m'] if ts.get('do_thi') else m['cach_nong_thon_m'])
            if kc > nguong:
                m = next(x for x in tdc['muc'] if x['ma'] == 'con_lai')
                hs = Decimal(m['he_so'])
                return ra(g * hs, hs, f'Cách {kc} m > {nguong} m: {m["ten"]} - {hs} x {vnd(g)}', tdc['can_cu'])
        hs = Decimal(m['he_so'])
        return ra(g * hs, hs, f'{m["ten"]}: {hs} x {vnd(g)}', tdc['can_cu'])
    if th.startswith('pham_vi_'):
        nhom, _, ma = th[len('pham_vi_'):].partition('_')
        bang = q['pham_vi'].get(nhom) or {}
        if ma not in bang or ma == 'san':
            raise LoiQuyTac(f'Không có phạm vi "{ma}" cho nhóm "{nhom}".')
        hs = Decimal(bang[ma])
        v = g * hs
        giai = f'{ma}: {hs} x {vnd(g)}'
        if ts.get('san') not in (None, ''):
            san = _D(ts['san'], 'Giá sàn')
            if v < san:
                v, giai = san, giai + f' < sàn ({bang.get("san", "")}) {vnd(san)}: lấy sàn'
        return ra(v, hs, giai, q['pham_vi']['can_cu'])
    if th in ('mat_tien_2_pl_vii', 'mat_tien_1_pl_vii'):
        mt = q['nhieu_mat_tien']
        hs = Decimal(mt['hai_duong_pl_vii' if th == 'mat_tien_2_pl_vii' else 'mot_pl_vii_va_duong_khac'])
        return ra(g * hs, hs, f'Lớp {mt["lop_m"]} m đầu: {hs} x {vnd(g)} (phần sau lớp {mt["lop_m"]} m tính như thửa một mặt tiền)',
                  mt['can_cu'], mt.get('nguon', ''))
    if th == 'giap_ranh':
        gr = q['giap_ranh']
        ban = _D(ts.get('gia_tinh_ban'), 'Giá đất tỉnh giáp ranh')
        nguong, tl = Decimal(gr['nguong_chenh_lech']), Decimal(gr['ty_le_gia_tinh_ban'])
        if g > 0 and ban > g and (ban - g) / g > nguong:
            v = max(g, ban * tl)
            return ra(v, tl, f'Chênh lệch {lam_tron((ban - g) / g * 100, 1)}% > {nguong * 100}%: max({vnd(g)}; {tl} x {vnd(ban)})',
                      gr['can_cu'])
        return ra(g, Decimal(1), f'Chênh lệch không quá {nguong * 100}%: giữ giá {vnd(g)}', gr['can_cu'])
    if th == 'thoi_han':
        n = _D(ts.get('so_nam'), 'Thời hạn sử dụng (năm)')
        chuan = Decimal(q['thoi_han']['nam_chuan'])
        if n <= 0:
            raise LoiQuyTac('Thời hạn sử dụng phải lớn hơn 0.')
        return ra(g * min(n, chuan) / chuan, None, f'{vnd(g)} x {min(n, chuan)} / {chuan} năm', q['thoi_han']['can_cu'])
    x = next((x for x in q['truong_hop'] if x['ma'] == th), None)
    if x is None:
        raise LoiQuyTac(f'Không có trường hợp "{th}" trong gói quy tắc NQ 28.')
    hs = Decimal(x['he_so'])
    return ra(g * hs, hs, f'{x["ten"]}: {hs} x {vnd(g)}', x['can_cu'], x.get('nguon', ''))


# trường hợp dùng được trong bảng tính đơn giá đất (nhân vào giá bảng giá G): bỏ chênh lệch suất TĐC (số tiền hỗ trợ, không phải giá) và
# phạm vi (bảng tính đã có ô Vị trí, phạm vi theo gói)
def truong_hop_bang_tinh() -> list:
    return [x for x in cac_truong_hop() if x[0] != 'chenh_lech_suat_tdc' and not x[0].startswith('pham_vi_')]


THAM_SO_TRUONG_HOP = {'tdc_gan_duong': ('khoang_cach_m', 'Khoảng cách tới đường Phụ lục VII (m); thêm "đô thị" nếu ở đô thị'),
                      'nga_ba': ('gia_cac_duong', 'Giá các đường giao nhau (đ/m²), cách nhau ";"'),
                      'giap_ranh': ('gia_tinh_ban', 'Giá đất cùng loại của tỉnh giáp ranh (đ/m²)'),
                      'thoi_han': ('so_nam', 'Thời hạn sử dụng còn lại (năm)')}


def tinh_theo_tham_so_chu(truong_hop: str, gia, chu: str = '') -> dict:
    """Như tinh_gia_tai_dinh_cu_va_truong_hop_cu_the, tham số riêng gõ trong một ô chữ (THAM_SO_TRUONG_HOP)."""
    ts = {}
    ten = THAM_SO_TRUONG_HOP.get(truong_hop, ('', ''))[0]
    chu = str(chu or '').strip()
    if ten == 'gia_cac_duong':
        ts[ten] = [x.strip() for x in chu.split(';') if x.strip()]
    elif ten == 'khoang_cach_m':
        k = bo_dau(chu).lower()
        ts['do_thi'] = 'do thi' in k
        m = re.search(r'\d+(?:[.,]\d+)?', k)
        ts[ten] = m.group(0) if m else None
    elif ten:
        ts[ten] = chu or None
    return tinh_gia_tai_dinh_cu_va_truong_hop_cu_the(truong_hop, gia, **ts)

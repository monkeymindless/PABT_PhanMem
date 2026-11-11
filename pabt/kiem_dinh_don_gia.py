"""Kiểm định đơn giá sau khi quét / đọc file (1.1.03): bảng giá đất, đơn giá tài sản - cây trồng, mã băm đối chiếu gói.

Module lá, không Qt, không ghi gì: chỉ SOI số đã đọc và trả danh sách dòng cần người dùng đối chiếu bản gốc. Không sửa số, không đoán số.
Bắt được: giá vị trí sau cao hơn vị trí trước của cùng một đoạn đường, giá chéo cột (nông nghiệp >= đất ở…), giá ngoài bậc độ lớn
thường gặp / lẻ dưới 100 đồng (nhầm đơn vị, nhầm chữ số khi nhận dạng), giá đổi quá nhiều so với bảng đang dùng, cây cùng loại đường kính
lớn hơn mà đơn giá thấp hơn. KHÔNG bắt được: số đọc nhầm mà vẫn giữ đúng thứ tự và bậc độ lớn (3.200 đọc thành 3.800), cả một cột lệch
đều, tên đường / điểm đầu / điểm cuối sai, dòng bị bỏ sót, đơn vị nghìn / đồng khi bảng không ghi mà số nằm trong cả hai miền. Điểm tin cậy
là thước xếp thứ tự việc cần soát, không phải xác suất đúng.

Các chuỗi vị trí và thứ bậc cột dưới đây là PHÉP SOI (đo trên bảng NQ 28/2025 gắn sẵn, 1.127 dòng), không phải quy tắc pháp lý: văn bản
thật vẫn có ngoại lệ (đường N7 xã Phú Lý: mặt tiền 560 < đấu nối mức 1 690) - vì vậy dòng vi phạm chỉ bị đánh dấu để đối chiếu, không bị
loại. Chuỗi "T3 >= K1" KHÔNG đúng với NQ 28 (805 / 805 cặp ngược: K1 bằng T1) nên không soi."""
from __future__ import annotations

import hashlib
import hmac
import re
from decimal import Decimal, InvalidOperation

# ---------------------------------------------------------------- cờ
LOI_THU_TU_VI_TRI = 'LOI_THU_TU_VI_TRI'
LOI_CHEO_COT_LOAI_DAT = 'LOI_CHEO_COT_LOAI_DAT'
NGHI_NGO_DON_VI_HOAC_OCR = 'NGHI_NGO_DON_VI_HOAC_OCR'
LECH_SO_VOI_GOC = 'LECH_SO_VOI_GOC'
OCR_KEM_TIN_CAY = 'OCR_KEM_TIN_CAY'
LOI_THU_TU_KICH_THUOC = 'LOI_THU_TU_KICH_THUOC'
CAN_DOI_CHIEU_BAN_GOC = 'CAN_DOI_CHIEU_BAN_GOC'

# điểm trừ (thang 100) theo nhóm cờ; dòng 100 = xanh, 70-99 = vàng (xác nhận), < 70 = đỏ (đối chiếu bản gốc trước khi áp dụng)
TRU_BAT_BIEN = 40
TRU_DO_LON = 30
TRU_LECH_GOC = 20
TRU_OCR = 25
NGUONG_VANG = 70
NGUONG_OCR = 85

# chuỗi vị trí: giá không tăng dần theo chuỗi; cặp ngang: mức đấu nối >= mức không đấu nối cùng số
CHUOI_VI_TRI = (('MT', 'T1', 'T2', 'T3'), ('MT', 'K1', 'K2', 'K3'), ('VT1', 'VT2', 'VT3', 'VT4', 'VT5')) + \
    tuple(tuple(f'KV{k}-VT{v}' for v in (1, 2, 3, 4, 5)) for k in (1, 2, 3)) + \
    tuple(tuple(f'KV{k}-VT{v}' for k in (1, 2, 3)) for v in (1, 2, 3, 4, 5))
CAP_NGANG = (('T1', 'K1'), ('T2', 'K2'), ('T3', 'K3'))
# thứ bậc cột trên cùng một dòng: (cột cao, cột thấp, phải cao HẲN?)
COT_PHI_NN = ('dat_o', 'tmdv', 'sxkd')
COT_NN = ('nn_cay', 'nn_cln', 'nn_chn', 'nn_rung_nts', 'nn_rsx', 'nn_nts')
THU_BAC_COT = (('dat_o', 'tmdv', False), ('tmdv', 'sxkd', False), ('nn_cay', 'nn_rung_nts', False), ('nn_cln', 'nn_chn', False),
               ('nn_chn', 'nn_rsx', False)) + tuple((a, b, True) for a in COT_PHI_NN for b in COT_NN)
COT_GIA = COT_PHI_NN + COT_NN
TEN_COT = {'dat_o': 'đất ở', 'tmdv': 'thương mại, dịch vụ', 'sxkd': 'sản xuất kinh doanh', 'nn_cay': 'cây lâu năm, hằng năm',
           'nn_cln': 'cây lâu năm', 'nn_chn': 'cây hằng năm', 'nn_rung_nts': 'rừng sản xuất, thủy sản', 'nn_rsx': 'rừng sản xuất',
           'nn_nts': 'nuôi trồng thủy sản'}
# bậc độ lớn (đồng/m²): ngoài miền là nghi nhầm đơn vị / mất chữ số
GIA_DAT_TOI_THIEU = 10_000
GIA_DAT_NN_TOI_THIEU = 1_000                # đất rừng sản xuất nhiều tỉnh dưới 10.000 đ/m²
GIA_DAT_TOI_DA = 500_000_000
TY_LE_VI_TRI_TOI_THIEU = Decimal('0.05')    # vị trí sau dưới 5% vị trí đầu chuỗi: nghi mất một chữ số
LECH_GOC_DAT = Decimal('0.5')               # đổi quá 50% so với bảng đang dùng
LECH_GOC_TAI_SAN = Decimal('3')             # đổi quá 300% so với bộ đơn giá gốc


def _so(v) -> Decimal:
    """Số trong dòng đã đọc (int / str / Decimal) -> Decimal; trống / lỗi -> 0. Không float."""
    if v is None or v == '' or isinstance(v, bool):
        return Decimal(0)
    if isinstance(v, Decimal):
        return v
    if isinstance(v, int):
        return Decimal(v)
    try:
        if isinstance(v, float):
            return Decimal(str(v))
        from .tien import doc_so_vn
        return Decimal(doc_so_vn(str(v)))
    except (ValueError, ArithmeticError, InvalidOperation):
        return Decimal(0)


def _khoa_chu(s) -> str:
    """Khóa so tên: chữ thường, bỏ dấu câu, GIỮ DẤU tiếng Việt ("Sụ" khác "Sú", "Lộc Thành" khác "Lộc Thạnh")."""
    import unicodedata
    return ' '.join(re.sub(r'[\W_]+', ' ', unicodedata.normalize('NFC', str(s or '')).casefold()).split())


def _vn(x) -> str:
    from .tien import so_vn
    return so_vn(x)


def muc_tin_cay(diem: int) -> str:
    """'xanh' (100) / 'vang' (70-99: tích xác nhận) / 'do' (< 70: đối chiếu bản gốc)."""
    return 'xanh' if diem >= 100 else ('vang' if diem >= NGUONG_VANG else 'do')


class _Dong:
    __slots__ = ('i', 'co', 'ly_do')

    def __init__(self, i: int):
        self.i, self.co, self.ly_do = i, [], []

    def gan(self, co: str, ly_do: str) -> None:
        if co not in self.co:
            self.co.append(co)
        if ly_do not in self.ly_do:
            self.ly_do.append(ly_do)

    def ket_qua(self) -> dict:
        diem = 100
        if LOI_THU_TU_VI_TRI in self.co or LOI_CHEO_COT_LOAI_DAT in self.co or LOI_THU_TU_KICH_THUOC in self.co:
            diem -= TRU_BAT_BIEN
        if NGHI_NGO_DON_VI_HOAC_OCR in self.co:
            diem -= TRU_DO_LON
        if LECH_SO_VOI_GOC in self.co or CAN_DOI_CHIEU_BAN_GOC in self.co:
            diem -= TRU_LECH_GOC
        if OCR_KEM_TIN_CAY in self.co:
            diem -= TRU_OCR
        diem = max(0, diem)
        return {'i': self.i, 'diem_tin_cay': diem, 'muc': muc_tin_cay(diem), 'co': list(self.co), 'ly_do': list(self.ly_do)}


def _tong_hop(kq: list, don_vi_chac: bool = True) -> dict:
    n = len(kq)
    dem = {m: sum(1 for x in kq if x['muc'] == m) for m in ('xanh', 'vang', 'do')}
    diem = (sum(x['diem_tin_cay'] for x in kq) // n) if n else 0
    if n and not don_vi_chac:
        diem = min(diem, 90)
    can = [x for x in kq if x['muc'] != 'xanh']
    if not n:
        chu = 'Không có dòng nào để kiểm định.'
    elif not can and don_vi_chac:
        chu = f'Kiểm định {n} dòng: không thấy dòng bất thường (thứ tự vị trí, chéo cột, bậc độ lớn).'
    else:
        chu = (f'Kiểm định {n} dòng: {dem["do"]} dòng cần đối chiếu bản gốc, {dem["vang"]} dòng cần xác nhận'
               + ('' if don_vi_chac else '; đơn vị giá (nghìn đồng hay đồng) của bảng chưa rõ - xác nhận trước khi áp dụng') + '.')
    return {'dong': kq, 'can_xac_nhan': can, 'so_dong': n, 'so_xanh': dem['xanh'], 'so_vang': dem['vang'], 'so_do': dem['do'],
            'diem_tin_cay': diem, 'don_vi_chac': bool(don_vi_chac), 'chan_ap_dung': dem['do'] > 0, 'tom_tat': chu}


# ---------------------------------------------------------------- bảng giá đất
def _nhom_doan(dong: list) -> list:
    """Gom dòng theo đoạn đường (xã, tuyến, điểm đầu, điểm cuối) THEO THỨ TỰ FILE: cùng khóa mà mã vị trí lặp lại (hai tuyến trùng chữ,
    cùng TT hai tuyến - Long Bình TT 99) thì mở nhóm mới, không trộn hai đoạn. Trả [{mã vị trí: chỉ số dòng}]."""
    nhom, mo = [], {}
    for i, r in enumerate(dong):
        k = (_khoa_chu(r.get('xa')), _khoa_chu(r.get('ten_duong')), _khoa_chu(r.get('diem_dau')), _khoa_chu(r.get('diem_cuoi')))
        vt = str(r.get('vi_tri') or '').strip().upper()
        g = mo.get(k)
        if g is None or vt in g:
            g = {}
            mo[k] = g
            nhom.append(g)
        g[vt] = i
    return nhom


def kiem_dinh_bang_gia_dat(dong: list, goc: list | None = None, don_vi: str = 'nghin', don_vi_chac: bool = True) -> dict:
    """Soi bảng giá đất đã đọc (dòng kiểu gia_dat_nq28: xa, ten_duong, diem_dau, diem_cuoi, vi_tri, cột giá). don_vi: 'nghin' (giá lưu
    nghìn đồng/m² như văn bản) hoặc 'dong'. goc: bảng đang dùng (cùng đơn vị) để so mức đổi giá; dòng có khóa 'ocr_tin_cay' (0-100) thì
    xét thêm độ tin cậy nhận dạng. Trả {'dong': [{i, diem_tin_cay, muc, co, ly_do}], 'can_xac_nhan', 'so_do', 'so_vang', 'so_xanh',
    'diem_tin_cay' (cả bảng), 'chan_ap_dung' (có dòng đỏ), 'tom_tat'}. Không sửa `dong`."""
    he = Decimal(1000) if don_vi == 'nghin' else Decimal(1)
    kq = [_Dong(i) for i in range(len(dong))]
    gia = [{c: _so(r.get(c)) for c in COT_GIA} for r in dong]
    # 1. đơn điệu vị trí trong từng đoạn đường
    for g in _nhom_doan(dong):
        cap = [(a, b) for ch in CHUOI_VI_TRI for a, b in zip(ch, ch[1:])] + list(CAP_NGANG)
        for a, b in cap:
            if a not in g or b not in g:
                continue
            ia, ib = g[a], g[b]
            for c in COT_GIA:
                x, y = gia[ia][c], gia[ib][c]
                if x > 0 and y > x:
                    chu = f'{TEN_COT[c]}: {b} ({_vn(y)}) cao hơn {a} ({_vn(x)}) của cùng đoạn đường'
                    kq[ia].gan(LOI_THU_TU_VI_TRI, chu)
                    kq[ib].gan(LOI_THU_TU_VI_TRI, chu)
        for ch in CHUOI_VI_TRI:
            if ch[0] not in g:
                continue
            for b in ch[1:]:
                if b not in g:
                    continue
                for c in COT_GIA:
                    x, y = gia[g[ch[0]]][c], gia[g[b]][c]
                    if x > 0 and 0 < y < x * TY_LE_VI_TRI_TOI_THIEU:
                        kq[g[b]].gan(NGHI_NGO_DON_VI_HOAC_OCR, f'{TEN_COT[c]}: {b} ({_vn(y)}) chưa bằng 5% của {ch[0]} ({_vn(x)}) - '
                                     'nghi mất chữ số')
    # 2. thứ bậc cột, 3. bậc độ lớn, 4. so với bảng đang dùng, 5. độ tin cậy nhận dạng
    theo_goc = {}
    for r in goc or ():
        theo_goc[(_khoa_chu(r.get('xa')), _khoa_chu(r.get('ten_duong')), _khoa_chu(r.get('diem_dau')), _khoa_chu(r.get('diem_cuoi')),
                  str(r.get('vi_tri') or '').strip().upper())] = r
    for i, r in enumerate(dong):
        g = gia[i]
        for a, b, han in THU_BAC_COT:
            x, y = g[a], g[b]
            if x > 0 and y > 0 and (y >= x if han else y > x):
                kq[i].gan(LOI_CHEO_COT_LOAI_DAT, f'giá {TEN_COT[b]} ({_vn(y)}) {"không thấp hơn" if han else "cao hơn"} giá '
                          f'{TEN_COT[a]} ({_vn(x)}) trên cùng dòng - nghi lệch cột')
        for c in COT_GIA:
            v = g[c] * he
            if v <= 0:
                continue
            san = GIA_DAT_NN_TOI_THIEU if c in COT_NN else GIA_DAT_TOI_THIEU
            if v < san or v > GIA_DAT_TOI_DA:
                kq[i].gan(NGHI_NGO_DON_VI_HOAC_OCR, f'{TEN_COT[c]}: {_vn(v)} đồng/m² ngoài miền thường gặp '
                          f'({_vn(san)} - {_vn(GIA_DAT_TOI_DA)}) - nghi nhầm đơn vị hoặc sai chữ số')
            elif v % 100 != 0:
                kq[i].gan(NGHI_NGO_DON_VI_HOAC_OCR, f'{TEN_COT[c]}: {_vn(v)} đồng/m² lẻ dưới 100 đồng - nghi sai chữ số')
        if theo_goc:
            cu = theo_goc.get((_khoa_chu(r.get('xa')), _khoa_chu(r.get('ten_duong')), _khoa_chu(r.get('diem_dau')),
                               _khoa_chu(r.get('diem_cuoi')), str(r.get('vi_tri') or '').strip().upper()))
            for c in COT_GIA if cu else ():
                x, y = _so(cu.get(c)), g[c]
                if x > 0 and y > 0 and abs(y - x) > x * LECH_GOC_DAT:
                    kq[i].gan(LECH_SO_VOI_GOC, f'{TEN_COT[c]}: {_vn(y)} đổi quá 50% so với bảng đang dùng ({_vn(x)})')
        tc = r.get('ocr_tin_cay')
        if tc is not None and _so(tc) < NGUONG_OCR:
            kq[i].gan(OCR_KEM_TIN_CAY, f'nhận dạng chữ chỉ tin cậy {_vn(_so(tc))}%')
    return _tong_hop([x.ket_qua() for x in kq], don_vi_chac)


def doan_don_vi(so: list) -> tuple:
    """Bảng KHÔNG ghi đơn vị: đoán từ các giá đã đọc. Trả (đơn vị 'dong' | 'nghin', chắc chắn?).
    - có giá từ 1.000.000 trở lên: đồng/m² (chắc);
    - mọi giá chia hết cho 1.000 và từ 10.000 trở lên (dạng đơn giá ghi bằng đồng của xã nông thôn, vd. 500.000): giữ là đồng/m², KHÔNG
      nhân 1.000 - nhưng không chắc (bảng nghìn đồng toàn giá tròn triệu từ 10 triệu trở lên cũng có dạng này): người dùng xác nhận;
    - còn lại: nghìn đồng/m² như văn bản (không chắc khi không có giá nào dưới 10.000)."""
    so = [int(x) for x in so if x]
    if not so:
        return 'nghin', False
    if max(so) >= 1_000_000:
        return 'dong', True
    if all(x % 1000 == 0 and x >= 10_000 for x in so):
        return 'dong', False
    return 'nghin', min(so) < 10_000


CHU_CHUA_RO_DON_VI = ('CHƯA RÕ ĐƠN VỊ: bảng không ghi "nghìn đồng" hay "đồng/m²" - phần mềm tạm hiểu là {hieu} vì {ly_do}; đối chiếu một giá '
                      'với văn bản gốc trước khi ghi.')


def chu_don_vi_doan(don_vi: str) -> str:
    """Câu nhắc xác nhận đơn vị khi doan_don_vi không chắc."""
    if don_vi == 'dong':
        return CHU_CHUA_RO_DON_VI.format(hieu='đồng/m²', ly_do='mọi giá chia hết cho 1.000 và từ 10.000 trở lên')
    return CHU_CHUA_RO_DON_VI.format(hieu='nghìn đồng/m²', ly_do='không có giá nào từ 1.000.000 trở lên')


def chu_gia_le(so: list) -> str:
    """Bảng ghi đồng/m² mà có giá lẻ dưới 100 đồng (128.443): câu nhắc đối chiếu, '' nếu không có."""
    le = [int(x) for x in so if x and int(x) % 100]
    if not le:
        return ''
    return (f' Có {len(le)} giá lẻ dưới 100 đồng (ví dụ {_vn(le[0])}): nghi sai chữ số khi đọc - đối chiếu văn bản gốc.')


# ---------------------------------------------------------------- tiêu đề cột nông nghiệp
_TU_KHOA_NN = ('nong nghiep', 'trong lua', 'cay hang nam', 'cay lau nam', 'dat rung', 'rung san xuat', 'rung phong ho', 'thuy san')


def tieu_de_la_dat_nong_nghiep(chu: str) -> bool:
    """Tiêu đề bảng nói về đất nông nghiệp (không phải "phi nông nghiệp", không kèm "đất ở") - cột "Đơn giá" không rõ tên của bảng này
    không được hiểu là đất ở. Chữ "rừng" đứng riêng không tính (địa danh "Xã Rừng …")."""
    from .lap_pa import bo_dau
    k = ' '.join(bo_dau(str(chu or '')).split()).replace('phi nong nghiep', '')
    if re.search(r'\bdat o\b', k):
        return False
    return any(re.search(r'\b' + t + r'\b', k) for t in _TU_KHOA_NN)


# ---------------------------------------------------------------- đơn giá tài sản, cây trồng
_RE_NAM_THU = re.compile(r'^(.*?)\s*-\s*năm thứ\s*(\d+)\s*$', re.I)


def _gia_goc_bo_gan_san() -> dict:
    """{tên chuẩn: [đơn giá]} của bộ đơn giá đóng kèm (mở CHỈ ĐỌC - file gói không được bị ghi). Lỗi đọc: {}."""
    import sqlite3
    from . import tai_nguyen
    kq = {}
    try:
        p = tai_nguyen('bo_don_gia.sqlite')
        con = sqlite3.connect('file:' + str(p).replace('\\', '/').replace('?', '%3f').replace('#', '%23') + '?mode=ro', uri=True)
        try:
            for ten, gia in con.execute("SELECT ten, don_gia FROM dm_taisan WHERE don_gia IS NOT NULL AND don_gia <> ''"):
                g = _so_csdl(gia)
                if g > 0:
                    kq.setdefault(_khoa_chu(ten), []).append(g)
        finally:
            con.close()
    except Exception:                                   # noqa: BLE001 - thiếu bộ gắn sẵn: bỏ phép so với gốc
        return {}
    return kq


def _so_csdl(v) -> Decimal:
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return Decimal(0)


def kiem_dinh_don_gia_tai_san_cay(ds_muc: list, goc: dict | None = None) -> dict:
    """Soi danh sách mục đơn giá nhà / tài sản / cây trồng / vật nuôi đã đọc: mỗi mục có 'ten', 'don_gia' (số đã đọc - int / Decimal /
    chuỗi lưu CSDL). goc: {tên: đơn giá hoặc [đơn giá]} để so mức đổi; None = bộ đơn giá đóng kèm; {} = không so.
    - cây cùng loại ghi đường kính "(d >a-b cm)" / "Đk thân" (cay_trong.khoang_duong_kinh) hoặc "Năm thứ N": đường kính / năm lớn hơn mà
      đơn giá thấp hơn -> LOI_THU_TU_KICH_THUOC (cả hai mục của cặp);
    - đơn giá <= 0, có phần lẻ thập phân, hoặc đổi quá 300% so với gốc -> CAN_DOI_CHIEU_BAN_GOC.
    Không soi "chia hết cho 10": 4.537 / 5.667 đơn giá thật của bộ đóng kèm lẻ đồng (cây bưởi năm thứ 1: 313.119)."""
    from . import cay_trong
    kq = [_Dong(i) for i in range(len(ds_muc))]
    gia = []
    for m in ds_muc:
        v = m.get('don_gia') if hasattr(m, 'get') else m['don_gia']
        gia.append(_so_csdl(v) if isinstance(v, str) and re.fullmatch(r'-?\d+(\.\d+)?', v.strip() or 'x') else _so(v))
    ten = [str((m.get('ten') if hasattr(m, 'get') else m['ten']) or '') for m in ds_muc]
    # 1. đơn điệu theo đường kính / năm tuổi
    nhom = {}
    for i, t in enumerate(ten):
        if gia[i] <= 0:
            continue
        k = cay_trong.khoang_duong_kinh(t)
        if k is not None:
            dau = k.tu if k.tu is not None else Decimal(-1)
            nhom.setdefault(('dk', _khoa_chu(cay_trong.ten_loai_dk(t))), []).append((dau, i))
            continue
        m = _RE_NAM_THU.match(' '.join(t.split()))
        if m:
            nhom.setdefault(('nam', _khoa_chu(m.group(1))), []).append((Decimal(int(m.group(2))), i))
    for (loai, _k), ds in nhom.items():
        ds.sort(key=lambda x: (x[0], x[1]))
        for (da, ia), (db, ib) in zip(ds, ds[1:]):
            if db > da and gia[ib] < gia[ia]:
                cai = 'đường kính' if loai == 'dk' else 'năm tuổi'
                chu = f'"{ten[ib]}" ({_vn(gia[ib])}) {cai} lớn hơn mà đơn giá thấp hơn "{ten[ia]}" ({_vn(gia[ia])})'
                kq[ia].gan(LOI_THU_TU_KICH_THUOC, chu)
                kq[ib].gan(LOI_THU_TU_KICH_THUOC, chu)
    # 2. bậc độ lớn, so với gốc
    if goc is None:
        goc = _gia_goc_bo_gan_san()
    theo_goc = {}
    for k, v in (goc or {}).items():
        ds = v if isinstance(v, (list, tuple)) else [v]
        theo_goc.setdefault(_khoa_chu(k), []).extend(x for x in (_so(y) for y in ds) if x > 0)
    for i, t in enumerate(ten):
        g = gia[i]
        if g <= 0:
            kq[i].gan(CAN_DOI_CHIEU_BAN_GOC, 'chưa đọc được đơn giá (trống hoặc không phải số dương)')
            continue
        if g != g.to_integral_value():
            kq[i].gan(CAN_DOI_CHIEU_BAN_GOC, f'đơn giá {_vn(g)} có phần lẻ dưới 1 đồng - nghi nhầm dấu chấm / phẩy')
        cu = theo_goc.get(_khoa_chu(t))
        if cu:
            gan = min(cu, key=lambda x: abs(x - g))
            if abs(g - gan) > gan * LECH_GOC_TAI_SAN or g * (LECH_GOC_TAI_SAN + 1) < gan:
                kq[i].gan(CAN_DOI_CHIEU_BAN_GOC, f'đơn giá {_vn(g)} lệch quá 300% so với bộ đơn giá gốc ({_vn(gan)})')
    return _tong_hop([x.ket_qua() for x in kq])


# ---------------------------------------------------------------- mã băm đối chiếu gói
def niemphong_sha256(du_lieu: bytes) -> str:
    """Mã băm SHA-256 (chữ hex thường) của nội dung gói .larcgia / .pabtcfg - để hai máy so xem có cùng một gói. Đây là mã ĐỐI CHIẾU,
    không phải chữ ký số: ai sửa gói cũng tính lại được mã, nên mã chỉ có nghĩa khi nhận qua kênh tin cậy (người thẩm định đọc / gửi riêng)."""
    if isinstance(du_lieu, str):
        du_lieu = du_lieu.encode('utf-8')
    return hashlib.sha256(bytes(du_lieu)).hexdigest()


def kiem_niem_phong(du_lieu: bytes, ma_bam: str) -> bool:
    """Nội dung có đúng mã băm đã ghi không (so hằng thời gian, bỏ khoảng trắng / chữ hoa)."""
    return hmac.compare_digest(niemphong_sha256(du_lieu), re.sub(r'\s+', '', str(ma_bam or '')).lower())


def niem_phong_file(file) -> str:
    """Mã băm SHA-256 của cả file gói (đọc từng khối - file lớn không nạp hết vào bộ nhớ)."""
    h = hashlib.sha256()
    with open(file, 'rb') as f:
        for khoi in iter(lambda: f.read(1 << 20), b''):
            h.update(khoi)
    return h.hexdigest()

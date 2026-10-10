"""Quy tắc tính phương án bồi thường, hỗ trợ (chuyển nguyên từ file Excel PABT).

Mọi công thức nằm ở đây; màn hình chỉ gọi các hàm này.
  Mục 1 (đất):        thành tiền = ROUND(DT x giá bảng giá x hệ số K x tỷ lệ, LAMTRON)
  Mục 2, 3, 4:        thành tiền = ROUND(số lượng x đơn giá x tỷ lệ, LAMTRON)
  Mục 5 (thưởng):     tra biểu thưởng theo tổng mục 1-4, chỉ khi có bồi thường về đất (mục 1 > 0)
                      (Điều 15 QĐ 42/2025/QĐ-UBND)

Phương án một hộ được đọc vào bộ nhớ (PhuongAn) rồi mới tính, nên màn hình lập phương án
và báo cáo đối chiếu dùng chung đúng một hàm tính (tinh_pa) và một hàm kiểm tra (kiem_tra_pa).
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from decimal import Decimal

from .tien import D, KHONG, lam_tron, so_vn

TEN_MUC = {1: 'Bồi thường về đất', 2: 'Bồi thường, hỗ trợ về nhà và công trình xây dựng',
           3: 'Bồi thường, hỗ trợ về cây trồng', 4: 'Các chính sách hỗ trợ khác',
           5: 'Thưởng chấp hành bàn giao mặt bằng trước thời hạn'}
MA_ON_DINH = ('HT01', 'HT02', 'HT03', 'HT04', 'HT05', 'HT06', 'HT34', 'HT35')
MA_TDC = ('HT11', 'HT12', 'HT13')               # tái định cư: là điều kiện (suất TĐC), không phải dòng tiền
# thuê nhà chờ TĐC / tự lo chỗ ở: mức cơ bản (hộ đến N nhân khẩu, đồng/tháng) + mỗi nhân khẩu vượt (đồng/khẩu/tháng)
MA_THEO_NK = {'HT17': ('THUENHA_XA', 'THUENHA_NK_XA'), 'HT18': ('THUENHA_PHUONG', 'THUENHA_NK_PHUONG'),
              'HT23': ('THUENHA_XA', 'THUENHA_NK_XA'), 'HT24': ('THUENHA_PHUONG', 'THUENHA_NK_PHUONG')}
NK_CO_BAN = 4                                   # QĐ 42/2025: mức cơ bản cho hộ đến 4 nhân khẩu, cộng thêm từ khẩu thứ 5


def don_gia_theo_nhan_khau(bc, ma: str, nhan_khau, nguong: int | None = None) -> tuple:
    """Đơn giá một tháng (gộp một dòng) của khoản thuê nhà / tự lo chỗ ở theo số nhân khẩu:
    (đơn giá, mô tả). Hộ đến `nguong` khẩu: mức cơ bản; vượt: cơ bản + số khẩu vượt × mức mỗi khẩu."""
    co_ban_ma, them_ma = MA_THEO_NK[ma]
    co_ban, them = bc.so_ts(co_ban_ma), bc.so_ts(them_ma)
    if not co_ban:
        co_ban = D((bc.hotro.get(ma) or {}).get('don_gia') or 0)
    n = nguong or NK_CO_BAN
    nk = int(nhan_khau or 0)
    vuot = max(nk - n, 0)
    dg = co_ban + them * vuot
    if not nk:
        return dg, f'Mức hộ đến {n} nhân khẩu: {so_vn(co_ban)} đ/tháng (chưa nhập số nhân khẩu)'
    if not vuot:
        return dg, f'Hộ {nk} nhân khẩu: {so_vn(co_ban)} đ/tháng (mức hộ đến {n} nhân khẩu)'
    return dg, (f'Hộ {nk} nhân khẩu: {so_vn(co_ban)} đ/tháng ({n} nhân khẩu) + {vuot} khẩu × {so_vn(them)} đ '
                f'= {so_vn(dg)} đ/tháng')
NGUON_DM, NGUON_TD, NGUON_TAY = 'danh mục', 'tương đương', 'nhập tay'


def he_so(x) -> Decimal:
    """Ô tỷ lệ / hệ số để trống = 1 (giống IF(J="",1,J) trong Excel)."""
    return D(1) if x is None or str(x).strip() == '' else D(x)


def thanh_tien_dat(dien_tich, gia_bang_gia, he_so_k=1, ty_le=1, lamtron: int = -3) -> Decimal:
    don_gia_bt = D(gia_bang_gia) * he_so(he_so_k)
    return lam_tron(D(dien_tich) * don_gia_bt * he_so(ty_le), lamtron)


def thanh_tien_khoan(so_luong, don_gia, ty_le=1, lamtron: int = -3) -> Decimal:
    return lam_tron(D(so_luong) * D(don_gia) * he_so(ty_le), lamtron)


def muc_thuong(tong, bieu) -> Decimal:
    """LOOKUP(tong, THUONG_TU, THUONG_MUC): mức của nấc lớn nhất có 'từ' <= tổng; dưới nấc đầu = 0."""
    tong = D(tong)
    kq = KHONG
    for tu, muc in sorted(((D(a), D(b)) for a, b in bieu), key=lambda t: t[0]):
        if tong >= tu:
            kq = muc
    return kq


def don_gia_on_dinh(kg_gao, gia_gao, so_thang, muc=1) -> Decimal:
    """Hỗ trợ ổn định đời sống (Điều 19 NĐ 88/2024; Điều 10 QĐ 42/2025): 30 kg gạo x giá x số tháng x mức."""
    return D(kg_gao) * D(gia_gao) * D(so_thang) * D(muc)


def so_vi_tri(x) -> str:
    """'1' / 'VT 2' / 'ONT/VT 2: đường A' / 'vị trí 3' -> '1' / '2' / '2' / '3'; không có số -> ''."""
    s = str(x or '').strip()
    if s.isdigit():
        return s
    m = re.search(r'(?:VT|v[iị]\s*tr[ií])\s*[:.]?\s*(\d+)', s, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'\d+', s)
    return m.group(0) if m and len(s) <= 3 else ''


def nhom_han_muc(loai_dat: str) -> int:
    """Nhóm hạn mức giao đất NN (Điều 176 Luật Đất đai): 1 cây hằng năm, NTTS, làm muối; 2 cây lâu năm; 3 rừng."""
    ld = (loai_dat or '').upper()
    return 2 if ld == 'CLN' else 3 if ld in ('RSX', 'RPH', 'RDD') else 1


# ---------------------------------------------------------------- phương án một hộ trong bộ nhớ
@dataclass
class DongDat:
    """Một dòng mục 1 (bồi thường về đất)."""
    ma_thua: int | None = None
    loai_dat: str = ''
    nhom_dat: str = ''
    dien_tich: Decimal = KHONG
    vi_tri: str = ''
    gia_bang_gia: Decimal = KHONG
    he_so_k: Decimal = D(1)
    ty_le: Decimal = D(1)
    ghi_chu: str = ''
    thanh_tien_excel: Decimal | None = None
    id: int | None = None
    cong_thuc: str = ''             # công thức đã gõ ra diện tích (=20*10,55); trống = gõ số


@dataclass
class DongKhoan:
    """Một dòng mục 2 (nhà, công trình), 3 (cây trồng), 4 (hỗ trợ)."""
    muc: int
    ma: str = ''
    ten: str = ''
    dvt: str = ''
    so_luong: Decimal = KHONG
    don_gia: Decimal = KHONG
    ty_le: Decimal = D(1)
    quy_cach: str = ''              # mục 2, 3: quy cách; mục 4: căn cứ pháp lý
    ghi_chu: str = ''
    nguon_gia: str = NGUON_DM       # danh mục / tương đương / nhập tay
    ma_tuong_duong: str = ''
    can_cu_gia: str = ''
    thanh_tien_excel: Decimal | None = None
    id: int | None = None
    cach_tinh: str = ''             # mô tả cách tính in thay ĐVT / SL / ĐG / tỷ lệ ("4 nhân khẩu x 30kg gạo x 6 tháng x ...")
    cong_thuc: str = ''             # công thức đã gõ ra số lượng (=4,2*5,7); trống = gõ số


@dataclass
class ThongTinHo:
    ma_ho: int
    thu_tu: int = 0
    ho_ten: str = ''
    nhan_khau: int | None = None
    phai_di_chuyen: bool = False
    dt_nn_dang_dung: Decimal | None = None
    trang_thai: str = ''
    luu_luc: str | None = None
    tai_dinh_cu: str = ''           # đủ điều kiện TĐC theo khoản... Điều 111 / không đủ điều kiện / (trống: không có)


@dataclass
class PhuongAn:
    ho: ThongTinHo
    dat: list = field(default_factory=list)                                   # [DongDat]
    khoan: dict = field(default_factory=lambda: {2: [], 3: [], 4: []})        # {mục: [DongKhoan]}

    def dong_ho_tro(self, *ma) -> list:
        return [d for d in self.khoan[4] if d.ma in ma]

    @property
    def nhan_khau(self) -> int | None:
        """Nhân khẩu của hộ; chưa nhập thì lấy Số lượng ở dòng ổn định đời sống (như bản Excel)."""
        if self.ho.nhan_khau:
            return self.ho.nhan_khau
        for d in self.dong_ho_tro(*MA_ON_DINH):
            if d.so_luong > 0:
                return int(d.so_luong)
        return None


@dataclass
class BoiCanh:
    """Số liệu chung của dự án dùng khi tính / kiểm tra / gợi ý (đọc một lần)."""
    lamtron: int = -3
    bieu: list = field(default_factory=list)
    ts: dict = field(default_factory=dict)
    cap_dia_ban: str = ''
    ten_dia_ban: str = ''
    thua: dict = field(default_factory=dict)        # ma_thua -> dict(so_to, so_thua, loai_dat, dt_thu_hoi, nguon_goc, vi_tri, ma_ho)
    loai_dat: dict = field(default_factory=dict)    # mã -> nhóm (Đất ở / Nông nghiệp / ...)
    hotro: dict = field(default_factory=dict)       # mã HT -> dict(ten, dvt, don_gia, can_cu)
    nguong_nk: int = 4                              # số nhân khẩu của mức cơ bản thuê nhà / tự lo chỗ ở (cài đặt dự án)

    @classmethod
    def tu(cls, con) -> 'BoiCanh':
        """Bối cảnh của dự án: đọc một lần trên mỗi kết nối, dùng chung tới khi dữ liệu đổi (csdl.nho) - trước đây mỗi hộ / mỗi lần
        tính đọc lại toàn bộ bảng thửa, danh mục hỗ trợ (tự lập 600 hộ đọc 1.200 lần). Dùng chung: KHÔNG sửa đối tượng trả về."""
        from .csdl import nho
        return nho(con, ('BoiCanh', cls), lambda: cls._doc(con))

    @classmethod
    def _doc(cls, con) -> 'BoiCanh':
        ts = {r['ma']: r['gia_tri'] for r in con.execute('SELECT ma, gia_tri FROM tham_so')}
        try:
            lam = int(D(ts.get('LAMTRON'))) if ts.get('LAMTRON') not in (None, '') else -3
        except ValueError:
            lam = -3
        da = con.execute('SELECT cap_dia_ban, ten_dia_ban FROM du_an WHERE id = 1').fetchone()
        from .csdl import doc_cai_dat
        try:
            nguong = int(D(doc_cai_dat(con, 'NGUONG_NHAN_KHAU', str(NK_CO_BAN))))
        except ValueError:
            nguong = NK_CO_BAN
        return cls(nguong_nk=nguong or NK_CO_BAN, lamtron=lam, bieu=[(r['tu'], r['muc']) for r in con.execute('SELECT tu, muc FROM bieu_thuong')], ts=ts,
                   cap_dia_ban=da['cap_dia_ban'] if da else '', ten_dia_ban=da['ten_dia_ban'] if da else '',
                   thua={r['ma_thua']: dict(r) for r in con.execute('SELECT * FROM thua')},
                   loai_dat={r['ma'].upper(): r['nhom'] for r in con.execute('SELECT ma, nhom FROM dm_loaidat')},
                   hotro={r['ma']: dict(r) for r in con.execute('SELECT * FROM dm_hotro')})

    def thua_cua(self, ma_ho) -> list:
        """Các thửa (dict) của hộ theo thứ tự (thu_tu, ma_thua); chỉ mục theo hộ dựng một lần (trước đây mỗi hộ duyệt cả bảng thửa)."""
        cm = self.__dict__.get('_thua_theo_ho')
        if cm is None:
            cm = {}
            for t in sorted(self.thua.values(), key=lambda t: (t['thu_tu'], t['ma_thua'])):
                cm.setdefault(t['ma_ho'], []).append(t)
            self.__dict__['_thua_theo_ho'] = cm
        return cm.get(ma_ho, [])

    def muc_thuong(self, tong) -> Decimal:
        """muc_thuong(tong, self.bieu): biểu thưởng đổi sang số và sắp xếp MỘT lần (trước đây mỗi hộ một lần - 3.000 hộ ~0,1 giây)."""
        b = self.__dict__.get('_bieu_so')
        if b is None:
            b = self.__dict__['_bieu_so'] = sorted(((D(a), D(m)) for a, m in self.bieu), key=lambda t: t[0])
        tong, kq = D(tong), KHONG
        for tu, muc in b:
            if tong >= tu:
                kq = muc
        return kq

    def so_ts(self, ma) -> Decimal:
        v = self.ts.get(ma)
        try:
            return D(v) if v not in (None, '') else KHONG
        except ValueError:
            return KHONG

    @property
    def la_phuong(self) -> bool:
        return 'phường' in (self.cap_dia_ban or '').lower() or 'thị trấn' in (self.cap_dia_ban or '').lower()


def _dec_hoac_none(v):
    return D(v) if v not in (None, '') else None


def _tao_ho(h) -> ThongTinHo:
    k = h.keys()
    return ThongTinHo(ma_ho=h['ma_ho'], thu_tu=h['thu_tu'], ho_ten=h['ho_ten'], nhan_khau=h['nhan_khau'],
                      phai_di_chuyen=bool(h['phai_di_chuyen']), dt_nn_dang_dung=_dec_hoac_none(h['dt_nn_dang_dung']),
                      trang_thai=h['trang_thai'], luu_luc=h['luu_luc'] if 'luu_luc' in k else None,
                      tai_dinh_cu=(h['tai_dinh_cu'] or '') if 'tai_dinh_cu' in k else '')


def _dong_dat(r) -> DongDat:
    return DongDat(ma_thua=r['ma_thua'], loai_dat=r['loai_dat'], nhom_dat=r['nhom_dat'], dien_tich=D(r['dien_tich']),
                   vi_tri=r['vi_tri'], gia_bang_gia=D(r['gia_bang_gia']), he_so_k=he_so(r['he_so_k']),
                   ty_le=he_so(r['ty_le']), ghi_chu=r['ghi_chu'],
                   thanh_tien_excel=_dec_hoac_none(r['thanh_tien_excel']), id=r['id'],
                   cong_thuc=(r['cong_thuc'] or '') if 'cong_thuc' in r.keys() else '')


def _dong_khoan(r) -> DongKhoan:
    kk = r.keys()
    return DongKhoan(
        muc=r['muc'], ma=r['ma'], ten=r['ten'], dvt=r['dvt'], so_luong=D(r['so_luong']), don_gia=D(r['don_gia']),
        ty_le=he_so(r['ty_le']), quy_cach=r['quy_cach'], ghi_chu=r['ghi_chu'], nguon_gia=r['nguon_gia'] or NGUON_DM,
        ma_tuong_duong=r['ma_tuong_duong'], can_cu_gia=r['can_cu_gia'] if 'can_cu_gia' in kk else '',
        thanh_tien_excel=_dec_hoac_none(r['thanh_tien_excel']), id=r['id'],
        cach_tinh=(r['cach_tinh'] or '') if 'cach_tinh' in kk else '',
        cong_thuc=(r['cong_thuc'] or '') if 'cong_thuc' in kk else '')


def doc_phuong_an(con, ma_ho: int) -> PhuongAn:
    h = con.execute('SELECT * FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
    if h is None:
        raise KeyError(f'không có hộ mã {ma_ho}')
    pa = PhuongAn(ho=_tao_ho(h))
    for r in con.execute('SELECT * FROM ct_dat WHERE ma_ho = ? ORDER BY thu_tu, id', (ma_ho,)):
        pa.dat.append(_dong_dat(r))
    for r in con.execute('SELECT * FROM ct_khoan WHERE ma_ho = ? ORDER BY muc, thu_tu, id', (ma_ho,)):
        pa.khoan[r['muc']].append(_dong_khoan(r))
    return pa


def doc_tat_ca_phuong_an(con, ds_ma_ho=None) -> dict:
    """{ma_ho: PhuongAn} theo thứ tự hộ (thu_tu, ma_ho) - 3 câu truy vấn cho cả dự án thay vì 3 câu mỗi hộ (3.000 hộ: 9.000 câu).
    Cùng thứ tự dòng như doc_phuong_an. ds_ma_ho: chỉ các hộ này (None = tất cả)."""
    chon = None if ds_ma_ho is None else set(ds_ma_ho)
    kq = {}
    for h in con.execute('SELECT * FROM ho ORDER BY thu_tu, ma_ho'):
        if chon is None or h['ma_ho'] in chon:
            kq[h['ma_ho']] = PhuongAn(ho=_tao_ho(h))
    for r in con.execute('SELECT * FROM ct_dat ORDER BY ma_ho, thu_tu, id'):
        pa = kq.get(r['ma_ho'])
        if pa is not None:
            pa.dat.append(_dong_dat(r))
    for r in con.execute('SELECT * FROM ct_khoan ORDER BY ma_ho, muc, thu_tu, id'):
        pa = kq.get(r['ma_ho'])
        if pa is not None:
            pa.khoan[r['muc']].append(_dong_khoan(r))
    return kq


@dataclass
class Dong:
    muc: int
    stt: str
    ten: str
    dvt: str
    so_luong: Decimal
    don_gia: Decimal
    ty_le: Decimal
    thanh_tien: Decimal
    ma: str = ''
    ghi_chu: str = ''
    id: int = 0
    thanh_tien_excel: Decimal | None = None
    cach_tinh: str = ''


@dataclass
class KetQuaHo:
    ma_ho: int
    ho_ten: str = ''
    dong: list = field(default_factory=list)
    muc: dict = field(default_factory=lambda: {1: KHONG, 2: KHONG, 3: KHONG, 4: KHONG, 5: KHONG})

    @property
    def tong(self) -> Decimal:
        return sum(self.muc.values(), KHONG)

    @property
    def co_phuong_an(self) -> bool:
        return any(d.muc in (1, 2, 3, 4) for d in self.dong)


def mo_ta_thua(so_to, so_thua, loai_dat, cap_dia_ban, ten_dia_ban, vi_tri) -> str:
    """Mô tả thửa trên bản in (dòng 1.x):
    'Thửa đất số …, tờ bản đồ số …, loại đất …, xã (phường) … (Vị trí 1 / 2 / 3 / 4)'. Thiếu thông tin thì để dấu chấm chờ điền."""
    cho = '……'
    cap = (cap_dia_ban or '').strip().lower() or 'xã (phường)'
    s = (f'Thửa đất số {so_thua or cho}, tờ bản đồ số {so_to or cho}, loại đất {loai_dat or cho}, '
         f'{cap} {(ten_dia_ban or "").strip() or cho}')
    vt = ' '.join(str(vi_tri or '').split())
    so = so_vi_tri(vt)
    if vt and so and re.fullmatch(r'(?i)(vt|vị trí|vi tri)?\s*\d+', vt):
        s += f' (Vị trí {so})'
    elif vt:
        s += f' (Vị trí: {vt})'
    return s


def thanh_tien_dong_dat(d: DongDat, bc: BoiCanh) -> Decimal:
    return thanh_tien_dat(d.dien_tich, d.gia_bang_gia, d.he_so_k, d.ty_le, bc.lamtron)


def thanh_tien_dong(d: DongKhoan, bc: BoiCanh) -> Decimal:
    return thanh_tien_khoan(d.so_luong, d.don_gia, d.ty_le, bc.lamtron)


def tinh_pa(pa: PhuongAn, bc: BoiCanh) -> KetQuaHo:
    """Tính toàn bộ phương án của một hộ (không dùng thành tiền cũ của Excel)."""
    kq = KetQuaHo(ma_ho=pa.ho.ma_ho, ho_ten=pa.ho.ho_ten)
    for k, r in enumerate(pa.dat, start=1):
        tt = thanh_tien_dong_dat(r, bc)
        t = bc.thua.get(r.ma_thua) or {}
        # vị trí: mô tả đầy đủ của thửa (HS_KIEMKE) nếu có, không thì số vị trí ở mục 1
        ten = mo_ta_thua(t.get('so_to', ''), t.get('so_thua', ''), r.loai_dat, bc.cap_dia_ban, bc.ten_dia_ban,
                         r.vi_tri or t.get('vi_tri'))
        kq.dong.append(Dong(1, f'1.{k}', ten, 'm²', r.dien_tich, r.gia_bang_gia * r.he_so_k, r.ty_le, tt,
                            r.loai_dat, r.ghi_chu, r.id or 0, r.thanh_tien_excel))
        kq.muc[1] += tt
    for muc in (2, 3, 4):
        for k, r in enumerate(pa.khoan[muc], start=1):
            tt = thanh_tien_dong(r, bc)
            kq.dong.append(Dong(muc, f'{muc}.{k}', r.ten, r.dvt, r.so_luong, r.don_gia, r.ty_le, tt, r.ma, r.ghi_chu,
                                r.id or 0, r.thanh_tien_excel, r.cach_tinh))
            kq.muc[muc] += tt
    if kq.muc[1] > 0:
        kq.muc[5] = bc.muc_thuong(kq.muc[1] + kq.muc[2] + kq.muc[3] + kq.muc[4])
    return kq


def tinh_ho(con, ma_ho: int, bc: BoiCanh | None = None) -> KetQuaHo:
    return tinh_pa(doc_phuong_an(con, ma_ho), bc or BoiCanh.tu(con))


# ---------------------------------------------------------------- kết quả tính của cả dự án (dùng chung)
KHOA_KQ = ('KetQuaHo',)


def _tinh_kiem(pa: PhuongAn, bc: BoiCanh) -> tuple:
    return tinh_pa(pa, bc), kiem_tra_pa(pa, bc)


def ket_qua_ho(con) -> dict:
    """{ma_ho: (KetQuaHo, [cảnh báo kiem_tra_pa])} theo thứ tự hộ - tính một lần trên kết nối, dùng chung cho danh sách hộ
    (đối chiếu), các trang tổng hợp, In / Xuất, đợt trình, báo cáo... tới khi dữ liệu đổi (csdl.nho). Lưu phương án một hộ chỉ
    tính lại hộ đó (giu_ket_qua_ho). Trước đây mỗi lần tải lại / chuyển trang / mở hộp thoại tính lại cả 3.000 hộ.
    Dùng chung: KHÔNG sửa các đối tượng trả về."""
    from .csdl import nho

    def tao():
        bc = BoiCanh.tu(con)
        return {m: _tinh_kiem(pa, bc) for m, pa in doc_tat_ca_phuong_an(con).items()}
    return nho(con, KHOA_KQ, tao)


def ket_qua_ho_san(con):
    """ket_qua_ho nếu đang nhớ và còn đúng (không tính lại); không thì None."""
    from .csdl import _trang_thai
    bo = getattr(con, 'bo_nho', None)
    if bo is None or con.in_transaction:
        return None
    cu = bo.get(KHOA_KQ)
    return cu[1] if cu is not None and cu[0] == _trang_thai(con) else None


def giu_ket_qua_ho(con, ds_ma_ho, truoc) -> None:
    """Sau một lần ghi CHỈ đổi phương án của các hộ ds_ma_ho (bảng ho / ct_dat / ct_khoan của các hộ đó; bối cảnh đã giữ bằng
    csdl.giu_nho): tính lại riêng các hộ này trong ket_qua_ho thay vì bỏ cả bảng nhớ. truoc = csdl.trang_thai_nho trước khi ghi;
    có thay đổi khác chen vào thì thôi (lần sau tính lại cả dự án)."""
    from .csdl import _trang_thai
    bo = getattr(con, 'bo_nho', None)
    if bo is None or truoc is None or con.in_transaction:
        return
    cu = bo.get(KHOA_KQ)
    if cu is None or cu[0] != truoc:
        return
    bc = BoiCanh.tu(con)
    moi = dict(cu[1])                                   # bản mới: nơi đang giữ bản cũ không bị đổi giữa chừng
    for m in ds_ma_ho:
        if m in moi:
            moi[m] = _tinh_kiem(doc_phuong_an(con, m), bc)
    bo[KHOA_KQ] = (_trang_thai(con), moi)


def tinh_tat_ca(con) -> list:
    """[KetQuaHo] mọi hộ theo thứ tự (dùng chung ket_qua_ho - không sửa)."""
    return [k for k, _ in ket_qua_ho(con).values()]


def lamtron_du_an(con) -> int:
    return BoiCanh.tu(con).lamtron


def bieu_thuong(con) -> list:
    return [(r['tu'], r['muc']) for r in con.execute('SELECT tu, muc FROM bieu_thuong')]


# ---------------------------------------------------------------- quy tắc hỗ trợ (QĐ 42/2025/QĐ-UBND)
def la_giao_khoan(d: DongDat, bc: BoiCanh) -> bool:
    """Thửa đất giao khoán chính chủ chưa thanh lý: nguồn gốc đất (kiểm kê) hoặc ghi chú dòng mục 1 có chữ 'giao khoán'."""
    t = bc.thua.get(d.ma_thua) or {}
    return 'giao khoán' in (t.get('nguon_goc') or '').lower() or 'giao khoán' in (d.ghi_chu or '').lower()


def dt_nn_thu_hoi(pa: PhuongAn) -> Decimal:
    return sum((d.dien_tich for d in pa.dat if d.nhom_dat == 'Nông nghiệp'), KHONG)


def _dao_tao_theo_thua(d: DongKhoan) -> bool:
    """Dòng hỗ trợ đào tạo nhập theo từng thửa (đơn giá = giá đất, tỷ lệ 150% / 50%), không phải một dòng gộp theo hệ số."""
    return d.ty_le != 1 or d.ten.startswith('Thửa đất')


def de_xuat_dao_tao_pa(pa: PhuongAn, bc: BoiCanh, giao_khoan: bool = False):
    """Gợi ý HT09 (giao_khoan=False) / HT10 (True): (SL m², ĐG).
    SL = DT đất nông nghiệp thu hồi ở mục 1, trong hạn mức giao đất NN (Điều 176 Luật Đất đai);
    ĐG = round(hệ số x giá đất NN bình quân theo DT, 0) (Điều 13 QĐ 42/2025)."""
    hs = bc.so_ts('HS_DAOTAO_2' if giao_khoan else 'HS_DAOTAO')
    han_muc = {1: bc.so_ts('HM_CHN'), 2: bc.so_ts('HM_CLN'), 3: bc.so_ts('HM_RUNG')}
    s = {1: KHONG, 2: KHONG, 3: KHONG}
    dt = {1: KHONG, 2: KHONG, 3: KHONG}
    for r in pa.dat:
        if r.nhom_dat != 'Nông nghiệp' or r.gia_bang_gia == 0 or la_giao_khoan(r, bc) != giao_khoan:
            continue
        g = nhom_han_muc(r.loai_dat)
        s[g] += r.dien_tich * r.gia_bang_gia
        dt[g] += r.dien_tich
    sl = KHONG
    tien = KHONG
    for g in (1, 2, 3):
        if dt[g] > 0:
            d = min(dt[g], han_muc[g]) if han_muc[g] > 0 else dt[g]
            sl += d
            tien += s[g] / dt[g] * d
    if sl == 0:
        return KHONG, KHONG
    return sl, lam_tron(hs * tien / sl, 0)


def de_xuat_dao_tao(con, ma_ho: int, giao_khoan: bool = False):
    return de_xuat_dao_tao_pa(doc_phuong_an(con, ma_ho), BoiCanh.tu(con), giao_khoan)


@dataclass
class GoiY:
    so_luong: Decimal | None = None
    don_gia: Decimal | None = None
    dvt: str | None = None
    thong_bao: str = ''


def goi_y_khoan(pa: PhuongAn, bc: BoiCanh, ma: str) -> GoiY:
    """Số lượng / đơn giá gợi ý cho một khoản hỗ trợ (giống nút chọn khoản trên GIAO_DIEN của bản Excel).
    Người dùng vẫn sửa được; thong_bao cho biết còn thiếu số liệu gì."""
    g = GoiY()
    ts = bc.so_ts
    if ma in ('HT09', 'HT10'):
        sl, dg = de_xuat_dao_tao_pa(pa, bc, ma == 'HT10')
        g.dvt = 'm²'
        if sl > 0:
            g.so_luong, g.don_gia = sl, dg
        elif ma == 'HT10':
            g.thong_bao = ('Mục 1 chưa có thửa đất nông nghiệp giao khoán (hợp đồng chưa thanh lý): ghi "giao khoán" ở '
                           'nguồn gốc đất của thửa hoặc ghi chú dòng mục 1.')
        else:
            g.thong_bao = 'Mục 1 chưa có dòng đất nông nghiệp có giá bảng giá: nhập xong mục 1 rồi chọn lại khoản này.'
    elif ma in MA_ON_DINH:
        nk = pa.nhan_khau
        if nk:
            g.so_luong = D(nk)
        else:
            g.thong_bao = 'Chưa có số nhân khẩu của hộ: nhập ô Nhân khẩu ở đầu màn hình.'
    elif ma == 'HT08':
        g.don_gia = ts('VATNUOI') or None
    elif ma in ('HT14', 'HT15', 'HT16'):
        g.so_luong = D(1)
        g.don_gia = ts({'HT14': 'DICHUYEN_XA', 'HT15': 'DICHUYEN_TP', 'HT16': 'DICHUYEN_NGOAI'}[ma]) or None
    elif ma in ('HT17', 'HT18'):
        g.so_luong = ts('TULO_THANG') or D(6)
        g.don_gia, g.thong_bao = don_gia_theo_nhan_khau(bc, ma, pa.nhan_khau, bc.nguong_nk)
        g.dvt = 'Tháng'
    elif ma in ('HT21', 'HT22', 'HT25', 'HT26'):
        nk = pa.nhan_khau or 0
        if ma in ('HT21', 'HT22'):
            th = ts('TULO_THANG') or D(6)
        else:
            th = next((d.so_luong for d in pa.dong_ho_tro('HT23', 'HT24') if d.so_luong > 0), KHONG)
        if nk > 4 and th > 0:
            g.so_luong = (nk - 4) * th
        g.don_gia = ts('THUENHA_NK_XA' if ma in ('HT21', 'HT25') else 'THUENHA_NK_PHUONG') or None
        if not nk:
            g.thong_bao = 'Chưa có số nhân khẩu của hộ: nhập ô Nhân khẩu ở đầu màn hình.'
        elif nk <= 4:
            g.thong_bao = f'Hộ có {nk} nhân khẩu: khoản cộng thêm chỉ tính từ nhân khẩu thứ 5.'
        elif th == 0:
            g.thong_bao = 'Nhập số tháng thuê nhà ở dòng HT23/HT24 trước, rồi chọn lại khoản này.'
    elif ma in ('HT23', 'HT24'):
        g.don_gia, mo_ta = don_gia_theo_nhan_khau(bc, ma, pa.nhan_khau, bc.nguong_nk)
        g.dvt = 'Tháng'
        g.thong_bao = (f'{mo_ta}. Số lượng = số tháng thực tế thuê nhà chờ tái định cư '
                       f'(tối đa {so_vn(ts("THUENHA_TOIDA") or 12)} tháng).')
    elif ma in ('HT19', 'HT27', 'HT28'):
        g.so_luong = D(1)
        g.don_gia = ts({'HT19': 'HOCHINHSACH', 'HT27': 'HOCHINHSACH_2', 'HT28': 'HOCHINHSACH_3'}[ma]) or None
    elif ma == 'HT29':
        g.don_gia = ts('MOMA') or None
        g.thong_bao = 'Nhập số mộ ở cột Số lượng.'
    elif ma in ('HT31', 'HT32', 'HT33'):
        g.so_luong = D(1)
        g.thong_bao = 'Nhập đơn giá theo báo giá của đơn vị cung cấp, ghi số báo giá ở cột Căn cứ giá.'
    elif ma in ('HT37', 'HT38', 'HT39'):
        g.so_luong = D(1)
    return g


def ma_on_dinh_doi_song(ty_le_thu_hoi: Decimal, phai_di_chuyen: bool) -> str:
    """Mã khoản ổn định đời sống theo tỷ lệ DT đất NN thu hồi (danh mục DM_HOTRO, Điều 10 QĐ 42/2025)."""
    if ty_le_thu_hoi < D('0.3'):
        return 'HT02' if phai_di_chuyen else 'HT01'
    if ty_le_thu_hoi <= D('0.7'):
        return 'HT04' if phai_di_chuyen else 'HT03'
    return 'HT06' if phai_di_chuyen else 'HT05'


@dataclass
class DeXuat:
    ma: str
    so_luong: Decimal | None
    don_gia: Decimal | None
    ly_do: str
    viec: str = 'thêm'          # thêm / sửa / thay
    dong_cu: object = None      # DongKhoan đang có (sửa / thay)


def goi_y_ho_tro(pa: PhuongAn, bc: BoiCanh) -> tuple:
    """Rà toàn bộ mục 4 theo số liệu của hộ: (danh sách DeXuat, danh sách khoản cần người lập tự xác định)."""
    dx = []
    dt_nn = dt_nn_thu_hoi(pa)
    nk = pa.nhan_khau

    def dg_dm(ma):
        v = (bc.hotro.get(ma) or {}).get('don_gia')
        return D(v) if v not in (None, '') else None

    # đào tạo, chuyển đổi nghề
    for ma, gk in (('HT09', False), ('HT10', True)):
        sl, dg = de_xuat_dao_tao_pa(pa, bc, gk)
        co = pa.dong_ho_tro(ma)
        if any(_dao_tao_theo_thua(d) for d in co):
            continue                                    # nhập theo từng thửa (giá đất × tỷ lệ): người lập đã tính
        if sl > 0 and not co:
            dx.append(DeXuat(ma, sl, dg, f'DT đất nông nghiệp{" giao khoán" if gk else ""} thu hồi {so_vn(sl)} m² (trong hạn mức), '
                                         f'ĐG = {"0,5" if gk else "1,5"} × giá đất NN'))
        elif co and (co[0].so_luong != sl or co[0].don_gia != dg):
            dx.append(DeXuat(ma, sl, dg, f'đang ghi {so_vn(co[0].so_luong)} m² × {so_vn(co[0].don_gia)} đ; theo quy tắc '
                                         f'{so_vn(sl)} m² × {so_vn(dg)} đ', 'sửa', co[0]))
    # ổn định đời sống
    od = pa.dong_ho_tro(*MA_ON_DINH)
    if dt_nn > 0 and nk:
        dung = pa.ho.dt_nn_dang_dung or dt_nn          # chưa nhập DT đang sử dụng: lấy DT đất NN ở mục 1
        if dung > 0:
            tl = dt_nn / dung
            ma = ma_on_dinh_doi_song(tl, pa.ho.phai_di_chuyen)
            ly = f'thu hồi {so_vn(lam_tron(tl * 100, 1))}% đất NN đang sử dụng, {"phải" if pa.ho.phai_di_chuyen else "không"} di chuyển chỗ ở, {nk} nhân khẩu'
            if not od:
                dx.append(DeXuat(ma, D(nk), dg_dm(ma), ly))
            elif od[0].ma not in (ma, 'HT34', 'HT35'):
                dx.append(DeXuat(ma, D(nk), dg_dm(ma), f'đang ghi {od[0].ma}; {ly}', 'thay', od[0]))
            elif od[0].so_luong != nk:
                dx.append(DeXuat(od[0].ma, D(nk), od[0].don_gia, f'số lượng = {nk} nhân khẩu', 'sửa', od[0]))
        elif od and od[0].so_luong != nk:
            dx.append(DeXuat(od[0].ma, D(nk), od[0].don_gia, f'số lượng = {nk} nhân khẩu', 'sửa', od[0]))
    # di chuyển tài sản khi phải di chuyển chỗ ở
    if pa.ho.phai_di_chuyen and not pa.dong_ho_tro('HT14', 'HT15', 'HT16'):
        g = goi_y_khoan(pa, bc, 'HT14')
        dx.append(DeXuat('HT14', g.so_luong, g.don_gia, 'hộ phải di chuyển chỗ ở (đổi sang HT15/HT16 nếu chuyển ra ngoài xã, phường)'))
    # thuê nhà / tự lo chỗ ở: một dòng, đơn giá tháng gồm mức cơ bản + nhân khẩu vượt (bản cũ có dòng cộng thêm HT21/22/25/26:
    # giữ nguyên, không gộp lại)
    co_dong_them = bool(pa.dong_ho_tro('HT21', 'HT22', 'HT25', 'HT26'))
    for d in pa.dong_ho_tro(*MA_THEO_NK):
        if co_dong_them or d.nguon_gia != NGUON_DM:
            continue
        dg, mo_ta = don_gia_theo_nhan_khau(bc, d.ma, nk, bc.nguong_nk)
        if dg and d.don_gia != dg:
            dx.append(DeXuat(d.ma, d.so_luong, dg, mo_ta, 'sửa', d))
    tu_xac_dinh = []
    if dt_nn > 0 and not nk:
        tu_xac_dinh.append('Ổn định đời sống (HT01–HT06): nhập số nhân khẩu của hộ.')
    if pa.ho.phai_di_chuyen:
        tu_xac_dinh.append('Tự lo chỗ ở (HT17/HT18) hoặc thuê nhà chờ tái định cư (HT23/HT24): theo phương án bố trí tái định cư của hộ.')
    tu_xac_dinh.append('Hộ chính sách (HT19/HT27/HT28), di dời mồ mả (HT29), di dời điện, nước, Internet (HT31–HT33): theo hồ sơ của hộ.')
    return dx, tu_xac_dinh


# ---------------------------------------------------------------- kiểm tra quy tắc (cảnh báo, không sửa dữ liệu)
def kiem_tra_pa(pa: PhuongAn, bc: BoiCanh) -> list:
    """Các điểm cần xem lại của một hộ (chuỗi mô tả)."""
    ct = []
    tong_dt = {}
    for r in pa.dat:
        t = bc.thua.get(r.ma_thua)
        if r.ma_thua is None or t is None:
            ct.append(f'Mục 1: dòng loại đất {r.loai_dat} không gắn với thửa nào trong hồ sơ kiểm kê.')
            continue
        ld_kk = [x.strip().upper() for x in str(t['loai_dat'] or '').replace(',', '+').split('+') if x.strip()]
        if ld_kk and r.loai_dat.upper() not in ld_kk:
            ct.append(f'Thửa {t["so_thua"]} tờ {t["so_to"]}: loại đất ở mục 1 là {r.loai_dat}, hồ sơ kiểm kê ghi {t["loai_dat"]}.')
        tong_dt[r.ma_thua] = tong_dt.get(r.ma_thua, KHONG) + r.dien_tich
    for mt, dtt in tong_dt.items():
        t = bc.thua[mt]
        if D(t['dt_thu_hoi']) != dtt:
            ct.append(f'Thửa {t["so_thua"]} tờ {t["so_to"]}: tổng DT ở mục 1 = {so_vn(dtt)} m², kiểm kê ghi {so_vn(t["dt_thu_hoi"])} m².')
    for r in pa.dat:
        if r.gia_bang_gia == 0:
            ct.append(f'Mục 1: dòng loại đất {r.loai_dat or "(trống)"} chưa có giá bảng giá.')
    for ma, gk in (('HT09', False), ('HT10', True)):
        co = pa.dong_ho_tro(ma)
        if not co or any(_dao_tao_theo_thua(d) for d in co):
            continue
        sl, dg = de_xuat_dao_tao_pa(pa, bc, gk)
        if co[0].so_luong != sl or co[0].don_gia != dg:
            ct.append(f'{ma}: đang lưu SL {so_vn(co[0].so_luong)} m² x ĐG {so_vn(co[0].don_gia)} đ; theo quy tắc hiện hành '
                      f'(chỉ đất nông nghiệp{", giao khoán" if gk else ""}) là SL {so_vn(sl)} m² x ĐG {so_vn(dg)} đ.')
    for muc in (2, 3, 4):
        for k, d in enumerate(pa.khoan[muc], start=1):
            if d.nguon_gia in (NGUON_TD, NGUON_TAY) and not d.can_cu_gia.strip():
                ct.append(f'Dòng {muc}.{k} ({d.ten[:40]}): áp giá {d.nguon_gia}, chưa ghi căn cứ đơn giá.')
            if muc == 4 and d.ma in MA_TDC:
                continue                                # suất tái định cư: không có đơn giá tiền
            if d.so_luong == 0 or d.don_gia == 0:
                ct.append(f'Dòng {muc}.{k} ({d.ten[:40]}): chưa có {"số lượng" if d.so_luong == 0 else "đơn giá"}.')
    return ct


def kiem_tra_ho(con, ma_ho: int, bc: BoiCanh | None = None) -> list:
    return kiem_tra_pa(doc_phuong_an(con, ma_ho), bc or BoiCanh.tu(con))

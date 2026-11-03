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
           3: 'Bồi thường, hỗ trợ về cây trồng', 7: 'Bồi thường, hỗ trợ về vật nuôi', 4: 'Các chính sách hỗ trợ khác',
           5: 'Thưởng chấp hành bàn giao mặt bằng trước thời hạn'}           # 7 = MUC_VN (in là mục 4)
MA_ON_DINH = ('CS1', 'CS2', 'CS3', 'CS4', 'CS5', 'CS6', 'CS34', 'CS35')
MA_TDC = ('CS11', 'CS12', 'CS13')               # tái định cư: là điều kiện (suất TĐC), không phải dòng tiền
# thuê nhà chờ TĐC / tự lo chỗ ở: mức cơ bản (hộ đến N nhân khẩu, đồng/tháng) + mỗi nhân khẩu vượt (đồng/khẩu/tháng)
MA_THEO_NK = {'CS17': ('THUENHA_XA', 'THUENHA_NK_XA'), 'CS18': ('THUENHA_PHUONG', 'THUENHA_NK_PHUONG'),
              'CS23': ('THUENHA_XA', 'THUENHA_NK_XA'), 'CS24': ('THUENHA_PHUONG', 'THUENHA_NK_PHUONG')}
MA_DAO_TAO = ('CS9', 'CS10')                   # hỗ trợ đào tạo, chuyển đổi nghề và tìm kiếm việc làm
NK_CO_BAN = 4                                   # QĐ 42/2025: mức cơ bản cho hộ đến 4 nhân khẩu, cộng thêm từ khẩu thứ 5
_TAP_MA: list = [None, None]                    # [hồ sơ địa phương đã đọc (đối tượng dia_phuong.doc()), (ổn định, theo NK, TĐC, đào tạo)]


def _tap_ma() -> tuple:
    """(mã ổn định đời sống, mã thuê nhà / tự lo chỗ ở, mã tái định cư, mã đào tạo) = mã chuẩn (Đồng Nai, QĐ 42/2025) HỢP với mã khai
    báo thêm ở hồ sơ địa phương chinh_sach_ho_tro.ma_on_dinh / ma_theo_nk / ma_tdc / ma_dao_tao (bộ đơn giá tỉnh khác). Mã ổn định / theo nhân khẩu KHÔNG BAO
    GIỜ là tái định cư (ưu tiên mã; hồ sơ ghi trùng thì bỏ khỏi tập TĐC). Nhớ theo đối tượng hồ sơ (dia_phuong.doc đổi khi nạp lại)."""
    from . import dia_phuong
    hs = dia_phuong.doc()
    if _TAP_MA[0] is not hs:
        ch = hs.get('chinh_sach_ho_tro') if isinstance(hs, dict) else None
        ch = ch if isinstance(ch, dict) else {}

        def them(k):
            v = ch.get(k)
            return tuple(str(x).strip() for x in v if str(x).strip()) if isinstance(v, list) else ()
        od = tuple(dict.fromkeys(MA_ON_DINH + them('ma_on_dinh')))
        nk = tuple(x for x in dict.fromkeys(tuple(MA_THEO_NK) + them('ma_theo_nk')) if x not in od)
        dt = tuple(x for x in dict.fromkeys(MA_DAO_TAO + them('ma_dao_tao')) if x not in od)
        tdc = tuple(x for x in dict.fromkeys(MA_TDC + them('ma_tdc')) if x not in od and x not in nk and x not in dt)
        _TAP_MA[:] = [hs, (od, nk, tdc, dt)]
    return _TAP_MA[1]


def tap_ma_on_dinh() -> tuple:
    return _tap_ma()[0]


def tap_ma_theo_nk() -> tuple:
    return _tap_ma()[1]


def tap_ma_tdc() -> tuple:
    return _tap_ma()[2]


def tap_ma_dao_tao() -> tuple:
    return _tap_ma()[3]


def _muc_khau_vuot_tinh_khac(ma: str):
    """Mức cộng mỗi khẩu vượt ngưỡng (đồng/khẩu/tháng) của mã thuê nhà / tự lo chỗ ở tỉnh khác: hồ sơ địa phương
    chinh_sach_ho_tro.muc_khau_vuot {mã: số tiền} (tùy chọn; không khai báo = 0)."""
    from . import dia_phuong
    ch = dia_phuong.lay('chinh_sach_ho_tro')
    bang = ch.get('muc_khau_vuot') if isinstance(ch, dict) else None
    if not isinstance(bang, dict) or ma not in bang:
        return KHONG
    v = bang.get(ma)
    try:
        if isinstance(v, str):                       # "600.000" kiểu Việt Nam
            from .tien import doc_so_vn
            return doc_so_vn(v) if v.strip() else KHONG
        return D(str(v or 0))
    except (ValueError, ArithmeticError):
        return KHONG


def don_gia_theo_nhan_khau(bc, ma: str, nhan_khau, nguong: int | None = None) -> tuple:
    """Đơn giá một tháng (gộp một dòng) của khoản thuê nhà / tự lo chỗ ở theo số nhân khẩu:
    (đơn giá, mô tả). Hộ đến `nguong` khẩu: mức cơ bản; vượt: cơ bản + số khẩu vượt × mức mỗi khẩu."""
    co_ban_ma, them_ma = MA_THEO_NK.get(ma, (None, None))    # mã tỉnh khác (hồ sơ địa phương): mức cơ bản = đơn giá danh mục
    co_ban = bc.so_ts(co_ban_ma) if co_ban_ma else KHONG
    them = bc.so_ts(them_ma) if them_ma else _muc_khau_vuot_tinh_khac(ma)
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
# Mục của phương án (0.9.20 tách Vật nuôi khỏi Cây trồng - người dùng yêu cầu). Mã mục bên trong GIỮ như cũ để dữ liệu đã lưu,
# tong_excel, quyết định (tien_dat/tai_san/cay/ho_tro/thuong) không đổi: 1 đất, 2 nhà / công trình, 3 cây trồng, 4 hỗ trợ,
# 5 thưởng; vật nuôi = MUC_VN (7 - mã 6 là "Chi phí khác" của dự toán). Hiển thị / bản in theo THU_TU_MUC, đánh số SO_MUC:
# 1 Đất, 2 Nhà, 3 Cây trồng, 4 Vật nuôi, 5 Hỗ trợ, 6 Thưởng.
MUC_VN = 7
MUC_KHOAN = (2, 3, MUC_VN, 4)                   # các mục có dòng khoản (ct_khoan.muc), theo thứ tự hiển thị
THU_TU_MUC = (1, 2, 3, MUC_VN, 4, 5)
SO_MUC = {1: 1, 2: 2, 3: 3, MUC_VN: 4, 4: 5, 5: 6}
TEN_MUC_NGAN = {1: 'Đất', 2: 'Nhà, công trình', 3: 'Cây trồng', MUC_VN: 'Vật nuôi', 4: 'Hỗ trợ', 5: 'Thưởng'}


def so_muc(muc: int) -> int:
    """Số thứ tự hiển thị của mục (vật nuôi = 4, hỗ trợ = 5, thưởng = 6)."""
    return SO_MUC.get(muc, muc)


def muc_5_cot(muc: dict) -> dict:
    """{1..5} cho các bảng / cột cố định 5 hạng mục (tong_excel, tiền quyết định, báo cáo, bảng tổng hợp): vật nuôi gộp vào 3
    (cây trồng, vật nuôi)."""
    return {1: muc.get(1, KHONG), 2: muc.get(2, KHONG), 3: muc.get(3, KHONG) + muc.get(MUC_VN, KHONG), 4: muc.get(4, KHONG),
            5: muc.get(5, KHONG)}


def la_vat_nuoi(phan_loai: str) -> bool:
    """Mục danh mục (dm_taisan.phan_loai) thuộc nhóm vật nuôi (QĐ 31/2025)."""
    return 'vật nuôi' in str(phan_loai or '').lower()


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
    khoan: dict = field(default_factory=lambda: {m: [] for m in MUC_KHOAN})   # {mục: [DongKhoan]} (2, 3, MUC_VN, 4)

    def dong_ho_tro(self, *ma) -> list:
        return [d for d in self.khoan[4] if d.ma in ma]

    @property
    def nhan_khau(self) -> int | None:
        """Nhân khẩu của hộ; chưa nhập thì lấy Số lượng ở dòng ổn định đời sống (như bản Excel)."""
        if self.ho.nhan_khau:
            return self.ho.nhan_khau
        for d in self.dong_ho_tro(*tap_ma_on_dinh()):
            if d.so_luong > 0:
                return int(d.so_luong)
        return None


def _loai_dat_day_du(con) -> dict:
    """{mã loại đất: nhóm}: đủ danh sách chuẩn `loai_dat.LOAI_DAT` (RDD, RPH, DGT... luôn hợp lệ dù bảng giá dự án không có), mã
    trong dm_loaidat của dự án ghi đè nhóm."""
    from .loai_dat import LOAI_DAT, nhom_mac_dinh
    kq = {ma: nhom_mac_dinh(ma) for ma, _, _ in LOAI_DAT}
    kq.update({r['ma'].upper(): r['nhom'] for r in con.execute('SELECT ma, nhom FROM dm_loaidat')})
    return kq


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
                   loai_dat=_loai_dat_day_du(con),
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
                   ty_le=None if r['ty_le'] in (None, '') else D(r['ty_le']), ghi_chu=r['ghi_chu'],
                   thanh_tien_excel=_dec_hoac_none(r['thanh_tien_excel']), id=r['id'],
                   cong_thuc=(r['cong_thuc'] or '') if 'cong_thuc' in r.keys() else '')


def _dong_khoan(r) -> DongKhoan:
    kk = r.keys()
    return DongKhoan(
        muc=r['muc'], ma=r['ma'], ten=r['ten'], dvt=r['dvt'], so_luong=D(r['so_luong']), don_gia=D(r['don_gia']),
        ty_le=None if r['ty_le'] in (None, '') else D(r['ty_le']), quy_cach=r['quy_cach'], ghi_chu=r['ghi_chu'],
        nguon_gia=r['nguon_gia'] or NGUON_DM,
        ma_tuong_duong=r['ma_tuong_duong'], can_cu_gia=r['can_cu_gia'] if 'can_cu_gia' in kk else '',
        thanh_tien_excel=_dec_hoac_none(r['thanh_tien_excel']), id=r['id'],
        cach_tinh=(r['cach_tinh'] or '') if 'cach_tinh' in kk else '',
        cong_thuc=(r['cong_thuc'] or '') if 'cong_thuc' in kk else '')


def co_cot_lan(con) -> bool:
    """File có cột ct_dat.lan (CSDL v17 - nhiều lần lập phương án / hộ). File chỉ xem bản cũ: không (mọi dòng là lần 1)."""
    co = getattr(con, '_co_cot_lan', None)
    if co is not None:
        return co
    co = 'lan' in [r[1] for r in con.execute('PRAGMA table_info(ct_dat)')]
    try:
        con._co_cot_lan = co                        # csdl.KetNoi (lớp con Python) nhận thuộc tính; sqlite3.Connection thường thì không
    except AttributeError:
        pass
    return co


def lan_bi_thay(con, ma_ho: int | None = None) -> dict:
    """{ma_ho: {lần bị THAY THẾ bởi một lần điều chỉnh}} (pa_lan.thay_the > 0). Lần bị thay giữ nguyên dòng + quyết định (tra cứu,
    in "phương án đã phê duyệt") nhưng KHÔNG cộng vào tổng của hộ - chỉ lần điều chỉnh tính."""
    try:
        if ma_ho is None:
            ds = con.execute('SELECT ma_ho, thay_the FROM pa_lan WHERE thay_the > 0').fetchall()
        else:
            ds = con.execute('SELECT ma_ho, thay_the FROM pa_lan WHERE ma_ho = ? AND thay_the > 0', (ma_ho,)).fetchall()
    except Exception:                                   # chưa có bảng / cột (file cũ, bộ đơn giá)
        return {}
    kq = {}
    for r in ds:
        kq.setdefault(r[0], set()).add(int(r[1]))
    return kq


def doc_phuong_an(con, ma_ho: int, lan: int | None = None, den_lan: int | None = None,
                  ngoai_lan: int | None = None) -> PhuongAn:
    """Phương án của hộ. Mặc định CỘNG DỒN mọi lần lập phương án (v17: lần đầu + các lần bổ sung - tổng của hộ, danh sách hộ, đối
    chiếu, kiểm tra lỗi). lan: chỉ dòng của lần đó (soạn / in / quyết định của một lần); den_lan: các lần <= den_lan (lũy kế);
    ngoai_lan: mọi lần TRỪ lần đó (cộng dồn khi đang soạn một lần). Lần đã bị lần ĐIỀU CHỈNH thay thế (lan_bi_thay) không được cộng
    (trừ khi chọn đúng lan=)."""
    h = con.execute('SELECT * FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
    if h is None:
        raise KeyError(f'không có hộ mã {ma_ho}')
    pa = PhuongAn(ho=_tao_ho(h))
    if den_lan is not None and lan is None and int(den_lan) <= 0:
        return pa                                   # "các lần trước lần 1": không có dòng nào (lần >= 1) - khỏi đọc ct_dat / ct_khoan
    loc, ts = '', (ma_ho,)
    if co_cot_lan(con):
        if lan is not None:
            loc, ts = ' AND lan = ?', (ma_ho, int(lan))
        elif den_lan is not None:
            loc, ts = ' AND lan <= ?', (ma_ho, int(den_lan))
        elif ngoai_lan is not None:
            loc, ts = ' AND lan <> ?', (ma_ho, int(ngoai_lan))
    elif lan is not None and int(lan) != 1 or den_lan is not None and int(den_lan) < 1 or ngoai_lan == 1:
        return pa                                   # file chưa có cột lan: chỉ có lần 1
    bo = set() if lan is not None else lan_bi_thay(con, ma_ho).get(ma_ho, set())
    for r in con.execute(f'SELECT * FROM ct_dat WHERE ma_ho = ?{loc} ORDER BY thu_tu, id', ts):
        if not bo or r['lan'] not in bo:
            pa.dat.append(_dong_dat(r))
    for r in con.execute(f'SELECT * FROM ct_khoan WHERE ma_ho = ?{loc} ORDER BY muc, thu_tu, id', ts):
        if not bo or r['lan'] not in bo:
            pa.khoan[r['muc']].append(_dong_khoan(r))
    return pa


def gop_phuong_an(*ds: PhuongAn) -> PhuongAn:
    """Ghép các phương án (các lần) của CÙNG một hộ: thông tin hộ của phương án cuối, dòng nối theo thứ tự."""
    pa = PhuongAn(ho=ds[-1].ho)
    for x in ds:
        pa.dat.extend(x.dat)
        for m in MUC_KHOAN:
            pa.khoan[m].extend(x.khoan.get(m, []))
    return pa


def tinh_pa_lan(pa_lan, pa_truoc, bc, bc_lan=None) -> KetQuaHo:
    """Hai cách gọi: tinh_pa_lan(pa_lan, pa_truoc, bc) (phương án trong bộ nhớ) hoặc tinh_pa_lan(con, ma_ho, lan, bc) (đọc CSDL - như
    tinh_lan). Xem _tinh_pa_lan."""
    if isinstance(pa_lan, PhuongAn):
        return _tinh_pa_lan(pa_lan, pa_truoc, bc)
    return tinh_lan(pa_lan, pa_truoc, bc, bc_lan)


def _tinh_pa_lan(pa_lan: PhuongAn, pa_truoc: PhuongAn, bc: BoiCanh) -> KetQuaHo:
    """Kết quả RIÊNG một lần lập phương án: mục 1-4 theo dòng của lần đó; thưởng bàn giao mặt bằng (theo bậc trên tổng của hộ, chỉ
    một lần cho hộ) = thưởng của lũy kế tới lần này - thưởng của các lần trước. Cộng các lần = đúng tổng cộng dồn của hộ.
    pa_truoc: các lần trước (doc_phuong_an(den_lan=lan - 1)); lần đầu: phương án rỗng."""
    kq = tinh_pa(pa_lan, bc)
    if pa_truoc.dat or any(pa_truoc.khoan[m] for m in MUC_KHOAN):
        kq.muc[5] = tinh_pa(gop_phuong_an(pa_truoc, pa_lan), bc).muc[5] - tinh_pa(pa_truoc, bc).muc[5]
    return kq


def tinh_lan(con, ma_ho: int, lan: int, bc: BoiCanh | None = None) -> KetQuaHo:
    bc = bc or BoiCanh.tu(con)
    return _tinh_pa_lan(doc_phuong_an(con, ma_ho, lan=lan), doc_phuong_an(con, ma_ho, den_lan=lan - 1), bc)


def tinh_chenh_lech_lan(con, ma_ho: int, lan: int, bc: BoiCanh | None = None) -> KetQuaHo:
    """Kết quả của lần ĐIỀU CHỈNH tính theo CHÊNH LỆCH so với lần ĐÃ PHÊ DUYỆT bị thay (từng mục: mới - cũ, có thể âm) - số tiền ghi
    vào quyết định điều chỉnh (cộng quyết định cũ + quyết định điều chỉnh = tổng sau điều chỉnh). Lần không phải điều chỉnh, hoặc
    điều chỉnh từ dự thảo chưa phê duyệt (26/10/2026 - chưa có gì được duyệt để trừ): toàn bộ số tiền của lần, như tinh_lan."""
    from .lan_pa import co_bang, lan_duyet_bi_thay
    bc = bc or BoiCanh.tu(con)
    moi = tinh_lan(con, ma_ho, lan, bc)
    try:
        cu_lan = lan_duyet_bi_thay(con, ma_ho, lan) if co_bang(con) else 0
    except Exception:
        cu_lan = 0
    if not cu_lan:
        return moi
    cu = tinh_lan(con, ma_ho, cu_lan, bc)
    kq = KetQuaHo(ma_ho=moi.ma_ho, ho_ten=moi.ho_ten, dong=moi.dong, da_luu=moi.da_luu)
    for m in kq.muc:
        kq.muc[m] = moi.muc.get(m, KHONG) - cu.muc.get(m, KHONG)
    return kq


def doc_tat_ca_phuong_an(con, ds_ma_ho=None) -> dict:
    """{ma_ho: PhuongAn} theo thứ tự hộ (thu_tu, ma_ho) - 3 câu truy vấn cho cả dự án thay vì 3 câu mỗi hộ (3.000 hộ: 9.000 câu).
    Cùng thứ tự dòng như doc_phuong_an. ds_ma_ho: chỉ các hộ này (None = tất cả)."""
    chon = None if ds_ma_ho is None else set(ds_ma_ho)
    kq = {}
    for h in con.execute('SELECT * FROM ho ORDER BY thu_tu, ma_ho'):
        if chon is None or h['ma_ho'] in chon:
            kq[h['ma_ho']] = PhuongAn(ho=_tao_ho(h))
    bo = lan_bi_thay(con)
    cot_lan = co_cot_lan(con)
    for r in con.execute('SELECT * FROM ct_dat ORDER BY ma_ho, thu_tu, id'):
        pa = kq.get(r['ma_ho'])
        if pa is not None and not (bo and cot_lan and r['lan'] in bo.get(r['ma_ho'], ())):
            pa.dat.append(_dong_dat(r))
    for r in con.execute('SELECT * FROM ct_khoan ORDER BY ma_ho, muc, thu_tu, id'):
        pa = kq.get(r['ma_ho'])
        if pa is not None and not (bo and cot_lan and r['lan'] in bo.get(r['ma_ho'], ())):
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


# trạng thái hộ người dùng đã bấm Lưu trong cửa sổ lập phương án (lap_pa.BoSoan.luu): "Đã lập phương án (lưu dd/mm/yyyy hh:mm)"
DA_LAP_LUU = 'Đã lập phương án (lưu'


@dataclass
class KetQuaHo:
    ma_ho: int
    ho_ten: str = ''
    dong: list = field(default_factory=list)
    muc: dict = field(default_factory=lambda: {1: KHONG, 2: KHONG, 3: KHONG, MUC_VN: KHONG, 4: KHONG, 5: KHONG})
    da_luu: bool = False              # người dùng đã lưu phương án (kể cả không có dòng nào: mọi mục 0 đồng)

    @property
    def tong(self) -> Decimal:
        return sum(self.muc.values(), KHONG)

    @property
    def co_phuong_an(self) -> bool:
        """Đã có phương án: có dòng ở mục 1-5, hoặc người dùng đã lưu (từ 0.9.21: hộ không có đất / tài sản / hỗ trợ - mọi mục
        0 đồng - lưu xong vẫn là đã lập phương án)."""
        return self.da_luu or any(d.muc in (1, 2, 3, MUC_VN, 4) for d in self.dong)


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
    kq = KetQuaHo(ma_ho=pa.ho.ma_ho, ho_ten=pa.ho.ho_ten,
                  da_luu=bool(pa.ho.luu_luc) and str(pa.ho.trang_thai or '').startswith(DA_LAP_LUU))
    for k, r in enumerate(pa.dat, start=1):
        tt = thanh_tien_dong_dat(r, bc)
        t = bc.thua.get(r.ma_thua) or {}
        # vị trí: mô tả đầy đủ của thửa (HS_KIEMKE) nếu có, không thì số vị trí ở mục 1
        ten = mo_ta_thua(t.get('so_to', ''), t.get('so_thua', ''), r.loai_dat, bc.cap_dia_ban, bc.ten_dia_ban,
                         r.vi_tri or t.get('vi_tri'))
        kq.dong.append(Dong(1, f'1.{k}', ten, 'm²', r.dien_tich, r.gia_bang_gia * r.he_so_k, r.ty_le, tt,
                            r.loai_dat, r.ghi_chu, r.id or 0, r.thanh_tien_excel))
        kq.muc[1] += tt
    for muc in MUC_KHOAN:
        for k, r in enumerate(pa.khoan[muc], start=1):
            tt = thanh_tien_dong(r, bc)
            kq.dong.append(Dong(muc, f'{so_muc(muc)}.{k}', r.ten, r.dvt, r.so_luong, r.don_gia, r.ty_le, tt, r.ma, r.ghi_chu,
                                r.id or 0, r.thanh_tien_excel, r.cach_tinh))
            kq.muc[muc] += tt
    if kq.muc[1] > 0:
        kq.muc[5] = bc.muc_thuong(kq.muc[1] + kq.muc[2] + kq.muc[3] + kq.muc[MUC_VN] + kq.muc[4])
    return kq


def tinh_ho(con, ma_ho: int, bc: BoiCanh | None = None) -> KetQuaHo:
    return tinh_pa(doc_phuong_an(con, ma_ho), bc or BoiCanh.tu(con))


# ---------------------------------------------------------------- kết quả tính của cả dự án (dùng chung)
KHOA_KQ = ('KetQuaHo',)


def _tinh_kiem(pa: PhuongAn, bc: BoiCanh) -> tuple:
    return tinh_pa(pa, bc), kiem_tra_pa(pa, bc)


def ket_qua_ho(con, tat_ca: dict | None = None) -> dict:
    """{ma_ho: (KetQuaHo, [cảnh báo kiem_tra_pa])} theo thứ tự hộ - tính một lần trên kết nối, dùng chung cho danh sách hộ
    (đối chiếu), các trang tổng hợp, In / Xuất, đợt trình, báo cáo... tới khi dữ liệu đổi (csdl.nho). Lưu phương án một hộ chỉ
    tính lại hộ đó (giu_ket_qua_ho). Trước đây mỗi lần tải lại / chuyển trang / mở hộp thoại tính lại cả 3.000 hộ.
    tat_ca: phương án CẢ dự án nơi gọi vừa đọc (doc_tat_ca_phuong_an(con)) - chưa nhớ thì tính trên đó, không đọc lại lần 2.
    Dùng chung: KHÔNG sửa các đối tượng trả về."""
    from .csdl import nho

    def tao():
        bc = BoiCanh.tu(con)
        return {m: _tinh_kiem(pa, bc) for m, pa in (tat_ca if tat_ca is not None else doc_tat_ca_phuong_an(con)).items()}
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
    return he_so(d.ty_le) != 1 or d.ten.startswith('Thửa đất')


def de_xuat_dao_tao_pa(pa: PhuongAn, bc: BoiCanh, giao_khoan: bool = False):
    """Gợi ý CS9 (giao_khoan=False) / CS10 (True): (SL m², ĐG).
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
        s[g] += r.dien_tich * r.gia_bang_gia * he_so(r.he_so_k)      # giá đất đã nhân hệ số K (QĐ 03/2026/QĐ-UBND)
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
    if ma in ('CS9', 'CS10'):
        sl, dg = de_xuat_dao_tao_pa(pa, bc, ma == 'CS10')
        g.dvt = 'm²'
        if sl > 0:
            g.so_luong, g.don_gia = sl, dg
        elif ma == 'CS10':
            g.thong_bao = ('Mục 1 chưa có thửa đất nông nghiệp giao khoán (hợp đồng chưa thanh lý): ghi "giao khoán" ở '
                           'nguồn gốc đất của thửa hoặc ghi chú dòng mục 1.')
        else:
            g.thong_bao = 'Mục 1 chưa có dòng đất nông nghiệp có giá bảng giá: nhập xong mục 1 rồi chọn lại khoản này.'
    elif ma in tap_ma_on_dinh():
        nk = pa.nhan_khau
        if nk:
            g.so_luong = D(nk)
        else:
            g.thong_bao = 'Chưa có số nhân khẩu của hộ: nhập ô Nhân khẩu ở đầu màn hình.'
    elif ma == 'CS8':
        g.don_gia = ts('VATNUOI') or None
    elif ma in ('CS14', 'CS15', 'CS16'):
        g.so_luong = D(1)
        g.don_gia = ts({'CS14': 'DICHUYEN_XA', 'CS15': 'DICHUYEN_TP', 'CS16': 'DICHUYEN_NGOAI'}[ma]) or None
    elif ma in ('CS17', 'CS18'):
        g.so_luong = ts('TULO_THANG') or D(6)
        g.don_gia, g.thong_bao = don_gia_theo_nhan_khau(bc, ma, pa.nhan_khau, bc.nguong_nk)
        g.dvt = 'Tháng'
    elif ma in ('CS21', 'CS22', 'CS25', 'CS26'):
        nk = pa.nhan_khau or 0
        if ma in ('CS21', 'CS22'):
            th = ts('TULO_THANG') or D(6)
        else:
            th = next((d.so_luong for d in pa.dong_ho_tro('CS23', 'CS24') if d.so_luong > 0), KHONG)
        if nk > 4 and th > 0:
            g.so_luong = (nk - 4) * th
        g.don_gia = ts('THUENHA_NK_XA' if ma in ('CS21', 'CS25') else 'THUENHA_NK_PHUONG') or None
        if not nk:
            g.thong_bao = 'Chưa có số nhân khẩu của hộ: nhập ô Nhân khẩu ở đầu màn hình.'
        elif nk <= 4:
            g.thong_bao = f'Hộ có {nk} nhân khẩu: khoản cộng thêm chỉ tính từ nhân khẩu thứ 5.'
        elif th == 0:
            g.thong_bao = 'Nhập số tháng thuê nhà ở dòng CS23/CS24 trước, rồi chọn lại khoản này.'
    elif ma in ('CS23', 'CS24'):
        g.don_gia, mo_ta = don_gia_theo_nhan_khau(bc, ma, pa.nhan_khau, bc.nguong_nk)
        g.dvt = 'Tháng'
        g.thong_bao = (f'{mo_ta}. Số lượng = số tháng thực tế thuê nhà chờ tái định cư '
                       f'(tối đa {so_vn(ts("THUENHA_TOIDA") or 12)} tháng).')
    elif ma in ('CS19', 'CS27', 'CS28'):
        g.so_luong = D(1)
        g.don_gia = ts({'CS19': 'HOCHINHSACH', 'CS27': 'HOCHINHSACH_2', 'CS28': 'HOCHINHSACH_3'}[ma]) or None
    elif ma == 'CS29':
        g.don_gia = ts('MOMA') or None
        g.thong_bao = 'Nhập số mộ ở cột Số lượng.'
    elif ma in ('CS31', 'CS32', 'CS33'):
        g.so_luong = D(1)
        g.thong_bao = 'Nhập đơn giá theo báo giá của đơn vị cung cấp, ghi số báo giá ở cột Căn cứ giá.'
    elif ma in ('CS37', 'CS38', 'CS39'):
        g.so_luong = D(1)
    return g


def ma_on_dinh_doi_song(ty_le_thu_hoi: Decimal, phai_di_chuyen: bool) -> str:
    """Mã khoản ổn định đời sống theo tỷ lệ DT đất NN thu hồi (danh mục DM_HOTRO, Điều 10 QĐ 42/2025)."""
    if ty_le_thu_hoi < D('0.3'):
        return 'CS2' if phai_di_chuyen else 'CS1'
    if ty_le_thu_hoi <= D('0.7'):
        return 'CS4' if phai_di_chuyen else 'CS3'
    return 'CS6' if phai_di_chuyen else 'CS5'


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
    for ma, gk in (('CS9', False), ('CS10', True)):
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
    od = pa.dong_ho_tro(*tap_ma_on_dinh())
    if dt_nn > 0 and nk:
        dung = pa.ho.dt_nn_dang_dung or dt_nn          # chưa nhập DT đang sử dụng: lấy DT đất NN ở mục 1
        if dung > 0:
            tl = dt_nn / dung
            ma = ma_on_dinh_doi_song(tl, pa.ho.phai_di_chuyen)
            ly = f'thu hồi {so_vn(lam_tron(tl * 100, 1))}% đất NN đang sử dụng, {"phải" if pa.ho.phai_di_chuyen else "không"} di chuyển chỗ ở, {nk} nhân khẩu'
            if not od:
                dx.append(DeXuat(ma, D(nk), dg_dm(ma), ly))
            elif od[0].ma not in (ma, 'CS34', 'CS35'):
                dx.append(DeXuat(ma, D(nk), dg_dm(ma), f'đang ghi {od[0].ma}; {ly}', 'thay', od[0]))
            elif od[0].so_luong != nk:
                dx.append(DeXuat(od[0].ma, D(nk), od[0].don_gia, f'số lượng = {nk} nhân khẩu', 'sửa', od[0]))
        elif od and od[0].so_luong != nk:
            dx.append(DeXuat(od[0].ma, D(nk), od[0].don_gia, f'số lượng = {nk} nhân khẩu', 'sửa', od[0]))
    # di chuyển tài sản khi phải di chuyển chỗ ở
    if pa.ho.phai_di_chuyen and not pa.dong_ho_tro('CS14', 'CS15', 'CS16'):
        g = goi_y_khoan(pa, bc, 'CS14')
        dx.append(DeXuat('CS14', g.so_luong, g.don_gia, 'hộ phải di chuyển chỗ ở (đổi sang CS15/CS16 nếu chuyển ra ngoài xã, phường)'))
    # thuê nhà / tự lo chỗ ở: một dòng, đơn giá tháng gồm mức cơ bản + nhân khẩu vượt (bản cũ có dòng cộng thêm CS21/22/25/26:
    # giữ nguyên, không gộp lại)
    co_dong_them = bool(pa.dong_ho_tro('CS21', 'CS22', 'CS25', 'CS26'))
    for d in pa.dong_ho_tro(*tap_ma_theo_nk()):
        if co_dong_them or d.nguon_gia != NGUON_DM:
            continue
        dg, mo_ta = don_gia_theo_nhan_khau(bc, d.ma, nk, bc.nguong_nk)
        if dg and d.don_gia != dg:
            dx.append(DeXuat(d.ma, d.so_luong, dg, mo_ta, 'sửa', d))
    tu_xac_dinh = []
    if dt_nn > 0 and not nk:
        tu_xac_dinh.append('Ổn định đời sống (CS1–CS6): nhập số nhân khẩu của hộ.')
    if pa.ho.phai_di_chuyen:
        tu_xac_dinh.append('Tự lo chỗ ở (CS17/CS18) hoặc thuê nhà chờ tái định cư (CS23/CS24): theo phương án bố trí tái định cư của hộ.')
    tu_xac_dinh.append('Hộ chính sách (CS19/CS27/CS28), di dời mồ mả (CS29), di dời điện, nước, Internet (CS31–CS33): theo hồ sơ của hộ.')
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
        if dtt != 0 and D(t['dt_thu_hoi']) != dtt:     # DT mục 1 = 0: không bồi thường đất (tài sản trên đất người khác)
            ct.append(f'Thửa {t["so_thua"]} tờ {t["so_to"]}: tổng DT ở mục 1 = {so_vn(dtt)} m², kiểm kê ghi {so_vn(t["dt_thu_hoi"])} m².')
    for ma, gk in (('CS9', False), ('CS10', True)):
        co = pa.dong_ho_tro(ma)
        if not co or any(_dao_tao_theo_thua(d) for d in co):
            continue
        sl, dg = de_xuat_dao_tao_pa(pa, bc, gk)
        if co[0].so_luong != sl or co[0].don_gia != dg:
            ct.append(f'{ma}: đang lưu SL {so_vn(co[0].so_luong)} m² x ĐG {so_vn(co[0].don_gia)} đ; theo quy tắc hiện hành '
                      f'(chỉ đất nông nghiệp{", giao khoán" if gk else ""}) là SL {so_vn(sl)} m² x ĐG {so_vn(dg)} đ.')
    for muc in MUC_KHOAN:
        for k, d in enumerate(pa.khoan[muc], start=1):
            if d.nguon_gia in (NGUON_TD, NGUON_TAY) and not d.can_cu_gia.strip():
                ct.append(f'Dòng {so_muc(muc)}.{k} ({d.ten[:40]}): áp giá {d.nguon_gia}, chưa ghi căn cứ đơn giá.')
    return ct


def dong_bang_0(pa: PhuongAn) -> list:
    """Dòng có diện tích / số lượng / đơn giá = 0 (thành tiền 0 đồng). Từ 0.9.21 KHÔNG còn là điểm cần xem lại khi lập phương
    án (người dùng nhập 0 = không bồi thường mục đó: cho lưu, vẫn là đã lập) - chỉ liệt kê để tham khảo ở Kiểm tra lỗi."""
    ct = []
    for k, r in enumerate(pa.dat, start=1):
        if r.dien_tich == 0 or r.gia_bang_gia == 0:
            ct.append(f'Dòng 1.{k} (loại đất {r.loai_dat or "(trống)"}): '
                      f'{"diện tích" if r.dien_tich == 0 else "giá đất"} = 0, thành tiền 0 đồng.')
    for muc in MUC_KHOAN:
        for k, d in enumerate(pa.khoan[muc], start=1):
            if muc == 4 and d.ma in tap_ma_tdc():
                continue                                # suất tái định cư: không có đơn giá tiền
            if d.so_luong == 0 or d.don_gia == 0:
                ct.append(f'Dòng {so_muc(muc)}.{k} ({d.ten[:40]}): {"số lượng" if d.so_luong == 0 else "đơn giá"} = 0, '
                          'thành tiền 0 đồng.')
    return ct


def kiem_tra_ho(con, ma_ho: int, bc: BoiCanh | None = None) -> list:
    return kiem_tra_pa(doc_phuong_an(con, ma_ho), bc or BoiCanh.tu(con))


# ---------------------------------------------------------------- giải trình một dòng (1.0.55 - người dùng 03/11/2026)
def chu_lam_tron(n: int) -> str:
    """-3 -> 'làm tròn đến nghìn đồng' (tham số LAMTRON của dự án, ROUND của Excel)."""
    return {0: 'làm tròn đến đồng', -1: 'làm tròn đến chục đồng', -2: 'làm tròn đến trăm đồng', -3: 'làm tròn đến nghìn đồng',
            -4: 'làm tròn đến chục nghìn đồng', -5: 'làm tròn đến trăm nghìn đồng', -6: 'làm tròn đến triệu đồng'}.get(
        int(n), f'làm tròn {n} chữ số')


def giai_trinh_dong_pa(pa: PhuongAn, bc: BoiCanh, muc: int, chi_so: int) -> dict:
    """Giải trình dòng chi_so (0-) của mục muc (1 đất; 2, 3, MUC_VN, 4 khoản) để trả lời thanh tra / người dân: ten_hang_muc,
    cong_thuc_chu (công thức bằng chữ), thay_so [dòng thay số cụ thể], can_cu [căn cứ / nguồn giá], thanh_tien (Decimal - đúng như
    tinh_pa), dong [mọi dòng gộp để hiện / chép]. Chỉ đọc, không đổi phương án."""
    from .tien import so_vn, vn
    tron = chu_lam_tron(bc.lamtron)
    if muc == 1:
        d = pa.dat[chi_so]
        t = bc.thua.get(d.ma_thua) or {}
        ten = mo_ta_thua(t.get('so_to', ''), t.get('so_thua', ''), d.loai_dat, bc.cap_dia_ban, bc.ten_dia_ban, d.vi_tri or t.get('vi_tri'))
        k, tl = he_so(d.he_so_k), he_so(d.ty_le)
        dg = D(d.gia_bang_gia) * k
        tt = thanh_tien_dong_dat(d, bc)
        cong_thuc = f'Thành tiền = ROUND(Diện tích × Giá đất theo bảng giá × Hệ số K × Tỷ lệ bồi thường; {tron})'
        thay = []
        if d.cong_thuc:
            thay.append(f'Diện tích tính từ công thức đã nhập: {d.cong_thuc} = {so_vn(d.dien_tich)} m²')
        thay.append(f'Đơn giá bồi thường = {vn(d.gia_bang_gia)} đ/m² × hệ số K {so_vn(k)} = {vn(dg)} đ/m²')
        thay.append(f'Thành tiền = {so_vn(d.dien_tich)} m² × {vn(dg)} đ/m² × {so_vn(tl * 100)}% = {vn(D(d.dien_tich) * dg * tl)} đồng'
                    f' -> {tron}: {vn(tt)} đồng')
        can_cu = [x for x in (f'Loại đất {d.loai_dat}' + (f', vị trí {d.vi_tri}' if d.vi_tri else '') if d.loai_dat else '',
                              (f'Nguồn gốc sử dụng đất: {t.get("nguon_goc")}' if t.get('nguon_goc') else ''),
                              (f'Ghi chú / căn cứ: {d.ghi_chu}' if d.ghi_chu else '')) if x]
    else:
        d = pa.khoan[muc][chi_so]
        tl = he_so(d.ty_le)
        tt = thanh_tien_dong(d, bc)
        ten = (f'{d.ma} - ' if d.ma else '') + (d.ten or '')
        cong_thuc = f'Thành tiền = ROUND(Số lượng × Đơn giá × Tỷ lệ; {tron})'
        thay = []
        if d.cong_thuc:
            thay.append(f'Số lượng tính từ công thức đã nhập: {d.cong_thuc} = {so_vn(d.so_luong)} {d.dvt or ""}'.rstrip())
        if muc == 4 and d.ma in tap_ma_theo_nk():
            thay.append('Đơn giá theo nhân khẩu: ' + don_gia_theo_nhan_khau(bc, d.ma, pa.nhan_khau, bc.nguong_nk)[1])
        if d.cach_tinh:
            thay.append(f'Cách tính: {d.cach_tinh}')
        if muc == 4 and d.ma in tap_ma_on_dinh():
            cong_thuc += ' (ổn định đời sống: số lượng = nhân khẩu, đơn giá = kg gạo × giá gạo × số tháng × mức hỗ trợ)'
        elif muc == 4 and d.ma in tap_ma_dao_tao():
            cong_thuc += ' (đào tạo, chuyển đổi nghề: số lượng = diện tích đất nông nghiệp thu hồi, đơn giá = giá đất × tỷ lệ hỗ trợ)'
        thay.append(f'Thành tiền = {so_vn(d.so_luong)} {d.dvt or ""} × {vn(d.don_gia)} đ × {so_vn(tl * 100)}% = '
                    f'{vn(D(d.so_luong) * D(d.don_gia) * tl)} đồng -> {tron}: {vn(tt)} đồng')
        nguon = {NGUON_DM: 'đơn giá theo danh mục bộ đơn giá', NGUON_TD: 'đơn giá theo mục tương đương'
                 + (f' {d.ma_tuong_duong}' if d.ma_tuong_duong else ''), NGUON_TAY: 'đơn giá nhập tay'}.get(d.nguon_gia, d.nguon_gia)
        ht = (bc.hotro.get(d.ma) or {}) if muc == 4 else {}
        can_cu = [x for x in (f'Nguồn giá: {nguon}' if nguon else '',
                              (f'Căn cứ giá: {d.can_cu_gia}' if d.can_cu_gia else ''),
                              (f'{"Căn cứ" if muc == 4 else "Quy cách"}: {d.quy_cach}' if d.quy_cach else ''),
                              (f'Căn cứ chính sách: {ht.get("can_cu")}' if ht.get('can_cu') and ht.get('can_cu') != d.quy_cach else ''),
                              (f'Ghi chú: {d.ghi_chu}' if d.ghi_chu and d.ghi_chu not in (d.quy_cach, ht.get('can_cu')) else ''))
                  if x]
    dong = [f'Hạng mục: {ten}', '', 'Công thức:', f'  {cong_thuc}', '', 'Thay số:', *[f'  {x}' for x in thay]]
    if can_cu:
        dong += ['', 'Căn cứ, nguồn số liệu:', *[f'  {x}' for x in can_cu]]
    # 1.0.56: quy định cách tính trích từ văn bản đơn giá (tham_so QDCT:…) có liên quan tới mục - xem để tính đúng (mật độ, tỷ lệ…)
    from .quy_dinh_van_ban import quy_dinh_lien_quan
    qd = quy_dinh_lien_quan(bc.ts, {1: 0, 2: 2, 3: 3, MUC_VN: 7, 4: 4}.get(muc, 0), ten) if muc != 1 else []
    if qd:
        dong += ['', 'Quy định cách tính trong văn bản đơn giá (liên quan):', *[f'  - {x}' for x in qd]]
    return dict(muc=muc, chi_so=chi_so, ten_hang_muc=ten, cong_thuc_chu=cong_thuc, thay_so=thay, can_cu=can_cu, thanh_tien=tt,
                dong=dong, quy_dinh=qd)

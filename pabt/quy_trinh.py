"""Trạng thái 16 bước quy trình QĐ 18 của một dự án ("LARC theo quy trình QĐ 18", người dùng 30/10/2026: sắp xếp giao diện theo
QĐ 18, dễ dùng cho người mới, dẫn từng bước). Không Qt. Tính từ dữ liệu sẵn có - KHÔNG đổi lược đồ CSDL; ngày của các bước chưa
có bảng riêng (2 họp dân, 10 công khai quyết định, 11 gửi phương án, 13 quyết định thu hồi) lưu ở bảng cai_dat (`MOC_BUOC`), bước 3
dùng chung khóa ngày thông báo thu hồi của thoi_han.

Nguồn danh sách hộ: các dòng `CuaSoChinh.mo_hinh.dong` (da_phe_duyet / da_chi_tra / da_ban_giao theo nấc tiến độ phân tích tự động,
cùng nguồn thẻ số liệu) hoặc `dong_tu_csdl(con)` khi không có cửa sổ. Tên / thứ tự bước theo `quy_trinh_qd18.BUOC`."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .quy_trinh_qd18 import BUOC

XONG, DANG, CHUA, QUA_HAN = 'xong', 'dang', 'chua', 'qua_han'
TEN_TRANG_THAI = {XONG: 'Đã xong', DANG: 'Đang làm', CHUA: 'Chưa tới', QUA_HAN: 'Quá hạn / có lỗi'}

# 5 giai đoạn gom 16 bước (thanh điều hướng, thanh tiến độ của buồng lái)
GIAI_DOAN = (
    ('A', 'Chuẩn bị', (1, 2, 3)),
    ('B', 'Điều tra, kiểm đếm', (4,)),
    ('C', 'Lập và công khai phương án', (5, 6, 7)),
    ('D', 'Thẩm định, phê duyệt', (8, 9, 10, 11)),
    ('E', 'Thực hiện, hoàn tất', (12, 13, 14, 15, 16)),
)
TEN_BUOC = {b[0]: b[1] for b in BUOC}
TEN_NGAN = {1: 'Kế hoạch, khái toán', 2: 'Họp dân', 3: 'Thông báo thu hồi', 4: 'Hộ, thửa, kiểm đếm', 5: 'Lập phương án',
            6: 'Niêm yết', 7: 'Lấy ý kiến, đối thoại', 8: 'Trình thẩm định', 9: 'Quyết định phê duyệt', 10: 'Công khai quyết định',
            11: 'Gửi phương án đến hộ', 12: 'Chi trả, tái định cư', 13: 'Quyết định thu hồi đất', 14: 'Vận động nhận tiền',
            15: 'Vận động bàn giao', 16: 'Mặt bằng sạch'}

# lệnh của cửa sổ chính (khóa CuaSoChinh.lenh) mở chỗ làm của từng bước; None = bước chưa có chỗ làm riêng (bổ sung ở bước đại tu 5)
LENH_BUOC = {1: 'Dự toán & khái toán', 2: None, 3: 'Theo dõi tiến độ', 4: 'Danh sách hộ', 5: 'Lập phương án hộ…',
             6: 'Dự thảo PABT…', 7: 'Dự thảo PABT…', 8: 'Đợt trình…', 9: 'Quyết định phê duyệt', 10: None, 11: 'In / Xuất…',
             12: 'Theo dõi tiến độ', 13: None, 14: 'Theo dõi tiến độ', 15: 'Theo dõi tiến độ', 16: 'Theo dõi tiến độ'}

# ngày đánh dấu xong của các bước không có bảng dữ liệu riêng (cai_dat của dự án, dd/mm/yyyy)
MOC_BUOC = {2: 'NGAY_HOP_DAN_CHU_TRUONG', 3: 'NGAY_THONG_BAO_THU_HOI', 10: 'NGAY_CONG_KHAI_QD', 11: 'NGAY_GUI_PA',
            13: 'NGAY_QD_THU_HOI'}

MUC_VIEC = ('loi', 'can', 'nhac')          # thứ tự ưu tiên việc: có lỗi / cần làm / nhắc
VIEC_TOI_DA = 6


@dataclass
class Viec:
    buoc: int
    chu: str
    muc: str = 'can'                        # 'loi' | 'can' | 'nhac'
    lenh: str | None = None                 # khóa CuaSoChinh.lenh mở chỗ làm
    so: int = 0


@dataclass
class TrangThaiBuoc:
    buoc: int
    trang_thai: str = CHUA
    xong: int = 0                           # tiến độ đếm được (hộ / đợt...) - tong 0 = bước không đếm theo hộ
    tong: int = 0
    mo_ta: str = ''                         # một dòng tình trạng, vd "128 / 170 hộ đã lập phương án"
    con_ngay: int | None = None             # hạn còn bao nhiêu ngày (âm = đã quá)
    ngay: date | None = None                # ngày đã ghi (bước có mốc ngày)
    dieu_kien: list = field(default_factory=list)       # [(đạt?, chữ)] điều kiện xong bước

    @property
    def ten(self) -> str:
        return TEN_BUOC[self.buoc]

    @property
    def ten_ngan(self) -> str:
        return TEN_NGAN[self.buoc]

    @property
    def lenh(self) -> str | None:
        return LENH_BUOC[self.buoc]

    @property
    def giai_doan(self) -> str:
        return giai_doan_cua(self.buoc)[0]


@dataclass
class KetQuaQuyTrinh:
    buoc: dict                              # {số bước: TrangThaiBuoc}
    hien_tai: int
    viec: list                              # [Viec] đã xếp ưu tiên
    so_ho: int = 0

    def theo_giai_doan(self):
        """[(mã, tên, [TrangThaiBuoc])] theo GIAI_DOAN."""
        return [(ma, ten, [self.buoc[b] for b in ds]) for ma, ten, ds in GIAI_DOAN]

    def trang_thai_giai_doan(self, ma: str) -> str:
        ds = [self.buoc[b].trang_thai for b in dict((g[0], g[2]) for g in GIAI_DOAN)[ma]]
        if all(t == XONG for t in ds):
            return XONG
        if QUA_HAN in ds:
            return QUA_HAN
        return DANG if any(t in (XONG, DANG) for t in ds) else CHUA


def giai_doan_cua(buoc: int) -> tuple:
    for ma, ten, ds in GIAI_DOAN:
        if buoc in ds:
            return ma, ten
    raise KeyError(buoc)


# ---------------------------------------------------------------- mốc ngày của bước (cai_dat)
def doc_moc(con, buoc: int) -> date | None:
    from . import csdl, thoi_han
    ma = MOC_BUOC.get(buoc)
    return thoi_han.doc_ngay(csdl.doc_cai_dat(con, ma, '')) if ma else None


def ghi_moc(con, buoc: int, ngay) -> None:
    """Ghi (ngay = date / chữ dd/mm/yyyy) hoặc xóa (None / '') ngày đánh dấu xong của bước; có nhật ký, hoàn tác được."""
    from . import csdl, thoi_han
    ma = MOC_BUOC.get(buoc)
    if not ma:
        raise KeyError(f'Bước {buoc} không đánh dấu bằng ngày.')
    d = thoi_han.doc_ngay(ngay) if ngay not in (None, '') else None
    if ngay not in (None, '') and d is None:
        from .lap_pa import LoiNhap
        raise LoiNhap(f'Ngày "{ngay}" không đúng dạng ngày/tháng/năm (ví dụ 05/03/2026).')
    chu = d.strftime('%d/%m/%Y') if d else ''
    with csdl.giao_dich(con):
        csdl.ghi_cai_dat(con, ma, chu)
        csdl.ghi_nhat_ky(con, f'Bước {buoc} - {TEN_NGAN[buoc]}: ' + (f'ngày {chu}' if chu else 'bỏ ngày'))


# ---------------------------------------------------------------- dòng hộ khi không có cửa sổ chính
def dong_tu_csdl(con) -> list:
    """Dòng hộ tối thiểu như CuaSoChinh.mo_hinh.dong (ma_ho, o[3] số thửa, tong, da_lap, da_phe_duyet, da_chi_tra, da_ban_giao) -
    nấc tiến độ theo theo_doi.phan_tich_tien_do (cùng quy tắc danh sách hộ)."""
    from . import theo_doi
    kq = []
    for x in theo_doi.tong_hop(con, tinh_pa=True):
        t = x.tien_do
        kq.append(dict(ma_ho=x.ma_ho, o=[x.thu_tu, x.ho_ten, x.dia_chi, len(x.thua), 0, '', ''], tong=x.tong_pa,
                       da_lap=t.da_lap, da_phe_duyet=t.da_pd, da_chi_tra=t.da_ct, da_ban_giao=t.da_bg))
    return kq


# ---------------------------------------------------------------- tính trạng thái
def _bang_co(con, bang: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (bang,)).fetchone() is not None


def _dem(con, sql: str, ts=()) -> int:
    try:
        return int(con.execute(sql, ts).fetchone()[0] or 0)
    except Exception:                                   # noqa: BLE001 - file cũ thiếu bảng / cột: coi như 0
        return 0


def _cac_dong(con, sql: str, ts=()) -> list:
    try:
        return con.execute(sql, ts).fetchall()
    except Exception:                                   # noqa: BLE001 - file cũ thiếu bảng / cột
        return []


def _tien_do(t: TrangThaiBuoc, xong: int, tong: int, chu: str) -> None:
    t.xong, t.tong = xong, tong
    t.mo_ta = f'{xong} / {tong} {chu}'
    t.trang_thai = XONG if tong and xong >= tong else DANG if xong else CHUA


def _moc(con, t: TrangThaiBuoc, ten_viec: str) -> None:
    t.ngay = doc_moc(con, t.buoc)
    if t.ngay:
        t.trang_thai, t.mo_ta = XONG, f'Đã ghi ngày {t.ngay.strftime("%d/%m/%Y")}'
    else:
        t.mo_ta = f'Chưa ghi ngày {ten_viec}'
    t.dieu_kien = [(t.ngay is not None, f'Đã ghi ngày {ten_viec}')]


def tinh(con, dong: list | None = None, lap: dict | None = None, hom_nay=None) -> KetQuaQuyTrinh:
    """Trạng thái 16 bước + bước hiện tại + việc nên làm tiếp. lap = lap_pa.phan_loai_lap(con) (tính lại khi None)."""
    from . import csdl, du_thao, kinh_phi_du_an, thoi_han, tiep_nhan_phap_ly, tong_quan_du_an
    from .lap_pa import phan_loai_lap
    nay = thoi_han.hom_nay_hoac(hom_nay)
    if dong is None:
        dong = dong_tu_csdl(con)
    if lap is None:
        lap = phan_loai_lap(con)
    n = len(dong)
    T = {b: TrangThaiBuoc(b) for b in TEN_BUOC}
    viec = []

    # 1. kế hoạch, khái toán: có file khái toán gắn với dự án hoặc hồ sơ tiếp nhận pháp lý
    co_kt = bool(csdl.doc_cai_dat(con, kinh_phi_du_an.KHOA_FILE_KHAI_TOAN, '').strip())
    try:
        co_pl = tiep_nhan_phap_ly.doc_du_an(con) is not None
    except Exception:                                   # noqa: BLE001 - hồ sơ tiếp nhận hỏng không chặn buồng lái
        co_pl = False
    t = T[1]
    t.dieu_kien = [(co_kt, 'Có bảng khái toán (Khái toán & dự toán)'), (co_pl, 'Có hồ sơ tiếp nhận pháp lý dự án')]
    t.trang_thai = XONG if co_kt or co_pl else CHUA
    t.mo_ta = 'Đã có khái toán / hồ sơ pháp lý' if t.trang_thai == XONG else 'Chưa gắn khái toán, hồ sơ pháp lý'

    # 2, 3: ngày họp dân, thông báo thu hồi
    _moc(con, T[2], 'họp dân phổ biến chủ trương')
    _moc(con, T[3], 'thông báo thu hồi đất')

    # 4. hộ, thửa
    co_thua = sum(1 for d in dong if int((d.get('o') or [0, '', '', 0])[3] or 0) > 0)
    t = T[4]
    _tien_do(t, co_thua, n, 'hộ có thửa đất')
    t.dieu_kien = [(n > 0, 'Có danh sách hộ'), (n > 0 and co_thua == n, 'Mọi hộ đều có thửa đất')]
    if n == 0:
        t.mo_ta = 'Chưa có hộ nào'
        viec.append(Viec(4, 'Dự án chưa có hộ: nhập danh sách hộ, thửa (Excel / kiểm đếm)', 'can', LENH_BUOC[4]))
    elif co_thua < n:
        viec.append(Viec(4, f'{n - co_thua} hộ chưa có thửa đất', 'nhac', LENH_BUOC[4], n - co_thua))

    # 5. lập phương án
    da = sum(1 for d in dong if lap.get(d['ma_ho']) == 'da_lap')
    tu = sum(1 for d in dong if lap.get(d['ma_ho']) == 'tu_lap')
    co_pa = da + tu                                     # hộ đã có phương án (kể cả tự lập chưa soát): mẫu số của các bước sau
    t = T[5]
    _tien_do(t, da, n, 'hộ đã lập phương án')
    if tu:
        t.mo_ta += f' · {tu} hộ tự lập chưa soát'
        if t.trang_thai == CHUA:
            t.trang_thai = DANG
    t.dieu_kien = [(n > 0 and da == n, 'Mọi hộ đã lập phương án'), (tu == 0, 'Không còn hộ tự lập chưa soát')]
    if n and da + tu < n:
        viec.append(Viec(5, f'{n - da - tu} hộ chưa lập phương án', 'can', LENH_BUOC[5], n - da - tu))
    if tu:
        viec.append(Viec(5, f'{tu} hộ phần mềm tự lập, chưa soát lại', 'nhac', LENH_BUOC[5], tu))

    # 6, 7. niêm yết, lấy ý kiến
    co_ny = _bang_co(con, 'dot_du_thao') and _bang_co(con, 'y_kien_du_thao')
    dots = du_thao.ds_dot(con) if co_ny else []
    ny = tong_quan_du_an.niem_yet(con, nay) if dots else None
    so_ny = _dem(con, 'SELECT COUNT(DISTINCT ma_ho) FROM y_kien_du_thao') if co_ny else 0
    t = T[6]
    t.xong, t.tong = so_ny, max(co_pa, so_ny)
    t.dieu_kien = [(bool(dots), 'Có đợt niêm yết'), (bool(co_pa) and so_ny >= co_pa, 'Mọi hộ có phương án đã niêm yết')]
    if not dots:
        t.mo_ta = 'Chưa có đợt niêm yết'
        if co_pa:
            viec.append(Viec(6, f'{co_pa} hộ có phương án, chưa tạo đợt niêm yết', 'can', LENH_BUOC[6], co_pa))
    else:
        t.mo_ta = f'{so_ny} / {t.tong} hộ đã niêm yết ({len(dots)} đợt)'
        dang_chay = ny is not None and ny['con_ngay'] is not None and ny['con_ngay'] >= 0
        t.con_ngay = ny['con_ngay'] if dang_chay else None
        t.trang_thai = DANG if dang_chay or so_ny < co_pa else XONG
        if co_pa > so_ny:
            viec.append(Viec(6, f'{co_pa - so_ny} hộ có phương án chưa đưa vào đợt niêm yết', 'nhac', LENH_BUOC[6], co_pa - so_ny))
    tk = du_thao.thong_ke_y_kien(con) if co_ny and so_ny else None
    t = T[7]
    if tk:
        co_y = tk['dong_y'] + tk['khong_dong_y'] + tk['y_kien_khac']
        t.xong, t.tong = co_y, co_y + tk['chua']
        t.mo_ta = f'{tk["dong_y"]} đồng ý · {tk["khong_dong_y"]} không đồng ý · {tk["chua"]} chưa lấy ý kiến'
        t.trang_thai = XONG if tk['chua'] == 0 else DANG
        if ny is not None and ny['con_ngay_doi_thoai'] is not None:
            t.con_ngay = ny['con_ngay_doi_thoai']
            if t.con_ngay < 0 and tk['chua']:
                t.trang_thai = QUA_HAN
        if tk['chua']:
            viec.append(Viec(7, f'{tk["chua"]} lượt hộ chưa lấy ý kiến', 'loi' if t.trang_thai == QUA_HAN else 'can', LENH_BUOC[7],
                             tk['chua']))
        if tk['khong_dong_y']:
            viec.append(Viec(7, f'{tk["khong_dong_y"]} hộ không đồng ý: tổ chức đối thoại', 'nhac', LENH_BUOC[7], tk['khong_dong_y']))
        t.dieu_kien = [(tk['chua'] == 0, 'Mọi hộ đã niêm yết đều có ý kiến')]
    else:
        t.mo_ta = 'Chưa có hộ niêm yết'
        t.dieu_kien = [(False, 'Có hộ đã niêm yết và có ý kiến')]

    # 8. trình thẩm định (đợt trình), 9. quyết định phê duyệt
    # 1.0.91 (người dùng 09/11/2026): ĐÃ TRÌNH = đợt có văn bản trình (số + ngày tờ trình); đợt mới xếp hộ chưa tính
    from .quan_ly import dot_co_van_ban_trinh
    dot_vb = dot_co_van_ban_trinh(con)
    so_dot_trinh = len(dot_vb)
    ho_trinh = sum(1 for r in _cac_dong(con, 'SELECT dot_id FROM ho WHERE dot_id IS NOT NULL') if r[0] in dot_vb)
    dot_chua_vb = _dem(con, 'SELECT COUNT(*) FROM dot_trinh') - so_dot_trinh
    if dot_chua_vb > 0:
        viec.append(Viec(8, f'{dot_chua_vb} đợt trình chưa có số, ngày văn bản trình: hộ trong đợt chưa tính là đã trình', 'nhac',
                         LENH_BUOC[8], dot_chua_vb))
    pd = sum(1 for d in dong if d.get('da_phe_duyet'))
    t = T[8]
    _tien_do(t, max(ho_trinh, pd), co_pa, 'hộ có phương án đã trình thẩm định')
    if not co_pa:
        t.trang_thai, t.mo_ta = CHUA, 'Chưa có hộ có phương án để trình'
    t.dieu_kien = [(so_dot_trinh > 0 or pd > 0, 'Có đợt trình thẩm định'),
                   (bool(co_pa) and max(ho_trinh, pd) >= co_pa, 'Mọi hộ có phương án đã trình')]
    if co_pa and so_dot_trinh == 0 and pd == 0 and T[7].trang_thai == XONG:
        viec.append(Viec(8, 'Đã lấy xong ý kiến: lập đợt trình thẩm định', 'can', LENH_BUOC[8]))
    t = T[9]
    _tien_do(t, pd, n, 'hộ có quyết định phê duyệt')
    t.dieu_kien = [(n > 0 and pd == n, 'Mọi hộ có quyết định phê duyệt')]
    if ho_trinh > pd:
        viec.append(Viec(9, f'{ho_trinh - pd} hộ đã trình chưa có quyết định phê duyệt', 'nhac', LENH_BUOC[9], ho_trinh - pd))

    # 10, 11. công khai quyết định, gửi phương án đến hộ (chỉ nhắc khi đã có quyết định)
    _moc(con, T[10], 'công khai quyết định phê duyệt')
    _moc(con, T[11], 'gửi phương án đã duyệt đến hộ')
    for b in (10, 11):
        if pd and T[b].trang_thai != XONG:
            T[b].trang_thai = DANG
            viec.append(Viec(b, f'Đã có quyết định phê duyệt: ghi ngày {TEN_NGAN[b].lower()}', 'nhac'))   # nút "Ghi ngày"

    # 12. chi trả, 13. quyết định thu hồi, 14-15 vận động, 16 mặt bằng sạch
    ct = sum(1 for d in dong if d.get('da_chi_tra'))
    bg = sum(1 for d in dong if d.get('da_ban_giao'))
    t = T[12]
    _tien_do(t, ct, pd, 'hộ đã phê duyệt đã nhận tiền')
    if not pd:
        t.trang_thai, t.mo_ta = CHUA, 'Chưa có hộ được phê duyệt'
    t.dieu_kien = [(bool(pd) and ct >= pd, 'Mọi hộ đã phê duyệt đã nhận tiền')]
    _moc(con, T[13], 'quyết định thu hồi đất')
    cc = tong_quan_du_an.cuong_che(con, nay) if pd else dict(dang_vd=0, du_cc=0)
    t = T[14]
    chua_nhan = max(pd - ct, 0)
    t.xong, t.tong = ct, pd
    t.mo_ta = f'{chua_nhan} hộ chưa nhận tiền · {cc["dang_vd"]} đang vận động'
    t.trang_thai = CHUA if not pd else XONG if chua_nhan == 0 else QUA_HAN if cc['du_cc'] else DANG
    t.dieu_kien = [(chua_nhan == 0 and pd > 0, 'Không còn hộ chưa nhận tiền')]
    if cc['du_cc']:
        viec.append(Viec(14, f'{cc["du_cc"]} hộ đủ điều kiện đề nghị cưỡng chế', 'loi', LENH_BUOC[14], cc['du_cc']))
    elif chua_nhan and pd:
        viec.append(Viec(14, f'{chua_nhan} hộ đã phê duyệt chưa nhận tiền', 'nhac', LENH_BUOC[14], chua_nhan))
    t = T[15]
    chua_bg = max(ct - bg, 0)
    t.xong, t.tong = bg, ct
    t.mo_ta = f'{chua_bg} hộ đã nhận tiền chưa bàn giao mặt bằng'
    t.trang_thai = CHUA if not ct else XONG if chua_bg == 0 else DANG
    t.dieu_kien = [(chua_bg == 0 and ct > 0, 'Hộ đã nhận tiền đều đã bàn giao')]
    if chua_bg:
        viec.append(Viec(15, f'{chua_bg} hộ đã nhận tiền chưa bàn giao mặt bằng', 'nhac', LENH_BUOC[15], chua_bg))
    t = T[16]
    _tien_do(t, bg, n, 'hộ đã bàn giao mặt bằng')
    t.dieu_kien = [(n > 0 and bg == n, 'Mọi hộ đã bàn giao mặt bằng')]

    # bước hiện tại: bước nhỏ nhất đang làm / quá hạn; không có thì bước chưa tới đầu tiên sau bước xong cuối cùng
    dang = [b for b, t in T.items() if t.trang_thai in (DANG, QUA_HAN) and b >= 4]
    if dang:
        hien_tai = min(dang)
    else:
        da_xong = [b for b, t in T.items() if t.trang_thai == XONG]
        sau = [b for b in T if b > max(da_xong, default=0) and T[b].trang_thai == CHUA]
        hien_tai = min(sau) if sau else 16
    viec.sort(key=lambda v: (MUC_VIEC.index(v.muc), v.buoc))
    return KetQuaQuyTrinh(buoc=T, hien_tai=hien_tai, viec=viec[:VIEC_TOI_DA], so_ho=n)

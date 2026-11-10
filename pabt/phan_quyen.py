"""Phân quyền theo vai trò tài khoản máy chủ LAN (1.0.57 - đề án LARC V2.0 của người dùng 03/11/2026, Gói 2: 6 vai trò). Không Qt.

Áp dụng cho dự án của MÁY CHỦ LAN (file nằm trong thư mục máy chủ hoặc bản mang về offline của tài khoản): vai trò gắn vào kết nối
(`gan(con, vai_tro)` trong app.mo - như con._ho_nhan_viec). Máy đơn / file riêng trên máy / chưa đăng nhập: không giới hạn (như trước).
Hai vai trò cũ giữ nguyên quyền để máy chủ đang dùng không đổi gì: 'quan_tri' = mọi quyền, 'nguoi_dung' = mọi quyền trừ quản trị.

Ba lớp chặn (như khóa hộ nhận việc 1.0.41):
1. giao diện: `lenh_bi_tat(vai_tro)` (lệnh cửa sổ chính tắt), CuaSoLapPA khóa ô theo `quyen_bang(vai_tro, muc)`;
2. hàm ghi: `kiem(con, quyen, viec)` ở đầu hàm (LoiQuyen, thông báo tiếng Việt), `kiem_pa(con, pa_goc, pa_moi)` khi lưu phương án;
3. CSDL: `gan_chan_csdl(con, vai_tro)` TRIGGER TẠM chặn ghi bảng ngoài quyền (đường ghi lọt) - không ghi gì vào file.
Thanh tra: mở dự án CHỈ XEM (`chi_xem`).
"""
from __future__ import annotations

from .loi import LoiNhap      # 1.0.96: không nhập ngược lap_pa (tầng nghiệp vụ)

LANH_DAO, THAM_DINH, CHUYEN_VIEN, KIEM_DEM, KE_TOAN, THANH_TRA = (
    'lanh_dao', 'tham_dinh', 'chuyen_vien', 'kiem_dem', 'ke_toan', 'thanh_tra')
QUAN_TRI_CU, NGUOI_DUNG_CU = 'quan_tri', 'nguoi_dung'      # = may_chu.QUAN_TRI / NGUOI_DUNG (vai trò trước 1.0.57)

TEN_VAI_TRO = {
    LANH_DAO: 'Lãnh đạo (phê duyệt, mở khóa)',
    THAM_DINH: 'Thẩm định viên',
    CHUYEN_VIEN: 'Chuyên viên lập phương án',
    KIEM_DEM: 'Kiểm đếm viên',
    KE_TOAN: 'Kế toán chi trả',
    THANH_TRA: 'Thanh tra, kiểm toán (chỉ xem)',
}

# quyền
QUAN_TRI = 'quan_tri'               # tài khoản, máy chủ, phát hành bộ đơn giá
SUA_DON_GIA = 'sua_don_gia'         # bộ đơn giá, bảng giá đất, hệ số K (quan_tri_bo)
SUA_HO_SO = 'sua_ho_so'             # thêm / sửa hộ, thửa
XOA_HO = 'xoa_ho'
SUA_KHOI_LUONG = 'sua_khoi_luong'   # dòng tài sản / đất: tên, ĐVT, số lượng, thêm / bỏ dòng
SUA_GIA = 'sua_gia'                 # đơn giá, hệ số K, tỷ lệ của dòng phương án
SUA_HO_TRO = 'sua_ho_tro'           # mục chính sách hỗ trợ
KHOA_LAN = 'khoa_lan'               # khóa thẩm định lần phương án
MO_KHOA_LAN = 'mo_khoa_lan'
LAP_BO_SUNG = 'lap_bo_sung'         # lập / sửa / xóa lần phương án bổ sung, điều chỉnh
QD_CHI_TRA = 'qd_chi_tra'           # quyết định phê duyệt, chi trả, bàn giao, vận động
NIEM_YET = 'niem_yet'               # niêm yết, ý kiến, đối thoại, đợt trình, số phương án
KHOI_PHUC_MOC = 'khoi_phuc_moc'     # Cỗ máy thời gian: khôi phục mốc
XEM_KIEM_TOAN = 'xem_kiem_toan'

TAT_CA = frozenset((QUAN_TRI, SUA_DON_GIA, SUA_HO_SO, XOA_HO, SUA_KHOI_LUONG, SUA_GIA, SUA_HO_TRO, KHOA_LAN, MO_KHOA_LAN,
                    LAP_BO_SUNG, QD_CHI_TRA, NIEM_YET, KHOI_PHUC_MOC, XEM_KIEM_TOAN))
QUYEN = {
    QUAN_TRI_CU: TAT_CA,
    NGUOI_DUNG_CU: TAT_CA - {QUAN_TRI, SUA_DON_GIA},
    LANH_DAO: frozenset((QUAN_TRI, SUA_DON_GIA, XOA_HO, KHOA_LAN, MO_KHOA_LAN, QD_CHI_TRA, NIEM_YET, KHOI_PHUC_MOC, XEM_KIEM_TOAN)),
    THAM_DINH: frozenset((KHOA_LAN, XEM_KIEM_TOAN)),
    CHUYEN_VIEN: frozenset((SUA_HO_SO, XOA_HO, SUA_KHOI_LUONG, SUA_GIA, SUA_HO_TRO, LAP_BO_SUNG, NIEM_YET, XEM_KIEM_TOAN)),
    KIEM_DEM: frozenset((SUA_HO_SO, SUA_KHOI_LUONG)),
    KE_TOAN: frozenset((QD_CHI_TRA, XEM_KIEM_TOAN)),
    THANH_TRA: frozenset((XEM_KIEM_TOAN,)),
}
TEN_QUYEN = {SUA_HO_SO: 'sửa hồ sơ hộ, thửa', XOA_HO: 'xóa hộ', SUA_KHOI_LUONG: 'sửa khối lượng kiểm đếm', SUA_GIA: 'sửa đơn giá, tỷ lệ',
             SUA_HO_TRO: 'áp chính sách hỗ trợ', KHOA_LAN: 'khóa thẩm định phương án', MO_KHOA_LAN: 'mở khóa phương án',
             LAP_BO_SUNG: 'lập phương án bổ sung / điều chỉnh', QD_CHI_TRA: 'ghi quyết định, chi trả, bàn giao',
             NIEM_YET: 'niêm yết, lấy ý kiến, đợt trình', KHOI_PHUC_MOC: 'khôi phục mốc thời gian', QUAN_TRI: 'quản trị hệ thống',
             SUA_DON_GIA: 'sửa bộ đơn giá', XEM_KIEM_TOAN: 'xem nhật ký kiểm toán'}


class LoiQuyen(LoiNhap):
    """Vai trò của tài khoản không có quyền làm việc này."""


def ten_vai_tro(vai_tro: str | None) -> str:
    from .may_chu import TEN_VAI_TRO as CU
    return TEN_VAI_TRO.get(vai_tro or '', CU.get(vai_tro or '', vai_tro or ''))


def quyen_cua(vai_tro: str | None) -> frozenset:
    """Quyền của vai trò. None (máy đơn, file riêng, chưa đăng nhập) = mọi quyền; vai trò lạ (máy chủ phiên bản mới hơn) = chỉ xem."""
    if vai_tro is None:
        return TAT_CA
    return QUYEN.get(vai_tro, frozenset())


def co(vai_tro: str | None, quyen: str) -> bool:
    return quyen in quyen_cua(vai_tro)


def chi_xem(vai_tro: str | None) -> bool:
    """Vai trò không ghi được gì vào dự án -> mở dự án CHỈ XEM (file mode=ro: chắc chắn nhất)."""
    return vai_tro is not None and not (quyen_cua(vai_tro) - {XEM_KIEM_TOAN, QUAN_TRI, SUA_DON_GIA})


# ---------------------------------------------------------------- vai trò của kết nối dự án
def gan(con, vai_tro: str | None) -> None:
    """Gắn vai trò vào kết nối dự án (app.mo) + trigger tạm chặn ghi ngoài quyền."""
    try:
        con._vai_tro = vai_tro
    except AttributeError:                              # sqlite3.Connection thường (không phải csdl.KetNoi)
        return
    if vai_tro is not None:
        gan_chan_csdl(con, vai_tro)


def vai_tro_cua(con) -> str | None:
    return getattr(con, '_vai_tro', None)


def kiem(con, quyen: str, viec: str = '') -> None:
    """Gọi đầu hàm ghi: vai trò của kết nối không có quyền -> LoiQuyen."""
    vt = vai_tro_cua(con)
    if vt is not None and quyen not in quyen_cua(vt):
        raise LoiQuyen(f'Tài khoản vai trò "{ten_vai_tro(vt)}" không được {viec or TEN_QUYEN.get(quyen, quyen)}.')


def vai_tro_cho_file(file) -> str | None:
    """Vai trò áp cho file dự án: file trong thư mục máy chủ (đang đăng nhập) hoặc bản mang về offline -> vai trò tài khoản; file riêng
    trên máy -> None (không giới hạn)."""
    from pathlib import Path
    from . import may_chu
    if file is None:
        return None
    p = Path(file).resolve()
    if may_chu.PHIEN is not None:
        try:
            p.relative_to(Path(may_chu.PHIEN.goc).resolve())
            return may_chu.PHIEN.vai_tro
        except ValueError:
            pass
    try:
        off = Path(may_chu.thu_muc_offline()).resolve()
        p.relative_to(off)
    except (ValueError, OSError, AttributeError):
        return None
    for muc in may_chu.ds_lay_ve_cuc_bo():
        try:
            if Path(muc.get('ban_sao') or muc.get('file') or '').resolve() == p:
                if may_chu.PHIEN is not None and muc.get('tai_khoan') == may_chu.PHIEN.tai_khoan:
                    return may_chu.PHIEN.vai_tro
                return muc.get('vai_tro') or (may_chu.PHIEN.vai_tro if may_chu.PHIEN is not None else None)
        except (OSError, TypeError):
            continue
    return may_chu.PHIEN.vai_tro if may_chu.PHIEN is not None else None


# ---------------------------------------------------------------- phương án: so bản lưu với bản lúc mở
def _ds_khoan(pa) -> list:
    """PhuongAn.khoan là {mục: [DongKhoan]}."""
    if pa is None:
        return []
    k = pa.khoan
    return [d for ds in (k.values() if isinstance(k, dict) else [k]) for d in ds]


def _ds_dat(pa) -> list:
    return list(pa.dat) if pa is not None else []


def _dong_khoan(d) -> tuple:
    return (d.muc, d.ma, d.ten, d.dvt, str(d.so_luong), str(d.don_gia), str(d.ty_le), d.ghi_chu, getattr(d, 'cach_tinh', ''))


def _gia_khoan(d) -> tuple:
    return (d.muc, d.ma, d.ten, str(d.don_gia), str(d.ty_le))


def _dong_dat(d) -> tuple:
    return (str(d.ma_thua), d.loai_dat, d.vi_tri, str(d.dien_tich), str(d.gia_bang_gia), str(d.he_so_k), str(d.ty_le), d.ghi_chu)


def _gia_dat(d) -> tuple:
    return (str(d.ma_thua), d.loai_dat, str(d.gia_bang_gia), str(d.he_so_k), str(d.ty_le))


def kiem_pa(con, pa_goc, pa_moi, dm=None) -> None:
    """BoSoan.luu: vai trò thiếu quyền mà phần tương ứng của phương án đổi -> LoiQuyen. Kiểm đếm viên: dòng mới phải lấy đúng đơn giá
    danh mục (dm.lay) hoặc chưa có giá; dòng đã có giữ nguyên đơn giá / tỷ lệ; mục hỗ trợ không đổi."""
    vt = vai_tro_cua(con)
    if vt is None:
        return
    q = quyen_cua(vt)
    if not ({SUA_KHOI_LUONG, SUA_GIA, SUA_HO_TRO} & q):
        if pa_goc is None or _so_pa(pa_goc) != _so_pa(pa_moi):
            raise LoiQuyen(f'Tài khoản vai trò "{ten_vai_tro(vt)}" chỉ xem phương án, không lưu được thay đổi.')
        return
    goc_k = [d for d in _ds_khoan(pa_goc) if d.muc == 4]
    moi_k = [d for d in _ds_khoan(pa_moi) if d.muc == 4]
    if SUA_HO_TRO not in q and sorted(map(_dong_khoan, goc_k)) != sorted(map(_dong_khoan, moi_k)):
        raise LoiQuyen(f'Tài khoản vai trò "{ten_vai_tro(vt)}" không được áp / sửa chính sách hỗ trợ.')
    if SUA_KHOI_LUONG not in q:
        a = (sorted(map(_dong_khoan, [d for d in _ds_khoan(pa_goc) if d.muc != 4])), sorted(map(_dong_dat, _ds_dat(pa_goc))))
        b = (sorted(map(_dong_khoan, [d for d in _ds_khoan(pa_moi) if d.muc != 4])), sorted(map(_dong_dat, _ds_dat(pa_moi))))
        if a != b and not _chi_doi_gia(pa_goc, pa_moi):
            raise LoiQuyen(f'Tài khoản vai trò "{ten_vai_tro(vt)}" không được sửa khối lượng kiểm đếm.')
    if SUA_GIA not in q:
        cu = set(map(_gia_khoan, _ds_khoan(pa_goc))) | set(map(_gia_dat, _ds_dat(pa_goc)))
        for d in _ds_khoan(pa_moi):
            if d.muc == 4 or _gia_khoan(d) in cu:
                continue
            if not _gia_danh_muc(d, dm):
                raise LoiQuyen(f'Tài khoản vai trò "{ten_vai_tro(vt)}" không được sửa đơn giá / tỷ lệ ("{d.ten}"): đơn giá lấy theo bộ '
                               'đơn giá, tỷ lệ 100% - chuyên viên lập phương án áp giá.')
        for d in _ds_dat(pa_moi):
            if _gia_dat(d) not in cu and (d.ty_le != 1 or d.he_so_k != 1):
                raise LoiQuyen(f'Tài khoản vai trò "{ten_vai_tro(vt)}" không được sửa hệ số K / tỷ lệ giá đất.')


def _so_pa(pa) -> tuple:
    return (sorted(map(_dong_khoan, _ds_khoan(pa))), sorted(map(_dong_dat, _ds_dat(pa))))


def _chi_doi_gia(pa_goc, pa_moi) -> bool:
    """Chỉ giá / tỷ lệ đổi (cùng dòng, cùng khối lượng) - vai trò có quyền giá mà không có quyền khối lượng."""
    def kl_k(d):
        return (d.muc, d.ma, d.ten, d.dvt, str(d.so_luong))

    def kl_d(d):
        return (str(d.ma_thua), d.loai_dat, str(d.dien_tich))
    return (sorted(map(kl_k, _ds_khoan(pa_goc))) == sorted(map(kl_k, _ds_khoan(pa_moi)))
            and sorted(map(kl_d, _ds_dat(pa_goc))) == sorted(map(kl_d, _ds_dat(pa_moi))))


def _gia_danh_muc(d, dm) -> bool:
    """Dòng mới của kiểm đếm viên: đơn giá = giá danh mục của mã (hoặc 0 / trống - chuyên viên áp giá sau), tỷ lệ 100%."""
    from decimal import Decimal, InvalidOperation
    try:
        tl = Decimal(str(d.ty_le or '1'))
    except (InvalidOperation, ValueError):
        return False
    if tl != 1:
        return False
    try:
        gia = Decimal(str(d.don_gia or '0'))
    except (InvalidOperation, ValueError):
        return False
    if gia == 0:
        return True
    if dm is None or not d.ma:
        return False
    r = dm.lay(d.ma) if hasattr(dm, 'lay') else None
    return r is not None and r.don_gia is not None and Decimal(str(r.don_gia)) == gia


def kiem_xoa_ho(con, ds_ma_ho) -> None:
    """Đề án ABAC: không vai trò nào xóa hộ đã có quyết định phê duyệt / đã chi trả; chuyên viên chỉ xóa hộ chưa lập phương án."""
    vt = vai_tro_cua(con)
    if vt is None or vt in (QUAN_TRI_CU, NGUOI_DUNG_CU):
        return
    ds = [int(m) for m in ds_ma_ho or () if m is not None]
    for m in ds:
        r = con.execute('SELECT ho_ten, da_phe_duyet, da_chi_tra FROM ho WHERE ma_ho = ?', (m,)).fetchone()
        if r is None:
            continue
        co_qd = bool(r[1] or r[2]) or (_co_bang(con, 'qd_ho') and con.execute(
            'SELECT 1 FROM qd_ho WHERE ma_ho = ? LIMIT 1', (m,)).fetchone() is not None)
        if co_qd:
            raise LoiQuyen(f'Hộ {r[0] or m} đã có quyết định phê duyệt / đã chi trả: không xóa được (lập phương án điều chỉnh nếu cần).')
        if vt == CHUYEN_VIEN and (con.execute('SELECT 1 FROM ct_dat WHERE ma_ho = ? LIMIT 1', (m,)).fetchone()
                                  or con.execute('SELECT 1 FROM ct_khoan WHERE ma_ho = ? LIMIT 1', (m,)).fetchone()):
            raise LoiQuyen(f'Hộ {r[0] or m} đã lập phương án: vai trò "{ten_vai_tro(vt)}" chỉ xóa hộ chưa lập - đề nghị lãnh đạo.')


def _co_bang(con, bang: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (bang,)).fetchone() is not None


# ---------------------------------------------------------------- tầng CSDL: trigger tạm
BANG_PA = ('ct_dat', 'ct_khoan')
BANG_QD = ('quyet_dinh', 'qd_ho')
BANG_NIEM_YET = ('dot_du_thao', 'y_kien_du_thao', 'doi_thoai_ho', 'dot_trinh')
COT_HO_SO = ('ho_ten', 'so_cccd', 'ngay_cap', 'noi_cap', 'dia_chi', 'dien_thoai', 'phap_ly', 'tranh_chap', 'tai_dinh_cu', 'ghi_chu', 'ghi_chu_ten',
             'phai_di_chuyen', 'nhan_khau', 'dt_nn_dang_dung')


def _cot(con, bang: str) -> set:
    return {r[1] for r in con.execute(f'PRAGMA main.table_info("{bang}")')}


def gan_chan_csdl(con, vai_tro: str) -> int:
    """Trigger tạm chặn ghi các bảng ngoài quyền của vai trò (đường ghi lọt kiểm tra ở hàm). Trả số trigger tạo."""
    q = quyen_cua(vai_tro)
    co_bang = {r[0] for r in con.execute("SELECT name FROM main.sqlite_master WHERE type = 'table'")}
    chan = []                                           # (bảng, sự kiện, điều kiện WHEN, lý do)
    if not ({SUA_KHOI_LUONG, SUA_GIA, SUA_HO_TRO} & q):
        chan += [(b, ev, '', 'không sửa phương án') for b in BANG_PA for ev in ('INSERT', 'UPDATE', 'DELETE')]
    if QD_CHI_TRA not in q:
        chan += [(b, ev, '', 'không ghi quyết định, chi trả') for b in BANG_QD for ev in ('INSERT', 'UPDATE', 'DELETE')]
    if NIEM_YET not in q:
        chan += [(b, ev, '', 'không ghi niêm yết, đợt trình') for b in BANG_NIEM_YET for ev in ('INSERT', 'UPDATE', 'DELETE')]
    if SUA_HO_SO not in q:
        chan += [('thua', ev, '', 'không sửa thửa đất') for ev in ('INSERT', 'UPDATE', 'DELETE')]
        chan.append(('ho', 'INSERT', '', 'không thêm hộ'))
        if 'ho' in co_bang:
            cot = [c for c in COT_HO_SO if c in _cot(con, 'ho')]
            if cot:
                chan.append(('ho', 'UPDATE OF ' + ', '.join(cot), '', 'không sửa hồ sơ hộ'))
    if XOA_HO not in q:
        chan.append(('ho', 'DELETE', '', 'không xóa hộ'))
    else:                                               # đề án: không xóa hộ đã có quyết định phê duyệt / đã chi trả
        chan.append(('ho', 'DELETE', 'OLD.da_phe_duyet = 1 OR OLD.da_chi_tra = 1', 'không xóa hộ đã có quyết định phê duyệt / đã '
                     'chi trả (lập phương án điều chỉnh nếu cần)'))
    n = 0
    for i, (bang, ev, khi, ly_do) in enumerate(chan):
        if bang not in co_bang:
            continue
        if khi and not {'da_phe_duyet', 'da_chi_tra'} <= _cot(con, bang):
            continue
        tb = f'Tài khoản vai trò "{ten_vai_tro(vai_tro)}": {ly_do}.'.replace("'", "''")
        con.execute(f'DROP TRIGGER IF EXISTS temp._pq_{i}')
        con.execute(f'CREATE TEMP TRIGGER _pq_{i} BEFORE {ev} ON main."{bang}"' + (f' WHEN {khi}' if khi else '')
                    + f" BEGIN SELECT RAISE(ABORT, '{tb}'); END")
        n += 1
    return n


# ---------------------------------------------------------------- giao diện: lệnh cửa sổ chính cần quyền
LENH_QUYEN = {
    'Thêm hộ…': SUA_HO_SO, 'Xóa hộ…': XOA_HO, 'Chọn hộ niêm yết…': NIEM_YET, 'Dự thảo PABT…': NIEM_YET, 'Đợt trình…': NIEM_YET,
    'Trạng thái hộ…': QD_CHI_TRA, 'Nhật ký kiểm toán…': XEM_KIEM_TOAN, 'Quản lý tài khoản…': QUAN_TRI,
    'Nhập file Excel…': SUA_HO_SO, 'Nhập phương án chi tiết…': SUA_HO_SO, 'Nhập bản vẽ CAD (.dxf)…': SUA_HO_SO,
}


def lenh_bi_tat(vai_tro: str | None, ds_lenh) -> list:
    """Các lệnh (trong ds_lenh) vai trò không có quyền dùng."""
    q = quyen_cua(vai_tro)
    return [t for t in ds_lenh if t in LENH_QUYEN and LENH_QUYEN[t] not in q]


def quyen_bang(vai_tro: str | None, muc: int) -> dict:
    """Ô sửa được của bảng mục phương án: {'khoi_luong': bool, 'gia': bool, 'them_xoa': bool} (mục 4 = chính sách hỗ trợ)."""
    q = quyen_cua(vai_tro)
    if muc == 4:
        hd = SUA_HO_TRO in q
        return dict(khoi_luong=hd, gia=hd, them_xoa=hd)
    return dict(khoi_luong=SUA_KHOI_LUONG in q, gia=SUA_GIA in q, them_xoa=SUA_KHOI_LUONG in q)


def ma_tran() -> list:
    """[(quyền, {vai trò: True/False})] - bảng ma trận phân quyền (màn hình tài khoản, hướng dẫn)."""
    return [(TEN_QUYEN.get(qq, qq), {vt: qq in QUYEN[vt] for vt in TEN_VAI_TRO}) for qq in
            (SUA_HO_SO, XOA_HO, SUA_KHOI_LUONG, SUA_GIA, SUA_HO_TRO, LAP_BO_SUNG, KHOA_LAN, MO_KHOA_LAN, NIEM_YET, QD_CHI_TRA,
             KHOI_PHUC_MOC, SUA_DON_GIA, QUAN_TRI, XEM_KIEM_TOAN)]

"""Nhập tài sản (nhà, công trình / cây trồng / vật nuôi / hỗ trợ) - MỘT bộ lệnh dùng chung cho lập phương án hộ (CuaSoLapPA) và
Dự toán & khái toán (KhungDuToan) - người dùng 12/10/2026: "dùng chung công cụ gọi lệnh ... tránh gọi nhiều lệnh trùng nhau".

  - `them_mot(dich, muc, m, ten, so_luong, ty_le, kieu, ghi_chu)`: hàng nhập nhanh (chọn trong danh mục hoặc tên gõ tự do,
    số lượng / công thức, tỷ lệ %, ghi chú; mục 3 kiểu 'dk' / 'cv' = các số đo đường kính / chu vi thân tự xếp vào quy cách).
  - `them_dong_tho(dich, muc, khop, ten, dvt, so_luong, ty_le, ghi_chu)`: một dòng của hộp "Dán danh sách tài sản".
  - "Đích" ghi: `DichPhuongAn` (BoSoan của một hộ) / `DichDuToan` (danh sách DongDT của dự toán) - cùng giao diện
    dm / them_danh_muc / them_tu_do / dat_so_luong / dat_ty_le / dat_ghi_chu / dat_quy_cach / dat_dvt.
Không dùng Qt (chạy được trong test, dùng chung Qt5 / Qt6). Chính sách hỗ trợ có cách tính riêng theo hộ (ổn định đời sống,
đào tạo nghề theo thửa, thuê nhà theo nhân khẩu) vẫn ở CuaSoLapPA - dự toán nhập khối lượng × đơn giá.
"""
from __future__ import annotations

from . import lap_pa
from .loi import LoiNhap
from .tien import D, KHONG, so_vn


def la_tu_do(m) -> bool:
    """Tên gõ tự do / chính sách không có trong đơn giá ('ten', tên)."""
    return m is None or (isinstance(m, tuple) and m[0] == 'ten')


class DichPhuongAn:
    """Ghi vào phương án của một hộ (lap_pa.BoSoan)."""

    def __init__(self, bo):
        self.bo = bo

    @property
    def dm(self):
        return self.bo.dm

    def them_danh_muc(self, muc: int, m) -> tuple:
        if m.nguon == 'quyuoc':
            i = self.bo.them_hang_muc_khac(muc, m.ten)
            self.bo.ap_gia_tuong_duong(muc, i, m)
            return i, ''
        return self.bo.them_tu_danh_muc(muc, m)

    def them_tu_do(self, muc: int, ten: str) -> int:
        return self.bo.them_hang_muc_khac(muc, ten)

    def dat_so_luong(self, muc: int, i: int, text: str) -> None:
        self.bo.sua_khoan(muc, i, 'so_luong', text)

    def dat_ty_le(self, muc: int, i: int, ty) -> None:
        self.bo.pa.khoan[muc][i].ty_le = ty

    def dat_ghi_chu(self, muc: int, i: int, gc: str) -> None:
        self.bo.pa.khoan[muc][i].ghi_chu = gc

    def dat_quy_cach(self, muc: int, i: int, qc: str) -> None:
        self.bo.sua_khoan(muc, i, 'quy_cach', qc)

    def dat_dvt(self, muc: int, i: int, dvt: str) -> None:
        self.bo.sua_khoan(muc, i, 'dvt', dvt)


class DichDuToan:
    """Ghi vào bảng Dự toán & khái toán (du_toan.DuToan.dong). Vật nuôi gộp mục 3 (du_toan.muc_du_toan); chỉ số trả về là vị
    trí dòng trong dt.dong."""

    def __init__(self, dt, dm):
        self.dt, self._dm = dt, dm

    @property
    def dm(self):
        return self._dm

    def _them(self, d) -> int:
        self.dt.dong.append(d)
        return len(self.dt.dong) - 1

    def them_danh_muc(self, muc: int, m) -> tuple:
        from .du_toan import DongDT, muc_du_toan
        mm = muc_du_toan(muc)
        don_gia = m.don_gia if (m.don_gia is not None and not (mm == 4 and m.don_gia < 100)) else KHONG   # hệ số < 100: không phải tiền
        can_cu = m.can_cu if m.nguon != 'quyuoc' else f'{m.phan_loai}; {m.can_cu}'.strip('; ')
        return self._them(DongDT(mm, m.ten, m.dvt, D(1) if mm == 4 else KHONG, don_gia, D(1), m.ma, can_cu)), ''

    def them_tu_do(self, muc: int, ten: str) -> int:
        from .du_toan import DongDT, muc_du_toan
        ten = ' '.join(str(ten or '').split())
        if not ten:
            raise LoiNhap('Nhập tên hoặc mô tả hạng mục.')
        mm = muc_du_toan(muc)
        return self._them(DongDT(mm, ten, '', D(1) if mm == 4 else KHONG))

    def dat_so_luong(self, muc: int, i: int, text: str) -> None:
        d = self.dt.dong[i]
        d.khoi_luong = lap_pa.doc_so_luong(text, d.dvt)

    def dat_ty_le(self, muc: int, i: int, ty) -> None:
        self.dt.dong[i].he_so = D(ty)                    # hệ số = tỷ lệ bồi thường, hỗ trợ (1 = 100%)

    def dat_ghi_chu(self, muc: int, i: int, gc: str) -> None:
        self.dt.dong[i].ghi_chu = gc

    def dat_quy_cach(self, muc: int, i: int, qc: str) -> None:
        d = self.dt.dong[i]
        d.ghi_chu = '; '.join(x for x in (qc, d.ghi_chu) if x)

    def dat_dvt(self, muc: int, i: int, dvt: str) -> None:
        self.dt.dong[i].dvt = dvt


def them_mot(dich, muc: int, m, ten: str = '', so_luong: str = '', ty_le: str = '', kieu: str = 'sl',
             ghi_chu: str = '', so_do: str = '') -> tuple:
    """Hàng nhập nhanh -> (chỉ số dòng cuối đã thêm, thông báo, tự do?). Lỗi -> LoiNhap (thông báo tiếng Việt).
    Kiểu 'dk' / 'cv' (cây theo đường kính / chu vi thân): so_do = các số đo, so_luong = số cây mỗi số đo (trống = 1) - 0.9.71;
    không có so_do thì so_luong là các số đo (cách gọi trước 0.9.71)."""
    sl, tl, gc, do = (so_luong or '').strip(), (ty_le or '').strip(), (ghi_chu or '').strip(), (so_do or '').strip()
    ty = lap_pa.doc_ty_le(tl) if tl else None
    if kieu in ('dk', 'cv'):
        i, tb = _them_theo_do(dich, m, do or sl, kieu, ty, gc, sl if do else '')
        return i, tb, False
    if isinstance(m, tuple) and m[0] == 'nhom':
        raise LoiNhap('Loại cây này nhập theo số đo: chọn "Đường kính" hoặc "Chu vi" rồi gõ các số đo (cm).')
    tu_do = la_tu_do(m)
    if isinstance(m, tuple):
        ten = m[1]
    ten = (ten or '').strip()
    if tu_do and not ten:
        raise LoiNhap('Chọn trong danh sách hoặc gõ tên hạng mục.')
    if sl:
        lap_pa.doc_so_luong(sl, m.dvt if not tu_do else '')     # kiểm tra trước khi thêm dòng (gõ sai: không thêm)
    if tu_do:
        i = dich.them_tu_do(muc, ten)
        tb = f'"{ten}" không có trong đơn giá: gõ đơn giá ở cột Đơn giá; ghi quy định, cách tính ở cột Ghi chú.'
    else:
        i, tb = dich.them_danh_muc(muc, m)
    if sl:
        dich.dat_so_luong(muc, i, sl)
    if ty is not None:
        dich.dat_ty_le(muc, i, ty)
    if gc:
        dich.dat_ghi_chu(muc, i, gc)
    return i, tb, tu_do


def _them_theo_do(dich, m, text: str, kieu: str, ty, gc: str = '', so_cay: str = '') -> tuple:
    """Cây có quy cách theo đường kính / chu vi thân: các số đo (15, 18x2, 22) -> số cây từng quy cách đơn giá. so_cay: số cây
    cho mỗi số đo (ô Khối lượng; trống = 1): "23" + 100 = 100 cây đường kính 23 cm."""
    from . import cay_trong as ct
    bang = ct.BangCayDK(dich.dm.muc[3])
    if isinstance(m, tuple):
        ten_loai = m[1]
    elif m is not None and ct.khoang_duong_kinh(m.ten) is not None:
        ten_loai = ct.ten_loai_dk(m.ten)
    else:
        raise LoiNhap('Chọn loại cây có quy cách theo đường kính thân (tên loại không có mã, ví dụ "Sao đen"), chọn kiểu '
                      'Đường kính / Chu vi.')
    try:
        ds = ct.doc_ds_chu_vi(text)
    except ValueError as e:
        raise LoiNhap(str(e).replace('chu vi (cm)', 'số đo (cm)')) from None
    if not ds:
        raise LoiNhap('Gõ các số đo (cm), cách nhau dấu phẩy; nhiều cây cùng số đo ghi 52x3.')
    if so_cay:
        n = lap_pa.doc_so(so_cay, 'Số cây')
        if n is None or n <= 0 or n != n.to_integral_value():
            raise LoiNhap('Số cây (ô Khối lượng) phải là số nguyên lớn hơn 0.')
        ds = [(do, so * int(n)) for do, so in ds]
    la_dk = kieu == 'dk'
    nhom, loi = ct.gom_theo_kich_thuoc(bang, ten_loai, ds, la_dk)
    if not nhom:
        raise LoiNhap(f'Số đo không thuộc quy cách nào của {ten_loai}: ' + ', '.join(so_vn(x) for x in loi))
    i = None
    for mm, so, a, z in nhom:
        i, _ = dich.them_danh_muc(3, mm)
        dich.dat_so_luong(3, i, str(so))
        dich.dat_quy_cach(3, i, ct.mo_ta_do(a, z, la_dk))
        if ty is not None:
            dich.dat_ty_le(3, i, ty)
        if gc:
            dich.dat_ghi_chu(3, i, gc)
    tb = f'Đã thêm {sum(x[1] for x in nhom)} cây vào {len(nhom)} quy cách.'
    if loi:
        tb += f' Không khớp quy cách nào (chưa thêm): {", ".join(so_vn(x) for x in loi)} cm.'
    return i, tb


def them_dong_tho(dich, muc: int, khop, ten: str, dvt: str = '', so_luong: str = '', ty_le: str = '',
                  ghi_chu: str = '') -> int:
    """Một dòng đã phân loại của hộp "Dán danh sách tài sản": khớp danh mục -> dòng danh mục, không thì hạng mục ngoài danh mục
    (giữ ĐVT đã dán). Tỷ lệ: "80" / "80%" = 80%, số <= 5 không có % = hệ số (0,8)."""
    if khop is not None:
        i, _ = dich.them_danh_muc(muc, khop)
    else:
        i = dich.them_tu_do(muc, ten)
        if dvt:
            dich.dat_dvt(muc, i, dvt)
    if so_luong:
        dich.dat_so_luong(muc, i, so_luong)
    if ty_le:
        so = lap_pa.doc_so(ty_le.rstrip('%'), 'Tỷ lệ')
        dich.dat_ty_le(muc, i, so if so <= 5 and not ty_le.endswith('%') else lap_pa.doc_ty_le(ty_le))
    if ghi_chu:
        dich.dat_ghi_chu(muc, i, ghi_chu)
    return i

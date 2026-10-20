"""Bộ căn trang thông minh bản in phương án chi tiết (người dùng 20/10/2026 - lỗi "trang thứ 2 mồ côi": vài dòng cuối + chữ ký lẻ loi
sang trang 2). Chạy SAU khi in_an.ngat_trang_ct đã xếp trang (xep_trang / co_gian_vua_trang), TRƯỚC khi ghi ngắt trang tay - không
phải bộ dàn trang thứ hai, chỉ thêm ba quyết định:

  1. an_dong_trong_khoi_i: dòng "Số CCCD:" / "Số điện thoại:" của mục I không có số liệu thì ẨN (không để dòng trống đẩy bảng).
  2. gom_mot_trang: tổng nội dung chỉ tràn một trang A4 <= nguong_du_1_trang_pt (mặc định NGUONG_DU_1_TRANG_PT): thu tỷ lệ in
     (1.0.07: không dưới in_an.TI_LE_CT_MIN 70% - không bật "vừa N trang"), bỏ ngắt trang tay và dòng tiêu đề lặp; thu tới 70% vẫn
     không vừa thì giữ 2 trang. Tràn nhiều hơn: GIỮ 2 trang (co cả trang cho vừa thì chữ quá nhỏ để ký duyệt).
  3. can_bang_hai_trang: phương án 2 trang mà trang 2 bắt đầu GIỮA một mục: dời chỗ ngắt lên ngay trước dòng tiêu đề mục gần nhất
     (trang 1 kết thúc trọn ở cuối mục trước, trang 2 bắt đầu trọn từ mục đó tới khung chữ ký) - khi trang 2 vẫn vừa và trang 1 còn
     dùng >= TRANG_1_TOI_THIEU chiều cao trang.

Không Qt. Hàm nhận ws (openpyxl) và danh sách trang [(dòng đầu, dòng cuối, chiều cao đã dùng)] như in_an.xep_trang.
"""
from __future__ import annotations

NGUONG_DU_1_TRANG_PT = 120.0     # tràn <= chừng này (pt, đơn vị sheet) thì gom vừa 1 trang (~5 dòng bảng)
TRANG_1_TOI_THIEU = 0.5          # cân bằng 2 trang: trang 1 phải dùng ít nhất 50% chiều cao trang
NHAN_AN_KHI_TRONG = {            # nhãn mục I (chữ thường, bỏ ":") -> khóa số liệu (in_an._thong_tin_ho)
    'số cccd': 'cccd', 'cccd': 'cccd', 'số cccd/cmnd': 'cccd', 'số cmnd': 'cccd',
    'số điện thoại': 'dien_thoai', 'điện thoại': 'dien_thoai', 'sđt': 'dien_thoai',
}


class BoCanhTrangInAn:
    """Các bước căn trang - gọi qua tu_dong_chinh_trang (in_an.ngat_trang_ct) hoặc từng bước (kiểm thử)."""

    @staticmethod
    def an_dong_trong_khoi_i(ws, den_dong: int, gia_tri: dict) -> list:
        """Ẩn dòng mục I có nhãn trong NHAN_AN_KHI_TRONG mà số liệu tương ứng trống. Trả các dòng đã ẩn."""
        from .in_an import _o_chu
        an = []
        for o in list(_o_chu(ws, den_dong)):
            k = o.value.strip().rstrip(':').strip().lower()
            khoa = NHAN_AN_KHI_TRONG.get(k)
            if khoa is not None and not str(gia_tri.get(khoa) or '').strip():
                ws.row_dimensions[o.row].hidden = True
                an.append(o.row)
        return an

    @staticmethod
    def dat_kho_a4_doc(ws) -> None:
        """A4 dọc cho phương án chi tiết (lề: in_an.chuan_le_trang, LE_TRANG['chi_tiet'])."""
        ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
        ws.page_setup.paperSize = ws.PAPERSIZE_A4

    @staticmethod
    def tong_noi_dung(ws, trang: list) -> float:
        """Chiều cao toàn bộ nội dung (pt) - không tính dòng tiêu đề lặp đầu các trang sau."""
        from .in_an import _ham_cao
        if not trang:
            return 0.0
        cao = _ham_cao(ws)
        return sum(cao(r) for r in range(trang[0][0], trang[-1][1] + 1))

    @staticmethod
    def gom_mot_trang(ws, trang: list, cap: float, nguong_pt: float | None = None) -> bool:
        """Nhiều trang mà nội dung chỉ tràn <= nguong_pt (None: NGUONG_DU_1_TRANG_PT lúc gọi) so với sức chứa một trang (cap): thu tỷ lệ
        in cho vừa 1 trang (>= in_an.TI_LE_CT_MIN), bỏ ngắt tay / tiêu đề lặp. Trả True khi đã gom."""
        nguong_pt = NGUONG_DU_1_TRANG_PT if nguong_pt is None else nguong_pt
        if len(trang) < 2 or nguong_pt < 0:
            return False
        noi_dung = BoCanhTrangInAn.tong_noi_dung(ws, trang)
        tran = noi_dung - cap
        if tran > nguong_pt or noi_dung <= 0:
            return False
        # 1.0.07 (người dùng 20/10/2026: tắt "vừa N trang", tỷ lệ 70 - 73%): thu TỶ LỆ IN cho vừa một trang, không dưới
        # in_an.TI_LE_CT_MIN - không vừa thì giữ 2 trang
        from openpyxl.worksheet.properties import PageSetupProperties
        from .in_an import TI_LE_CT_MIN
        ti_le = int(ws.page_setup.scale or 100)
        moi = int(ti_le * cap / noi_dung)
        if moi < TI_LE_CT_MIN:
            return False
        if ws.sheet_properties.pageSetUpPr is None:
            ws.sheet_properties.pageSetUpPr = PageSetupProperties()
        ws.sheet_properties.pageSetUpPr.fitToPage = False
        ws.page_setup.fitToWidth = None
        ws.page_setup.fitToHeight = None
        ws.page_setup.scale = min(ti_le, moi)
        ws.row_breaks.brk = []
        ws._print_rows = None                              # setter print_title_rows của openpyxl bỏ qua None
        return True

    @staticmethod
    def can_bang_hai_trang(ws, trang: list, cap: float, dong_muc: list, tieu_de: tuple | None = None) -> list:
        """2 trang, trang 2 bắt đầu giữa một mục: ngắt ngay trước dòng tiêu đề mục (dong_muc) gần nhất trên trang 1 mà trang 2 vẫn
        vừa cap (tính cả dòng tiêu đề lặp) và trang 1 còn >= TRANG_1_TOI_THIEU. Trả danh sách trang (mới hoặc như cũ)."""
        if len(trang) != 2:
            return trang
        from .in_an import _ham_cao
        cao = _ham_cao(ws)
        (d1, c1, _), (d2, c2, _) = trang
        if d2 in dong_muc:
            return trang                                   # đã bắt đầu đúng ở đầu mục
        cao_td = sum(cao(r) for r in range(tieu_de[0], tieu_de[1] + 1)) if tieu_de else 0.0
        for h in sorted((r for r in dong_muc if d1 < r < d2), reverse=True):
            if tieu_de and h <= tieu_de[1] + 1:
                continue                                   # mục đầu bảng: không tách khỏi tiêu đề cột
            t1 = sum(cao(r) for r in range(d1, h))
            t2 = cao_td + sum(cao(r) for r in range(h, c2 + 1))
            if t2 <= cap and t1 >= TRANG_1_TOI_THIEU * cap:
                return [(d1, h - 1, t1), (h, c2, t2)]
        return trang

    @staticmethod
    def tu_dong_chinh_trang(ws, trang: list | None = None, cap: float | None = None, tieu_de: tuple | None = None,
                            dong_muc: list | None = None, cho_phep_fit_1_trang: bool = True,
                            nguong_du_1_trang_pt: float | None = None) -> dict:
        """Quyết định căn trang: gom 1 trang (nếu cho phép và tràn ít) / cân bằng 2 trang / giữ. trang None: tự xếp lại theo các dòng
        đang có (một cụm tự do - dùng khi gọi riêng). Trả dict(trang=[...], mot_trang=bool, can_bang=bool)."""
        from .in_an import cao_trang_in, xep_trang
        BoCanhTrangInAn.dat_kho_a4_doc(ws)
        cap = cao_trang_in(ws) if cap is None else cap
        if trang is None:
            cuoi = ws.max_row
            trang = xep_trang(ws, [('tu_do', [(r, r) for r in range(1, cuoi + 1)])], cap, tieu_de)
        if cho_phep_fit_1_trang and BoCanhTrangInAn.gom_mot_trang(ws, trang, cap, nguong_du_1_trang_pt):
            return dict(trang=[(trang[0][0], trang[-1][1], BoCanhTrangInAn.tong_noi_dung(ws, trang))], mot_trang=True, can_bang=False)
        moi = BoCanhTrangInAn.can_bang_hai_trang(ws, trang, cap, dong_muc or [], tieu_de)
        return dict(trang=moi, mot_trang=False, can_bang=moi is not trang)

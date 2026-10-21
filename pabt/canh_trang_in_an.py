"""Bộ căn trang thông minh bản in phương án chi tiết (người dùng 20/10/2026 - lỗi "trang thứ 2 mồ côi": vài dòng cuối + chữ ký lẻ loi
sang trang 2). Chạy SAU khi in_an.ngat_trang_ct đã xếp trang (xep_trang / co_gian_vua_trang), TRƯỚC khi ghi ngắt trang tay - không
phải bộ dàn trang thứ hai, chỉ thêm ba quyết định:

  1. an_dong_trong_khoi_i: dòng "Số CCCD:" / "Số điện thoại:" của mục I không có số liệu thì ẨN (không để dòng trống đẩy bảng).
  2. gom_mot_trang: tổng nội dung chỉ tràn một trang A4 <= nguong_du_1_trang_pt (mặc định NGUONG_DU_1_TRANG_PT): thu tỷ lệ in
     (1.0.07: không dưới in_an.TI_LE_CT_MIN 70% - không bật "vừa N trang"), bỏ ngắt trang tay và dòng tiêu đề lặp; chỉ thu tỷ lệ
     không đủ thì (21/10/2026) nén các dòng bảng còn chữ + DEM_GOM pt đệm rồi thu tỷ lệ; vẫn không vừa thì giữ 2 trang. Tràn nhiều
     hơn: GIỮ 2 trang (co cả trang cho vừa thì chữ quá nhỏ để ký duyệt).
  3. can_bang_hai_trang: phương án 2 trang mà trang 2 bắt đầu GIỮA một mục: dời chỗ ngắt lên ngay trước dòng tiêu đề mục gần nhất
     (trang 1 kết thúc trọn ở cuối mục trước, trang 2 bắt đầu trọn từ mục đó tới khung chữ ký) - khi trang 2 vẫn vừa và trang 1 còn
     dùng >= TRANG_1_TOI_THIEU chiều cao trang (21/10/2026: 50% -> 85% - trước đây lùi ngắt về tận "mục 2", trang 1 hở gần nửa trang).

Không Qt. Hàm nhận ws (openpyxl) và danh sách trang [(dòng đầu, dòng cuối, chiều cao đã dùng)] như in_an.xep_trang.
"""
from __future__ import annotations

NGUONG_DU_1_TRANG_PT = 160.0     # tràn <= chừng này (pt, đơn vị sheet) thì thử gom vừa 1 trang (21/10/2026: 120 -> 160)
TRANG_1_TOI_THIEU = 0.85         # cân bằng 2 trang: trang 1 phải dùng ít nhất 85% chiều cao trang (21/10/2026: 50% -> 85%)
DEM_GOM = 2.5                    # gom 1 trang: đệm dòng bảng (pt) khi nén - mặc định in_an.DEM_DONG 4 pt
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
        """Chiều cao toàn bộ nội dung (pt) - không tính dòng tiêu đề lặp đầu các trang sau; tới hết vùng in nếu vùng in dài hơn trang
        cuối (vùng in của phương án chi tiết thừa một dòng sau dòng có chữ cuối)."""
        import re
        from .in_an import _ham_cao
        if not trang:
            return 0.0
        cao = _ham_cao(ws)
        cuoi = trang[-1][1]
        m = re.search(r'\$?(\d+)$', str(ws.print_area or '').split(',')[0])
        if m:
            cuoi = max(cuoi, int(m.group(1)))
        return sum(cao(r) for r in range(trang[0][0], cuoi + 1))

    @staticmethod
    def thay_nen_gom(ws, dong_nen, san: dict | None = None, san_khoi=()) -> dict:
        """Chiều cao nén để gom 1 trang: dòng bảng (dong_nen, không ẩn) = chữ của dòng + DEM_GOM pt (san[dòng] là chữ + đệm nén khít
        của in_an: DEM_DONG - NEN_DEM), không dưới in_an.CAO_NEN_TOI_THIEU, không cao hơn hiện tại; vùng gộp ghi chú (a, b, tối thiểu)
        giữ đủ cao. Trả {dòng: chiều cao mới} (chỉ dòng thấp đi)."""
        from .in_an import CAO_NEN_TOI_THIEU, DEM_DONG, NEN_DEM, _ham_cao
        cao = _ham_cao(ws)
        them = DEM_GOM - (DEM_DONG - NEN_DEM)
        thay = {}
        for r in dong_nen or ():
            h = cao(r)
            if h <= 0 or san is None or r not in san:
                continue
            moi = min(h, max(CAO_NEN_TOI_THIEU, san[r] + them))
            if moi < h - 0.01:
                thay[r] = moi
        for a, b, toi_thieu in san_khoi or ():
            tong = sum(thay.get(r, cao(r)) for r in range(a, b + 1))
            can = toi_thieu + them
            if tong < can:
                bu = can - tong
                for r in range(a, b + 1):
                    thay[r] = min(cao(r), thay.get(r, cao(r)) + bu / (b - a + 1))
        return {r: h for r, h in thay.items() if h < cao(r) - 0.01}

    @staticmethod
    def gom_mot_trang(ws, trang: list, cap: float, nguong_pt: float | None = None, dong_nen=None, san: dict | None = None,
                      san_khoi=()) -> bool:
        """Nhiều trang mà nội dung chỉ tràn <= nguong_pt (None: NGUONG_DU_1_TRANG_PT lúc gọi) so với sức chứa một trang (cap): thu tỷ lệ
        in cho vừa 1 trang (>= in_an.TI_LE_CT_MIN), bỏ ngắt tay / tiêu đề lặp. Chỉ thu tỷ lệ chưa đủ: nén dòng bảng (dong_nen - đệm
        DEM_GOM, thay_nen_gom) rồi thu tỷ lệ; đã nén thì báo VBS xuất PDF giữ đệm đó. Trả True khi đã gom."""
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
        from .in_an import TI_LE_CT_MIN, _dat_ten_vbs
        ti_le = int(ws.page_setup.scale or 100)
        moi = int(ti_le * cap / noi_dung)
        thay = {}
        if moi < TI_LE_CT_MIN:
            # 21/10/2026: thu tỷ lệ 72 -> 70% chỉ được ~3% trang - nén thêm đệm dòng bảng (4 -> DEM_GOM pt)
            thay = BoCanhTrangInAn.thay_nen_gom(ws, dong_nen, san, san_khoi)
            if not thay:
                return False
            from .in_an import _ham_cao
            cao = _ham_cao(ws)
            noi_dung -= sum(cao(r) - h for r, h in thay.items())
            moi = int(ti_le * cap / noi_dung)
            if moi < TI_LE_CT_MIN:
                return False
            for r, h in thay.items():
                ws.row_dimensions[r].height = round(h, 2)
            _dat_ten_vbs(ws, True, DEM_GOM)
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
                            nguong_du_1_trang_pt: float | None = None, dong_nen=None, san: dict | None = None,
                            san_khoi=()) -> dict:
        """Quyết định căn trang: gom 1 trang (nếu cho phép và tràn ít - dong_nen / san / san_khoi: dòng bảng được nén đệm) / cân bằng
        2 trang / giữ. trang None: tự xếp lại theo các dòng đang có (một cụm tự do - dùng khi gọi riêng). Trả dict(trang=[...],
        mot_trang=bool, can_bang=bool)."""
        from .in_an import cao_trang_in, xep_trang
        BoCanhTrangInAn.dat_kho_a4_doc(ws)
        cap = cao_trang_in(ws) if cap is None else cap
        if trang is None:
            cuoi = ws.max_row
            trang = xep_trang(ws, [('tu_do', [(r, r) for r in range(1, cuoi + 1)])], cap, tieu_de)
        if cho_phep_fit_1_trang and BoCanhTrangInAn.gom_mot_trang(ws, trang, cap, nguong_du_1_trang_pt, dong_nen, san, san_khoi):
            return dict(trang=[(trang[0][0], trang[-1][1], BoCanhTrangInAn.tong_noi_dung(ws, trang))], mot_trang=True, can_bang=False)
        moi = BoCanhTrangInAn.can_bang_hai_trang(ws, trang, cap, dong_muc or [], tieu_de)
        return dict(trang=moi, mot_trang=False, can_bang=moi is not trang)

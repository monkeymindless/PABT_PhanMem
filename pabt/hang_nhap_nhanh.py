"""Hàng nhập nhanh tài sản - MỘT thành phần dùng chung cho thẻ mục của cửa sổ lập phương án hộ (man_hinh.BangMuc) và trang
Dự toán & khái toán (man_hinh_du_toan.KhungDuToan) - 0.9.67, người dùng 12/10/2026.

Một hàng: [Mục ▼ (chỉ dự toán)] Tên (gõ không dấu, ▼ danh sách) → [kiểu số đo - cây] → [Số đo: đường kính / chu vi (cm)]
→ Khối lượng (=4,2*5,7; cây theo số đo: số cây mỗi số đo) → Tỷ lệ % → Ghi chú → Thêm vào bảng (Tab đi tiếp, Enter thêm - cả
khi đang ở nút Thêm vào bảng). Màn hình chủ đọc `gia_tri()` rồi ghi bằng nhap_tai_san.them_mot (cùng một bộ lệnh).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPushButton, QWidget

from .lap_pa import DanhMuc, bo_dau
from .nghiep_vu import MUC_KHOAN, MUC_VN, tap_ma_tdc
from .tien import vn

# chữ ngắn (ô số đo ghi đơn vị cm): ô kiểu hẹp, thanh nhập nhanh khái toán vừa một hàng ở màn hình 1366
KIEU_SL = [('sl', 'Số lượng'), ('dk', 'Đường kính'), ('cv', 'Chu vi')]
GOI_Y = {2: 'Tên nhà, công trình (gõ không dấu, ▼ xem danh sách)',
         3: 'Tên cây trồng (gõ không dấu, vd: xoai 11-15, sao den)',
         MUC_VN: 'Tên vật nuôi (gõ không dấu, vd: ca, tom, ga)',
         4: 'Chính sách hỗ trợ (gõ không dấu, vd: on dinh, dao tao, thue nha)',
         5: 'Khoản thưởng (gõ tên, ví dụ: Thưởng bàn giao mặt bằng trước thời hạn)'}
# ô số đo (chỉ hiện khi kiểu đường kính / chu vi) và ô Khối lượng (luôn hiện - 0.9.71, người dùng 12/10/2026)
GOI_Y_DO = {'dk': '15, 18x2, 22 (cm)', 'cv': '45, 52x3, 60 (cm)'}
# chữ gợi ý ngắn (ô Khối lượng hẹp 90 px ở thanh khái toán); công thức / "trống = 1" ở chú thích của ô
GOI_Y_SL = {'sl': 'Khối lượng', 'dk': 'Số cây', 'cv': 'Số cây'}


def ds_chon_nhanh(dm: DanhMuc, muc: int) -> list:
    """Danh sách chọn nhanh của mục 2-4 [(nhãn, mục danh mục)]. Chỉ phụ thuộc danh mục (đối tượng DanhMuc dùng chung giữa
    các lần mở cửa sổ): dựng một lần rồi dùng lại; cửa sổ chính dựng sẵn lúc rảnh sau khi mở dự án (lam_san).
    Mục không có danh mục (5 - thưởng): [] (gõ tên tự do)."""
    from . import lap_pa
    from .cay_trong import BangCayDK, mo_ta_chu_vi
    if muc not in dm.muc:
        return []
    nho = dm.__dict__.setdefault('_ds_chon', {})
    if muc in nho:
        return nho[muc]
    ds = []
    for m in dm.muc[muc]:
        if muc == 4 and m.ma in (tap_ma_tdc() + ('CS21', 'CS22', 'CS25', 'CS26')):
            continue                    # tái định cư: chọn ở ô Tái định cư; cộng thêm nhân khẩu: đã gộp vào đơn giá tháng
        gia = f'{vn(m.don_gia)} đ/{m.dvt}' if m.don_gia is not None and not (muc == 4 and m.ma in lap_pa.MA_HE_SO) \
            else (m.dvt or '')
        cv = mo_ta_chu_vi(m.ten) if muc == 3 else ''
        ds.append((f'{m.ma} – {m.ten}' + (f' [{cv}]' if cv else '') + (f'  ·  {gia}' if gia else ''), m))
    if muc == 3:
        # loại cây có quy cách theo đường kính thân: chọn tên loại, số lượng nhập theo đường kính / chu vi (ô bên cạnh)
        ds = [(ten, ('nhom', ten)) for ten in BangCayDK(dm.muc[3]).ten_loai()] + ds
    if muc == 4:
        from .chinh_sach import CHINH_SACH_KHAC
        ds += [(f'{t} (nhập số tiền)', ('ten', t)) for t in CHINH_SACH_KHAC]
    if muc in (2, 3, MUC_VN):
        # quy ước tương đương / đơn giá thẩm định của dự án (tài sản đặc biệt): đứng đầu danh sách để chọn nhanh
        from .don_gia_rieng import ID_RIENG
        qu = []
        for m in dm.muc[9]:
            if m.don_gia is None:
                continue
            try:
                if int(str(m.ma)[2:]) < ID_RIENG:       # quy ước gắn sẵn của bộ đơn giá cũ (0.9.69 bỏ): không hiện để chọn
                    continue
            except ValueError:
                pass
            nhan = 'Thẩm định' if bo_dau(m.phan_loai).startswith('don gia tham dinh') else 'Quy ước'
            qu.append((f'[{nhan}] {m.ten}  ·  {vn(m.don_gia)} đ/{m.dvt}'
                       + (f'  (theo {m.phan_loai})' if nhan == 'Quy ước' and m.phan_loai else ''), m))
        ds = qu + ds
    nho[muc] = ds
    return ds


def lam_san(dm: DanhMuc) -> None:
    for m in MUC_KHOAN:
        ds_chon_nhanh(dm, m)


CAO_HANG = 29                 # ô nhập / nút của hàng nhập nhanh (20/10/2026: 29 px; 1.0.02: 30; trước: ô kiểu nhap="1" ~34 px)
# kiểu ô của hàng: giao_dien.QSS_HANG_NHAP trong bảng kiểu chung (chọn theo property hang_nhap="1") - KHÔNG setStyleSheet trên hàng:
# kiểu cục bộ bắt Qt tính lại kiểu cả cây con, 4 hàng làm mở cửa sổ lập phương án chậm thêm ~60 ms (đo 1.0.02)


class HangNhapNhanh(QWidget):
    """muc: mục cố định (thẻ mục của phương án hộ); chon_muc [(mục, nhãn)]: có ô chọn mục (dự toán - một bảng mọi mục).
    them(): hàm thêm của màn hình chủ (Enter / nút Thêm vào bảng). sau_chon(m) -> True nếu đã tự đặt con trỏ (mục 4 hộ)."""

    def __init__(self, them, muc: int | None = None, chon_muc: list | None = None, parent=None):
        super().__init__(parent)
        from .giao_dien import OTimChon, RONG_NUT_XO
        self._them = them
        self._muc = muc
        self._dm = None
        self.sau_chon = None
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(8)
        self.cb_muc = None
        if chon_muc:
            self.cb_muc = QComboBox()
            for k, t in chon_muc:
                self.cb_muc.addItem(t, k)
            self.cb_muc.setToolTip('Mục của hạng mục: nhà, công trình / cây trồng / vật nuôi / hỗ trợ / thưởng')
            self.cb_muc.setProperty('nhap', '1')
            self.cb_muc.currentIndexChanged.connect(lambda *_: self._doi_muc())
            lo.addWidget(self.cb_muc)
        self.o_chon = OTimChon(GOI_Y.get(self.muc(), GOI_Y[2]))
        self.o_chon.khi_chon = lambda m: self._da_chon(m)
        self.o_chon.o.setProperty('nhap', '1')
        self.o_chon.nut.setFixedSize(RONG_NUT_XO, CAO_HANG)     # nút ▼ liền ô chữ (1.0.03)
        self.o_chon.nut.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        lo.addWidget(self.o_chon, 5)
        # kiểu số đo của cây (đường kính / chu vi thân): chỉ tạo khi hàng có mục 3 (thẻ Nhà / Vật nuôi / Hỗ trợ của hộ không cần -
        # mở cửa sổ lập phương án nhanh hơn ~4-9 ms, đo 0.9.67)
        self.cb_kieu = None
        if self.muc() == 3 or any(k == 3 for k, _ in (chon_muc or ())):
            self.cb_kieu = QComboBox()
            for k, t in KIEU_SL:
                self.cb_kieu.addItem(t, k)
            self.cb_kieu.setToolTip('Nhập số cây, hoặc các số đo đường kính / chu vi thân (cm) cách nhau dấu phẩy, nhiều cây cùng số '
                                    'đo ghi 52x3: phần mềm tự xếp vào đúng quy cách đơn giá')
            self.cb_kieu.currentIndexChanged.connect(lambda *_: self._doi_kieu())
            self.cb_kieu.setProperty('nhap', '1')
            lo.addWidget(self.cb_kieu)
        # số đo thân cây (cm): chỉ hiện ở kiểu Đường kính / Chu vi; chỉ tạo khi hàng có mục 3 (như cb_kieu)
        self.o_do = None
        if self.cb_kieu is not None:
            self.o_do = QLineEdit()
            self.o_do.setPlaceholderText(GOI_Y_DO['dk'])
            self.o_do.setToolTip('Các số đo (cm) cách nhau dấu phẩy; nhiều cây cùng số đo ghi 52x3')
            self.o_do.setMinimumWidth(150)
            self.o_do.setMaximumWidth(260)
            self.o_do.setVisible(False)
        self.o_sl = QLineEdit()
        self.o_sl.setPlaceholderText(GOI_Y_SL['sl'])
        self.o_sl.setToolTip('Khối lượng / số lượng theo đơn vị tính (có thể gõ công thức =4,2*5,7). Cây nhập theo số đo: số '
                             'cây cho MỖI số đo (trống = 1)')
        self.o_sl.setMinimumWidth(120)
        self.o_sl.setMaximumWidth(200)
        self.o_tl = QLineEdit()
        self.o_tl.setPlaceholderText('Tỷ lệ %')
        self.o_tl.setMaximumWidth(80)
        self.o_tl.setToolTip('Tỷ lệ bồi thường, hỗ trợ (%) - để trống = 100%')
        self.o_gc = QLineEdit()
        self.o_gc.setPlaceholderText('Ghi chú: quy định, cách tính…')
        self.o_gc.setToolTip('Quy định pháp luật áp dụng, cách tính… (in ở cột Ghi chú / Căn cứ)')
        for o, k in ((self.o_do, 2), (self.o_sl, 2), (self.o_tl, 1), (self.o_gc, 3)):
            if o is None:
                continue
            o.setProperty('nhap', '1')
            o.returnPressed.connect(lambda: self._them())
            lo.addWidget(o, k)
        self.nut_them = QPushButton('Thêm vào bảng')
        self.nut_them.setMinimumHeight(CAO_HANG)
        self.nut_them.setAutoDefault(True)             # Enter khi đang ở nút cũng thêm (ngoài hộp thoại Qt chỉ nhận Space)
        self.nut_them.clicked.connect(lambda: self._them())
        lo.addWidget(self.nut_them)
        chuoi = [w for w in (self.cb_muc, self.o_chon.o, self.cb_kieu, self.o_do, self.o_sl, self.o_tl, self.o_gc,
                             self.nut_them)
                 if w is not None]
        for a, b in zip(chuoi, chuoi[1:]):            # Tab: (mục) → tên → (kiểu số đo) → số lượng → tỷ lệ → ghi chú → Thêm
            QWidget.setTabOrder(a, b)
        if self.cb_kieu is not None:
            self.cb_kieu.setVisible(self.muc() == 3)
        # 1.0.02 (Hybrid Enterprise Navy): mọi ô + nút cao CAO_HANG, viền slate, đang gõ viền navy (QSS chung, bộ chọn
        # QWidget[hang_nhap="1"] QLineEdit cụ thể hơn QLineEdit[nhap="1"] cao 34 px)
        self.setProperty('hang_nhap', '1')
        for w in chuoi:
            if w is not self.nut_them:
                w.setFixedHeight(CAO_HANG)
        self.nut_them.setFixedHeight(CAO_HANG)
        from .giao_dien import KieuNut, ap_kieu_nut
        ap_kieu_nut(self.nut_them, KieuNut.CHINH)       # thao tác chính của hàng: nền navy chữ trắng

    # ---------------------------------------------- mục, danh sách chọn
    def muc(self) -> int:
        return self.cb_muc.currentData() if self.cb_muc is not None else self._muc

    def nap(self, dm: DanhMuc) -> None:
        """Danh sách chọn của mục đang chọn theo danh mục dm."""
        self._dm = dm
        self.o_chon.dat_muc(ds_chon_nhanh(dm, self.muc()))

    def _doi_muc(self):
        m = self.muc()
        self.o_chon.o.setPlaceholderText(GOI_Y.get(m, GOI_Y[2]))
        if self.cb_kieu is not None:
            self.cb_kieu.setVisible(m == 3)
            if m != 3:
                self.cb_kieu.setCurrentIndex(0)
            self._doi_kieu()
        self.o_chon.xoa()
        if self._dm is not None:
            self.nap(self._dm)

    def _da_chon(self, m):
        if self.muc() == 3:
            nhom = isinstance(m, tuple) and m[0] == 'nhom'
            if nhom and self.cb_kieu.currentData() == 'sl':
                self.cb_kieu.setCurrentIndex(1)
            elif not nhom and m is not None and self.cb_kieu.currentData() != 'sl':
                from .cay_trong import khoang_duong_kinh
                if khoang_duong_kinh(m.ten) is None:
                    self.cb_kieu.setCurrentIndex(0)
        if self.sau_chon is not None and self.sau_chon(m):
            return
        o = self.o_do if self.o_do is not None and self.o_do.isVisibleTo(self) else self.o_sl
        o.setFocus()
        o.selectAll()

    def kieu(self) -> str:
        return self.cb_kieu.currentData() if self.cb_kieu is not None and self.muc() == 3 else 'sl'

    def _doi_kieu(self):
        k = self.kieu()
        if self.o_do is not None:
            self.o_do.setVisible(k in GOI_Y_DO)
            if k in GOI_Y_DO:
                self.o_do.setPlaceholderText(GOI_Y_DO[k])
        self.o_sl.setPlaceholderText(GOI_Y_SL[k])

    # ---------------------------------------------- giá trị / xóa
    def gia_tri(self) -> dict:
        k = self.kieu()
        return dict(muc=self.muc(), m=self.o_chon.chon, ten=self.o_chon.text().strip(), so_luong=self.o_sl.text().strip(),
                    ty_le=self.o_tl.text().strip(), kieu=k, ghi_chu=self.o_gc.text().strip(),
                    so_do=self.o_do.text().strip() if k in GOI_Y_DO and self.o_do is not None else '')

    def xoa(self) -> None:
        self.o_chon.xoa()
        if self.o_do is not None:
            self.o_do.clear()
        self.o_sl.clear()
        self.o_tl.clear()
        self.o_gc.clear()
        self.o_chon.o.setFocus()

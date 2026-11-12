"""Dựng giao diện cửa sổ lập phương án (1.1.05: tách từ CuaSoLapPA - lớp man_hinh.py 2.200 dòng): thanh trên, ô thông tin hộ,
thẻ mục, dải tổng / cảnh báo, thanh chia, phím tắt, dải định danh, dải lần phương án, hàng điều hướng. Mixin, không dùng riêng:
CuaSoLapPA kế thừa DungGiaoDienLapPA; mọi self.X khác là của CuaSoLapPA. Thân hàm chép nguyên văn; tên dùng chung của man_hinh
(TEN_TAB, THE_MUC, NhanTongPA...) nhập lúc gọi. man_hinh nhập lại các hằng chuyển sang đây (man_hinh.CAO_NUT_TREN...)."""
from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSplitter, QTabWidget, QVBoxLayout, QWidget
from .giao_dien import dat_kieu_theo_tong


# ---------------------------------------------------------------- màn hình lập phương án hộ
# ô chọn hộ của cửa sổ lập phương án (px): rộng tới 560 cho đủ tên hộ / tổ chức; hẹp được tới 160 để hàng nút trên cùng luôn MỘT hàng
# (16/10/2026, người dùng: bỏ nút SCAN, mọi nút lên một dòng) - màn hình 1366 ở 125% còn ~1.090 điểm
RONG_O_HO = (240, 400)              # 1.0.90: trần 560 -> 400 (tên hộ thường < 40 ký tự; ô dài để trống, người dùng 09/11/2026)
# 1.0.02 (Hybrid Enterprise Navy cửa sổ con, theo ảnh mẫu người dùng 17/10/2026): nút Dán tài sản nền trắng viền slate chữ đậm,
# biểu tượng xanh trời; rê chuột nền xanh băng viền xanh trời
QSS_NUT_DAN_TS = ('QPushButton#btn_dan_ts { background: #FFFFFF; color: #0F172A; font-weight: 700; border: 1px solid #CBD5E1; '
                  'border-radius: 6px; padding: 0 14px; }'
                  'QPushButton#btn_dan_ts:hover { background: #F0F9FF; border-color: #1F76A6; color: #1A5C85; }'
                  'QPushButton#btn_dan_ts:pressed { background: #E0F2FE; }')
MAU_ICON_DAN_TS = '#1F76A6'
# 1.0.02 (ảnh mẫu): tắt = nền trắng viền slate chữ navy; bật (đang xem) = nền xanh băng, viền navy, chữ navy đậm
QSS_NUT_XEM_TRUOC = ('QPushButton#btn_toggle_preview { color: #1E3A5F; background: #FFFFFF; border: 1px solid #CBD5E1; '
                     'border-radius: 6px; padding: 0 12px; font-weight: 600; }'
                     'QPushButton#btn_toggle_preview:hover { background: #F1F5F9; border-color: #2563EB; }'
                     'QPushButton#btn_toggle_preview:checked { color: #1E3A5F; background: #EFF6FF; border: 1px solid #1E3A5F; '
                     'font-weight: 700; }'
                     'QPushButton#btn_toggle_preview:checked:hover { background: #DBEAFE; }')
# thanh trên cùng (chọn hộ + lệnh): nền slate nhạt, vạch dưới; ô chọn hộ nền trắng chữ đậm; nút ◀ ▶ nền trắng viền slate
QSS_THANH_TREN = ('QWidget#thanh_tren_lap_pa { background: #F8FAFC; border: 0; border-bottom: 1px solid #E2E8F0; }'
                  'QComboBox#o_chon_ho { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 5px; padding: 0 8px; min-height: 26px; '
                  'font-weight: 700; color: #0F172A; }'
                  'QComboBox#o_chon_ho:hover { border-color: #94A3B8; }'
                  'QComboBox#o_chon_ho:focus { border: 2px solid #2563EB; padding: 0 7px; }'
                  'QPushButton#nut_ho_truoc, QPushButton#nut_ho_sau { background: #FFFFFF; border: 1px solid #CBD5E1; '
                  'border-radius: 5px; padding: 0; color: #1E3A5F; font-weight: 700; }'
                  'QPushButton#nut_ho_truoc:hover, QPushButton#nut_ho_sau:hover { background: #F1F5F9; border-color: #94A3B8; }'
                  'QPushButton#nut_ho_truoc:disabled, QPushButton#nut_ho_sau:disabled { color: #CBD5E1; border-color: #E2E8F0; }')
# dải tổng cộng + ◀ Trở lại / Tiếp theo ▶ dưới đáy: nền slate, vạch trên 2 px, tổng chữ navy đậm
QSS_DAI_DIEU_HUONG = ('QFrame#dai_dieu_huong { background: #F1F5F9; border: 0; border-top: 2px solid #CBD5E1; }'
                      'QLabel#tong_pa { font-size: 13px; font-weight: 700; color: #1E3A5F; background: transparent; border: 0; '
                      'padding: 2px 4px; }')
CAO_NUT_TREN = 28                  # hàng trên cùng cửa sổ lập phương án (chọn hộ + nút lệnh) một hàng (0.9.95: 27; 1.0.02: 28)


class DungGiaoDienLapPA:
    """Các phương thức dựng giao diện của CuaSoLapPA."""
    def _tao_nut_tren(self) -> None:
        """Ô chọn hộ và các nút của thanh trên."""
        # ---- dòng chọn hộ
        self.cb_ho = QComboBox()
        # 16/10/2026 (người dùng): hiện rõ đủ tên hộ - ô rộng hơn (bỏ nút Gợi ý, chữ nút ngắn lại nhường chỗ), chữ hiện từ ĐẦU tên
        # (ô sửa được trước đây cuộn về cuối: "ất do UBND xã…"), tên đầy đủ ở chú thích
        self.cb_ho.setMinimumWidth(RONG_O_HO[0])
        self.cb_ho.setMaximumWidth(RONG_O_HO[1])
        # không AdjustToContents (tối thiểu = tên dài nhất, hàng nút không còn MỘT hàng trên màn hình 1366): co tới RONG_O_HO[0],
        # giãn nhận chỗ thừa tới RONG_O_HO[1]; tên đầy đủ ở chú thích
        self.cb_ho.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cb_ho.setMinimumContentsLength(12)
        self.cb_ho.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cb_ho.setEditable(True)
        self.cb_ho.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cb_ho.setObjectName('o_chon_ho')
        self.cb_ho.setFixedHeight(CAO_NUT_TREN)
        self.cb_ho.currentIndexChanged.connect(lambda *_: self._hien_ten_ho())
        self._nap_ds_ho()
        self.cb_ho.activated.connect(self._chon_ho_tu_hop)
        self.b_truoc = QPushButton('◀')
        self.b_sau = QPushButton('▶')
        self.b_truoc.clicked.connect(lambda: self.sang_ho(-1))
        self.b_sau.clicked.connect(lambda: self.sang_ho(1))
        self.b_truoc.setToolTip('Hộ trước (Ctrl+Left, Ctrl+PgUp)')
        self.b_sau.setToolTip('Hộ sau (Ctrl+Right, Ctrl+PgDn)')
        self.b_ds_ho = QPushButton('DS hộ')             # 1.0.58: ghim danh sách hộ bên trái
        self.b_ds_ho.setCheckable(True)
        self.b_ds_ho.setProperty('khong_icon', True)
        self.b_ds_ho.setFixedWidth(48)                  # hàng nút đã kín ở 1366 @125% (~1.090 điểm): không dùng bề rộng nút thường 80 px
        self.b_ds_ho.setStyleSheet('QPushButton { padding: 0 2px; }')
        self.b_ds_ho.setToolTip('Ghim danh sách hộ bên trái (Ctrl+B): bấm tên hộ để chuyển, lọc không dấu, đối chiếu hai hộ')
        self.b_ds_ho.clicked.connect(lambda v: self.bat_tat_ds_ho(v))
        for b, ten in ((self.b_truoc, 'nut_ho_truoc'), (self.b_sau, 'nut_ho_sau')):
            b.setFixedWidth(32)
            b.setObjectName(ten)
            b.setProperty('khong_icon', True)
        # 16/10/2026: bỏ nút "Gợi ý hỗ trợ…" (người dùng - thu gọn hàng nút); chữ nút ngắn
        self.b_dan = self.btn_dan_ts = QPushButton('Dán tài sản')   # phím tắt Ctrl+Shift+V ở chú thích
        self.b_dan.setObjectName('btn_dan_ts')
        self.b_dan.setToolTip('Ctrl+Shift+V. Dán / gõ nhiều dòng tài sản (Tên, ĐVT, Số lượng…): phần mềm tự xếp vào Nhà, công trình / Cây trồng / '
                              'Vật nuôi / Hỗ trợ theo bộ đơn giá. Đang có bảng tài sản trong bộ nhớ đệm (Excel, Word…) thì tự điền '
                              'và phân loại ngay khi mở.')
        self.b_dan.setFixedHeight(CAO_NUT_TREN)
        self.b_dan.setCursor(Qt.CursorShape.PointingHandCursor)
        dat_kieu_theo_tong(self.b_dan, QSS_NUT_DAN_TS)        # có bộ chọn #btn_dan_ts: không truyền sang tooltip của nút
        self.b_dan.setProperty('khong_icon', True)      # to_mau không gắn biểu tượng màu nhóm đè lên nền xanh
        from .giao_dien import icon_ky_hieu
        ic = icon_ky_hieu(0xE77F, MAU_ICON_DAN_TS, 16)  # Paste (Segoe MDL2); máy không có phông (Win 7): chỉ chữ
        if ic is not None:
            self.b_dan.setIcon(ic)
        self.b_dan.clicked.connect(lambda: self.mo_dan_tai_san())
        self.b_luu = QPushButton('Lưu')                  # 1.0.16: chữ ngắn (màn hình 1366 @125%: nút bị cắt chữ); phím Ctrl+S ở chú thích
        self.b_luu.setToolTip('Lưu phương án của hộ (Ctrl+S)')
        self.b_luu.clicked.connect(lambda: self.luu())
        from .giao_dien import KieuNut, ap_kieu_nut
        ap_kieu_nut(self.b_luu, KieuNut.LUU)            # hành động lưu - nền xanh lục (1.0.52)
        self.b_bo = QPushButton('Bỏ thay đổi')
        self.b_bo.clicked.connect(lambda: self.bo_thay_doi())
        self.b_in = QPushButton('In / Xuất…')
        self.b_in.clicked.connect(lambda: self.in_xuat())
        # 0.9.84 (người dùng 14/10/2026): bật / tắt khung xem trước A4 bên phải (phím F4) - bản in của phương án ĐANG SOẠN
        self.btn_toggle_preview = QPushButton('Xem trước')   # phím F4 ở chú thích
        self.btn_toggle_preview.setObjectName('btn_toggle_preview')
        self.btn_toggle_preview.setCheckable(True)
        self.btn_toggle_preview.setFixedHeight(CAO_NUT_TREN)
        self.btn_toggle_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_preview.setToolTip('Xem trước (F4): hiện / ẩn bản in A4 của hộ đang mở ở nửa phải cửa sổ. Bản xem trước lấy cả số liệu '
                                           'chưa lưu; cần Microsoft Excel.')
        dat_kieu_theo_tong(self.btn_toggle_preview, QSS_NUT_XEM_TRUOC)
        self.btn_toggle_preview.setProperty('khong_icon', True)
        # View (Segoe MDL2): tắt biểu tượng navy, bật (đang xem, nền navy) biểu tượng trắng; Win 7 không có phông: chỉ chữ
        ic = icon_ky_hieu(0xE890, '#1E3A5F', 16)
        if ic is not None:
            self.btn_toggle_preview.setIcon(ic)
        self.btn_toggle_preview.clicked.connect(lambda: self.bat_tat_xem_truoc())
        self.b_dong = QPushButton('Đóng')
        self.b_dong.clicked.connect(lambda: self.close())

    def _dung_thanh_tren(self) -> None:
        """Xếp thanh trên."""
        # 16/10/2026 (người dùng): bỏ nút SCAN, mọi nút MỘT hàng trên cùng: Hộ [ô chọn hộ] ◀ ▶ | Dán tài sản ... Lưu, Bỏ thay đổi |
        # Xem trước, In / Xuất, Đóng. Ô chọn hộ giãn / co (200 - 560 px) nhận phần chỗ thừa / thiếu thay cho xuống dòng
        self.thanh_tren = QWidget()
        self.thanh_tren.setObjectName('thanh_tren_lap_pa')
        self.thanh_tren.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        dat_kieu_theo_tong(self.thanh_tren, QSS_THANH_TREN)       # khung ít widget con: kiểu cục bộ không làm chậm (đã đo)
        h1 = QHBoxLayout(self.thanh_tren)
        h1.setContentsMargins(8, 4, 8, 4)
        h1.setSpacing(4)
        for b in (self.b_truoc, self.b_sau, self.b_ds_ho, self.b_luu, self.b_bo, self.b_in, self.b_dong):
            b.setFixedHeight(CAO_NUT_TREN)
        nhan = QLabel('Hộ:')
        nhan.setProperty('vai', 'nhan')
        # 1.0.69: MỘT thanh: Hộ | phiên bản, lần | Lưu, In / Xuất, Đóng. Dán tài sản xuống hàng công cụ của bảng; Xem trước vào menu In / Xuất; Bỏ thay đổi hỏi khi Đóng.
        for w in (nhan, self.cb_ho, self.b_truoc, self.b_sau, self.b_ds_ho):
            h1.addWidget(w, 1 if w is self.cb_ho else 0)
        self._h_tren = h1
        h1.addSpacing(8)
        h1.addStretch(0)
        for w in (self.b_dan, self.b_bo, self.btn_toggle_preview):      # giữ làm nguồn trạng thái / phím tắt, ẩn
            h1.addWidget(w)
        for w in (self.b_luu, self.b_in, self.b_dong):
            h1.addWidget(w)
        for w in (self.b_dan, self.b_bo, self.btn_toggle_preview):
            w.hide()
        self.b_in.setText('In / Xuất ▾')
        self.b_luu.setText('Lưu (Ctrl+S)')
        self.menu_in = QMenu(self.b_in)
        self.menu_in.aboutToShow.connect(self._ve_menu_in)
        self.b_in.setMenu(self.menu_in)

    def _tao_o_thong_tin_ho(self) -> None:
        """Thông tin hộ dùng cho chính sách hỗ trợ."""
        # ---- thông tin hộ dùng cho chính sách hỗ trợ
        from .giao_dien import OSoChuaNhap
        self.o_nk = OSoChuaNhap('chưa nhập')
        self.o_nk.setRange(0, 200)
        self.o_nk.setMinimumWidth(110)
        self.o_nk.setToolTip('Số nhân khẩu: ổn định đời sống, thuê nhà / tự lo chỗ ở tự tính theo số này')
        self.o_nk.valueChanged.connect(self._doi_nk)
        self.o_di_chuyen = QCheckBox('Phải di chuyển chỗ ở')
        self.o_di_chuyen.toggled.connect(self._doi_di_chuyen)
        self.o_dt_nn = QLineEdit()
        self.o_dt_nn.setMaximumWidth(150)
        self.o_dt_nn.setToolTip('Để trống: tự lấy tổng diện tích đất nông nghiệp đã nhập ở mục 1 (Đất). Gõ số khác nếu hộ còn đất '
                                'nông nghiệp ngoài phần thu hồi.')
        self.o_dt_nn.editingFinished.connect(self._doi_dt_nn)
        self.lb_tl = QLabel('')                     # các ô này đặt ở thẻ 5. Hỗ trợ (BangMuc mục 4)

    def _tao_the_muc(self, con, ma_ho):
        """Thẻ hồ sơ hộ + 5 mục. Trả cài đặt đã nhớ."""
        from .man_hinh import KHOA_BANG_GON, TEN_TAB, THE_MUC, _BangMucTre      # 1.1.05: tên của man_hinh (nạp lúc gọi)
        # ---- thẻ 0 hồ sơ hộ + 5 mục
        from .man_hinh_ho_so import KhungHoSo
        self.tab = QTabWidget()
        self.tab.setDocumentMode(True)
        self.tab.tabBar().setProperty('vai', 'gach_chan')   # kiểu thẻ gạch chân: QSS chung (QSS_THE_LAP_PA)
        the0 = QWidget()
        lo0 = QVBoxLayout(the0)
        lo0.setContentsMargins(6, 4, 6, 4)
        self.ho_so = KhungHoSo(con, ma_ho, the0, an=('trang_thai', 'tai_dinh_cu'), khi_thay_doi_csdl=self._sau_ghi_ho_so,
                               khi_xoa_ho=self._sau_xoa_ho)
        lo0.addWidget(self.ho_so, 1)
        # 22/10/2026 (nâng cấp giao diện): cửa sổ thấp (1366 / 1536 x 125%) thì thẻ hồ sơ CUỘN DỌC - trước đây bị ép: ô nhập chồng nhau,
        # bảng thửa chỉ còn một vạch. Đủ chỗ thì vẫn giãn hết khung (widgetResizable)
        cuon0 = QScrollArea()
        cuon0.setObjectName('cuon_ho_so')
        cuon0.setWidgetResizable(True)
        cuon0.setFrameShape(QFrame.Shape.NoFrame)
        cuon0.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cuon0.setWidget(the0)
        self.tab.addTab(cuon0, TEN_TAB[0])
        from .giao_dien import cai_dat_nho
        cd = cai_dat_nho()                              # 1.0.58: nhớ Gọn cột / ghim danh sách hộ (offscreen - kiểm thử: không đọc)
        self._bang_gon = cd is not None and str(cd.value(KHOA_BANG_GON, 'false')).lower() in ('true', '1')
        self._w_ds_ho = None
        self.bang = _BangMucTre(self)
        self._dang_dung_bang = set()
        for the, m in enumerate(THE_MUC[1:], start=1):
            cho = QWidget()
            cho.setProperty('the_cho', m)
            self.tab.addTab(cho, TEN_TAB[the])
        return cd

    def _tao_tong_canh_bao(self) -> None:
        """Tổng + cảnh báo, dải bộ đếm."""
        from .man_hinh import NhanTongPA      # 1.1.05: tên của man_hinh (nạp lúc gọi)
        # ---- tổng + cảnh báo
        self.lb_tong = NhanTongPA()
        self.lb_tong.setObjectName('tong_pa')                # kiểu: QSS_DAI_DIEU_HUONG (dải đáy cửa sổ)
        self.lb_tb = QLabel('')
        self.lb_tb.setWordWrap(True)
        # 1.0.69: dải dưới chân bảng: bộ đếm vùng chọn (không nổi trong lòng bảng, không che dòng); luôn giữ chỗ để kéo chọn không làm bảng co giãn
        from .giao_dien import NhanBoDem
        self.dai_bo_dem = QFrame()
        self.dai_bo_dem.setObjectName('dai_bo_dem')
        self.dai_bo_dem.setFixedHeight(24)
        hb = QHBoxLayout(self.dai_bo_dem)
        hb.setContentsMargins(8, 0, 8, 0)
        self.lb_goi_y_bo_dem = QLabel('Chọn nhiều ô để xem tổng diện tích, đơn giá, thành tiền · Ctrl+C: sao chép ô')
        self.lb_goi_y_bo_dem.setProperty('vai', 'nhan')
        self.lb_bo_dem = NhanBoDem()
        hb.addWidget(self.lb_goi_y_bo_dem, 1)
        hb.addWidget(self.lb_bo_dem)
        from .giao_dien import TOKEN
        dat_kieu_theo_tong(self.lb_tb, 'QLabel { color: %s; padding: 2px 6px; }' % TOKEN['chinh'])
        self.o_cb = QPlainTextEdit()
        self.o_cb.setReadOnly(True)
        from .giao_dien import kieu_trang_thai
        self.o_cb.setStyleSheet(kieu_trang_thai('canh_bao', 'QPlainTextEdit', dam=False))   # màu "cần xem lại" dùng chung
        self.o_cb.setVisible(False)

    def _dung_tach(self) -> None:
        """Vùng soạn | xem trước."""
        # QSplitter ngang: trái = các thẻ soạn + tổng / cảnh báo; phải = KhungXemTruocTaiLieu, MẶC ĐỊNH ẨN (F4 / nút bật). Khung xem
        # trước TẠO KHI BẬT LẦN ĐẦU (máy yếu - 16/10/2026: mở cửa sổ lập phương án không dựng khung PDF ~70 ms) - xem w_preview
        trai = QWidget()
        lo_trai = QVBoxLayout(trai)
        lo_trai.setContentsMargins(0, 0, 0, 0)
        lo_trai.setSpacing(4)
        lo_trai.addWidget(self.tab, 1)
        lo_trai.addWidget(self.dai_bo_dem)
        self.dai_bo_dem.hide()                          # 06/11/2026 (V3.3): gộp vào dải đáy (_dat_chan); nhãn giữ làm nguồn số liệu vùng chọn
        lo_trai.addWidget(self.lb_tb)
        self.lb_tb.setVisible(False)
        self.hang_dieu_huong()                          # dải tổng cộng + ◀ Trở lại / Tiếp theo ▶ một hàng (0.9.95) -> dai_dieu_huong
        lo_trai.addWidget(self.dai_dieu_huong)
        lo_trai.addWidget(self.o_cb)
        self._w_preview = None
        self.tach = QSplitter(Qt.Orientation.Horizontal)
        self.tach.addWidget(trai)
        self.tach.setChildrenCollapsible(False)
        self.tach.setStretchFactor(0, 3)
        self._hen_xem = QTimer(self)                # sửa số liệu khi khung đang hiện: lập lại sau khi ngừng sửa (Excel mất vài giây)
        self._hen_xem.setSingleShot(True)
        self._hen_xem.timeout.connect(lambda: self.lam_moi_xem_truoc())

    def _dung_than(self, lo) -> None:
        """Lần phương án, thanh 6 mục, vùng soạn."""
        self._h_tren.insertWidget(self._h_tren.indexOf(self.b_ds_ho) + 1, self._tao_dai_lan())   # 1.0.05: lần phương án; 1.0.69: nằm trên thanh hộ
        from .man_hinh_the_muc import ThanhTheMuc
        self.thanh_the = ThanhTheMuc(self, self.tab.count())
        self.thanh_the.dat_huy_hieu(self.lb_tong_dd)
        self.tab.tabBar().hide()                       # thanh 6 mục thay cho thanh thẻ gốc
        lo.addWidget(self.thanh_the)
        lo_tach = QHBoxLayout()                         # 1.0.58: [danh sách hộ ghim] + vùng soạn | xem trước
        lo_tach.setContentsMargins(6, 0, 6, 0)
        lo_tach.setSpacing(6)
        lo_tach.addWidget(self.tach, 1)
        self._lo_tach = lo_tach
        lo.addLayout(lo_tach, 1)

    def _gan_phim_tat(self) -> None:
        """Phím tắt của cửa sổ."""
        self._phim = []
        for phim, ham in ((QKeySequence(QKeySequence.StandardKey.Save), lambda: self.luu()),
                          (QKeySequence('Ctrl+PgDown'), lambda: self.sang_ho(1)),
                          (QKeySequence('Ctrl+PgUp'), lambda: self.sang_ho(-1)),
                          # 0.9.72 (người dùng 13/10/2026): Ctrl + mũi tên trái / phải = hộ trước / hộ sau. Đang gõ trong ô chữ
                          # thì Ctrl + mũi tên vẫn nhảy từng từ (ô chữ nhận phím trước phím tắt - ShortcutOverride)
                          (QKeySequence('Ctrl+Right'), lambda: self.sang_ho(1)),
                          (QKeySequence('Ctrl+Left'), lambda: self.sang_ho(-1)),
                          # 0.9.78: Dán danh sách tài sản (nhận cả khi đang đứng ở thẻ Hồ sơ hay thẻ mục nào)
                          (QKeySequence('Ctrl+Shift+V'), lambda: self.mo_dan_tai_san()),
                          # 0.9.84: bật / tắt xem trước A4 (cả khi đang đứng trong ô bảng / ô chữ của cửa sổ)
                          (QKeySequence('F4'), lambda: self.bat_tat_xem_truoc()),
                          # 1.0.55: giải trình cách tính dòng đang chọn (không dùng F2 - phím sửa ô của bảng)
                          (QKeySequence('Ctrl+I'), lambda: self.xem_giai_trinh_dong()),
                          # 1.0.58: ghim danh sách hộ bên trái
                          (QKeySequence('Ctrl+B'), lambda: self.bat_tat_ds_ho())):
            sc = QShortcut(phim, self)
            # WidgetWithChildren: chỉ khi đang làm việc trên cửa sổ lập PA — tránh đụng Ctrl+Shift+V của tab Đơn giá bồi thường
            if phim.toString() == 'Ctrl+Shift+V':
                sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(ham)
            self._phim.append(sc)

    # ---------------------------------------------- nhiều lần lập phương án (1.0.05)
    def _tao_dai_dinh_danh(self) -> QFrame:
        """Dải định danh hộ (ảnh mẫu 20/10/2026): Chủ hộ | Số CCCD | Địa chỉ | Đợt trình ...... Tổng kinh phí phương án [khung vàng].
        Kiểu: giao_dien.QSS_LAP_PA_DAI (QSS chung - không setStyleSheet trên khung chứa)."""
        from .man_hinh import CAO_DAI_DINH_DANH      # 1.1.05: tên của man_hinh (nạp lúc gọi)
        from .giao_dien import NhanRutGon
        f = QFrame()
        f.setObjectName('dai_dinh_danh')
        f.setFixedHeight(CAO_DAI_DINH_DANH)
        h = QHBoxLayout(f)
        h.setContentsMargins(10, 3, 10, 3)
        h.setSpacing(6)
        self.dai_dinh_danh = f
        self.dd = {}

        def cap(khoa, nhan, gt, gian=0):
            lb = QLabel(nhan)
            lb.setProperty('vai_dd', 'nhan')
            h.addWidget(lb)
            gt.setProperty('vai_dd', khoa)
            h.addWidget(gt, gian)
            self.dd[khoa] = (lb, gt)
            h.addSpacing(10)
        cap('ten', 'Chủ hộ:', QLabel(''))
        cap('cccd', 'Số CCCD:', QLabel(''))
        dc = NhanRutGon('')
        dc.setMinimumWidth(120)
        cap('dia_chi', 'Địa chỉ:', dc, 1)
        cap('dot', 'Đợt:', QLabel(''))
        lb = QLabel('Tổng kinh phí:')
        lb.setProperty('vai_dd', 'nhan')
        h.addWidget(lb)
        self.lb_tong_dd = QLabel('')
        self.lb_tong_dd.setObjectName('tong_dinh_danh')
        h.addWidget(self.lb_tong_dd)
        self.dd['tong'] = (lb, self.lb_tong_dd)
        return f

    def _tao_dai_lan(self) -> QFrame:
        """Dải lần phương án: chọn lần (lần đầu / bổ sung), trạng thái phê duyệt, cộng dồn; lập bổ sung, sửa tên - số PA, mở khóa
        lần đã phê duyệt (điều chỉnh), xóa lần bổ sung chưa duyệt."""
        f = QFrame()
        f.setObjectName('dai_lan_pa')
        h = QHBoxLayout(f)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        self.nhan_lan = nhan = QLabel('Lần:')
        nhan.setProperty('vai', 'nhan')
        self.cb_lan = QComboBox()
        self.cb_lan.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cb_lan.setMinimumContentsLength(24)      # 30/10/2026: đủ chữ "Lần 2: Điều chỉnh khối lượng…" (trước 14 - cắt)
        self.cb_lan.setToolTip('Mỗi lần lập phương án (lần đầu, bổ sung lần 1, 2…) có dòng tài sản / chính sách, số phương án và '
                               'quyết định phê duyệt riêng. Lần đã có quyết định chỉ xem - không làm sai quyết định cũ.')
        self.cb_lan.activated.connect(lambda i: self.chon_lan(self.cb_lan.itemData(i)))
        from .giao_dien import KieuNut, NhanRutGon, ap_kieu_nut
        # trạng thái lần đang xem ("ĐÃ PHÊ DUYỆT (QĐ …) - CHỈ XEM" / "ĐANG LẬP DỰ THẢO") + tổng lần này / cộng dồn cả hộ
        self.lb_trang_thai_lan = QLabel('')
        self.lb_trang_thai_lan.setObjectName('lb_trang_thai_lan')
        self.lb_lan = self.lb_tong_cong_don = NhanRutGon('')
        self.lb_lan.setObjectName('lb_lan_pa')
        self.b_lan_moi = QPushButton('+ PA bổ sung')
        ap_kieu_nut(self.b_lan_moi, KieuNut.PHU)     # 1.0.55: nút phụ - không tranh nổi bật với nút Lưu / nút chính của cửa sổ
        self.b_lan_moi.setToolTip('Lập thêm một phương án cho hộ (tài sản, chính sách bổ sung) - các lần trước và quyết định đã '
                                  'phê duyệt giữ nguyên; tổng của hộ cộng dồn mọi lần')
        self.b_lan_moi.clicked.connect(lambda: self.lap_bo_sung())
        self.b_dieu_chinh = QPushButton('+ PA điều chỉnh')
        ap_kieu_nut(self.b_dieu_chinh, KieuNut.PHU)
        self.b_dieu_chinh.setToolTip('Sửa phương án đã lập / đã phê duyệt bị sai: chép lần đang xem sang lần điều chỉnh để sửa. '
                                     'Lần gốc giữ nguyên để in; tổng của hộ tính theo lần điều chỉnh, tiền quyết định = chênh lệch.')
        self.b_dieu_chinh.clicked.connect(lambda: self.lap_dieu_chinh())
        self.b_sua_lan = QPushButton('Sửa')
        self.b_sua_lan.setToolTip('Sửa lần: tên lần phương án, số / ngày phương án chi tiết của lần này')
        self.b_sua_lan.clicked.connect(lambda: self.sua_lan())
        self.b_mo_khoa = QPushButton('Mở khóa')
        self.b_mo_khoa.setToolTip('Lần đã có quyết định phê duyệt: cho sửa lại (điều chỉnh quyết định). Số liệu quyết định đã ghi '
                                  'giữ nguyên - cần ban hành quyết định điều chỉnh.')
        self.b_mo_khoa.clicked.connect(lambda: self.mo_khoa_lan())
        self.b_khoa_lan = QPushButton('Khóa lại')
        self.b_khoa_lan.setToolTip('Lần này đang mở khóa để điều chỉnh: khóa lại, chỉ xem như trước khi mở khóa.')
        self.b_khoa_lan.clicked.connect(lambda: self.khoa_lai_lan())
        self.b_xoa_lan = QPushButton('Xóa')
        self.b_xoa_lan.setToolTip('Xóa lần: chỉ xóa được lần bổ sung chưa có quyết định phê duyệt (cùng mọi dòng của lần đó)')
        self.b_xoa_lan.clicked.connect(lambda: self.xoa_lan())
        for b in (self.b_lan_moi, self.b_dieu_chinh, self.b_sua_lan, self.b_mo_khoa, self.b_khoa_lan, self.b_xoa_lan):
            b.setFixedHeight(26)
        self.cb_lan.setFixedHeight(26)
        # 1.0.63: một dải duy nhất - lần | V0 -> V1 -> V2.n -> V3 | trạng thái | Đối chiếu, "…". Bổ sung, điều chỉnh, sửa, xóa lần vào menu "…"
        from .man_hinh_phien_ban import ThanhPhienBan
        self.thanh_pb = ThanhPhienBan(self)
        self._nut_an_lan = QWidget(f)                   # giữ các nút (trạng thái bật / tắt, chữ) làm nguồn cho menu; luôn ẩn, không chiếm chỗ
        la = QHBoxLayout(self._nut_an_lan)
        for b in (self.b_lan_moi, self.b_dieu_chinh, self.b_sua_lan, self.b_xoa_lan, self.lb_trang_thai_lan, self.lb_lan):
            la.addWidget(b)
        self.nut_them_lan = QPushButton('⋯ ▾')
        self.nut_them_lan.setFixedHeight(26)
        self.nut_them_lan.setToolTip('Thêm PA bổ sung, PA điều chỉnh; sửa, xóa lần phương án')
        self.menu_lan = QMenu(self.nut_them_lan)
        self.menu_lan.setToolTipsVisible(True)
        self.menu_lan.aboutToShow.connect(self._ve_menu_lan)
        self.nut_them_lan.setMenu(self.menu_lan)
        h.addWidget(nhan)
        h.addWidget(self.cb_lan)
        h.addWidget(self.thanh_pb)
        h.addWidget(self.thanh_pb.b_khoa)
        h.addWidget(self.b_mo_khoa)
        h.addWidget(self.b_khoa_lan)
        self.b_khoa_lan.hide()
        h.addWidget(self.thanh_pb.b_dc)
        h.addWidget(self.nut_them_lan)
        h.addWidget(self._nut_an_lan)
        self._nut_an_lan.hide()
        self.dai_lan = f
        return f

    def hang_dieu_huong(self, the: int | None = None) -> QHBoxLayout:
        """0.9.95: MỘT hàng dưới đáy cửa sổ (28 px) = dải tổng cộng `lb_tong` + ◀ Trở lại / Tiếp theo ▶ theo thẻ đang xem (trước
        0.9.95 mỗi thẻ một hàng nút riêng cao 40 px). Thẻ cuối không có nút lưu riêng: "Lưu (Ctrl+S)" ở thanh trên.
        1.0.02: hàng nằm trong khung `dai_dieu_huong` (nền slate, vạch trên) - trả về layout của khung."""
        from .man_hinh import NhanTongPA      # 1.1.05: tên của man_hinh (nạp lúc gọi)
        self.dai_dieu_huong = QFrame()
        self.dai_dieu_huong.setObjectName('dai_dieu_huong')
        dat_kieu_theo_tong(self.dai_dieu_huong, QSS_DAI_DIEU_HUONG)
        h = QHBoxLayout(self.dai_dieu_huong)
        h.setContentsMargins(8, 3, 6, 3)
        h.setSpacing(6)
        self.dai_dieu_huong.setFixedHeight(34)
        self.b_tro_lai = QPushButton('◀ Mục trước')
        self.b_tiep_theo = QPushButton('Mục tiếp theo ▶')
        self.b_tro_lai.clicked.connect(lambda: self.sang_the(self.tab.currentIndex() - 1))
        self.b_tiep_theo.clicked.connect(lambda: self.sang_the(self.tab.currentIndex() + 1))
        for b in (self.b_tro_lai, self.b_tiep_theo):
            b.setFixedHeight(26)
        # 1.0.51: trạng thái lưu + chu kỳ lưu tự động ở dải đáy (thanh trên đã kín ở màn hình 1366 @125%)
        from . import chu_de
        self.lb_trang_thai_luu = QLabel('')
        self.lb_trang_thai_luu.setObjectName('trang_thai_luu')
        self.cb_tu_luu = QComboBox()
        self.cb_tu_luu.setObjectName('o_tu_luu')
        for giay, nhan in chu_de.CAC_MUC_LUU_TU_DONG:
            self.cb_tu_luu.addItem(nhan, giay)
        self.cb_tu_luu.setToolTip('Lưu tự động phương án / hồ sơ hộ sau khoảng thời gian NGỪNG thao tác (không cắt ngang ô đang gõ, '
                                  'không hiện hộp thoại). Tắt: chỉ lưu khi bấm Lưu / Ctrl+S.')
        self.cb_tu_luu.setFixedHeight(26)
        self.cb_tu_luu.setMaximumWidth(92)              # chữ ngắn nhất "Tắt", dài nhất "10 giây": nhường chỗ cho số tổng
        i = self.cb_tu_luu.findData(chu_de.chu_ky_luu_tu_dong())
        self.cb_tu_luu.setCurrentIndex(max(0, i))
        self.cb_tu_luu.activated.connect(lambda *_: self._doi_chu_ky_tu_luu())
        self.lb_chan = NhanTongPA()                     # 06/11/2026: hẹp thì chữ gọn dần, số tổng không bị cắt ("TỔNG CỘNG PHƯƠNG ÁN: 162" đọc nhầm số tiền)
        self.lb_chan.setObjectName('lb_chan_lap_pa')
        nhan_tl = QLabel('Tự lưu:')
        nhan_tl.setProperty('vai', 'nhan')
        h.addWidget(self.lb_tong)
        self.lb_tong.hide()                             # chi tiết từng mục: chú thích của lb_chan
        h.addWidget(self.lb_chan, 1)
        h.addWidget(self.lb_trang_thai_luu)
        h.addWidget(nhan_tl)
        h.addWidget(self.cb_tu_luu)
        h.addWidget(self.b_tro_lai)
        h.addWidget(self.b_tiep_theo)
        self.tab.currentChanged.connect(lambda i: self._cap_nhat_dieu_huong(i))
        self._cap_nhat_dieu_huong(self.tab.currentIndex() if the is None else the)
        return h

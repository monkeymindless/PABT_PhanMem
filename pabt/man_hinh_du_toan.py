"""Màn hình dự toán / khái toán kinh phí bồi thường, hỗ trợ (logic: du_toan.py). Dùng được khi chưa mở dự án nào
(đơn giá lấy theo bộ đơn giá đang dùng của máy).

0.9.23 (lộ trình người dùng 11/10/2026: dự toán là "mục tiêu tài chính của dự án", đưa lên nhóm Dự án): KhungDuToan là MỘT TRANG
của cửa sổ chính (trước: hộp thoại HopDuToan - nay chỉ là vỏ cho mã cũ / kiểm thử); thẻ "So sánh với thực tế áp giá" (khái toán
đã duyệt = ngân sách trần, cảnh báo vượt); sửa một ô chỉ vẽ lại dòng đó + các dòng % + tổng (trước: dựng lại cả bảng mỗi ô).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFrame,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton, QRadioButton,
                               QSizePolicy, QStackedWidget, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import du_toan
from .du_toan import DongDT, DuToan
from .lap_pa import DanhMuc, LoiNhap, doc_so
from .tien import D, KHONG, so_vn, tien_bang_chu, vn
from .giao_dien import con_tro_cho
from .thong_bao import chu_loi

TIEU_DE = 'Dự toán & khái toán'
XAM, XANH = QColor('#F2F2F2'), QColor('#DDEBF7')
DO_NHAT, XANH_LA = QColor('#F8CBAD'), QColor('#E2EFDA')
COT_SS = ['Mục', 'Hạng mục', 'Khái toán (đ)', 'Thực tế áp giá (đ)', 'Chênh lệch (đ)', 'Tỷ lệ']
COT = [('muc', 'Mục', 45), ('ten', 'Hạng mục', 380), ('dvt', 'ĐVT', 60), ('khoi_luong', 'Khối lượng (%)', 100),
       ('don_gia', 'Đơn giá (đ)', 110), ('he_so', 'Hệ số / tỷ lệ', 80), ('thanh_tien', 'Thành tiền (đ)', 130), ('ma', 'Mã', 70),
       ('can_cu', 'Căn cứ, ghi chú', 300)]
SO = {'khoi_luong', 'don_gia', 'he_so', 'thanh_tien', 'muc'}


class HopTraNQ28(QDialog):
    """Chọn giá đất theo bảng giá NQ 28/2025 (đồng/m²)."""

    def __init__(self, parent=None, xa: str = '', loai_dat: str = ''):
        super().__init__(parent)
        from . import gia_dat_nq28 as nq
        self.nq = nq
        self.chon = None
        self.dong = None
        self.setWindowTitle('Tra giá đất — ' + nq.tom_tat())
        self.resize(1100, 560)
        self.cb_xa = QComboBox()
        self.cb_xa.addItem('Tất cả địa bàn', '')
        for x in nq.ds_xa():
            self.cb_xa.addItem(x, x)
        i = next((k for k in range(self.cb_xa.count()) if xa and nq.khop_xa(xa, self.cb_xa.itemData(k) or '')), 0)
        self.cb_xa.setCurrentIndex(i)
        self.cb_cot = QComboBox()
        for k, t in nq.COT:
            self.cb_cot.addItem(t, k)
        cot = nq.cot_cua_loai(loai_dat)
        if cot:
            self.cb_cot.setCurrentIndex([k for k, _ in nq.COT].index(cot))
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tên đường, điểm đầu / cuối, vị trí (MT, T1…K3)…')
        self.bang = QTableWidget(0, 6)
        self.bang.setHorizontalHeaderLabels(['Địa bàn', 'Tên đường', 'Từ', 'Đến', 'Vị trí', 'Giá (đồng/m²)'])
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.verticalHeader().setVisible(False)
        for c, w in enumerate((120, 260, 220, 220, 60, 120)):
            self.bang.setColumnWidth(c, w)
        self.bang.doubleClicked.connect(lambda *_: self.accept())
        h = QHBoxLayout()
        for w in (QLabel('Địa bàn:'), self.cb_xa, QLabel('Loại đất:'), self.cb_cot, self.o_tim):
            h.addWidget(w)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText('Lấy giá này')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        lo.addLayout(h)
        lo.addWidget(self.bang)
        lo.addWidget(nut)
        for s in (self.cb_xa.currentIndexChanged, self.cb_cot.currentIndexChanged, self.o_tim.textChanged):
            s.connect(lambda *_: self.loc())
        self.loc()

    def loc(self):
        nq = self.nq
        self.ds = nq.tim(self.cb_xa.currentData() or '', self.o_tim.text())[:500]
        cot = self.cb_cot.currentData()
        self.bang.setRowCount(len(self.ds))
        for r, x in enumerate(self.ds):
            for c, v in enumerate((x['xa'], x['ten_duong'], x['diem_dau'], x['diem_cuoi'], x['vi_tri'], vn(nq.gia_dong(x, cot)))):
                it = QTableWidgetItem(str(v))
                it.setToolTip(nq.mo_ta_vi_tri(x) if c == 4 else str(v))
                self.bang.setItem(r, c, it)

    def accept(self):
        r = self.bang.currentRow()
        if not 0 <= r < len(self.ds):
            return
        x, cot = self.ds[r], self.cb_cot.currentData()
        self.dong = x                                   # dòng bảng giá đã chọn (cửa sổ lập phương án ghi vị trí + giá theo dòng này)
        self.chon = (D(self.nq.gia_dong(x, cot)), self.nq.can_cu(x, cot))
        super().accept()


# nhãn ngắn trên khối thông tin chuẩn bị đầu tư (vừa màn hình 1366; tên đầy đủ du_toan.NHAN_CHUAN_BI ở chú thích)
NHAN_NGAN = {'ten': 'Dự án', 'dia_ban': 'Địa bàn', 'quy_mo_dt': 'DT dự kiến', 'so_thua_dk': 'Số thửa', 'so_ho_dk': 'Số hộ',
             'kinh_phi': 'Kinh phí QĐ08'}


def _co_theo_ky_tu(cb: QComboBox, n: int) -> None:
    """Ô chọn rộng theo n ký tự (không theo mục dài nhất) - danh sách xổ xuống vẫn hiện đủ chữ."""
    cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    cb.setMinimumContentsLength(n)
    cb.view().setMinimumWidth(cb.view().sizeHintForColumn(0) + 24)


class KhungDuToan(QWidget):
    """Trang "Dự toán & khái toán": thẻ 1 lập khái toán / dự toán (lấy khối lượng từ dự án đang mở, file .pabt, file Excel, danh
    sách thô; áp đơn giá hiện hành; chi phí tổ chức 2,5% / 3,5% theo QĐ 08/2025), thẻ 2 so sánh với thực tế áp giá."""
    im_lang = False

    def __init__(self, parent=None, con=None, file_du_an=None):
        super().__init__(parent)
        self.con, self.file_du_an = con, file_du_an
        self.file = None
        self.dt = DuToan()
        self.dt_goc = None                              # khái toán đã duyệt mở từ file (thẻ So sánh); None: dùng bảng thẻ 1
        self.ss = None                                  # kết quả so sánh gần nhất (du_toan.so_sanh)
        self.dt_goc_file = None
        self.b_tu_du_an = None                          # nút "Từ dự án đang mở": bật / tắt theo dự án (dat_du_an)
        self._dm = None
        from .giao_dien import KieuNut, ap_kieu_nut
        from .hang_nhap_nhanh import HangNhapNhanh
        from .loai_dat import ds_chon
        from .nghiep_vu import MUC_VN
        # 0.9.71 (người dùng 12/10/2026 - bo_cuc_khai_toan.txt): tiêu đề phân hệ + chế độ | thông tin chuẩn bị đầu tư | thanh nhập
        # nhanh MỘT khung | bảng dự toán (phần lớn chiều cao) | thẻ tổng cộng | hàng nút đáy. Logic giữ nguyên (cùng đối tượng:
        # bang, hang, cb_loai_dat / o_dt_dat / o_gia_dat, lb_tong, lb_tb; self.tab = 2 chế độ, thanh thẻ ẩn - nút chọn chế độ)
        tieu = QLabel('KHÁI TOÁN KINH PHÍ BỒI THƯỜNG, HỖ TRỢ & TÁI ĐỊNH CƯ')
        tieu.setObjectName('tieu_khai_toan')
        tieu.setStyleSheet('QLabel#tieu_khai_toan { font-size: 13px; font-weight: bold; color: #0F3866; }')
        self.rd_khai_toan = QRadioButton('Lập khái toán')
        self.rd_so_sanh = QRadioButton('So sánh với thực tế')
        self.rd_khai_toan.setChecked(True)
        self.nhom_che_do = QButtonGroup(self)
        self.nhom_che_do.addButton(self.rd_khai_toan, 0)
        self.nhom_che_do.addButton(self.rd_so_sanh, 1)
        h_top = QHBoxLayout()
        h_top.addWidget(tieu)
        h_top.addStretch(1)
        nhan = QLabel('Chế độ:')
        nhan.setProperty('vai', 'nhan')
        h_top.addWidget(nhan)
        h_top.addWidget(self.rd_khai_toan)
        h_top.addWidget(self.rd_so_sanh)
        khoi_dau = self._khoi_chuan_bi()                # 7 trường + Kinh phí QĐ08 (lưu trong .pabtdt)
        # ---- thanh nhập nhanh: Lấy khối lượng ▾ | Mục | (đất: loại đất, diện tích, đơn giá) / (tài sản: hàng dùng chung với hộ)
        self.b_lay = QPushButton('Lấy khối lượng')
        self.b_lay.setToolTip('Lấy khối lượng (thay các dòng đang có) từ dự án đang mở, file dự án .pabt, file PABT Excel hoặc danh '
                              'sách thô; áp đơn giá hiện hành của bộ đơn giá')
        m_lay = QMenu(self.b_lay)
        self.b_tu_du_an = m_lay.addAction('Từ dự án đang mở', lambda: self.lay('du_an'))
        self.b_tu_du_an.setEnabled(con is not None)
        m_lay.addAction('Từ file dự án .pabt…', lambda: self.lay('pabt'))
        m_lay.addAction('Từ file PABT Excel…', lambda: self.lay('excel'))
        m_lay.addAction('Từ danh sách thô…', lambda: self.lay('tho'))
        m_lay.addSeparator()
        m_lay.addAction('Áp đơn giá hiện hành', lambda: self.ap_gia_hien_hanh())
        self.b_lay.setMenu(m_lay)
        self.cb_muc_nhap = QComboBox()
        for k, t in ((1, '1. Đất'), (2, '2. Nhà, công trình'), (3, '3. Cây trồng'), (MUC_VN, '4. Vật nuôi'), (4, '5. Hỗ trợ'),
                     (5, '6. Thưởng')):
            self.cb_muc_nhap.addItem(t, k)
        self.cb_muc_nhap.setToolTip('Mục của hạng mục cần thêm (số in trên bảng khái toán)')
        _co_theo_ky_tu(self.cb_muc_nhap, 11)
        self.cb_muc_nhap.setProperty('nhap', '1')
        # đất (mục 1): loại đất xổ xuống (dùng chung danh sách loại đất của phương án hộ), diện tích, đơn giá
        self.cb_loai_dat = QComboBox()
        self.cb_loai_dat.setEditable(True)
        self.cb_loai_dat.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cb_loai_dat.setMaxVisibleItems(20)
        _co_theo_ky_tu(self.cb_loai_dat, 20)          # không rộng theo tên loại đất dài nhất (trang vừa màn hình 1366)
        for ma, nhan in ds_chon(con):
            self.cb_loai_dat.addItem(nhan, ma)
        self.cb_loai_dat.setCurrentIndex(-1)
        self.cb_loai_dat.lineEdit().setPlaceholderText('Loại đất (▼ chọn, hoặc gõ mã: CLN, ONT…)')
        self.o_dt_dat = QLineEdit()
        self.o_dt_dat.setPlaceholderText('Diện tích (m²), =12*30')
        self.o_dt_dat.setMaximumWidth(190)
        self.o_gia_dat = QLineEdit()
        self.o_gia_dat.setPlaceholderText('Đơn giá (đ/m²)')
        self.o_gia_dat.setMaximumWidth(190)
        self.o_gia_dat.returnPressed.connect(lambda: self.them_dat())
        self.o_dt_dat.returnPressed.connect(lambda: self.them_dat())
        # Enter ở ô Loại đất: sang ô Diện tích (Diện tích / Đơn giá: Enter = thêm đất)
        self.cb_loai_dat.lineEdit().returnPressed.connect(lambda: (self.o_dt_dat.setFocus(), self.o_dt_dat.selectAll()))
        trang_dat = QWidget()
        h_dat = QHBoxLayout(trang_dat)
        h_dat.setContentsMargins(0, 0, 0, 0)
        h_dat.setSpacing(6)
        h_dat.addWidget(self.cb_loai_dat, 3)
        h_dat.addWidget(self.o_dt_dat, 1)
        h_dat.addWidget(self.o_gia_dat, 1)
        # tài sản: CÙNG hàng nhập nhanh và bộ lệnh với lập phương án hộ (hang_nhap_nhanh + nhap_tai_san, 0.9.67); ô Mục của hàng
        # ẩn (chọn ở ô Mục của thanh), nút Thêm của hàng ẩn (một nút Thêm vào bảng cho cả đất lẫn tài sản)
        self.hang = HangNhapNhanh(lambda: self.them_nhanh(), chon_muc=[
            (2, 'Nhà, công trình'), (3, 'Cây trồng'), (MUC_VN, 'Vật nuôi'), (4, 'Hỗ trợ'), (5, 'Thưởng')])
        self.hang.cb_muc.setVisible(False)
        self.hang.nut_them.setVisible(False)
        self.ngan_nhap = QStackedWidget()
        self.ngan_nhap.addWidget(trang_dat)
        self.ngan_nhap.addWidget(self.hang)
        self.b_tra_nq28 = QPushButton('Tra NQ 28…')
        self.b_tra_nq28.setToolTip('Tra giá đất Nghị quyết 28/2025 cho ô Đơn giá (theo địa bàn, loại đất)')
        self.b_tra_nq28.clicked.connect(lambda: self._tra_gia_o_dat())
        self.b_dan = b_dan = QPushButton('Dán danh sách…')
        b_dan.setToolTip('Dán danh sách tài sản chép từ bảng Excel, bảng Word hoặc văn bản bất kỳ: tự xếp vào nhà / cây / vật nuôi / '
                         'hỗ trợ')
        b_dan.clicked.connect(lambda: self.dan_tai_san())
        self.b_ocr = QPushButton('Quét giấy tờ…')
        self.b_ocr.setToolTip('Ảnh chụp / PDF Giấy chứng nhận QSDĐ, biên bản kiểm kê: nhận dạng chữ (OCR) lấy thửa đất (loại đất, diện tích) '
                              'và tài sản, cây trồng đưa vào bảng khái toán')
        self.b_ocr.clicked.connect(lambda: self.quet_giay_to())
        self.b_them = QPushButton('Thêm vào bảng')
        self.b_them.setAutoDefault(True)                # Enter khi đang ở nút (ngoài hộp thoại Qt chỉ nhận Space)
        self.b_them.clicked.connect(lambda: self.them_tu_thanh())
        ap_kieu_nut(self.b_them, KieuNut.CHINH)
        self.b_them_dat = self.b_them                   # tên cũ (0.9.71 trước bố cục mới)
        self.cb_muc_nhap.currentIndexChanged.connect(lambda *_: self._doi_muc_nhap())
        dock = self.thanh_nhap = QFrame()
        dock.setObjectName('thanh_nhap_nhanh')
        # không ép bề rộng tối thiểu của trang (như NhanRutGon): hẹp thì nút xuống dòng (_xep_thanh_nhap), cửa sổ không bị đẩy
        # rộng hơn màn hình 1366 (lỗi phóng to 0.9.26)
        dock.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        dock.setStyleSheet('QFrame#thanh_nhap_nhanh { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; }')
        v_dock = QVBoxLayout(dock)
        v_dock.setContentsMargins(8, 5, 8, 5)
        v_dock.setSpacing(4)
        h_d1 = QHBoxLayout()
        h_d1.setSpacing(6)
        h_d1.addWidget(self.b_lay)
        self.nhan_muc = QLabel('Mục:')
        self.nhan_muc.setProperty('vai', 'nhan')
        h_d1.addWidget(self.nhan_muc)
        h_d1.addWidget(self.cb_muc_nhap)
        h_d1.addWidget(self.ngan_nhap, 1)
        # cả thanh MỘT hàng (người dùng 13/10/2026: thêm ~28 px chiều cao cho bảng): nút ở cuối hàng; ô của hàng nhập tài sản co
        # lại cho vừa (Khối lượng 90, Tỷ lệ 60, Ghi chú 120-180, số đo 100-150); dòng thông báo chỉ hiện khi có chữ
        self.khoi_nut_nhap = QWidget()
        h_nut = QHBoxLayout(self.khoi_nut_nhap)
        h_nut.setContentsMargins(0, 0, 0, 0)
        h_nut.setSpacing(6)
        for b in (self.b_tra_nq28, b_dan, self.b_ocr, self.b_them):
            h_nut.addWidget(b)
        h_d1.addWidget(self.khoi_nut_nhap)
        self._h_d1 = h_d1
        self._h_d2 = QHBoxLayout()                      # hàng dự phòng: nút xuống đây khi cửa sổ hẹp
        self._h_d2.addStretch(1)
        self.hang.layout().setSpacing(6)
        # kiểu ô gọn (đặc tả: thanh cao ~38 px) thay kiểu ô nhập lớn [nhap="1"] (chữ 14 px, lề 11 px) - vừa một hàng ở 1366
        for w in (self.cb_muc_nhap, self.cb_loai_dat, self.o_dt_dat, self.o_gia_dat, self.hang.o_chon.o, self.hang.cb_kieu,
                  self.hang.o_do, self.hang.o_sl, self.hang.o_tl, self.hang.o_gc):
            if w is not None:
                w.setProperty('nhap', '0')
        self.hang.o_sl.setFixedWidth(90)
        if self.hang.cb_kieu is not None:
            _co_theo_ky_tu(self.hang.cb_kieu, 10)
            self.hang.cb_kieu.currentIndexChanged.connect(lambda *_: QTimer.singleShot(0, self._xep_thanh_nhap))
        self.hang.o_tl.setFixedWidth(60)
        self.hang.o_tl.setPlaceholderText('Tỷ lệ')
        for o in (self.hang.o_sl, self.hang.o_tl):     # ô hẹp: lề trong nhỏ để chữ gợi ý không bị cắt "Khối lượ…"
            o.setStyleSheet('QLineEdit { padding-left: 4px; padding-right: 4px; }')
        self.hang.o_gc.setMinimumWidth(120)
        self.hang.o_gc.setMaximumWidth(180)
        if self.hang.o_do is not None:
            self.hang.o_do.setMinimumWidth(100)
            self.hang.o_do.setMaximumWidth(150)
        self.lb_tb = QLabel('')                         # thông báo của lần thêm gần nhất (không bật hộp thoại mỗi lần thêm)
        self.lb_tb.setWordWrap(True)
        self.lb_tb.setStyleSheet('QLabel { color: #475569; }')
        self.lb_tb.setVisible(False)
        v_dock.addLayout(h_d1)
        v_dock.addLayout(self._h_d2)
        v_dock.addWidget(self.lb_tb)
        dock.installEventFilter(self)
        # ---- bảng dự toán
        self.bang = QTableWidget(0, len(COT))
        self.bang.setHorizontalHeaderLabels([c[1] for c in COT])
        for i, c in enumerate(COT):
            self.bang.setColumnWidth(i, c[2])
        self.bang.horizontalHeader().setSectionResizeMode(len(COT) - 1, QHeaderView.ResizeMode.Stretch)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setWordWrap(True)
        self.bang.setAlternatingRowColors(True)
        self.bang.cellChanged.connect(self._doi_o)
        self.bang.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bang.customContextMenuRequested.connect(self._menu_bang)
        h_bang = QHBoxLayout()
        nhan = QLabel('BẢNG DỰ TOÁN KINH PHÍ CHI TIẾT')
        nhan.setProperty('vai', 'nhan')
        h_bang.addWidget(nhan)
        h_bang.addStretch(1)
        for ten, ham in (('Thêm dòng', lambda: self.them_dong()), ('Tra giá đất dòng chọn…', lambda: self.tra_gia_dat()),
                         ('Xóa dòng', lambda: self.xoa_dong())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            h_bang.addWidget(b)
        # ---- thẻ tổng cộng + hàng nút đáy
        self.lb_tong = QLabel('')
        self.lb_tong.setObjectName('the_tong_khai_toan')
        self.lb_tong.setWordWrap(True)
        self.lb_tong.setTextFormat(Qt.TextFormat.RichText)
        self.lb_tong.setStyleSheet('QLabel#the_tong_khai_toan { background: #ECFDF5; border-left: 4px solid #107C41; '
                                   'border-radius: 4px; padding: 6px 10px; color: #065F46; }')
        b_mo = QPushButton('Mở tệp (.pabtdt)…')
        b_mo.clicked.connect(lambda: self.mo())
        b_moi = QPushButton('Tạo mới')
        b_moi.setToolTip('Khái toán mới (trống): xóa thông tin và các dòng đang có trên màn hình')
        b_moi.clicked.connect(lambda: self.tao_moi())
        self.b_xuat = QPushButton('Xuất báo cáo')
        m_xuat = QMenu(self.b_xuat)
        m_xuat.addAction('Bảng khái toán (Excel)…', lambda: self.xuat_khai_toan())
        m_xuat.addAction('Bảng khái toán (PDF)…', lambda: self.xuat_khai_toan(pdf=True))
        m_xuat.addAction('Bảng chi tiết (Excel)…', lambda: self.xuat())
        self.b_xuat.setMenu(m_xuat)
        self.b_luu = QPushButton('LƯU DỰ TOÁN (Ctrl+S)')
        self.b_luu.setToolTip('Lưu khái toán vào file .pabtdt (Ctrl+S khi đang ở trang này)')
        self.b_luu.clicked.connect(lambda: self.luu())
        ap_kieu_nut(self.b_luu, KieuNut.LUU)
        h_day = QHBoxLayout()
        for b in (b_mo, b_moi, self.b_xuat):
            h_day.addWidget(b)
        h_day.addStretch(1)
        h_day.addWidget(self.b_luu)
        ghi = QLabel('Mục 1 đất, 2 nhà - công trình, 3 cây trồng, 4 hỗ trợ, 5 thưởng, 6 chi phí khác (cột Khối lượng là %, tính trên '
                     'tổng mục 1-5). Thành tiền = khối lượng × đơn giá × hệ số, làm tròn như dự án. "Áp đơn giá hiện hành" thay '
                     'đơn giá các dòng có mã theo bộ đơn giá đang dùng (áp giá dự thảo cho dự án tương tự).')
        self._cach_tinh = ghi.text()                    # cách tính: chú thích của ô tổng (dòng chữ dài chiếm chỗ của bảng)
        the1 = QWidget()
        lo = QVBoxLayout(the1)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(6)
        lo.addWidget(khoi_dau)
        lo.addWidget(dock)
        lo.addLayout(h_bang)
        lo.addWidget(self.bang, 1)
        lo.addWidget(self.lb_tong)
        lo.addLayout(h_day)
        self.tab = QTabWidget()                         # 2 chế độ; thanh thẻ ẩn - chọn bằng nút Chế độ (giữ self.tab cho mã cũ)
        self.tab.addTab(the1, 'Khái toán / dự toán')
        self.tab.addTab(self._the_so_sanh(), 'So sánh với thực tế áp giá')
        self.tab.tabBar().setVisible(False)
        self.tab.setDocumentMode(True)
        self.tab.currentChanged.connect(lambda i: i == 1 and self.con is not None and self.so_sanh_thuc_te())
        self.tab.currentChanged.connect(lambda i: self.nhom_che_do.button(i).setChecked(True))
        self.nhom_che_do.idClicked.connect(self.tab.setCurrentIndex)
        ngoai = QVBoxLayout(self)
        ngoai.setContentsMargins(10, 8, 10, 8)
        ngoai.setSpacing(8)
        ngoai.addLayout(h_top)
        ngoai.addWidget(self.tab)
        self._doi_muc_nhap()
        self._dang_ve = False
        for k, w in self.o_cb.items():                  # gõ là ghi vào dự toán (lưu cùng file .pabtdt)
            if isinstance(w, QComboBox):
                w.currentIndexChanged.connect(lambda _=0, k=k, w=w: setattr(self.dt, k, w.currentData() or ''))
            else:
                w.textChanged.connect(lambda t, k=k: setattr(self.dt, k, ' '.join(t.split())))
        self.ve()
        self._nap_hang()

    def _khoi_chuan_bi(self) -> QFrame:
        """Thông tin chuẩn bị đầu tư & khái toán tổng mức (người dùng 12/10/2026, đặc tả ARCH-PABT-2026-V7 phần IV): hai hàng -
        Tên dự án, Chủ đầu tư, Nguồn vốn | Địa bàn thu hồi, Diện tích, Số thửa, Số hộ dự kiến. Lưu / mở cùng file .pabtdt, không
        lấy từ Thông tin dự án của file .pabt đang mở (lấy khối lượng từ dự án chỉ điền các ô còn trống)."""
        khung = QFrame()
        khung.setObjectName('khoi_chuan_bi')
        # có bộ chọn: kiểu không bộ chọn truyền sang ô gợi ý (tooltip) của các ô con -> nền đen
        khung.setStyleSheet('QFrame#khoi_chuan_bi { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; }')
        vo = QVBoxLayout(khung)
        vo.setContentsMargins(8, 6, 8, 6)
        vo.setSpacing(5)
        tieu = QLabel('THÔNG TIN CHUẨN BỊ ĐẦU TƯ & KHÁI TOÁN TỔNG MỨC')
        tieu.setProperty('vai', 'nhan')
        vo.addWidget(tieu)
        self.o_ten = QLineEdit()
        self.o_ten.setPlaceholderText('Tên dự án / công trình dự toán')
        self.o_chu_dau_tu = QLineEdit()
        self.o_chu_dau_tu.setPlaceholderText('Ban QLDA / doanh nghiệp')
        self.cb_nguon_von = QComboBox()
        self.cb_nguon_von.addItem('(chưa chọn)', '')
        for t in du_toan.NGUON_VON:
            self.cb_nguon_von.addItem(t, t)
        self.o_dia_ban = QLineEdit()
        self.o_dia_ban.setPlaceholderText('Xã, phường - dùng khi tra giá đất NQ 28')
        self.o_quy_mo = QLineEdit()
        self.o_quy_mo.setPlaceholderText('15,5 ha hoặc 155.000 m²')
        self.o_so_thua = QLineEdit()
        self.o_so_thua.setPlaceholderText('Số thửa')
        self.o_so_ho = QLineEdit()
        self.o_so_ho.setPlaceholderText('Số hộ')
        # đủ rộng cho chữ gợi ý (13/10/2026: "15,5 ha hoặc 1…", "Số t…" bị cắt)
        self.o_quy_mo.setMinimumWidth(130)
        self.o_so_thua.setMinimumWidth(75)
        self.o_so_ho.setMinimumWidth(75)
        self.o_cb = {'ten': self.o_ten, 'chu_dau_tu': self.o_chu_dau_tu, 'nguon_von': self.cb_nguon_von,
                     'dia_ban': self.o_dia_ban, 'quy_mo_dt': self.o_quy_mo, 'so_thua_dk': self.o_so_thua,
                     'so_ho_dk': self.o_so_ho}
        # Kinh phí tổ chức thực hiện QĐ 08/2025 (0.9.71): chọn loại -> dòng chi phí mục 6 theo mức của loại (+ dự phòng 10%)
        from .lap_pa import CAN_CU_KINH_PHI, LOAI_KINH_PHI
        self.cb_kp = QComboBox()
        self.cb_kp.addItem('Tự nhận theo tên', '')
        for k, (ten, toi_da) in LOAI_KINH_PHI.items():
            self.cb_kp.addItem({'tuyen': 'Tuyến', 'khac': 'Khu / cụm / khác'}.get(k, ten.split(' (')[0]) +
                               f' (≤ {so_vn(toi_da)}%)', k)
        _co_theo_ky_tu(self.cb_kp, 14)
        self.cb_kp.setToolTip(f'{CAN_CU_KINH_PHI}: hạ tầng theo tuyến không quá 3,5%; cụm, vùng, khu và dự án khác không quá '
                              '2,5%. Chọn loại: dòng "Chi phí tổ chức thực hiện" (mục 6) lấy mức của loại, kèm dự phòng 10%.')
        self.cb_kp.activated.connect(lambda _=0: self._doi_kinh_phi())        # chỉ khi người dùng chọn (nạp file: không thêm)
        for hang in ((('ten', 3), ('chu_dau_tu', 2), ('nguon_von', 2)),
                     (('dia_ban', 3), ('quy_mo_dt', 2), ('so_thua_dk', 1), ('so_ho_dk', 1), ('kinh_phi', 2))):
            h = QHBoxLayout()
            h.setSpacing(8)
            for k, gian in hang:
                nhan = QLabel(NHAN_NGAN.get(k, du_toan.NHAN_CHUAN_BI.get(k, '')) + ':')
                nhan.setToolTip(du_toan.NHAN_CHUAN_BI.get(k, 'Kinh phí tổ chức thực hiện bồi thường (QĐ 08/2025)'))
                nhan.setProperty('vai', 'nhan')
                h.addWidget(nhan)
                h.addWidget(self.cb_kp if k == 'kinh_phi' else self.o_cb[k], gian)
            vo.addLayout(h)
        return khung

    def _doi_kinh_phi(self):
        """Ô Kinh phí QĐ08: ghi loại vào dự toán và thêm / sửa dòng chi phí tổ chức thực hiện theo mức của loại."""
        self.dt.loai_kinh_phi = self.cb_kp.currentData() or ''
        self.them_chi_phi(self.dt.loai_kinh_phi or None)

    def eventFilter(self, o, e):
        if o is getattr(self, 'thanh_nhap', None) and e.type() == QEvent.Type.Resize:
            self._xep_thanh_nhap()
        return super().eventFilter(o, e)

    def can_mot_hang(self) -> int:
        """Bề rộng thanh nhập nhanh cần để mọi ô + nút nằm trên một hàng (theo mục / kiểu số đo đang chọn)."""
        ds = [self.b_lay, self.nhan_muc, self.cb_muc_nhap, self.ngan_nhap.currentWidget(), self.khoi_nut_nhap]
        m = self.thanh_nhap.layout().contentsMargins()
        return sum(max(w.minimumWidth(), w.minimumSizeHint().width()) for w in ds) + \
            self._h_d1.spacing() * (len(ds) - 1) + m.left() + m.right() + 2

    def _xep_thanh_nhap(self):
        """Một hàng khi đủ chỗ; hẹp hơn thì cụm nút (Tra NQ 28, Dán danh sách, Thêm vào bảng) xuống hàng dưới, canh phải."""
        if not hasattr(self, 'thanh_nhap'):
            return
        try:
            mot = self.thanh_nhap.width() >= self.can_mot_hang()
        except RuntimeError:                            # QTimer.singleShot(0) chạy sau khi khung đã bị xóa (đóng nhanh)
            return
        o_hang_1 = self._h_d1.indexOf(self.khoi_nut_nhap) >= 0
        if mot and not o_hang_1:
            self._h_d2.removeWidget(self.khoi_nut_nhap)
            self._h_d1.addWidget(self.khoi_nut_nhap)
        elif not mot and o_hang_1:
            self._h_d1.removeWidget(self.khoi_nut_nhap)
            self._h_d2.addWidget(self.khoi_nut_nhap)

    def _doi_muc_nhap(self):
        """Ô Mục của thanh nhập nhanh: Đất -> ô loại đất / diện tích / đơn giá (+ Tra NQ 28); mục khác -> hàng nhập tài sản."""
        m = self.cb_muc_nhap.currentData()
        dat = m == 1
        self.ngan_nhap.setCurrentIndex(0 if dat else 1)
        self.b_tra_nq28.setVisible(dat)
        if not dat:
            i = self.hang.cb_muc.findData(m)
            if i >= 0 and self.hang.cb_muc.currentIndex() != i:
                self.hang.cb_muc.setCurrentIndex(i)
        QTimer.singleShot(0, self._xep_thanh_nhap)      # bề rộng cần đổi theo mục (đất / tài sản, ô số đo cây)

    def them_tu_thanh(self):
        """Nút Thêm vào bảng của thanh nhập nhanh: đất (mục 1) hoặc tài sản theo ô Mục."""
        return self.them_dat() if self.cb_muc_nhap.currentData() == 1 else self.them_nhanh()

    def tao_moi(self):
        """Khái toán mới trống (hỏi khi đang có dòng)."""
        if self.dt.dong and not self.im_lang and QMessageBox.question(
                self, TIEU_DE, 'Bỏ khái toán đang mở (các dòng chưa lưu sẽ mất), tạo khái toán mới?') != \
                QMessageBox.StandardButton.Yes:
            return None
        self.dt = DuToan()
        self.file = None
        self.ve()
        return self.dt

    def _menu_bang(self, pos):
        m = QMenu(self)
        m.addAction('Thêm dòng', lambda: self.them_dong())
        m.addAction('Tra giá đất dòng chọn…', lambda: self.tra_gia_dat())
        m.addAction('Áp đơn giá hiện hành', lambda: self.ap_gia_hien_hanh())
        m.addSeparator()
        m.addAction('Xóa dòng', lambda: self.xoa_dong())
        m.exec(self.bang.viewport().mapToGlobal(pos))
        m.deleteLater()

    # ---------------------------------------------- nhập tài sản (dùng chung với lập phương án hộ)
    def _nap_hang(self):
        """Danh sách chọn của hàng nhập nhanh theo danh mục đang dùng (dự án đang mở, không thì bộ đơn giá)."""
        self.hang.nap(self.dm)

    def _dich(self):
        from .nhap_tai_san import DichDuToan
        return DichDuToan(self.dt, self.dm)

    def _sau_khi_them(self, d, tb: str = '', cot: str = 'khoi_luong'):
        """Vẽ lại (bảng sắp theo mục: tìm lại dòng vừa thêm theo đối tượng), chọn ô cần nhập tiếp, ghi thông báo."""
        self.ve()
        r = next((k for k, x in enumerate(self.dt.dong) if x is d), -1)
        if r >= 0:
            c = [x[0] for x in COT].index(cot)
            self.bang.setCurrentCell(r, c)
        self.lb_tb.setText(tb)
        self.lb_tb.setVisible(bool(tb))
        return r

    def them_nhanh(self, **thay):
        """Hàng nhập nhanh -> nhap_tai_san.them_mot (cùng lệnh với phương án hộ). thay: giá trị thay ô nhập (kiểm thử)."""
        from .nhap_tai_san import them_mot
        v = dict(self.hang.gia_tri(), **thay)
        try:
            i, tb, tu_do = them_mot(self._dich(), v['muc'], v['m'], v['ten'], v['so_luong'], v['ty_le'], v['kieu'],
                                    v['ghi_chu'], v.get('so_do', ''))
        except LoiNhap as e:
            self.bao(str(e))
            return None
        d = self.dt.dong[i]
        self.hang.xoa()
        r = self._sau_khi_them(d, tb, 'don_gia' if tu_do else 'khoi_luong')
        if tu_do and r >= 0:
            self.bang.editItem(self.bang.item(r, [x[0] for x in COT].index('don_gia')))
        return r

    def quet_giay_to(self, files=None, cho: bool = True):
        """Quét giấy tờ (OCR, 0.9.87): dòng đất + tài sản đọc từ ảnh chụp / PDF giấy chứng nhận, biên bản kiểm kê."""
        from .man_hinh_ocr import HopQuetGiayTo
        hop = HopQuetGiayTo(self, 'du_toan', self, files)
        if cho:
            hop.exec()
        return hop

    def dan_tai_san(self, chu: str = '', cho: bool = True):
        """Hộp "Dán danh sách tài sản" (cùng hộp với phương án hộ): dán nhiều dòng, tự xếp vào nhà / cây / vật nuôi / hỗ trợ."""
        from .man_hinh_phan_loai import HopDanTaiSan
        hop = HopDanTaiSan(self, chu, dich=self._dich())
        hop.im_lang = self.im_lang
        if cho:
            hop.exec()
        return hop

    def sau_khi_dan_tai_san(self, n: int, muc_cuoi: int) -> None:
        self.ve()
        self.lb_tb.setText(f'Đã thêm {n} dòng từ danh sách tài sản vào bảng dự toán.')
        self.lb_tb.setVisible(True)

    # ---------------------------------------------- danh mục đơn giá
    @property
    def dm(self) -> DanhMuc:
        if self._dm is None:
            if self.con is not None:
                self._dm = DanhMuc(self.con)
            else:
                from . import csdl, don_gia
                c = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
                try:
                    self._dm = DanhMuc(c)
                finally:
                    c.close()
        return self._dm

    def bao(self, chu: str, loi: bool = True):
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TIEU_DE, chu)

    # ---------------------------------------------- hiển thị
    def _ve_dong(self, r: int) -> None:
        """Dựng các ô của dòng r (gọi trong _dang_ve)."""
        d = self.dt.dong[r]
        pt = d.muc == 6 and d.phan_tram is not None
        gt = dict(muc=str(d.muc), ten=d.ten, dvt='%' if pt else d.dvt,
                  khoi_luong=so_vn(d.phan_tram) if pt else so_vn(d.khoi_luong),
                  don_gia=vn(self.dt.co_so_phan_tram()) if pt else vn(d.don_gia),
                  he_so='' if pt else so_vn(d.he_so), thanh_tien=vn(self.dt.thanh_tien(d)), ma=d.ma,
                  can_cu=d.can_cu + ('; ' if d.can_cu and d.ghi_chu else '') + d.ghi_chu)
        for c, (k, _, _) in enumerate(COT):
            it = QTableWidgetItem(gt[k])
            it.setToolTip(gt[k])
            if k in SO:
                it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if k == 'thanh_tien' or (pt and k in ('don_gia', 'he_so', 'dvt')):
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                it.setBackground(QBrush(XAM))
            if k == 'thanh_tien':
                f = QFont()
                f.setBold(True)
                it.setFont(f)
            self.bang.setItem(r, c, it)

    def ve(self, chon: int | None = None):
        self._dang_ve = True
        try:
            self.dt.sap_xep()
            self.bang.setRowCount(len(self.dt.dong))
            for r in range(len(self.dt.dong)):
                self._ve_dong(r)
        finally:
            self._dang_ve = False
        self.bang.resizeRowsToContents()                 # chữ dài xuống dòng, hiện đủ nội dung
        if chon is not None and 0 <= chon < len(self.dt.dong):
            self.bang.setCurrentCell(chon, 1)
        self._ve_dau_tong()

    def _ve_lai_dong(self, r: int) -> None:
        """Sửa một ô (không đổi mục - không đổi thứ tự dòng): vẽ lại dòng r, các dòng % (mục 6, tính trên tổng mục 1-5) và
        dòng tổng - không dựng lại cả bảng (dự toán vài trăm dòng: mỗi lần gõ một ô trước đây dựng lại hàng nghìn ô)."""
        self._dang_ve = True
        try:
            for i, d in enumerate(self.dt.dong):
                if i == r or (d.muc == 6 and d.phan_tram is not None):
                    self._ve_dong(i)
        finally:
            self._dang_ve = False
        self.bang.resizeRowToContents(r)
        self._ve_dau_tong()

    def _ve_dau_tong(self):
        for k, w in self.o_cb.items():
            v = getattr(self.dt, k) or ''
            if isinstance(w, QComboBox):
                i = w.findData(v)
                if i < 0 and v:                         # nguồn vốn lạ (file sửa tay): vẫn hiện, không mất khi lưu lại
                    w.addItem(v, v)
                    i = w.count() - 1
                if w.currentIndex() != max(i, 0):
                    w.setCurrentIndex(max(i, 0))
            elif ' '.join(w.text().split()) != v:
                w.setText(v)
        # 2 dòng (trang trong cửa sổ chính: dành chỗ cho bảng); nguồn khối lượng + cách tính ở chú thích khi rê chuột
        i = self.cb_kp.findData(self.dt.loai_kinh_phi or '')
        if self.cb_kp.currentIndex() != max(i, 0):
            self.cb_kp.setCurrentIndex(max(i, 0))
        self.lb_tong.setText(f'<span style="font-size: 15px; font-weight: bold;">TỔNG CỘNG KHÁI TOÁN: {vn(self.dt.tong)} đồng'
                             f'</span><br><i>Bằng chữ: {tien_bang_chu(self.dt.tong)}.</i>'
                             f'<br><span style="font-size: 11px; color: #047857;">{du_toan.mo_ta_tong(self.dt)}</span>')
        self.lb_tong.setToolTip((f'Nguồn khối lượng: {self.dt.nguon}\n\n' if self.dt.nguon else '') + self._cach_tinh)

    def _doi_o(self, r: int, c: int):
        if self._dang_ve or not 0 <= r < len(self.dt.dong):
            return
        d = self.dt.dong[r]
        k = COT[c][0]
        text = self.bang.item(r, c).text()
        try:
            if k == 'muc':
                m = int(doc_so(text, 'Mục', cho_phep_trong=False))
                if m not in du_toan.TEN_MUC:
                    raise LoiNhap('Mục: 1 đến 6.')
                d.muc = m
                if m == 6 and d.phan_tram is None:
                    d.phan_tram = KHONG
            elif k == 'khoi_luong':
                v = doc_so(text, 'Khối lượng')
                if d.muc == 6 and d.phan_tram is not None:
                    d.phan_tram = v
                else:
                    d.khoi_luong = v
            elif k == 'don_gia':
                d.don_gia = doc_so(text, 'Đơn giá')
            elif k == 'he_so':
                d.he_so = doc_so(text, 'Hệ số') or D(1)
            elif k == 'can_cu':
                d.can_cu, d.ghi_chu = text.strip(), ''
            elif k in ('ten', 'dvt', 'ma'):
                setattr(d, k, ' '.join(text.split()))
        except LoiNhap as e:
            self.bao(str(e))
        if k == 'muc':
            self.ve(r)                                  # đổi mục: thứ tự dòng đổi (sắp theo mục) - vẽ lại cả bảng
        else:
            self._ve_lai_dong(r)

    def _doc_dau(self):
        for k, w in self.o_cb.items():
            setattr(self.dt, k, (w.currentData() or '') if isinstance(w, QComboBox) else ' '.join(w.text().split()))

    # ---------------------------------------------- dự án đang mở (trang của cửa sổ chính)
    def dat_du_an(self, con, file_du_an=None):
        """Cửa sổ chính mở / đóng dự án: nút "Từ dự án đang mở", thẻ So sánh theo dự án mới; danh sách loại đất theo dự án."""
        self.con, self.file_du_an, self._dm = con, file_du_an, None
        if self.b_tu_du_an is not None:
            self.b_tu_du_an.setEnabled(con is not None)
        from .loai_dat import ds_chon
        self.cb_loai_dat.clear()
        for ma, nhan in ds_chon(con):
            self.cb_loai_dat.addItem(nhan, ma)
        self.cb_loai_dat.setCurrentIndex(-1)
        self.ss = None
        if con is None:
            self.bang_ss.setRowCount(0)
            self.lb_ss.setText('Mở một dự án để so sánh khái toán với thực tế áp giá của các hộ.')
        elif self.tab.currentIndex() == 1:
            self.so_sanh_thuc_te()
        self._nap_hang()                                # danh mục của dự án mới / bộ đơn giá khi đóng dự án

    # ---------------------------------------------- so sánh khái toán - thực tế áp giá
    def _the_so_sanh(self) -> QWidget:
        w = QWidget()
        lo = QVBoxLayout(w)
        h = QHBoxLayout()
        self.lb_goc = QLabel('')
        self.lb_goc.setWordWrap(True)
        h.addWidget(self.lb_goc, 1)
        for ten, ham in (('Mở khái toán đã duyệt (.pabtdt)…', lambda: self.mo_khai_toan_goc()),
                         ('Dùng bảng ở thẻ "Khái toán / dự toán"', lambda: self.mo_khai_toan_goc(dung_bang=True)),
                         ('Tính lại', lambda: self.so_sanh_thuc_te())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            h.addWidget(b)
        self.bang_ss = QTableWidget(0, len(COT_SS))
        self.bang_ss.setHorizontalHeaderLabels(COT_SS)
        for i, rong in enumerate((50, 420, 160, 160, 160, 90)):
            self.bang_ss.setColumnWidth(i, rong)
        self.bang_ss.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.bang_ss.verticalHeader().setVisible(False)
        self.bang_ss.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.lb_ss = QLabel('')
        self.lb_ss.setWordWrap(True)
        self.lb_ss.setStyleSheet('QLabel { font-size: 14px; padding: 8px 10px; border-radius: 6px; }')
        ghi = QLabel('Khái toán đã duyệt là ngân sách trần của dự án; thực tế = tổng các phương án đã áp giá trong dự án đang mở '
                     '(chi phí khác mục 6 tính theo các tỷ lệ của khái toán). Đỏ: thực tế vượt khái toán.')
        ghi.setWordWrap(True)
        lo.addLayout(h)
        lo.addWidget(self.bang_ss, 1)
        lo.addWidget(self.lb_ss)
        lo.addWidget(ghi)
        self._ghi_goc()
        return w

    def _ghi_goc(self):
        self.lb_goc.setText(f'<b>Khái toán:</b> file {self.dt_goc_file.name}' if self.dt_goc is not None else
                            '<b>Khái toán:</b> bảng đang lập ở thẻ "Khái toán / dự toán"')

    def mo_khai_toan_goc(self, file=None, dung_bang: bool = False):
        if dung_bang:
            self.dt_goc = None
        else:
            if file is None:
                file, _ = QFileDialog.getOpenFileName(self, 'Mở khái toán đã duyệt', self._thu_muc(),
                                                      f'Dự toán PABT (*{du_toan.DUOI})')
                if not file:
                    return None
            try:
                self.dt_goc = DuToan.mo(file)
            except (OSError, ValueError, TypeError) as e:
                self.bao(chu_loi('Không mở được file khái toán', e))
                return None
            self.dt_goc_file = Path(file)
        self._ghi_goc()
        return self.so_sanh_thuc_te() if self.con is not None else None

    def so_sanh_thuc_te(self):
        """Khái toán (file đã duyệt hoặc bảng thẻ 1) so với thực tế áp giá của dự án đang mở. Trả du_toan.so_sanh."""
        if self.con is None:
            self.bao('Mở một dự án để so sánh với thực tế áp giá.', loi=False)
            return None
        goc = self.dt_goc if self.dt_goc is not None else self.dt
        try:
            with con_tro_cho():
                self.ss = du_toan.so_sanh(goc, du_toan.tu_du_an(self.con))
        except Exception as e:                          # dự án lỗi dữ liệu: báo, không làm hỏng trang
            self.bao(chu_loi('Không tính được thực tế áp giá', e))
            return None
        dong = self.ss['dong'] + [('', 'TỔNG CỘNG', *self.ss['tong'])]
        self.bang_ss.setRowCount(len(dong))
        dam = QFont()
        dam.setBold(True)
        for r, (m, ten, kt, tt, chenh, tl) in enumerate(dong):
            o = [str(m), ten, vn(kt), vn(tt), ('+' if chenh > 0 else '') + vn(chenh),
                 '' if tl is None else f'{"+" if tl > 0 else ""}{so_vn(tl.quantize(D("0.1")))}%']
            for c, v in enumerate(o):
                it = QTableWidgetItem(v)
                if c != 1:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c in (4, 5) and (kt or tt):
                    it.setBackground(QBrush(DO_NHAT if chenh > 0 else XANH_LA))
                if r == len(dong) - 1:
                    it.setFont(dam)
                self.bang_ss.setItem(r, c, it)
        kt, tt, chenh, tl = self.ss['tong']
        if not kt:
            self.lb_ss.setStyleSheet('QLabel { font-size: 14px; padding: 8px 10px; border-radius: 6px; background: #EAF2FB; }')
            self.lb_ss.setText('Khái toán chưa có số liệu: lập bảng ở thẻ "Khái toán / dự toán" hoặc mở file khái toán đã duyệt.')
        elif self.ss['vuot']:
            self.lb_ss.setStyleSheet('QLabel { font-size: 14px; padding: 8px 10px; border-radius: 6px; background: #F8CBAD; '
                                     'color: #7A1B12; font-weight: bold; }')
            self.lb_ss.setText(f'⚠ Thực tế áp giá VƯỢT khái toán {vn(chenh)} đồng ({so_vn(tl.quantize(D("0.1")))}%): '
                               'rà soát phương án các hộ hoặc trình điều chỉnh tổng mức kinh phí.')
        else:
            self.lb_ss.setStyleSheet('QLabel { font-size: 14px; padding: 8px 10px; border-radius: 6px; background: #E2EFDA; '
                                     'color: #1E5E2F; font-weight: bold; }')
            self.lb_ss.setText(f'✓ Thực tế áp giá trong phạm vi khái toán: còn {vn(-chenh)} đồng '
                               f'({so_vn((-tl).quantize(D("0.1")))}% tổng mức).')
        return self.ss

    # ---------------------------------------------- lấy khối lượng
    def lay(self, nguon: str, file=None):
        if self.dt.dong and not self.im_lang and QMessageBox.question(
                self, TIEU_DE, 'Thay toàn bộ các dòng dự toán hiện có bằng khối lượng mới?') != QMessageBox.StandardButton.Yes:
            return None
        if nguon != 'du_an' and file is None:
            loc = {'pabt': 'Dự án PABT (*.pabt)', 'excel': 'File PABT Excel (*.xlsm *.xlsx)',
                   'tho': 'Danh sách Excel (*.xlsx *.xlsm)'}[nguon]
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn file', '', loc)
            if not file:
                return None
        try:
            with con_tro_cho():
                if nguon == 'du_an':
                    dt = du_toan.tu_du_an(self.con)
                elif nguon == 'pabt':
                    dt = du_toan.tu_file_pabt(file)
                elif nguon == 'excel':
                    dt = du_toan.tu_excel_pabt(file)
                else:
                    dt = du_toan.tu_ds_tho(file)
        except Exception as e:                      # file hỏng / không đúng mẫu
            self.bao(chu_loi('Không lấy được khối lượng', e))
            return None
        # thông tin chuẩn bị đầu tư đã gõ giữ nguyên (độc lập với file nguồn khối lượng); ô trống mới lấy theo nguồn
        self._doc_dau()
        for k in du_toan.TRUONG_CHUAN_BI:
            if getattr(self.dt, k):
                setattr(dt, k, getattr(self.dt, k))
        self.dt = dt
        self.file = None
        self.ve()
        return dt

    def ap_gia_hien_hanh(self):
        doi = du_toan.ap_don_gia_hien_hanh(self.dt, self.dm)
        self.ve()
        if doi:
            self.bao(f'Đã thay đơn giá {len(doi)} dòng theo bộ đơn giá hiện hành, ví dụ:\n' +
                     '\n'.join(f'- {t[:60]}: {vn(a)} -> {vn(b)}' for t, a, b in doi[:12]), loi=False)
        else:
            self.bao('Các dòng có mã đã đúng đơn giá hiện hành.', loi=False)
        return doi

    def them_chi_phi(self, loai=None):
        self.dt.them_chi_phi_mac_dinh(loai)
        self.ve()

    # ---------------------------------------------- dòng
    def them_danh_muc(self, m):
        """Thêm một mục danh mục (nhà / cây / vật nuôi / hỗ trợ) - cùng lệnh với hàng nhập nhanh (nhap_tai_san.DichDuToan)."""
        muc = m.nhom if m.nhom in (2, 3, du_toan.MUC_VN, 4) else 2
        i, _ = self._dich().them_danh_muc(muc, m)
        return self._sau_khi_them(self.dt.dong[i])

    def them_dong(self, muc: int | None = None):
        if muc is None:
            muc = 1
            r = self.bang.currentRow()
            if 0 <= r < len(self.dt.dong):
                muc = self.dt.dong[r].muc
        self.dt.dong.append(DongDT(muc, 'Hạng mục mới', 'm²' if muc == 1 else ''))
        self.ve()
        r = max(i for i, d in enumerate(self.dt.dong) if d.ten == 'Hạng mục mới')
        self.bang.setCurrentCell(r, 1)
        return r

    def them_dat(self, ma: str | None = None, dien_tich=None, don_gia=None, can_cu: str = ''):
        """Thêm một dòng đất (mục 1, nằm trên cùng bảng khái toán): loại đất, diện tích, đơn giá nhập tay."""
        from .loai_dat import ds_chon
        if ma is None:
            i = self.cb_loai_dat.currentIndex()
            chu = self.cb_loai_dat.currentText().strip()
            ma = self.cb_loai_dat.itemData(i) if i >= 0 and self.cb_loai_dat.itemText(i) == chu else chu.split('–')[0].strip()
        ma = (ma or '').upper()
        if not ma:
            self.bao('Chọn loại đất.', loi=False)
            return None
        try:
            dt = doc_so(self.o_dt_dat.text() if dien_tich is None else dien_tich, 'Diện tích', cho_phep_trong=False)
            gia = doc_so(self.o_gia_dat.text() if don_gia is None else don_gia, 'Đơn giá') or KHONG
        except LoiNhap as e:
            self.bao(str(e))
            return None
        ten = next((n.split('–', 1)[1].strip() for m, n in ds_chon(self.con) if m == ma), '')
        nhan = ten if ten.lower().startswith('đất') else (f'Đất {ten.lower()}' if ten else f'Đất {ma}')
        self.dt.dong.append(DongDT(1, f'{nhan} ({ma})', 'm²', dt, gia, D(1), ma,
                                   can_cu or getattr(self, '_can_cu_gia_dat', '')))
        self._can_cu_gia_dat = ''
        self.o_dt_dat.clear()
        self.o_gia_dat.clear()
        self.ve()
        r = max(i for i, d in enumerate(self.dt.dong) if d.muc == 1 and d.ma == ma)
        self.bang.setCurrentCell(r, 3)
        return r

    def _tra_gia_o_dat(self):
        """Tra giá NQ 28 cho ô đơn giá của hàng "Thêm đất"."""
        dlg = HopTraNQ28(self, self.o_dia_ban.text(), self.cb_loai_dat.currentData() or self.cb_loai_dat.currentText())
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.chon is not None:
            self.o_gia_dat.setText(vn(dlg.chon[0]))
            self._can_cu_gia_dat = dlg.chon[1]

    def tra_gia_dat(self, chon=None):
        r = self.bang.currentRow()
        if not 0 <= r < len(self.dt.dong):
            self.bao('Chọn dòng đất (mục 1) cần tra giá.', loi=False)
            return None
        d = self.dt.dong[r]
        if chon is None:
            dlg = HopTraNQ28(self, self.o_dia_ban.text(), d.ma or d.ten)
            if dlg.exec() != QDialog.DialogCode.Accepted or dlg.chon is None:
                return None
            chon = dlg.chon
        d.don_gia, d.can_cu = chon
        self.ve(r)
        return chon

    def xoa_dong(self):
        r = self.bang.currentRow()
        if 0 <= r < len(self.dt.dong):
            del self.dt.dong[r]
            self.ve(min(r, len(self.dt.dong) - 1))

    # ---------------------------------------------- lưu / mở / xuất
    def _thu_muc(self) -> str:
        return str(Path(self.file_du_an).parent) if self.file_du_an else ''

    def luu(self, file=None):
        self._doc_dau()
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu dự toán', str(self.file or Path(self._thu_muc()) /
                                                                         f'{self.dt.ten or "DuToan"}{du_toan.DUOI}'),
                                                  f'Dự toán PABT (*{du_toan.DUOI})')
            if not file:
                return None
        self.file = self.dt.luu(file)
        return self.file

    def mo(self, file=None):
        if file is None:
            file, _ = QFileDialog.getOpenFileName(self, 'Mở dự toán', self._thu_muc(), f'Dự toán PABT (*{du_toan.DUOI})')
            if not file:
                return None
        try:
            self.dt = DuToan.mo(file)
        except (OSError, ValueError, TypeError) as e:
            self.bao(chu_loi('Không mở được file dự toán', e))
            return None
        self.file = Path(file)
        self.ve()
        return self.dt

    def xuat_khai_toan(self, file=None, pdf: bool = False):
        """Bảng khái toán theo mẫu của đơn vị (Excel, kèm PDF nếu chọn - cần Microsoft Excel)."""
        self._doc_dau()
        if not self.dt.dong:
            self.bao('Chưa có dòng dự toán: lấy khối lượng hoặc thêm dòng trước.', loi=False)
            return None
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Xuất Bảng khái toán', str(Path(self._thu_muc()) /
                                                                                f'KhaiToan_{self.dt.ten or "PABT"}.xlsx'),
                                                  'File Excel (*.xlsx)')
            if not file:
                return None
        try:
            with con_tro_cho():
                kq = du_toan.xuat_khai_toan(self.dt, file, pdf=pdf)
        except Exception as e:                      # file đang mở trong Excel, không có Excel để xuất PDF...
            self.bao(chu_loi('Không xuất được Bảng khái toán', e))
            return None
        mo = kq['pdf'] or kq['excel']
        if kq['loi']:
            self.bao('Đã lưu Excel nhưng không xuất được PDF:\n' + '\n'.join(kq['loi'][:5]))
        elif not self.im_lang and QMessageBox.question(self, TIEU_DE, f'Đã xuất:\n{mo}\n\nMở file?') == \
                QMessageBox.StandardButton.Yes:
            from .in_an import mo_file
            mo_file(mo)
        return kq

    def xuat(self, file=None):
        self._doc_dau()
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Xuất dự toán ra Excel', str(Path(self._thu_muc()) /
                                                                                   f'DuToan_{self.dt.ten or "PABT"}.xlsx'),
                                                  'File Excel (*.xlsx)')
            if not file:
                return None
        try:
            p = du_toan.xuat_excel(self.dt, file)
        except OSError as e:
            self.bao(chu_loi('Không ghi được file', e))
            return None
        if not self.im_lang and QMessageBox.question(self, TIEU_DE, f'Đã xuất:\n{p}\n\nMở file?') == QMessageBox.StandardButton.Yes:
            from .in_an import mo_file
            mo_file(p)
        return p


class HopDuToan(QDialog):
    """Dự toán trong hộp thoại riêng (giữ cho mã cũ / kiểm thử). Cửa sổ chính dùng KhungDuToan làm một trang (0.9.23).
    Thuộc tính / hàm không có ở hộp thoại chuyển sang khung (dlg.dt, dlg.lay(), dlg.bang...)."""

    def __init__(self, parent=None, con=None, file_du_an=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setWindowTitle('Dự toán & khái toán kinh phí bồi thường, hỗ trợ')
        self.resize(1360, 760)
        self.khung = KhungDuToan(self, con, file_du_an)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        lo.addWidget(self.khung, 1)
        lo.addWidget(nut)

    @property
    def im_lang(self):
        return self.khung.im_lang

    @im_lang.setter
    def im_lang(self, v):
        self.khung.im_lang = v

    def __getattr__(self, ten):
        khung = self.__dict__.get('khung')
        if khung is None:
            raise AttributeError(ten)
        return getattr(khung, ten)

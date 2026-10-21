"""Màn hình Dự thảo PABT: phễu tiến độ, 5 việc (niêm yết, ý kiến, đối thoại, tổng hợp, hộ vướng)."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMenu, QMessageBox, QProgressBar, QPushButton, QTabWidget,
                               QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)

from . import du_thao
from .thong_bao import TEN_UD, chu_loi
from .tien import vn


def _o(chu, mau=None) -> QTableWidgetItem:
    it = QTableWidgetItem('' if chu is None else str(chu))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return it


CAN_GIUA = Qt.AlignmentFlag.AlignCenter
RONG_TOI_THIEU_COT = 60      # cột không hẹp hơn (kéo tay cũng vậy)


def _bang(cot: list, rong: list | None = None, gian: int | None = None) -> QTableWidget:
    """Bảng một thẻ. rong: bề rộng chuẩn từng cột (px); gian: cột giãn lấp chỗ trống (các cột khác Interactive, kéo được).
    15/10/2026 (người dùng): trước đây chỉ cột cuối giãn, các cột khác theo mặc định Qt -> "Tổng tiền dự thảo" bị cắt chữ tiêu
    đề, "Nhóm vướng" cắt "Chưa đánh dấu…"."""
    b = QTableWidget(0, len(cot))
    b.setHorizontalHeaderLabels(cot)
    b.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    b.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    b.verticalHeader().setVisible(False)
    b.setAlternatingRowColors(True)
    hd = b.horizontalHeader()
    hd.setMinimumSectionSize(RONG_TOI_THIEU_COT)
    hd.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    if gian is None:
        hd.setStretchLastSection(True)
    else:
        hd.setStretchLastSection(False)
        hd.setSectionResizeMode(gian, QHeaderView.ResizeMode.Stretch)
    for c, w in enumerate(rong or ()):
        if w and c != gian:
            b.setColumnWidth(c, w)
    b.setProperty('rong_chuan', list(rong or ()))
    san_tieu_de(b)
    return b


def san_tieu_de(b) -> None:
    """Sàn tiêu đề (giao_dien.san_tieu_de, đo phông đậm); cột 0 "Nhóm lý do kiến nghị" thẻ 4 >= 185 px."""
    from .giao_dien import san_tieu_de as san
    san(b, {0: 185} if b.property('the_tong_hop') else None)


MAU_Y_KIEN = {'dong_y': '#15803D', 'khong_dong_y': '#B91C1C', 'y_kien_khac': '#B45309', 'chua': '#64748B'}
# thẻ KPI trang Niêm yết (1.0.02, như thẻ số màn hình chính): màu vạch trái + màu số. Navy = tổng; xanh trời / xanh dương = đủ điều kiện /
# đã niêm yết; teal / xanh lá = phê duyệt / bàn giao (đã đồng thuận); hổ phách = vướng (cần xử lý)
MAU_THE_NY = {'tong': '#0F294A', 'du': '#0284C7', 'vuong': '#B45309', 'dt': '#2563EB', 'pd': '#0F766E', 'bg': '#15803D'}
# 1.0.03: góc trái bo 3 px (bằng bề dày vạch) - vạch màu bên trái thẳng đứng, không cong thành dấu "(" như bo 6 px (Ảnh 7)
QSS_THE_NY = ('QFrame[vai="the_ny"] {{ background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 3px solid {m}; '
              'border-radius: 6px; border-top-left-radius: 3px; border-bottom-left-radius: 3px; }}'
              'QFrame[vai="the_ny"]:hover {{ background: #F8FAFC; border-color: {m}; }}'
              'QLabel#the_ny_tieu {{ color: #475569; font-size: 12px; font-weight: 600; border: 0; background: transparent; }}'
              'QLabel#the_ny_so {{ color: {m}; font-size: 16px; font-weight: 700; border: 0; background: transparent; }}'
              'QLabel#the_ny_phu {{ color: #64748B; font-size: 12px; border: 0; background: transparent; }}')
CAO_THE_NY = 54
RONG_O_DOT = 300            # ô chọn đợt (chữ dài đủ ở chú thích)


def _pt(x) -> str:
    """Phần trăm kiểu VN, 1 chữ số lẻ: 12.5 -> "12,5" (dấu phẩy thập phân)."""
    return f'{float(x):.1f}'.replace('.', ',')


class _The(QFrame):
    def __init__(self, tieu_de, mau, bam):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty('vai', 'the_ny')
        self.mau = mau
        self.setStyleSheet(QSS_THE_NY.format(m=mau))    # bộ chọn theo vai: không truyền sang nhãn con (QLabel cũng là QFrame)
        self._bam = bam
        # 1.0.03: thẻ KPI 2 tầng cao 54 px như thẻ số màn hình chính - tên trên; số lớn + chữ phụ dưới (đủ chữ ở chú thích)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(10, 6, 10, 6)
        lo.setSpacing(2)
        self.setFixedHeight(CAO_THE_NY)
        from .giao_dien import NhanRutGon
        self.tieu = NhanRutGon(tieu_de)                 # hẹp thì rút "…" (đủ ở chú thích), không đẩy cửa sổ rộng ra
        self.tieu.setObjectName('the_ny_tieu')
        self.gia = QLabel('0')
        self.gia.setObjectName('the_ny_so')
        self.phu = NhanRutGon('')
        self.phu.setObjectName('the_ny_phu')
        lo.addWidget(self.tieu)
        duoi = QHBoxLayout()
        duoi.setSpacing(6)
        duoi.addWidget(self.gia)
        duoi.addWidget(self.phu, 1, Qt.AlignmentFlag.AlignBottom)
        lo.addLayout(duoi)

    def dat(self, gia, phu):
        self.gia.setText(gia)
        self.phu.setText(phu)
        self.setToolTip(f'{self.tieu.text()}: {gia}' + (f' - {phu}' if phu else ''))

    def mousePressEvent(self, e):
        self._bam()
        super().mousePressEvent(e)


class HopTaoDot(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Tạo đợt dự thảo')
        self.ten = QLineEdit()
        self.ten.setPlaceholderText('Đợt 1 — tuyến ưu tiên')
        self.ngay = QLineEdit()
        self.ngay.setPlaceholderText('11/10/2026')
        self.dia = QLineEdit()
        self.dia.setPlaceholderText('Trụ sở UBND xã, nhà văn hóa ấp')
        f = QFormLayout(self)
        f.addRow('Tên đợt:', self.ten)
        f.addRow('Ngày bắt đầu niêm yết:', self.ngay)
        f.addRow('Địa điểm niêm yết:', self.dia)
        b = QPushButton('Tạo đợt')
        b.clicked.connect(self.accept)
        f.addRow(b)


class HopYKien(QDialog):
    def __init__(self, parent, ho):
        super().__init__(parent)
        self.setWindowTitle(f'Ý kiến — {ho["ho_ten"]}')
        self.resize(560, 420)
        self.loai = QComboBox()
        for k, t in du_thao.LOAI_Y_KIEN:
            self.loai.addItem(t, k)
        i = self.loai.findData(ho['loai'])
        if i >= 0:
            self.loai.setCurrentIndex(i)
        self.nhom = QComboBox()
        for k, t in du_thao.NHOM_KIEN_NGHI:
            self.nhom.addItem(t or '(không)', k)
        i = self.nhom.findData(ho['nhom'] or '')
        if i >= 0:
            self.nhom.setCurrentIndex(i)
        self.nd = QTextEdit(ho['noi_dung'] or '')
        self.kq = QTextEdit(ho['ket_qua_doi_thoai'] or '')
        self.tien = QLineEdit(str(ho['so_tien_chenh'] or '0'))
        self.ngay_dt = QLineEdit()
        self.ngay_dt.setPlaceholderText('Ngày đối thoại, nếu có')
        f = QVBoxLayout(self)
        h = QHBoxLayout()
        h.addWidget(QLabel('Ý kiến:'))
        h.addWidget(self.loai, 1)
        h.addWidget(QLabel('Nhóm:'))
        h.addWidget(self.nhom, 1)
        f.addLayout(h)
        f.addWidget(QLabel('Nội dung ý kiến của người có đất:'))
        f.addWidget(self.nd, 1)
        f.addWidget(QLabel('Kết quả tiếp thu, giải trình, đối thoại:'))
        f.addWidget(self.kq, 1)
        h2 = QHBoxLayout()
        h2.addWidget(QLabel('Chênh lệch tiền (đồng):'))
        h2.addWidget(self.tien)
        h2.addWidget(self.ngay_dt)
        f.addLayout(h2)
        b = QPushButton('Lưu')
        b.clicked.connect(self.accept)
        f.addWidget(b)


class HopNoiDung(QDialog):
    """Nhập nhanh nội dung phản ánh, kiến nghị của người có đất (bấm đúp ô Nội dung ở thẻ Lấy ý kiến)."""

    def __init__(self, parent, ho):
        super().__init__(parent)
        self.setWindowTitle(f'Nội dung phản ánh — {ho["ho_ten"]}')
        self.resize(560, 300)
        self.nd = QTextEdit(ho['noi_dung'] or '')
        self.nd.setPlaceholderText('Nội dung phản ánh, kiến nghị của người có đất (ghi theo lời người phản ánh)')
        lo = QVBoxLayout(self)
        lo.addWidget(QLabel(f'Hộ {ho["ma_ho"]} - {ho["ho_ten"]} · ý kiến: {du_thao.TEN_LOAI.get(ho["loai"], "")}'))
        lo.addWidget(self.nd, 1)
        h = QHBoxLayout()
        h.addStretch(1)
        b_huy = QPushButton('Hủy')
        b_huy.clicked.connect(self.reject)
        b = QPushButton('Lưu')
        b.setDefault(True)
        b.clicked.connect(self.accept)
        h.addWidget(b_huy)
        h.addWidget(b)
        lo.addLayout(h)


class HopPhapLy(QDialog):
    def __init__(self, parent, ho):
        super().__init__(parent)
        self.setWindowTitle(f'Pháp lý — {ho["ho_ten"]}')
        self.du = QComboBox()
        self.du.addItem('Chưa đủ điều kiện lập dự thảo', 0)
        self.du.addItem('Đủ điều kiện đưa vào đợt lấy ý kiến', 1)
        self.du.setCurrentIndex(1 if ho['du_dieu_kien'] else 0)
        self.vuong = QComboBox()
        self.vuong.addItem('(không vướng)', '')
        for k, t in du_thao.NHOM_VUONG:
            self.vuong.addItem(f'{k} — {t}', k)
        i = self.vuong.findData(ho['ma_vuong'] or '')
        if i >= 0:
            self.vuong.setCurrentIndex(i)
        self.gc = QLineEdit(ho['ghi_chu_phap_ly'] or '')
        f = QFormLayout(self)
        f.addRow('Điều kiện:', self.du)
        f.addRow('Nhóm vướng:', self.vuong)
        f.addRow('Ghi chú:', self.gc)
        b = QPushButton('Lưu')
        b.clicked.connect(self.accept)
        f.addRow(b)


class HopThemHo(QDialog):
    """Chọn hộ đưa vào đợt đang mở: theo đợt niêm yết, hoặc theo tình trạng ý kiến."""

    def __init__(self, parent, con, dot_id: int):
        super().__init__(parent)
        self.con, self.dot_id = con, dot_id
        self.setWindowTitle('Thêm hộ vào đợt')
        self.resize(720, 480)
        self.cb = QComboBox()
        self.cb.addItem('Hộ đủ điều kiện, chưa có trong đợt này', ('du', None))
        for d in du_thao.ds_dot(con):
            if d['id'] == dot_id:
                continue
            self.cb.addItem(f'Hộ đang niêm yết: {d["ten"]}', ('dot', d['id']))
        self.cb.addItem('Hộ chưa lấy ý kiến', ('chua', None))
        self.cb.addItem('Hộ chưa đồng thuận', ('khong_dong_y', None))
        self.cb.addItem('Hộ có ý kiến khác', ('y_kien_khac', None))
        self.bang = _bang(['', 'Mã hộ', 'Họ và tên', 'Thửa', 'Nguồn'])
        self.bang.setColumnWidth(0, 36)
        self.cb.currentIndexChanged.connect(self._nap)
        lo = QVBoxLayout(self)
        lo.addWidget(QLabel('Chọn nhóm hộ, đánh dấu những hộ cần thêm vào đợt đang mở '
                            '(niêm yết, lấy ý kiến và đối thoại dùng chung danh sách này).'))
        lo.addWidget(self.cb)
        hang = QHBoxLayout()
        b1 = QPushButton('Chọn tất cả')
        b2 = QPushButton('Bỏ chọn')
        b1.clicked.connect(lambda: self._chon(True))
        b2.clicked.connect(lambda: self._chon(False))
        hang.addWidget(b1)
        hang.addWidget(b2)
        hang.addStretch(1)
        lo.addLayout(hang)
        lo.addWidget(self.bang, 1)
        b = QPushButton('Thêm vào đợt')
        b.clicked.connect(self.accept)
        lo.addWidget(b)
        self._nap()

    def _nap(self):
        loc, nguon = self.cb.currentData()
        self.ds = du_thao.ds_de_them(self.con, self.dot_id, loc, nguon)
        self.bang.setRowCount(len(self.ds))
        for i, h in enumerate(self.ds):
            o = QTableWidgetItem('')
            o.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            o.setCheckState(Qt.CheckState.Unchecked if h['vuong'] else Qt.CheckState.Checked)
            self.bang.setItem(i, 0, o)
            for c, v in enumerate((h['ma_ho'], h['ho_ten'], h['thua'], h['nhan']), 1):
                self.bang.setItem(i, c, _o(v))

    def _chon(self, bat: bool):
        st = Qt.CheckState.Checked if bat else Qt.CheckState.Unchecked
        for i in range(self.bang.rowCount()):
            self.bang.item(i, 0).setCheckState(st)

    def ma_chon(self) -> list:
        kq = []
        for i, h in enumerate(self.ds):
            it = self.bang.item(i, 0)
            if it is not None and it.checkState() == Qt.CheckState.Checked:
                kq.append(h['ma_ho'])
        return kq


class KhungDuThao(QWidget):
    def __init__(self, con, parent=None, chi_doc: bool = False):
        super().__init__(parent)
        self.con, self.chi_doc = con, chi_doc
        self.thay_doi_csdl = False
        self._dung = False
        lo = QVBoxLayout(self)
        lo.setContentsMargins(8, 8, 8, 8)
        lo.setSpacing(6)
        hud = QHBoxLayout()
        hud.setSpacing(6)                               # 6 thẻ KPI cách nhau 6 px
        hud.setProperty('giu_khoang_cach', True)        # giao_dien.gian_cach không nâng lên 10 px
        self.the = {
            'tong': _The('Tổng số hộ', MAU_THE_NY['tong'], lambda: None),
            'du': _The('Đủ điều kiện lập PA', MAU_THE_NY['du'], lambda: self.tabs.setCurrentIndex(0)),
            'vuong': _The('Vướng pháp lý', MAU_THE_NY['vuong'], lambda: self.tabs.setCurrentIndex(0)),
            'dt': _The('Đã dự thảo (niêm yết)', MAU_THE_NY['dt'], lambda: self.tabs.setCurrentIndex(0)),
            'pd': _The('Đã phê duyệt QĐ', MAU_THE_NY['pd'], self._mo_tien_do),
            'bg': _The('Đã bàn giao mặt bằng', MAU_THE_NY['bg'], self._mo_tien_do),
        }
        for t in self.the.values():
            hud.addWidget(t, 1)
        lo.addLayout(hud)
        # 1.0.03 (Ảnh 7): ô đợt + 7 nút xếp nối tiếp, hẹp thì xuống dòng - trước đây một hàng cứng (ô đợt tối thiểu 360 px) ép nút
        # nhỏ hơn chữ ("Gợi ý đủ điều kiệ", "uất bảng niêm yế")
        from .giao_dien import XepDong
        hang = XepDong(cach=6)
        khoi_dot = QWidget()
        h_dot = QHBoxLayout(khoi_dot)
        h_dot.setContentsMargins(0, 0, 0, 0)
        h_dot.setSpacing(6)
        h_dot.addWidget(QLabel('Đợt:'))
        self.cb = QComboBox()
        self.cb.setMinimumWidth(RONG_O_DOT)
        self.cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cb.currentIndexChanged.connect(self._doi_dot)
        self.cb.currentIndexChanged.connect(lambda *_: self.cb.setToolTip(self.cb.currentText()))
        h_dot.addWidget(self.cb, 1)
        hang.addWidget(khoi_dot)
        self.b_tao = QPushButton('Tạo đợt')
        self.b_xoa_dot = QPushButton('Xóa đợt')
        self.b_xoa_dot.setToolTip('Xóa đợt đang chọn: các hộ trở về danh sách chờ, phương án và hồ sơ hộ giữ nguyên. Mờ khi chọn "Lũy kế".')
        self.b_xoa_dot.clicked.connect(lambda: self._xoa_dot())
        self.b_in_du_thao = QPushButton('In PA Dự thảo gửi dân')
        self.b_in_du_thao.setToolTip('Mở Xuất hồ sơ & Bản in ở chế độ Dự thảo cho các hộ của đợt: mẫu có chữ DỰ THẢO, in đủ số CCCD')
        self.b_in_du_thao.clicked.connect(lambda: self._in_du_thao())
        # 0.9.75: hai nút "Đưa hộ đủ điều kiện vào đợt" / "Thêm hộ vào đợt…" gộp một nút xổ
        self.b_dua = QPushButton('Đưa hộ vào đợt')
        self.b_dua.setToolTip('Đưa hộ vào đợt đang chọn: tất cả hộ đủ điều kiện, hoặc chọn từng hộ (hộ của đợt khác, chưa lấy ý '
                              'kiến, chưa đồng thuận, ý kiến khác)')
        m = QMenu(self.b_dua)
        m.addAction('Thêm toàn bộ hộ đủ điều kiện', self._dua)
        m.addAction('Chọn hộ từ danh sách…', self._them_ho)
        self.b_dua.setMenu(m)
        self.b_goi = QPushButton('Gợi ý đủ điều kiện')
        self.b_hop = QPushButton('Ngày họp dân')
        self.b_hop.setToolTip('Ngày họp lấy ý kiến người dân: tự tính hạn đối thoại')
        for b, ham in ((self.b_tao, self._tao), (self.b_goi, self._goi_y), (self.b_hop, self._ngay_hop)):
            b.clicked.connect(ham)
        # "Xuất bảng niêm yết" cùng hàng nút đợt, không chiếm một hàng riêng trên bảng (15/10/2026)
        self._nut = {}
        self.b_xuat_ny = QPushButton('Xuất bảng niêm yết')
        self.b_xuat_ny.setToolTip('Xuất Excel bảng niêm yết công khai của đợt đang chọn')
        self.b_xuat_ny.clicked.connect(lambda: self._xuat_ny())
        self._nut['Xuất bảng niêm yết'] = self.b_xuat_ny
        for b in (self.b_tao, self.b_xoa_dot, self.b_dua, self.b_goi, self.b_hop, self.b_in_du_thao, self.b_xuat_ny):
            hang.addWidget(b)
        lo.addLayout(hang)
        # dải tiến độ một dòng cân đối (0.9.75): tiến độ đợt | lũy kế | bao phủ; chữ dài rút gọn "…", đủ ở chú thích
        from .giao_dien import NhanRutGon
        self.lb_dot, self.lb_luy, self.lb_phu = NhanRutGon(''), NhanRutGon(''), NhanRutGon('')
        dai = QFrame()
        dai.setObjectName('dai_tien_do_ny')
        dai.setStyleSheet('QFrame#dai_tien_do_ny { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 5px; }'
                          'QFrame#dai_tien_do_ny QLabel { color: #334155; background: transparent; border: 0; }')
        so = QHBoxLayout(dai)
        so.setContentsMargins(10, 3, 10, 3)
        so.setSpacing(14)
        so.addWidget(self.lb_dot, 5)
        so.addWidget(self.lb_luy, 3)
        so.addWidget(self.lb_phu, 3)
        lo.addWidget(dai)
        self.thanh = QProgressBar()
        self.thanh.setFixedHeight(8)
        self.thanh.setTextVisible(False)
        self.thanh.setStyleSheet('QProgressBar { background: #E2E8F0; border: none; border-radius: 4px; }'
                                 'QProgressBar::chunk { background: #0F294A; border-radius: 4px; }')
        lo.addWidget(self.thanh)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        # 4 thẻ gọn (15/10/2026, người dùng): cao 28-30 px, chữ 12 px - nhường chiều cao cho bảng
        # phông ở mức QTabBar (Qt5 đo bề rộng thẻ theo phông thanh thẻ - xem giao_dien.THE_TAB)
        self.tabs.setStyleSheet('QTabBar { font-size: 12px; } QTabBar::tab { min-height: 16px; padding: 4px 12px; margin-top: 0px; }')
        # CCCD hiển thị đủ số (1.0.04 bỏ che) - tiêu đề chỉ "CCCD"; bề rộng chuẩn từng cột + một cột giãn
        self.bang_ny = _bang(['STT', 'Họ và tên', 'CCCD', 'Thửa', 'Tổng tiền dự thảo', 'Địa điểm'],
                             [50, 170, 115, 85, 155], gian=5)
        self.bang_yk = _bang(['Mã hộ', 'Họ và tên', 'Ý kiến', 'Nhóm kiến nghị', 'Nội dung', 'Chênh lệch'],
                             [70, 160, 145, 150, 0, 120], gian=4)
        self.bang_dt = _bang(['Mã hộ', 'Họ và tên', 'Lý do chưa đồng ý', 'Lần đối thoại', 'Kết luận', 'Chuyển đợt'],
                             [70, 160, 180, 95, 0, 110], gian=4)
        self.bang_th = _bang(['Nhóm lý do kiến nghị', 'Số hộ kiến nghị', 'Đã đồng thuận', 'Chưa đồng thuận', 'Tỷ lệ đồng thuận',
                              'Nội dung tiêu biểu'], [200, 80, 90, 90, 90], gian=5)
        self.bang_th.setProperty('the_tong_hop', True)
        self.bang_vm = _bang(['Mã hộ', 'Chủ hộ', 'Thửa', 'Nhóm vướng', 'Ghi chú pháp lý'], [70, 160, 85, 185], gian=4)
        # 1.0.03: Ý kiến / Nhóm vướng vẽ viên thuốc màu, Tỷ lệ đồng thuận có thanh tỷ trọng; bảng trống có lời hướng dẫn
        from .giao_dien import gan_chu_khi_trong, gan_thanh_ty_le, gan_vien_thuoc
        gan_vien_thuoc(self.bang_yk, 2)
        gan_vien_thuoc(self.bang_vm, 3)
        gan_thanh_ty_le(self.bang_th, 4, mau='#0F766E')
        gan_chu_khi_trong(self.bang_ny, 'Chưa có hộ trong đợt niêm yết',
                          'Tạo đợt rồi bấm "Đưa hộ vào đợt" để thêm các hộ đủ điều kiện.')
        gan_chu_khi_trong(self.bang_vm, 'Không có hộ vướng pháp lý', 'Hộ đánh dấu V1-V5 (chưa đủ điều kiện) hiện ở đây.')
        gan_chu_khi_trong(self.bang_yk, 'Chưa có hộ để lấy ý kiến', 'Chọn đợt niêm yết đã có hộ.')
        gan_chu_khi_trong(self.bang_th, 'Chưa có kiến nghị nào được tổng hợp')
        # 0.9.70 (đặc tả ARCH-PABT-2026-V7 phần V): 4 thẻ con, tên không ghi cứng số ngày. Thẻ 1 gồm hộ đang niêm yết và (khung
        # dưới) hộ vướng / chưa đủ điều kiện - trước là thẻ 5 riêng: người niêm yết cần thấy ngay hộ nào chưa đưa vào được
        from PySide6.QtWidgets import QSplitter
        goc = QWidget()                                 # góc phải thanh 4 thẻ: nút của thẻ đang mở
        self._h_goc = QHBoxLayout(goc)
        self._h_goc.setContentsMargins(0, 0, 4, 2)
        self._h_goc.setSpacing(6)
        self._nut_goc = []
        self.tabs.setCornerWidget(goc, Qt.Corner.TopRightCorner)
        tach = self.tach = QSplitter(Qt.Orientation.Vertical)
        tach.setChildrenCollapsible(False)
        tach.setHandleWidth(10)
        tach.setStyleSheet('QSplitter::handle:vertical { background: #CBD5E1; margin: 3px 38%; border-radius: 2px; }'
                           'QSplitter::handle:vertical:hover { background: #94A3B8; }')
        tach.addWidget(self._trang(self.bang_ny, []))   # nút "Xuất bảng niêm yết": hàng nút đợt phía trên (15/10/2026)
        tach.addWidget(self._trang(self.bang_vm, [
            ('Đánh dấu pháp lý hộ đang chọn', self._phap_ly),
            ('Xuất danh sách đôn đốc V1, V2', self._xuat_dd)],
            'Hộ vướng / chưa đủ điều kiện niêm yết (kéo thanh ngăn phía trên để đổi chiều cao hai bảng)'))
        tach.setStretchFactor(0, 3)
        tach.setStretchFactor(1, 2)
        tach.handle(1).setToolTip('Kéo lên / xuống để đổi chiều cao bảng Hộ niêm yết và bảng Hộ vướng')
        self.tabs.addTab(tach, '1. Niêm yết công khai')
        self.tabs.addTab(self._trang(self.bang_yk, []), '2. Lấy ý kiến nhân dân')
        self.tabs.addTab(self._trang(self.bang_dt, [
            ('Chuyển hộ sang đợt sau', self._chuyen), ('Xuất biên bản đối thoại', self._xuat_dt)]), '3. Đối thoại && Tiếp thu')
        self.tabs.addTab(self._trang(self.bang_th, [
            ('Xuất báo cáo tổng hợp ý kiến', self._xuat_yk)]), '4. Tổng hợp kết quả ý kiến')
        self.tabs.currentChanged.connect(lambda *_: self._hien_nut_goc())
        self._hien_nut_goc()
        # thẻ 2: một chạm đổi ý kiến (bấm ô Ý kiến hoặc phím Space), bấm đúp ô Nội dung nhập phản ánh
        self.bang_yk.setToolTip('Bấm ô "Ý kiến" (hoặc phím Space) để đổi: Chưa lấy ý kiến → Đồng ý → Không đồng ý → Ý kiến khác. '
                                'Bấm đúp ô "Nội dung" để nhập phản ánh của người dân.')
        self.bang_yk.cellClicked.connect(self._bam_y_kien)
        self.bang_yk.cellDoubleClicked.connect(self._kep_y_kien)
        ph = QShortcut(QKeySequence(Qt.Key.Key_Space), self.bang_yk)
        ph.setContext(Qt.ShortcutContext.WidgetShortcut)
        ph.activated.connect(self._phim_y_kien)
        self._phim_yk = ph
        self.bang_dt.cellDoubleClicked.connect(lambda r, c: self._sua_yk(self.bang_dt, r))
        self.bang_vm.cellDoubleClicked.connect(lambda r, c: self._phap_ly())
        lo.addWidget(self.tabs, 1)
        self.lb_chu = QLabel(f'Hộ chỉ vào đợt khi đã đủ điều kiện và không vướng. Niêm yết {du_thao.SO_NGAY_NIEM_YET} ngày, '
                             f'đối thoại không quá {du_thao.SO_NGAY_DOI_THOAI} ngày (Luật Đất đai 2024, Nghị định 88/2024/NĐ-CP, '
                             'QĐ 18/2026). Ba tỷ lệ bên trên không thay thế nhau.')
        self.lb_chu.setWordWrap(True)
        self.lb_chu.setProperty('vai', 'phu')
        lo.addWidget(self.lb_chu)
        for b in (self.b_tao, self.b_dua, self.b_goi, self.b_hop):
            b.setEnabled(not chi_doc)
        self.nap()

    def _hien_nut_goc(self):
        hien = self.tabs.currentWidget()
        for trang, b in self._nut_goc:
            b.setVisible(trang is hien)

    def showEvent(self, e):
        super().showEvent(e)
        for b in (self.bang_ny, self.bang_yk, self.bang_dt, self.bang_th, self.bang_vm):   # cỡ chữ cuối (phóng to) đã áp
            san_tieu_de(b)

    def _trang(self, bang, nut, tieu_de: str = ''):
        w = QWidget()
        lo = QVBoxLayout(w)
        lo.setContentsMargins(0, 4 if tieu_de else 2, 0, 0)
        if not tieu_de:
            # 0.9.95: nút của thẻ (Xuất biên bản đối thoại, Xuất báo cáo tổng hợp ý kiến, Chuyển hộ sang đợt sau) nằm ở góc phải
            # thanh 4 thẻ, chỉ hiện khi thẻ đó đang mở - bảng sát thanh thẻ, không còn hàng nút riêng
            for ten, ham in nut:
                b = QPushButton(ten)
                b.clicked.connect(ham)
                b.setFixedHeight(26)
                self._nut[ten] = b
                if not ten.startswith('Xuất'):
                    b.setEnabled(not self.chi_doc)
                self._nut_goc.append((w, b))
                self._h_goc.addWidget(b)
            lo.addWidget(bang, 1)
            return w
        h = QHBoxLayout()
        if tieu_de:                                     # khung con có tên (thẻ Niêm yết: phần hộ vướng)
            nhan = QLabel(tieu_de)
            nhan.setProperty('vai', 'nhan')
            h.addWidget(nhan)
        h.addStretch(1)
        for ten, ham in nut:
            b = QPushButton(ten)
            b.clicked.connect(ham)
            self._nut[ten] = b
            if ten.startswith('Xuất'):
                pass
            else:
                b.setEnabled(not self.chi_doc)
            h.addWidget(b)
        lo.addLayout(h)
        lo.addWidget(bang, 1)
        return w

    def _mo_tien_do(self):
        cha = self.window()
        if hasattr(cha, 'mo_trang'):
            from .app import TRANG_THEO_DOI
            cha.mo_trang(TRANG_THEO_DOI)

    def _dot_id(self):
        return self.cb.currentData()

    def nap(self):
        self._dung = True
        cu = self._dot_id()
        self.cb.clear()
        self.cb.addItem('Lũy kế toàn bộ các đợt', None)
        for d in du_thao.ds_dot(self.con):
            self.cb.addItem(
                f'{d["ten"]} ({du_thao.hien_ngay(d["ngay_bat_dau"])} – {du_thao.hien_ngay(d["ngay_ket_thuc"])})', d['id'])
        i = self.cb.findData(cu)
        self.cb.setCurrentIndex(i if i >= 0 else 0)
        self._dung = False
        self._cap_nut_dot()
        self._ve()

    def _doi_dot(self):
        if not self._dung:
            self._cap_nut_dot()
            self._ve()

    def _cap_nut_dot(self):
        """Nút theo đợt: sáng khi chọn một đợt cụ thể; mờ ở dòng "Lũy kế" (và Xóa đợt mờ khi chỉ xem)."""
        co_dot = bool(self._dot_id())
        self.b_xoa_dot.setEnabled(co_dot and not self.chi_doc)
        self.b_in_du_thao.setEnabled(co_dot)

    def _ve(self):
        p = du_thao.thong_ke_phieu(self.con)
        self.the['tong'].dat(f'{p["tong"]} hộ', '100% quy mô dự án')
        self.the['du'].dat(f'{p["du_dieu_kien"]} hộ', f'{_pt(p["pt_du"])}% đã đánh dấu đủ điều kiện')
        self.the['vuong'].dat(f'{p["vuong"]} hộ', f'{_pt(p["pt_vuong"])}% chờ xử lý, chưa đưa vào đợt')
        self.the['dt'].dat(f'{p["da_du_thao"]} hộ', f'{_pt(p["pt_du_thao"])}% đã đưa ra niêm yết')
        self.the['pd'].dat(f'{p["phe_duyet"]} hộ', f'{_pt(p["pt_phe_duyet"])}% có quyết định')
        self.the['bg'].dat(f'{p["ban_giao"]} hộ', f'{_pt(p["pt_ban_giao"])}% đã bàn giao')
        dot = self._dot_id()
        tk = du_thao.thong_ke_y_kien(self.con, dot)
        self.lb_dot.setText(
            f'Tiến độ {"đợt" if dot else "lũy kế"}: Đồng thuận {tk["dong_y"]}/{tk["so_ho_dot"]} ({tk["pt_dot"]:.0f}%)'
            f' · Không đồng ý: {tk["khong_dong_y"]} · Ý kiến khác: {tk["y_kien_khac"]} · Chưa lấy ý kiến: {tk["chua"]}')
        self.lb_luy.setText(f'Lũy kế niêm yết: {tk["luy_dong"]}/{tk["luy_ny"]} hộ đồng ý ({_pt(tk["pt_luy"])}%)')
        self.lb_phu.setText(f'Bao phủ dự án: {tk["luy_dong"]}/{tk["tong_du_an"]} hộ ({_pt(tk["pt_bao_phu"])}%)')
        self.lb_dot.setToolTip('Tỷ lệ đồng thuận của đợt đang chọn (số hộ đồng ý / số hộ của đợt). Chọn "Lũy kế" để xem mọi đợt.')
        self.lb_luy.setToolTip('Hộ đồng ý / số hộ đã đưa ra niêm yết, lấy ý kiến (mọi đợt)')
        self.lb_phu.setToolTip('Hộ đã đồng ý / tổng số hộ của dự án')
        self.thanh.setValue(int(round(tk['pt_bao_phu'])))
        self._ve_bang(dot, tk)

    def _ve_bang(self, dot, tk):
        ho = du_thao.ds_ho_dot(self.con, dot) if dot else []
        dia = ''
        if dot:
            r = self.con.execute('SELECT dia_diem FROM dot_du_thao WHERE id = ?', (dot,)).fetchone()
            dia = r['dia_diem'] if r else ''
        self.bang_ny.setRowCount(len(ho))
        for i, h in enumerate(ho):
            for c, v in enumerate((i + 1, h['ho_ten'], h['cccd_che'], h['thua'],
                                   vn(h['tien']) if h['tien'] is not None else '', dia)):
                self.bang_ny.setItem(i, c, _o(v))
            self.bang_ny.item(i, 0).setData(Qt.ItemDataRole.UserRole, h['ma_ho'])
        self.bang_yk.setRowCount(len(ho))
        for i, h in enumerate(ho):
            for c, v in enumerate((h['ma_ho'], h['ho_ten'], '● ' + du_thao.TEN_LOAI.get(h['loai'], ''),
                                   du_thao.TEN_NHOM.get(h['nhom'], ''), h['noi_dung'], h['so_tien_chenh'])):
                self.bang_yk.setItem(i, c, _o(v))
            self.bang_yk.item(i, 0).setData(Qt.ItemDataRole.UserRole, h['ma_ho'])
            it = self.bang_yk.item(i, 2)                                # màu theo ý kiến (xanh / đỏ / vàng / xám)
            it.setForeground(QBrush(QColor(MAU_Y_KIEN.get(h['loai'], '#64748B'))))
            it.setData(Qt.ItemDataRole.UserRole, h['loai'])
            it.setToolTip('Bấm để đổi ý kiến (hoặc phím Space)')
        chua_dong = [h for h in ho if h['loai'] in ('khong_dong_y', 'y_kien_khac')]
        self.bang_dt.setRowCount(len(chua_dong))
        for i, h in enumerate(chua_dong):
            for c, v in enumerate((h['ma_ho'], h['ho_ten'], h['noi_dung'], h['lan_dt'], h['ket_qua_doi_thoai'],
                                   'Đã chuyển' if h['chuyen_dot_id'] else '')):
                self.bang_dt.setItem(i, c, _o(v))
            self.bang_dt.item(i, 0).setData(Qt.ItemDataRole.UserRole, h['ma_ho'])
        nhom = du_thao.tong_hop_nhom(self.con, dot)                     # tỷ lệ đồng thuận theo nhóm lý do (0.9.75)
        self.bang_th.setRowCount(len(nhom))
        for i, x in enumerate(nhom):
            for c, v in enumerate((x['ten'], x['so_ho'], x['dong_y'], x['chua_dong_y'],
                                   f'{_pt(x["pt_dong_y"])}%' if x['so_ho'] else '-', x['noi_dung'])):
                it = _o(v)
                if c in (1, 2, 3, 4):                                   # 1.0.03: cột số căn giữa (kể cả dòng "Toàn bộ các đợt")
                    it.setTextAlignment(CAN_GIUA)
                if not x['nhom']:                                       # dòng tổng: đậm
                    f = it.font()
                    f.setBold(True)
                    it.setFont(f)
                self.bang_th.setItem(i, c, it)
        self.bang_th.setToolTip('Tỷ lệ đồng thuận = hộ đã đồng ý trong nhóm lý do / hộ có kiến nghị nhóm đó')
        vm = du_thao.ds_vuong(self.con)
        self.bang_vm.setRowCount(len(vm))
        for i, h in enumerate(vm):
            for c, v in enumerate((h['ma_ho'], h['ho_ten'], h['thua'], h['ten_vuong'], h['ghi_chu_phap_ly'])):
                self.bang_vm.setItem(i, c, _o(v))
            self.bang_vm.item(i, 0).setData(Qt.ItemDataRole.UserRole, h['ma_ho'])
        # nút xuất chỉ sáng khi có dữ liệu để xuất
        for b in (self.bang_ny, self.bang_yk, self.bang_dt, self.bang_th, self.bang_vm):
            san_tieu_de(b)
        if 'Xuất bảng niêm yết' in self._nut:
            self._nut['Xuất bảng niêm yết'].setEnabled(bool(dot) and bool(ho))
            self._nut['Xuất biên bản đối thoại'].setEnabled(bool(dot) and bool(chua_dong))
            self._nut['Xuất báo cáo tổng hợp ý kiến'].setEnabled(bool(dot) and bool(ho))

    def _bao(self, chu):
        QMessageBox.information(self, TEN_UD, chu)

    def _loi(self, e):
        QMessageBox.warning(self, TEN_UD, chu_loi('Dự thảo', e) if not isinstance(e, du_thao.LoiNhap) else str(e))

    def _tao(self):
        d = HopTaoDot(self)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            moi = du_thao.tao_dot(self.con, d.ten.text(), d.ngay.text(), d.dia.text())
        except du_thao.LoiNhap as e:
            self._loi(e)
            return
        self.thay_doi_csdl = True
        self.nap()
        i = self.cb.findData(moi)
        if i >= 0:
            self.cb.setCurrentIndex(i)
        self._bao(f'Đã tạo đợt. Niêm yết đến ngày {du_thao.hien_ngay(du_thao.ngay_ket_thuc(d.ngay.text()))}. '
                  'Bấm "Đưa hộ đủ điều kiện vào đợt" để chọn hộ được lấy ý kiến.')

    def _xoa_dot(self, xac_nhan: bool | None = None):
        """Xóa đợt đang chọn (đặc tả V10): hỏi xác nhận nói rõ điều gì mất / giữ. Hộ về danh sách chờ, phương án giữ nguyên 100%."""
        dot = self._dot_id()
        if not dot:
            self._bao('Chọn một đợt cụ thể để xóa (dòng "Lũy kế toàn bộ các đợt" không phải một đợt).')
            return None
        try:
            tt = du_thao.thong_tin_xoa_dot(self.con, dot)
        except du_thao.LoiNhap as e:
            self._loi(e)
            return None
        if xac_nhan is None:
            chu = (f'Xóa "{tt["ten"]}"?\n\n- {tt["so_ho"]} hộ của đợt trở về danh sách chờ; phương án, thửa, hồ sơ của các hộ '
                   'giữ nguyên.')
            if tt['co_y_kien'] or tt['so_doi_thoai']:
                chu += (f'\n- Mất {tt["co_y_kien"]} ý kiến đã ghi và {tt["so_doi_thoai"]} biên bản đối thoại của đợt này '
                        '(lấy lại bằng Hoàn tác - Ctrl+Z ngay sau khi xóa).')
            xac_nhan = QMessageBox.question(self, TEN_UD, chu) == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        try:
            tt = du_thao.xoa_dot(self.con, dot)
        except du_thao.LoiNhap as e:
            self._loi(e)
            return None
        self.thay_doi_csdl = True
        self.nap()
        return tt

    def _in_du_thao(self, cho: bool = True):
        """In PA Dự thảo gửi dân: Xuất hồ sơ & Bản in ở chế độ Dự thảo cho các hộ của đợt đang chọn (đặc tả V10)."""
        dot = self._dot_id()
        if not dot:
            self._bao('Chọn một đợt cụ thể (dòng "Lũy kế" không phải một đợt) rồi bấm lại.')
            return None
        ds = [h['ma_ho'] for h in du_thao.ds_ho_dot(self.con, dot)]
        if not ds:
            self._bao('Đợt này chưa có hộ: bấm "Đưa hộ vào đợt" trước.')
            return None
        cha = self.window()
        if not hasattr(cha, 'in_xuat'):
            return None
        return cha.in_xuat(cho=cho, ma_ho=ds, che_do='du_thao')

    def _them_ho(self):
        dot = self._dot_id()
        if not dot:
            self._bao('Chọn một đợt (đợt 1, đợt 2 hoặc đợt khác). Dòng "Lũy kế" không nhận thêm hộ.')
            return
        d = HopThemHo(self, self.con, dot)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        ds = d.ma_chon()
        if not ds:
            self._bao('Chưa đánh dấu hộ nào.')
            return
        try:
            them, bo = du_thao.them_thu_cong(self.con, dot, ds)
        except du_thao.LoiNhap as e:
            self._loi(e)
            return
        self.thay_doi_csdl = True
        self._ve()
        self._bao(f'Đã thêm {them} hộ vào đợt này. Bỏ qua {bo} hộ (đang vướng pháp lý hoặc đã có trong đợt). '
                  'Danh sách niêm yết, lấy ý kiến và đối thoại dùng chung các hộ vừa thêm.')

    def _dua(self):
        dot = self._dot_id()
        if not dot:
            self._bao('Chọn một đợt. Dòng "Lũy kế" không phải một đợt.')
            return
        try:
            them, bo = du_thao.dua_ho_vao_dot(self.con, dot)
        except du_thao.LoiNhap as e:
            self._loi(e)
            return
        self.thay_doi_csdl = True
        self._ve()
        self._bao(f'Thêm {them} hộ vào đợt. Bỏ qua {bo} hộ (chưa đủ điều kiện, đang vướng, hoặc đã có trong đợt).')

    def _goi_y(self):
        n = du_thao.goi_y_du_dieu_kien(self.con)
        self.thay_doi_csdl = True
        self._ve()
        self._bao(f'Đã gợi ý {n} hộ đủ điều kiện (có tên, nguồn gốc thửa, không tranh chấp, đã có phương án, không đang vướng). '
                  'Đối chiếu lại 4 điều kiện pháp lý trước khi niêm yết. Hộ vướng đánh dấu ở thẻ 5.')

    def _ngay_hop(self):
        dot = self._dot_id()
        if not dot:
            self._bao('Chọn một đợt.')
            return
        d = QDialog(self)
        d.setWindowTitle('Ngày họp lấy ý kiến')
        ngay = QLineEdit()
        ngay.setPlaceholderText('Ngày họp dân, sau khi hết 10 ngày niêm yết')
        f = QFormLayout(d)
        f.addRow('Ngày họp:', ngay)
        b = QPushButton('Ghi')
        b.clicked.connect(d.accept)
        f.addRow(b)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            han = du_thao.dat_ngay_hop(self.con, dot, ngay.text())
        except du_thao.LoiNhap as e:
            self._loi(e)
            return
        self.thay_doi_csdl = True
        self._bao(f'Hạn đối thoại: {du_thao.hien_ngay(han)} (30 ngày kể từ ngày họp).')

    def _ho_dong(self, bang, row):
        it = bang.item(row, 0)
        if it is None:
            return None
        ma = it.data(Qt.ItemDataRole.UserRole)
        dot = self._dot_id()
        if not dot or ma is None:
            return None
        for h in du_thao.ds_ho_dot(self.con, dot):
            if h['ma_ho'] == ma:
                return h
        return None

    def _sua_yk(self, bang, row):
        if self.chi_doc:
            self._bao('Dự án đang mở chỉ xem.')
            return
        h = self._ho_dong(bang, row)
        if h is None:
            return
        d = HopYKien(self, h)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            du_thao.ghi_y_kien(self.con, self._dot_id(), h['ma_ho'], d.loai.currentData(), d.nhom.currentData(),
                               d.nd.toPlainText(), tien_chenh=d.tien.text(), ket_qua=d.kq.toPlainText())
            if d.ngay_dt.text().strip() and d.kq.toPlainText().strip():
                du_thao.ghi_doi_thoai(self.con, self._dot_id(), h['ma_ho'], d.ngay_dt.text(), '', d.kq.toPlainText())
        except du_thao.LoiNhap as e:
            self._loi(e)
            return
        self.thay_doi_csdl = True
        self._ve()

    def _doi_nhanh(self, r: int):
        """Một chạm: đổi ý kiến của hộ ở dòng r (thẻ Lấy ý kiến) sang loại kế tiếp, giữ dòng đang chọn."""
        it = self.bang_yk.item(r, 0)
        dot = self._dot_id()
        if self.chi_doc or it is None or not dot:
            return None
        try:
            loai = du_thao.doi_y_kien_nhanh(self.con, dot, it.data(Qt.ItemDataRole.UserRole))
        except du_thao.LoiNhap as e:
            self._loi(e)
            return None
        self.thay_doi_csdl = True
        self._ve()
        self.bang_yk.selectRow(r)
        self.bang_yk.setCurrentCell(r, 2)
        return loai

    def _bam_y_kien(self, r: int, c: int):
        if c == 2:
            self._doi_nhanh(r)

    def _phim_y_kien(self):
        r = self.bang_yk.currentRow()
        if r >= 0 and self.bang_yk.currentColumn() == 2:
            self._doi_nhanh(r)

    def _kep_y_kien(self, r: int, c: int):
        """Bấm đúp: ô Nội dung -> hộp nhập phản ánh; ô Ý kiến -> bỏ qua (hai cú bấm đã đổi ý kiến hai lần); ô khác -> hộp ý kiến đủ."""
        if c == 2:
            return
        if c == 4:
            self._sua_noi_dung(r)
        else:
            self._sua_yk(self.bang_yk, r)

    def _sua_noi_dung(self, r: int):
        if self.chi_doc:
            self._bao('Dự án đang mở chỉ xem.')
            return None
        h = self._ho_dong(self.bang_yk, r)
        if h is None:
            return None
        d = HopNoiDung(self, h)
        if d.exec() != QDialog.DialogCode.Accepted:
            return None
        try:
            du_thao.cap_nhat_y_kien(self.con, self._dot_id(), h['ma_ho'], noi_dung=d.nd.toPlainText())
        except du_thao.LoiNhap as e:
            self._loi(e)
            return None
        self.thay_doi_csdl = True
        self._ve()
        self.bang_yk.selectRow(r)
        return True

    def _ma_chon(self, bang) -> list:
        return [bang.item(r, 0).data(Qt.ItemDataRole.UserRole) for r in sorted({i.row() for i in bang.selectedIndexes()})
                if bang.item(r, 0) is not None]

    def _chuyen(self):
        dot = self._dot_id()
        ds = self._ma_chon(self.bang_dt)
        if not dot or not ds:
            self._bao('Chọn hộ chưa đồng ý ở thẻ Đối thoại, và đang xem một đợt.')
            return
        dots = [d for d in du_thao.ds_dot(self.con) if d['id'] != dot]
        if not dots:
            self._bao('Tạo đợt sau trước, rồi chuyển hộ sang đợt đó.')
            return
        d = QDialog(self)
        d.setWindowTitle('Chuyển sang đợt sau')
        cb = QComboBox()
        for x in dots:
            cb.addItem(x['ten'], x['id'])
        f = QFormLayout(d)
        f.addRow('Đợt nhận:', cb)
        b = QPushButton('Chuyển')
        b.clicked.connect(d.accept)
        f.addRow(b)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        n = du_thao.chuyen_sang_dot(self.con, dot, ds, cb.currentData())
        self.thay_doi_csdl = True
        self._ve()
        self._bao(f'Đã chuyển {n} hộ. Ý kiến ở đợt này giữ nguyên. Đợt sau ghi nhận hộ ở trạng thái chưa lấy ý kiến.')

    def _phap_ly(self):
        if self.chi_doc:
            self._bao('Dự án đang mở chỉ xem.')
            return
        ds = self._ma_chon(self.bang_vm)
        if len(ds) != 1:
            self._bao('Chọn một hộ ở thẻ Hộ vướng.')
            return
        ho = next(h for h in du_thao.ds_vuong(self.con) if h['ma_ho'] == ds[0])
        d = HopPhapLy(self, ho)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            du_thao.ghi_phap_ly(self.con, ds[0], d.du.currentData(), d.vuong.currentData(), d.gc.text())
        except du_thao.LoiNhap as e:
            self._loi(e)
            return
        self.thay_doi_csdl = True
        self._ve()

    def _luu_file(self, tieu_de, ham):
        dot = self._dot_id()
        p, _ = QFileDialog.getSaveFileName(self, tieu_de, '', 'Excel (*.xlsx)')
        if not p:
            return
        try:
            f = ham(dot, p) if ham != du_thao.xuat_don_doc else ham(self.con, p)
        except du_thao.LoiNhap as e:
            self._loi(e)
            return
        except OSError as e:
            self._loi(e)
            return
        self._bao(f'Đã ghi:\n{f}')

    def _xuat_ny(self):
        if not self._dot_id():
            self._bao('Chọn một đợt.')
            return
        self._luu_file('Bảng niêm yết dự thảo', lambda dot, p: du_thao.xuat_niem_yet(self.con, dot, p))

    def _xuat_yk(self):
        if not self._dot_id():
            self._bao('Chọn một đợt.')
            return
        self._luu_file('Báo cáo ý kiến', lambda dot, p: du_thao.xuat_y_kien(self.con, dot, p))

    def _xuat_dt(self):
        if not self._dot_id():
            self._bao('Chọn một đợt.')
            return
        self._luu_file('Biên bản đối thoại, giải trình', lambda dot, p: du_thao.xuat_doi_thoai(self.con, dot, p))

    def _xuat_dd(self):
        self._luu_file('Danh sách đôn đốc', du_thao.xuat_don_doc)


class HopChonNiemYet(QDialog):
    """Chọn hộ đủ điều kiện niêm yết công khai, lấy ý kiến (0.9.69 - người dùng 12/10/2026: đánh dấu ngay trên danh sách hộ sau
    khi lập phương án). Phần mềm xét các điều kiện `du_thao.DIEU_KIEN_NIEM_YET` và tích sẵn các hộ đạt; người dùng tích /
    bỏ tích từng hộ rồi Lưu (ho.du_dieu_kien), có thể đưa luôn các hộ đã tích vào một đợt niêm yết."""
    LOC = (('tat_ca', 'Tất cả hộ'), ('du', 'Đủ điều kiện'), ('chua_du', 'Chưa đủ điều kiện'), ('da_danh_dau', 'Đang tích'),
           ('chua_vao_dot', 'Chưa vào đợt niêm yết nào'))

    def __init__(self, parent, con, ds_ma_ho=None, chi_doc: bool = False):
        super().__init__(parent)
        self.con, self.chi_doc = con, chi_doc
        self.im_lang = False
        self.setWindowTitle('Chọn hộ niêm yết công khai, lấy ý kiến')
        self.resize(980, 600)
        self.ds = du_thao.danh_gia_niem_yet(con, ds_ma_ho)
        # tích theo mã hộ: hộ đã đánh dấu giữ nguyên; hộ chưa đánh dấu mà đủ điều kiện thì tích sẵn (gợi ý); hộ vướng: không
        self.tich = {h['ma_ho']: bool(h['da_danh_dau'] or h['du']) and not h['vuong'] for h in self.ds}
        lo = QVBoxLayout(self)
        n_du = sum(1 for h in self.ds if h['du'])
        dk = QLabel('Điều kiện xét: ' + '; '.join(f'({i}) {t}' for i, t in enumerate(du_thao.DIEU_KIEN_NIEM_YET, 1)) +
                    f'. Đủ điều kiện: {n_du} / {len(self.ds)} hộ' + (' (trong các hộ đang chọn)' if ds_ma_ho else '') +
                    '. Phần mềm đã tích sẵn các hộ đủ điều kiện - rà lại rồi bấm Lưu.')
        dk.setWordWrap(True)
        lo.addWidget(dk)
        hang = QHBoxLayout()
        self.cb_loc = QComboBox()
        for k, t in self.LOC:
            self.cb_loc.addItem(t, k)
        self.cb_loc.currentIndexChanged.connect(lambda *_: self._ve())
        b_du = QPushButton('Tích các hộ đủ điều kiện')
        b_du.clicked.connect(lambda: self._dat(lambda h: h['du']))
        b_het = QPushButton('Tích tất cả đang hiện')
        b_het.clicked.connect(lambda: self._dat(lambda h: True, chi_dang_hien=True))
        b_bo = QPushButton('Bỏ tích đang hiện')
        b_bo.clicked.connect(lambda: self._dat(lambda h: False, chi_dang_hien=True))
        nhan = QLabel('Lọc:')
        nhan.setProperty('vai', 'nhan')
        hang.addWidget(nhan)
        hang.addWidget(self.cb_loc)
        for b in (b_du, b_het, b_bo):
            hang.addWidget(b)
        hang.addStretch(1)
        lo.addLayout(hang)
        self.bang = _bang(['Niêm yết', 'STT', 'Họ và tên', 'Tổng tiền (đồng)', 'Tình trạng', 'Đợt niêm yết'])
        self.bang.itemChanged.connect(self._doi_tich)
        lo.addWidget(self.bang, 1)
        hd = QHBoxLayout()
        nhan_dot = QLabel('Sau khi lưu:')
        nhan_dot.setProperty('vai', 'nhan')
        self.cb_dot = QComboBox()
        self.cb_dot.addItem('Chỉ đánh dấu đủ điều kiện (đưa vào đợt sau, ở Niêm yết & Lấy ý kiến)', None)
        for d in du_thao.ds_dot(con):
            self.cb_dot.addItem(f'Đưa các hộ đã tích vào đợt: {d["ten"]}', d['id'])
        self.lb_dem = QLabel('')
        self.b_luu = QPushButton('Lưu')
        self.b_luu.clicked.connect(lambda: self.luu())
        self.b_luu.setEnabled(not chi_doc)
        if chi_doc:
            self.b_luu.setToolTip('Dự án đang mở chỉ xem')
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        hd.addWidget(nhan_dot)
        hd.addWidget(self.cb_dot, 1)
        hd.addWidget(self.lb_dem)
        hd.addWidget(self.b_luu)
        hd.addWidget(b_dong)
        lo.addLayout(hd)
        self._ve()

    def _hien(self, h) -> bool:
        k = self.cb_loc.currentData()
        return (k == 'tat_ca' or (k == 'du' and h['du']) or (k == 'chua_du' and not h['du']) or
                (k == 'da_danh_dau' and bool(self.tich.get(h['ma_ho']))) or (k == 'chua_vao_dot' and not h['dot']))

    def _ve(self):
        self.dang_hien = [h for h in self.ds if self._hien(h)]
        self.bang.blockSignals(True)
        self.bang.setRowCount(len(self.dang_hien))
        for i, h in enumerate(self.dang_hien):
            o = QTableWidgetItem('')
            co = Qt.ItemFlag.ItemIsEnabled | (Qt.ItemFlag.ItemIsUserCheckable if not h['vuong'] else Qt.ItemFlag.NoItemFlags)
            o.setFlags(co)
            o.setCheckState(Qt.CheckState.Checked if self.tich.get(h['ma_ho']) else Qt.CheckState.Unchecked)
            o.setData(Qt.ItemDataRole.UserRole, h['ma_ho'])
            self.bang.setItem(i, 0, o)
            tt = 'Đủ điều kiện' if h['du'] else '; '.join(h['ly_do'])
            if h['du'] and h['can_xem']:
                tt += f' (kiểm tra phương án: {len(h["can_xem"])} điểm cần xem lại)'
            o_tt = _o(tt)
            o_tt.setToolTip(chr(10).join(h['ly_do'] + h['can_xem']) or tt)
            o_tt.setForeground(Qt.GlobalColor.darkGreen if h['du'] else Qt.GlobalColor.darkRed)
            o_tien = _o('' if h['tien'] is None else vn(h['tien']))
            o_tien.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            for c, x in enumerate((_o(h['thu_tu']), _o(h['ho_ten']), o_tien, o_tt, _o(h['dot'])), 1):
                self.bang.setItem(i, c, x)
        self.bang.blockSignals(False)
        for c, w in enumerate((70, 50, 220, 130, 330)):
            self.bang.setColumnWidth(c, w)
        self._dem()

    def _doi_tich(self, it):
        if it.column() == 0:
            self.tich[it.data(Qt.ItemDataRole.UserRole)] = it.checkState() == Qt.CheckState.Checked
            self._dem()

    def _dat(self, dieu_kien, chi_dang_hien: bool = False):
        for h in (self.dang_hien if chi_dang_hien else self.ds):
            if not h['vuong']:
                self.tich[h['ma_ho']] = bool(dieu_kien(h))
        self._ve()

    def _dem(self):
        self.lb_dem.setText(f'Đã tích {sum(1 for v in self.tich.values() if v)} hộ')

    def ma_da_tich(self) -> list:
        return [h['ma_ho'] for h in self.ds if self.tich.get(h['ma_ho'])]

    def luu(self):
        """Ghi đánh dấu (một bước Hoàn tác); chọn đợt thì đưa các hộ đã tích chưa có trong đợt vào. Trả (số hộ đổi, số thêm
        vào đợt)."""
        if self.chi_doc:
            return None
        dot = self.cb_dot.currentData()
        try:
            doi, _ = du_thao.ghi_danh_dau(self.con, dict(self.tich))
            them = 0
            if dot is not None and self.ma_da_tich():
                them, _ = du_thao.dua_ho_vao_dot(self.con, dot, self.ma_da_tich())
        except Exception as e:
            if not self.im_lang:
                QMessageBox.warning(self, TEN_UD, chu_loi('Lưu đánh dấu hộ niêm yết', e))
            return None
        if not self.im_lang:
            QMessageBox.information(self, TEN_UD, f'Đã lưu: {len(self.ma_da_tich())} hộ đủ điều kiện niêm yết'
                                    f' ({doi} hộ đổi đánh dấu)' + (f'; đưa {them} hộ vào đợt niêm yết.' if dot is not None
                                                                   else '.'))
        self.accept()
        return doi, them

"""Màn hình Dự thảo PABT: phễu tiến độ, 5 việc (niêm yết, ý kiến, đối thoại, tổng hợp, hộ vướng)."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMenu, QMessageBox, QProgressBar, QPushButton, QStackedWidget, QTabWidget,
                               QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)

from . import du_thao
from .giao_dien import dat_kieu_theo_tong  # noqa: E402  (1.0.34: kiểu riêng đổi theo tông nền)
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
    if b.property('stt_co_dinh'):                       # cột STT rộng cố định: chữ "STT" vừa, không theo sàn chung
        b.setColumnWidth(0, b.property('stt_co_dinh'))


MAU_Y_KIEN = {'dong_y': '#2F7D54', 'khong_dong_y': '#B83A3A', 'y_kien_khac': '#9A5A12', 'chua': '#64748B'}
# thẻ KPI trang Niêm yết (1.0.02, như thẻ số màn hình chính): màu vạch trái + màu số. Navy = tổng; xanh trời / xanh dương = đủ điều kiện /
# đã niêm yết; teal / xanh lá = phê duyệt / bàn giao (đã đồng thuận); hổ phách = vướng (cần xử lý)
MAU_THE_NY = {'tong': '#1E3A5F', 'du': '#1F76A6', 'vuong': '#9A5A12', 'dt': '#2563EB', 'pd': '#1F6F66', 'bg': '#2F7D54'}
# 1.0.03: góc trái bo 3 px (bằng bề dày vạch) - vạch màu bên trái thẳng đứng, không cong thành dấu "(" như bo 6 px (Ảnh 7)
QSS_THE_NY = ('QFrame[vai="the_ny"] {{ background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 3px solid {m}; '
              'border-radius: 6px; border-top-left-radius: 3px; border-bottom-left-radius: 3px; }}'
              'QFrame[vai="the_ny"]:hover {{ background: #F8FAFC; border-color: {m}; }}'
              'QLabel#the_ny_tieu {{ color: #475569; font-size: 12px; font-weight: 600; border: 0; background: transparent; }}'
              'QLabel#the_ny_so {{ color: #0F172A; font-family: "Consolas"; font-size: 16px; font-weight: 700; border: 0; background: transparent; }}'
              'QLabel#the_ny_phu {{ color: #64748B; font-size: 12px; border: 0; background: transparent; }}')
CAO_THE_NY = 54
RONG_O_DOT = 300            # ô chọn đợt (chữ dài đủ ở chú thích)
RONG_COT_NY = [48, 0, 125, 130, 135, 240]       # bảng hộ niêm yết (06/11/2026, người dùng): cột Họ và tên giãn


def _pt(x) -> str:
    """Phần trăm kiểu VN, 1 chữ số lẻ: 12.5 -> "12,5" (dấu phẩy thập phân)."""
    return f'{float(x):.1f}'.replace('.', ',')


class _The(QFrame):
    def __init__(self, tieu_de, mau, bam):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty('vai', 'the_ny')
        self.mau = mau
        dat_kieu_theo_tong(self, QSS_THE_NY.format(m=mau))    # bộ chọn theo vai: không truyền sang nhãn con (QLabel cũng là QFrame)
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
        # 22/10/2026 (nâng cấp giao diện): trên thẻ chỉ tỷ lệ "75,0%" (chữ diễn giải dài bị cắt "75,0% đã đánh …") - câu đủ ở chú thích
        import re
        m = re.match(r'\s*(\d[\d.,]*\s*%)', phu or '')
        self.phu.setText(m.group(1) if m else phu)
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


class _OSap(QTableWidgetItem):
    """Ô bảng sắp xếp theo khóa (UserRole + 1: số thứ tự / số tiền / mức) thay vì theo chữ."""

    def __lt__(self, other):
        a, b = self.data(Qt.ItemDataRole.UserRole + 1), other.data(Qt.ItemDataRole.UserRole + 1)
        if a is not None and b is not None:
            try:
                return a < b
            except TypeError:
                pass
        return self.text().lower() < other.text().lower()


class HopThemHo(QDialog):
    """Chọn hộ đưa vào đợt đang mở (30/10/2026 - người dùng): MỌI hộ chưa có trong đợt, kèm lập phương án, tổng tiền, điều kiện, ý kiến gần
    nhất, đợt hiện tại; lọc theo từng thuộc tính + tìm; bấm tiêu đề cột để sắp xếp. Hộ đủ điều kiện, không vướng được đánh dấu sẵn; hộ chưa
    đủ điều kiện / đang vướng vẫn thêm được khi người lập đánh dấu (ô "Cho thêm cả hộ chưa đủ điều kiện" tự bật)."""
    COT = ['', 'STT', 'Họ và tên', 'Thửa', 'Lập phương án', 'Tổng tiền (đ)', 'Điều kiện', 'Ý kiến gần nhất', 'Đợt hiện tại']
    LOC_LAP = [('', 'Lập PA: tất cả'), ('da_lap', 'Đã lập PA'), ('tu_lap', 'Tự lập, chưa soát'), ('chua', 'Chưa lập PA')]
    LOC_DK = [('', 'Điều kiện: tất cả'), ('du', 'Đủ điều kiện'), ('chua', 'Chưa đánh dấu đủ điều kiện'), ('vuong', 'Đang vướng V1-V5')]
    LOC_YK = [('', 'Ý kiến: tất cả'), ('-', 'Chưa vào đợt nào'), ('chua', 'Chưa lấy ý kiến'), ('dong_y', 'Đồng ý'),
              ('khong_dong_y', 'Không đồng ý'), ('y_kien_khac', 'Ý kiến khác')]

    def __init__(self, parent, con, dot_id: int):
        super().__init__(parent)
        from .giao_dien import loc_khi_ngung_go
        self.con, self.dot_id = con, dot_id
        self.setWindowTitle('Thêm hộ vào đợt')
        self.resize(1280, 640)
        self.ds = du_thao.ds_ho_cho_dot(con, dot_id)
        self.cb_lap, self.cb_dk, self.cb_yk = (self._o_loc(x) for x in (self.LOC_LAP, self.LOC_DK, self.LOC_YK))
        self.cb_dot = QComboBox()
        self.cb_dot.addItem('Đợt hiện tại: tất cả', None)
        self.cb_dot.addItem('Chưa thuộc đợt nào', 0)
        for d in du_thao.ds_dot(con):
            if d['id'] != dot_id:
                self.cb_dot.addItem(f'Đang ở: {d["ten"]}', d['id'])
        self.cb_dot.currentIndexChanged.connect(lambda *_: self._loc())
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm họ tên, thửa, địa chỉ…')
        loc_khi_ngung_go(self.o_tim, self._loc)
        self.o_ca_chua = QCheckBox('Cho thêm cả hộ chưa đủ điều kiện / đang vướng')
        self.o_ca_chua.setToolTip('Bình thường chỉ hộ đủ điều kiện, không vướng mới vào đợt. Bật để thêm cả hộ chưa đủ điều kiện hoặc '
                                  'đang vướng (V1-V5) đã đánh dấu - tự bật khi đánh dấu một hộ như vậy.')
        self.bang = _bang(self.COT, [34, 50, 240, 150, 125, 115, 165, 125, 100], gian=2)
        self.bang.setWordWrap(False)                    # một dòng mỗi hộ; chữ dài: chú thích
        from .giao_dien import giu_cot_gian
        self._giu = giu_cot_gian(self.bang, [2], 220)          # cột Họ và tên không bị bóp (hẹp thì cuộn ngang)
        self.bang.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.bang.setSortingEnabled(False)
        self.bang.itemChanged.connect(self._doi_dau)
        self.lb_dem = QLabel('')
        lo = QVBoxLayout(self)
        lo.addWidget(QLabel('Đánh dấu hộ cần thêm vào đợt đang mở (niêm yết, lấy ý kiến và đối thoại dùng chung danh sách này). Lọc theo '
                            'từng thuộc tính; bấm tiêu đề cột để sắp xếp.'))
        h1 = QHBoxLayout()
        for w in (self.cb_lap, self.cb_dk, self.cb_yk, self.cb_dot):
            h1.addWidget(w)
        h1.addWidget(self.o_tim, 1)
        lo.addLayout(h1)
        hang = QHBoxLayout()
        b1 = QPushButton('Chọn các hộ đang hiện')
        b2 = QPushButton('Bỏ chọn các hộ đang hiện')
        b1.clicked.connect(lambda: self._chon(True))
        b2.clicked.connect(lambda: self._chon(False))
        hang.addWidget(b1)
        hang.addWidget(b2)
        hang.addWidget(self.o_ca_chua)
        hang.addStretch(1)
        hang.addWidget(self.lb_dem)
        lo.addLayout(hang)
        lo.addWidget(self.bang, 1)
        b = QPushButton('Thêm vào đợt')
        b.clicked.connect(self.accept)
        lo.addWidget(b)
        self._nap()

    def _o_loc(self, ds) -> QComboBox:
        cb = QComboBox()
        for k, t in ds:
            cb.addItem(t, k)
        cb.currentIndexChanged.connect(lambda *_: self._loc())
        return cb

    def _nap(self):
        self.bang.blockSignals(True)
        self.bang.setRowCount(len(self.ds))
        thu_dk = {k: i for i, k in enumerate(du_thao.VONG_VUONG)}
        thu_lap = {'da_lap': 0, 'tu_lap': 1, 'chua': 2}
        for i, h in enumerate(self.ds):
            o = _OSap('')
            o.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            o.setCheckState(Qt.CheckState.Checked if h['dieu_kien'] == 'du' else Qt.CheckState.Unchecked)
            o.setData(Qt.ItemDataRole.UserRole, h['ma_ho'])
            o.setData(Qt.ItemDataRole.UserRole + 1, 0 if h['dieu_kien'] == 'du' else 1)
            self.bang.setItem(i, 0, o)
            gt = [(h['thu_tu'], h['thu_tu']), (h['ho_ten'], None), (h['thua'], None), (h['ten_lap'], thu_lap.get(h['lap'], 9)),
                  (vn(h['tien']) if h['tien'] is not None else '', float(h['tien']) if h['tien'] is not None else -1.0),
                  ((f'{h["dieu_kien"]} - ' if h['dieu_kien'] in du_thao.TEN_VUONG else '') + h['ten_dieu_kien'],
                   thu_dk.get(h['dieu_kien'], 99)), (h['ten_y_kien'], None), (h['dot_hien'], None)]
            for c, (chu, khoa) in enumerate(gt, 1):
                it = _OSap('' if chu is None else str(chu))
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if khoa is not None:
                    it.setData(Qt.ItemDataRole.UserRole + 1, khoa)
                if c in (1, 5):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c == 2 and h['dia_chi']:
                    it.setToolTip(f'{h["ho_ten"]} - {h["dia_chi"]}')
                elif c in (3, 6) and chu:
                    it.setToolTip(str(chu))
                self.bang.setItem(i, c, it)
        self.bang.blockSignals(False)
        self.bang.setSortingEnabled(True)
        self.bang.sortByColumn(1, Qt.SortOrder.AscendingOrder)
        self._loc()

    def _h(self, r: int):
        it = self.bang.item(r, 0)
        ma = it.data(Qt.ItemDataRole.UserRole) if it is not None else None
        return next((h for h in self.ds if h['ma_ho'] == ma), None)

    def khop_loc(self, h) -> bool:
        """Hộ h thỏa mọi ô lọc đang chọn."""
        from .lap_pa import bo_dau
        lap, dk, yk, dot = (self.cb_lap.currentData(), self.cb_dk.currentData(), self.cb_yk.currentData(), self.cb_dot.currentData())
        if lap and h['lap'] != lap:
            return False
        if dk == 'vuong':
            if h['dieu_kien'] not in du_thao.TEN_VUONG:
                return False
        elif dk and h['dieu_kien'] != dk:
            return False
        if yk == '-' and h['y_kien']:
            return False
        if yk and yk != '-' and h['y_kien'] != yk:
            return False
        if dot == 0 and h['dot_hien_id']:
            return False
        if dot and h['dot_hien_id'] != dot:
            return False
        tim = bo_dau(self.o_tim.text()).lower().strip()
        return not tim or tim in bo_dau(f'{h["ho_ten"]} {h["thua"]} {h["dia_chi"]} {h["thu_tu"]}').lower()

    def _loc(self, *_):
        hien = 0
        ma_h = {h['ma_ho']: h for h in self.ds}
        for r in range(self.bang.rowCount()):
            it = self.bang.item(r, 0)
            h = ma_h.get(it.data(Qt.ItemDataRole.UserRole)) if it is not None else None
            an = h is None or not self.khop_loc(h)
            self.bang.setRowHidden(r, an)
            hien += not an
        self._dem(hien)

    def _dem(self, hien: int | None = None):
        if hien is None:
            hien = sum(1 for r in range(self.bang.rowCount()) if not self.bang.isRowHidden(r))
        self.lb_dem.setText(f'Đang hiện {hien}/{len(self.ds)} hộ · đã đánh dấu {len(self.ma_chon())}')

    def _doi_dau(self, it):
        if it.column() != 0:
            return
        h = self._h(it.row())
        if it.checkState() == Qt.CheckState.Checked and h is not None and h['dieu_kien'] != 'du' and not self.o_ca_chua.isChecked():
            self.o_ca_chua.setChecked(True)            # đánh dấu hộ chưa đủ điều kiện: hiểu là muốn thêm cả hộ đó
        self._dem()

    def _chon(self, bat: bool):
        st = Qt.CheckState.Checked if bat else Qt.CheckState.Unchecked
        self.bang.blockSignals(True)
        for r in range(self.bang.rowCount()):
            if not self.bang.isRowHidden(r):
                h = self._h(r)
                if bat and h is not None and h['dieu_kien'] != 'du' and not self.o_ca_chua.isChecked():
                    continue                            # chọn hàng loạt: hộ chưa đủ điều kiện chỉ khi đã bật ô cho phép
                self.bang.item(r, 0).setCheckState(st)
        self.bang.blockSignals(False)
        self._dem()

    def ca_chua(self) -> bool:
        return self.o_ca_chua.isChecked()

    def ma_chon(self) -> list:
        """Mã hộ đã đánh dấu, theo thứ tự hộ của dự án."""
        chon = set()
        for r in range(self.bang.rowCount()):
            it = self.bang.item(r, 0)
            if it is not None and it.checkState() == Qt.CheckState.Checked:
                chon.add(it.data(Qt.ItemDataRole.UserRole))
        return [h['ma_ho'] for h in self.ds if h['ma_ho'] in chon]


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
            'du': _The('Đủ điều kiện lập PA', MAU_THE_NY['du'], lambda: self.mo_bang_con(0)),
            'vuong': _The('Vướng pháp lý', MAU_THE_NY['vuong'], lambda: self.mo_bang_con(1)),
            'dt': _The('Đã niêm yết', MAU_THE_NY['dt'], lambda: self.mo_bang_con(0)),
            'pd': _The('Đã phê duyệt QĐ', MAU_THE_NY['pd'], self._mo_tien_do),
            'bg': _The('Đã bàn giao', MAU_THE_NY['bg'], self._mo_tien_do),
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
        dat_kieu_theo_tong(dai,
            'QFrame#dai_tien_do_ny { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 5px; }'
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
        dat_kieu_theo_tong(self.thanh,
            'QProgressBar { background: #E2E8F0; border: none; border-radius: 4px; }'
            'QProgressBar::chunk { background: #1E3A5F; border-radius: 4px; }')
        lo.addWidget(self.thanh)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        # 4 thẻ gọn: phông + lề ở mức QTabBar (Qt5 đo bề rộng thẻ theo phông thanh thẻ). Không setStyleSheet trên QTabWidget.
        f_the = self.tabs.tabBar().font()
        f_the.setPointSize(12)
        self.tabs.tabBar().setFont(f_the)
        self.tabs.tabBar().setStyleSheet('QTabBar { font-size: 12px; } QTabBar::tab { padding: 4px 12px; }')
        # 1.0.69: 4 thẻ luôn đủ chữ, sát lề trái: không cuộn thanh thẻ ("...ết công khai"), không cắt chữ
        self.tabs.setUsesScrollButtons(False)
        self.tabs.setElideMode(Qt.TextElideMode.ElideNone)
        self.tabs.tabBar().setExpanding(False)
        # CCCD hiển thị đủ số (1.0.04 bỏ che) - tiêu đề chỉ "CCCD"; bề rộng chuẩn từng cột + một cột giãn
        self.bang_ny = _bang(['STT', 'Họ và tên', 'CCCD', 'Thửa', 'Tổng tiền dự thảo', 'Địa điểm'], RONG_COT_NY, gian=1)
        self.bang_ny.horizontalHeader().setMinimumSectionSize(RONG_COT_NY[0])
        self.bang_ny.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.bang_ny.setProperty('stt_co_dinh', RONG_COT_NY[0])
        san_tieu_de(self.bang_ny)
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
        gan_thanh_ty_le(self.bang_th, 4, mau='#1F6F66')
        gan_chu_khi_trong(self.bang_ny, 'Chưa có hộ trong đợt niêm yết',
                          'Tạo đợt rồi bấm "Đưa hộ vào đợt" để thêm các hộ đủ điều kiện.')
        gan_chu_khi_trong(self.bang_vm, 'Không có hộ vướng pháp lý', 'Hộ đánh dấu V1-V5 (chưa đủ điều kiện) hiện ở đây.')
        gan_chu_khi_trong(self.bang_yk, 'Chưa có hộ để lấy ý kiến', 'Chọn đợt niêm yết đã có hộ.')
        gan_chu_khi_trong(self.bang_th, 'Chưa có kiến nghị nào được tổng hợp')
        # 0.9.70 (đặc tả ARCH-PABT-2026-V7 phần V): 4 thẻ con, tên không ghi cứng số ngày. Thẻ 1 gồm hộ đang niêm yết và hộ vướng / chưa đủ
        # điều kiện - trước là thẻ 5 riêng. 06/11/2026 (người dùng): hai bảng con chuyển bằng nút, mỗi bảng trọn chiều cao (trước: hai bảng chồng dọc, kéo thanh ngăn)
        from .giao_dien import giu_cot_gian
        self._giu_ny = giu_cot_gian(self.bang_ny, [1], 230)
        for b in (self.bang_yk, self.bang_dt):
            b.setColumnWidth(1, max(230, b.columnWidth(1)))
        # 06/11/2026 (người dùng kèm ảnh): nút của thẻ đang mở ở HÀNG RIÊNG dưới thanh thẻ, căn phải. Trước ở góc phải thanh thẻ: nút chiếm 658 px, 4 thẻ
        # cần 606 px và không cuộn được (1.0.69), cửa sổ dưới ~1.600 px thì nút che thẻ, không bấm tới được
        self._goc_nut = QWidget()
        self._h_goc = QHBoxLayout(self._goc_nut)
        self._h_goc.setContentsMargins(0, 0, 0, 0)
        self._h_goc.setSpacing(6)
        self._h_goc.addStretch(1)
        self._nut_goc = []
        self._ruot_the = {}                             # trang của tabs -> nội dung (bảng) của thẻ
        self.trang_ny = self._trang(self.bang_ny, [])   # nút "Xuất bảng niêm yết": hàng nút đợt phía trên (15/10/2026)
        self.trang_vm = self._trang(self.bang_vm, [
            ('Đánh dấu pháp lý hộ đang chọn', self._phap_ly),
            ('Xuất danh sách đôn đốc V1, V2', self._xuat_dd)])
        self.ngan_ny = QStackedWidget()
        self.ngan_ny.addWidget(self.trang_ny)
        self.ngan_ny.addWidget(self.trang_vm)
        self._tao_nut_bang_con()
        self.tabs.addTab(self._boc_the(self.ngan_ny), '1. Niêm yết công khai')
        self.tabs.addTab(self._boc_the(self._trang(self.bang_yk, [])), '2. Lấy ý kiến nhân dân')
        self.tabs.addTab(self._boc_the(self._trang(self.bang_dt, [
            ('Đối chiếu V1 - V2 - V3…', lambda: self.doi_chieu_phien_ban()), ('Chuyển hộ sang đợt sau', self._chuyen), ('Xuất biên bản đối thoại', self._xuat_dt)])), '3. Đối thoại && Tiếp thu')
        self.tabs.addTab(self._boc_the(self._trang(self.bang_th, [
            ('Đối chiếu V1 - V2 - V3… ', lambda: self.doi_chieu_phien_ban()), ('Xuất báo cáo tổng hợp ý kiến', self._xuat_yk)])), '4. Tổng hợp kết quả ý kiến')
        # 1.0.58 (người dùng 04/11/2026): văn bản, biên bản theo từng mục; đọc kết quả từ file scan / Word / Excel - theo thẻ đang mở
        self.b_van_ban = QPushButton('Văn bản, biên bản…')
        self.b_van_ban.setFixedHeight(26)
        self.b_van_ban.setToolTip('Thông báo niêm yết, Giấy mời, Biên bản… của mục (thẻ) đang mở trong đợt đang chọn: gõ nội dung hoặc đính kèm file')
        self.b_van_ban.clicked.connect(lambda: self.mo_van_ban())
        self.b_doc_kq = QPushButton('Đọc kết quả từ file…')
        self.b_doc_kq.setFixedHeight(26)
        self.b_doc_kq.setToolTip('Chọn file biên bản / danh sách (PDF scan, ảnh, Word, Excel): nhận ra từng hộ trong đợt và kết quả, xem trước rồi mới ghi')
        self.b_doc_kq.clicked.connect(lambda: self.doc_ket_qua())
        self._h_goc.addWidget(self.b_van_ban)
        self._h_goc.addWidget(self.b_doc_kq)
        # 05/11/2026: các việc quét của thẻ Niêm yết cùng gọi MỘT bộ quét dùng chung (quet_chung / lệnh 'Quét file thông minh…' của cửa sổ chính)
        self.b_quet_ny = QPushButton('Quét, căn cứ')       # một nút: thanh 4 thẻ không phải cuộn
        self.b_quet_ny.setFixedHeight(26)
        self.b_quet_ny.setToolTip('Quét hồ sơ chi tiết của hộ, file đơn giá đất, nhà, cây; Văn bản căn cứ của dự án. Đọc trên máy, xem trước kết quả rồi mới áp')
        m_q = QMenu(self.b_quet_ny)
        self.nut_quet = {}
        for ngu_canh, chu in (('DETAILED_HOUSEHOLD_DOSSIER', 'Quét hồ sơ chi tiết của hộ (đất, nhà, cây)…'), ('LAND_PRICE_TABLE', 'Quét file đơn giá đất…'), ('ASSET_CROP_PRICE_TABLE', 'Quét file đơn giá nhà, vật kiến trúc, cây trồng…')):
            self.nut_quet[ngu_canh] = m_q.addAction(chu, lambda nc=ngu_canh: self.quet_chung(nc))
        m_q.addSeparator()
        self.nut_can_cu = m_q.addAction('Văn bản căn cứ của dự án (13 bậc)…', lambda: self.van_ban_can_cu())
        self.b_quet_ny.setMenu(m_q)
        self._h_goc.addWidget(self.b_quet_ny)
        self._nut_goc.append((self.trang_ny, self.b_quet_ny))
        self.b_doc_kq.setEnabled(not chi_doc)
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
        # 30/10/2026 (người dùng): Hộ vướng cũng một chạm như cột Ý kiến - bấm ô "Nhóm vướng" (hoặc Space) đổi trạng thái
        self._vm_giu = set()                            # hộ vừa đổi sang Đủ điều kiện: vẫn hiện tới khi mở lại trang
        self.bang_vm.setToolTip('Bấm ô "Nhóm vướng" (hoặc phím Space) để đổi: Chưa đánh dấu → Đủ điều kiện → V1 … V5 → Chưa đánh dấu. '
                                'Bấm đúp ô khác để mở hộp đánh dấu pháp lý (ghi chú).')
        self.bang_vm.cellClicked.connect(lambda r, c: self._doi_vuong(r) if c == 3 else None)
        self.bang_vm.cellDoubleClicked.connect(lambda r, c: None if c == 3 else self._phap_ly())
        pv = QShortcut(QKeySequence(Qt.Key.Key_Space), self.bang_vm)
        pv.setContext(Qt.ShortcutContext.WidgetShortcut)
        pv.activated.connect(lambda: self._doi_vuong(self.bang_vm.currentRow()) if self.bang_vm.currentColumn() == 3 else None)
        self._phim_vm = pv
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

    def _muc_hien_tai(self) -> str:
        from .van_ban_dot import MUC
        return MUC[max(0, self.tabs.currentIndex())][0]

    def _can_dot(self):
        """Mã đợt đang chọn; đang xem Lũy kế: nhắc chọn một đợt."""
        d = self._dot_id()
        if d is None:
            self._bao('Chọn một đợt ở ô "Đợt" (văn bản, kết quả gắn với từng đợt, không gắn với Lũy kế).')
        return d

    def mo_van_ban(self, cho: bool = True):
        d = self._can_dot()
        if d is None:
            return None
        from .man_hinh_van_ban_dot import HopVanBanDot
        h = HopVanBanDot(self, self.con, d, self.cb.currentText(), self._muc_hien_tai(), self.chi_doc)
        if cho:
            h.exec()
        return h

    def van_ban_can_cu(self, cho: bool = True):
        from .man_hinh_quet_chung import HopVanBanCanCu
        d = HopVanBanCanCu(self, self.con, self.chi_doc)
        if cho:
            d.exec()
        return d

    def quet_chung(self, ngu_canh: str, files=None, doc=None, cho: bool = True):
        """Nút Quét của thẻ Niêm yết -> bộ quét dùng chung của cửa sổ chính (cùng hộp xem kết quả, cùng văn bản căn cứ 13 bậc)."""
        w = self.window()
        if not hasattr(w, 'quet_thong_minh'):
            return None
        return w.quet_thong_minh(files=files, cho=cho, ngu_canh=ngu_canh, doc=doc)

    def doc_ket_qua(self, files=None, cho: bool = True):
        """Đọc kết quả từ file vào mục đang mở: xem trước theo từng hộ rồi mới ghi. cho=False: trả hộp (kiểm thử)."""
        d = self._can_dot()
        if d is None:
            return None
        from . import ocr, van_ban_dot as vbd
        from .lap_pa import LoiNhap
        from .man_hinh_quan_ly import doc_co_tien_do
        from .man_hinh_van_ban_dot import LOC_FILE, HopKetQuaFile
        from .thong_bao import chu_loi
        if files is None:
            files, _ = QFileDialog.getOpenFileNames(self, 'Chọn file kết quả', '', LOC_FILE)
            if not files:
                return None
        try:
            kq = doc_co_tien_do(self, vbd.doc_ket_qua, self.con, d, files)
        except ocr.DaHuy:
            return None
        except (LoiNhap, OSError, ValueError, ocr.LoiOCR) as e:
            self._bao(chu_loi('Không đọc được file', e))
            return None
        if not kq['dong']:
            mau = '; '.join(kq.get('khong_khop', ())[:3])
            self._bao(f'Đọc {kq["tong_dong"]} dòng nhưng không dòng nào khớp với {kq.get("so_ho_dot", 0)} hộ của đợt đang chọn (đã thử mã định danh, CCCD, số thửa + tờ, '
                      f'họ tên). Xem lại đã chọn đúng đợt chưa, file có cột họ tên hoặc thửa không.' + (f'\nVí dụ dòng không khớp: {mau}' if mau else ''))
            return None
        h = HopKetQuaFile(self, self.con, d, self._muc_hien_tai(), list(files), kq)
        if not cho:
            return h
        if h.exec():
            self.nap()
            so_v2 = sum(1 for x in kq['dong'] if x.v2)
            self._bao(f'Đã ghi kết quả {h.so_ghi} hộ.' + (f' Tạo sẵn nhánh dự thảo V2 cho {so_v2} hộ có ý kiến khác (V1 giữ nguyên).' if so_v2 else ''))
        return h

    def _boc_the(self, trang):
        """Trang của thanh 4 thẻ: [hàng nút của thẻ] + nội dung. Hàng nút chuyển sang trang đang mở (_hien_nut_goc)."""
        w = QWidget()
        lo = QVBoxLayout(w)
        lo.setContentsMargins(0, 4, 0, 0)
        lo.setSpacing(4)
        lo.addWidget(trang, 1)
        self._ruot_the[w] = trang
        return w

    def _hien_nut_goc(self):
        bao = self.tabs.currentWidget()
        if bao is not None and self._goc_nut.parentWidget() is not bao:
            bao.layout().insertWidget(0, self._goc_nut)
            self._goc_nut.show()                        # đổi cha làm widget ẩn: hiện lại SAU khi vào bố cục (không thành cửa sổ lạ)
        hien = self._ruot_the.get(bao)
        the_ny = hien is self.ngan_ny
        if the_ny:
            hien = self.ngan_ny.currentWidget()
        self.khoi_bang_con.setVisible(the_ny)
        for trang, b in self._nut_goc:
            b.setVisible(trang is hien)
        for b in (self.b_van_ban, self.b_doc_kq):       # bảng hộ vướng chỉ có hai nút của nó
            b.setVisible(hien is not self.trang_vm)
        self._ve_nut_bang_con()

    def _tao_nut_bang_con(self):
        """Hai nút chuyển bảng con của thẻ Niêm yết, ở đầu hàng nút của thẻ."""
        from .giao_dien import QSS_NUT_BANG_CON
        self.khoi_bang_con = QWidget()
        h = QHBoxLayout(self.khoi_bang_con)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        self.nhom_bang_con = QButtonGroup(self)
        self.nut_bang_con = []
        for i, loai in enumerate(('ny', 'vuong')):
            b = QPushButton('')
            b.setObjectName('nut_bang_con')
            b.setProperty('loai', loai)
            b.setProperty('khong_icon', True)           # biểu tượng riêng (_ve_nut_bang_con), to_mau không gắn đè
            b.setCheckable(True)
            b.setFixedHeight(26)
            dat_kieu_theo_tong(b, QSS_NUT_BANG_CON)
            b.clicked.connect(lambda _=False, i=i: self.mo_bang_con(i))
            self.nhom_bang_con.addButton(b)
            self.nut_bang_con.append(b)
            h.addWidget(b)
        self.nut_bang_con[0].setChecked(True)
        self._h_goc.insertWidget(0, self.khoi_bang_con)

    def mo_bang_con(self, i: int):
        """Mở thẻ Niêm yết công khai ở bảng con i (0: hộ trong đợt, 1: hộ chưa đủ điều kiện / vướng)."""
        self.tabs.setCurrentIndex(0)
        self.ngan_ny.setCurrentIndex(i)
        self.nut_bang_con[i].setChecked(True)
        self._hien_nut_goc()

    def _ve_nut_bang_con(self):
        """Chữ (số hộ), màu cảnh báo, biểu tượng hai nút bảng con; hàng nút không đủ chỗ thì dùng chữ ngắn, đủ chữ ở chú thích."""
        from .giao_dien import MAU_NUT_BANG_CON, icon_ky_hieu
        so = (self.bang_ny.rowCount(), self.bang_vm.rowCount())
        day = (f'DS hộ niêm yết trong đợt ({so[0]})', f'Hộ chưa đủ ĐK / Vướng pháp lý ({so[1]})')
        ngan = (f'Hộ trong đợt ({so[0]})', f'Hộ vướng ({so[1]})')
        nut_khac = sum(b.sizeHint().width() + self._h_goc.spacing() for _, b in self._nut_goc if b.isVisibleTo(self._goc_nut))
        for b in (self.b_van_ban, self.b_doc_kq):
            if b.isVisibleTo(self._goc_nut):
                nut_khac += b.sizeHint().width() + self._h_goc.spacing()
        # đo theo chữ ĐẬM (nút đang chọn đậm hơn; sizeHint của Qt đo chữ thường: cắt ký tự cuối): biểu tượng + lề + viền
        f = QFont(self.nut_bang_con[0].font())
        f.setPixelSize(12)
        f.setBold(True)
        fm = QFontMetrics(f)
        rong_nut = lambda chu: fm.horizontalAdvance(chu) + 50    # noqa: E731
        can = nut_khac + 6 + sum(rong_nut(x) for x in day)
        rong = self._goc_nut.width() if self._goc_nut.isVisible() else self.width() - 16
        chu = day if can <= rong else ngan
        for i, b in enumerate(self.nut_bang_con):
            canh = '1' if i == 1 and so[1] > 0 else '0'
            if b.property('canh_bao') != canh:
                b.setProperty('canh_bao', canh)
                b.style().unpolish(b)
                b.style().polish(b)
            if b.text() != chu[i]:
                b.setText(chu[i])
            b.setMinimumWidth(rong_nut(chu[i]))
            b.setToolTip(day[i])
            k = 'chon' if b.isChecked() else ('canh' if canh == '1' else 'thuong')
            ic = icon_ky_hieu(0xE7BA if i else 0xE73E, MAU_NUT_BANG_CON[k], 14)   # Warning / CheckMark (Segoe MDL2): Win 7 không có phông: chỉ chữ
            if ic is not None:
                b.setIcon(ic)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._ve_nut_bang_con()

    def showEvent(self, e):
        super().showEvent(e)
        for b in (self.bang_ny, self.bang_yk, self.bang_dt, self.bang_th, self.bang_vm):   # cỡ chữ cuối (phóng to) đã áp
            san_tieu_de(b)

    def _trang(self, bang, nut):
        w = QWidget()
        lo = QVBoxLayout(w)
        lo.setContentsMargins(0, 2, 0, 0)
        # nút của thẻ / bảng con (Xuất biên bản đối thoại, Xuất báo cáo tổng hợp ý kiến, Chuyển hộ sang đợt sau…) ở hàng nút dưới thanh 4 thẻ, chỉ hiện khi đang mở
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
            for c, v in enumerate((i + 1, h['ho_ten'], h['so_cccd'] or '', h['thua'],
                                   vn(h['tien']) if h['tien'] is not None else '', dia)):
                o = _o(v)
                if c in (1, 3, 5):
                    o.setToolTip(str(v))
                if c in (0, 2, 3):
                    o.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif c == 4:
                    o.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    f = o.font()
                    f.setBold(True)
                    o.setFont(f)
                self.bang_ny.setItem(i, c, o)
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
        vm = du_thao.ds_vuong(self.con, getattr(self, '_vm_giu', ()))
        self.bang_vm.setRowCount(len(vm))
        for i, h in enumerate(vm):
            for c, v in enumerate((h['ma_ho'], h['ho_ten'], h['thua'], h['ten_vuong'], h['ghi_chu_phap_ly'])):
                self.bang_vm.setItem(i, c, _o(v))
            self.bang_vm.item(i, 0).setData(Qt.ItemDataRole.UserRole, h['ma_ho'])
        self._ve_nut_bang_con()
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
        from . import phien_ban_pa
        phien_ban_pa.khoa_v1_nhieu(self.con, ds, self.cb.currentText())    # 1.0.63: in dự thảo gửi dân = chốt V1, bản in lấy số V1
        return cha.in_xuat(cho=cho, ma_ho=ds, che_do='du_thao')

    def doi_chieu_phien_ban(self, cho: bool = True):
        """Bảng đối chiếu V1 | V2.n | V3 của các hộ trong đợt đang chọn (Mẫu 01-04, áp dụng đồng loạt)."""
        dot = self._can_dot()
        if dot is None:
            return None
        ds = [h['ma_ho'] for h in du_thao.ds_ho_dot(self.con, dot)]
        if not ds:
            self._bao('Đợt này chưa có hộ.')
            return None
        from .man_hinh_phien_ban import HopDoiChieu, xoa_hop_da_dong
        d = HopDoiChieu(self, self.con, ds, ds[0], self.chi_doc, dot)
        if not cho:
            return d
        d.exec()
        xoa_hop_da_dong(d)                            # bấm từ khung niêm yết không qua _chay_lenh: không tự xóa thì mỗi lần mở để lại một hộp ẩn giữ cả dữ liệu
        if d.da_doi:
            self.nap()
            cha = self.window()
            if hasattr(cha, 'tai_lai'):
                cha.tai_lai(giu_trang=True)
        return d

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
            them, bo = du_thao.them_thu_cong(self.con, dot, ds, ca_vuong=d.ca_chua())
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
        bd, kt, hop = du_thao.so_bien_ban(self.con, dot)
        ngay = QLineEdit(du_thao.hien_ngay(hop) if hop else '')
        ngay.setPlaceholderText('Ngày họp dân, sau khi hết 10 ngày niêm yết')
        o_bd, o_kt = QLineEdit(bd), QLineEdit(kt)
        o_bd.setPlaceholderText('Số biên bản bắt đầu niêm yết (không bắt buộc)')
        o_kt.setPlaceholderText('Số biên bản kết thúc niêm yết (không bắt buộc)')
        f = QFormLayout(d)
        f.addRow('Ngày họp:', ngay)
        f.addRow('Biên bản bắt đầu niêm yết số:', o_bd)
        f.addRow('Biên bản kết thúc niêm yết số:', o_kt)
        b = QPushButton('Ghi')
        b.clicked.connect(d.accept)
        f.addRow(b)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            han = du_thao.dat_ngay_hop(self.con, dot, ngay.text(), o_bd.text(), o_kt.text())
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

    def _doi_vuong(self, r: int):
        """Một chạm: đổi trạng thái pháp lý của hộ ở dòng r (bảng Hộ vướng), giữ dòng đang chọn. Trả trạng thái mới."""
        it = self.bang_vm.item(r, 0) if r >= 0 else None
        if self.chi_doc or it is None:
            return None
        ma = it.data(Qt.ItemDataRole.UserRole)
        try:
            tt = du_thao.doi_vuong_nhanh(self.con, ma)
        except du_thao.LoiNhap as e:
            self._loi(e)
            return None
        self._vm_giu.add(ma)
        self.thay_doi_csdl = True
        self._ve()
        for i in range(self.bang_vm.rowCount()):
            o = self.bang_vm.item(i, 0)
            if o is not None and o.data(Qt.ItemDataRole.UserRole) == ma:
                self.bang_vm.setCurrentCell(i, 3)
                break
        return tt

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
        ho = next(h for h in du_thao.ds_vuong(self.con, self._vm_giu | {ds[0]}) if h['ma_ho'] == ds[0])
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
        from .csdl import duong_goi_y
        p, _ = QFileDialog.getSaveFileName(self, tieu_de, duong_goi_y(self.con, tieu_de + '.xlsx'), 'Excel (*.xlsx)')
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

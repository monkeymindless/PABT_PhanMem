"""Màn hình giai đoạn 2: Lập phương án hộ, chọn danh mục / giá tương đương, gợi ý hỗ trợ, thông tin dự án, rà soát giá.

Mọi quy tắc nằm trong lap_pa.BoSoan; ở đây chỉ hiển thị và chuyển thao tác của người dùng.
Các hàm thao tác nhận tham số tùy chọn (mục danh mục, tên, thửa...) để kiểm thử không cần bấm hộp thoại.
"""
from __future__ import annotations
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QKeySequence, QShortcut
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QRadioButton, QScrollArea, QSpinBox,
                               QHeaderView, QSplitter, QStyledItemDelegate, QTableWidget, QTableWidgetItem, QTabWidget,
                               QVBoxLayout, QWidget)

from . import lap_pa, nghiep_vu
from .lap_pa import NHOM_TIM, BoSoan, DanhMuc, LoiNhap, bo_dau
# in_an (kéo theo openpyxl ~0,2 giây) chỉ nạp trong hộp In / Xuất: mở dự án, cửa sổ lập phương án không phải chờ
from .nghiep_vu import DA_LAP_LUU, MUC_KHOAN, MUC_VN, NGUON_TAY, NGUON_TD, TEN_MUC, so_muc
from .tien import D, KHONG, lam_tron, so_luong_vn, so_vn, vn
from .giao_dien import con_tro_cho, loc_khi_ngung_go
from .thong_bao import TEN_UD, chu_loi

XAM, VANG, CAM = QColor('#F4F6F8'), QColor('#FFF6D6'), QColor('#FDEBDD')
COT_SO = {'dien_tich', 'gia_bang_gia', 'he_so_k', 'ty_le', 'thanh_tien', 'so_luong', 'don_gia'}

COT_GD = {
    1: [('thua', 'Thửa', 130), ('loai_dat', 'Loại đất', 70), ('dien_tich', 'DT thu hồi (m²)', 100), ('vi_tri', 'Vị trí', 260),
        ('gia_bang_gia', 'Giá đất (đ/m²)', 110), ('he_so_k', 'Hệ số K', 65), ('ty_le', 'Tỷ lệ %', 60),
        ('thanh_tien', 'Thành tiền (đ)', 120), ('ghi_chu', 'Ghi chú', 220)],
}
for _m in (2, 3, MUC_VN):
    COT_GD[_m] = [('ma', 'Mã', 60), ('ten', {2: 'Tên nhà, công trình, tài sản', 3: 'Tên cây trồng', MUC_VN: 'Tên vật nuôi'}[_m], 340),
                  ('dvt', 'ĐVT', 70), ('so_luong', 'Số lượng', 85), ('don_gia', 'Đơn giá (đ)', 110), ('ty_le', 'Tỷ lệ %', 60),
                  ('thanh_tien', 'Thành tiền (đ)', 120), ('nguon', 'Nguồn giá', 110), ('quy_cach', 'Quy cách', 170),
                  ('ghi_chu', 'Ghi chú (quy định, cách tính)', 240), ('can_cu_gia', 'Căn cứ giá', 200)]
COT_GD[4] = [('ma', 'Mã', 60), ('ten', 'Chính sách hỗ trợ', 300), ('cach_tinh', 'Cách tính', 280), ('dvt', 'ĐVT', 70),
             ('so_luong', 'Số lượng', 80), ('don_gia', 'Đơn giá (đ)', 110), ('ty_le', 'Tỷ lệ %', 60),
             ('thanh_tien', 'Thành tiền (đ)', 120), ('ghi_chu', 'Ghi chú (căn cứ)', 280)]
# thẻ của cửa sổ lập phương án: chỉ số thẻ -> mục (0 = hồ sơ hộ). Từ 0.9.21 vật nuôi là thẻ 4 (mục MUC_VN), hỗ trợ thẻ 5 (mục 4)
# 0.9.95 (đặc tả Ultra-Compact): cột ngắn bề rộng gọn; cột chữ (tên, cách tính, quy cách, ghi chú, vị trí) GIÃN chia phần còn lại -
# hết thanh cuộn ngang thừa. Cột vẫn không hẹp hơn chữ tiêu đề (giao_dien.san_tieu_de)
# 0.9.96: Ghi chú / Quy cách thường trống -> bề rộng gọn (không giãn, tiêu đề vẫn đủ chữ nhờ san_tieu_de); phần còn lại giãn cho
# Tên / Vị trí / Chính sách / Cách tính
RONG_COT_GON = {'ma': 52, 'dvt': 55, 'so_luong': 72, 'don_gia': 92, 'ty_le': 54, 'thanh_tien': 105, 'nguon': 68,
                'quy_cach': 110, 'ghi_chu': 150, 'can_cu_gia': 150}
COT_GIAN = ('ten', 'cach_tinh', 'vi_tri')
CAO_NUT_DONG = 24                  # nút thao tác dòng (Xóa dòng, Lên, Xuống…) gọn
THE_MUC = (0, 1, 2, 3, MUC_VN, 4)
TEN_TAB = {0: 'Thông tin hộ, thửa đất', 1: '1. Đất', 2: '2. Nhà, công trình', 3: '3. Cây trồng', 4: '4. Vật nuôi',
           5: '5. Hỗ trợ'}                  # theo chỉ số thẻ


def the_cua(muc: int) -> int:
    """Chỉ số thẻ của một mục (mục 4 hỗ trợ = thẻ 5, vật nuôi = thẻ 4)."""
    return THE_MUC.index(muc)


def _hoi(parent, tieu_de, noi_dung):
    """Lưu / Không lưu / Hủy -> 'luu' / 'bo' / None."""
    nut = QMessageBox.question(parent, tieu_de, noi_dung,
                               QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                               QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Save)
    if nut == QMessageBox.StandardButton.Save:
        return 'luu'
    if nut == QMessageBox.StandardButton.Discard:
        return 'bo'
    return None


# ---------------------------------------------------------------- chọn mục danh mục
class ChonDanhMuc(QDialog):
    """Tìm và chọn một mục trong danh mục đơn giá (thêm dòng, hoặc chọn giá tương đương)."""

    def __init__(self, dm: DanhMuc, nhom: int, parent=None, tuong_duong: bool = False, tu_khoa: str = ''):
        super().__init__(parent)
        self.dm = dm
        self.chon = None
        self.setWindowTitle('Chọn giá tương đương' if tuong_duong else 'Chọn từ danh mục đơn giá')
        self.resize(1050, 600)
        self.cb_nhom = QComboBox()
        ds_nhom = [2, 3, MUC_VN, 4, 9] if tuong_duong else ([nhom, 9] if nhom in (2, 3, MUC_VN) else [nhom])
        for n in ds_nhom:
            self.cb_nhom.addItem(NHOM_TIM[n], n)
        self.cb_nhom.setCurrentIndex(max(0, ds_nhom.index(nhom)) if nhom in ds_nhom else 0)
        self.o_tim = QLineEdit(tu_khoa)
        self.o_tim.setPlaceholderText('Gõ từ khóa, không cần dấu (ví dụ: xoai 11-15, mai che, tu lo cho o)…')
        self.o_tim.setClearButtonEnabled(True)
        self.lb_dem = QLabel('')
        self.bang = QTableWidget(0, 6)
        self.bang.setHorizontalHeaderLabels(['Mã', 'Tên', 'ĐVT', 'Đơn giá (đ)', 'Quy cách theo chu vi', 'Phân loại / căn cứ'])
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.verticalHeader().setVisible(False)
        for i, w in enumerate((70, 420, 60, 100, 170, 260)):
            self.bang.setColumnWidth(i, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.doubleClicked.connect(lambda *_: self.accept())
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText('Chọn' if not tuong_duong else 'Áp dụng giá này')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        hang = QHBoxLayout()
        hang.addWidget(QLabel('Nhóm:'))
        hang.addWidget(self.cb_nhom)
        hang.addWidget(QLabel('Tìm:'))
        hang.addWidget(self.o_tim, 1)
        hang.addWidget(self.lb_dem)
        lo = QVBoxLayout(self)
        if tuong_duong:
            ghi = QLabel('Đơn giá và ĐVT lấy theo mục được chọn; tên in ra vẫn là tên đã gõ. Nhóm "Quy ước tương đương" là các trường '
                         'hợp đã thống nhất áp giá trước đây.')
            ghi.setWordWrap(True)
            lo.addWidget(ghi)
        lo.addLayout(hang)
        lo.addWidget(self.bang)
        lo.addWidget(nut)
        self.ket_qua = []
        loc_khi_ngung_go(self.o_tim, self.tim)
        self.cb_nhom.currentIndexChanged.connect(self.tim)
        self.tim()
        self.o_tim.setFocus()

    def tim(self, *_):
        from .cay_trong import mo_ta_chu_vi
        self.ket_qua = self.dm.tim(self.cb_nhom.currentData(), self.o_tim.text())
        self.bang.setRowCount(len(self.ket_qua))
        for r, m in enumerate(self.ket_qua):
            gia = vn(m.don_gia) if m.don_gia is not None else '(chưa có)'
            cv = mo_ta_chu_vi(m.ten) if m.nhom == 3 else ''
            for c, v in enumerate((m.ma, m.ten, m.dvt, gia, cv, m.phan_loai or m.can_cu)):
                it = QTableWidgetItem(str(v or ''))
                if c == 3:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                it.setToolTip(str(v or ''))
                self.bang.setItem(r, c, it)
        self.lb_dem.setText(f'{len(self.ket_qua)} mục' + (' (hiện 300 mục đầu)' if len(self.ket_qua) >= 300 else ''))
        if self.ket_qua:
            self.bang.selectRow(0)

    def chon_hien_tai(self):
        r = self.bang.currentRow()
        return self.ket_qua[r] if 0 <= r < len(self.ket_qua) else None

    def accept(self):
        self.chon = self.chon_hien_tai()
        if self.chon is None:
            return
        super().accept()


# ---------------------------------------------------------------- gợi ý hỗ trợ
class HopGoiY(QDialog):
    def __init__(self, de_xuat: list, tu_xac_dinh: list, parent=None):
        super().__init__(parent)
        self.de_xuat = de_xuat
        self.setWindowTitle('Gợi ý các khoản hỗ trợ (QĐ 42/2025/QĐ-UBND)')
        self.resize(900, 480)
        lo = QVBoxLayout(self)
        lo.addWidget(QLabel('<b>Đánh dấu các khoản muốn áp dụng</b> (số lượng, đơn giá vẫn sửa được sau khi áp dụng):'))
        self.ds = QListWidget()
        for x in de_xuat:
            sl = so_vn(x.so_luong) if x.so_luong is not None else '?'
            dg = vn(x.don_gia) if x.don_gia is not None else '?'
            it = QListWidgetItem(f'{x.viec.capitalize()} {x.ma}: SL {sl} × ĐG {dg} đ  –  {x.ly_do}')
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked)
            self.ds.addItem(it)
        if not de_xuat:
            self.ds.addItem('Không có khoản nào cần thêm hoặc sửa theo số liệu hiện có của hộ.')
        lo.addWidget(self.ds)
        if tu_xac_dinh:
            ghi = QLabel('<b>Người lập tự xác định:</b><br>' + '<br>'.join('• ' + t for t in tu_xac_dinh))
            ghi.setWordWrap(True)
            lo.addWidget(ghi)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText('Áp dụng')
        nut.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(de_xuat))
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Đóng')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo.addWidget(nut)

    def da_chon(self) -> list:
        return [x for i, x in enumerate(self.de_xuat) if self.ds.item(i).checkState() == Qt.CheckState.Checked]


# ---------------------------------------------------------------- ô bảng: danh sách xổ xuống, chữ nhiều dòng
class XoXuongDong(QStyledItemDelegate):
    """Ô có danh sách xổ xuống lấy theo từng dòng (thửa của hộ, vị trí NQ 28...). Chọn / gõ xong gọi goi(dòng, giá trị):
    giá trị là dữ liệu của mục được chọn, hoặc chữ gõ tay (sua_tay=True)."""

    def __init__(self, ds_cua_dong, goi, sua_tay: bool = True, parent=None):
        super().__init__(parent)
        self.ds_cua_dong, self.goi, self.sua_tay = ds_cua_dong, goi, sua_tay

    def paint(self, p, option, index):
        from .giao_dien import ve_mui_ten
        ve_mui_ten(super(), p, option, index)        # mũi tên ▾: ô có danh sách chọn

    def editorEvent(self, event, model, option, index):
        from .giao_dien import nhap_mot_lan
        return nhap_mot_lan(self, event, option, index) or super().editorEvent(event, model, option, index)

    def createEditor(self, parent, option, index):
        from PySide6.QtWidgets import QCompleter
        from .giao_dien import HopXo
        cb = HopXo(parent)
        cb.setEditable(self.sua_tay)
        cb.setMaxVisibleItems(14)
        for nhan, gt in self.ds_cua_dong(index.row()):
            cb.addItem(nhan, gt)
        if self.sua_tay:
            cb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            g = QCompleter(cb.model(), cb)
            g.setFilterMode(Qt.MatchFlag.MatchContains)
            g.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            g.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            cb.setCompleter(g)
        if cb.count() <= 40:
            cb.view().setMinimumWidth(min(max(cb.view().sizeHintForColumn(0) + 30, 260), 720))
        else:
            cb.view().setMinimumWidth(560)
        from .giao_dien import mo_danh_sach
        mo_danh_sach(cb)                              # mở ô là hiện luôn danh sách
        return cb

    def setEditorData(self, cb, index):
        v = str(index.data() or '')
        i = cb.findText(v)
        # chữ đang có không thuộc danh sách: danh sách mở từ dòng đầu (chỉ số -1 làm danh sách mở ở cuối - người dùng tưởng
        # thiếu các tuyến đường phía trên); ô vẫn giữ chữ cũ (setEditText) nên đóng lại không đổi gì
        cb.setCurrentIndex(i if i >= 0 or not self.sua_tay else 0)
        if self.sua_tay:
            cb.setEditText(v)

    def setModelData(self, cb, model, index):
        cu = str(index.data() or '')
        chu = cb.currentText().strip()
        if chu == cu:
            return
        i = cb.findText(chu)
        gt = cb.itemData(i) if i >= 0 else (chu if self.sua_tay else None)
        if gt is None:
            return
        r = index.row()
        QTimer.singleShot(0, lambda: self.goi(r, gt))          # vẽ lại dòng sau khi ô sửa đã đóng


class ChuNhieuDong(QStyledItemDelegate):
    """Ô chữ dài (tên tài sản, quy cách, căn cứ, ghi chú): sửa trong khung nhiều dòng, Enter để ghi (Shift+Enter xuống dòng)."""

    def createEditor(self, parent, option, index):
        o = QPlainTextEdit(parent)
        o.setTabChangesFocus(True)
        return o

    def setEditorData(self, o, index):
        o.setPlainText(str(index.data() or ''))
        o.selectAll()

    def setModelData(self, o, model, index):
        model.setData(index, ' '.join(o.toPlainText().split()))

    def updateEditorGeometry(self, o, option, index):
        # khung sửa cao vừa đủ: không thấp hơn 32, tối đa max(64, chiều cao dòng) - trước đây 64 cố định đè xuống dòng dưới
        r = option.rect
        doc = o.document()
        doc.setTextWidth(max(20, r.width() - 12))
        can = int(doc.size().height()) + 10                 # cao theo chữ đang sửa
        o.setMinimumHeight(32)
        o.setGeometry(r.x(), r.y(), r.width(), max(32, r.height(), min(can, max(64, r.height()))))

    def eventFilter(self, o, e):
        if e.type() == QEvent.Type.KeyPress and e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) \
                and not (e.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.commitData.emit(o)
            self.closeEditor.emit(o)
            return True
        return super().eventFilter(o, e)


class CongThucSo(QStyledItemDelegate):
    """Ô số lượng / diện tích: sửa ô thì hiện lại công thức đã gõ (=4,2*5,7) thay vì số đã tính, để biết số lượng từ đâu ra."""

    def setEditorData(self, editor, index):
        ct = index.data(Qt.ItemDataRole.UserRole)
        editor.setText(str(ct) if ct else str(index.data() or ''))
        editor.selectAll()


class HopChonNhieuThua(QDialog):
    """Chọn nhiều thửa của hộ đưa vào mục 1 (0.9.96): ô đánh dấu từng thửa, lọc theo Tờ / Loại đất, Ctrl+A chọn mọi thửa đang hiện.
    thua: [(ma_thua, so_to, so_thua, loai_dat, dt_con_lai, da_co_trong_muc_1)]. chon_ma() -> mã các thửa đã đánh dấu."""
    im_lang: bool = False
    COT = ('', 'Tờ', 'Thửa', 'Loại đất', 'DT còn lại (m²)', 'Đã có ở mục 1')

    def __init__(self, thua: list, parent=None):
        super().__init__(parent)
        from PySide6.QtGui import QKeySequence, QShortcut
        self.setWindowTitle('Chọn nhiều thửa đưa vào mục 1. Đất')
        self.resize(640, 520)
        self.thua = list(thua)
        self.cb_to, self.cb_ld = QComboBox(), QComboBox()
        for cb, tat_ca, gt in ((self.cb_to, 'Mọi tờ', {t[1] for t in self.thua}), (self.cb_ld, 'Mọi loại đất', {t[3] for t in self.thua})):
            cb.addItem(tat_ca, None)
            for v in sorted(gt, key=lambda x: (len(str(x)), str(x))):
                cb.addItem(str(v) or '(trống)', v)
            cb.currentIndexChanged.connect(lambda *_: self.loc())
        h = QHBoxLayout()
        for nhan, cb in (('Tờ:', self.cb_to), ('Loại đất:', self.cb_ld)):
            lb = QLabel(nhan)
            lb.setProperty('vai', 'nhan')
            h.addWidget(lb)
            h.addWidget(cb)
        h.addStretch(1)
        self.b_tat_ca = QPushButton('Chọn tất cả (Ctrl+A)')
        self.b_tat_ca.clicked.connect(lambda: self.danh_dau(True))
        self.b_bo = QPushButton('Bỏ chọn')
        self.b_bo.clicked.connect(lambda: self.danh_dau(False))
        h.addWidget(self.b_tat_ca)
        h.addWidget(self.b_bo)
        self.bang = QTableWidget(len(self.thua), len(self.COT))
        self.bang.setHorizontalHeaderLabels(list(self.COT))
        self.bang.verticalHeader().setVisible(False)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for r, (mt, to, so, ld, con_lai, da_co) in enumerate(self.thua):
            o = QTableWidgetItem()
            o.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            o.setCheckState(Qt.CheckState.Unchecked if da_co else Qt.CheckState.Checked)
            o.setData(Qt.ItemDataRole.UserRole, mt)
            self.bang.setItem(r, 0, o)
            for c, v in enumerate((to, so, ld, so_luong_vn(con_lai, 1), 'Có' if da_co else ''), start=1):
                it = QTableWidgetItem(str(v))
                if c == 4:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.bang.setItem(r, c, it)
        self.bang.setColumnWidth(0, 30)
        self.bang.horizontalHeader().setStretchLastSection(True)
        QShortcut(QKeySequence.StandardKey.SelectAll, self, activated=lambda: self.danh_dau(True))
        self.lb = QLabel('')
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText('Thêm vào mục 1')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        lo.addLayout(h)
        lo.addWidget(self.bang, 1)
        lo.addWidget(self.lb)
        lo.addWidget(nut)
        self.bang.itemChanged.connect(lambda *_: self._dem())
        self._dem()

    def loc(self) -> None:
        to, ld = self.cb_to.currentData(), self.cb_ld.currentData()
        for r, t in enumerate(self.thua):
            self.bang.setRowHidden(r, (to is not None and t[1] != to) or (ld is not None and t[3] != ld))
        self._dem()

    def danh_dau(self, chon: bool) -> None:
        """Đánh dấu / bỏ đánh dấu mọi thửa đang hiện (theo bộ lọc)."""
        self.bang.blockSignals(True)
        for r in range(self.bang.rowCount()):
            if not self.bang.isRowHidden(r):
                self.bang.item(r, 0).setCheckState(Qt.CheckState.Checked if chon else Qt.CheckState.Unchecked)
        self.bang.blockSignals(False)
        self._dem()

    def chon_ma(self) -> list:
        return [self.bang.item(r, 0).data(Qt.ItemDataRole.UserRole) for r in range(self.bang.rowCount())
                if not self.bang.isRowHidden(r) and self.bang.item(r, 0).checkState() == Qt.CheckState.Checked]

    def _dem(self) -> None:
        self.lb.setText(f'Đã chọn {len(self.chon_ma())} / {len(self.thua)} thửa.')


COT_CHU_DAI = {'ten', 'quy_cach', 'can_cu_gia', 'ghi_chu', 'cach_tinh'}
COT_CONG_THUC = {'so_luong', 'dien_tich'}
AP_NHIEU_DONG = {'loai_dat', 'vi_tri', 'gia_bang_gia', 'he_so_k', 'ty_le', 'ghi_chu'}   # mục 1: sửa một ô -> áp cho mọi dòng đã chọn
# hàng nhập nhanh + danh sách chọn: dùng chung với Dự toán & khái toán (0.9.67) - tên cũ giữ cho mã / test gọi từ man_hinh
from .hang_nhap_nhanh import KIEU_SL, HangNhapNhanh, ds_chon_nhanh, lam_san  # noqa: E402,F401


class BangMuc(QWidget):
    """Một thẻ mục: hàng nhập nhanh (chọn / gõ tên → số lượng → Thêm), bảng dòng phương án, nút Trở lại / Tiếp theo."""

    def __init__(self, man, muc: int):
        super().__init__()
        self.man, self.muc = man, muc
        self.cot = COT_GD[muc]
        self.bang = QTableWidget(0, len(self.cot))
        self.bang.setHorizontalHeaderLabels([c[1] for c in self.cot])
        hd = self.bang.horizontalHeader()
        hd.setStretchLastSection(False)
        for i, c in enumerate(self.cot):
            if c[0] in COT_GIAN:
                hd.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                self.bang.setColumnWidth(i, RONG_COT_GON.get(c[0], c[2]))
        from .giao_dien import san_tieu_de
        san_tieu_de(self.bang)
        hd.setMinimumHeight(30)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # mục 1: chọn nhiều dòng (Shift / Ctrl) để xóa hàng loạt, đặt cùng vị trí / giá / tỷ lệ cho các thửa đã chọn
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection if muc == 1
                                   else QAbstractItemView.SelectionMode.SingleSelection)
        self.bang.setAlternatingRowColors(True)
        self.bang.setWordWrap(True)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed |
                                  QAbstractItemView.EditTrigger.AnyKeyPressed)
        self.bang.cellChanged.connect(self._doi_o)
        khoa = [c[0] for c in self.cot]
        self._uy_quyen = []
        chu_dai = ChuNhieuDong(self.bang)
        self._uy_quyen.append(chu_dai)
        for k in COT_CHU_DAI & set(khoa):
            self.bang.setItemDelegateForColumn(khoa.index(k), chu_dai)
        cong_thuc = CongThucSo(self.bang)
        self._uy_quyen.append(cong_thuc)
        for k in COT_CONG_THUC & set(khoa):
            self.bang.setItemDelegateForColumn(khoa.index(k), cong_thuc)
        self.bang.currentCellChanged.connect(lambda r, c, *_: self._bao_cong_thuc(r, c))
        if muc == 1:
            for k, ds, goi, tay in (('thua', man.ds_thua_dong, man.doi_thua_dong, False),
                                    ('vi_tri', man.ds_vi_tri_dong, man.doi_vi_tri_dong, True)):
                u = XoXuongDong(ds, goi, tay, self.bang)
                self._uy_quyen.append(u)
                self.bang.setItemDelegateForColumn(khoa.index(k), u)
            # loại đất: xổ xuống các loại đất có giá trong danh mục của dự án (mã - tên), vẫn gõ mã được
            from .giao_dien import ChonXoXuong
            from .loai_dat import ds_chon
            u = ChonXoXuong(ds_chon(man.bo.con), self.bang)
            self._uy_quyen.append(u)
            self.bang.setItemDelegateForColumn(khoa.index('loai_dat'), u)
        # ---- hàng nhập nhanh
        nhap = QHBoxLayout()
        nhap.setSpacing(8)
        self.nut = {}
        if muc == 1:
            self.cb_thua = QComboBox()
            self.cb_thua.setMinimumWidth(260)
            nhan = QLabel('Thửa:')
            nhan.setProperty('vai', 'nhan')
            nhap.addWidget(nhan)
            nhap.addWidget(self.cb_thua, 1)
            b = QPushButton('Thêm thửa vào mục 1')
            b.clicked.connect(lambda: man.them_thua(self.cb_thua.currentData()) if self.cb_thua.count() else man.them_thua())
            nhap.addWidget(b)
            self.nut['Thêm thửa…'] = b
            # 0.9.96: thêm cả loạt thửa (hộ / tổ chức hàng trăm thửa - trước đây thêm từng thửa)
            self.b_them_tat_ca_thua = QPushButton('Thêm tất cả thửa')
            self.b_them_tat_ca_thua.setToolTip('Thêm một dòng mục 1 cho mỗi thửa của hộ chưa có trong mục 1 (loại đất, DT còn lại, vị trí, '
                                               'giá - giá 0 vẫn giữ loại đất)')
            self.b_them_tat_ca_thua.clicked.connect(lambda: man.them_tat_ca_thua())
            nhap.addWidget(self.b_them_tat_ca_thua)
            self.b_chon_nhieu_thua = QPushButton('Chọn nhiều thửa…')
            self.b_chon_nhieu_thua.setToolTip('Đánh dấu nhiều thửa (lọc theo tờ / loại đất, Ctrl+A chọn tất cả) rồi thêm vào mục 1')
            self.b_chon_nhieu_thua.clicked.connect(lambda: man.chon_nhieu_thua())
            nhap.addWidget(self.b_chon_nhieu_thua)
            # 0.9.75: tra giá đất NQ 28 ngay hàng nhập mục 1 (cạnh cột Vị trí của bảng): chọn dòng đất rồi tra
            b = QPushButton('Tra giá đất NQ 28…')
            b.setToolTip('Chọn dòng đất ở bảng rồi tra bảng giá đất Nghị quyết 28/2025: ghi vị trí và điền giá theo loại đất')
            b.clicked.connect(lambda: man.tra_gia_dat_nq28())
            nhap.addWidget(b)
            self.nut['Tra giá đất NQ 28…'] = b
        else:
            # hàng nhập nhanh DÙNG CHUNG với Dự toán & khái toán (hang_nhap_nhanh.HangNhapNhanh, 0.9.67); tên cũ giữ làm bí danh
            self.hang = HangNhapNhanh(lambda: man.them_nhanh(muc), muc=muc)
            self.hang.sau_chon = self._sau_chon
            if muc == MUC_VN:                            # danh mục chưa có vật nuôi: ▼ hỏi bổ sung từ bộ đơn giá
                self.hang.o_chon.khi_trong = lambda: man.bo_sung_vat_nuoi(hoi=True)
                self.hang.o_chon.goi_y_trong = ('Danh mục đơn giá của dự án chưa có vật nuôi: bấm "Bổ sung vật nuôi từ bộ đơn '
                                                'giá" phía dưới.')
            self.o_chon, self.o_sl, self.o_tl, self.o_gc = self.hang.o_chon, self.hang.o_sl, self.hang.o_tl, self.hang.o_gc
            self.cb_kieu = self.hang.cb_kieu
            self.nhan_tl = QLabel('')                        # (tỷ lệ ghi ngay trong ô)
            self.nhan_tl.setVisible(False)
            nhap.addWidget(self.hang, 1)
            self.nut['Thêm vào bảng'] = self.hang.nut_them
        # ---- nút thao tác dòng
        nut = QHBoxLayout()
        nut.setSpacing(6)
        ds = []
        if muc == 2:
            ds.append(('Kiểm tra DT xây dựng…', lambda: man.kiem_tra_dt_xay_dung()))
        if muc == 3:
            ds.append(('Tính mật độ…', lambda: man.tinh_mat_do()))
        ds += [('Xóa dòng', lambda: man.xoa_dong(muc)), ('▲ Lên', lambda: man.di_chuyen(muc, -1)),
               ('▼ Xuống', lambda: man.di_chuyen(muc, 1))]
        for ten, ham in ds:
            b = QPushButton(ten)
            b.clicked.connect(ham)
            b.setFixedHeight(CAO_NUT_DONG)
            b.setStyleSheet('QPushButton { padding: 1px 8px; }')
            nut.addWidget(b)
            self.nut[ten] = b
        nut.addStretch(1)
        self.lb_tong = QLabel('')
        self.lb_tong.setStyleSheet('QLabel { font-weight: bold; color: #1F4E79; }')
        nut.addWidget(self.lb_tong)
        nut.setContentsMargins(0, 0, 0, 0)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(6, 4, 6, 4)
        lo.setSpacing(4)
        if muc == 4:
            # một hàng: thông tin hộ dùng tính hỗ trợ + tình trạng tái định cư (gọn 26 px, lề 0)
            h = QHBoxLayout()
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            for w in (QLabel('Nhân khẩu:'), man.o_nk, man.o_di_chuyen, QLabel('DT đất NN đang dùng (m²):'),
                      man.o_dt_nn, man.lb_tl):
                if isinstance(w, QLabel) and w is not man.lb_tl:
                    w.setProperty('vai', 'nhan')
                h.addWidget(w)
            for w in (man.o_nk, man.o_dt_nn):
                w.setProperty('nhap', '1')
            nhan = QLabel('Tái định cư:')
            nhan.setProperty('vai', 'nhan')
            self.cb_tdc = QComboBox()
            self.cb_tdc.setEditable(True)
            self.cb_tdc.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            self.cb_tdc.addItems(lap_pa.TAI_DINH_CU)
            self.cb_tdc.setToolTip('Tái định cư là điều kiện của hộ (suất tái định cư), không phải khoản tiền: không đủ điều '
                                   'kiện, đủ điều kiện theo khoản 4 / khoản 5 Điều 111 Luật Đất đai năm 2024, hoặc không có.')
            self.cb_tdc.currentTextChanged.connect(lambda t: man.doi_tai_dinh_cu(t))
            self.cb_tdc.setProperty('nhap', '1')
            h.addSpacing(10)
            h.addWidget(nhan)
            h.addWidget(self.cb_tdc, 1)
            for i in range(h.count()):
                w = h.itemAt(i).widget()
                if w is not None:
                    w.setMaximumHeight(26)
            lo.addLayout(h)
        # 0.9.95: bỏ khung viền bao hàng nhập (lề 0); mục 1: nút thao tác dòng + "Cộng mục 1" lên CÙNG hàng chọn thửa
        khung_nhap = QWidget()
        khung_nhap.setObjectName('khung_nhap')
        if muc == 1:
            # 0.9.96: 3 khối xếp nối tiếp (chọn thửa | thêm nhiều thửa, tra giá | nút dòng + Cộng mục 1) - hẹp thì xuống dòng (một
            # hàng cứng cần ~1.480 điểm ở Windows 125%, rộng hơn màn hình 1366)
            from .giao_dien import XepDong
            ds_w = []
            while nhap.count():
                it = nhap.takeAt(0)
                if it.widget() is not None:
                    ds_w.append(it.widget())
            xd = XepDong(khung_nhap, 6)
            xd.setContentsMargins(0, 0, 0, 0)
            for nhom in (ds_w[:3], ds_w[3:]):
                k = QWidget()
                hk = QHBoxLayout(k)
                hk.setContentsMargins(0, 0, 0, 0)
                hk.setSpacing(6)
                for w in nhom:
                    hk.addWidget(w, 1 if w is self.cb_thua else 0)
                xd.addWidget(k)
            k = QWidget()
            k.setLayout(nut)
            xd.addWidget(k)
        else:
            nhap.setContentsMargins(0, 0, 0, 0)
            khung_nhap.setLayout(nhap)
        lo.addWidget(khung_nhap)
        if muc == MUC_VN:
            # dự án lập trước khi bộ đơn giá có vật nuôi (QĐ 31/2025): danh mục dự án không có dòng nào -> ô chọn trống
            self.khung_thieu_vn = QWidget()
            h = QHBoxLayout(self.khung_thieu_vn)
            h.setContentsMargins(0, 0, 0, 0)
            lb = QLabel('Danh mục đơn giá của dự án chưa có vật nuôi (dự án lập trước khi bộ đơn giá có QĐ 31/2025/QĐ-UBND).')
            lb.setWordWrap(True)
            lb.setStyleSheet('QLabel { color: #8A5A00; }')
            b = QPushButton('Bổ sung vật nuôi từ bộ đơn giá')
            b.setToolTip('Chỉ thêm các mục vật nuôi còn thiếu vào danh mục dự án - đơn giá khác của dự án giữ nguyên')
            b.clicked.connect(lambda: man.bo_sung_vat_nuoi())
            self.nut['Bổ sung vật nuôi từ bộ đơn giá'] = b
            h.addWidget(lb, 1)
            h.addWidget(b)
            self.khung_thieu_vn.setVisible(False)
            lo.addWidget(self.khung_thieu_vn)
        if muc == 1:
            self.cb_thua.setProperty('nhap', '1')
        if muc == 4:
            lo.addWidget(self._the_cach_tinh())
        if muc != 1:
            lo.addLayout(nut)
        lo.addWidget(self.bang, 1)
        # nút Trở lại / Tiếp theo: MỘT hàng chung dưới đáy cửa sổ, cùng dải tổng cộng (CuaSoLapPA.hang_dieu_huong)
        self.bang.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bang.customContextMenuRequested.connect(self.menu_dong)
        from .giao_dien import dat_dong_gon, nhap_bang_phim
        nhap_bang_phim(self.bang)                    # Tab / Enter đi giữa các ô, không cần chuột
        # dòng gọn 30-32 px, cao theo chữ thật (vua_dong) - ô Ghi chú / Quy cách trống không làm dòng cao 60-90 px
        dat_dong_gon(self.bang)
        self._hen_vua = QTimer(self)
        self._hen_vua.setSingleShot(True)
        self._hen_vua.setInterval(50)
        self._hen_vua.timeout.connect(self._vua_neu_doi_rong)
        self._rong_da_do = None
        self.bang.horizontalHeader().sectionResized.connect(lambda *a: self._hen_vua.start())
        # ô xổ có chữ dài (câu tái định cư, mô tả thửa): không bắt cửa sổ rộng theo chữ dài nhất
        for cb in self.findChildren(QComboBox):
            cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            cb.setMinimumContentsLength(14)
        if muc == 4:
            man.o_dt_nn.setMinimumWidth(130)
        self._dang_ve = False                        # thứ tự Tab của hàng nhập nhanh: HangNhapNhanh

    # ---------------------------------------------- mục 4: ô nhập theo cách tính của từng chính sách
    def _the_cach_tinh(self) -> QWidget:
        from PySide6.QtWidgets import QStackedWidget
        self.cs_loai = ''
        self.the_cs = QStackedWidget()

        def o_so(goi_y, rong=110):
            o = QLineEdit()
            o.setPlaceholderText(goi_y)
            o.setMaximumWidth(rong)
            o.setAlignment(Qt.AlignmentFlag.AlignRight)
            o.textChanged.connect(lambda *_: self.xem_cach_tinh())
            o.returnPressed.connect(lambda: self.man.them_nhanh(4))
            return o

        def hang(*ds):
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(8)
            for x in ds:
                if isinstance(x, str):
                    n = QLabel(x)
                    n.setProperty('vai', 'nhan')
                    h.addWidget(n)
                else:
                    h.addWidget(x)
            h.addStretch(1)
            return w
        self.the_cs.addWidget(QWidget())                                         # khoản khác: số lượng, tỷ lệ ở hàng trên
        self.o_gao, self.o_kg, self.o_thang_od, self.o_tl_od = o_so('16.450'), o_so('30', 60), o_so('6', 60), o_so('100', 60)
        self.lb_od = QLabel('')
        self.the_cs.addWidget(hang('Giá gạo (đ/kg):', self.o_gao, 'Số kg/khẩu/tháng:', self.o_kg, 'Số tháng:', self.o_thang_od,
                                   'Tỷ lệ %:', self.o_tl_od, self.lb_od))
        self.bang_dt = QTableWidget(0, 5)
        self.bang_dt.setHorizontalHeaderLabels(['Tính', 'Thửa đất nông nghiệp (mục 1)', 'Diện tích (m²)', 'Đơn giá đất (đ/m²)',
                                                'Tỷ lệ %'])
        for c, w in enumerate((44, 520, 110, 130, 80)):
            self.bang_dt.setColumnWidth(c, w)
        self.bang_dt.verticalHeader().setVisible(False)
        self.bang_dt.setMaximumHeight(150)
        self.bang_dt.setWordWrap(True)
        self.the_cs.addWidget(self.bang_dt)
        self.o_thang_tn, self.o_co_ban, self.o_them = o_so('số tháng', 80), o_so('mức hộ / tháng', 130), o_so('mức / khẩu', 120)
        self.lb_tn = QLabel('')
        self.lb_tn.setWordWrap(True)
        self.the_cs.addWidget(hang('Số tháng:', self.o_thang_tn, 'Mức hộ (đ/tháng):', self.o_co_ban,
                                   'Mỗi nhân khẩu tăng thêm (đ/tháng):', self.o_them, self.lb_tn))
        self.the_cs.setVisible(False)
        return self.the_cs

    def _dat_loai_cs(self, k: str):
        """Hiện ô nhập theo loại chính sách ('od' / 'dt' / 'tn' / '' khoản khác)."""
        self.cs_loai = k
        self.the_cs.setCurrentIndex({'': 0, 'od': 1, 'dt': 2, 'tn': 3}.get(k, 0))
        self.the_cs.setVisible(k in ('od', 'dt', 'tn'))
        for w in (self.o_sl, self.o_tl, self.nhan_tl):
            w.setVisible(k not in ('od', 'dt', 'tn'))

    def xem_cach_tinh(self):
        """Xem trước chuỗi cách tính / số tiền (ổn định đời sống, thuê nhà)."""
        from . import chinh_sach as cs
        bo = self.man.bo
        try:
            if self.cs_loai == 'od':
                nk = bo.pa.nhan_khau or 0
                gia, kg = lap_pa.doc_so(self.o_gao.text(), 'Giá gạo'), lap_pa.doc_so(self.o_kg.text(), 'Số kg')
                th = lap_pa.doc_so(self.o_thang_od.text(), 'Số tháng')
                tl = nghiep_vu.he_so(lap_pa.doc_ty_le(self.o_tl_od.text()))
                self.lb_od.setText(f'→ {cs.cach_tinh_on_dinh(nk, kg, th, gia, tl)} = '
                                   f'<b>{vn(lam_tron(nk * kg * gia * th * tl, bo.bc.lamtron))} đ</b>')
            elif self.cs_loai == 'tn':
                n = bo.bc.nguong_nk
                nk = bo.pa.nhan_khau or 0
                th = lap_pa.doc_so(self.o_thang_tn.text(), 'Số tháng')
                cb, them = lap_pa.doc_so(self.o_co_ban.text(), 'Mức hộ'), lap_pa.doc_so(self.o_them.text(), 'Mức mỗi khẩu')
                tien = th * (cb + them * max(int(nk) - n, 0))
                self.lb_tn.setText(f'→ {cs.cach_tinh_thue_nha(nk, th, cb, them, n)} = '
                                   f'<b>{vn(lam_tron(tien, bo.bc.lamtron))} đ</b>')
        except LoiNhap as e:
            (self.lb_od if self.cs_loai == 'od' else self.lb_tn).setText(f'<span style="color:#B8433A">{e}</span>')

    def nap_dao_tao(self, ma: str):
        from . import chinh_sach as cs
        bo = self.man.bo
        tl = so_vn(cs.ty_le_dao_tao(bo.bc, ma) * 100)
        ds = cs.ds_thua_nn(bo)
        self.bang_dt.setRowCount(len(ds))
        for r, x in enumerate(ds):
            ck = QTableWidgetItem('')
            ck.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            ck.setCheckState(Qt.CheckState.Checked)
            self.bang_dt.setItem(r, 0, ck)
            mt = QTableWidgetItem(x['mo_ta'])
            mt.setFlags(mt.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.bang_dt.setItem(r, 1, mt)
            for c, v in ((2, so_vn(x['dien_tich'])), (3, vn(x['don_gia'])), (4, tl)):
                it = QTableWidgetItem(v)
                it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.bang_dt.setItem(r, c, it)
        self.bang_dt.resizeRowsToContents()
        if not ds:
            self.man.thong_bao('Mục 1 chưa có thửa đất nông nghiệp: nhập mục 1 trước, hoặc gõ số lượng / đơn giá ở bảng sau khi thêm.')

    def nap_danh_sach(self):
        """Danh sách chọn nhanh của mục (theo danh mục đơn giá của dự án)."""
        dm = self.man.bo.dm
        if self.muc == 1:
            cu = self.cb_thua.currentData()
            self.cb_thua.clear()
            for mt, mo_ta, _ in self.man.bo.thua_cua_ho():
                self.cb_thua.addItem(mo_ta, mt)
            i = self.cb_thua.findData(cu)
            self.cb_thua.setCurrentIndex(max(i, 0))
            return
        self.hang.nap(dm)
        if self.muc == MUC_VN:
            self.khung_thieu_vn.setVisible(not dm.muc[MUC_VN])

    def _da_chon(self, m):
        """Chọn một mục ở hàng nhập nhanh (gọi thẳng khi kiểm thử): HangNhapNhanh xử lý kiểu số đo cây rồi gọi _sau_chon."""
        self.hang._da_chon(m)

    def _sau_chon(self, m) -> bool:
        """Mục 4 của hộ: ô theo cách tính của chính sách (ổn định đời sống, đào tạo nghề, thuê nhà), gợi ý số lượng.
        True = đã tự đặt con trỏ (HangNhapNhanh không chuyển về ô số lượng)."""
        if self.muc != 4:
            return False
        from . import chinh_sach as cs
        bo = self.man.bo
        k = cs.loai(m.ma) if m is not None and not isinstance(m, tuple) else ''
        self._dat_loai_cs(k)
        if m is not None and not isinstance(m, tuple):
            self.o_gc.setText(cs.can_cu_ghi_chu(m.can_cu))
            self.o_gc.setCursorPosition(0)
        if k == 'od':
            d = cs.mac_dinh_on_dinh(bo.bc, m.ten)
            self.o_gao.setText(vn(d['gia_gao']))
            self.o_kg.setText(so_vn(d['kg']))
            self.o_thang_od.setText(so_vn(d['thang']))
            self.o_tl_od.setText(so_vn(d['ty_le'] * 100))
            self.xem_cach_tinh()
            self.man.o_nk.setFocus()
            return True
        if k == 'dt':
            self.nap_dao_tao(m.ma)
            return True
        if k == 'tn':
            cb, them, _ = cs.gia_thue_nha(bo.bc, m.ma)
            self.o_co_ban.setText(vn(cb))
            self.o_them.setText(vn(them))
            self.o_thang_tn.setText(so_vn(bo.bc.so_ts('TULO_THANG') or 6) if m.ma in ('CS17', 'CS18') else '')
            self.xem_cach_tinh()
            self.o_thang_tn.setFocus()
            return True
        if m is not None and not isinstance(m, tuple) and not self.o_sl.text().strip():
            from .nghiep_vu import goi_y_khoan
            g = goi_y_khoan(bo.pa, bo.bc, m.ma)
            if g.so_luong is not None:
                self.o_sl.setText(so_vn(g.so_luong))
        return False

    def xoa_nhap(self):
        if self.muc != 1:
            if self.muc == 4:
                self._dat_loai_cs('')
            self.hang.xoa()

    def menu_dong(self, pos=None) -> QMenu:
        """Menu chuột phải của bảng mục (16/10/2026): thêm / nhân bản / xóa / di chuyển dòng, chép ô, và lệnh riêng của mục (mục 1:
        thêm nhiều thửa, tra giá NQ 28, chọn mọi dòng; mục 2: kiểm tra DT xây dựng, tách trong / ngoài ranh; mục 3: tính mật độ).
        pos None: chỉ dựng menu (kiểm thử), không hiện."""
        man, muc, b = self.man, self.muc, self.bang
        if pos is not None:
            r = b.rowAt(pos.y())
            if r >= 0 and r not in self.cac_dong_chon():            # bấm phải ngoài vùng chọn: chọn dòng dưới con trỏ
                b.selectRow(r)
        chon = self.cac_dong_chon()
        co = bool(chon)
        m = QMenu(self)

        def them(chu, ham, bat=True):
            a = m.addAction(chu)
            a.setEnabled(bat)
            a.triggered.connect(lambda *_: ham())
            return a
        if muc == 1:
            them('Thêm thửa vào mục 1…', lambda: man.them_thua())
            them('Thêm tất cả thửa', lambda: man.them_tat_ca_thua())
            them('Chọn nhiều thửa…', lambda: man.chon_nhieu_thua())
        else:
            them('Thêm dòng (ô nhập nhanh)', lambda: self.hang.o_chon.setFocus())
        them('Nhân bản dòng', lambda: man.nhan_ban_dong(muc), len(chon) == 1)
        them(f'Xóa {len(chon)} dòng đã chọn' if len(chon) > 1 else 'Xóa dòng', lambda: man.xoa_dong(muc), co)
        m.addSeparator()
        them('▲ Lên', lambda: man.di_chuyen(muc, -1), len(chon) == 1)
        them('▼ Xuống', lambda: man.di_chuyen(muc, 1), len(chon) == 1)
        m.addSeparator()
        them('Chép nội dung ô', lambda: self.chep_o(), b.currentItem() is not None)
        if muc == 1:
            them('Chọn mọi dòng (Ctrl+A)', lambda: b.selectAll(), b.rowCount() > 0)
            m.addSeparator()
            them('Tra giá đất NQ 28…', lambda: man.tra_gia_dat_nq28(), len(chon) == 1)
        elif muc == 2:
            m.addSeparator()
            them('Kiểm tra DT xây dựng…', lambda: man.kiem_tra_dt_xay_dung())
            them('Tách phần trong / ngoài ranh thu hồi…', lambda: man.tach_ranh(), len(chon) == 1)
        elif muc == 3:
            m.addSeparator()
            them('Tính mật độ…', lambda: man.tinh_mat_do(), len(chon) == 1)
        if pos is not None:
            m.exec(b.viewport().mapToGlobal(pos))
            m.deleteLater()
        return m

    def chep_o(self) -> str:
        it = self.bang.currentItem()
        chu = it.text() if it is not None else ''
        QApplication.clipboard().setText(chu)
        return chu

    def dong_chon(self) -> int:
        return self.bang.currentRow()

    def cac_dong_chon(self) -> list:
        """Các dòng đang chọn (tăng dần); không chọn dòng nào thì dòng hiện tại."""
        ds = sorted({i.row() for i in self.bang.selectionModel().selectedRows()})
        if not ds and self.bang.currentRow() >= 0:
            ds = [self.bang.currentRow()]
        return ds

    def ve(self, chon: int | None = None):
        bo = self.man.bo
        n = len(bo.ds(self.muc))
        self._dang_ve = True
        try:
            self.bang.setRowCount(n)
            for r in range(n):
                self._ve_dong(r)
        finally:
            self._dang_ve = False
        self.vua_dong()
        if chon is not None and 0 <= chon < n:
            self.bang.setCurrentCell(chon, 1)

    def vua_dong(self):
        """Chiều cao mọi dòng theo chữ thật trên bề rộng cột hiện tại (30-88 px)."""
        from .giao_dien import vua_dong
        vua_dong(self.bang)
        self._rong_da_do = self._rong_cot()

    def _rong_cot(self) -> tuple:
        return tuple(self.bang.columnWidth(c) for c in range(self.bang.columnCount()))

    def _vua_neu_doi_rong(self):
        """Đổi cỡ / hiện lại thẻ: chỉ đo lại khi bề rộng cột thật sự đổi (quay lại thẻ 300 dòng không tốn ~60 ms mỗi lần)."""
        if self._rong_cot() != self._rong_da_do:
            self.vua_dong()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._hen_vua.start()                        # cột giãn đổi bề rộng: đo lại sau 50 ms (kéo cửa sổ không đo liên tục)

    def _ve_dong(self, r: int):
        bo = self.man.bo
        o = bo.o_dat(r) if self.muc == 1 else bo.o_khoan(self.muc, r)
        sua = lap_pa.SUA_DUOC_DAT if self.muc == 1 else lap_pa.SUA_DUOC_KHOAN
        nguon = '' if self.muc == 1 else bo.pa.khoan[self.muc][r].nguon_gia
        cu = self._dang_ve
        self._dang_ve = True
        try:
            for c, (k, _, _) in enumerate(self.cot):
                it = QTableWidgetItem(str(o.get(k, '')))
                if k in COT_SO:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if k not in sua:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    it.setBackground(QBrush(XAM))
                if k == 'nguon' and nguon == NGUON_TD:
                    it.setBackground(QBrush(VANG))
                elif k == 'nguon' and nguon == NGUON_TAY:
                    it.setBackground(QBrush(CAM))
                if k == 'thanh_tien':
                    f = QFont()
                    f.setBold(True)
                    it.setFont(f)
                if k in ('ten', 'can_cu_gia', 'quy_cach', 'ghi_chu', 'thua', 'vi_tri'):
                    it.setToolTip(str(o.get(k, '')))
                if k in COT_CONG_THUC and o.get('cong_thuc'):
                    it.setData(Qt.ItemDataRole.UserRole, o['cong_thuc'])          # sửa ô: hiện lại công thức
                    it.setToolTip(f'Công thức: {o["cong_thuc"]} = {o[k]}')
                    it.setForeground(QBrush(QColor('#1F5FA0')))
                self.bang.setItem(r, c, it)
        finally:
            self._dang_ve = cu
        if not cu:
            from .giao_dien import cao_can_dong
            self.bang.setRowHeight(r, cao_can_dong(self.bang, r))

    def _bao_cong_thuc(self, r: int, c: int):
        """Chọn ô số lượng / diện tích: dòng thông báo cho biết số / công thức đã nhập ra số đó."""
        if self._dang_ve or not (0 <= c < len(self.cot)) or self.cot[c][0] not in COT_CONG_THUC:
            return
        it = self.bang.item(r, c)
        if it is None:
            return
        ct = it.data(Qt.ItemDataRole.UserRole)
        ten = self.cot[c][1]
        sm = so_muc(self.muc)
        self.man.thong_bao(f'Dòng {sm}.{r + 1} – {ten}: {ct} = {it.text()}' if ct else
                           f'Dòng {sm}.{r + 1} – {ten}: {it.text()} (gõ số trực tiếp)')

    def _doi_o(self, r: int, c: int):
        if self._dang_ve:
            return
        self.man.sua_o(self.muc, r, self.cot[c][0], self.bang.item(r, c).text())


# ---------------------------------------------------------------- màn hình lập phương án hộ
TB_QUET_HO_SO = 'Tiện ích đang trong quá trình hoàn thiện'
CLIP_TOI_DA = 200_000        # clipboard dài hơn (cả một tài liệu) không tự điền vào hộp Dán danh sách: phân loại sẽ đơ
QSS_NUT_DAN_TS = ('QPushButton#btn_dan_ts { background: #0284C7; color: #FFFFFF; font-weight: 700; border: none; '
                  'border-radius: 6px; padding: 0 14px; }'
                  'QPushButton#btn_dan_ts:hover { background: #0369A1; }'
                  'QPushButton#btn_dan_ts:pressed { background: #075985; }')


RONG_XEM_TOI_THIEU = 320          # màn hình hẹp: khung xem trước CuaSoLapPA không hẹp hơn chừng này
CHO_XEM_SAU_SUA_MS = 1500          # khung xem trước đang hiện: sửa số liệu xong chừng này mới nhờ Excel lập lại bản in
QSS_NUT_XEM_TRUOC = ('QPushButton#btn_toggle_preview { color: #FFFFFF; background: #0F3866; border: 1px solid #2563EB; '
                     'border-radius: 6px; padding: 4px 12px; font-weight: 600; }'
                     'QPushButton#btn_toggle_preview:hover { background: #16467E; }'
                     'QPushButton#btn_toggle_preview:checked { background: #2563EB; border-color: #93C5FD; }')


CAO_NUT_TREN = 27                  # 0.9.95: hàng trên cùng cửa sổ lập phương án (chọn hộ + nút lệnh) một hàng 27 px


class CuaSoLapPA(QDialog):
    """Hồ sơ và phương án một hộ trong một cửa sổ: thẻ 0 thông tin hộ, thửa đất → 1 đất → 2 nhà, công trình → 3 cây trồng →
    4 vật nuôi → 5 hỗ trợ (Tiếp theo / Trở lại). self.bang theo MỤC (bang[4] = hỗ trợ, bang[MUC_VN] = vật nuôi), thẻ: the_cua."""

    def __init__(self, con, ma_ho: int, parent=None, danh_muc: DanhMuc | None = None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.resize(1360, 840)
        self.bo = BoSoan(con, ma_ho, danh_muc)
        self.da_luu = False
        self.thay_doi_csdl = False
        # ---- dòng chọn hộ
        self.cb_ho = QComboBox()
        self.cb_ho.setMinimumWidth(190)             # 0.9.95: ô chọn hộ 190-270 px, cùng hàng với các nút lệnh
        self.cb_ho.setMaximumWidth(270)
        self.cb_ho.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cb_ho.setMinimumContentsLength(14)
        self.cb_ho.setEditable(True)
        self.cb_ho.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._nap_ds_ho()
        self.cb_ho.activated.connect(self._chon_ho_tu_hop)
        self.b_truoc = QPushButton('◀')
        self.b_sau = QPushButton('▶')
        self.b_truoc.clicked.connect(lambda: self.sang_ho(-1))
        self.b_sau.clicked.connect(lambda: self.sang_ho(1))
        self.b_truoc.setToolTip('Hộ trước (Ctrl+Left, Ctrl+PgUp)')
        self.b_sau.setToolTip('Hộ sau (Ctrl+Right, Ctrl+PgDn)')
        for b in (self.b_truoc, self.b_sau):
            b.setFixedWidth(32)
        self.b_goi_y = QPushButton('Gợi ý hỗ trợ…')
        self.b_goi_y.clicked.connect(lambda: self.goi_y())
        self.b_dan = self.btn_dan_ts = QPushButton('Dán danh sách tài sản…')   # 0.9.95: phím tắt ở chú thích (hàng gọn)
        self.b_dan.setObjectName('btn_dan_ts')
        self.b_dan.setToolTip('Ctrl+Shift+V. Dán / gõ nhiều dòng tài sản (Tên, ĐVT, Số lượng…): phần mềm tự xếp vào Nhà, công trình / Cây trồng / '
                              'Vật nuôi / Hỗ trợ theo bộ đơn giá. Đang có bảng tài sản trong bộ nhớ đệm (Excel, Word…) thì tự điền '
                              'và phân loại ngay khi mở.')
        self.b_dan.setFixedHeight(CAO_NUT_TREN)
        self.b_dan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_dan.setStyleSheet(QSS_NUT_DAN_TS)        # có bộ chọn #btn_dan_ts: không truyền sang tooltip của nút
        self.b_dan.setProperty('khong_icon', True)      # to_mau không gắn biểu tượng màu nhóm đè lên nền xanh
        from .giao_dien import icon_ky_hieu
        ic = icon_ky_hieu(0xE77F, '#FFFFFF', 16)        # Paste (Segoe MDL2); máy không có phông (Win 7): chỉ chữ
        if ic is not None:
            self.b_dan.setIcon(ic)
        self.b_dan.clicked.connect(lambda: self.mo_dan_tai_san())
        # 0.9.96 (người dùng): nút giữ chỗ - quét hồ sơ trong cửa sổ lập phương án hộ đang hoàn thiện, bấm chỉ báo
        self.b_ocr = QPushButton('Quét hồ sơ…')
        self.b_ocr.setToolTip(TB_QUET_HO_SO)
        self.b_ocr.clicked.connect(lambda: self.quet_giay_to())
        self.b_luu = QPushButton('Lưu (Ctrl+S)')
        self.b_luu.clicked.connect(lambda: self.luu())
        self.b_bo = QPushButton('Bỏ thay đổi')
        self.b_bo.clicked.connect(lambda: self.bo_thay_doi())
        self.b_in = QPushButton('In / Xuất…')
        self.b_in.clicked.connect(lambda: self.in_xuat())
        # 0.9.84 (người dùng 14/10/2026): bật / tắt khung xem trước A4 bên phải (phím F4) - bản in của phương án ĐANG SOẠN
        self.btn_toggle_preview = QPushButton('Xem trước A4 (F4)')
        self.btn_toggle_preview.setObjectName('btn_toggle_preview')
        self.btn_toggle_preview.setCheckable(True)
        self.btn_toggle_preview.setFixedHeight(CAO_NUT_TREN)
        self.btn_toggle_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_preview.setToolTip('Hiện / ẩn bản in A4 của hộ đang mở ở nửa phải cửa sổ (F4). Bản xem trước lấy cả số liệu '
                                           'chưa lưu; cần Microsoft Excel.')
        self.btn_toggle_preview.setStyleSheet(QSS_NUT_XEM_TRUOC)
        self.btn_toggle_preview.setProperty('khong_icon', True)
        ic = icon_ky_hieu(0xE890, '#FFFFFF', 16)        # View (Segoe MDL2); Win 7 không có phông: chỉ chữ (không emoji)
        if ic is not None:
            self.btn_toggle_preview.setIcon(ic)
        self.btn_toggle_preview.clicked.connect(lambda: self.bat_tat_xem_truoc())
        self.b_dong = QPushButton('Đóng')
        self.b_dong.clicked.connect(lambda: self.close())
        # 0.9.84: hàng trên cùng = 3 khối trong XepDong (hẹp thì khối sau xuống dòng) - một hàng cứng cần ~1.600 điểm (đo Windows
        # 125%), cửa sổ không thu nhỏ được dưới mức đó, rộng hơn màn hình 1366; nay tối thiểu = khối rộng nhất
        from .giao_dien import XepDong
        self.thanh_tren = QWidget()
        h1 = XepDong(self.thanh_tren, 4)
        h1.setContentsMargins(0, 0, 0, 0)
        for b in (self.b_truoc, self.b_sau, self.b_ocr, self.b_goi_y, self.b_luu, self.b_bo, self.b_in, self.b_dong):
            b.setFixedHeight(CAO_NUT_TREN)
        nhan = QLabel('Hộ:')
        nhan.setProperty('vai', 'nhan')
        # 0.9.95: 4 khối nhỏ (chọn hộ | nhập liệu | lưu | xem / in / đóng) - đủ rộng (>= ~1.300 điểm) thì MỘT hàng 27 px với ô chọn hộ,
        # hẹp (màn hình 1366 ở 125%) thì xuống 2 hàng thay vì 3
        for nhom, gian in (((nhan, self.cb_ho, self.b_truoc, self.b_sau), None),
                           ((self.b_dan, self.b_ocr, self.b_goi_y), 'dau'),
                           ((self.b_luu, self.b_bo), 'dau'),
                           ((self.btn_toggle_preview, self.b_in, self.b_dong), 'dau')):
            khoi = QWidget()
            hk = QHBoxLayout(khoi)
            hk.setContentsMargins(0, 0, 0, 0)
            hk.setSpacing(6)
            if gian:
                hk.addStretch(1)                    # nút dồn về phải trong khối (chỗ thừa khi một hàng)
            for w in nhom:
                hk.addWidget(w, 1 if w is self.cb_ho else 0)
            h1.addWidget(khoi)
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
        # ---- thẻ 0 hồ sơ hộ + 5 mục
        from .man_hinh_ho_so import KhungHoSo
        self.tab = QTabWidget()
        the0 = QWidget()
        lo0 = QVBoxLayout(the0)
        lo0.setContentsMargins(6, 4, 6, 4)
        self.ho_so = KhungHoSo(con, ma_ho, the0, an=('trang_thai', 'tai_dinh_cu'), khi_thay_doi_csdl=self._sau_ghi_ho_so,
                               khi_xoa_ho=self._sau_xoa_ho)
        lo0.addWidget(self.ho_so, 1)
        self.tab.addTab(the0, TEN_TAB[0])
        self.bang = {}
        for the, m in enumerate(THE_MUC[1:], start=1):
            self.bang[m] = BangMuc(self, m)
            self.tab.addTab(self.bang[m], TEN_TAB[the])
        # ---- tổng + cảnh báo
        self.lb_tong = QLabel('')
        self.lb_tong.setObjectName('tong_pa')
        self.lb_tong.setStyleSheet('QLabel#tong_pa { font-size: 13px; padding: 3px 8px; background: #EAF2FB; '
                                   'border: 1px solid #D3E2F1; border-radius: 5px; }')
        self.lb_tong.setWordWrap(True)
        self.lb_tb = QLabel('')
        self.lb_tb.setWordWrap(True)
        self.lb_tb.setStyleSheet('QLabel { color: #1F4E78; padding: 2px 6px; }')
        self.o_cb = QPlainTextEdit()
        self.o_cb.setReadOnly(True)
        from .giao_dien import kieu_trang_thai
        self.o_cb.setStyleSheet(kieu_trang_thai('canh_bao', 'QPlainTextEdit', dam=False))   # màu "cần xem lại" dùng chung
        self.o_cb.setVisible(False)
        # QSplitter ngang: trái = các thẻ soạn + tổng / cảnh báo; phải = KhungXemTruocTaiLieu, MẶC ĐỊNH ẨN (F4 / nút bật)
        from .xem_truoc_tai_lieu import KhungXemTruocTaiLieu, in_qua_excel
        trai = QWidget()
        lo_trai = QVBoxLayout(trai)
        lo_trai.setContentsMargins(0, 0, 0, 0)
        lo_trai.setSpacing(4)
        lo_trai.addWidget(self.tab, 1)
        lo_trai.addWidget(self.lb_tb)
        lo_trai.addLayout(self.hang_dieu_huong())       # dải tổng cộng + ◀ Trở lại / Tiếp theo ▶ một hàng (0.9.95)
        lo_trai.addWidget(self.o_cb)
        self.w_preview = KhungXemTruocTaiLieu(self, ham_in=lambda pdf, xlsx: in_qua_excel(self, pdf, xlsx))
        self.w_preview.setMinimumWidth(520)
        self.w_preview.setVisible(False)
        self.tach = QSplitter(Qt.Orientation.Horizontal)
        self.tach.addWidget(trai)
        self.tach.addWidget(self.w_preview)
        self.tach.setChildrenCollapsible(False)
        self.tach.setStretchFactor(0, 3)
        self.tach.setStretchFactor(1, 2)
        self._hen_xem = QTimer(self)                # sửa số liệu khi khung đang hiện: lập lại sau khi ngừng sửa (Excel mất vài giây)
        self._hen_xem.setSingleShot(True)
        self._hen_xem.timeout.connect(lambda: self.lam_moi_xem_truoc())
        lo = QVBoxLayout(self)
        lo.setContentsMargins(6, 4, 6, 4)
        lo.setSpacing(4)
        lo.addWidget(self.thanh_tren)
        lo.addWidget(self.tach, 1)
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
                          (QKeySequence('F4'), lambda: self.bat_tat_xem_truoc())):
            sc = QShortcut(phim, self)
            sc.activated.connect(ham)
            self._phim.append(sc)
        self._dang_nap = False
        for m in MUC_KHOAN:
            self.bang[m].nap_danh_sach()
        self.nap_ho()
        self.tab.setCurrentIndex(1 if self.bo.pa.dat or any(self.bo.pa.khoan[m] for m in MUC_KHOAN) else 0)

    def _nap_ds_ho(self):
        self.cb_ho.blockSignals(True)
        self.cb_ho.clear()
        for ma, tt, ten in self.bo.danh_sach_ho():
            self.cb_ho.addItem(f'{tt}. {ten}', ma)            # không hiện "(mã n)" (16/10/2026)
        self.cb_ho.blockSignals(False)

    def hang_dieu_huong(self, the: int | None = None) -> QHBoxLayout:
        """0.9.95: MỘT hàng dưới đáy cửa sổ (28 px) = dải tổng cộng `lb_tong` + ◀ Trở lại / Tiếp theo ▶ theo thẻ đang xem (trước
        0.9.95 mỗi thẻ một hàng nút riêng cao 40 px). Thẻ cuối không có nút lưu riêng: "Lưu (Ctrl+S)" ở thanh trên."""
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        self.b_tro_lai = QPushButton('◀ Trở lại')
        self.b_tiep_theo = QPushButton('Tiếp theo ▶')
        self.b_tro_lai.clicked.connect(lambda: self.sang_the(self.tab.currentIndex() - 1))
        self.b_tiep_theo.clicked.connect(lambda: self.sang_the(self.tab.currentIndex() + 1))
        for b in (self.b_tro_lai, self.b_tiep_theo):
            b.setFixedHeight(28)
        h.addWidget(self.lb_tong, 1)
        h.addWidget(self.b_tro_lai)
        h.addWidget(self.b_tiep_theo)
        self.tab.currentChanged.connect(lambda i: self._cap_nhat_dieu_huong(i))
        self._cap_nhat_dieu_huong(self.tab.currentIndex() if the is None else the)
        return h

    def _cap_nhat_dieu_huong(self, the: int):
        co_lui, co_tien = the > 0, the < len(THE_MUC) - 1
        self.b_tro_lai.setVisible(co_lui)
        self.b_tiep_theo.setVisible(co_tien)
        if co_lui:
            self.b_tro_lai.setText(f'◀ Trở lại: {TEN_TAB[the - 1]}')
        if co_tien:
            self.b_tiep_theo.setText(f'Tiếp theo: {TEN_TAB[the + 1]} ▶')

    def sang_the(self, the: int) -> bool:
        """Chuyển thẻ; rời thẻ hồ sơ hộ có sửa đổi thì lưu hồ sơ trước (để thửa mới dùng được ở mục 1)."""
        if self.tab.currentIndex() == 0 and the != 0 and self.ho_so.co_thay_doi() and not self.ho_so.luu():
            return False
        self.tab.setCurrentIndex(the)
        if THE_MUC[the] in MUC_KHOAN:
            self.bang[THE_MUC[the]].o_chon.o.setFocus()
        return True

    # ---------------------------------------------- hiển thị
    def nap_ho(self):
        self._dang_nap = True
        try:
            i = self.cb_ho.findData(self.bo.ma_ho)
            self.cb_ho.setCurrentIndex(i)
            h = self.bo.pa.ho
            self.o_nk.setValue(h.nhan_khau or 0)
            self.o_di_chuyen.setChecked(h.phai_di_chuyen)
            self.o_dt_nn.setText(so_vn(h.dt_nn_dang_dung) if h.dt_nn_dang_dung else '')
            cb = self.bang[4].cb_tdc
            cb.setCurrentText(h.tai_dinh_cu or lap_pa.TAI_DINH_CU[0])
            cb.lineEdit().setCursorPosition(0)
            if self.ho_so.ma_ho != self.bo.ma_ho:
                self.ho_so.nap(self.bo.ma_ho)
            for m in THE_MUC[1:]:
                self.bang[m].ve()
            self.bang[1].nap_danh_sach()
        finally:
            self._dang_nap = False
        self.b_truoc.setEnabled(self.bo.ho_ke(-1) is not None)
        self.b_sau.setEnabled(self.bo.ho_ke(1) is not None)
        self.lb_tb.setText('')
        if not getattr(self, '_dang_ht', False):
            self._lich_su, self._vi_tri = [], -1             # hộ mới mở / vừa lưu: bắt đầu lịch sử hoàn tác mới
        self.cap_nhat()

    def cap_nhat(self):
        self._ghi_lich_su()
        kq = self.bo.ket_qua
        for the, m in enumerate(THE_MUC[1:], start=1):
            self.bang[m].lb_tong.setText(f'Cộng mục {so_muc(m)}: {vn(kq.muc[m])} đ')
            self.tab.setTabText(the, f'{TEN_TAB[the]} ({len(self.bo.ds(m))})')
        self.tab.setTabText(0, f'{TEN_TAB[0]} ({self.ho_so.bang.rowCount()} thửa)')
        cach = '&nbsp;&nbsp;&nbsp;·&nbsp;&nbsp;&nbsp;'
        self.lb_tong.setText(
            cach.join([f'{so_muc(m)}. {vn(kq.muc[m])}' for m in THE_MUC[1:]] + [f'{so_muc(5)}. Thưởng {vn(kq.muc[5])}']) +
            f'{cach}<b>TỔNG CỘNG: {vn(kq.tong)} đồng</b>')
        from .nghiep_vu import dt_nn_thu_hoi
        dt_nn = dt_nn_thu_hoi(self.bo.pa)
        self.o_dt_nn.setPlaceholderText(f'tự lấy: {so_vn(dt_nn)}')     # để trống = DT đất NN đã nhập ở mục 1
        tl = self.bo.ty_le_thu_hoi_nn()
        self.lb_tl.setText(f'→ thu hồi {so_vn(round(tl * 100, 1))}% đất NN' if tl is not None else '')
        cb = self.bo.canh_bao
        # chỉ hiện khi có điểm cần xem lại, cao vừa số dòng (trước 0.9.18: luôn chiếm 96 px để ghi "Không có điểm cần xem lại")
        self.o_cb.setPlainText('Cần xem lại:\n' + '\n'.join('- ' + x for x in cb) if cb else '')
        if cb:
            dong = min(len(cb) + 1, 5)
            self.o_cb.setFixedHeight(self.o_cb.fontMetrics().lineSpacing() * dong + 22)
        self.o_cb.setVisible(bool(cb))
        thay = self.bo.co_thay_doi
        h = self.bo.pa.ho
        # hộ chưa lưu lần nào: Lưu vẫn bấm được - xác nhận đã lập phương án dù không có dòng nào (mọi mục 0 đồng)
        chua_lap = not str(h.trang_thai or '').startswith(DA_LAP_LUU)
        self.b_luu.setEnabled(thay or self.ho_so.co_thay_doi() or chua_lap)
        self.b_bo.setEnabled(thay)
        self.setWindowTitle(f'{"* " if thay else ""}Hồ sơ, phương án – hộ {h.ma_ho}: {h.ho_ten}  ·  {h.trang_thai}')
        if getattr(self, 'w_preview', None) is not None and self.w_preview.isVisible() and not self._dang_nap:
            self._hen_xem.start(CHO_XEM_SAU_SUA_MS)     # phương án đổi: bản xem trước lập lại khi ngừng sửa

    def thong_bao(self, tb: str):
        self.lb_tb.setText(tb or '')

    def bo_sung_vat_nuoi(self, hoi: bool = False) -> int:
        """Thêm các mục vật nuôi của bộ đơn giá vào danh mục dự án (dự án lập trước khi bộ đơn giá có vật nuôi).
        hoi=True (bấm ▼ ở thẻ Vật nuôi khi danh mục chưa có): hỏi trước khi thêm."""
        from . import don_gia
        if hoi and not getattr(self, 'im_lang', False):
            hoi_lai = ('Danh mục đơn giá của dự án chưa có vật nuôi (dự án lập trước QĐ 31/2025/QĐ-UBND).\n\n'
                       'Bổ sung các mục vật nuôi từ bộ đơn giá đang dùng vào dự án? Đơn giá khác giữ nguyên.')
            if QMessageBox.question(self, TEN_UD, hoi_lai) != QMessageBox.StandardButton.Yes:
                return 0
        try:
            with con_tro_cho():
                n = don_gia.bo_sung_vat_nuoi(self.bo.con)
        except Exception as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không bổ sung được vật nuôi', e))
            return 0
        if not n:
            self.thong_bao('Bộ đơn giá đang dùng không có mục vật nuôi nào mới để bổ sung.')
            return 0
        self.bo.dm = DanhMuc(self.bo.con)
        if hasattr(self.parent(), 'dm'):
            self.parent().dm = self.bo.dm               # cửa sổ chính: lần mở sau dùng danh mục mới
        self.bang[MUC_VN].nap_danh_sach()
        self.thong_bao(f'Đã bổ sung {n} mục vật nuôi vào danh mục dự án - gõ tên hoặc bấm ▼ để chọn.')
        return n

    # ---------------------------------------------- hoàn tác (Ctrl+Z / Ctrl+Y) trong cửa sổ
    def _ghi_lich_su(self):
        """Sau mỗi thay đổi (cap_nhat được gọi sau mọi sửa đổi): lưu một bản phương án đang soạn nếu khác bản trước."""
        if getattr(self, '_dang_ht', False) or not hasattr(self, '_lich_su'):
            return
        from .lap_pa import _dang_luu
        hien = _dang_luu(self.bo.pa)
        if 0 <= self._vi_tri < len(self._lich_su) and self._lich_su[self._vi_tri][0] == hien:
            return
        import copy
        del self._lich_su[self._vi_tri + 1:]
        self._lich_su.append((hien, copy.deepcopy(self.bo.pa)))
        if len(self._lich_su) > 100:
            del self._lich_su[0]
        self._vi_tri = len(self._lich_su) - 1

    def hoan_tac(self, lam_lai: bool = False) -> str:
        """Hoàn tác / làm lại sửa đổi chưa lưu của hộ đang soạn; hết bước (hoặc vừa lưu) thì hoàn tác thao tác đã ghi file
        (cửa sổ chính) rồi đọc lại hộ. Trả mô tả việc đã làm ('' nếu không có gì)."""
        import copy
        moi = self._vi_tri + (1 if lam_lai else -1)
        if hasattr(self, '_lich_su') and 0 <= moi < len(self._lich_su):
            self._vi_tri = moi
            self._dang_ht = True
            try:
                self.bo.pa = copy.deepcopy(self._lich_su[moi][1])
                self.nap_ho()
            finally:
                self._dang_ht = False
            tb = 'Đã làm lại' if lam_lai else 'Đã hoàn tác'
            self.thong_bao(f'{tb} (chưa lưu). Ctrl+Z / Ctrl+Y để tiếp.')
            return tb
        from .hoan_tac import cua
        ht = cua(self.bo.con)
        if ht is None or self.bo.co_thay_doi or self.ho_so.co_thay_doi():
            self.thong_bao('Không còn bước để ' + ('làm lại.' if lam_lai else 'hoàn tác.'))
            return ''
        viec = ht.lam_lai() if lam_lai else ht.hoan_tac()
        if not viec:
            self.thong_bao('Không còn bước để ' + ('làm lại.' if lam_lai else 'hoàn tác.'))
            return ''
        self.thay_doi_csdl = True
        ma = self.bo.ma_ho
        if not self.bo.con.execute('SELECT 1 FROM ho WHERE ma_ho = ?', (ma,)).fetchone():
            ma = self.bo.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()
            if ma is None:
                return viec
            ma = ma[0]
        self.bo.mo(ma)
        self.ho_so.nap(ma)
        self._nap_ds_ho()
        self.nap_ho()
        self.thong_bao(f'{"Đã làm lại" if lam_lai else "Đã hoàn tác"} thao tác đã lưu: {viec}')
        return viec

    def hoan_tac_phim(self, lam_lai: bool) -> bool:
        self.hoan_tac(lam_lai)
        return True

    # ---------------------------------------------- hồ sơ hộ (thẻ 0)
    def _sau_ghi_ho_so(self):
        """Hồ sơ hộ vừa ghi CSDL (lưu, gộp, chuyển thửa): đọc lại thửa / tên hộ, giữ phương án đang soạn."""
        self.thay_doi_csdl = True
        bc = self.bo.bc.__class__.tu(self.bo.con)
        self.bo.bc = bc
        r = self.bo.con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (self.bo.ma_ho,)).fetchone()
        if r is not None:
            self.bo.pa.ho.ho_ten = r[0]
        self._nap_ds_ho()
        self.cb_ho.setCurrentIndex(self.cb_ho.findData(self.bo.ma_ho))
        self.bang[1].nap_danh_sach()
        self.bang[1].ve()
        self.cap_nhat()

    def _sau_xoa_ho(self, tb: str):
        self.thay_doi_csdl = True
        ds = [x[0] for x in self.bo.danh_sach_ho()]
        if not ds:
            QDialog.accept(self)
            return
        self.bo.mo(ds[0])
        self._nap_ds_ho()
        self.ho_so.nap(ds[0])
        self.nap_ho()
        self.thong_bao(tb)

    # ---------------------------------------------- sửa ô
    def sua_o(self, muc: int, r: int, cot: str, text: str):
        # mục 1: sửa ô của một dòng đang nằm trong vùng chọn nhiều dòng -> áp cùng giá trị cho mọi dòng đã chọn (vị trí, giá, tỷ lệ…)
        ds = [r]
        if muc == 1 and cot in AP_NHIEU_DONG:
            chon = self.bang[1].cac_dong_chon()
            if r in chon and len(chon) > 1:
                ds = chon
        try:
            tb = ''
            for i in ds:
                tb = self.bo.sua_dat(i, cot, text) if muc == 1 else self.bo.sua_khoan(muc, i, cot, text)
            if len(ds) > 1:
                tb = f'Đã áp cho {len(ds)} dòng đã chọn. ' + tb
            if muc == 3 and cot == 'so_luong':          # 0.9.72: tự nhận diện mật độ khi sửa số cây
                tb = ' '.join(x for x in (tb, self._canh_bao_mat_do(r)) if x)
            self.thong_bao(tb)
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
        for i in ds:
            self.bang[muc]._ve_dong(i)
        self.cap_nhat()

    def ds_thua_dong(self, r: int) -> list:
        return [(mo_ta, mt) for mt, mo_ta, _ in self.bo.thua_cua_ho()]

    def doi_thua_dong(self, r: int, ma_thua):
        self.sua_o(1, r, 'thua', ma_thua)

    def ds_vi_tri_dong(self, r: int) -> list:
        return [(nhan, ('nq28', x)) for nhan, x, _ in self.bo.ds_vi_tri_nq28(r)] if 0 <= r < len(self.bo.pa.dat) else []

    def doi_vi_tri_dong(self, r: int, gt):
        if isinstance(gt, tuple) and gt[0] == 'nq28':
            chon = self.bang[1].cac_dong_chon()
            ds = chon if r in chon and len(chon) > 1 else [r]          # chọn nhiều dòng: cùng tuyến đường / vị trí cho cả loạt
            try:
                tb = ''
                for i in ds:
                    tb = self.bo.chon_vi_tri_nq28(i, gt[1])
                self.thong_bao((f'Đã áp cho {len(ds)} dòng đã chọn. ' if len(ds) > 1 else '') + tb)
            except LoiNhap as e:
                QMessageBox.warning(self, TEN_UD, str(e))
            for i in ds:
                self.bang[1]._ve_dong(i)
            self.cap_nhat()
        else:
            self.sua_o(1, r, 'vi_tri', str(gt))

    def doi_tai_dinh_cu(self, text: str):
        if self._dang_nap:
            return
        self.bo.dat_tai_dinh_cu(text)
        self.cap_nhat()

    def _doi_nk(self, v):
        if self._dang_nap:
            return
        self.bo.dat_nhan_khau(str(v))
        self.bang[4].ve()
        self.cap_nhat()

    def _doi_di_chuyen(self, co):
        if self._dang_nap:
            return
        self.bo.dat_phai_di_chuyen(co)
        self.cap_nhat()

    def _doi_dt_nn(self):
        if self._dang_nap:
            return
        try:
            self.bo.dat_dt_nn_dang_dung(self.o_dt_nn.text())
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
        h = self.bo.pa.ho
        self.o_dt_nn.setText(so_vn(h.dt_nn_dang_dung) if h.dt_nn_dang_dung else '')
        self.cap_nhat()

    # ---------------------------------------------- thêm / xóa dòng
    def mo_dan_tai_san(self, cho: bool = True, clip: str | None = None):
        """Nút / Ctrl+Shift+V: mở hộp "Dán danh sách tài sản". Bộ nhớ đệm Windows có bảng tài sản (hơn 5 ký tự, có xuống dòng hoặc Tab -
        ví dụ vừa chép từ Excel) thì điền sẵn vào ô soạn thảo và Phân loại ngay; không thì mở hộp trống như trước. `clip`: thay cho
        clipboard (kiểm thử)."""
        if clip is None:
            clip = QApplication.clipboard().text()
        clip = (clip or '').strip()
        co_bang = len(clip) > 5 and ('\n' in clip or '\t' in clip) and len(clip) <= CLIP_TOI_DA
        return self.dan_tai_san(clip if co_bang else '', cho=cho)

    def quet_giay_to(self, cho: bool = True) -> str:
        """Nút "Quét hồ sơ" (0.9.96): tiện ích đang hoàn thiện - chỉ báo, không đọc / ghi gì. Trả chữ thông báo."""
        if cho and not getattr(self, 'im_lang', False):
            QMessageBox.information(self, TEN_UD, TB_QUET_HO_SO)
        return TB_QUET_HO_SO

    def dan_tai_san(self, chu: str = '', cho: bool = True):
        """Hộp "Dán danh sách tài sản" (man_hinh_phan_loai): tự xếp từng dòng vào mục nhà / cây / vật nuôi / hỗ trợ."""
        from .man_hinh_phan_loai import HopDanTaiSan
        hop = HopDanTaiSan(self, chu)
        if cho:
            hop.exec()
        return hop

    def sau_khi_dan_tai_san(self, n: int, muc_cuoi: int) -> None:
        """HopDanTaiSan đã thêm n dòng: vẽ lại các thẻ mục, mở thẻ của dòng cuối."""
        for m in MUC_KHOAN:
            self.bang[m].ve()
        self.tab.setCurrentIndex(the_cua(muc_cuoi))
        self.cap_nhat()
        self.thong_bao(f'Đã thêm {n} dòng từ danh sách tài sản (chưa lưu: bấm Lưu).')

    def _canh_bao_mat_do(self, i: int) -> str:
        from .man_hinh_cay import canh_bao_mat_do
        try:
            return canh_bao_mat_do(self.bo, i)
        except Exception:                               # noqa: BLE001 - chỉ là lời nhắc: lỗi đọc quy chuẩn không chặn nhập liệu
            return ''

    def _sau_khi_them(self, muc, i, tb=''):
        if muc == 3 and i is not None:
            tb = ' '.join(x for x in (tb, self._canh_bao_mat_do(i)) if x)
        self.tab.setCurrentIndex(the_cua(muc))
        self.bang[muc].ve(chon=i)
        self.thong_bao(tb)
        self.cap_nhat()

    def them_thua(self, ma_thua=None):
        if ma_thua is None:
            ds = self.bo.thua_cua_ho()
            if not ds:
                QMessageBox.information(self, TEN_UD, 'Hộ này chưa có thửa: thêm thửa ở thẻ "Thông tin hộ, thửa đất".')
                return None
            ten, ok = QInputDialog.getItem(self, 'Thêm thửa vào mục 1', 'Chọn thửa của hộ:', [x[1] for x in ds], 0, False)
            if not ok:
                return None
            ma_thua = ds[[x[1] for x in ds].index(ten)][0]
        try:
            i, tb = self.bo.them_thua(ma_thua)
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        self._sau_khi_them(1, i, tb)
        self.bang[1].nap_danh_sach()
        return i

    def them_nhanh(self, muc: int, m=None, so_luong: str | None = None, ty_le: str | None = None, kieu: str | None = None):
        """Hàng nhập nhanh: mục đã chọn (hoặc tên gõ tự do = hạng mục ngoài danh mục) + số lượng + tỷ lệ → thêm dòng.
        Mục 3 kiểu 'dk' / 'cv': số lượng là các số đo đường kính / chu vi thân, tự xếp vào đúng quy cách đơn giá."""
        # 0.9.67: logic thêm dùng chung với Dự toán & khái toán (nhap_tai_san.them_mot, đích DichPhuongAn)
        from .nhap_tai_san import DichPhuongAn, la_tu_do, them_mot
        bm = self.bang[muc]
        m = bm.o_chon.chon if m is None else m
        sl = bm.o_sl.text().strip() if so_luong is None else str(so_luong)
        tl = bm.o_tl.text().strip() if ty_le is None else str(ty_le)
        kieu = kieu or (bm.cb_kieu.currentData() if muc == 3 else 'sl')
        gc = bm.o_gc.text().strip()
        try:
            if muc == 4 and not la_tu_do(m) and bm.cs_loai in ('od', 'dt', 'tn'):
                return self._them_chinh_sach(m, bm, so_luong, gc)      # chính sách tính theo hộ: riêng phương án
            do = bm.hang.o_do.text().strip() if so_luong is None and kieu in ('dk', 'cv') else ''
            i, tb, tu_do = them_mot(DichPhuongAn(self.bo), muc, m, bm.o_chon.text(), sl, tl, kieu, gc, do)
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        if kieu in ('dk', 'cv'):
            muc = 3
        self._sau_khi_them(muc, i, tb)
        bm.xoa_nhap()
        if tu_do:                                       # ngoài danh mục: chuyển ngay tới ô đơn giá
            c = [x[0] for x in bm.cot].index('don_gia')
            bm.bang.setCurrentCell(i, c)
            bm.bang.editItem(bm.bang.item(i, c))
        return i

    def _them_chinh_sach(self, m, bm, so_luong, gc: str):
        """Mục 4 theo cách tính: ổn định đời sống (nhân khẩu × kg gạo × tháng × giá gạo × tỷ lệ), đào tạo chuyển đổi nghề
        (mỗi thửa đất nông nghiệp: DT × đơn giá đất × tỷ lệ), thuê nhà / tự lo chỗ ở (một dòng theo nhân khẩu)."""
        from . import chinh_sach as cs
        bo, k = self.bo, bm.cs_loai
        nk = bo.pa.nhan_khau
        if k == 'od':
            if not nk:
                raise LoiNhap('Nhập số nhân khẩu của hộ (ô Nhân khẩu) trước.')
            ds = [cs.dong_on_dinh(m, nk, lap_pa.doc_so(bm.o_gao.text(), 'Giá gạo', cho_phep_trong=False),
                                  lap_pa.doc_so(bm.o_kg.text(), 'Số kg gạo', cho_phep_trong=False),
                                  lap_pa.doc_so(bm.o_thang_od.text(), 'Số tháng', cho_phep_trong=False),
                                  lap_pa.doc_ty_le(bm.o_tl_od.text()))]
            tb = f'Đã thêm {ds[0].ten}: {ds[0].cach_tinh}.'
        elif k == 'tn':
            thang = str(so_luong) if so_luong is not None else bm.o_thang_tn.text()
            ds = [cs.dong_thue_nha(m, bo.bc, nk, lap_pa.doc_so(thang, 'Số tháng', cho_phep_trong=False),
                                   lap_pa.doc_so(bm.o_co_ban.text(), 'Mức hộ'), lap_pa.doc_so(bm.o_them.text(), 'Mức mỗi khẩu'))]
            tb = f'Đã thêm {ds[0].ten}: {ds[0].cach_tinh}.'
        else:
            ds = []
            b = bm.bang_dt
            for r in range(b.rowCount()):
                if b.item(r, 0).checkState() != Qt.CheckState.Checked:
                    continue
                ds.append(cs.dong_dao_tao(m, b.item(r, 1).text(), lap_pa.doc_so_luong(b.item(r, 2).text(), 'm²', 'Diện tích'),
                                          lap_pa.doc_so(b.item(r, 3).text(), 'Đơn giá đất'), lap_pa.doc_ty_le(b.item(r, 4).text())))
            if not ds:
                raise LoiNhap('Đánh dấu ít nhất một thửa đất nông nghiệp để tính hỗ trợ đào tạo, chuyển đổi nghề.')
            tb = f'Đã thêm hỗ trợ đào tạo, chuyển đổi nghề cho {len(ds)} thửa.'
        for d in ds:
            d.quy_cach = d.quy_cach or m.can_cu
            if gc:
                d.ghi_chu = gc
        i = bo.them_dong_ho_tro(ds)
        self._sau_khi_them(4, i, tb)
        bm.xoa_nhap()
        return i

    def them_tu_danh_muc(self, muc: int, m=None):
        if m is None:
            dlg = ChonDanhMuc(self.bo.dm, muc, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return None
            m = dlg.chon
        try:
            if m.nguon == 'quyuoc':
                # quy ước tương đương: thêm dòng mang tên thực tế, áp giá theo mục tương đương
                i = self.bo.them_hang_muc_khac(muc, m.ten)
                self.bo.ap_gia_tuong_duong(muc, i, m)
                tb = ''
            else:
                i, tb = self.bo.them_tu_danh_muc(muc, m)
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        self._sau_khi_them(muc, i, tb)
        return i

    def them_hang_muc_khac(self, muc: int, ten: str | None = None, m_tuong_duong=None, hoi_gia: bool = True):
        if ten is None:
            ten, ok = QInputDialog.getText(self, 'Hạng mục ngoài danh mục',
                                           'Tên hoặc mô tả tài sản / khoản (in ra đúng như gõ):')
            if not ok:
                return None
        try:
            i = self.bo.them_hang_muc_khac(muc, ten)
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        self._sau_khi_them(muc, i)
        if m_tuong_duong is not None or hoi_gia:
            self.chon_gia_tuong_duong(muc, i, m_tuong_duong)
        return i

    def chon_gia_tuong_duong(self, muc: int, i: int | None = None, m=None):
        if i is None:
            i = self.bang[muc].dong_chon()
        if not (0 <= i < len(self.bo.ds(muc))):
            QMessageBox.information(self, TEN_UD, 'Chọn một dòng trước.')
            return False
        if m is None:
            ten = self.bo.pa.khoan[muc][i].ten
            dlg = ChonDanhMuc(self.bo.dm, muc, self, tuong_duong=True, tu_khoa=' '.join(ten.split()[:2]))
            if dlg.exec() != QDialog.DialogCode.Accepted:
                self.thong_bao('Chưa chọn giá tương đương: nhập đơn giá tay và ghi căn cứ ở cột Căn cứ giá.')
                return False
            m = dlg.chon
        try:
            self.bo.ap_gia_tuong_duong(muc, i, m)
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return False
        self._sau_khi_them(muc, i, f'Đã áp giá tương đương {m.ma}: {vn(m.don_gia)} đ/{m.dvt}. Nhập số lượng.')
        return True

    # ---------------------------------------------- tiện ích cây trồng, tài sản
    def _dong_dang_chon(self, muc: int, ten_viec: str):
        i = self.bang[muc].dong_chon()
        if not (0 <= i < len(self.bo.ds(muc))):
            QMessageBox.information(self, TEN_UD, f'Chọn một dòng ở mục {so_muc(muc)} để {ten_viec}.')
            return None
        return i

    def them_cay_chu_vi(self, ten_loai: str | None = None, chu_vi: str | None = None, cho: bool = True):
        """Thêm cây theo chu vi đo được (cho=False: trả hộp thoại để kiểm thử). Trên màn hình: hàng nhập nhanh mục 3."""
        from .man_hinh_cay import HopCayChuVi
        dlg = HopCayChuVi(self)
        if ten_loai is not None:
            dlg.chon_loai(ten_loai)
        if chu_vi is not None:
            dlg.o_cv.setPlainText(chu_vi)
        if not cho:
            return dlg
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.dong_moi:
            self._sau_khi_them(3, dlg.dong_moi[-1], f'Đã thêm {len(dlg.dong_moi)} dòng cây theo chu vi.')
        return dlg

    def tinh_mat_do(self, i: int | None = None, cho: bool = True):
        from .man_hinh_cay import HopMatDo
        i = self._dong_dang_chon(3, 'tính mật độ') if i is None else i
        if i is None:
            return None
        dlg = HopMatDo(self, i)
        if not cho:
            return dlg
        if dlg.exec() == QDialog.DialogCode.Accepted:
            trong, ngoai, _ = dlg.ket_qua
            self._sau_khi_them(3, i, f'Trong mật độ {trong} cây; ngoài mật độ {ngoai} cây' +
                               (' (dòng ngay dưới).' if ngoai else '.'))
        return dlg

    def tra_gia_dat_nq28(self, i: int | None = None, dong: dict | None = None):
        """Mục 1: tra bảng giá đất NQ 28/2025 cho dòng đất đang chọn (một dòng thì dòng đó): chọn dòng bảng giá -> ghi vị trí và
        điền giá bảng giá theo loại đất của dòng (vẫn sửa tay được). dong: dòng bảng giá cho sẵn (kiểm thử)."""
        if i is None:
            i = self.bang[1].dong_chon()
            if not 0 <= i < len(self.bo.pa.dat):
                if len(self.bo.pa.dat) != 1:
                    QMessageBox.information(self, TEN_UD, 'Chọn một dòng đất ở mục 1 để tra giá.')
                    return None
                i = 0
        if dong is None:
            from .man_hinh_du_toan import HopTraNQ28
            dlg = HopTraNQ28(self, self.bo.bc.ten_dia_ban or '', self.bo.pa.dat[i].loai_dat)
            if dlg.exec() != QDialog.DialogCode.Accepted or dlg.dong is None:
                return None
            dong = dlg.dong
        try:
            tb = self.bo.chon_vi_tri_nq28(i, dong)
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        self.thong_bao(tb)
        self.bang[1]._ve_dong(i)
        self.cap_nhat()
        return tb

    def kiem_tra_dt_xay_dung(self, cho: bool = True):
        """Tổng diện tích tài sản xây dựng (nhà chính trước, rồi nhà khác, mái che…) so với tổng diện tích thu hồi."""
        from .man_hinh_cay import HopDienTichXayDung
        dlg = HopDienTichXayDung(self)
        if cho:
            dlg.exec()
        return dlg

    def tach_ranh(self, i: int | None = None, cho: bool = True):
        from .man_hinh_cay import HopRanh
        i = self._dong_dang_chon(2, 'tách theo ranh thu hồi') if i is None else i
        if i is None:
            return None
        dlg = HopRanh(self, i)
        if not cho:
            return dlg
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._sau_khi_them(2, i, 'Đã tách phần trong / ngoài ranh thu hồi (mô tả ở cột Quy cách).')
        return dlg

    def nhan_ban_dong(self, muc: int, i: int | None = None) -> int | None:
        """Chép dòng đang chọn thành dòng mới ngay dưới (mục 1: cùng thửa - tách diện tích theo loại đất / vị trí). Trả chỉ số dòng mới."""
        from dataclasses import replace
        i = self.bang[muc].dong_chon() if i is None else i
        if not 0 <= i < len(self.bo.ds(muc)):
            return None
        if muc == 1:
            ds = self.bo.pa.dat
            ds.insert(i + 1, replace(ds[i], id=None, thanh_tien_excel=None))
            j = i + 1
        else:
            j = self.bo.nhan_ban(muc, i)
        self.bang[muc].ve(chon=j)
        self.thong_bao(f'Đã nhân bản dòng {i + 1}: sửa số liệu dòng mới.')
        self.cap_nhat()
        return j

    def them_tat_ca_thua(self) -> int:
        """Thêm dòng mục 1 cho mọi thửa của hộ chưa có trong mục 1. Trả số dòng thêm."""
        return self._them_cac_thua(None)

    def chon_nhieu_thua(self, cho: bool = True):
        """Hộp chọn nhiều thửa -> thêm vào mục 1. cho=False: trả hộp (test đặt dấu rồi gọi them_cac_thua_da_chon)."""
        da_co = {d.ma_thua for d in self.bo.pa.dat}
        con = {x[0]: x[2] for x in self.bo.thua_cua_ho()}
        ds = []
        for t in self.bo.bc.thua_cua(self.bo.ma_ho):
            con_lai = con.get(t['ma_thua'], KHONG)
            ds.append((t['ma_thua'], t['so_to'] or '', t['so_thua'] or '', t['loai_dat'] or '', con_lai, t['ma_thua'] in da_co))
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Hộ này chưa có thửa: thêm thửa ở thẻ "Thông tin hộ, thửa đất".')
            return None
        hop = HopChonNhieuThua(ds, self)
        if not cho:
            return hop
        if hop.exec() == QDialog.DialogCode.Accepted:
            self._them_cac_thua(hop.chon_ma(), bo_qua_da_co=False)
        return hop

    def _them_cac_thua(self, ds_ma_thua, bo_qua_da_co: bool = True) -> int:
        n0 = len(self.bo.pa.dat)
        n = self.bo.them_nhieu_thua(ds_ma_thua, bo_qua_da_co=bo_qua_da_co)
        self.tab.setCurrentIndex(the_cua(1))
        self.bang[1].ve(chon=n0 if n else None)
        self.bang[1].nap_danh_sach()
        self.thong_bao(f'Đã thêm {n} thửa vào mục 1.' if n else 'Không có thửa nào cần thêm (các thửa đã có trong mục 1).')
        self.cap_nhat()
        return n

    def xoa_dong(self, muc: int, i: int | None = None):
        if i is None and muc == 1 and len(self.bang[1].cac_dong_chon()) > 1:
            ds = self.bang[1].cac_dong_chon()                         # chọn nhiều dòng mục 1: xóa cả loạt
            n = self.bo.xoa_nhieu_dat(ds)
            self.bang[1].ve(chon=min(ds[0], len(self.bo.pa.dat) - 1))
            self.bang[1].nap_danh_sach()
            self.thong_bao(f'Đã xóa {n} dòng mục 1.')
            self.cap_nhat()
            return
        i = self.bang[muc].dong_chon() if i is None else i
        if 0 <= i < len(self.bo.ds(muc)):
            self.bo.xoa(muc, i)
            self.bang[muc].ve(chon=min(i, len(self.bo.ds(muc)) - 1))
            if muc == 1:
                self.bang[1].nap_danh_sach()
            self.cap_nhat()

    def di_chuyen(self, muc: int, buoc: int):
        i = self.bang[muc].dong_chon()
        if i < 0:
            return
        j = self.bo.di_chuyen(muc, i, buoc)
        self.bang[muc].ve(chon=j)
        self.cap_nhat()

    # ---------------------------------------------- gợi ý
    def goi_y(self, tu_dong: bool = False):
        dx, tu = self.bo.goi_y()
        if tu_dong:
            chon = dx
        else:
            dlg = HopGoiY(dx, tu, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return []
            chon = dlg.da_chon()
        self.bo.ap_dung_goi_y(chon)
        self.bang[4].ve()
        self.tab.setCurrentIndex(the_cua(4))
        self.thong_bao(f'Đã áp dụng {len(chon)} gợi ý hỗ trợ.' if chon else '')
        self.cap_nhat()
        return chon

    # ---------------------------------------------- lưu / chuyển hộ / đóng
    def luu(self) -> bool:
        if self.ho_so.co_thay_doi() and not self.ho_so.luu():
            self.tab.setCurrentIndex(0)
            return False
        try:
            tb = self.bo.luu()
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return False
        self.da_luu = True
        self.nap_ho()
        self.thong_bao(tb)
        cha = self.parent()
        if self.property('nhung_tab') and cha is not None and hasattr(cha, 'tai_lai'):
            cha.tai_lai()
        return True

    def in_xuat(self, cho: bool = True):
        """In / xuất phương án hộ đang mở (in theo số liệu đã lưu, nên hỏi lưu trước)."""
        if self.bo.co_thay_doi or self.ho_so.co_thay_doi():
            tl = _hoi(self, TEN_UD, 'Bản in lấy số liệu đã lưu. Lưu hộ này trước khi in?')
            if tl is None or (tl == 'luu' and not self.luu()):
                return None
            if tl == 'bo':
                self.bo_thay_doi()
        dlg = HopIn(self.bo.con, self, ma_ho_chon=[self.bo.ma_ho], file_du_an=getattr(self.parent(), 'file', None))
        if cho:
            dlg.exec()
        return dlg

    def bo_thay_doi(self):
        self.bo.mo(self.bo.ma_ho)
        self.ho_so.nap(self.bo.ma_ho)
        self.nap_ho()
        self.lam_moi_xem_truoc()

    # ---------------------------------------------- xem trước A4 (khung bên phải, F4)
    def bat_tat_xem_truoc(self, hien: bool | None = None) -> bool:
        """Hiện / ẩn khung xem trước; hiện thì lập ngay bản in của hộ đang mở. Trả trạng thái mới."""
        hien = not self.w_preview.isVisible() if hien is None else bool(hien)
        self.w_preview.setVisible(hien)
        self.btn_toggle_preview.setChecked(hien)
        if hien:
            self._vua_xem_truoc()
            w = max(2, self.tach.width())
            phai = max(self.w_preview.minimumWidth(), int(w * 0.45))
            self.tach.setSizes([max(1, w - phai), phai])
            self.lam_moi_xem_truoc(ngay=True)
        else:
            self._hen_xem.stop()
        return hien

    def _vua_xem_truoc(self) -> None:
        """Khung xem trước rộng tối thiểu 520; màn hình không đủ chỗ cho phần soạn + 520 (1366 x 125%) thì hạ tối thiểu của khung
        (không dưới RONG_XEM_TOI_THIEU) để cửa sổ không rộng hơn màn hình."""
        man = self.screen() or QApplication.primaryScreen()
        rong = man.availableGeometry().width() if man is not None else 10 ** 6
        m = self.layout().contentsMargins()
        con = rong - self.tach.widget(0).minimumSizeHint().width() - m.left() - m.right() - self.tach.handleWidth() - 16
        self.w_preview.setMinimumWidth(max(RONG_XEM_TOI_THIEU, min(520, con)))

    def lam_moi_xem_truoc(self, ngay: bool = False) -> None:
        """Bản in A4 (mẫu IN_CHITIET) của hộ đang mở theo phương án ĐANG SOẠN trong bộ nhớ (chưa lưu cũng hiện); thông tin hộ,
        nguồn gốc theo hồ sơ đã lưu."""
        if not self.w_preview.isVisible():
            return
        self._hen_xem.stop()
        from . import in_an
        bo, ma = self.bo, self.bo.ma_ho

        def tao(thu_muc):
            return in_an.lap_chi_tiet(bo.con, ma, Path(thu_muc) / f'{in_an.ten_file_ho(bo.con, ma)}.xlsx', bc=bo.bc, pa=bo.pa)
        ten = f'{bo.pa.ho.ho_ten}' + (' (chưa lưu)' if bo.co_thay_doi else '')
        self.w_preview.yeu_cau(None, tao, ten, ngay)

    def hoi_luu(self) -> bool:
        """True nếu được phép rời hộ đang soạn."""
        if not self.bo.co_thay_doi and not self.ho_so.co_thay_doi():
            return True
        tl = _hoi(self, TEN_UD, f'Hộ {self.bo.ma_ho} – {self.bo.pa.ho.ho_ten} có thay đổi chưa lưu. Lưu lại?')
        if tl == 'luu':
            return self.luu()
        if tl == 'bo':
            self.bo.mo(self.bo.ma_ho)
            self.ho_so.nap(self.bo.ma_ho)
            return True
        return False

    def chuyen_ho(self, ma_ho: int) -> bool:
        if ma_ho == self.bo.ma_ho:
            return True
        if not self.hoi_luu():
            self.cb_ho.setCurrentIndex(self.cb_ho.findData(self.bo.ma_ho))
            return False
        self.bo.mo(ma_ho)
        self.ho_so.nap(ma_ho)
        self.nap_ho()
        self.lam_moi_xem_truoc()
        return True

    def sang_ho(self, buoc: int):
        ma = self.bo.ho_ke(buoc)
        if ma is not None:
            self.chuyen_ho(ma)

    def _chon_ho_tu_hop(self, idx):
        ma = self.cb_ho.itemData(idx)
        if ma is not None:
            self.chuyen_ho(ma)

    def reject(self):
        if self.hoi_luu():
            super().reject()

    def closeEvent(self, e):
        if self.hoi_luu():
            self.w_preview.don_dep()
            e.accept()
            super().closeEvent(e)
        else:
            e.ignore()

    def done(self, r):
        self.w_preview.don_dep()                    # xóa file xem trước tạm
        super().done(r)


# ---------------------------------------------------------------- thông tin dự án
class HopDuAn(QDialog):
    def __init__(self, con, parent=None):
        super().__init__(parent)
        self.con = con
        self.setWindowTitle('Thông tin dự án')
        self.resize(1080, 500)                          # 0.9.95: đủ cao, ô tên đơn vị bên phải không bị cắt (rộng >= 920)
        gt = lap_pa.doc_du_an(con)
        self.o = {}
        from . import csdl
        from .giao_dien import can_giua, the_form
        du_an, don_vi = [], []
        for k, ten in lap_pa.TRUONG_DU_AN:
            if k == 'cap_dia_ban':
                w = QComboBox()
                w.addItems(['Xã', 'Phường', 'Thị trấn', 'Đặc khu'])
                w.setCurrentText(gt[k] or 'Phường')
            elif k == 'co_quan_tham_dinh':
                # 0.9.72: gõ tự do hoặc chọn gợi ý theo địa bàn (phường: Phòng Kinh tế, Hạ tầng và Đô thị; xã: Phòng Kinh tế)
                w = QComboBox()
                w.setEditable(True)
                w.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
                w.setToolTip('Cơ quan thẩm định phương án (tờ trình: Kính gửi, đề nghị thẩm định). Để trống: tự lấy theo cấp '
                             'địa bàn - phường: Phòng Kinh tế, Hạ tầng và Đô thị; xã: Phòng Kinh tế')
                w.setEditText(gt[k])
            else:
                w = QLineEdit(gt[k])
                w.setCursorPosition(0)
            self.o[k] = w
            (don_vi if k in csdl.TRUONG_DON_VI else du_an).append((ten + ':', w))
        # kinh phí tổ chức thực hiện bồi thường (QĐ 08/2025/QĐ-UBND): theo tuyến 3,5%, cụm / vùng / khác 2,5%. 0.9.72 (người dùng
        # 13/10/2026): chọn sẵn theo tên dự án (đường, tuyến, kênh, đường dây, đường ống… -> theo tuyến) và đổi theo khi sửa tên,
        # tới khi người dùng tự chọn loại
        loai, tl, tu_nhan = lap_pa.kinh_phi_to_chuc(con)
        self.o_loai_kp = QComboBox()
        for k, (ten, toi_da) in lap_pa.LOAI_KINH_PHI.items():
            self.o_loai_kp.addItem(f'{ten} - tối đa {so_vn(toi_da)}%', k)
        self.o_loai_kp.setCurrentIndex(self.o_loai_kp.findData(loai))
        self._kp_tu_dong = tu_nhan
        self.o_loai_kp.activated.connect(lambda _=0: setattr(self, '_kp_tu_dong', False))
        self.o['ten'].textChanged.connect(lambda _=None: self._kp_theo_ten())
        for k in ('cap_dia_ban', 'ten_dia_ban'):
            w = self.o[k]
            (w.currentTextChanged if isinstance(w, QComboBox) else w.textChanged).connect(lambda _=None: self._goi_y_tham_dinh())
        self._goi_y_tham_dinh()
        # 0.9.69 (người dùng 12/10/2026): chỉ chọn loại dự án - tỷ lệ tự lấy mức tối đa của loại (bỏ ô Tỷ lệ cho đỡ rối)
        kp = the_form('Kinh phí tổ chức thực hiện bồi thường (bảng tổng hợp, dự toán)',
                      [('Loại dự án:', self.o_loai_kp)], 110)
        kp.setToolTip(f'{lap_pa.CAN_CU_KINH_PHI}: dự án, tiểu dự án hạ tầng theo tuyến không quá 3,5%; dự án còn lại '
                      '(cụm, vùng, khu…) không quá 2,5% tổng kinh phí bồi thường, hỗ trợ, tái định cư.')
        form = QVBoxLayout()
        form.addWidget(can_giua(the_form('Thông tin dự án', du_an, 110), the_form('Đơn vị lập, người ký', don_vi, 160)))
        form.addWidget(can_giua(kp))
        ghi = QLabel('Cấp và tên xã, phường dùng trong mô tả thửa trên bản in và để chọn mức hỗ trợ theo địa bàn xã / phường. '
                     f'Kinh phí tổ chức thực hiện theo {lap_pa.CAN_CU_KINH_PHI}: theo tuyến tối đa 3,5%, cụm / vùng / khác '
                     'tối đa 2,5%.')
        ghi.setWordWrap(True)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Save).setText('Lưu')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        lo.addLayout(form)
        lo.addWidget(ghi)
        lo.addWidget(nut)

    def _kp_theo_ten(self):
        """Đang tự chọn: loại kinh phí theo tên dự án đang gõ (lap_pa.loai_kinh_phi_tu_ten)."""
        if self._kp_tu_dong:
            self.o_loai_kp.setCurrentIndex(self.o_loai_kp.findData(lap_pa.loai_kinh_phi_tu_ten(self.o['ten'].text())))

    def _goi_y_tham_dinh(self):
        """Gợi ý Cơ quan thẩm định theo cấp / tên địa bàn đang nhập (giữ chữ đã gõ)."""
        w = self.o['co_quan_tham_dinh']
        cap, ten = self.o['cap_dia_ban'].currentText(), self.o['ten_dia_ban'].text()
        chu = w.currentText()
        goi_y = [lap_pa.co_quan_tham_dinh_mac_dinh(c, ten) for c in (cap, 'Phường' if cap == 'Xã' else 'Xã')]
        w.blockSignals(True)
        w.clear()
        w.addItems(goi_y)
        w.setEditText(chu)
        w.lineEdit().setPlaceholderText(f'Trống = {goi_y[0]}')
        w.blockSignals(False)

    def gia_tri(self) -> dict:
        return {k: (w.currentText() if isinstance(w, QComboBox) else w.text()) for k, w in self.o.items()}

    def accept(self):
        try:
            lap_pa.luu_du_an(self.con, self.gia_tri())
            # tự chọn theo tên: lưu '' (đổi tên dự án sau này vẫn tự nhận lại); người dùng đã chọn: lưu loại đã chọn
            lap_pa.luu_kinh_phi_to_chuc(self.con, '' if self._kp_tu_dong else (self.o_loai_kp.currentData() or ''), '')
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return
        super().accept()


# ---------------------------------------------------------------- rà soát giá
class HopRaSoat(QDialog):
    COT = [('ma_ho', 'Mã hộ', 60), ('ho_ten', 'Họ và tên', 200), ('stt', 'STT', 50), ('ten', 'Tên tài sản, khoản', 320),
           ('dvt', 'ĐVT', 60), ('don_gia', 'Đơn giá', 100), ('ghi_chu_ra_soat', 'Cần rà soát', 220), ('can_cu_gia', 'Căn cứ giá', 300)]

    def __init__(self, ds: list, parent=None):
        super().__init__(parent)
        self.ds = ds
        self.ma_ho_chon = None
        self.setWindowTitle(f'Rà soát giá trước khi trình – {len(ds)} dòng')
        self.resize(1300, 600)
        self.bang = QTableWidget(len(ds), len(self.COT))
        self.bang.setHorizontalHeaderLabels([c[1] for c in self.COT])
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.verticalHeader().setVisible(False)
        for c, (_, _, w) in enumerate(self.COT):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        for r, x in enumerate(ds):
            for c, (k, _, _) in enumerate(self.COT):
                v = vn(x[k]) if k == 'don_gia' else str(x[k] or '')
                it = QTableWidgetItem(v)
                it.setToolTip(v)
                if 'chưa ghi căn cứ' in x['ghi_chu_ra_soat']:
                    it.setBackground(QBrush(CAM))
                self.bang.setItem(r, c, it)
        self.bang.doubleClicked.connect(lambda *_: self.mo_ho())
        lo = QVBoxLayout(self)
        lo.addWidget(QLabel('Các dòng áp giá tương đương, nhập tay hoặc có đơn giá khác danh mục hiện hành. '
                            'Nhấp đúp một dòng để mở phương án của hộ.'))
        lo.addWidget(self.bang)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        nut.button(QDialogButtonBox.StandardButton.Close).setText('Đóng')
        nut.rejected.connect(self.reject)
        lo.addWidget(nut)
        if not ds:
            lo.insertWidget(0, QLabel('<b>Không có dòng nào cần rà soát.</b>'))

    def mo_ho(self):
        r = self.bang.currentRow()
        if 0 <= r < len(self.ds):
            self.ma_ho_chon = self.ds[r]['ma_ho']
            self.accept()


# ---------------------------------------------------------------- in / xuất
class HopIn(QDialog):
    """Chọn hộ, loại bản in, đầu ra (Excel / Excel + PDF / máy in) và thư mục."""

    def __init__(self, con, parent=None, ma_ho_chon: list | None = None, file_du_an=None, che_do: str | None = None,
                 dot_id: int | None = None):
        from . import in_an
        super().__init__(parent)
        self.con = con
        self.file_du_an = file_du_an
        self.ket_qua = None
        self.setWindowTitle('Xuất hồ sơ & Bản in')
        self.resize(1600, 900)                      # 0.9.84: nửa phải là khung xem trước A4 (vua_man_hinh thu lại theo màn hình)
        # hộ + tình trạng lập phương án: "đã lập" không tính phương án phần mềm tự lập lúc tạo Dự án mới mà chưa soát
        kq = nghiep_vu.tinh_tat_ca(con)
        self.tong = {k.ma_ho: k.tong for k in kq}
        self.lap = in_an.phan_loai_lap(con, {k.ma_ho: k.co_phuong_an for k in kq})
        self.ho = [dict(r) for r in con.execute('SELECT ma_ho, thu_tu, ho_ten FROM ho ORDER BY thu_tu, ma_ho')]
        self.ds_tat_ca = [h['ma_ho'] for h in self.ho]
        self.ds_pa = [m for m in self.ds_tat_ca if self.lap.get(m) == 'da_lap']
        self.ds_tu_lap = [m for m in self.ds_tat_ca if self.lap.get(m) == 'tu_lap']
        self.ds_co_pa = [m for m in self.ds_tat_ca if self.lap.get(m) != 'chua']
        self.ma_ho_chon = [m for m in (ma_ho_chon or []) if m is not None]
        self.cb_pham_vi = QComboBox()
        if self.ma_ho_chon:
            ten = con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (self.ma_ho_chon[0],)).fetchone()[0]
            self.cb_pham_vi.addItem(f'Hộ đang chọn: {ten}' if len(self.ma_ho_chon) == 1
                                    else f'{len(self.ma_ho_chon)} hộ đang chọn', 'chon')
        self.cb_pham_vi.addItem(f'Các hộ đã lập phương án ({len(self.ds_pa)} hộ)', 'pa')
        if self.ds_tu_lap:
            self.cb_pham_vi.addItem(f'Hộ có phương án tự lập, chưa soát ({len(self.ds_tu_lap)} hộ)', 'tu_lap')
            self.cb_pham_vi.addItem(f'Mọi hộ có phương án ({len(self.ds_co_pa)} hộ)', 'co_pa')
        self.cb_pham_vi.addItem(f'Tất cả hộ ({len(self.ds_tat_ca)} hộ)', 'tat_ca')
        self.cb_pham_vi.addItem('Tự chọn trong danh sách bên dưới', 'tu_chon')
        self.cb_pham_vi.currentIndexChanged.connect(lambda _: self._theo_pham_vi())
        # danh sách hộ đánh dấu chọn: lọc theo chữ, chọn nhanh
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm theo STT, họ tên, tình trạng (không cần dấu)…')
        loc_khi_ngung_go(self.o_tim, self._loc)
        self.bang_ho = QTableWidget(len(self.ho), 4)
        self.bang_ho.setHorizontalHeaderLabels(['Chọn', 'STT - Họ và tên', 'Tình trạng phương án', 'Tổng tiền (đ)'])
        self.bang_ho.verticalHeader().setVisible(False)
        self.bang_ho.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang_ho.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        mau_lap = {'da_lap': '#1B5E20', 'tu_lap': '#8A5A00', 'chua': '#7A8794'}
        for i, h in enumerate(self.ho):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, h['ma_ho'])
            self.bang_ho.setItem(i, 0, chk)
            lap = self.lap.get(h['ma_ho'], 'chua')
            for c, v in enumerate((f'{h["thu_tu"]}. {h["ho_ten"]}', in_an.LAP[lap],
                                   vn(self.tong.get(h['ma_ho'], D(0))) if lap != 'chua' else ''), start=1):
                it = QTableWidgetItem(v)
                if c == 2:
                    it.setForeground(QColor(mau_lap[lap]))
                if c == 3:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.bang_ho.setItem(i, c, it)
        for c, w in enumerate((56, 420, 190, 150)):
            self.bang_ho.setColumnWidth(c, w)
        self.bang_ho.horizontalHeader().setStretchLastSection(True)
        self.bang_ho.itemChanged.connect(self._doi_chon)
        self.lb_chon = QLabel()
        hang_chon = QHBoxLayout()
        hang_chon.addWidget(self.o_tim, 1)
        for chu, ham in (('Chọn hộ đã lập', lambda: self._danh_dau(self.ds_pa)),
                         ('Chọn các hộ đang hiện', lambda: self._danh_dau(self._dang_hien(), giu=True)),
                         ('Bỏ chọn tất cả', lambda: self._danh_dau([]))):
            b = QPushButton(chu)
            b.clicked.connect(ham)
            hang_chon.addWidget(b)
        self.o_ct = QCheckBox('Phương án chi tiết từng hộ (mẫu IN_CHITIET, A4 dọc)')
        self.o_ct.setChecked(True)
        self.o_bth = QCheckBox('Bảng tổng hợp (mẫu IN_BANGTONGHOP, A3 ngang)')
        self.o_bth.setChecked(not self.ma_ho_chon)
        # văn bản trình của đợt (0.9.16): tờ trình / văn bản trình - số, ngày lấy theo đợt trình đã chọn; phương án tổng bỏ
        # từ 0.9.69 (người dùng tự làm)
        self.o_tt = QCheckBox('Tờ trình / văn bản trình (mẫu Word / Excel - sửa ở "Trình phê duyệt")')
        self.o_bc = QCheckBox('Báo cáo tiếp thu ý kiến (Word - kết quả niêm yết, lấy ý kiến, đối thoại)')
        # chế độ phát hành (đặc tả V10 phần V): bản DỰ THẢO (niêm yết, họp dân - Bước 6) / bản CHÍNH THỨC (trình thẩm định Bước 8, gửi hộ Bước 11)
        self.r_du_thao = QRadioButton('Bản DỰ THẢO (niêm yết công khai, họp dân - Bước 6)')
        self.r_chinh_thuc = QRadioButton('Bản CHÍNH THỨC (trình thẩm định - Bước 8, gửi từng hộ - Bước 11)')
        self.r_chinh_thuc.setChecked(True)
        self.nhom_che_do = QButtonGroup(self)
        for b in (self.r_du_thao, self.r_chinh_thuc):
            self.nhom_che_do.addButton(b)
        self.lb_che_do = QLabel('')
        self.lb_che_do.setWordWrap(True)
        self.lb_che_do.setProperty('vai', 'phu')
        self.cb_dot = QComboBox()
        self.cb_dot.addItem('(Không theo đợt: số tờ trình, số phương án tổng để trống)', None)
        from . import quan_ly
        try:
            self.ds_dot = quan_ly.ds_dot(con)
        except Exception:                               # file chỉ xem phiên bản cũ
            self.ds_dot = []
        for d in self.ds_dot:
            self.cb_dot.addItem(f'{d.ten} - {d.so_ho} hộ' + (f' - {d.van_ban_trinh}' if d.van_ban_trinh else ''), d.id)
        self.cb_dot.currentIndexChanged.connect(lambda _: self._theo_dot())
        b_het = QPushButton('Chọn tất cả mẫu (in đồng loạt)')
        b_het.clicked.connect(lambda: self.chon_mau(True))
        b_bo = QPushButton('Bỏ chọn mẫu')
        b_bo.clicked.connect(lambda: self.chon_mau(False))
        hang_mau_in = QHBoxLayout()
        hang_mau_in.addWidget(b_het)
        hang_mau_in.addWidget(b_bo)
        hang_mau_in.addStretch(1)
        self.o_chia = QCheckBox('Lưu thành 2 thư mục: "PA CHI TIET" (phương án chi tiết) và "PA TONG" (tờ trình / văn bản trình, '
                                'phương án tổng, bảng tổng hợp)')
        self.o_chia.setChecked(True)
        self.r_excel = QRadioButton('File Excel / Word (.xlsx / .docx)')
        self.r_pdf = QRadioButton('File Excel / Word + PDF (qua Microsoft Excel / Word)')
        self.r_in = QRadioButton('In ra máy in mặc định (qua Microsoft Excel / Word)')
        self.r_pdf.setChecked(True)
        self.nhom_ra = QButtonGroup(self)
        for b in (self.r_excel, self.r_pdf, self.r_in):
            self.nhom_ra.addButton(b)
        # tùy chọn đầu ra
        self.o_gop = QCheckBox('Gộp PDF phương án chi tiết các hộ thành một file (PHUONG_AN_CHI_TIET.pdf)')
        self.o_so_ban = QSpinBox()
        self.o_so_ban.setRange(1, 20)
        self.o_so_ban.setSuffix(' bản / hộ')
        self.o_mo = QCheckBox('Mở thư mục kết quả khi xong')
        self.o_mo.setChecked(True)
        # Nghị định 13/2023/NĐ-CP: bản niêm yết công khai che số CCCD (lưu theo dự án - an_toan.KHOA_CHE_CCCD)
        from .an_toan import can_che_cccd
        self.o_che_cccd = QCheckBox('Che số CCCD - bản niêm yết công khai tại UBND xã (ví dụ 075092******)')
        self.o_che_cccd.setChecked(can_che_cccd(con))
        self.o_che_cccd.setToolTip('Bảo vệ dữ liệu cá nhân (Nghị định 13/2023/NĐ-CP): phương án chi tiết và tờ trình in số CCCD '
                                   'dạng che, bỏ ngày / nơi cấp. Phần mềm nhớ lựa chọn theo dự án.')
        hang_in = QHBoxLayout()
        hang_in.addWidget(self.r_in)
        hang_in.addWidget(QLabel('Số bản:'))
        hang_in.addWidget(self.o_so_ban)
        hang_in.addStretch(1)
        for b in (self.r_excel, self.r_pdf, self.r_in):
            b.toggled.connect(lambda _: self._bat_tuy_chon())
        self._bat_tuy_chon()
        goc = Path(file_du_an).parent if file_du_an else Path.home() / 'Documents'
        self.o_thu_muc = QLineEdit(str(goc / f'BanIn_{datetime.now():%Y%m%d_%H%M}'))
        b_chon = QPushButton('Chọn…')
        b_chon.clicked.connect(lambda: self._chon_thu_muc())
        hang = QHBoxLayout()
        hang.addWidget(self.o_thu_muc, 1)
        hang.addWidget(b_chon)
        form = QFormLayout()
        form.addRow('Chế độ phát hành:', self.r_du_thao)
        form.addRow('', self.r_chinh_thuc)
        form.addRow('', self.lb_che_do)
        form.addRow('Đợt trình:', self.cb_dot)
        form.addRow('Hộ cần in:', self.cb_pham_vi)
        form.addRow('', hang_chon)
        form.addRow('', self.bang_ho)
        form.addRow('', self.lb_chon)
        # mẫu riêng (in_an.ds_mau: IN_CHITIET__<tên>.xlsx, thêm bằng "Mẫu in…"): chọn mẫu cho từng loại bản in
        from . import in_an as _ia
        self.cb_mau_ct, self.cb_mau_bth = QComboBox(), QComboBox()
        for cb, ten_mau, o in ((self.cb_mau_ct, _ia.TEN_CT, self.o_ct), (self.cb_mau_bth, _ia.TEN_BTH, self.o_bth)):
            for t, f in _ia.ds_mau(ten_mau):
                cb.addItem(t, None if t == 'Mẫu chính' else str(f))
                if t.startswith('Dự thảo'):
                    cb.setItemData(cb.count() - 1,
                                   'Chỉ dùng khi áp giá trước khi niêm yết công khai, lấy ý kiến phương án bồi thường '
                                   'theo Luật Đất đai năm 2024 và Nghị định 88/2024/NĐ-CP.',
                                   Qt.ItemDataRole.ToolTipRole)
            cb.setToolTip('Mẫu chính: in chính thức (có số phương án, không chữ dự thảo). '
                          'Dự thảo: chỉ khi áp giá trước niêm yết, lấy ý kiến theo Luật Đất đai 2024 và Nghị định 88/2024/NĐ-CP.')
            cb.setVisible(cb.count() > 1)
            h = QHBoxLayout()
            h.addWidget(o)
            h.addWidget(cb)
            if o is self.o_bth:                     # 16/10/2026: xem trước bảng tổng hợp của các hộ đang đánh dấu ngay trong khung
                self.b_xem_bth = QPushButton('Xem trước bảng tổng hợp')
                self.b_xem_bth.setToolTip('Lập bảng tổng hợp các hộ đang đánh dấu (theo mẫu, chế độ dự thảo / chính thức đang chọn) '
                                          'và hiện ở khung xem trước bên phải')
                self.b_xem_bth.clicked.connect(lambda: self.xem_truoc_bang_tong_hop())
                h.addWidget(self.b_xem_bth)
            h.addStretch(1)
            if o is self.o_ct:
                form.addRow('Bản in:', h)
            else:
                form.addRow('', h)
        form.addRow('', self.o_tt)
        form.addRow('', self.o_bc)
        form.addRow('', hang_mau_in)
        form.addRow('Đầu ra:', self.r_excel)
        form.addRow('', self.r_pdf)
        form.addRow('', self.o_gop)
        form.addRow('', hang_in)
        form.addRow('', self.o_che_cccd)
        form.addRow('Lưu vào thư mục:', hang)
        form.addRow('', self.o_chia)
        form.addRow('', self.o_mo)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText('Thực hiện')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Đóng')
        nut.accepted.connect(lambda: self.thuc_hien())
        nut.rejected.connect(self.reject)
        self.lb = QLabel('Bản in lấy đúng mẫu IN_CHITIET / IN_BANGTONGHOP của file PABT Excel (thư mục mau_in); tờ trình theo mẫu ở '
                         'cửa sổ "Trình phê duyệt" (số văn bản, số phương án tổng lấy theo đợt đã chọn). PDF và máy in '
                         'cần Microsoft Excel (văn bản Word: Microsoft Word) trên máy.')
        self.lb.setWordWrap(True)
        b_mau = QPushButton('Sửa mẫu in trong Excel…')
        b_mau.setToolTip('Mở mẫu phương án chi tiết bằng Excel: sửa chữ, phông, lề, độ rộng cột, kéo đường kẻ... rồi Lưu. '
                         'Giữ nguyên các chỗ trống {du_an}, {ho_ten}, {nguon_goc}...')
        b_mau.clicked.connect(lambda: self.sua_mau())
        hang_mau = QHBoxLayout()
        hang_mau.addWidget(b_mau)
        for chu, loai in (('Sửa mẫu tờ trình…', 'to_trinh'),):
            b = QPushButton(chu)
            b.setToolTip('Mở mẫu bằng Word / Excel để sửa; thêm mẫu từ file Word / Excel / PDF ở cửa sổ "Trình phê duyệt"')
            b.clicked.connect(lambda _=False, x=loai: self.sua_mau_van_ban(x))
            hang_mau.addWidget(b)
        hang_mau.addStretch(1)
        # 0.9.84 (người dùng 14/10/2026): xem trước A4 ngay trong hộp - QSplitter 50/50: trái = tùy chọn (cuộn được khi màn hình
        # hẹp, không ép hộp rộng hơn màn hình 1366), phải = KhungXemTruocTaiLieu luôn hiện. Bấm một hộ -> bản in của hộ đó; đổi chế
        # độ Dự thảo / Chính thức, che CCCD, mẫu -> lập lại (yeu_cau: Excel xuất PDF ở nền, chỉ giữ yêu cầu mới nhất)
        from .xem_truoc_tai_lieu import KhungXemTruocTaiLieu, in_qua_excel
        trai = QWidget()
        lo_trai = QVBoxLayout(trai)
        lo_trai.setContentsMargins(0, 0, 6, 0)
        lo_trai.addLayout(form)
        lo_trai.addLayout(hang_mau)
        lo_trai.addWidget(self.lb)
        lo_trai.addStretch(1)
        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QFrame.Shape.NoFrame)
        cuon.setWidget(trai)
        self.w_preview = KhungXemTruocTaiLieu(self, ham_in=lambda pdf, xlsx: in_qua_excel(self, pdf, xlsx))
        self.w_preview.setMinimumWidth(520)
        self.tach = QSplitter(Qt.Orientation.Horizontal)
        self.tach.addWidget(cuon)
        self.tach.addWidget(self.w_preview)
        self.tach.setChildrenCollapsible(False)
        self.tach.setStretchFactor(0, 1)
        self.tach.setStretchFactor(1, 1)
        self._chia_doi = False
        self._da_keo = False                        # người dùng kéo vạch chia: không ép lại 50/50 khi đổi cỡ hộp
        self.tach.splitterMoved.connect(lambda *_: setattr(self, '_da_keo', True))
        self._ma_xem = None
        lo = QVBoxLayout(self)
        lo.addWidget(self.tach, 1)
        lo.addWidget(nut)
        self._theo_pham_vi()
        for b in (self.r_du_thao, self.r_chinh_thuc):
            b.toggled.connect(lambda dang, x=b: dang and (self._ap_che_do(), self._lam_moi_xem_truoc()))
        self.o_che_cccd.toggled.connect(lambda _: self._lam_moi_xem_truoc())
        self.cb_mau_ct.currentIndexChanged.connect(lambda _: self._lam_moi_xem_truoc())
        self.bang_ho.currentCellChanged.connect(lambda r, c, r0, c0: r != r0 and self.xem_dong(r))
        self.bang_ho.cellClicked.connect(lambda r, c: self.xem_dong(r))
        if dot_id is not None and self.cb_dot.findData(dot_id) >= 0:
            self.cb_dot.setCurrentIndex(self.cb_dot.findData(dot_id))       # -> _theo_dot: hộ của đợt, mọi mẫu, thư mục của đợt
        if che_do in ('du_thao', 'chinh_thuc'):
            self.dat_che_do(che_do)
        else:
            self._ghi_chu_che_do()
        if self.ma_ho_chon:                         # mở từ hộ đang chọn: xem trước ngay hộ đầu
            i = next((i for i, h in enumerate(self.ho) if h['ma_ho'] == self.ma_ho_chon[0]), None)
            if i is not None:
                self.bang_ho.setCurrentCell(i, 1)

    # ---- xem trước A4 (khung bên phải)
    def showEvent(self, e):
        super().showEvent(e)
        if not self._chia_doi:                      # chia đôi theo bề rộng thật - sau khi bố cục xếp xong lần đầu
            self._chia_doi = True
            QTimer.singleShot(0, self.chia_doi)

    def chia_doi(self) -> None:
        w = max(2, self.tach.width() - self.tach.handleWidth())
        self.tach.setSizes([w // 2, w - w // 2])

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._chia_doi and not self._da_keo:
            self.chia_doi()

    def xem_dong(self, r: int) -> None:
        """Xem trước bản in phương án chi tiết của hộ ở dòng r danh sách."""
        it = self.bang_ho.item(r, 0) if r >= 0 else None
        if it is None:
            return
        ma = it.data(Qt.ItemDataRole.UserRole)
        if ma == self._ma_xem and self.w_preview.dang_lap():
            return
        self._ma_xem = ma
        self._lam_moi_xem_truoc()

    def khoa_xem_truoc(self):
        """Khóa bản xem trước: (hộ, dự thảo?, mẫu, che CCCD?) - cùng khóa thì dùng lại bản đã lập trong phiên."""
        return (self._ma_xem, self.che_do() == 'du_thao', self.cb_mau_ct.currentData(), self.o_che_cccd.isChecked())

    def _lam_moi_xem_truoc(self, ngay: bool = False) -> None:
        if self._ma_xem is None:
            return
        from . import in_an
        ma, du_thao, mau, che = self.khoa_xem_truoc()
        ten = next((h['ho_ten'] for h in self.ho if h['ma_ho'] == ma), '')

        def tao(thu_muc):
            return in_an.lap_chi_tiet(self.con, ma, Path(thu_muc) / f'{in_an.ten_file_ho(self.con, ma)}.xlsx', mau,
                                      du_thao=du_thao, che_cccd=che)
        self.w_preview.yeu_cau(self.khoa_xem_truoc(), tao, f'{ten} ({"dự thảo" if du_thao else "chính thức"})', ngay)

    def xem_truoc_bang_tong_hop(self, ngay: bool = False):
        """Xem trước bảng tổng hợp các hộ đang đánh dấu (khóa: danh sách hộ, dự thảo?, mẫu - cùng khóa thì dùng lại bản đã lập).
        Trả khóa đã yêu cầu (None: chưa đánh dấu hộ nào)."""
        from . import in_an
        ds = list(self.ds_ho())
        if not ds:
            if not getattr(self, 'im_lang', False):
                QMessageBox.information(self, TEN_UD, 'Đánh dấu ít nhất một hộ để xem trước bảng tổng hợp.')
            return None
        du_thao, mau = self.che_do() == 'du_thao', self.cb_mau_bth.currentData()
        khoa = ('bth', tuple(ds), du_thao, mau)
        self._ma_xem = None                         # bấm lại một dòng hộ thì xem lại phương án chi tiết của hộ đó

        def tao(thu_muc):
            return in_an.lap_bang_tong_hop(self.con, Path(thu_muc) / 'BangTongHop.xlsx', ds, mau, du_thao=du_thao)
        self.w_preview.yeu_cau(khoa, tao, f'Bảng tổng hợp {len(ds)} hộ ({"dự thảo" if du_thao else "chính thức"})', ngay)
        return khoa

    def done(self, r):
        self.w_preview.don_dep()                    # xóa file tạm %TEMP%\pabt_preview\…
        super().done(r)

    # ---- chế độ phát hành: bản dự thảo / bản chính thức
    def che_do(self) -> str:
        return 'du_thao' if self.r_du_thao.isChecked() else 'chinh_thuc'

    def dat_che_do(self, che_do: str) -> None:
        """Chọn chế độ phát hành và áp bộ cài đặt đi kèm (xem _ap_che_do)."""
        (self.r_du_thao if che_do == 'du_thao' else self.r_chinh_thuc).setChecked(True)
        self._ap_che_do()

    def _chon_mau_theo(self, du_thao: bool) -> bool:
        """0.9.82 (người dùng 14/10/2026 - MỘT bộ mẫu): cả hai chế độ dùng "Mẫu chính"; chữ DỰ THẢO do chế độ phát hành quyết định khi
        in (in_an.ap_che_do_du_thao: dự thảo giữ / tự thêm, chính thức xóa). Mẫu riêng vẫn chọn tay được trong ô. Trước đây chế độ Dự
        thảo tìm mục tên bắt đầu "Dự thảo" - mẫu riêng tên không dấu ("Du thao"), mẫu dự thảo nằm ở thư mục cài trong khi máy đã sửa mẫu
        chính ở %APPDATA% -> báo "chưa có mẫu Dự thảo"; còn mẫu chính có sẵn dòng DỰ THẢO thì bị xóa vì tên file không phải dự thảo."""
        for cb in (self.cb_mau_ct, self.cb_mau_bth):
            cb.setCurrentIndex(0)
        return True

    def _ap_che_do(self) -> None:
        """DỰ THẢO: mẫu in có chữ DỰ THẢO, che số CCCD (NĐ 13/2023/NĐ-CP), chỉ phương án chi tiết + bảng tổng hợp (chưa tờ trình, báo cáo
        tiếp thu). CHÍNH THỨC: mẫu chính (số PA chính thức, không chữ dự thảo), trọn bộ hồ sơ trình - tờ trình, bảng tổng hợp, phương án
        chi tiết, báo cáo tiếp thu ý kiến - số che CCCD theo cài đặt của dự án."""
        from .an_toan import can_che_cccd
        if self.che_do() == 'du_thao':
            self._chon_mau_theo(True)
            self.o_che_cccd.setChecked(True)
            for o, v in ((self.o_ct, True), (self.o_bth, True), (self.o_tt, False), (self.o_bc, False)):
                o.setChecked(v)
        else:
            self._chon_mau_theo(False)
            self.o_che_cccd.setChecked(can_che_cccd(self.con))
            for o in (self.o_ct, self.o_bth, self.o_tt, self.o_bc):
                o.setChecked(True)
        self._ghi_chu_che_do()

    def _ghi_chu_che_do(self) -> None:
        if self.che_do() == 'du_thao':
            self.lb_che_do.setText('In bằng mẫu chính, CÓ chữ "(DỰ THẢO)" (mẫu đã có dòng này thì giữ, chưa có thì phần mềm tự thêm dưới '
                                   'dòng "Số:" và vào tiêu đề bảng tổng hợp), chưa ghi số phương án, tự che số CCCD (NĐ 13/2023/NĐ-CP); '
                                   'dùng khi niêm yết 10 ngày và họp dân lấy ý kiến.')
        else:
            self.lb_che_do.setText('In bằng mẫu chính, KHÔNG có chữ "DỰ THẢO" (phần mềm tự xóa nếu mẫu có), số phương án chính thức theo '
                                   'đợt; trọn bộ: tờ trình, bảng tổng hợp, phương án chi tiết từng hộ, báo cáo tiếp thu ý kiến.')

    # ---- danh sách hộ đánh dấu chọn
    def _theo_pham_vi(self):
        k = self.cb_pham_vi.currentData()
        if k == 'tu_chon':
            self._dem()
            return
        self._danh_dau({'chon': self.ma_ho_chon, 'pa': self.ds_pa, 'tu_lap': self.ds_tu_lap, 'co_pa': self.ds_co_pa,
                        'tat_ca': self.ds_tat_ca}.get(k, []), doi_pham_vi=False)

    def _danh_dau(self, ds, giu: bool = False, doi_pham_vi: bool = True):
        chon = set(ds)
        self.bang_ho.blockSignals(True)
        for i in range(self.bang_ho.rowCount()):
            it = self.bang_ho.item(i, 0)
            if it.data(Qt.ItemDataRole.UserRole) in chon:
                it.setCheckState(Qt.CheckState.Checked)
            elif not giu:
                it.setCheckState(Qt.CheckState.Unchecked)
        self.bang_ho.blockSignals(False)
        if doi_pham_vi:
            self._ve_tu_chon()
        self._dem()

    def _doi_chon(self, it):
        if it.column() == 0:
            self._ve_tu_chon()
            self._dem()

    def _ve_tu_chon(self):
        i = self.cb_pham_vi.findData('tu_chon')
        if self.cb_pham_vi.currentIndex() != i:
            self.cb_pham_vi.blockSignals(True)
            self.cb_pham_vi.setCurrentIndex(i)
            self.cb_pham_vi.blockSignals(False)

    def _dang_hien(self) -> list:
        return [self.bang_ho.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(self.bang_ho.rowCount())
                if not self.bang_ho.isRowHidden(i)]

    def _loc(self, chu: str):
        k = bo_dau(chu).split()
        for i in range(self.bang_ho.rowCount()):
            dong = bo_dau(' '.join(self.bang_ho.item(i, c).text() for c in (1, 2)))
            self.bang_ho.setRowHidden(i, bool(k) and not all(x in dong for x in k))

    def _dem(self):
        ds = self.ds_ho()
        tong = sum((self.tong.get(m, D(0)) for m in ds), D(0))
        tu_lap = sum(1 for m in ds if self.lap.get(m) == 'tu_lap')
        chua = sum(1 for m in ds if self.lap.get(m) == 'chua')
        self.lb_chon.setText(f'Đã chọn {len(ds)} hộ, tổng {vn(tong)} đồng' +
                             (f' — trong đó {tu_lap} hộ phương án tự lập CHƯA SOÁT' if tu_lap else '') +
                             (f', {chua} hộ chưa có phương án' if chua else '') + '.')

    def _bat_tuy_chon(self):
        self.o_gop.setEnabled(self.r_pdf.isChecked())
        self.o_so_ban.setEnabled(self.r_in.isChecked())

    # ---- đợt trình, chọn mẫu in
    def dot_chon(self):
        """quan_ly.Dot đang chọn ở ô "Đợt trình" (None: không theo đợt)."""
        i = self.cb_dot.currentData()
        return next((d for d in self.ds_dot if d.id == i), None)

    def _theo_dot(self):
        """Chọn một đợt: đánh dấu các hộ của đợt và chọn sẵn mọi mẫu (số tờ trình, số / ngày phương án tổng lấy theo đợt)."""
        d = self.dot_chon()
        if d is None:
            return
        from . import quan_ly
        self._danh_dau(quan_ly.ho_cua_dot(self.con, d.id))
        self.chon_mau(True)
        # thư mục lưu theo đợt: <thư mục hồ sơ dự án>\<Tên đợt - k hộ> (thư mục cũ của đợt được đổi tên theo số hộ khi xuất)
        self.o_thu_muc.setText(str(quan_ly.thu_muc_ho_so(self.con, self.file_du_an) / d.ten_thu_muc))
        self._thu_muc_dot_mac_dinh = self.o_thu_muc.text()
        self.o_chia.setChecked(True)

    def chon_mau(self, co: bool):
        """Chọn / bỏ chọn mọi mẫu in (in đồng loạt), hoặc đánh dấu từng mẫu để in riêng lẻ."""
        for o in (self.o_ct, self.o_bth, self.o_tt, self.o_bc):
            o.setChecked(co)

    def sua_mau_van_ban(self, loai: str, mo: bool = True):
        from . import van_ban_trinh as vb
        from .in_an import mo_file
        p = vb.mau_de_sua(loai)
        if mo:
            QMessageBox.information(self, TEN_UD, f'Mở mẫu {vb.LOAI[loai][1].lower()} bằng {"Excel" if p.suffix == ".xlsx" else "Word"}:'
                                    f'\n{p}\n\nSửa xong bấm Lưu rồi đóng. Chỗ trống viết trong ngoặc nhọn, ví dụ {{so_to_trinh}} '
                                    '(danh sách ở cửa sổ "Trình phê duyệt" > "Mã điền tự động {…}…").')
            mo_file(p)
        return p

    def xem_truoc(self):
        """Xem trước (khung bên phải) hộ đầu tiên đang đánh dấu chọn - thay nút "Xem trước bản in…" mở file ra ngoài (trước 0.9.84).
        Trả khung xem trước."""
        ds = self.ds_ho()
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Không có hộ nào để xem.')
            return None
        i = next((i for i, h in enumerate(self.ho) if h['ma_ho'] == ds[0]), -1)
        self.bang_ho.blockSignals(True)
        self.bang_ho.setCurrentCell(i, 1)
        self.bang_ho.blockSignals(False)
        self._ma_xem = ds[0]
        self._lam_moi_xem_truoc(ngay=True)
        return self.w_preview

    def sua_mau(self, mo: bool = True):
        from . import in_an
        try:
            f = Path(self.cb_mau_ct.currentData()) if self.cb_mau_ct.currentData() else in_an.mau_de_sua()
        except (in_an.LoiIn, OSError) as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        if mo:
            QMessageBox.information(self, TEN_UD, f'Mở mẫu in bằng Excel:\n{f}\n\nSửa xong bấm Lưu (giữ định dạng .xlsx) rồi đóng Excel; '
                                    'lần in sau phần mềm dùng mẫu đã sửa. Giữ nguyên các chỗ trống trong ngoặc {…} '
                                    '(tên dự án, họ tên, nguồn gốc…). Lưu mẫu xong, bấm lại một hộ trong danh sách để xem trước '
                                    'ở khung bên phải.')
            in_an.mo_file(f)
        self.w_preview.xoa_nho()                    # mẫu sắp sửa: bản xem trước đã lập trong phiên không còn đúng
        return f

    def _chon_thu_muc(self):
        p = QFileDialog.getExistingDirectory(self, 'Chọn thư mục lưu bản in', self.o_thu_muc.text())
        if p:
            self.o_thu_muc.setText(p)

    def ds_ho(self) -> list:
        """Các hộ đang đánh dấu chọn, theo thứ tự danh sách."""
        return [self.bang_ho.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(self.bang_ho.rowCount())
                if self.bang_ho.item(i, 0).checkState() == Qt.CheckState.Checked]

    def _luu_che_cccd(self) -> bool:
        """Ô "Che số CCCD" đổi: lưu vào dự án (bản in / văn bản trình đọc từ dự án). Dự án mở chỉ xem: báo, không in."""
        import sqlite3
        from . import csdl
        from .an_toan import KHOA_CHE_CCCD, can_che_cccd
        bat = self.o_che_cccd.isChecked()
        if bat == can_che_cccd(self.con):
            return True
        try:
            with self.con:
                csdl.ghi_cai_dat(self.con, KHOA_CHE_CCCD, '1' if bat else '0')
                csdl.ghi_nhat_ky(self.con, 'Đổi chế độ che số CCCD', 'bật (bản niêm yết công khai)' if bat else 'tắt')
        except sqlite3.Error as e:                    # dự án mở chỉ xem
            QMessageBox.warning(self, TEN_UD, chu_loi('Không đổi được chế độ che số CCCD (dự án đang mở chỉ xem?)', e))
            return False
        return True

    def thuc_hien(self, xac_nhan: bool = True):
        from . import in_an
        from . import van_ban_trinh as vb
        ds = self.ds_ho()
        chon = dict(chi_tiet=self.o_ct.isChecked(), bang_tong_hop=self.o_bth.isChecked(), to_trinh=self.o_tt.isChecked(),
                    bao_cao_y_kien=self.o_bc.isChecked())
        if not any(chon.values()):
            QMessageBox.information(self, TEN_UD, 'Chọn ít nhất một loại bản in.')
            return None
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Chưa chọn hộ nào để in: đánh dấu cột "Chọn" trong danh sách hộ.')
            return None
        if not self._luu_che_cccd():
            return None
        tu_lap = [m for m in ds if self.lap.get(m) == 'tu_lap']
        if tu_lap and xac_nhan and QMessageBox.question(
                self, TEN_UD, f'Có {len(tu_lap)} / {len(ds)} hộ đang chọn là phương án phần mềm TỰ LẬP, chưa mở soát và lưu. '
                              'Vẫn in / xuất các hộ này?') != QMessageBox.StandardButton.Yes:
            return None
        in_may = self.r_in.isChecked()
        so_ban = self.o_so_ban.value() if in_may else 1
        if in_may and xac_nhan:
            so = (len(ds) if chon['chi_tiet'] else 0) + sum(1 for k in ('bang_tong_hop', 'to_trinh', 'bao_cao_y_kien') if chon[k])
            if QMessageBox.question(self, TEN_UD, f'Gửi {so} bản in' + (f' × {so_ban} bản' if so_ban > 1 else '') +
                                    ' tới máy in mặc định của Windows?') != QMessageBox.StandardButton.Yes:
                return None
        thu_muc = Path(self.o_thu_muc.text().strip() or '.')
        dot = self.dot_chon() if self.che_do() == 'chinh_thuc' else None        # bản dự thảo: số phương án / văn bản trình để trống
        if dot is not None and self.o_thu_muc.text() == getattr(self, '_thu_muc_dot_mac_dinh', None):
            from . import quan_ly                         # thư mục mặc định của đợt: đổi tên thư mục cũ nếu số hộ đã khác
            thu_muc = quan_ly.thu_muc_cua_dot(thu_muc.parent, dot)
        # chạy dài (hàng trăm hộ, Excel xuất PDF từng file): hộp tiến trình có nút Dừng, giao diện không bị "Không đáp ứng"
        from PySide6.QtWidgets import QProgressDialog
        tien = QProgressDialog('Đang tạo file Excel từng hộ…', 'Dừng', 0, len(ds) + 1, self)
        tien.setWindowTitle(TEN_UD)
        tien.setWindowModality(Qt.WindowModality.WindowModal)
        tien.setMinimumDuration(300)
        tien.setAutoClose(False)
        tien.setAutoReset(False)
        viec = 'in' if in_may else 'xuất PDF'

        def bao_tao(i, n):
            tien.setMaximum(n)
            tien.setValue(min(i, n))
            tien.setLabelText(f'Đang tạo file Excel: {i}/{n}…')
            QApplication.processEvents()
            return tien.wasCanceled()

        def bao_excel(i, n):
            if tien.maximum() != n:
                tien.setMaximum(n)
            tien.setValue(min(i, n))
            tien.setLabelText(f'Microsoft Excel đang {viec}: xong {i}/{n} file…' +
                              ('\n(Đang dừng sau file hiện tại…)' if tien.wasCanceled() else ''))
            QApplication.processEvents()
            return tien.wasCanceled()
        try:
            with con_tro_cho():
                # PA CHI TIET\ phương án chi tiết; PA TONG\ bảng tổng hợp, tờ trình / văn bản trình, phương án tổng (số theo đợt)
                kq = vb.xuat_bo_ho_so(self.con, ds, thu_muc, dot=dot, pdf=self.r_pdf.isChecked(), in_may=in_may,
                                      mau_ct=self.cb_mau_ct.currentData(), mau_bth=self.cb_mau_bth.currentData(),
                                      du_thao=self.che_do() == 'du_thao', so_ban=so_ban, chia_thu_muc=self.o_chia.isChecked(), bao_tien_do=bao_tao, bao_excel=bao_excel,
                                      **chon)
                ct = [f for f in kq['pdf'] if f.name.startswith('PA_')]
                if self.o_gop.isChecked() and self.o_gop.isEnabled() and len(ct) > 1:
                    tien.setLabelText(f'Đang gộp {len(ct)} file PDF…')
                    QApplication.processEvents()
                    try:
                        kq['gop'] = in_an.gop_pdf(ct, kq['thu_muc_ct'] / 'PHUONG_AN_CHI_TIET.pdf')
                    except Exception as e:                 # pypdf báo nhiều loại lỗi khác nhau
                        kq['loi'].append(f'LOI_GOP\t\tKhông gộp được PDF: {e}')
        except (in_an.LoiIn, LoiNhap) as e:
            tien.close()
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        except OSError as e:
            tien.close()
            QMessageBox.warning(self, TEN_UD, chu_loi('Không ghi được file', e))
            return None
        except Exception:                               # lỗi khác (mẫu in, dữ liệu...): không để kẹt hộp tiến trình
            tien.close()                                # (giao_dien.cai_bat_loi báo lỗi)
            raise
        tien.close()
        tien.deleteLater()
        if dot is not None and not kq['loi']:
            try:
                from . import quan_ly
                quan_ly.dat_thu_muc_dot(self.con, dot.id, thu_muc)         # cột "Thư mục đã xuất" của đợt
            except Exception:                              # noqa: BLE001 - dự án mở chỉ xem: không ghi được, bản in vẫn đã xong
                pass
        self.ket_qua = kq
        dung = any(x.startswith(('DA_DUNG', 'LOI_TREO')) for x in kq['loi'])
        tb = f'Đã tạo {len(kq["excel"])} file Excel' + (f', {len(kq["word"])} file Word' if kq.get('word') else '') + \
             (f', {len(kq["pdf"])} file PDF' if kq['pdf'] else '') + \
             (f' (gộp: {kq["gop"].name})' if kq.get('gop') else '') + \
             (' và gửi tới máy in' if in_may and not kq['loi'] else '') + f'.\nThư mục: {thu_muc}'
        if kq['loi']:
            tb += ('\n\nChưa xong:' if dung else '\n\nLỗi:') + '\n' + \
                '\n'.join(x.replace('\t\t', ' – ').replace('\t', ' – ') for x in kq['loi'][:10])
        if xac_nhan:
            QMessageBox.information(self, TEN_UD, tb)
            if self.o_mo.isChecked():
                in_an.mo_file(thu_muc)
            self.accept()
        return kq


__all__ = ['HopIn', 'CuaSoLapPA', 'ChonDanhMuc', 'HopGoiY', 'HopDuAn', 'HopRaSoat', 'TEN_MUC']

"""Màn hình giai đoạn 2: Lập phương án hộ, chọn danh mục / giá tương đương, gợi ý hỗ trợ, thông tin dự án, rà soát giá.

Mọi quy tắc nằm trong lap_pa.BoSoan; ở đây chỉ hiển thị và chuyển thao tác của người dùng.
Các hàm thao tác nhận tham số tùy chọn (mục danh mục, tên, thửa...) để kiểm thử không cần bấm hộp thoại.
"""
from __future__ import annotations
import re
import sqlite3
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QIcon, QKeySequence, QShortcut
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QRadioButton, QScrollArea, QSizePolicy, QSpinBox,
                               QHeaderView, QSplitter, QStyledItemDelegate, QTableWidget, QTableWidgetItem, QTabWidget,
                               QVBoxLayout, QWidget, QGridLayout, QGroupBox)

from . import du_lieu_in
from .giao_dien import dat_kieu_theo_tong  # noqa: E402  (1.0.34: kiểu riêng đổi theo tông nền)
from . import lap_pa, nghiep_vu
from .ho_so import tach_ho_ten
from .lap_pa import NHOM_TIM, BoSoan, DanhMuc, LoiNhap, bo_dau
# in_an (kéo theo openpyxl ~0,2 giây) chỉ nạp trong hộp In / Xuất: mở dự án, cửa sổ lập phương án không phải chờ
from .nghiep_vu import DA_LAP_LUU, MUC_KHOAN, MUC_VN, NGUON_TAY, NGUON_TD, TEN_MUC, so_muc
from .tien import D, KHONG, lam_tron, so_luong_vn, so_vn, vn
from .giao_dien import cat_khoi_bang, dan_vao_bang, gan_cat_dan  # noqa: E402
from .giao_dien import but_so, con_tro_cho, kieu_o_canh_bao, loc_khi_ngung_go, mau_so, mau_theo_tong, nap_o_chon, phong_so, qmau_theo_tong, vua_dong
from .thong_bao import TEN_UD, chu_loi

XAM, VANG, CAM = QColor('#F4F6F8'), QColor('#FFF6D6'), QColor('#FDEBDD')
COT_SO = {'dien_tich', 'gia_bang_gia', 'he_so_k', 'ty_le', 'thanh_tien', 'so_luong', 'don_gia'}

COT_GD = {
    1: [('thua', 'Thửa', 130), ('loai_dat', 'Loại đất', 70), ('dien_tich', 'DT thu hồi (m²)', 100), ('vi_tri', 'Vị trí', 65),
        ('gia_bang_gia', 'Giá đất (đ/m²)', 110), ('he_so_k', 'Hệ số K', 75), ('ty_le', 'Tỷ lệ %', 75),
        ('thanh_tien', 'Thành tiền (đ)', 120), ('ghi_chu', 'Ghi chú', 220)],
}
for _m in (2, 3, MUC_VN):
    COT_GD[_m] = [('ma', 'Mã', 60), ('ten', {2: 'Tên nhà, công trình, tài sản', 3: 'Tên cây trồng', MUC_VN: 'Tên vật nuôi'}[_m], 340),
                  ('dvt', 'ĐVT', 70), ('so_luong', 'Số lượng', 85), ('don_gia', 'Đơn giá (đ)', 110), ('ty_le', 'Tỷ lệ %', 60),
                  ('thanh_tien', 'Thành tiền (đ)', 120), ('nguon', 'Nguồn\ngiá', 110), ('quy_cach', 'Quy\ncách', 170),
                  ('ghi_chu', 'Ghi chú (quy định,\ncách tính)', 240), ('can_cu_gia', 'Căn cứ\ngiá', 200)]
# 1.0.03: tiêu đề cột phụ 2 dòng - sàn tiêu đề (san_tieu_de) đo dòng dài nhất: cột gọn 80-95 px nhường chỗ Tên và cột tiền
COT_GD[4] = [('ma', 'Mã', 60), ('ten', 'Chính sách hỗ trợ', 300), ('cach_tinh', 'Cách tính', 280), ('dvt', 'ĐVT', 70),
             ('so_luong', 'Số lượng', 80), ('don_gia', 'Đơn giá (đ)', 110), ('ty_le', 'Tỷ lệ %', 60),
             ('thanh_tien', 'Thành tiền (đ)', 120), ('ghi_chu', 'Ghi chú (căn cứ)', 280)]
# thẻ của cửa sổ lập phương án: chỉ số thẻ -> mục (0 = hồ sơ hộ). Từ 0.9.21 vật nuôi là thẻ 4 (mục MUC_VN), hỗ trợ thẻ 5 (mục 4)
# 0.9.95 (đặc tả Ultra-Compact): cột ngắn bề rộng gọn; cột chữ (tên, cách tính, quy cách, ghi chú, vị trí) GIÃN chia phần còn lại -
# hết thanh cuộn ngang thừa. Cột vẫn không hẹp hơn chữ tiêu đề (giao_dien.san_tieu_de)
# 0.9.96: Ghi chú / Quy cách thường trống -> bề rộng gọn (không giãn, tiêu đề vẫn đủ chữ nhờ san_tieu_de); phần còn lại giãn cho
# Tên / Vị trí / Chính sách / Cách tính
# 1.0.03 (Ảnh 6): cột phụ Nguồn giá / Quy cách / Căn cứ giá gọn 80-95 px - nhường chỗ cho Tên tài sản / cây trồng và cột tiền
RONG_COT_GON = {'ma': 52, 'dvt': 55, 'so_luong': 72, 'don_gia': 92, 'ty_le': 54, 'thanh_tien': 105, 'nguon': 80,
                'quy_cach': 90, 'ghi_chu': 150, 'can_cu_gia': 95}
COT_GIAN = ('ten', 'cach_tinh', 'vi_tri')
# 1.0.58 (Gói 3 đề án V2.0): chế độ Gọn cột ẩn cột phụ - nhường chỗ cho Tên; đọc / sửa ở khung chi tiết dòng (phím Space). Mặc định tắt
COT_PHU_GON = {'ma', 'nguon', 'quy_cach', 'can_cu_gia'}
KHOA_BANG_GON, KHOA_GHIM_DS_HO = 'lap_pa/bang_gon', 'lap_pa/ghim_ds_ho'
CAO_NUT_DONG = 24                  # nút thao tác dòng (Xóa dòng, Lên, Xuống…) gọn
THE_MUC = (0, 1, 2, 3, MUC_VN, 4)
# 20/10/2026 (ảnh mẫu người dùng): bảng mục dòng 36 px, số / tiền phông số chung (giao_dien.PHONG_SO) canh phải; dải định danh hộ 38 px nền #F1F5F9
CAO_DONG_MUC = 36
KHE_HANG_NHAP = 6               # px: khoảng cách thêm giữa hàng nhân khẩu / tái định cư và hàng nhập chính sách (mục 4)
PHONG_SO = 'Segoe UI'
CAO_DAI_DINH_DANH = 38
# 1.0.51: màn hình thấp (vùng làm việc <= MAN_HINH_THAP điểm - laptop 1366 x 768 @125% còn ~600): dải định danh / lần PA / thanh trên /
# dải đáy sát lại, khung "Cần xem lại" tối đa 2 dòng - nhường ~90 px cho bảng phương án
MAN_HINH_THAP = 680
CAO_DAI_DINH_DANH_GON = 28
CAO_CANH_BAO_GON = 56
TEN_TAB = {0: '0. Hồ sơ & Thửa', 1: '1. Đất', 2: '2. Nhà, công trình', 3: '3. Cây trồng', 4: '4. Vật nuôi',
           5: '5. Hỗ trợ & TĐC'}                  # theo chỉ số thẻ


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


RONG_COT_XOA = 44                  # cột thùng rác cuối bảng mục (px)
MAU_XOA = ('#94A3B8', '#DC2626')   # biểu tượng thùng rác: thường (slate) / rê chuột (đỏ)
# nút phụ của hàng nhập nhanh các mục 2-5: chữ ngắn, mã biểu tượng Segoe MDL2, chú thích (None: giữ chú thích sẵn có)
NUT_PHU_HANG = {'Kiểm tra DT xây dựng…': ('KT diện tích', 0xECC6, 'Kiểm tra diện tích xây dựng'), 'Tính mật độ…': ('Tính mật độ', 0xECC6, 'Tính mật độ cây trồng'),
                'Dán tài sản': ('Dán', 0xE77F, None), 'Gọn cột': ('Gọn cột', 0xE9A6, None),
                'Tự tính hỗ trợ': ('Tự tính hỗ trợ', 0xE945, 'Căn cứ nhân khẩu, di chuyển chỗ ở, diện tích và loại đất của hộ: thêm các khoản hỗ trợ đủ điều kiện vào bảng. Chưa ghi cho tới khi bấm Lưu.')}
SO_NGUYEN_DVT = {'cay', 'con', 'cai', 'bo', 'ho', 'nhan khau', 'nguoi', 'chiec'}


def _so_luong_hien(chu, dvt) -> str:
    """Đơn vị đếm (cây, con, cái…): bỏ đuôi ",0" (số lẻ thật vẫn giữ, không làm mất số liệu)."""
    chu = str(chu if chu is not None else '')
    if bo_dau(str(dvt or '')).lower().strip() in SO_NGUYEN_DVT and re.fullmatch(r'-?[\d.]+,0+', chu):
        return chu.split(',')[0]
    return chu


def _nguon_hien(chu) -> str:
    chu = str(chu if chu is not None else '')
    return chu[:1].upper() + chu[1:]


class NutXoaDong(QStyledItemDelegate):
    """Cột cuối bảng mục: biểu tượng thùng rác giữa ô (người dùng 18/10/2026: thay nút "Xóa dòng" - bấm thẳng vào dòng cần xóa).
    Rê chuột: đỏ. Máy không có phông biểu tượng (Win 7): ký tự ×."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from .giao_dien import icon_ky_hieu
        self.icon = [icon_ky_hieu(0xE74D, m, 16) for m in MAU_XOA]

    def paint(self, p, option, index):
        from PySide6.QtWidgets import QStyle
        super().paint(p, option, index)                 # nền (dòng xen kẽ, đang chọn) như ô khác
        re_ = bool(option.state & QStyle.StateFlag.State_MouseOver)
        ic = self.icon[1 if re_ else 0]
        r = option.rect
        if ic is not None:
            pm = ic.pixmap(16, 16)
            p.drawPixmap(r.x() + (r.width() - 16) // 2, r.y() + (r.height() - 16) // 2, pm)
        else:
            p.save()
            p.setPen(QColor(MAU_XOA[1 if re_ else 0]))
            p.drawText(r, int(Qt.AlignmentFlag.AlignCenter), '×')
            p.restore()

    def createEditor(self, *a):                         # không sửa ô thùng rác
        return None


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
AP_NHIEU_DONG = {'loai_dat', 'vi_tri', 'gia_bang_gia', 'he_so_k', 'ty_le', 'ghi_chu'}
COT_GIA_VAI_TRO = {'don_gia', 'gia_bang_gia', 'he_so_k', 'ty_le', 'nguon', 'can_cu_gia'}   # 1.0.57: vai trò không quyền giá không sửa   # mục 1: sửa một ô -> áp cho mọi dòng đã chọn
# hàng nhập nhanh + danh sách chọn: dùng chung với Dự toán & khái toán (0.9.67) - tên cũ giữ cho mã / test gọi từ man_hinh
from .hang_nhap_nhanh import KIEU_SL, HangNhapNhanh, ds_chon_nhanh, lam_san  # noqa: E402,F401


CHU_TRONG_MUC = {1: 'Chưa có dòng bồi thường đất', 2: 'Chưa có nhà, công trình', 3: 'Chưa có cây trồng',
                 MUC_VN: 'Chưa có vật nuôi', 4: 'Chưa có khoản hỗ trợ'}    # 1.0.03: chữ giữa bảng mục khi chưa có dòng


CHU_BANG_TINH_DAT = 'Bảng tính giá đất (NQ 28 & QĐ 03)'


class BangMuc(QWidget):
    """Một thẻ mục: hàng nhập nhanh (chọn / gõ tên → số lượng → Thêm), bảng dòng phương án, nút Trở lại / Tiếp theo."""

    def __init__(self, man, muc: int):
        super().__init__()
        self.man, self.muc = man, muc
        self.cot = COT_GD[muc]
        self._tao_bang_muc(man, muc)
        nhap = self._tao_hang_nhap(man, muc)
        nut = self._tao_nut_dong(man, muc)
        self._tao_dai_cong()
        lo = QVBoxLayout(self)
        lo.setContentsMargins(6, 4, 6, 4)
        lo.setSpacing(4)
        self._dung_hang_ho_tro(man, muc, lo)
        self._dung_khung_nhap(muc, lo, nhap, nut)
        self._dung_khung_thieu_vn(man, muc, lo)
        self._dung_thanh_gia(man, muc, lo)
        if muc == 4:
            lo.addWidget(self._the_cach_tinh())
        self._dung_khoi_bang(man, lo)
        self._ket_thuc_dung(man, muc)

    def _tao_bang_muc(self, man, muc) -> None:
        """Bảng của mục: cột, ủy quyền ô, phím."""
        # cột cuối (ngoài self.cot): thùng rác xóa dòng (18/10/2026 - thay nút "Xóa dòng")
        self.c_xoa = len(self.cot)
        self.bang = QTableWidget(0, len(self.cot) + 1)
        self.bang.setHorizontalHeaderLabels([c[1] for c in self.cot] + ['Xóa'])
        hd = self.bang.horizontalHeader()
        hd.setStretchLastSection(False)
        for i, c in enumerate(self.cot):
            if c[0] in (('ghi_chu',) if muc == 1 else COT_GIAN):      # 1.0.69: mục 1 Ghi chú giãn hết chỗ thừa; Vị trí gọn, đủ chữ ở chú thích
                hd.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                self.bang.setColumnWidth(i, c[2] if muc == 1 else RONG_COT_GON.get(c[0], c[2]))
        from .giao_dien import giu_cot_gian, san_tieu_de
        san_tieu_de(self.bang)
        hd.setSectionResizeMode(self.c_xoa, QHeaderView.ResizeMode.Fixed)
        self.bang.setColumnWidth(self.c_xoa, RONG_COT_XOA)
        self._giu_gian = giu_cot_gian(self.bang)        # 22/10/2026: cột giãn (Tên, Vị trí…) không bị bóp nát khi thiếu chỗ
        hd.setMinimumHeight(30)
        self.vua_tieu_de()
        # 20/10/2026: chọn TỪNG Ô (nhấp một lần -> Ctrl+C chép ô); Shift / Ctrl chọn nhiều ô - các dòng có ô được chọn là "dòng đang
        # chọn" (mục 1: xóa hàng loạt, đặt cùng vị trí / giá / tỷ lệ cho các thửa đã chọn)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
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
        nut_xoa = NutXoaDong(self.bang)
        self._uy_quyen.append(nut_xoa)
        self.bang.setItemDelegateForColumn(self.c_xoa, nut_xoa)
        self.bang.setMouseTracking(True)                # rê chuột lên thùng rác: đổi màu đỏ
        self.bang.cellClicked.connect(self._bam_o)
        from .giao_dien import gan_chu_khi_trong
        gan_chu_khi_trong(self._bang, CHU_TRONG_MUC.get(muc, 'Chưa có dòng nào'),
                          'Gõ tên vào ô nhập nhanh phía trên rồi bấm "+ Thêm", hoặc "Dán" từ Excel / Word.' if muc != 1
                          else 'Bấm "Thêm thửa vào mục 1" (hoặc thêm tất cả / chọn nhiều thửa) để lập dòng bồi thường đất.')
        # phím Delete trên bảng (không đang sửa ô): xóa dòng / các dòng đang chọn
        self._phim_xoa = QShortcut(QKeySequence(QKeySequence.StandardKey.Delete), self.bang)
        self._phim_xoa.setContext(Qt.ShortcutContext.WidgetShortcut)
        self._phim_xoa.activated.connect(lambda: man.xoa_dong(muc))
        gan_cat_dan(self.bang, lambda: self.dan_o(), lambda: self.cat_o())      # 1.0.78: như Excel; Ctrl+C của cho_phep_sao_chep_bang
        # 1.0.58: Space trên bảng (không đang sửa ô): bật / tắt khung chi tiết dòng dưới bảng
        self.khung_ct = None
        self._phim_ct = QShortcut(QKeySequence(Qt.Key.Key_Space), self.bang)
        self._phim_ct.setContext(Qt.ShortcutContext.WidgetShortcut)
        self._phim_ct.activated.connect(lambda: self.bat_tat_chi_tiet())
        self.bang.currentCellChanged.connect(lambda r, *_: self._nap_chi_tiet(r))
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

    def _tao_hang_nhap(self, man, muc) -> QHBoxLayout:
        """Hàng nhập nhanh."""
        # ---- hàng nhập nhanh
        nhap = QHBoxLayout()
        nhap.setSpacing(8)
        self.nut = {}
        if muc == 1:
            self.cb_thua = QComboBox()
            self.cb_thua.setMinimumWidth(240)
            nhan = QLabel('Thửa:')
            nhan.setProperty('vai', 'nhan')
            nhap.addWidget(nhan)
            nhap.addWidget(self.cb_thua, 1)
            b = QPushButton('Thêm thửa')
            b.setToolTip('Thêm dòng mục 1 cho thửa đang chọn ở ô Thửa')
            from .giao_dien import KieuNut, ap_kieu_nut
            ap_kieu_nut(b, KieuNut.CHINH)            # 1.0.02 (ảnh mẫu): thao tác chính của hàng nhập - nền navy
            b.clicked.connect(lambda: man.them_thua(self.cb_thua.currentData()) if self.cb_thua.count() else man.them_thua())
            nhap.addWidget(b)
            self.nut['Thêm thửa…'] = b
            # 0.9.96: thêm cả loạt thửa (hộ / tổ chức hàng trăm thửa - trước đây thêm từng thửa)
            self.b_them_tat_ca_thua = QPushButton('Thêm tất cả thửa')
            self.b_them_tat_ca_thua.setToolTip('Thêm một dòng mục 1 cho mỗi thửa của hộ chưa có trong mục 1 (loại đất, DT còn lại, vị trí, '
                                               'giá - giá 0 vẫn giữ loại đất)')
            self.b_them_tat_ca_thua.clicked.connect(lambda: man.them_tat_ca_thua())
            self.b_chon_nhieu_thua = QPushButton('Chọn nhiều thửa…')
            self.b_chon_nhieu_thua.setToolTip('Đánh dấu nhiều thửa (lọc theo tờ / loại đất, Ctrl+A chọn tất cả) rồi thêm vào mục 1')
            self.b_chon_nhieu_thua.clicked.connect(lambda: man.chon_nhieu_thua())
            # 1.0.69: nút kép Thêm thửa + mũi tên: các nút cũ giữ làm nguồn lệnh (bật / tắt theo khóa), ẩn, không vào bố cục
            for x in (self.b_them_tat_ca_thua, self.b_chon_nhieu_thua):
                x.setParent(self)
                x.hide()
            self.b_mui_thua = QPushButton('▾')
            self.b_mui_thua.setFixedWidth(34)                # chữ ▾ + mũi tên menu: 24 px cắt chữ
            self.b_mui_thua.setProperty('khong_icon', True)
            self.b_mui_thua.setToolTip('Thêm tất cả thửa, chọn nhiều thửa, tách thửa thành dòng đất mới')
            ap_kieu_nut(self.b_mui_thua, KieuNut.CHINH)
            self.menu_thua = QMenu(self.b_mui_thua)
            self.menu_thua.addAction('Thêm tất cả thửa của hộ', lambda: man.them_tat_ca_thua())
            self.menu_thua.addAction('Chọn nhiều thửa…', lambda: man.chon_nhieu_thua())
            self.menu_thua.addAction('Tách thửa thành dòng đất mới', lambda: man.tach_thua_dong())
            self.b_mui_thua.setMenu(self.menu_thua)
            nhap.addWidget(self.b_mui_thua)
            # 1.0.68: thay nút Tra giá đất NQ 28 (giá gốc, chưa có hệ số K) ở hàng này; lệnh Tra giá vẫn ở menu chuột phải của dòng
            from .giao_dien import chu_hien, icon_ky_hieu
            b = QPushButton(chu_hien(CHU_BANG_TINH_DAT))
            b.setToolTip('Mở bảng tính đơn giá đất: K2, yếu tố ảnh hưởng, hệ số khác, giá đất cụ thể; áp vào dòng đang chọn hoặc nhiều hộ')
            b.clicked.connect(lambda: man.mo_bang_tinh_dat())
            from .giao_dien import TOKEN
            ic = icon_ky_hieu(0xE8EF, TOKEN['chinh'], 16)     # Calculator
            if ic is not None:
                b.setIcon(ic)
            nhap.addWidget(b)
            self.nut[CHU_BANG_TINH_DAT] = b
            self.b_ap_nhanh = QPushButton('Áp giá nhanh ▾')
            self.b_ap_nhanh.setCheckable(True)
            self.b_ap_nhanh.setToolTip('Mở / đóng ngăn áp giá nhanh ngay dưới hàng này')
            nhap.addWidget(self.b_ap_nhanh)
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
            nhap.addWidget(self.hang, 1)
            self.nut['Thêm vào bảng'] = self.hang.nut_them
            from .giao_dien import QSS_NUT_THEM_HANG
            self.hang.nut_them.setText('+ Thêm')
            self.hang.nut_them.setProperty('khong_icon', True)
            self.hang.nut_them.setIcon(QIcon())
            dat_kieu_theo_tong(self.hang.nut_them, QSS_NUT_THEM_HANG)
            self.hang.o_sl.setMinimumWidth(78)
            self.hang.o_sl.setMaximumWidth(100)
            self.hang.o_tl.setMaximumWidth(62)
            self.hang.o_gc.setMinimumWidth(70)
            self.hang.o_gc.setMaximumWidth(180)
            self.hang.o_chon.setMinimumWidth(150)
            self.hang.o_chon.o.setMinimumWidth(0)
            if self.hang.cb_kieu is not None:
                self.hang.cb_kieu.setMaximumWidth(112)
        return nhap

    def _tao_nut_dong(self, man, muc) -> QHBoxLayout:
        """Nút thao tác dòng."""
        # ---- nút thao tác dòng
        nut = QHBoxLayout()
        nut.setSpacing(6)
        ds = []
        if muc == 2:
            ds.append(('Kiểm tra DT xây dựng…', lambda: man.kiem_tra_dt_xay_dung()))
        if muc == 3:
            ds.append(('Tính mật độ…', lambda: man.tinh_mat_do()))
        if muc == 4:
            ds.append(('Tự tính hỗ trợ', lambda: man.tu_tinh_ho_tro()))
        # nút "Xóa dòng" bỏ (18/10/2026): thùng rác ở cột cuối mỗi dòng, phím Delete, menu chuột phải
        ds += [('Dán tài sản', lambda: man.mo_dan_tai_san()), ('▲ Lên', lambda: man.di_chuyen(muc, -1)), ('▼ Xuống', lambda: man.di_chuyen(muc, 1))]
        for ten, ham in ds:
            b = QPushButton(ten)
            b.clicked.connect(ham)
            b.setFixedHeight(CAO_NUT_DONG)
            b.setStyleSheet('QPushButton { padding: 1px 8px; }')
            if ten in ('▲ Lên', '▼ Xuống'):             # 1.0.69: nút biểu tượng 28 px, chữ ở chú thích
                b.setText(ten[0])
                b.setToolTip('Chuyển dòng đang chọn ' + ('lên trên' if ten[0] == '▲' else 'xuống dưới'))
                b.setFixedWidth(28)
                b.setProperty('khong_icon', True)
                b.setStyleSheet('QPushButton { padding: 0; }')
            elif ten == 'Dán tài sản':
                b.setToolTip('Ctrl+Shift+V. Dán / gõ nhiều dòng tài sản: tự xếp vào đúng mục theo bộ đơn giá')
            if muc != 1:                                # chữ ngắn + biểu tượng vector (không emoji: Win 7 không có phông)
                self._nut_gon_hang(b, ten)
            nut.addWidget(b)
            self.nut[ten] = b
        self.b_gon = None
        if muc != 1:                                     # mục 1 không có cột phụ để ẩn
            self.b_gon = QPushButton('Gọn cột')
            self.b_gon.setCheckable(True)
            self.b_gon.setFixedHeight(CAO_NUT_DONG)
            self.b_gon.setStyleSheet('QPushButton { padding: 1px 8px; }')
            self.b_gon.setToolTip('Ẩn cột phụ (Mã, Nguồn giá, Quy cách, Căn cứ giá) để cột Tên rộng hơn. Xem / sửa các cột này ở khung chi '
                                  'tiết dòng: chọn dòng rồi bấm phím Space.')
            self.b_gon.toggled.connect(lambda v: man.doi_bang_gon(v))
            self._nut_gon_hang(self.b_gon, 'Gọn cột')
            nut.addWidget(self.b_gon)
        if muc == 1:
            nut.addStretch(1)
        nut.setContentsMargins(0, 0, 0, 0)
        return nut

    def _xep_cum_nut(self) -> None:
        """Cụm nút phụ: đủ chỗ thì cùng hàng nhập nhanh; hẹp thì xuống hàng dưới, căn phải."""
        k = getattr(self, '_khoi_nut', None)
        if k is None:
            return
        o_hang_2 = self._hang_2.indexOf(k) >= 0
        ds = [w for w in (self.hang.o_chon, self.hang.cb_kieu, self.hang.o_do, self.hang.o_sl, self.hang.o_tl, self.hang.o_gc, self.hang.nut_them)
              if w is not None and w.isVisibleTo(self.hang)]
        can = sum(max(w.minimumWidth(), w.minimumSizeHint().width()) + 8 for w in ds) + k.sizeHint().width() + 60    # 60: ô tên, ghi chú còn chỗ gõ
        hep = self.width() < can
        if hep != o_hang_2:
            (self._hang_nhap if o_hang_2 else self._hang_2).removeWidget(k)
            (self._hang_2 if hep else self._hang_nhap).addWidget(k)
            k.show()                                    # đổi cha làm widget ẩn: hiện lại SAU khi vào bố cục
            self._khung_2.setVisible(hep)

    def _nut_gon_hang(self, b, ten: str) -> None:
        """Nút phụ trên hàng nhập nhanh: cao bằng hàng, chữ ngắn, biểu tượng (NUT_PHU_HANG)."""
        from .giao_dien import TOKEN, icon_ky_hieu
        from .hang_nhap_nhanh import CAO_HANG
        b.setFixedHeight(CAO_HANG)
        if ten not in NUT_PHU_HANG:
            return
        chu, ma, goi_y = NUT_PHU_HANG[ten]
        b.setText(chu)
        if goi_y:
            b.setToolTip(goi_y)
        b.setProperty('khong_icon', True)
        ic = icon_ky_hieu(ma, TOKEN['chinh'], 14)
        if ic is not None:
            b.setIcon(ic)

    def _tao_dai_cong(self) -> None:
        """Dải chân bảng."""
        # dải chân bảng (20/10/2026, ảnh mẫu): "Tổng số: n hạng mục · Ctrl+C…" | "CỘNG MỤC k: … đ" (kiểu QSS_DAI_CONG_MUC)
        self.dai_cong = QFrame()
        self.dai_cong.setObjectName('dai_cong_muc')
        hd = QHBoxLayout(self.dai_cong)
        hd.setContentsMargins(10, 3, 10, 3)
        hd.setSpacing(8)
        self.lb_dem = QLabel('')
        self.lb_dem.setObjectName('dem_muc')
        self.lb_dem.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)   # chữ phụ: co theo chỗ, không đẩy bề rộng tối thiểu
        self.lb_tong = QLabel('')
        self.lb_tong.setObjectName('cong_muc')
        hd.addWidget(self.lb_dem, 1)
        hd.addWidget(self.lb_tong)

    def _dung_hang_ho_tro(self, man, muc, lo) -> None:
        """Mục 4: hàng thông tin hộ dùng tính hỗ trợ."""
        if muc == 4:
            # một hàng: thông tin hộ dùng tính hỗ trợ + tình trạng tái định cư (gọn 26 px, lề 0)
            # 1.0.16: ba khối xếp bằng XepDong - màn hình hẹp (1366 @125%: vùng chữ ~840 điểm, một hàng cứng cần ~955) xuống dòng,
            # không đẩy bề rộng tối thiểu của cả cửa sổ
            from .giao_dien import XepDong
            h = XepDong(None, 14)
            h.setContentsMargins(0, 0, 0, 0)

            def khoi(*ws):
                k = QWidget()
                hk = QHBoxLayout(k)
                hk.setContentsMargins(0, 0, 0, 0)
                hk.setSpacing(6)
                for w in ws:
                    if isinstance(w, QLabel) and w is not man.lb_tl:
                        w.setProperty('vai', 'nhan')
                        w.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)   # nhãn sát ô, không giãn
                    hk.addWidget(w)
                    w.setMaximumHeight(26)
                return k
            h.addWidget(khoi(QLabel('Nhân khẩu:'), man.o_nk, man.o_di_chuyen))
            h.addWidget(khoi(QLabel('DT đất NN đang dùng (m²):'), man.o_dt_nn, man.lb_tl))
            for w in (man.o_nk, man.o_dt_nn):           # cao 28: chữ gợi ý "tự lấy: …" không tụt xuống mép dưới (trước: kiểu ô lớn trong khung 26)
                w.setProperty('nhap', '0')
                w.setMaximumHeight(28)
                w.setMinimumHeight(28)
            man.o_dt_nn.setStyleSheet('QLineEdit { padding: 2px 8px; }')
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
            # 30/10/2026 (người dùng): ô Tái định cư giãn hết phần còn lại của hàng (chữ dài - khoản 4 / 5 Điều 111), nhãn sát ô
            self.cb_tdc.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            self.cb_tdc.setMinimumContentsLength(30)
            self.cb_tdc.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            k_tdc = khoi(nhan, self.cb_tdc)
            h.addWidget(k_tdc)
            h.gian(k_tdc)
            self.cb_tdc.setMinimumWidth(280)
            lo.addLayout(h)
            lo.addSpacing(KHE_HANG_NHAP)          # 30/10/2026 (người dùng): hai hàng nhập (nhân khẩu / chính sách) quá sát nhau

    def _dung_khung_nhap(self, muc, lo, nhap, nut) -> None:
        """Xếp hàng nhập nhanh (mục 1: cùng nút thao tác dòng)."""
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
            for nhom in (ds_w[:4], ds_w[4:]):
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
            # 06/11/2026 (V3.3): nút phụ cùng hàng nhập nhanh, sau vách dọc - bảng thêm một hàng chiều cao
            from .giao_dien import QSS_VACH_HANG_NHAP
            self._khoi_nut = QWidget()
            hk = QHBoxLayout(self._khoi_nut)
            hk.setContentsMargins(0, 0, 0, 0)
            hk.setSpacing(6)
            vach = QFrame()
            vach.setFixedWidth(1)
            dat_kieu_theo_tong(vach, QSS_VACH_HANG_NHAP)
            hk.addWidget(vach)
            hk.addLayout(nut)
            nhap.addWidget(self._khoi_nut)
            nhap.setContentsMargins(0, 0, 0, 0)
            self._hang_nhap = nhap
            self._lo_nhap = QVBoxLayout(khung_nhap)
            self._lo_nhap.setContentsMargins(0, 0, 0, 0)
            self._lo_nhap.setSpacing(4)
            self._lo_nhap.addLayout(nhap)
            self._khung_2 = QWidget()                   # cửa sổ hẹp: cụm nút phụ xuống đây, không bóp ô nhập (_xep_cum_nut)
            self._hang_2 = QHBoxLayout(self._khung_2)
            self._hang_2.setContentsMargins(0, 0, 0, 0)
            self._hang_2.addStretch(1)
            self._lo_nhap.addWidget(self._khung_2)
            self._khung_2.hide()
        lo.addWidget(khung_nhap)

    def _dung_khung_thieu_vn(self, man, muc, lo) -> None:
        """Mục vật nuôi: báo danh mục dự án chưa có vật nuôi."""
        if muc == MUC_VN:
            # dự án lập trước khi bộ đơn giá có vật nuôi (QĐ 31/2025): danh mục dự án không có dòng nào -> ô chọn trống
            self.khung_thieu_vn = QWidget()
            h = QHBoxLayout(self.khung_thieu_vn)
            h.setContentsMargins(0, 0, 0, 0)
            lb = QLabel('Danh mục đơn giá của dự án chưa có vật nuôi (dự án lập trước khi bộ đơn giá có QĐ 31/2025/QĐ-UBND).')
            lb.setWordWrap(True)
            from .giao_dien import TOKEN
            dat_kieu_theo_tong(lb, 'QLabel { color: %s; }' % TOKEN['canh_bao'])
            b = QPushButton('Bổ sung vật nuôi từ bộ đơn giá')
            b.setToolTip('Chỉ thêm các mục vật nuôi còn thiếu vào danh mục dự án - đơn giá khác của dự án giữ nguyên')
            b.clicked.connect(lambda: man.bo_sung_vat_nuoi())
            self.nut['Bổ sung vật nuôi từ bộ đơn giá'] = b
            h.addWidget(lb, 1)
            h.addWidget(b)
            self.khung_thieu_vn.setVisible(False)
            lo.addWidget(self.khung_thieu_vn)

    def _dung_thanh_gia(self, man, muc, lo) -> None:
        """Mục 1: ngăn áp giá nhanh."""
        self.thanh_gia = None
        if muc == 1:
            self.cb_thua.setProperty('nhap', '1')
            from .man_hinh_ap_gia_nhanh import ThanhApGiaNhanh
            self.thanh_gia = ThanhApGiaNhanh(man, self)
            lo.addWidget(self.thanh_gia)
            self.thanh_gia.hide()                       # mặc định đóng: bảng rộng thoáng
            self.b_ap_nhanh.toggled.connect(self.thanh_gia.setVisible)
            self.bang.currentCellChanged.connect(lambda r, c, r0, c0: self.thanh_gia.tinh() if r != r0 else None)
            self.cb_thua.currentIndexChanged.connect(lambda *_: self.thanh_gia.tinh())

    def _dung_khoi_bang(self, man, lo) -> None:
        """Bảng + dải chân bảng."""
        khoi = QVBoxLayout()                          # bảng + dải chân bảng liền nhau
        khoi.setSpacing(0)
        khoi.addWidget(self.bang, 1)
        khoi.addWidget(self.dai_cong)
        self.dai_cong.hide()                          # 1.0.69: số liệu lên dải đáy duy nhất của cửa sổ (_dat_chan); nhãn giữ làm nguồn
        lo.addLayout(khoi, 1)
        self._khoi_bang = khoi
        self.dat_gon(bool(getattr(man, '_bang_gon', False)))

    def _ket_thuc_dung(self, man, muc) -> None:
        """Menu chuột phải, phím, chiều cao dòng, cỡ ô xổ."""
        # nút Trở lại / Tiếp theo: MỘT hàng chung dưới đáy cửa sổ, cùng dải tổng cộng (CuaSoLapPA.hang_dieu_huong)
        self.bang.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bang.customContextMenuRequested.connect(self.menu_dong)
        from .giao_dien import dat_dong_gon, nhap_bang_phim
        nhap_bang_phim(self.bang)                    # Tab / Enter đi giữa các ô, không cần chuột
        # dòng gọn 30-32 px, cao theo chữ thật (vua_dong) - ô Ghi chú / Quy cách trống không làm dòng cao 60-90 px
        dat_dong_gon(self.bang, CAO_DONG_MUC)
        self._hen_vua = QTimer(self)
        self._hen_vua.setSingleShot(True)
        self._hen_vua.setInterval(50)
        self._hen_vua.timeout.connect(self._vua_neu_doi_rong)
        self._hen_vua.timeout.connect(self._xep_cum_nut)    # sau resizeEvent, không xếp trong sự kiện: đổi bố cục ngay thì cha giãn lại, gọi lồng
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
        for w in (self.o_sl, self.o_tl):
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
            (self.lb_od if self.cs_loai == 'od' else self.lb_tn).setText(f'<span style="color:{mau_theo_tong("#B8433A", "chu")}">{e}</span>')

    def nap_dao_tao(self, ma: str):
        from . import chinh_sach as cs
        bo = self.man.bo
        tl = so_vn(cs.ty_le_dao_tao(bo.bc, ma) * 100)
        ds = cs.ds_thua_nn(bo, ma)
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
        vua_dong(self.bang_dt, None, None)
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
        khoa = (id(dm), len(dm.muc.get(self.muc) or ()))
        if getattr(self, '_khoa_nap', None) == khoa:
            return
        self._khoa_nap = khoa
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
        sua_duoc = b.editTriggers() != QAbstractItemView.EditTrigger.NoEditTriggers
        them('Cắt\tCtrl+X', lambda: self.cat_o(), sua_duoc)
        them('Dán\tCtrl+V', lambda: self.dan_o(), sua_duoc)
        m.addSeparator()
        if muc == 1:
            them('Thêm thửa vào mục 1…', lambda: man.them_thua())
            them('Thêm tất cả thửa', lambda: man.them_tat_ca_thua())
            them('Chọn nhiều thửa…', lambda: man.chon_nhieu_thua())
        else:
            them('Thêm dòng (ô nhập nhanh)', lambda: self.hang.o_chon.setFocus())
        them('Giải trình cách tính && căn cứ…\tCtrl+I', lambda: man.xem_giai_trinh_dong(muc, chon[0]), len(chon) == 1)
        them('Chi tiết dòng\tSpace', lambda: self.bat_tat_chi_tiet(), len(chon) == 1)
        m.addSeparator()
        them('Nhân bản dòng', lambda: man.nhan_ban_dong(muc), len(chon) == 1)
        them(f'Xóa {len(chon)} dòng đã chọn' if len(chon) > 1 else 'Xóa dòng', lambda: man.xoa_dong(muc), co)
        m.addSeparator()
        them('▲ Lên', lambda: man.di_chuyen(muc, -1), len(chon) == 1)
        them('▼ Xuống', lambda: man.di_chuyen(muc, 1), len(chon) == 1)
        if muc == 1:
            them('Chọn mọi dòng (Ctrl+A)', lambda: b.selectAll(), b.rowCount() > 0)
            m.addSeparator()
            them('Tra giá đất NQ 28…', lambda: man.tra_gia_dat_nq28(), len(chon) == 1)
            them(CHU_BANG_TINH_DAT.replace('&', '&&') + '…', lambda: man.mo_bang_tinh_dat())
        elif muc == 2:
            m.addSeparator()
            them('Kiểm tra DT xây dựng…', lambda: man.kiem_tra_dt_xay_dung())
            them('Tách phần trong / ngoài ranh thu hồi…', lambda: man.tach_ranh(), len(chon) == 1)
        elif muc == 3:
            m.addSeparator()
            them('Tính mật độ…', lambda: man.tinh_mat_do(), b.rowCount() > 0)
        from .giao_dien import them_muc_sao_chep
        them_muc_sao_chep(m, b, pos)                 # 1.0.04: "Sao chép ô" / "Sao chép cả dòng" đứng đầu menu
        if pos is not None:
            m.exec(b.viewport().mapToGlobal(pos))
            m.deleteLater()
        return m

    def chep_o(self) -> str:
        it = self.bang.currentItem()
        chu = it.text() if it is not None else ''
        QApplication.clipboard().setText(chu)
        return chu

    def dat_gon(self, gon: bool) -> None:
        """Chế độ Gọn cột: ẩn / hiện cột phụ (dữ liệu, sao chép, Tab giữa các ô không đổi - Tab tự bỏ qua cột ẩn)."""
        for i, c in enumerate(self.cot):
            if c[0] in COT_PHU_GON:
                self._bang.setColumnHidden(i, gon)
        if self.b_gon is not None and self.b_gon.isChecked() != gon:
            self.b_gon.blockSignals(True)
            self.b_gon.setChecked(gon)
            self.b_gon.blockSignals(False)

    def bat_tat_chi_tiet(self, hien: bool | None = None) -> bool:
        """Hiện / ẩn khung chi tiết dòng dưới bảng (dựng lần đầu dùng). Trả trạng thái mới."""
        hien = (self.khung_ct is None or self.khung_ct.isHidden()) if hien is None else bool(hien)
        if self.khung_ct is None:
            if not hien:
                return False
            from .man_hinh_phu_lap_pa import KhungChiTietDong
            self.khung_ct = KhungChiTietDong(self)
            self._khoi_bang.insertWidget(1, self.khung_ct)     # vào bố cục TRƯỚC khi hiện (không thành cửa sổ lạ)
        self.khung_ct.setVisible(hien)
        if hien:
            self.khung_ct.nap()
        else:
            self._bang.setFocus()
        return hien

    def _nap_chi_tiet(self, r: int | None = None) -> None:
        if self.khung_ct is not None and not self.khung_ct.isHidden() and not self._dang_ve:
            self.khung_ct.nap(r)

    def dong_chon(self) -> int:
        return self.bang.currentRow()

    def cac_dong_chon(self) -> list:
        """Các dòng đang chọn (tăng dần); không chọn dòng nào thì dòng hiện tại."""
        ds = sorted({i.row() for i in self.bang.selectionModel().selectedIndexes()})
        if not ds and self.bang.currentRow() >= 0:
            ds = [self.bang.currentRow()]
        return ds

    # vẽ lười (máy yếu - 16/10/2026): mở / chuyển hộ chỉ vẽ bảng của thẻ đang xem; thẻ khác vẽ khi hiện ra hoặc khi mã / kiểm thử
    # đọc tới bảng (property bang) - dữ liệu luôn đúng khi được dùng
    _can_ve = False

    @property
    def bang(self):
        if self._can_ve:
            self._can_ve = False
            self.ve()
        return self._bang

    @bang.setter
    def bang(self, v):
        self._bang = v

    def ve_sau(self) -> None:
        """Đánh dấu cần vẽ lại; vẽ khi thẻ hiện ra / bảng được đọc tới."""
        self._can_ve = True

    def vua_tieu_de(self) -> int:
        """Hàng tiêu đề cột đủ số dòng chữ của tiêu đề dài nhất ("Ghi chú (quy định, cách tính)" hai dòng) theo cỡ chữ hiện tại."""
        from PySide6.QtGui import QFontMetrics
        hd = self._bang.horizontalHeader()
        f = QFont(hd.font())
        f.setBold(True)
        dong = max([str(c[1]).count('\n') + 1 for c in self.cot] or [1])
        cao = max(30, QFontMetrics(f).lineSpacing() * dong + 14)
        if hd.minimumHeight() != cao:
            hd.setMinimumHeight(cao)
        return cao

    def showEvent(self, e):
        super().showEvent(e)
        self.vua_tieu_de()
        if self._can_ve:
            self.bang                                   # noqa: B018 - property: vẽ phần còn chờ

    def ve(self, chon: int | None = None):
        self._can_ve = False
        bo = self.man.bo
        n = len(bo.ds(self.muc))
        cu = self._dang_ve                              # vẽ lười có thể chạy giữa _ve_dong: giữ cờ của nơi gọi
        self._dang_ve = True
        try:
            self.bang.setRowCount(n)
            for r in range(n):
                self._ve_dong(r)
        finally:
            self._dang_ve = cu
        self.vua_dong()
        if chon is not None and 0 <= chon < n:
            self.bang.setCurrentCell(chon, 1)
        self._nap_chi_tiet()

    def vua_dong(self):
        """Chiều cao mọi dòng theo chữ thật trên bề rộng cột hiện tại (30-88 px)."""
        from .giao_dien import vua_dong
        vua_dong(self.bang, CAO_DONG_MUC)
        self._rong_da_do = self._rong_cot()

    def _rong_cot(self) -> tuple:
        return tuple(self.bang.columnWidth(c) for c in range(self.bang.columnCount()))

    def _vua_neu_doi_rong(self):
        """Đổi cỡ / hiện lại thẻ: chỉ đo lại khi bề rộng cột thật sự đổi (quay lại thẻ 300 dòng không tốn ~60 ms mỗi lần)."""
        if self._can_ve:                                # thẻ chưa vẽ (đang ẩn): đo khi vẽ
            return
        if self._rong_cot() != self._rong_da_do:
            self.vua_dong()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._hen_vua.start()                       # cột giãn đổi bề rộng: đo lại sau 50 ms (kéo cửa sổ không đo liên tục)

    def _ve_dong(self, r: int):
        bo = self.man.bo
        o = bo.o_dat(r) if self.muc == 1 else bo.o_khoan(self.muc, r)
        sua = lap_pa.SUA_DUOC_DAT if self.muc == 1 else lap_pa.SUA_DUOC_KHOAN
        nguon = '' if self.muc == 1 else bo.pa.khoan[self.muc][r].nguon_gia
        cu = self._dang_ve
        self._dang_ve = True
        try:
            f_so, f_tien = self._phong_so()
            for c, (k, _, _) in enumerate(self.cot):
                it = QTableWidgetItem(_so_luong_hien(o.get(k, ''), o.get('dvt', '')) if k == 'so_luong' else _nguon_hien(o.get(k, '')) if k == 'nguon' else str(o.get(k, '')))
                if k in COT_SO:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    it.setFont(f_tien if k == 'thanh_tien' else f_so)
                    mau = mau_so(it.text(), tien=k == 'thanh_tien')
                    if mau is not None:
                        it.setForeground(but_so(mau))
                if k not in sua:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    it.setBackground(QBrush(qmau_theo_tong(XAM.name())))
                if k == 'nguon' and it.text():
                    self._to_nguon_gia(it, nguon)
                if k in ('ten', 'can_cu_gia', 'quy_cach', 'ghi_chu', 'thua', 'vi_tri'):
                    it.setToolTip(str(o.get(k, '')))
                if k in COT_CONG_THUC and o.get('cong_thuc'):
                    it.setData(Qt.ItemDataRole.UserRole, o['cong_thuc'])          # sửa ô: hiện lại công thức
                    it.setToolTip(f'Công thức: {o["cong_thuc"]} = {o[k]}')
                    it.setForeground(QBrush(QColor('#1F5FA0')))
                if self.muc == 1 and k == 'dien_tich':      # 20/10/2026: vượt DT thu hồi / nguyên thửa - nhắc, không chặn
                    cb = bo.canh_bao_dien_tich(r)
                    if cb:
                        kieu_o_canh_bao(it, cb)
                self.bang.setItem(r, c, it)
            it = QTableWidgetItem('')                   # ô thùng rác (NutXoaDong vẽ biểu tượng)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            it.setToolTip('Xóa dòng này (hoặc chọn dòng rồi nhấn Delete)')
            self.bang.setItem(r, self.c_xoa, it)
        finally:
            self._dang_ve = cu
        if not cu:
            from .giao_dien import cao_can_dong
            self.bang.setRowHeight(r, cao_can_dong(self.bang, r, CAO_DONG_MUC))

    @staticmethod
    def _to_nguon_gia(it, nguon) -> None:
        """Ô Nguồn giá: danh mục xanh, tương đương vàng, nhập tay cam (chữ đậm, căn giữa)."""
        from .giao_dien import MAU_NGUON_GIA
        nen, chu = MAU_NGUON_GIA['td' if nguon == NGUON_TD else 'tay' if nguon == NGUON_TAY else 'dm']
        it.setBackground(QBrush(qmau_theo_tong(nen)))
        it.setForeground(QBrush(qmau_theo_tong(chu)))
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        f = it.font()
        f.setBold(True)
        it.setFont(f)
        it.setToolTip(it.text())

    def _phong_so(self) -> tuple:
        """(phông số, phông thành tiền đậm) cùng cỡ chữ bảng - giao_dien.phong_so (một nguồn, nhớ theo cỡ: Phóng to / Thu nhỏ)."""
        f = self._bang.font()
        return phong_so(f), phong_so(f, dam=True)

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

    def _bam_o(self, r: int, c: int):
        """Bấm ô thùng rác: xóa đúng dòng r (không xóa cả vùng đang chọn)."""
        if c == self.c_xoa and 0 <= r < self.bang.rowCount():
            self.man.xoa_dong(self.muc, r)

    def _ghi_nhieu_o(self, lam) -> dict:
        """Dán / cắt nhiều ô: ghi qua đúng ô bảng (cellChanged -> sua_o); ô sai gom lại báo một lần; một bước Hoàn tác."""
        man = self.man
        man._gom_loi, man._gop_lich_su = [], True
        try:
            kq = lam()
        finally:
            loi, man._gom_loi, man._gop_lich_su = man._gom_loi, None, False
        man._ghi_lich_su()
        kq['loi'] = loi
        bo = kq['bo_qua'] + len(loi)
        man.thong_bao(f'Đã ghi {kq["da_ghi"] - len(loi)} ô' + (f', bỏ qua {bo} ô (không sửa được / sai giá trị)' if bo else '')
                      + (f': {loi[0]}' if loi else '') + '.')
        return kq

    def dan_o(self, chu=None) -> dict:
        """Ctrl+V. Cột Thửa chọn bằng danh sách, không nhận chữ dán."""
        bo = {i for i, c in enumerate(self.cot) if c[0] == 'thua'}
        return self._ghi_nhieu_o(lambda: dan_vao_bang(self.bang, chu, bo_cot=bo))

    def cat_o(self) -> dict:
        bo = {i for i, c in enumerate(self.cot) if c[0] == 'thua'}
        return self._ghi_nhieu_o(lambda: cat_khoi_bang(self.bang, bo_cot=bo))

    def _doi_o(self, r: int, c: int):
        if self._dang_ve or c >= len(self.cot):
            return
        self.man.sua_o(self.muc, r, self.cot[c][0], self.bang.item(r, c).text())
        self._nap_chi_tiet()


# ---------------------------------------------------------------- màn hình lập phương án hộ
# ô chọn hộ của cửa sổ lập phương án (px): rộng tới 560 cho đủ tên hộ / tổ chức; hẹp được tới 160 để hàng nút trên cùng luôn MỘT hàng
# (16/10/2026, người dùng: bỏ nút SCAN, mọi nút lên một dòng) - màn hình 1366 ở 125% còn ~1.090 điểm
RONG_O_HO = (240, 560)
CLIP_TOI_DA = 200_000        # clipboard dài hơn (cả một tài liệu) không tự điền vào hộp Dán danh sách: phân loại sẽ đơ
# 1.0.02 (Hybrid Enterprise Navy cửa sổ con, theo ảnh mẫu người dùng 17/10/2026): nút Dán tài sản nền trắng viền slate chữ đậm,
# biểu tượng xanh trời; rê chuột nền xanh băng viền xanh trời
QSS_NUT_DAN_TS = ('QPushButton#btn_dan_ts { background: #FFFFFF; color: #0F172A; font-weight: 700; border: 1px solid #CBD5E1; '
                  'border-radius: 6px; padding: 0 14px; }'
                  'QPushButton#btn_dan_ts:hover { background: #F0F9FF; border-color: #1F76A6; color: #1A5C85; }'
                  'QPushButton#btn_dan_ts:pressed { background: #E0F2FE; }')
MAU_ICON_DAN_TS = '#1F76A6'


RONG_XEM_TOI_THIEU = 320          # màn hình hẹp: khung xem trước CuaSoLapPA không hẹp hơn chừng này
CHO_XEM_SAU_SUA_MS = 1500          # khung xem trước đang hiện: sửa số liệu xong chừng này mới nhờ Excel lập lại bản in
# 1.0.02 (ảnh mẫu): tắt = nền trắng viền slate chữ navy; bật (đang xem) = nền xanh băng, viền navy, chữ navy đậm
QSS_NUT_XEM_TRUOC = ('QPushButton#btn_toggle_preview { color: #1E3A5F; background: #FFFFFF; border: 1px solid #CBD5E1; '
                     'border-radius: 6px; padding: 0 12px; font-weight: 600; }'
                     'QPushButton#btn_toggle_preview:hover { background: #F1F5F9; border-color: #2563EB; }'
                     'QPushButton#btn_toggle_preview:checked { color: #1E3A5F; background: #EFF6FF; border: 1px solid #1E3A5F; '
                     'font-weight: 700; }'
                     'QPushButton#btn_toggle_preview:checked:hover { background: #DBEAFE; }')
# thẻ Hồ sơ / Đất / Nhà… của cửa sổ lập phương án (ảnh mẫu): kiểu gạch chân giao_dien.QSS_THE_GACH_CHAN (QSS chung, thanh thẻ có
# property vai="gach_chan") - KHÔNG setStyleSheet: trên QTabWidget thì chậm (tính lại kiểu cả cây con), trên chính QTabBar thì Qt5 tính
# bề rộng thẻ theo phông cũ -> cắt chữ hai đầu (bản Win7, 18/10/2026)
from .giao_dien import QSS_THE_GACH_CHAN as QSS_THE_LAP_PA  # noqa: E402,F401  (tên cũ)
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


# 1.0.05: dải "Lần phương án" dưới hàng nút trên cùng (lần đầu + các lần bổ sung của hộ, khóa lần đã phê duyệt)
QSS_DAI_LAN = ('QFrame#dai_lan_pa { background: #FFFBEB; border: 0; border-bottom: 1px solid #FDE68A; }'
               'QFrame#dai_lan_pa[khoa="1"] { background: #F1F5F9; border-bottom: 1px solid #CBD5E1; }'
               'QLabel#lb_lan_pa { color: #0F172A; background: transparent; }')


class HopLanPA(QDialog):
    """Tên, số / ngày phương án, ghi chú của MỘT lần lập phương án (1.0.05)."""

    def __init__(self, parent, x, im_lang: bool = False):
        super().__init__(parent)
        self.im_lang = im_lang
        self.setWindowTitle(f'Lần {x.lan} - thông tin phương án')
        f = QFormLayout(self)
        self.o = {}
        for k, nhan, gt in (('ten', 'Tên lần phương án:', x.ten), ('so_pa', 'Số phương án:', x.so_pa),
                            ('ngay_pa', 'Ngày phương án (dd/mm/yyyy):', x.ngay_pa), ('ghi_chu', 'Ghi chú:', x.ghi_chu)):
            o = QLineEdit(gt or '')
            o.setMinimumWidth(360)
            self.o[k] = o
            f.addRow(nhan, o)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Save).setText('Lưu')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        f.addRow(nut)

    def gia_tri(self) -> dict:
        return {k: o.text().strip() for k, o in self.o.items()}


CAO_NUT_TREN = 28                  # hàng trên cùng cửa sổ lập phương án (chọn hộ + nút lệnh) một hàng (0.9.95: 27; 1.0.02: 28)


TEN_MUC_TONG = {1: 'Đất', 2: 'Nhà', 3: 'Cây', MUC_VN: 'Vật nuôi', 4: 'Hỗ trợ', 5: 'Thưởng'}   # dải tổng cửa sổ lập PA
MAU_MUC_KHONG, MAU_MUC_CO = '#64748B', '#0F172A'


def chu_tong_pa(kq) -> tuple:
    """1.0.03 (Ảnh 6): chữ dải tổng cửa sổ lập phương án có TÊN mục - (đầy đủ, gọn). Mục 0 đồng chữ xám, mục có tiền chữ đậm;
    bản gọn (cửa sổ hẹp) ghi số tiền từng mục kiểu "1,2 tỷ" / "23,5 triệu" (tien.vn_gon); TỔNG CỘNG luôn đủ số."""
    from .tien import vn_gon
    cach = '&nbsp;·&nbsp;'
    tong = f'<span style="color:{mau_theo_tong("#1E3A5F", "chu")}">TỔNG CỘNG: <b>{vn(kq.tong)} đồng</b></span>'
    ra = []
    # mức: đầy đủ; gọn (vn_gon); chỉ mục có tiền (gọn); chỉ TỔNG CỘNG - hẹp tới đâu thì TỔNG CỘNG vẫn hiện đủ
    for gon, bo_khong in ((False, False), (True, False), (True, True)):
        muc = []
        for m in (*THE_MUC[1:], 5):
            x = kq.muc[m]
            if bo_khong and not x:
                continue
            so = (vn_gon(x) if gon else vn(x)) if x else '0'
            mau = mau_theo_tong(MAU_MUC_CO if x else MAU_MUC_KHONG, 'chu')
            muc.append(f'<span style="color:{mau}">{so_muc(m)}. {TEN_MUC_TONG[m]}: '
                       + (f'<b>{so}</b>' if x else so) + '</span>')
        ra.append(cach.join(muc) + ('&nbsp;&nbsp;|&nbsp;&nbsp;' if muc else '') + tong)
    ra.append(tong)
    return tuple(ra)


class NhanTongPA(QLabel):
    """Dải tổng một dòng: đủ chỗ thì chữ đầy đủ, hẹp thì chữ gọn (vn_gon từng mục). Bề rộng ngang Ignored - chữ dài không đẩy cửa sổ
    rộng hơn màn hình; đủ số ở chú thích."""

    def __init__(self):
        super().__init__('')
        from PySide6.QtWidgets import QSizePolicy
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._chu = ('', '')
        self.chu_thich = None                           # chú thích riêng; None: chữ đầy đủ

    def dat(self, du: str, *gon: str) -> None:
        """du: chữ đầy đủ; gon: các mức gọn dần (chọn mức đầu tiên vừa bề rộng; không mức nào vừa: mức gọn nhất)."""
        self._chu = (du, *gon)
        self._chon()

    def _chon(self) -> None:
        du = self._chu[0]
        from PySide6.QtGui import QTextDocument
        doc = QTextDocument()
        doc.setDefaultFont(self.font())
        rong = max(1, self.width() - 4)
        for chu in self._chu:
            doc.setHtml(chu)
            if doc.idealWidth() <= rong:
                break
        if chu != QLabel.text(self):
            self.setText(chu)
        doc.setHtml(du)
        self.setToolTip(self.chu_thich if self.chu_thich is not None else doc.toPlainText().replace('\xa0·\xa0', '\n').replace('\xa0\xa0|\xa0\xa0', '\n'))

    def text(self) -> str:
        """Chữ ĐẦY ĐỦ (như NhanRutGon) - chữ đang vẽ có thể là bản gọn."""
        return self._chu[0] if self._chu[0] else QLabel.text(self)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._chu[0]:
            self._chon()


class _BangMucTre(dict):
    """self.bang[m] dựng BangMuc lần đầu đọc (thẻ chưa xem không dựng lúc mở cửa sổ). .get / values / in không dựng."""

    def __init__(self, man):
        dict.__init__(self)
        self._man = man

    def __contains__(self, m):
        return dict.__contains__(self, m)

    def __getitem__(self, m):
        self._man._dam_bao_bang(m)
        return dict.__getitem__(self, m)


def _ten_ho_hien(ten) -> str:
    """Tên hộ hiển thị: bỏ giá trị rỗng bị nối vào cuối tên (" 0", " None")."""
    return re.sub(r'\s+(?:0|None|none|null)\s*$', '', str(ten or '').strip())


class CuaSoLapPA(QDialog):
    """Hồ sơ và phương án một hộ trong một cửa sổ: thẻ 0 thông tin hộ, thửa đất → 1 đất → 2 nhà, công trình → 3 cây trồng →
    4 vật nuôi → 5 hỗ trợ (Tiếp theo / Trở lại). self.bang theo MỤC (bang[4] = hỗ trợ, bang[MUC_VN] = vật nuôi), thẻ: the_cua."""

    def __init__(self, con, ma_ho: int, parent=None, danh_muc: DanhMuc | None = None, nhung: bool = False):
        super().__init__(parent)
        if nhung:
            # nhúng thành trang tab của cửa sổ chính: đặt cờ Widget NGAY khi chưa có widget con (rà soát 31/10/2026: đặt sau khi đã dựng
            # ~500 widget con tốn ~100 ms, cộng lần chuẩn hóa cờ cửa sổ con ở sự kiện Polish)
            self.setWindowFlags(Qt.WindowType.Widget)
            self.setProperty('nhung_tab', True)
        else:
            self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
            from .giao_dien import chuan_hoa_cua_so_con
            chuan_hoa_cua_so_con(self)                  # đo 1.0.47: setWindowFlags lúc Polish (đã có ~500 widget) = 38 ms
        self.resize(1360, 840)
        self.bo = BoSoan(con, ma_ho, danh_muc)
        self.da_luu = False
        self.thay_doi_csdl = False
        # 1.0.51: lưu tự động sau N giây ngừng thao tác (chu_de.chu_ky_luu_tu_dong) - _kich_hoat_hen_luu_tu_dong / _thuc_hien_luu_tu_dong
        self._hen_luu_tu_dong = QTimer(self)
        self._hen_luu_tu_dong.setSingleShot(True)
        self._hen_luu_tu_dong.timeout.connect(lambda: self._thuc_hien_luu_tu_dong())
        self._luc_doi_dau = None                       # lúc có thay đổi đầu tiên chưa lưu: chờ ngừng gõ không quá 3 chu kỳ
        self._luc_go = 0.0                             # lần gõ phím gần nhất trong ô chữ của thẻ hồ sơ
        self._tao_nut_tren()
        self._dung_thanh_tren()
        self._tao_o_thong_tin_ho()
        cd = self._tao_the_muc(con, ma_ho)
        self._tao_tong_canh_bao()
        self._dung_tach()
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 4)
        from . import giao_dien
        lo.setSpacing(2 if giao_dien.MAT_DO[0] == 'gon' else 4)      # 1.0.33: mật độ Gọn - đầu cửa sổ sát hơn, bảng thêm dòng
        lo.addWidget(self.thanh_tren)
        dd = self._tao_dai_dinh_danh()                 # 20/10/2026; 1.0.69: chữ chuyển vào chú thích ô Hộ, dải ẩn giữ làm nguồn
        lo.addWidget(dd)
        dd.hide()
        self._dung_than(lo)
        self._gan_phim_tat()
        self._to_mau_thanh_tren()
        self._noi_tu_luu_ho_so()
        self._thap = self._man_hinh_thap()
        if self._thap:
            self._gon_man_hinh_thap()
        self._dang_nap = False
        self.nap_ho()
        self.tab.setCurrentIndex(1 if self.bo.pa.dat or any(self.bo.pa.khoan[m] for m in MUC_KHOAN) else 0)
        if cd is not None and str(cd.value(KHOA_GHIM_DS_HO, 'false')).lower() in ('true', '1'):
            self.bat_tat_ds_ho(True, nho=False)

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
        from PySide6.QtWidgets import QScrollArea
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

    def _nap_dinh_danh(self) -> None:
        """Chủ hộ, CCCD, địa chỉ, đợt trình của hộ đang mở (đọc CSDL - đã lưu). Tổ chức: nhãn "Tổ chức:", ẩn CCCD."""
        r = self.bo.con.execute('SELECT h.ho_ten, h.so_cccd, h.dia_chi, d.so AS dot_so, d.ten AS dot_ten FROM ho h '
                                'LEFT JOIN dot_trinh d ON d.id = h.dot_id WHERE h.ma_ho = ?', (self.bo.ma_ho,)).fetchone()
        if r is None:
            return
        from . import ho_so
        tc = ho_so.la_to_chuc(r['ho_ten'])
        self.dd['ten'][0].setText('Tổ chức:' if tc else 'Chủ hộ:')
        self.dd['ten'][1].setText(r['ho_ten'] or '')
        self.dd['cccd'][1].setText(r['so_cccd'] or '—')
        for w in self.dd['cccd']:
            w.setVisible(not tc)
        self.dd['dia_chi'][1].setText(r['dia_chi'] or '—')
        if r['dot_so'] is None:
            dot = 'Chưa xếp đợt'
        else:
            dot = f'Đợt {r["dot_so"]:02d}' + (f' ({r["dot_ten"]})' if r['dot_ten'] else '')
        self.dd['dot'][1].setText(dot)
        self._hien_ten_ho()

    def _dat_tong_dinh_danh(self) -> None:
        """Tổng kinh phí phương án của HỘ (cộng dồn mọi lần lập phương án, gồm số chưa lưu của lần đang soạn)."""
        if not hasattr(self, 'lb_tong_dd'):
            return
        kq = self.bo.ket_qua_cong_don
        self.lb_tong_dd.setText(f'Tổng kinh phí hộ: {vn(kq.tong)} đ')
        if hasattr(self, 'thanh_the'):
            self.thanh_the.vua()
        self.lb_tong_dd.setToolTip('Tổng kinh phí phương án của hộ' + (' - cộng dồn mọi lần lập phương án'
                                                                       if self.cb_lan.count() > 1 else ''))

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

    def _ve_menu_lan(self) -> None:
        """Menu "…": đúng trạng thái bật / tắt, hiện / ẩn của các nút lần phương án (tính ở _nap_lan)."""
        self.menu_lan.clear()
        for b, chu in ((self.b_lan_moi, 'Thêm PA bổ sung…'), (self.b_dieu_chinh, 'Thêm PA điều chỉnh…'), (self.b_sua_lan, 'Sửa lần phương án…'), (self.b_xoa_lan, 'Xóa lần phương án…')):
            if b.isHidden():
                continue
            a = self.menu_lan.addAction(chu, b.click)
            a.setEnabled(b.isEnabled())
            a.setToolTip(b.toolTip())
        self.thanh_pb.them_menu(self.menu_lan)

    def _ve_menu_in(self) -> None:
        """Menu In / Xuất: xem trước, bảng In / Xuất, 4 mẫu theo phiên bản."""
        m = self.menu_in
        m.clear()
        a = m.addAction('Xem trước bản in (F4)', lambda: self.bat_tat_xem_truoc())
        a.setCheckable(True)
        a.setChecked(self.btn_toggle_preview.isChecked())
        m.addAction('In / Xuất…', lambda: self.in_xuat())
        m.addSeparator()
        for ma, chu in (('01', 'Mẫu 1: Dự thảo gửi hộ dân, niêm yết (theo V1)…'), ('02', 'Mẫu 2: Dự thảo điều chỉnh phục vụ đối thoại (theo V2)…'),
                        ('03', 'Mẫu 3: Đối chiếu, giải trình V1 - V2 - V3…'), ('04', 'Mẫu 4: Phương án chính thức trình thẩm định (theo V3)…')):
            m.addAction(chu, lambda k=ma: self.thanh_pb.in_mau(k))

    def _nap_lan(self) -> None:
        ds = self.bo.ds_lan()
        self.cb_lan.blockSignals(True)
        self.cb_lan.clear()
        for x in ds:
            self.cb_lan.addItem(x.nhan, x.lan)
            self.cb_lan.setItemData(self.cb_lan.count() - 1, x.nhan, Qt.ItemDataRole.ToolTipRole)
        self.cb_lan.setCurrentIndex(max(0, self.cb_lan.findData(self.bo.lan)))
        self.cb_lan.blockSignals(False)
        self.cb_lan.setToolTip(self.cb_lan.currentText())
        for w in (self.nhan_lan, self.cb_lan):          # 1.0.69: một lần phương án thì không chiếm chỗ; thêm lần ở menu ⋯
            w.setVisible(len(ds) > 1)
        x = next((y for y in ds if y.lan == self.bo.lan), None)
        pb_mo = getattr(self.bo, 'phien_ban', None)
        self.b_mo_khoa.setVisible(bool(x.khoa) if x is not None else bool(self.bo.khoa) and not pb_mo)   # khóa của LẦN đã phê duyệt, ở mọi phiên bản; khóa của phiên bản: thanh_pb.b_khoa
        self.b_khoa_lan.setVisible(x is not None and x.trang_thai == 'mo_khoa')
        if hasattr(self, 'thanh_pb'):
            self.thanh_pb.nap()
        khong_nhan = self._ho_khong_nhan()
        self.b_xoa_lan.setEnabled(self.bo.lan > 1 and not (x and x.qd) and not khong_nhan)
        self.b_xoa_lan.setVisible(len(ds) > 1)          # 1.0.55: hộ một lần PA - không có lần nào xóa được: nhường chỗ cho chữ tổng
        for b in (self.b_lan_moi, self.b_dieu_chinh, self.b_sua_lan, self.b_mo_khoa, self.b_khoa_lan):
            b.setEnabled(not khong_nhan)       # 1.0.31: bản offline theo hộ - hộ không nhận việc chỉ xem
        if x is not None:
            # 22/10/2026 (nâng cấp giao diện): thẻ nhỏ gọn, KHÔNG kèm danh sách quyết định (chữ dài đẩy ô chọn lần / nút bị cắt)
            # - số, ngày quyết định ở chú thích; màu: đã duyệt chỉ xem xanh lá, đang mở khóa vàng, đang lập lam
            import re
            day_du = x.nhan_trang_thai
            self.lb_trang_thai_lan.setText(re.sub(r'\s*\(QĐ[^)]*\)', '', day_du).replace('ĐÃ PHÊ DUYỆT - CHỈ XEM', 'ĐÃ DUYỆT'))
            self.lb_trang_thai_lan.setToolTip(day_du)
            from .giao_dien import dat_the_nho
            dat_the_nho(self.lb_trang_thai_lan, 'vang' if x.trang_thai == 'mo_khoa' else ('xanh' if self.bo.khoa else 'lam'))
            if pb_mo:                                   # đang xem một phiên bản: thẻ nói đúng phiên bản đó
                self.lb_trang_thai_lan.setText(f'{pb_mo} ĐÃ KHÓA - CHỈ XEM' if self.bo.khoa else f'ĐANG SỬA {pb_mo}')
                if pb_mo == 'V1' and not self.bo.khoa:
                    dat_the_nho(self.lb_trang_thai_lan, 'vang')
        self.dai_lan.setProperty('khoa', '1' if self.bo.khoa else '0')
        self.dai_lan.style().unpolish(self.dai_lan)
        self.dai_lan.style().polish(self.dai_lan)
        self._ds_lan = ds

    def _dat_chu_lan(self) -> None:
        """Chữ tổng ở dải lần: bản gọn hiện trên dải, bản đầy đủ ở chú thích."""
        self.lb_lan.setText(self._chu_lan())
        ds = getattr(self, '_ds_lan', None) or self.bo.ds_lan()
        co = [x for x in ds if x.so_dong or x.lan == self.bo.lan]
        self.lb_lan.setToolTip(f'Tổng tiền lần này: {vn(self.bo.ket_qua.tong)} đ  |  TỔNG CỘNG DỒN CẢ HỘ ({len(co)} LẦN): '
                               f'{vn(self.bo.ket_qua_cong_don.tong)} đ · đã phê duyệt {sum(1 for x in co if x.qd)}/{len(co)} lần')

    def _chu_lan(self) -> str:
        """Chữ tổng: "Tổng tiền lần này: X đ  |  TỔNG CỘNG DỒN CẢ HỘ (N LẦN): Y đ · đã phê duyệt k/N lần"."""
        ds = getattr(self, '_ds_lan', None) or self.bo.ds_lan()
        co = [x for x in ds if x.so_dong or x.lan == self.bo.lan]
        duyet = sum(1 for x in co if x.qd)
        # 1.0.16: ngắn (dải lần ở cửa sổ 1366 chỉ còn ~240 điểm): số liệu đủ ở chú thích (NhanRutGon)
        from .tien import vn_gon
        return (f'Lần này {vn_gon(self.bo.ket_qua.tong)} · Cả hộ ({len(co)} lần) {vn_gon(self.bo.ket_qua_cong_don.tong)} · duyệt {duyet}/{len(co)}')

    def _ap_khoa(self) -> None:
        """Lần đang khóa: bảng mục chỉ xem, tắt ô / nút nhập; lần đang lập: như cũ."""
        k0 = bool(self.bo.khoa) or self._ho_khong_nhan()
        vt = getattr(self.bo.con, '_vai_tro', None)
        from PySide6.QtWidgets import QAbstractButton, QAbstractSpinBox
        for bm in self.bang.values():
            k = k0
            if vt is not None and not k:                # 1.0.57: vai trò không sửa mục này (kiểm đếm viên: mục hỗ trợ; kế toán…)
                from . import phan_quyen
                q = phan_quyen.quyen_bang(vt, 4 if bm.muc == 4 else bm.muc)
                k = not (q['khoi_luong'] or q['gia'])
            b = bm._bang                               # không đọc bm.bang: thuộc tính đó vẽ thẻ chưa hiện (vẽ lười)
            if not hasattr(bm, '_et_goc'):
                bm._et_goc = b.editTriggers()
            b.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers if k else bm._et_goc)
            for w in bm.findChildren(QWidget):
                if isinstance(w, (QAbstractButton, QLineEdit, QComboBox, QAbstractSpinBox)) and not b.isAncestorOf(w) \
                        and w is not b and w is not bm.b_gon \
                        and not (bm.thanh_gia is not None and bm.thanh_gia.isAncestorOf(w)) and w is not bm.nut.get(CHU_BANG_TINH_DAT) \
                        and not (bm.khung_ct is not None and bm.khung_ct.isAncestorOf(w)):   # 1.0.58: chỉ đổi cách xem / ô tự chỉ đọc
                    w.setEnabled(not k)
            if bm.thanh_gia is not None:               # tự bật / tắt: V1 khóa vẫn áp được, ghi vào nhánh V2
                bm.thanh_gia.cap_nhat_khoa()
        from . import phan_quyen
        self.b_dan.setEnabled(not k0 and phan_quyen.quyen_bang(vt, 2)['khoi_luong'])

    def _ap_trang_thai_khoa(self) -> None:
        self._ap_khoa()

    def _ho_khong_nhan(self) -> bool:
        """Bản offline theo hộ (máy chủ LAN) mà hộ đang mở không thuộc danh sách nhận việc: chỉ xem (1.0.31)."""
        from .lap_pa import ho_nhan_viec
        ds = ho_nhan_viec(self.bo.con)
        return ds is not None and self.bo.ma_ho is not None and int(self.bo.ma_ho) not in ds

    def chuyen_lan(self, lan) -> bool:
        return self.chon_lan(lan)

    def chon_lan(self, lan) -> bool:
        if lan is None or lan == self.bo.lan:
            return True
        if not self.hoi_luu():
            self._nap_lan()
            return False
        self.bo.mo(self.bo.ma_ho, int(lan))
        self.nap_ho()
        self.lam_moi_xem_truoc()
        return True

    def lap_bo_sung(self, ten: str | None = None):
        """Lập phương án bổ sung (lần mới) cho hộ đang mở. ten None: hỏi tên (mặc định "Phương án bổ sung lần k")."""
        if not self.hoi_luu():
            return None
        from .lan_pa import ten_mac_dinh
        so = max(x.lan for x in self.bo.ds_lan()) + 1
        if ten is None:
            if getattr(self, 'im_lang', False):
                ten = ''
            else:
                ten, ok = QInputDialog.getText(self, TEN_UD, 'Tên phương án bổ sung (ví dụ: Bổ sung cây trồng, chính sách thuê nhà):',
                                               text=ten_mac_dinh(so))
                if not ok:
                    return None
        try:
            lan = self.bo.lap_bo_sung(ten or '')
        except LoiNhap as e:
            if not getattr(self, 'im_lang', False):
                QMessageBox.warning(self, TEN_UD, str(e))
            return None
        self.thay_doi_csdl = True
        self.nap_ho()
        self.thong_bao(f'Đã lập phương án bổ sung - lần {lan}. Thêm tài sản / chính sách bổ sung rồi bấm Lưu; các lần trước giữ '
                       'nguyên.')
        self.tab.setCurrentIndex(1)
        return lan

    def lap_dieu_chinh(self, ten: str | None = None):
        """Lập phương án điều chỉnh từ lần đang xem (xem lap_pa.BoSoan.lap_dieu_chinh). ten None: hỏi tên."""
        if not self.hoi_luu():
            return None
        from .lan_pa import TEN_LOAI, DIEU_CHINH
        if ten is None:
            if getattr(self, 'im_lang', False):
                ten = ''
            else:
                ten, ok = QInputDialog.getText(self, TEN_UD, 'Tên phương án điều chỉnh (ví dụ: Điều chỉnh cây trồng):',
                                               text=TEN_LOAI.get(DIEU_CHINH, 'Điều chỉnh'))
                if not ok:
                    return None
        try:
            lan = self.bo.lap_dieu_chinh(None, ten or '')
        except LoiNhap as e:
            if not getattr(self, 'im_lang', False):
                QMessageBox.warning(self, TEN_UD, str(e))
            return None
        self.thay_doi_csdl = True
        self.nap_ho()
        self.thong_bao(f'Đã lập phương án điều chỉnh - lần {lan} (chép từ lần gốc). Sửa số liệu rồi bấm Lưu.')
        self.tab.setCurrentIndex(1)
        return lan

    def sua_lan(self, gia_tri: dict | None = None) -> bool:
        from . import lan_pa
        x = lan_pa.lan_cua(self.bo.con, self.bo.ma_ho, self.bo.lan)
        if gia_tri is None:
            d = HopLanPA(self, x)
            if d.exec() != QDialog.DialogCode.Accepted:
                return False
            gia_tri = d.gia_tri()
        try:
            lan_pa.sua_lan(self.bo.con, self.bo.ma_ho, self.bo.lan, **gia_tri)
        except Exception as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không lưu được thông tin lần phương án', e))
            return False
        self.thay_doi_csdl = True
        self._nap_lan()
        self._dat_chu_lan()
        return True

    def mo_khoa_lan(self, xac_nhan: bool | None = None, ly_do: str | None = None) -> bool:
        """Mở khóa tạm lần đã phê duyệt: hỏi LÝ DO (bắt buộc, ghi nhật ký cảnh báo)."""
        if not self.bo.khoa:
            return False
        if ly_do is None and not getattr(self, 'im_lang', False):
            ly_do, ok = QInputDialog.getText(
                self, TEN_UD, f'Lần {self.bo.lan} đã có quyết định phê duyệt. Số liệu đã ghi trong quyết định GIỮ NGUYÊN - sau khi sửa '
                'cần ban hành quyết định điều chỉnh. Chỉ bổ sung tài sản / chính sách mới thì dùng "+ Lập PA bổ sung".\n\n'
                'Lý do mở khóa sửa (ghi nhật ký):')
            if not ok or not ly_do.strip():
                return False
            xac_nhan = True
        if xac_nhan is None:
            xac_nhan = getattr(self, 'im_lang', False)
        if not xac_nhan:
            return False
        from . import lan_pa
        lan_pa.mo_khoa_lan(self.bo.con, self.bo.ma_ho, self.bo.lan, ly_do or '')
        self.bo.mo_phien_ban(getattr(self.bo, 'phien_ban', None))     # đang xem V2, V3: ở lại phiên bản đó
        self.nap_ho()
        return True

    def khoa_lai_lan(self) -> bool:
        """Khóa lại lần đang mở khóa điều chỉnh. Có thay đổi chưa lưu: hỏi trước như khi rời hộ."""
        if not self.hoi_luu():
            return False
        from . import lan_pa
        lan_pa.khoa_lai(self.bo.con, self.bo.ma_ho, self.bo.lan)
        self.bo.mo_phien_ban(getattr(self.bo, 'phien_ban', None))     # đang xem V2, V3: ở lại phiên bản đó
        self.nap_ho()
        return True

    def xoa_lan(self, xac_nhan: bool | None = None) -> bool:
        if self.bo.lan <= 1:
            return False
        if xac_nhan is None:
            xac_nhan = getattr(self, 'im_lang', False) or QMessageBox.question(
                self, TEN_UD, f'Xóa lần {self.bo.lan} (phương án bổ sung chưa phê duyệt) cùng mọi dòng của lần này?') \
                == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return False
        from . import lan_pa
        try:
            lan_pa.xoa_lan(self.bo.con, self.bo.ma_ho, self.bo.lan)
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return False
        self.thay_doi_csdl = True
        self.bo.mo(self.bo.ma_ho)
        self.nap_ho()
        return True

    def _nap_ds_ho(self):
        self.cb_ho.blockSignals(True)
        ds = []
        for ma, tt, ten in self.bo.danh_sach_ho():
            ten = _ten_ho_hien(ten)
            ds.append((f'{tt}. {tach_ho_ten(ten)[0]}', ma, f'{tt}. {ten}'))    # không hiện "(mã n)" (16/10/2026); ô chỉ tên riêng, đủ câu ở chú thích (06/11/2026)
        nap_o_chon(self.cb_ho, ds)
        self.cb_ho.blockSignals(False)
        self._hien_ten_ho()

    def _hien_ten_ho(self):
        """Ô chọn hộ: chữ hiện từ ĐẦU tên (ô sửa được mặc định cuộn về cuối chữ), chú thích = tên đầy đủ."""
        o = self.cb_ho.lineEdit()
        if o is not None:
            o.setCursorPosition(0)
        dd = getattr(self, 'dd', None)
        if dd:                                         # 1.0.69: Họ tên - CCCD - Địa chỉ - Đợt ở chú thích (dải định danh đã gộp)
            self.cb_ho.setToolTip(' - '.join(x for x in (dd['ten'][1].text() or self.cb_ho.currentText(), dd['cccd'][1].text(), dd['dia_chi'][1].text(), dd['dot'][1].text()) if x and x != '—'))
        else:
            self.cb_ho.setToolTip(self.cb_ho.currentText())

    def _dam_bao_bang(self, m: int) -> None:
        """Dựng BangMuc mục m lần đầu (thẻ đang xem / lệnh đọc self.bang[m])."""
        if dict.__contains__(self.bang, m) or m in self._dang_dung_bang or m not in THE_MUC[1:]:
            return
        self._dang_dung_bang.add(m)
        try:
            the = the_cua(m)
            bm = BangMuc(self, m)
            cu = self.tab.widget(the)
            giu = self.tab.currentIndex()
            nhan = self.tab.tabText(the)
            self.tab.blockSignals(True)
            self.tab.removeTab(the)
            self.tab.insertTab(the, bm, nhan or TEN_TAB[the])
            if 0 <= giu < self.tab.count():
                self.tab.setCurrentIndex(giu)
            self.tab.blockSignals(False)
            dict.__setitem__(self.bang, m, bm)
            if cu is not None:
                cu.deleteLater()
            if m == 4:
                h = self.bo.pa.ho
                cb = bm.cb_tdc
                cb.blockSignals(True)
                cb.setCurrentText(h.tai_dinh_cu or lap_pa.TAI_DINH_CU[0])
                le = cb.lineEdit()
                if le is not None:
                    le.setCursorPosition(0)
                cb.blockSignals(False)
            bm.nap_danh_sach()
            if bm.isVisible():
                bm.ve()
            else:
                bm.ve_sau()
            kq = self.bo.ket_qua
            n = len(self.bo.ds(m))
            bm.lb_tong.setText(
                f'CỘNG MỤC {so_muc(m)} ({TEN_TAB[the].split(". ", 1)[-1].upper()}): {vn(kq.muc[m])} đồng')
            bm.lb_dem.setText(
                f'Tổng số: <b>{n:02d}</b> {"dòng đất" if m == 1 else "hạng mục"}  ·  Ctrl+C: sao chép ô')
            bm.lb_dem.setToolTip(
                'Chọn ô rồi bấm Ctrl+C sao chép giá trị; Ctrl+Shift+C hoặc chuột phải: sao chép cả dòng')
            self._ap_khoa()
        finally:
            self._dang_dung_bang.discard(m)

    def hang_dieu_huong(self, the: int | None = None) -> QHBoxLayout:
        """0.9.95: MỘT hàng dưới đáy cửa sổ (28 px) = dải tổng cộng `lb_tong` + ◀ Trở lại / Tiếp theo ▶ theo thẻ đang xem (trước
        0.9.95 mỗi thẻ một hàng nút riêng cao 40 px). Thẻ cuối không có nút lưu riêng: "Lưu (Ctrl+S)" ở thanh trên.
        1.0.02: hàng nằm trong khung `dai_dieu_huong` (nền slate, vạch trên) - trả về layout của khung."""
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

    def _cap_nhat_dieu_huong(self, the: int):
        co_lui, co_tien = the > 0, the < len(THE_MUC) - 1
        self.b_tro_lai.setVisible(co_lui)
        self.b_tiep_theo.setVisible(co_tien)
        if co_lui:
            self.b_tro_lai.setToolTip(f'Về mục {TEN_TAB[the - 1]}')
        if co_tien:
            self.b_tiep_theo.setToolTip(f'Sang mục {TEN_TAB[the + 1]}')
        if hasattr(self, 'lb_chan') and hasattr(self, 'bo') and getattr(self, '_dang_nap', True) is False:
            self._dat_chan()
        if 0 < the < len(THE_MUC):
            m = THE_MUC[the]
            self._dam_bao_bang(m)
            if m in MUC_KHOAN:
                self.bang[m].nap_danh_sach()

    def _dat_chan(self, kq=None) -> None:
        """Dải đáy duy nhất (1.0.69): số dòng, cộng mục đang xem, tổng phương án; chi tiết từng mục ở chú thích."""
        kq = kq or self.bo.ket_qua
        i = self.tab.currentIndex()
        if 0 < i < len(THE_MUC):
            m = THE_MUC[i]
            chu = f'Tổng số: {len(self.bo.ds(m))} dòng  |  Cộng mục đang xem: {vn(kq.muc[m])} đ  |  '
        else:
            chu = f'Tổng số: {self.ho_so.bang.rowCount()} thửa  |  '
        gon = f'<b>TỔNG: {vn(kq.tong)} đ</b>'
        giua = f'Cộng mục: {vn(kq.muc[THE_MUC[i]])} đ  |  {gon}' if 0 < i < len(THE_MUC) else gon
        self.lb_chan.chu_thich = self.lb_tong.text()
        vung = self._vung_chon_dang_hien()
        if vung:                                        # quét chọn nhiều ô: số của vùng chọn thay chữ thường
            self.lb_chan.dat(*vung[1:], gon)
        else:
            du = f'{chu}<b>TỔNG CỘNG PHƯƠNG ÁN: {vn(kq.tong)} đồng</b>'
            self.lb_chan.dat(f'{du}  (Mẹo: Quét chọn nhiều ô để tính tổng nhanh · Ctrl+C sao chép)', du, giua, gon)
        f_dam = self.lb_chan.font()
        f_dam.setBold(True)
        self.lb_chan.setMinimumWidth(QFontMetrics(f_dam).horizontalAdvance(f'TỔNG: {vn(kq.tong)} đ') + 8)

    def _vung_chon_dang_hien(self) -> tuple | None:
        """Vùng chọn còn hiệu lực để hiện ở dải đáy. Bảng đã bị hủy phía C++ (nhập lại mục, đóng hộp chứa bảng): coi như hết vùng chọn và quên luôn."""
        vung = getattr(self, '_chu_vung', None)
        if not vung:
            return None
        try:
            return vung if vung[0].isVisible() else None
        except RuntimeError:
            self._chu_vung = None
            return None

    def cap_nhat_bo_dem(self, bang, tk: dict) -> None:
        """Bộ đếm vùng chọn của mọi bảng trong cửa sổ (giao_dien._BoChonVung tìm hàm này ở cha gần nhất). Hiện ngay trên dải đáy."""
        self.lb_bo_dem.dat(tk)
        self.lb_goi_y_bo_dem.setVisible(not self.lb_bo_dem.text())
        self._chu_vung = self._tinh_vung_chon(bang)
        self._dat_chan()

    def _tinh_vung_chon(self, bang) -> tuple | None:
        """Nhiều ô đang chọn: (bảng, chữ đầy đủ, chữ gọn) - số dòng, số ô, tổng số lượng / diện tích, đơn giá trung bình, tổng thành tiền. Đọc theo tiêu đề cột."""
        from .giao_dien import MAU_CHU_VUNG_CHON, mau_theo_tong
        from .tien import KHONG, doc_so_vn
        ds = bang.selectedIndexes()
        if len(ds) < 2:
            return None
        sl, tt, gia = KHONG, KHONG, []
        co_sl = co_tt = False
        co_muc_dau = hasattr(bang, 'horizontalHeaderItem')   # QTableWidget có mục tiêu đề; QTableView đọc từ mô hình
        for ix in ds:
            if co_muc_dau:
                it = bang.horizontalHeaderItem(ix.column())
                cot = it.text().replace('\n', ' ') if it is not None else ''
            else:
                cot = str(bang.model().headerData(ix.column(), Qt.Orientation.Horizontal) or '').replace('\n', ' ')
            chu = str(ix.data() or '').strip()
            if not chu or not (cot.startswith(('Số lượng', 'Diện tích', 'DT ')) or cot.startswith('Đơn giá') or cot.startswith('Thành tiền')):
                continue
            try:
                v = doc_so_vn(chu)
            except (ValueError, ArithmeticError, LoiNhap):
                continue
            if cot.startswith('Đơn giá'):
                gia.append(v)
            elif cot.startswith('Thành tiền'):
                tt, co_tt = tt + v, True
            else:
                sl, co_sl = sl + v, True
        phan = [f'Đang chọn: {len({ix.row() for ix in ds})} dòng ({len(ds)} ô)']
        if co_sl:
            phan.append(f'Tổng SL/DT: {so_vn(sl)}')
        if gia:
            phan.append(f'Đơn giá TB: {vn(sum(gia, KHONG) / len(gia))} đ')
        if co_tt:
            phan.append(f'Tổng Thành tiền vùng chọn: {vn(tt)} đồng')
        if len(phan) == 1:                              # bảng không có các cột đó: bộ đếm chung (Trung bình, Đếm, Tổng)
            phan.append(self.lb_bo_dem.text())
        mau = mau_theo_tong(MAU_CHU_VUNG_CHON, 'chu')
        return (bang, f'<b style="color:{mau}">' + '  |  '.join(x for x in phan if x) + '</b>',
                f'<b style="color:{mau}">' + '  |  '.join(x.replace('Tổng Thành tiền vùng chọn', 'Thành tiền') for x in phan[1:] if x) + '</b>')

    def sang_the(self, the: int) -> bool:
        """Chuyển thẻ; rời thẻ hồ sơ hộ có sửa đổi thì lưu hồ sơ trước (để thửa mới dùng được ở mục 1)."""
        if self.tab.currentIndex() == 0 and the != 0 and self.ho_so.co_thay_doi() and not self.ho_so.luu():
            return False
        self.tab.setCurrentIndex(the)
        if THE_MUC[the] in MUC_KHOAN:
            self.bang[THE_MUC[the]].o_chon.o.setFocus()
        return True

    # ---------------------------------------------- hiển thị
    def bat_tat_ds_ho(self, hien: bool | None = None, nho: bool = True) -> bool:
        """Ghim / bỏ ghim danh sách hộ bên trái (Ctrl+B; dựng lần đầu dùng). Trả trạng thái mới."""
        hien = (self._w_ds_ho is None or self._w_ds_ho.isHidden()) if hien is None else bool(hien)
        if self._w_ds_ho is None and hien:
            from .man_hinh_phu_lap_pa import KhungDsHo
            self._w_ds_ho = KhungDsHo(self)
            self._lo_tach.insertWidget(0, self._w_ds_ho)      # vào bố cục TRƯỚC khi hiện (không thành cửa sổ lạ)
        if self._w_ds_ho is not None:
            if hien:
                self._w_ds_ho.setFixedWidth(self._rong_ds_ho())
            self._w_ds_ho.setVisible(hien)
            if hien:
                self._w_ds_ho.nap()
        self.b_ds_ho.setChecked(hien)
        if nho:
            from .giao_dien import cai_dat_nho
            cd = cai_dat_nho()
            if cd is not None:
                cd.setValue(KHOA_GHIM_DS_HO, hien)
        return hien

    def _rong_ds_ho(self, rong_man: int | None = None) -> int:
        """Bề rộng danh sách ghim: RONG_DS_HO; màn hình không đủ chỗ cho phần soạn + danh sách (1366 @125%) thì hẹp lại, không dưới 120,
        để cửa sổ không rộng hơn màn hình (tên dài: xem chú thích khi rê chuột)."""
        from .man_hinh_phu_lap_pa import RONG_DS_HO
        if rong_man is None:
            man = self.screen() or QApplication.primaryScreen()
            rong_man = man.availableGeometry().width() if man is not None else 10 ** 6
        m = self.layout().contentsMargins()
        con = rong_man - self.tach.minimumSizeHint().width() - m.left() - m.right() - 12 - 16
        return max(120, min(RONG_DS_HO, con))

    def doi_bang_gon(self, gon: bool) -> None:
        """Bật / tắt Gọn cột cho mọi bảng mục của cửa sổ (bảng chưa dựng đọc _bang_gon khi dựng); nhớ cho lần sau."""
        self._bang_gon = bool(gon)
        for bm in self.bang.values():
            bm.dat_gon(self._bang_gon)
        from .giao_dien import cai_dat_nho
        cd = cai_dat_nho()
        if cd is not None:
            cd.setValue(KHOA_BANG_GON, self._bang_gon)

    def doi_chieu_ho(self, ma_b: int | None = None, cho: bool = True):
        """Hộp đối chiếu phương án đã lưu của hộ đang mở với hộ khác (mặc định hộ kế tiếp) - không chặn cửa sổ này."""
        from .man_hinh_phu_lap_pa import HopSoSanhHo
        ma_b = ma_b if ma_b is not None else (self.bo.ho_ke(1) or self.bo.ho_ke(-1))
        d = HopSoSanhHo(self, self.bo.con, self.bo.danh_sach_ho(), self.bo.ma_ho, ma_b)
        if cho:
            d.show()
        return d

    def nap_ho(self):
        self._dang_nap = True
        try:
            self._nap_dinh_danh()
            i = self.cb_ho.findData(self.bo.ma_ho)
            self.cb_ho.setCurrentIndex(i)
            self._hien_ten_ho()
            if self._w_ds_ho is not None and not self._w_ds_ho.isHidden():
                self._w_ds_ho.nap()
            h = self.bo.pa.ho
            self.o_nk.setValue(h.nhan_khau or 0)
            self.o_di_chuyen.setChecked(h.phai_di_chuyen)
            self.o_dt_nn.setText(so_vn(h.dt_nn_dang_dung) if h.dt_nn_dang_dung else '')
            bm4 = self.bang.get(4)
            if bm4 is not None:
                cb = bm4.cb_tdc
                cb.setCurrentText(h.tai_dinh_cu or lap_pa.TAI_DINH_CU[0])
                cb.lineEdit().setCursorPosition(0)
            if self.ho_so.ma_ho != self.bo.ma_ho:
                self.ho_so.nap(self.bo.ma_ho)
            for m in THE_MUC[1:]:                       # chỉ vẽ thẻ đã dựng; thẻ khác dựng khi chuyển sang (_dam_bao_bang)
                bm = self.bang.get(m)
                if bm is None:
                    continue
                if bm.isVisible():
                    bm.ve()
                else:
                    bm.ve_sau()
            if 1 in self.bang:
                self.bang[1].nap_danh_sach()
        finally:
            self._dang_nap = False
        self.b_truoc.setEnabled(self.bo.ho_ke(-1) is not None)
        self.b_sau.setEnabled(self.bo.ho_ke(1) is not None)
        self._nap_lan()
        self._ap_khoa()
        chu_pb = self.thanh_pb.chu_trang_thai()       # V1 khóa vì đã niêm yết, không phải vì quyết định phê duyệt; đang sửa V2, V3: Lưu ghi vào đâu
        if chu_pb and (getattr(self.bo, 'phien_ban', None) or not self.bo.khoa):
            self.thong_bao(chu_pb)
        else:
            self.thong_bao(f'Lần {self.bo.lan} đã có quyết định phê duyệt - chỉ xem. Bổ sung tài sản / chính sách: "+ Lập PA '
                           'bổ sung"; điều chỉnh lần này: "Mở khóa".' if self.bo.khoa else '')
        if not getattr(self, '_dang_ht', False):
            self._lich_su, self._vi_tri = [], -1             # hộ mới mở / vừa lưu: bắt đầu lịch sử hoàn tác mới
        self.cap_nhat()

    def cap_nhat(self):
        self._ghi_lich_su()
        kq = self.bo.ket_qua
        from .tien import vn_gon
        for the, m in enumerate(THE_MUC[1:], start=1):
            n = len(self.bo.ds(m))
            bm = self.bang.get(m)
            if bm is not None:
                bm.lb_tong.setText(f'CỘNG MỤC {so_muc(m)} ({TEN_TAB[the].split(". ", 1)[-1].upper()}): {vn(kq.muc[m])} đồng')
                bm.lb_dem.setText(f'Tổng số: <b>{n:02d}</b> {"dòng đất" if m == 1 else "hạng mục"}  ·  Ctrl+C: sao chép ô')
                bm.lb_dem.setToolTip('Chọn ô rồi bấm Ctrl+C sao chép giá trị; Ctrl+Shift+C hoặc chuột phải: sao chép cả dòng')
            # tên thẻ kèm số dòng; mục Đất kèm số tiền (1.0.69)
            chu = f'{TEN_TAB[the]} ({n}' + (f' • {vn_gon(kq.muc[m])}' if m == 1 and kq.muc[m] else '') + ')'
            self.tab.setTabText(the, chu.replace('&', '&&'))
            self.thanh_the.dat_chu(the, chu, n)
        self._dat_tong_dinh_danh()
        so_thua = self.ho_so.bang.rowCount()
        self.tab.setTabText(0, f'{TEN_TAB[0]} ({so_thua} thửa)'.replace('&', '&&'))
        self.thanh_the.dat_chu(0, f'{TEN_TAB[0]} ({so_thua} thửa)', so_thua)
        self.lb_tong.dat(*chu_tong_pa(kq))
        self._dat_chan(kq)
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
            cao = self.o_cb.fontMetrics().lineSpacing() * dong + 22
            self.o_cb.setFixedHeight(min(cao, CAO_CANH_BAO_GON) if getattr(self, '_thap', False) else cao)
        self.o_cb.setVisible(bool(cb))
        thay = self.bo.co_thay_doi
        h = self.bo.pa.ho
        # hộ chưa lưu lần nào: Lưu vẫn bấm được - xác nhận đã lập phương án dù không có dòng nào (mọi mục 0 đồng)
        chua_lap = not str(h.trang_thai or '').startswith(DA_LAP_LUU)
        ho_so_thay = self.ho_so.co_thay_doi()
        self.b_luu.setEnabled((thay or ho_so_thay or chua_lap) and not (self.bo.khoa and not ho_so_thay)
                              and not self._ho_khong_nhan())
        self._ve_nut_luu()
        self._sau_cap_nhat_tu_luu(thay or ho_so_thay)
        self.b_bo.setEnabled(thay)
        if hasattr(self, 'lb_lan'):
            self._dat_chu_lan()
        lan = f'  ·  lần {self.bo.lan}' if self.cb_lan.count() > 1 else ''
        self.setWindowTitle(f'{"* " if thay else ""}Hồ sơ, phương án – hộ {h.ma_ho}: {h.ho_ten}{lan}  ·  {h.trang_thai}')
        if getattr(self, '_w_preview', None) is not None and self._w_preview.isVisible() and not self._dang_nap:
            self._hen_xem.start(CHO_XEM_SAU_SUA_MS)     # phương án đổi: bản xem trước lập lại khi ngừng sửa

    def thong_bao(self, tb: str):
        self.lb_tb.setText(tb or '')
        self.lb_tb.setVisible(bool(tb))                 # trống: không chiếm chỗ trên dải điều hướng (20/10/2026)

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
        if getattr(self, '_dang_ht', False) or getattr(self, '_gop_lich_su', False) or not hasattr(self, '_lich_su'):
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
            from .giao_dien import thong_bao_noi
            thong_bao_noi(self, f'{tb} (chưa lưu)')                          # 1.0.07: thông báo nổi
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
        from .giao_dien import thong_bao_noi
        thong_bao_noi(self, f'{"Đã làm lại" if lam_lai else "Đã hoàn tác"}: {viec}')
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
        self._hien_ten_ho()
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
        # 1.0.57: vai trò tài khoản máy chủ (phan_quyen) - kiểm đếm viên không sửa đơn giá / hệ số / tỷ lệ
        vt = getattr(self.bo.con, '_vai_tro', None)
        if vt is not None and cot in COT_GIA_VAI_TRO:
            from . import phan_quyen
            if not phan_quyen.quyen_bang(vt, muc)['gia']:
                if getattr(self, '_gom_loi', None) is not None:     # đang dán nhiều ô: báo gộp một lần
                    self._gom_loi.append(f'vai trò không sửa cột {cot}')
                    self.bang[muc]._ve_dong(r)
                    return
                QMessageBox.information(self, TEN_UD, f'Vai trò "{phan_quyen.ten_vai_tro(vt)}" không sửa đơn giá, hệ số, tỷ lệ: '
                                                      'đơn giá theo bộ đơn giá - chuyên viên lập phương án áp giá.')
                self.bang[muc]._ve_dong(r)
                return
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
            if muc == 1 and cot in ('dien_tich', 'thua'):   # 20/10/2026: vượt DT thu hồi / nguyên thửa - chỉ nhắc
                cb = self.bo.canh_bao_dien_tich(r)
                tb = ' '.join(x for x in (tb, f'Cần xem lại diện tích: {cb}.' if cb else '') if x)
            self.thong_bao(tb)
        except LoiNhap as e:
            if getattr(self, '_gom_loi', None) is not None:
                self._gom_loi.append(str(e))
            else:
                QMessageBox.warning(self, TEN_UD, str(e))
        if muc == 1:                                    # cảnh báo diện tích tính theo cả thửa: vẽ lại mọi dòng cùng thửa
            thua = {self.bo.pa.dat[i].ma_thua for i in ds if 0 <= i < len(self.bo.pa.dat)}
            ds = sorted(set(ds) | {i for i, d in enumerate(self.bo.pa.dat) if d.ma_thua in thua})
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
                QMessageBox.information(self, TEN_UD, 'Hộ này chưa có thửa: thêm thửa ở thẻ "0. Hồ sơ & Thửa".')
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

    def tach_thua_dong(self):
        """Thêm một dòng nữa cho thửa đang chọn (thửa nhiều loại đất, nhiều phần): diện tích = phần còn lại, sửa loại đất ở dòng mới."""
        i = self.them_thua(self.bang[1].cb_thua.currentData() if self.bang[1].cb_thua.count() else None)
        if i is not None and not self.bo.pa.dat[i].dien_tich:
            self.thong_bao('Thửa đã đưa hết diện tích vào mục 1: sửa diện tích dòng cũ và dòng mới cho khớp phần tách.')
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
        """Tính mật độ cây trồng. i None (nút / chuột phải): MỌI loại cây của hộ trên cùng diện tích trồng - cây đơn giá cao tính
        trước, phần vượt mật độ thành dòng riêng (HopMatDoNhieuCay, 30/10/2026). i cho sẵn: một dòng (HopMatDo)."""
        if i is None:
            from .man_hinh_cay import HopMatDoNhieuCay
            dlg = HopMatDoNhieuCay(self)
            if not cho:
                return dlg
            if dlg.exec() == QDialog.DialogCode.Accepted:
                trong, ngoai, so_dong = dlg.ket_qua
                self._sau_khi_them(3, None, f'Mật độ: {trong} cây trong mật độ, {ngoai} cây vượt mật độ' +
                                   (f' ({so_dong} dòng vượt mật độ ngay dưới dòng cây).' if so_dong else '.'))
            return dlg
        from .man_hinh_cay import HopMatDo
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

    # ---------------------------------------------------------------- áp đơn giá đất (ap_gia_dat, man_hinh_ap_gia_nhanh, man_hinh_tinh_gia_dat)
    def co_the_ap_gia_dat(self) -> bool:
        """Hộ / bản đang mở có áp giá được không. V1 khóa vẫn được: áp thì chuyển sang nhánh V2; lần đã phê duyệt thì không."""
        from . import lan_pa
        bo = self.bo
        if getattr(self, '_chi_xem', False) or self._ho_khong_nhan():
            return False
        vt = getattr(bo.con, '_vai_tro', None)
        if vt is not None:                             # vai trò máy chủ LAN không được sửa giá đất
            from . import phan_quyen
            if not phan_quyen.quyen_bang(vt, 1)['gia']:
                return False
        return not bo.khoa or (getattr(bo, 'phien_ban', None) == 'V1' and not (lan_pa.co_bang(bo.con) and lan_pa.dang_khoa(bo.con, bo.ma_ho, bo.lan)))

    def dam_bao_sua_dat(self) -> bool:
        """Trước khi áp giá vào bản đang mở: V1 đang khóa thì tạo nhánh V2 rồi mở nhánh đó, V1 giữ nguyên. False: không ghi được."""
        from .ap_gia_dat import LY_DO_V2
        bo = self.bo
        if not self.co_the_ap_gia_dat():
            self.thong_bao('Bản đang mở chỉ xem, không áp giá được.')
            return False
        if bo.khoa:
            ma = self.thanh_pb.tao_v2(LY_DO_V2)
            if not ma or self.bo.khoa:
                return False
            self.thong_bao(f'V1 đã niêm yết giữ nguyên: đang áp giá vào nhánh {ma}.')
        return True

    def sau_ap_gia_dat(self, tb: str = '', chon=None) -> None:
        """Vẽ lại sau khi áp giá vào bộ soạn: bảng Đất, khoản hỗ trợ đã tính lại, tổng; hẹn lưu như mọi lần sửa ô. Thửa mới thêm từ bảng tính: thẻ hồ sơ đọc lại."""
        bo = self.bo
        if bo.bc is not None and len(bo.bc.thua_cua(bo.ma_ho)) != self.bang[1].cb_thua.count() and not self.ho_so.co_thay_doi():
            self.ho_so.nap(bo.ma_ho)
        self.bang[1].ve(chon=chon)
        self.bang[1].nap_danh_sach()
        bm4 = self.bang.get(4)
        if bm4 is not None:
            bm4.ve()
        self.cap_nhat()
        if tb:
            self.thong_bao(tb)
        self._kich_hoat_hen_luu_tu_dong()

    def mo_bang_tinh_dat(self, cho: bool = True):
        """Bảng tính đầy đủ: chọn sẵn hộ này, tích sẵn dòng đang chọn (không chọn dòng nào thì mọi dòng). Áp xong bảng Đất cập nhật ngay. cho=False: trả hộp (kiểm thử)."""
        from .man_hinh_tinh_gia_dat import HopTinhGiaDat
        bo = self.bo
        bm = self.bang[1]
        chon = [i for i in bm.cac_dong_chon() if 0 <= i < len(bo.pa.dat)]
        d = HopTinhGiaDat(self, bo.con, [bo.ma_ho], bo.bc.ten_dia_ban or '', not self.co_the_ap_gia_dat(), bo_mo=bo, dong_tich=chon or None,
                          truoc_ap=self.dam_bao_sua_dat, sau_ap=self.sau_ap_gia_dat, thong_so=bm.thanh_gia.thong_so())
        d.im_lang = getattr(self, 'im_lang', False)
        if not cho:
            return d
        d.exec()
        d.deleteLater()
        return d

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

    def xem_giai_trinh_dong(self, muc: int | None = None, i: int | None = None, cho: bool = True) -> dict | None:
        """1.0.55: hộp "Giải trình cách tính" của một dòng phương án (công thức, thay số, căn cứ - nghiep_vu.giai_trinh_dong_pa) để
        trả lời thanh tra / giải thích cho người dân; có nút Chép. muc / i None: thẻ mục và dòng đang chọn. cho=False: không hiện
        hộp (kiểm thử). Trả dict giải trình hoặc None (không có dòng)."""
        from .nghiep_vu import giai_trinh_dong_pa, so_muc
        if muc is None:
            t = self.tab.currentIndex()
            if not 0 < t < len(THE_MUC):
                self.thong_bao('Chọn một dòng ở thẻ mục (1. Đất … 5. Hỗ trợ) rồi bấm Ctrl+I để xem cách tính.')
                return None
            muc = THE_MUC[t]
        ds = self.bo.ds(muc)
        if i is None:
            i = self.bang[muc].dong_chon()
        if not 0 <= i < len(ds):
            self.thong_bao('Chọn một dòng trong bảng để xem cách tính.')
            return None
        gt = giai_trinh_dong_pa(self.bo.pa, self.bo.bc, muc, i)
        from .giao_dien import hop_ket_qua
        from .tien import vn
        hop_ket_qua(self, f'Mục {so_muc(muc)}, dòng {i + 1}: {gt["ten_hang_muc"]} - thành tiền {vn(gt["thanh_tien"])} đồng.', gt['dong'],
                    'Công thức, thay số và căn cứ', hien=cho, tieu_de='Giải trình cách tính')
        return gt

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
            QMessageBox.information(self, TEN_UD, 'Hộ này chưa có thửa: thêm thửa ở thẻ "0. Hồ sơ & Thửa".')
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

    def tu_tinh_ho_tro(self):
        """Nút Tự tính hỗ trợ (mục Hỗ trợ): thêm các khoản hộ đủ điều kiện (nghiep_vu.goi_y_ho_tro), chưa ghi cho tới khi Lưu."""
        chon = self.goi_y(tu_dong=True)
        if not chon:
            self.thong_bao('Không có khoản hỗ trợ mới nào đủ điều kiện: xem lại Nhân khẩu, Phải di chuyển chỗ ở, DT đất nông nghiệp, Loại đất.')
        return chon

    def _to_mau_thanh_tren(self) -> None:
        """Phân cấp màu nút thanh trên (V3.3): Tạo nhánh, Đối chiếu xanh nhạt; In xám; Đóng đỏ nhạt. Nút Lưu theo trạng thái: _ve_nut_luu."""
        from .giao_dien import QSS_NUT_DONG_THANH, QSS_NUT_IN_THANH, QSS_NUT_PHIEN_BAN
        for b in (self.thanh_pb.b_hd, self.thanh_pb.b_dc):
            dat_kieu_theo_tong(b, QSS_NUT_PHIEN_BAN)
        dat_kieu_theo_tong(self.b_in, QSS_NUT_IN_THANH)
        dat_kieu_theo_tong(self.b_dong, QSS_NUT_DONG_THANH)

    def _ve_nut_luu(self) -> None:
        """Có gì để lưu: xanh lá đậm; không: xám "✓ Đã lưu"."""
        from .giao_dien import QSS_NUT_DA_LUU, QSS_NUT_LUU_DOI
        doi = self.b_luu.isEnabled()
        self.b_luu.setText(('Lưu' if self.width() < self.RONG_THANH_TREN_GON else 'Lưu (Ctrl+S)') if doi else '✓ Đã lưu')
        if getattr(self, '_kieu_luu', None) != doi:
            self._kieu_luu = doi
            dat_kieu_theo_tong(self.b_luu, QSS_NUT_LUU_DOI if doi else QSS_NUT_DA_LUU)

    # ---------------------------------------------- màn hình thấp (1.0.51)
    RONG_THANH_TREN_GON = 1280

    def resizeEvent(self, e):
        super().resizeEvent(e)
        hep = self.width() < self.RONG_THANH_TREN_GON
        if hep != getattr(self, '_thanh_tren_hep', False) and hasattr(self, 'thanh_pb'):
            self._thanh_tren_hep = hep                  # hàng trên ở 1366 @125%: 2 ô chọn nhường chỗ, nút Chốt V1 / Mở khóa không bị cắt; chữ đủ ở danh sách xổ và chú thích
            self.cb_lan.setMinimumContentsLength(8 if hep else 24)
            self.thanh_pb.cb.setMinimumContentsLength(8 if hep else 22)
            self.nhan_lan.setVisible(not hep)
            self.cb_ho.setMinimumWidth(150 if hep else RONG_O_HO[0])
            self._ve_nut_luu()
            for b in (self.thanh_pb.b_hd, self.thanh_pb.b_khoa, self.b_mo_khoa, self.b_khoa_lan, self.thanh_pb.b_dc):
                b.setMinimumWidth(b.fontMetrics().horizontalAdvance(b.text()) + 18 if hep else 0)

    def _man_hinh_thap(self) -> bool:
        man = self.screen() or QApplication.primaryScreen()
        return man is not None and man.availableGeometry().height() <= MAN_HINH_THAP

    def _gon_man_hinh_thap(self) -> None:
        self.dai_dinh_danh.setFixedHeight(CAO_DAI_DINH_DANH_GON)
        for f in (self.dai_dinh_danh, self.thanh_tren, self.dai_lan, self.dai_dieu_huong):
            lo = f.layout()
            if lo is not None:
                m = lo.contentsMargins()
                lo.setContentsMargins(m.left(), 1, m.right(), 1)

    # ---------------------------------------------- lưu tự động (1.0.51)
    def _noi_tu_luu_ho_so(self) -> None:
        """Sửa ô bảng thửa / gõ ô chữ của thẻ hồ sơ cũng hẹn lưu tự động (thay đổi phương án hẹn qua cap_nhat)."""
        import time
        self.ho_so.bang.itemChanged.connect(lambda *_: self._kich_hoat_hen_luu_tu_dong())
        for w in self.ho_so.o.values():
            tin_hieu = getattr(w, 'textEdited', None)
            if tin_hieu is not None:
                tin_hieu.connect(lambda *_: (setattr(self, '_luc_go', time.monotonic()), self._kich_hoat_hen_luu_tu_dong(chac=True)))

    def _doi_chu_ky_tu_luu(self) -> None:
        from . import chu_de
        giay = chu_de.dat_chu_ky_luu_tu_dong(int(self.cb_tu_luu.currentData() or 0))
        if giay <= 0:
            self._hen_luu_tu_dong.stop()
            self.thong_bao('Đã tắt lưu tự động (bấm Lưu hoặc Ctrl+S để lưu).')
        else:
            self.thong_bao(f'Đã bật lưu tự động sau {chu_de.nhan_chu_ky(giay)} ngừng thao tác.')
            self._luc_doi_dau = None
            self._kich_hoat_hen_luu_tu_dong()

    def _co_the_tu_luu(self) -> bool:
        return not (self._dang_nap or self.bo.khoa or self._ho_khong_nhan() or getattr(self, '_chi_xem', False))

    def _kich_hoat_hen_luu_tu_dong(self, chac: bool = False) -> None:
        """Có thay đổi chưa lưu: hiện "● Chưa lưu" và hẹn lưu sau chu kỳ ngừng thao tác (gõ tiếp thì hẹn lại, nhưng không quá
        3 chu kỳ kể từ thay đổi đầu tiên - làm liên tục vẫn được lưu)."""
        if getattr(self, '_dang_nap', True) or not hasattr(self, 'lb_trang_thai_luu'):
            return
        if not chac and not (self.bo.co_thay_doi or self.ho_so.co_thay_doi()):
            return
        self._dat_trang_thai_luu('chua')
        if not self._co_the_tu_luu():
            return
        from . import chu_de
        giay = chu_de.chu_ky_luu_tu_dong()
        if giay <= 0:
            return
        import time
        bay_gio = time.monotonic()
        if self._luc_doi_dau is None:
            self._luc_doi_dau = bay_gio
        con_lai = self._luc_doi_dau + 3 * giay - bay_gio
        self._hen_luu_tu_dong.start(int(1000 * max(1.0, min(giay, con_lai))))

    def _sau_cap_nhat_tu_luu(self, co_thay_doi: bool) -> None:
        if co_thay_doi:
            self._kich_hoat_hen_luu_tu_dong(chac=True)
        elif hasattr(self, 'lb_trang_thai_luu') and self.lb_trang_thai_luu.property('tt') == 'chua':
            self._hen_luu_tu_dong.stop()
            self._luc_doi_dau = None
            self._dat_trang_thai_luu('')

    def _dat_trang_thai_luu(self, tt: str, luc: str = '', tu_dong: bool = True) -> None:
        from .giao_dien import TOKEN, mau_theo_tong
        lb = self.lb_trang_thai_luu
        if lb.property('tt') == tt and not luc:
            return
        lb.setProperty('tt', tt)
        if tt == 'chua':
            lb.setText('● Chưa lưu')
            lb.setToolTip('Có thay đổi chưa ghi vào file dự án')
            mau = TOKEN['canh_bao']
        elif tt == 'xong':
            lb.setText(f'✓ Đã {"tự lưu" if tu_dong else "lưu"} {luc}')
            lb.setToolTip('Đã ghi vào file dự án' + (' (lưu tự động)' if tu_dong else ''))
            mau = '#0F6E56'
        else:
            lb.setText('')
            lb.setToolTip('')
            mau = TOKEN['chu_phu']
        lb.setStyleSheet('QLabel#trang_thai_luu { color: %s; font-weight: 600; padding: 0 4px; }' % mau_theo_tong(mau, 'chu'))

    def _dang_sua_o_bang(self) -> bool:
        """Đang gõ dở (ô bảng đang sửa, danh sách gợi ý / menu đang mở, hộp thoại khác đang chờ, vừa gõ ô chữ thẻ hồ sơ): chưa tự lưu."""
        import time
        hop = QApplication.activeModalWidget()
        if hop is not None and hop is not self and hop is not self.window():
            return True
        if QApplication.activePopupWidget() is not None:
            return True
        ds = [self.ho_so.bang] + [bm.bang for bm in self.bang.values() if bm is not None]
        for b in ds:
            if b.state() == QAbstractItemView.State.EditingState:
                return True
        return time.monotonic() - self._luc_go < 2.5

    def _thuc_hien_luu_tu_dong(self) -> None:
        if not self.isVisible() or not (self.bo.co_thay_doi or self.ho_so.co_thay_doi()) or not self._co_the_tu_luu():
            return
        if self._dang_sua_o_bang():
            self._hen_luu_tu_dong.start(2000)          # đang gõ dở: lùi 2 giây
            return
        self.luu(tu_dong=True)

    def _luu_im_lang(self) -> bool:
        """Lưu tự động: không hộp thoại, không chuyển thẻ, không dựng lại bảng phương án (giữ ô đang chọn, vị trí cuộn); lỗi nhập
        -> chỉ báo ở dòng thông báo, chờ lần sửa sau."""
        if self.ho_so.co_thay_doi():
            bang = self.ho_so.bang
            o = (bang.currentRow(), bang.currentColumn())
            cuon = bang.verticalScrollBar().value()
            tieu_diem = QApplication.focusWidget()
            if not self.ho_so.luu(im_lang=True):
                self.thong_bao(f'Tự lưu tạm hoãn: {getattr(self.ho_so, "loi_luu", "") or "hồ sơ hộ chưa hợp lệ"}')
                return False
            if 0 <= o[0] < bang.rowCount():
                bang.setCurrentCell(o[0], max(0, o[1]))
            bang.verticalScrollBar().setValue(cuon)
            if tieu_diem is not None and tieu_diem.isVisible():
                tieu_diem.setFocus()
        if self.bo.co_thay_doi:
            try:
                tb = self.bo.luu_tai_cho()
            except LoiNhap as e:
                self.thong_bao(f'Tự lưu tạm hoãn: {" ".join(str(e).split())}')
                return False
            except sqlite3.Error as e:                  # 1.0.58: không bật hộp lỗi giữa lúc đang gõ
                from .thong_bao import giai_thich
                self.thong_bao(f'Tự lưu tạm hoãn: {giai_thich(e)[0]}')
                return False
            self.thong_bao(tb)
        self.da_luu = True
        self._luc_doi_dau = None
        self._hen_luu_tu_dong.stop()
        self.cap_nhat()
        self._dat_trang_thai_luu('xong', datetime.now().strftime('%H:%M:%S'))
        cha = self.parent()
        if self.property('nhung_tab') and cha is not None and hasattr(cha, 'tai_lai'):
            cha.tai_lai()                               # DauVetHo: chỉ dựng lại dòng của hộ vừa lưu
        return True

    # ---------------------------------------------- lưu / chuyển hộ / đóng
    def luu(self, tu_dong: bool = False) -> bool:
        """tu_dong=True: lưu tự động (_luu_im_lang). Không thì lưu khi người dùng bấm Lưu / Ctrl+S (báo lỗi bằng hộp thoại)."""
        if tu_dong:
            return self._luu_im_lang()
        self._chot_dang_go()
        self._hen_luu_tu_dong.stop()
        self._luc_doi_dau = None
        if self.ho_so.co_thay_doi() and not self.ho_so.luu():
            self.tab.setCurrentIndex(0)
            return False
        try:
            tb = self.bo.luu()
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return False
        except sqlite3.Error as e:                      # 1.0.58: file bị khóa / ổ mạng mất kết nối: báo rõ, số vừa soạn còn trên màn hình
            self._luc_doi_dau = None
            self._hen_luu_tu_dong.start()
            QMessageBox.warning(self, TEN_UD, chu_loi('Chưa lưu được phương án của hộ này (số liệu vừa soạn vẫn còn trên màn hình)', e))
            return False
        self.da_luu = True
        self.nap_ho()
        self.thong_bao(tb)
        self._dat_trang_thai_luu('xong', datetime.now().strftime('%H:%M:%S'), tu_dong=False)
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
        self.bo.mo(self.bo.ma_ho, self.bo.lan)
        self.ho_so.nap(self.bo.ma_ho)
        self.nap_ho()
        self.lam_moi_xem_truoc()

    # ---------------------------------------------- xem trước A4 (khung bên phải, F4)
    @property
    def w_preview(self):
        """Khung xem trước A4 - tạo lần đầu được hỏi tới (bật F4 / nút Xem trước), ẩn sẵn."""
        if self._w_preview is None:
            from .xem_truoc_tai_lieu import KhungXemTruocTaiLieu, in_qua_excel
            w = KhungXemTruocTaiLieu(self, ham_in=lambda pdf, xlsx: in_qua_excel(self, pdf, xlsx))
            w.setMinimumWidth(520)
            w.setVisible(False)
            self.tach.addWidget(w)
            self.tach.setStretchFactor(1, 2)
            self._w_preview = w
        return self._w_preview

    def _dang_xem_truoc(self) -> bool:
        return self._w_preview is not None and self._w_preview.isVisible()

    def bat_tat_xem_truoc(self, hien: bool | None = None) -> bool:
        """Hiện / ẩn khung xem trước; hiện thì lập ngay bản in của hộ đang mở. Trả trạng thái mới."""
        hien = not self._dang_xem_truoc() if hien is None else bool(hien)
        if not hien and self._w_preview is None:
            self.btn_toggle_preview.setChecked(False)
            return False
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
        if self._w_ds_ho is not None and not self._w_ds_ho.isHidden():      # 1.0.58: danh sách hộ ghim cũng chiếm chỗ
            con -= self._w_ds_ho.width() + 6
        self.w_preview.setMinimumWidth(max(RONG_XEM_TOI_THIEU, min(520, con)))

    def lam_moi_xem_truoc(self, ngay: bool = False) -> None:
        """Bản in A4 (bản Word thể thức NĐ 30 - in_word, mẫu chuẩn duy nhất của phương án chi tiết từ 22/10/2026) của hộ đang mở
        theo phương án ĐANG SOẠN trong bộ nhớ (chưa lưu cũng hiện); thông tin hộ, nguồn gốc theo hồ sơ đã lưu. Máy không dùng được
        Word: bản gần đúng dựng bằng Qt từ chính file Word (docx_sang_pdf)."""
        if not self._dang_xem_truoc():
            return
        self._hen_xem.stop()
        from . import in_word
        bo, ma = self.bo, self.bo.ma_ho

        def tao(thu_muc):                                       # 1.0.05: bản in của LẦN đang soạn
            return in_word.xuat_chi_tiet_docx(bo.con, ma, Path(thu_muc) / f'{du_lieu_in.ten_file_ho(bo.con, ma)}.docx', bc=bo.bc,
                                              pa=bo.pa, lan=bo.lan)

        ten = f'{bo.pa.ho.ho_ten}' + (' (chưa lưu)' if bo.co_thay_doi else '')
        self.w_preview.yeu_cau(None, tao, ten, ngay)

    def _chot_dang_go(self) -> None:
        """1.0.58: ô bảng / ô chữ đang gõ dở: mất tiêu điểm để Qt ghi giá trị trước khi lưu / rời hộ (phím tắt không đổi tiêu điểm -
        trước đây Ctrl+S báo "Đã lưu" mà bỏ số vừa gõ, Ctrl+PgDown sang hộ khác không hỏi)."""
        f = QApplication.focusWidget()
        if f is not None and self.isAncestorOf(f):
            f.clearFocus()
            QApplication.processEvents()

    def hoi_luu(self) -> bool:
        """True nếu được phép rời hộ đang soạn."""
        self._chot_dang_go()
        if not self.bo.co_thay_doi and not self.ho_so.co_thay_doi():
            return True
        tl = _hoi(self, TEN_UD, f'Hộ {self.bo.ma_ho} – {self.bo.pa.ho.ho_ten} có thay đổi chưa lưu. Lưu lại?')
        if tl == 'luu':
            return self.luu()
        if tl == 'bo':
            self.bo.mo(self.bo.ma_ho, self.bo.lan)
            self.ho_so.nap(self.bo.ma_ho)
            return True
        return False

    def chuyen_ho(self, ma_ho: int) -> bool:
        if ma_ho == self.bo.ma_ho:
            return True
        if not self.hoi_luu():
            self.cb_ho.setCurrentIndex(self.cb_ho.findData(self.bo.ma_ho))
            self._hien_ten_ho()
            return False
        self.bo.mo(ma_ho)
        self.ho_so.nap(ma_ho)
        for bm in self.bang.values():                   # 1.0.58: ô nhập nhanh gõ dở không đi theo sang hộ khác (Enter ghi nhầm hộ)
            if getattr(bm, 'hang', None) is not None:
                bm.hang.xoa(giu_tieu_diem=True)
        self.nap_ho()
        self.lam_moi_xem_truoc()
        # 1.0.78 (người dùng): sang hộ khác luôn bắt đầu ở thẻ Hồ sơ & Thửa để nhập theo thứ tự. Tiêu điểm vào khung, không vào ô chữ:
        # đứng trong ô chữ thì Ctrl + mũi tên nhảy từng từ, không sang hộ được nữa
        self.tab.setCurrentIndex(0)
        self.ho_so.setFocus()
        return True

    def dat_tieu_diem_dau(self) -> None:
        """1.0.58: mở hộ: tiêu điểm vào ô nhập đầu của thẻ đang xem (trước đây còn ở nút thu gọn menu: Space thu menu, 21 lần Tab mới tới ô tên)."""
        t = self.tab.currentIndex()
        if t <= 0 or t >= len(THE_MUC):
            return
        bm = self.bang[THE_MUC[t]]
        o = bm.hang.o_chon.o if getattr(bm, 'hang', None) is not None else getattr(bm, 'cb_thua', None)
        if o is not None:
            o.setFocus()

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
            if self._w_preview is not None:
                self._w_preview.don_dep()
            e.accept()
            super().closeEvent(e)
            from .csdl import giai_phong_bo_nho
            QTimer.singleShot(0, giai_phong_bo_nho)
        else:
            e.ignore()

    def done(self, r):
        if self._w_preview is not None:
            self._w_preview.don_dep()                   # xóa file xem trước tạm
        super().done(r)
        from .csdl import giai_phong_bo_nho
        QTimer.singleShot(0, giai_phong_bo_nho)         # 1.0.08: máy yếu - trả RAM của phương án / bảng vừa đóng


# ---------------------------------------------------------------- thông tin dự án
KICH_THUOC_HOP_DU_AN = (1180, 640)               # 1.0.04: thêm khung Tóm tắt quy mô & hồ sơ pháp lý


NHAN_GON_DU_AN = {'don_vi_cap_tren': 'Đơn vị cấp trên', 'don_vi_tieu_de': 'Tiêu đề in (dòng 2)', 'don_vi_lap': 'Đơn vị lập PA', 'dia_danh_don_vi': 'Địa danh ngày ký'}


class HopDuAn(QDialog):
    def __init__(self, con, parent=None):
        super().__init__(parent)
        self.con = con
        self.setWindowTitle('Thông tin dự án')
        self.resize(*KICH_THUOC_HOP_DU_AN)              # 1.0.03: tên đơn vị / cơ quan thẩm định dài không bị cắt
        gt = lap_pa.doc_du_an(con)
        self.o = {}
        from . import csdl
        from .giao_dien import the_form
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
                # 1.0.04: không giãn theo gợi ý dài nhất (bỏ can_giua thì ô này ép hộp rộng gấp đôi màn hình)
                w.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
                w.setMinimumContentsLength(18)
                w.setToolTip('Cơ quan thẩm định phương án (tờ trình: Kính gửi, đề nghị thẩm định). Để trống: tự lấy theo cấp '
                             'địa bàn - phường: Phòng Kinh tế, Hạ tầng và Đô thị; xã: Phòng Kinh tế')
                w.setEditText(gt[k])
            else:
                w = QLineEdit(gt[k])
                w.setCursorPosition(0)
                if k == 'dia_danh_don_vi':                  # 1.0.29: nơi đơn vị công tác (dòng ngày tháng), không phải xã có đất
                    w.setPlaceholderText('Nơi đơn vị đặt trụ sở, in đầu dòng ngày tháng (vd: Trị An) - không phải xã có đất')
                    w.setToolTip('Địa danh in ở dòng "<địa danh>, ngày … tháng … năm …" của phương án chi tiết, bảng tổng hợp, tờ trình: nơi đơn vị công tác. '
                                 'Để trống: theo hồ sơ địa phương (Cấu hình nghiệp vụ), chưa có thì để chỗ trống.')
            self.o[k] = w
            if k in csdl.TRUONG_DON_VI and isinstance(w, QLineEdit):      # 1.0.69: đủ chữ "TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT"
                w.setMinimumWidth(260)
                w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            (don_vi if k in csdl.TRUONG_DON_VI else du_an).append((NHAN_GON_DU_AN.get(k, ten) + ':', w))
        # 1.0.69: cấp địa bàn, tên xã / phường, năm chung một hàng
        hang_db = QWidget()
        hd = QHBoxLayout(hang_db)
        hd.setContentsMargins(0, 0, 0, 0)
        hd.setSpacing(6)
        for i, (w, nhan) in enumerate(((self.o['cap_dia_ban'], ''), (self.o['ten_dia_ban'], 'Tên xã, phường:'), (self.o['nam'], 'Năm:'))):
            if nhan:
                lb = QLabel(nhan)
                lb.setProperty('vai', 'nhan')
                hd.addWidget(lb)
            hd.addWidget(w, 1 if w is self.o['ten_dia_ban'] else 0)
        self.o['nam'].setMaximumWidth(70)
        self.o['cap_dia_ban'].setMinimumContentsLength(6)
        self.o['cap_dia_ban'].setMaximumWidth(110)
        self.o['ten_dia_ban'].setMinimumWidth(130)
        self.o['ten_dia_ban'].editingFinished.connect(lambda: self.o['ten_dia_ban'].setText(lap_pa.chuan_ten_dia_ban(self.o['ten_dia_ban'].text())))
        cac_o_gop = (self.o['cap_dia_ban'], self.o['ten_dia_ban'], self.o['nam'])
        for ds_dong in (du_an, don_vi):
            cu = [x for x in ds_dong if x[1] in cac_o_gop]
            if cu:
                vt = ds_dong.index(cu[0])
                ds_dong[:] = [x for x in ds_dong if x[1] not in cac_o_gop]
                ds_dong.insert(vt, ('Cấp địa bàn:', hang_db))
        # kinh phí tổ chức thực hiện bồi thường (QĐ 08/2025/QĐ-UBND): theo tuyến 3,5%, cụm / vùng / khác 2,5%. 0.9.72 (người dùng
        # 13/10/2026): chọn sẵn theo tên dự án (đường, tuyến, kênh, đường dây, đường ống… -> theo tuyến) và đổi theo khi sửa tên,
        # tới khi người dùng tự chọn loại
        loai, tl, tu_nhan = lap_pa.kinh_phi_to_chuc(con)
        self.o_loai_kp = QComboBox()
        self.o_loai_kp.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.o_loai_kp.setMinimumContentsLength(30)
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
        self._dau_dong_va_goi_y()
        # 0.9.69 (người dùng 12/10/2026): chỉ chọn loại dự án - tỷ lệ tự lấy mức tối đa của loại (bỏ ô Tỷ lệ cho đỡ rối)
        kp = the_form('Kinh phí tổ chức thực hiện bồi thường (bảng tổng hợp, dự toán)',
                      [('Loại dự án:', self.o_loai_kp)], 110)
        kp.setToolTip(f'{lap_pa.CAN_CU_KINH_PHI}: dự án, tiểu dự án hạ tầng theo tuyến không quá 3,5%; dự án còn lại '
                      '(cụm, vùng, khu…) không quá 2,5% tổng kinh phí bồi thường, hỗ trợ, tái định cư.')
        # 1.0.04 (người dùng 19/10/2026): bỏ can_giua (bó hẹp giữa màn hình, che chữ cuối tên dài) - lưới 2 cột giãn sát hai mép
        luoi = QGridLayout()
        luoi.setHorizontalSpacing(12)
        self.the_du_an, self.the_don_vi = the_form('Thông tin dự án', du_an, 110), the_form('Đơn vị lập, người ký', don_vi, 120)
        for i, t in enumerate((self.the_du_an, self.the_don_vi)):
            t.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            luoi.addWidget(t, 0, i, Qt.AlignmentFlag.AlignTop)
            luoi.setColumnStretch(i, 1)
        kp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        luoi.addWidget(kp, 1, 0, 1, 2)                   # kinh phí + khung pháp lý giãn hết bề ngang (hai cột)
        self.the_phap_ly = self._the_phap_ly()
        luoi.addWidget(self.the_phap_ly, 2, 0, 1, 2)
        form = QVBoxLayout()
        form.addLayout(luoi)
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

    def _the_phap_ly(self) -> QWidget:
        """Khung thứ 4 (1.0.04): tóm tắt quy mô (số hộ, số thửa, tổng DT thu hồi) + căn cứ thu hồi đất, trạng thái hồ sơ pháp lý đầu
        vào (tiep_nhan_phap_ly lưu trong dự án) và nút mở hộp Tiếp nhận & Kiểm tra pháp lý."""
        g = QGroupBox('Tóm tắt quy mô && trạng thái hồ sơ pháp lý đầu vào')     # '&&': '&' trơn thành phím tắt (lộ dấu _)
        g.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        f = QFormLayout(g)
        self.lb_pl = {}
        for k, ten in (('quy_mo', 'Quy mô:'), ('can_cu', 'Căn cứ thu hồi đất:'), ('trang_thai', 'Hồ sơ pháp lý:')):
            lb = QLabel('')
            lb.setWordWrap(True)
            lb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.lb_pl[k] = lb
            f.addRow(ten, lb)
        self.b_phap_ly = QPushButton('Kiểm tra && Tiếp nhận hồ sơ pháp lý đầu vào…')
        self.b_phap_ly.clicked.connect(lambda: self.mo_tiep_nhan())
        f.addRow('', self.b_phap_ly)
        self.cap_nhat_phap_ly()
        return g

    def cap_nhat_phap_ly(self) -> None:
        from . import tiep_nhan_phap_ly as tn
        tt = tn.tom_tat_du_an(self.con)
        self.lb_pl['quy_mo'].setText(f'{tt["so_ho"]} hộ · {tt["so_thua"]} thửa · tổng DT thu hồi {so_vn(tt["dt_thu_hoi"])} m²')
        d = tn.doc_du_an(self.con)
        self.lb_pl['can_cu'].setText('; '.join(tn.TEN_CAN_CU[x].split(' - ')[0] for x in d['can_cu']) if d and d['can_cu']
                                     else '(chưa chọn - mở hộp Tiếp nhận để chọn)')
        self.lb_pl['trang_thai'].setText(tn.trang_thai(d)['nhan'])

    def mo_tiep_nhan(self, cho: bool = True):
        from .man_hinh_tiep_nhan import HopTiepNhanPhapLy
        dlg = HopTiepNhanPhapLy(self.con, None, self, im_lang=getattr(self, 'im_lang', False))
        if not cho:
            return dlg
        dlg.exec()
        self.cap_nhat_phap_ly()
        return dlg

    def _dau_dong_va_goi_y(self):
        """1.0.03 (Ảnh 4): chữ dài (tên cơ quan, "Phòng Kinh tế, Hạ tầng và Đô thị phường…") hiện TỪ ĐẦU (ô sửa
        được mặc định cuộn về cuối - mất chữ đầu) và đủ chữ ở chú thích; chú thích đi theo khi sửa."""
        for w in self.o.values():
            o = w.lineEdit() if isinstance(w, QComboBox) else w
            if o is None:
                continue
            o.setCursorPosition(0)
            if not w.toolTip():
                o.setToolTip(o.text())
                o.textChanged.connect(lambda t, o=o: o.setToolTip(t))

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
        except sqlite3.OperationalError as e:                # dự án mở chỉ xem / file chỉ đọc: báo rõ, không văng lỗi
            from .thong_bao import chu_loi
            QMessageBox.warning(self, TEN_UD, chu_loi('Lưu thông tin dự án', e))
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
                    it.setBackground(QBrush(qmau_theo_tong(CAM.name())))
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
# mô tả hai chế độ phát hành (chú thích nút chọn - 16/10/2026 bỏ dòng ghi chú dưới nút cho gọn cửa sổ)
MO_TA_CHE_DO = {
    'du_thao': 'In bằng mẫu chính, CÓ chữ "(DỰ THẢO)" (mẫu chưa có thì phần mềm tự thêm dưới dòng "Số:" và vào tiêu đề bảng '
               'tổng hợp), chưa ghi số phương án, in đủ số CCCD; dùng khi niêm yết và họp dân lấy ý kiến.',
    'chinh_thuc': 'In bằng mẫu chính, KHÔNG có chữ "DỰ THẢO" (phần mềm tự xóa nếu mẫu có), số phương án chính thức theo đợt; '
                  'tờ trình, bảng tổng hợp, phương án chi tiết từng hộ.',
}


# 20/10/2026 (ảnh mẫu người dùng): hai thẻ chế độ phát hành + khung quy tắc tự động + danh sách tài liệu có thẻ nhỏ
TOI_DA_IN_PDF = 100             # in qua bản PDF tối đa chừng này hộ một lệnh; nhiều hơn: Word gửi từng hộ (ảnh 300 dpi của lô lớn rất nặng)
CHO_LAP_BAN_IN_GIAY = 900
THE_CHE_DO = (('du_thao', 'Bản dự thảo', 'Niêm yết, họp dân; có chữ DỰ THẢO'), ('chinh_thuc', 'Bản chính thức', 'Trình thẩm định, gửi từng hộ'))


class _MucSap(QTableWidgetItem):
    """Ô bảng hộ sắp xếp theo giá trị (UserRole + 1: số thứ tự / số tiền) thay vì theo chữ."""

    def __lt__(self, other):
        a, b = self.data(Qt.ItemDataRole.UserRole + 1), other.data(Qt.ItemDataRole.UserRole + 1)
        if a is not None and b is not None:
            return a < b
        return self.text().lower() < other.text().lower()


XEM_NHIEU_TOI_DA = 30           # xem trước gộp nhiều hộ: tối đa chừng này hộ một lần (mỗi hộ Word xuất PDF ~1-2 s)


class HopIn(QDialog):
    """In / xuất hồ sơ theo cấu trúc bảng In của Word (người dùng 05/11/2026, 1.0.66): cột trái In | Xuất | Xuất dữ liệu; cột tùy chọn: nút In + số bản, Máy in, Thiết đặt (hộ, tài liệu, bản, trang,
    hai mặt, xếp bộ, khổ giấy); phải: bản xem trước, thanh trang và thu phóng ở đáy. Tài liệu đang xem là tài liệu sẽ in. Mở mặc định Dự thảo. Xuất file lưu vào thư mục chứa file dự án, không hỏi. Lõi xuất: van_ban_trinh.xuat_bo_ho_so, một chỗ."""

    def __init__(self, con, parent=None, ma_ho_chon: list | None = None, file_du_an=None, che_do: str | None = None,
                 dot_id: int | None = None):
        from . import in_an
        super().__init__(parent)
        self.con = con
        self.file_du_an = file_du_an
        self.ket_qua = None
        self.setWindowTitle('In / Xuất hồ sơ')
        self.resize(1360, 820)                      # phần lớn bề rộng cho khung xem trước A4 (vua_man_hinh thu lại theo màn hình)
        self._doc_ds_ho(con, in_an, ma_ho_chon)
        self._tao_trang_thai_xuat(con)
        self._dung_chon_ho(in_an)
        from . import xem_truoc_tai_lieu as xt
        lenh = getattr(parent, 'lenh', None) or {}
        self._co_du_lieu = 'Xuất danh sách hộ…' in lenh
        self._rail = 'in'
        self._mot = len(self.ma_ho_chon) == 1 and che_do is None and dot_id is None
        self._in_pdf = xt.co_hop_in()                     # chọn máy in, hai mặt, trang: vẽ PDF lên máy in (bản Qt 6); bản Win 7: Word / Excel gửi máy in mặc định
        cot_rail = self._dung_rail()
        self._dung_nut_lon()
        self._dung_may_in()
        self._dung_thiet_dat(con, parent)
        self._dung_in_them(lenh)
        self._dung_xuat_them(file_du_an)
        self._dung_du_lieu(lenh)
        cuon = self._dung_cot_trai()

        # ---- xem trước A4: thanh trang, thu phóng ở đáy như Word
        self.w_preview = xt.KhungXemTruocTaiLieu(self, ham_in=lambda pdf, xlsx: xt.in_qua_excel(self, pdf, xlsx), kieu_office=True)
        self.w_preview.setMinimumWidth(420)
        self.phai = self.w_preview
        lo = QHBoxLayout(self)
        lo.setContentsMargins(6, 6, 6, 6)
        lo.setSpacing(8)
        lo.addWidget(cot_rail)
        lo.addWidget(cuon)
        lo.addWidget(self.khung_chon_ho)
        lo.addWidget(self.phai, 1)
        self._ma_xem = None
        self._phim_in = QShortcut(QKeySequence('Ctrl+P'), self)
        self._phim_in.activated.connect(lambda: self.in_ra_may())
        self.hang_pham_vi.dat('mot' if self._mot else ('chon' if self.ma_ho_chon else 'pa'), im=True)
        self._theo_pham_vi()
        for b in (self.r_du_thao, self.r_chinh_thuc):
            b.toggled.connect(lambda dang, x=b: dang and (self._ap_che_do(), self._xem_lai()))
        self._ap_tai_lieu()
        self.bang_ho.currentCellChanged.connect(lambda r, c, r0, c0: r != r0 and self.xem_dong(r, c))
        self.bang_ho.cellClicked.connect(lambda r, c: self.xem_dong(r, c))
        self._nap_lua_chon()
        if dot_id is not None and self.cb_dot.findData(dot_id) >= 0:
            self.cb_dot.setCurrentIndex(self.cb_dot.findData(dot_id))       # -> _theo_dot: hộ của đợt, mọi mẫu, thư mục của đợt
        if che_do in ('du_thao', 'chinh_thuc'):
            self.dat_che_do(che_do)
        self._ap_pham_vi()
        if self.ma_ho_chon:                         # mở từ hộ đang chọn: xem trước ngay hộ đầu
            i = next((i for i, h in enumerate(self.ho) if h['ma_ho'] == self.ma_ho_chon[0]), None)
            if i is not None:
                self.bang_ho.setCurrentCell(i, 1)
        self._dem()

    def _doc_ds_ho(self, con, in_an, ma_ho_chon) -> None:
        """Hộ + tình trạng lập phương án."""
        # hộ + tình trạng lập phương án: "đã lập" không tính phương án phần mềm tự lập lúc tạo Dự án mới mà chưa soát
        kq = nghiep_vu.tinh_tat_ca(con)
        self.tong = {k.ma_ho: k.tong for k in kq}
        self.lap = in_an.phan_loai_lap(con, {k.ma_ho: k.co_phuong_an for k in kq})
        try:                                    # 24/10/2026: thêm địa chỉ + đợt trình để lọc / sắp xếp (file cũ chưa có đợt: bỏ cột)
            self.ho = [dict(r) for r in con.execute(
                'SELECT h.ma_ho, h.thu_tu, h.ho_ten, h.dia_chi, d.ten AS dot FROM ho h LEFT JOIN dot_trinh d ON d.id = h.dot_id '
                'ORDER BY h.thu_tu, h.ma_ho')]
        except sqlite3.OperationalError:
            self.ho = [dict(r, dot=None) for r in con.execute('SELECT ma_ho, thu_tu, ho_ten, dia_chi FROM ho ORDER BY thu_tu, ma_ho')]
        self._stt = {h['ma_ho']: i for i, h in enumerate(self.ho)}          # thứ tự gốc của dự án (danh sách xuất theo thứ tự này)
        self.ds_tat_ca = [h['ma_ho'] for h in self.ho]
        self.ds_pa = [m for m in self.ds_tat_ca if self.lap.get(m) == 'da_lap']
        self.ds_tu_lap = [m for m in self.ds_tat_ca if self.lap.get(m) == 'tu_lap']
        self.ds_co_pa = [m for m in self.ds_tat_ca if self.lap.get(m) != 'chua']
        self.ma_ho_chon = [m for m in (ma_ho_chon or []) if m is not None]

    def _tao_trang_thai_xuat(self, con) -> None:
        """Các ô trạng thái dùng cho lõi xuất, không hiện."""
        # trạng thái dùng cho lõi xuất, không hiện: phạm vi, đợt chọn ở dòng "In ..."; đầu ra theo ô Word / PDF và nút In; luôn chia PA CHI TIET / PA TONG khi nhiều hộ; luôn mở thư mục kết quả
        self.cb_pham_vi = QComboBox()
        if self.ma_ho_chon:
            ten = con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (self.ma_ho_chon[0],)).fetchone()[0]
            self.cb_pham_vi.addItem(f'Hộ đang chọn: {ten}' if len(self.ma_ho_chon) == 1
                                    else f'{len(self.ma_ho_chon)} hộ đang chọn', 'chon')
        self.cb_pham_vi.addItem(f'Đã lập phương án ({len(self.ds_pa)} hộ)', 'pa')
        if self.ds_tu_lap:
            self.cb_pham_vi.addItem(f'Tự lập, chưa soát ({len(self.ds_tu_lap)} hộ)', 'tu_lap')
            self.cb_pham_vi.addItem(f'Mọi hộ có phương án ({len(self.ds_co_pa)} hộ)', 'co_pa')
        self.cb_pham_vi.addItem(f'Tất cả ({len(self.ds_tat_ca)} hộ)', 'tat_ca')
        self.cb_pham_vi.addItem('Tự chọn', 'tu_chon')
        self.cb_pham_vi.currentIndexChanged.connect(lambda _: self._theo_pham_vi())
        self.cb_dot = QComboBox()
        self.cb_dot.addItem('Không theo đợt', None)
        from . import quan_ly
        try:
            self.ds_dot = quan_ly.ds_dot(con)
        except Exception:                               # file chỉ xem phiên bản cũ
            self.ds_dot = []
        for d in self.ds_dot:
            self.cb_dot.addItem(f'{d.ten} - {d.so_ho} hộ' + (f' - {d.van_ban_trinh}' if d.van_ban_trinh else ''), d.id)
        self.cb_dot.currentIndexChanged.connect(lambda _: self._theo_dot())
        self.o_chia = QCheckBox('Lưu thành 2 thư mục "PA CHI TIET" và "PA TONG"')
        self.o_chia.setChecked(True)
        self.o_mo = QCheckBox('Mở thư mục kết quả khi xong')
        self.o_mo.setChecked(True)
        self.r_excel = QRadioButton('File Excel / Word (.xlsx / .docx)')
        self.r_pdf = QRadioButton('File Excel / Word + PDF (qua Microsoft Excel / Word)')
        self.r_in = QRadioButton('Gửi cả lô ra máy in mặc định (qua Microsoft Excel / Word)')
        self.r_pdf.setChecked(True)
        self.nhom_ra = QButtonGroup(self)
        for b in (self.r_excel, self.r_pdf, self.r_in):
            self.nhom_ra.addButton(b)
        self.o_word = QCheckBox('Xuất bản Word (.docx) chuẩn Nghị định 30', self)
        self.o_word.setChecked(True)
        self.o_word.setVisible(False)
        self.chi_tiet_theo_word = False                 # hộp ẩn của Xuất bản theo đợt: bỏ tích Word là không xuất phương án chi tiết, PDF chỉ cho hồ sơ kèm theo
        # chế độ phát hành (đặc tả V10 phần V); mở bảng in: mặc định Dự thảo (người dùng 05/11/2026)
        self.r_du_thao = QRadioButton('Bản DỰ THẢO (niêm yết công khai, họp dân - Bước 6)')
        self.r_chinh_thuc = QRadioButton('Bản CHÍNH THỨC (trình thẩm định - Bước 8, gửi từng hộ - Bước 11)')
        self.r_du_thao.setChecked(True)
        self.nhom_che_do = QButtonGroup(self)
        for b in (self.r_du_thao, self.r_chinh_thuc):
            self.nhom_che_do.addButton(b)
        self.r_du_thao.setToolTip(MO_TA_CHE_DO['du_thao'])
        self.r_chinh_thuc.setToolTip(MO_TA_CHE_DO['chinh_thuc'])
        # các ô trạng thái trên không vào bố cục: phải có cha, nếu không tín hiệu nối lambda giữ self làm cả hộp không bao giờ được giải
        # phóng sau khi đóng (mỗi lần mở bảng In sót 12 widget cấp cao, allWidgets ngày càng dài)
        for w in (self.cb_pham_vi, self.cb_dot, self.o_chia, self.o_mo, self.r_excel, self.r_pdf, self.r_in, self.r_du_thao, self.r_chinh_thuc):
            w.setParent(self)
            w.setVisible(False)

    def _dung_chon_ho(self, in_an) -> None:
        """Danh sách hộ (khung mở bằng nút Chọn…)."""

        # ---- danh sách hộ (khung mở bằng nút Chọn…): lọc theo chữ, sắp xếp theo cột; tình trạng, đợt, địa chỉ vẫn tìm được, hiện ở chú thích và màu tên
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm hộ (không cần dấu)…')
        loc_khi_ngung_go(self.o_tim, self._loc)
        self.bang_ho = QTableWidget(len(self.ho), 6)
        self.bang_ho.setHorizontalHeaderLabels(['Chọn', 'STT - Họ và tên', 'Tình trạng', 'Tổng tiền (đ)', 'Đợt', 'Địa chỉ'])
        self.bang_ho.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.bang_ho.horizontalHeader().setSectionsClickable(True)           # bấm tiêu đề cột để sắp xếp
        self.bang_ho.horizontalHeader().sectionClicked.connect(self._sap_xep)
        self._cot_sx, self._chieu_sx = None, Qt.SortOrder.AscendingOrder
        self.bang_ho.verticalHeader().setVisible(False)
        self.bang_ho.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang_ho.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        from .giao_dien import TOKEN
        mau_lap = {'da_lap': '#1B5E20', 'tu_lap': TOKEN['canh_bao'], 'chua': '#7A8794'}
        for i, h in enumerate(self.ho):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, h['ma_ho'])
            self.bang_ho.setItem(i, 0, chk)
            lap = self.lap.get(h['ma_ho'], 'chua')
            khoa_sx = {1: i, 3: float(self.tong.get(h['ma_ho'], D(0)))}      # STT theo thứ tự dự án, tiền theo số
            dia_chi = ' '.join(str(h.get('dia_chi') or '').split())
            for c, v in enumerate((f'{h["thu_tu"]}. {h["ho_ten"]}', in_an.LAP[lap],
                                   vn(self.tong.get(h['ma_ho'], D(0))) if lap != 'chua' else '', h.get('dot') or '', dia_chi), start=1):
                it = _MucSap(v)
                if c in khoa_sx:
                    it.setData(Qt.ItemDataRole.UserRole + 1, khoa_sx[c])
                if c == 1:
                    it.setToolTip(' · '.join(x for x in (v, in_an.LAP[lap], f'Đợt {h["dot"]}' if h.get('dot') else '', dia_chi) if x))
                    if lap != 'da_lap':
                        it.setForeground(QColor(mau_lap[lap]))
                if c == 3:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.bang_ho.setItem(i, c, it)
        dau = self.bang_ho.horizontalHeader()
        dau.setStretchLastSection(False)
        self.bang_ho.setColumnWidth(0, 62)
        dau.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        dau.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        for c in (2, 4, 5):
            self.bang_ho.setColumnHidden(c, True)
        self.bang_ho.itemChanged.connect(self._doi_chon)
        self.lb_chon = QLabel()
        self.lb_chon.setWordWrap(True)
        from .giao_dien import NhanBoDem
        self.lb_bo_dem = NhanBoDem()                    # bộ đếm vùng chọn (như Excel): nằm DƯỚI bảng, không nổi đè lên cột tiền
        self.b_chon_het = QPushButton('Chọn hết')
        self.b_chon_het.setToolTip('Chọn các hộ đang hiện trong danh sách')
        self.b_chon_het.clicked.connect(lambda: self._danh_dau(self._dang_hien(), giu=True))
        self.b_bo_chon = QPushButton('Bỏ chọn')
        self.b_bo_chon.clicked.connect(lambda: self._danh_dau([]))
        self.khung_chon_ho = QWidget()
        self.khung_chon_ho.setFixedWidth(330)
        v_ho = QVBoxLayout(self.khung_chon_ho)
        v_ho.setContentsMargins(0, 0, 0, 0)
        v_ho.setSpacing(4)
        v_ho.addWidget(self.o_tim)
        h_nut_ho = QHBoxLayout()
        h_nut_ho.addWidget(self.b_chon_het)
        h_nut_ho.addWidget(self.b_bo_chon)
        h_nut_ho.addStretch(1)
        v_ho.addLayout(h_nut_ho)
        v_ho.addWidget(self.bang_ho, 1)
        v_ho.addWidget(self.lb_bo_dem)


    def _dung_rail(self) -> QWidget:
        """Cột trái: In | Xuất | Xuất dữ liệu, như cột trái của Word."""
        # ---- cột trái: In | Xuất | Xuất dữ liệu, như cột trái của Word
        from .thanh_phan_in import IC_DU_LIEU, IC_IN, IC_LUI, IC_XUAT, nut_rail
        cot_rail = QWidget()
        cot_rail.setFixedWidth(136)
        v_rail = QVBoxLayout(cot_rail)
        v_rail.setContentsMargins(0, 4, 0, 4)
        v_rail.setSpacing(2)
        b_lui = nut_rail('Đóng', IC_LUI, False)
        b_lui.clicked.connect(self.reject)
        v_rail.addWidget(b_lui)
        v_rail.addSpacing(10)
        self.nut_rail = {}
        self.nhom_rail = QButtonGroup(self)
        for k, chu, ma in (('in', 'In', IC_IN), ('xuat', 'Xuất', IC_XUAT), ('du_lieu', 'Xuất dữ liệu', IC_DU_LIEU)):
            if k == 'du_lieu' and not self._co_du_lieu:
                continue
            b = nut_rail(chu, ma)
            b.clicked.connect(lambda _=False, x=k: self.dat_pham_vi(x))
            self.nhom_rail.addButton(b)
            self.nut_rail[k] = b
            v_rail.addWidget(b)
        self.nut_rail['in'].setChecked(True)
        v_rail.addStretch(1)
        return cot_rail

    def _dung_nut_lon(self) -> None:
        """Cột tùy chọn: tiêu đề, nút In + số bản sao, nút Xuất."""
        from .thanh_phan_in import IC_IN, IC_XUAT, NutLon, nhan_de_muc

        # ---- cột tùy chọn
        self.lb_tieu_de = nhan_de_muc('In', lon=True)
        # In: nút lớn + số bản sao
        self.b_in = NutLon('In', IC_IN)
        self.b_in.setToolTip('In tài liệu đang xem (Ctrl+P)')
        self.b_in.clicked.connect(lambda: self.in_ra_may())
        self.o_so_ban = QSpinBox()
        self.o_so_ban.setRange(1, 99)
        self.khung_nut_in = QWidget()
        h_in = QHBoxLayout(self.khung_nut_in)
        h_in.setContentsMargins(0, 0, 0, 0)
        h_in.addWidget(self.b_in)
        h_in.addSpacing(10)
        h_in.addWidget(QLabel('Số bản sao:'))
        h_in.addWidget(self.o_so_ban)
        h_in.addStretch(1)
        # Xuất: nút lớn
        self.b_thuc_hien = NutLon('Xuất file', IC_XUAT)
        self.b_thuc_hien.setToolTip('Tạo file theo các ô đã tích, lưu vào thư mục dưới đây')
        self.b_thuc_hien.clicked.connect(lambda: self.thuc_hien())
        self.khung_nut_xuat = QWidget()
        h_x = QHBoxLayout(self.khung_nut_xuat)
        h_x.setContentsMargins(0, 0, 0, 0)
        h_x.addWidget(self.b_thuc_hien)
        h_x.addStretch(1)


    def _dung_may_in(self) -> None:
        """Máy in."""
        from .thanh_phan_in import IC_IN, HangChon, ds_may_in, may_in_mac_dinh, nhan_de_muc, nut_lien_ket, trang_thai_may_in
        # Máy in
        ds_may = ds_may_in() if self._in_pdf else []
        self._may_mac_dinh = may_in_mac_dinh() if self._in_pdf else ''
        self.hang_may_in = HangChon(IC_IN, [(m, m, trang_thai_may_in(m)) for m in ds_may] or [('', 'Máy in mặc định của Windows', 'Qua Microsoft Word / Excel')])
        self.hang_may_in.dat(self._may_mac_dinh, im=True)
        self.hang_may_in.doi.connect(lambda _m: self._theo_may_in())
        self.b_thuoc_tinh = nut_lien_ket('Thuộc tính máy in')
        self.b_thuoc_tinh.clicked.connect(lambda: self.mo_thuoc_tinh_may_in())
        self.b_thuoc_tinh.setEnabled(bool(ds_may))
        self.b_hop_windows = nut_lien_ket('Hộp in Windows…')
        self.b_hop_windows.setToolTip('Hộp in chuẩn của Windows như Word, Excel: máy in, trang, số bản; nút Preferences chỉnh khay giấy, '
                                      'chất lượng, ghim… theo trình điều khiển, áp dụng cho lần in này')
        self.b_hop_windows.clicked.connect(lambda: self.in_hop_windows())
        self.b_hop_windows.setEnabled(bool(ds_may))
        self.khung_may_in = QWidget()
        v_may = QVBoxLayout(self.khung_may_in)
        v_may.setContentsMargins(0, 0, 0, 0)
        v_may.setSpacing(3)
        v_may.addWidget(nhan_de_muc('Máy in'))
        v_may.addWidget(self.hang_may_in)
        h_lk = QHBoxLayout()
        h_lk.setContentsMargins(0, 0, 0, 0)
        h_lk.addStretch(1)
        h_lk.addWidget(self.b_hop_windows)
        h_lk.addSpacing(10)
        h_lk.addWidget(self.b_thuoc_tinh)
        v_may.addLayout(h_lk)
        if not self._in_pdf:                            # bản Win 7 (Qt5): in qua Word / Excel, không có hộp này
            self.b_hop_windows.hide()


    def _dung_thiet_dat(self, con, parent) -> None:
        """Thiết đặt chung: hộ nào, tài liệu nào, bản nào."""
        from .thanh_phan_in import IC_BAN, IC_HO, IC_TAI_LIEU, HangChon, nhan_de_muc
        # Thiết đặt chung: hộ nào, tài liệu nào, bản nào
        self.hang_pham_vi = HangChon(IC_HO, self._ds_pham_vi())
        self.hang_pham_vi.doi.connect(self._doi_hang_pham_vi)
        self.o_ho = QLineEdit()
        self.o_ho.setPlaceholderText('1-3, 5')
        self.o_ho.setToolTip('Một hộ: gõ STT hoặc tên. Nhiều hộ: gõ STT kiểu 1-3, 5 rồi Enter.')
        self.o_ho.returnPressed.connect(lambda: self._nhap_o_ho())
        self.b_ho_truoc = QPushButton('◀')
        self.b_ho_truoc.setToolTip('Hộ trước')
        self.b_ho_truoc.clicked.connect(lambda: self.sang_ho(-1))
        self.b_ho_sau = QPushButton('▶')
        self.b_ho_sau.setToolTip('Hộ sau')
        self.b_ho_sau.clicked.connect(lambda: self.sang_ho(1))
        for b in (self.b_ho_truoc, self.b_ho_sau):
            b.setFixedWidth(30)
            b.setProperty('khong_icon', True)
        self.b_chon_ho = QPushButton('Chọn…')
        self.b_chon_ho.setCheckable(True)
        self.b_chon_ho.setProperty('khong_icon', True)
        self.b_chon_ho.setToolTip('Mở danh sách hộ để tìm, tích chọn')
        self.b_chon_ho.toggled.connect(lambda _b: self._ap_pham_vi())
        self.hang_tai_lieu = HangChon(IC_TAI_LIEU, [('ct', 'Phương án chi tiết', 'Word')])
        self.hang_tai_lieu.doi.connect(lambda _k: self._xem_lai(True))
        self.hang_che_do = HangChon(IC_BAN, [(k, chu, mo_ta) for k, chu, mo_ta in THE_CHE_DO])
        self.hang_che_do.doi.connect(lambda k: (self.r_du_thao if k == 'du_thao' else self.r_chinh_thuc).setChecked(True))
        # 1.0.52 (người dùng 02/11/2026): che số CCCD trên bản niêm yết công khai - tùy chọn của dự án, mặc định tắt; văn bản chính thức luôn đủ 12 số
        from .an_toan import che_cccd_niem_yet
        self.o_che_cccd = QCheckBox('Che số CCCD (bản niêm yết)')
        self.o_che_cccd.setToolTip('Chỉ áp cho bản Dự thảo dán tại điểm dân cư (Nghị định 13/2023/NĐ-CP): giữ 6 số đầu + 3 số cuối. Nhớ theo dự án.')
        self.o_che_cccd.setChecked(che_cccd_niem_yet(con))
        if getattr(parent, 'chi_doc', False):            # dự án mở chỉ xem: không ghi được tùy chọn - tắt ô, không cho bấm rồi báo lỗi
            self.o_che_cccd.setEnabled(False)
        self.o_che_cccd.toggled.connect(lambda bat: self._doi_che_cccd(bat))
        # 1.0.05: hộ có nhiều lần lập phương án (lần đầu + bổ sung) - in lần mới nhất (đợt trình bổ sung) hay cộng dồn
        from .lan_pa import co_bang, ho_nhieu_lan
        self.cb_lan = QComboBox()
        self.cb_lan.addItem('Lần mới nhất của mỗi hộ', 'moi_nhat')
        self.cb_lan.addItem('Cộng dồn mọi lần', 'cong_don')
        self.cb_lan.setToolTip('Hộ có phương án bổ sung: "mới nhất" chỉ in lần bổ sung đó; "cộng dồn" in tất cả các lần trong một bản.')
        self.so_ho_nhieu_lan = len(ho_nhieu_lan(con)) if co_bang(con) else 0
        self.cb_lan.currentIndexChanged.connect(lambda _: self._xem_lai())
        self.khung_thiet_dat = QWidget()
        v_td = QVBoxLayout(self.khung_thiet_dat)
        v_td.setContentsMargins(0, 0, 0, 0)
        v_td.setSpacing(4)
        v_td.addWidget(nhan_de_muc('Thiết đặt'))
        v_td.addWidget(self.hang_pham_vi)
        h_ho = QHBoxLayout()
        h_ho.setSpacing(4)
        h_ho.addWidget(QLabel('Hộ:'))
        h_ho.addWidget(self.o_ho, 1)
        h_ho.addWidget(self.b_ho_truoc)
        h_ho.addWidget(self.b_ho_sau)
        h_ho.addWidget(self.b_chon_ho)
        v_td.addLayout(h_ho)
        v_td.addWidget(self.lb_chon)
        v_td.addWidget(self.hang_tai_lieu)
        v_td.addWidget(self.hang_che_do)


    def _dung_in_them(self, lenh) -> None:
        """Chỉ khi in: trang, hai mặt, xếp bộ, khổ giấy."""
        from .thanh_phan_in import HAI_MAT, IC_KHO, IC_MAT, IC_XEP_BO, KHO_GIAY, XEP_BO, HangChon, nut_lien_ket
        # chỉ khi in: trang, hai mặt, xếp bộ, khổ giấy
        self.o_trang = QLineEdit()
        self.o_trang.setPlaceholderText('Tất cả các trang')
        self.o_trang.setToolTip('Trang cần in của tài liệu đang xem, ví dụ 1-3, 5')
        self.hang_mat = HangChon(IC_MAT, HAI_MAT)
        self.hang_xep_bo = HangChon(IC_XEP_BO, XEP_BO)
        self.hang_kho = HangChon(IC_KHO, KHO_GIAY)
        self.khung_in_them = QWidget()
        v_ith = QVBoxLayout(self.khung_in_them)
        v_ith.setContentsMargins(0, 0, 0, 0)
        v_ith.setSpacing(4)
        h_tr = QHBoxLayout()
        h_tr.addWidget(QLabel('Trang:'))
        h_tr.addWidget(self.o_trang, 1)
        v_ith.addLayout(h_tr)
        for w in (self.hang_mat, self.hang_xep_bo, self.hang_kho):
            v_ith.addWidget(w)
        self._theo_may_in()
        self.b_thiet_lap = nut_lien_ket('Thiết lập trang')
        self.b_thiet_lap.setToolTip('Lề, khổ giấy, phông chữ của mẫu in')
        if 'Quản lý Mẫu in & Bản in…' in lenh:
            self.b_thiet_lap.clicked.connect(lambda _=False, a=lenh['Quản lý Mẫu in & Bản in…']: a.trigger())


    def _dung_xuat_them(self, file_du_an) -> None:
        """Chỉ khi xuất: định dạng phương án chi tiết, hồ sơ kèm theo, nơi lưu."""
        from .giao_dien import NhanRutGon
        from .thanh_phan_in import nhan_de_muc, nut_lien_ket
        # chỉ khi xuất: định dạng phương án chi tiết (Word, Excel, PDF độc lập; PDF lấy từ bản Word, chỉ tích PDF thì không để lại file Word), hồ sơ kèm theo, nơi lưu
        self.o_ct = QCheckBox('Word')
        self.o_ct.setToolTip('Bản Word thể thức Nghị định 30/2020')
        self.o_ct.setChecked(True)
        self.o_ct_excel = QCheckBox('Excel')
        self.o_ct_excel.setToolTip('Một file Excel, mỗi hộ một sheet, số liệu như bản Word: để sửa, tính tiếp')
        self.o_pdf = QCheckBox('PDF')
        self.o_pdf.setToolTip('PDF lấy từ bản Word. Máy không có Word: PDF gần đúng.')
        self.o_pdf.setChecked(True)
        self.o_gop = QCheckBox('Gộp một file')
        self.o_gop.setToolTip('Gộp PDF các hộ thành PHUONG_AN_CHI_TIET.pdf')
        self.o_pdf.toggled.connect(lambda bat: None if self.r_in.isChecked() else (self.r_pdf if bat else self.r_excel).setChecked(True))
        self.r_pdf.toggled.connect(lambda bat: bat and self.o_pdf.setChecked(True))
        self.r_excel.toggled.connect(lambda bat: bat and self.o_pdf.setChecked(False))
        for b in (self.r_excel, self.r_pdf, self.r_in):
            b.toggled.connect(lambda _: self._bat_tuy_chon())
        self._bat_tuy_chon()
        from . import bang_dieu_chinh as _bdc
        self.o_bth = QCheckBox('Bảng tổng hợp')
        self.o_bth.setToolTip('Bảng tổng hợp kinh phí A3 ngang (Excel)')
        self.o_bth.setChecked(not self.ma_ho_chon)
        self.o_bth_dc = QCheckBox('Bảng điều chỉnh')
        self.o_bth_dc.setToolTip('Bảng tổng hợp các hộ có phương án điều chỉnh: đã phê duyệt, đề nghị điều chỉnh, chênh lệch (A3 ngang)')
        self.co_dieu_chinh = _bdc.co_dieu_chinh(self.con)
        self.o_bth_dc.setChecked(self.co_dieu_chinh)
        self.o_tt = QCheckBox('Tờ trình')
        self.o_tt.setToolTip('Tờ trình đề nghị thẩm định, phê duyệt; số, ngày theo đợt. Sửa mẫu ở cửa sổ Trình phê duyệt.')
        self.o_bc = QCheckBox('Báo cáo ý kiến')
        self.o_bc.setToolTip('Báo cáo tổng hợp ý kiến nhân dân, tiếp thu và giải trình (Word)')
        # nơi lưu: tự hiểu là thư mục chứa file dự án (người dùng 05/11/2026), không nhớ thư mục lần trước; đổi khi thật cần
        goc = Path(file_du_an).parent if file_du_an else Path.home() / 'Documents'
        self.o_thu_muc = QLineEdit(str(goc / f'BanIn_{datetime.now():%Y%m%d_%H%M}'), self)
        self.o_thu_muc.setVisible(False)
        self.lb_luu = NhanRutGon('')
        self.o_thu_muc.textChanged.connect(lambda *_: self._ve_noi_luu())
        self._ve_noi_luu()
        self.b_chon_tm = nut_lien_ket('Đổi thư mục')
        self.b_chon_tm.clicked.connect(lambda: self._chon_thu_muc())
        self.khung_xuat_them = QWidget()
        v_xt = QVBoxLayout(self.khung_xuat_them)
        v_xt.setContentsMargins(0, 0, 0, 0)
        v_xt.setSpacing(4)
        v_xt.addWidget(nhan_de_muc('Phương án chi tiết'))
        h_dd = QHBoxLayout()
        for o in (self.o_ct, self.o_ct_excel, self.o_pdf, self.o_gop):
            h_dd.addWidget(o)
        h_dd.addStretch(1)
        v_xt.addLayout(h_dd)
        self.khung_kem = QWidget()
        lu_kem = QGridLayout(self.khung_kem)
        lu_kem.setContentsMargins(0, 0, 0, 0)
        lu_kem.addWidget(nhan_de_muc('Kèm theo'), 0, 0, 1, 2)
        for i, o in enumerate((self.o_bth, self.o_bth_dc, self.o_tt, self.o_bc)):
            lu_kem.addWidget(o, 1 + i // 2, i % 2)
        v_xt.addWidget(self.khung_kem)
        v_xt.addWidget(nhan_de_muc('Lưu vào'))
        v_xt.addWidget(self.lb_luu)
        v_xt.addWidget(self.b_chon_tm, 0, Qt.AlignmentFlag.AlignRight)


    def _dung_du_lieu(self, lenh) -> None:
        """Xuất dữ liệu: dùng lại lệnh của cửa sổ chính."""
        # Xuất dữ liệu: dùng lại lệnh của cửa sổ chính
        self.khung_du_lieu = QWidget()
        v_dl = QVBoxLayout(self.khung_du_lieu)
        v_dl.setContentsMargins(0, 4, 0, 0)
        self.nut_du_lieu = {}
        for chu, ten in (('Danh sách hộ (Excel)', 'Xuất danh sách hộ…'), ('Báo cáo đối chiếu (Excel)', 'Xuất báo cáo đối chiếu…')):
            if ten in lenh:
                b = QPushButton(chu)
                b.clicked.connect(lambda _=False, a=lenh[ten]: a.trigger())
                self.nut_du_lieu[ten] = b
                v_dl.addWidget(b)
        n = QLabel('File lưu vào thư mục chứa file dự án.')
        n.setProperty('vai', 'nhan')
        v_dl.addWidget(n)


    def _dung_cot_trai(self) -> QScrollArea:
        """Ghép các khung thành cột tùy chọn có cuộn."""
        trai = QWidget()
        trai.setObjectName('the_tuy_chon_in')
        trai.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # kiểu ở QSS chung (giao_dien): kiểu cục bộ trên khung chứa bắt Qt tính lại kiểu cho cả cây con
        lo_trai = QVBoxLayout(trai)
        lo_trai.setContentsMargins(12, 6, 12, 6)
        lo_trai.setSpacing(5)
        lo_trai.addWidget(self.lb_tieu_de)
        for w in (self.khung_nut_in, self.khung_nut_xuat, self.khung_may_in, self.khung_thiet_dat, self.khung_in_them, self.khung_xuat_them, self.khung_du_lieu):
            lo_trai.addWidget(w)
        lo_trai.addWidget(self.o_che_cccd)
        if self.so_ho_nhieu_lan:
            lo_trai.addWidget(self.cb_lan)
        else:
            self.cb_lan.setParent(trai)
            self.cb_lan.setVisible(False)
        lo_trai.addWidget(self.b_thiet_lap, 0, Qt.AlignmentFlag.AlignRight)
        lo_trai.addStretch(1)
        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        cuon.setFrameShape(QFrame.Shape.NoFrame)
        cuon.setStyleSheet('QScrollArea { background: transparent; border: 0; }')
        cuon.viewport().setAutoFillBackground(False)
        cuon.setWidget(trai)
        cuon.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cuon.setFixedWidth(350)
        self.cuon_trai = cuon
        return cuon

    # ---- phạm vi in: một hộ / nhiều hộ; cột trái: in / xuất / xuất dữ liệu
    def _ds_pham_vi(self) -> list:
        ds = [('mot', 'In một hộ', 'Hộ đang trỏ')]
        if len(self.ma_ho_chon) >= 1:
            ds.append(('chon', f'In {len(self.ma_ho_chon)} hộ đang chọn', 'Chọn ở danh sách hộ'))
        ds.append(('pa', 'In các hộ đã lập phương án', f'{len(self.ds_pa)} hộ'))
        if self.ds_tu_lap:
            ds.append(('tu_lap', 'In các hộ tự lập, chưa soát', f'{len(self.ds_tu_lap)} hộ'))
            ds.append(('co_pa', 'In mọi hộ có phương án', f'{len(self.ds_co_pa)} hộ'))
        ds.append(('tat_ca', 'In tất cả các hộ', f'{len(self.ds_tat_ca)} hộ'))
        ds.append(('tu_chon', 'In các hộ tự chọn', 'Tích ở danh sách hộ'))
        ds += [(f'dot:{d.id}', f'In {d.ten}', f'{d.so_ho} hộ') for d in self.ds_dot]
        return ds

    def _doi_hang_pham_vi(self, k) -> None:
        self._mot = k == 'mot'
        if not self._mot:
            if str(k).startswith('dot:'):
                self.cb_dot.setCurrentIndex(self.cb_dot.findData(int(str(k)[4:])))
            else:
                self.cb_dot.blockSignals(True)
                self.cb_dot.setCurrentIndex(0)
                self.cb_dot.blockSignals(False)
                self.cb_pham_vi.setCurrentIndex(self.cb_pham_vi.findData(k))
                self._theo_pham_vi()
        self._ap_pham_vi()
        self._xem_lai()

    def pham_vi_in(self) -> str:
        """'mot' | 'nhieu' | 'du_lieu'."""
        return 'du_lieu' if self._rail == 'du_lieu' else ('mot' if self._mot else 'nhieu')

    def mot_ho(self) -> bool:
        return self._mot

    def dat_pham_vi(self, k: str) -> None:
        """'in' | 'xuat' | 'du_lieu': cột trái; 'mot' | 'nhieu': phạm vi hộ."""
        if k in ('in', 'xuat', 'du_lieu'):
            self._rail = k
            self.nut_rail[k].setChecked(True)
            self._ap_pham_vi()
        elif k == 'mot':
            self.hang_pham_vi.dat('mot')
        elif self._mot:
            self.hang_pham_vi.dat('chon' if self.ma_ho_chon else 'pa')

    def _ap_pham_vi(self) -> None:
        """Mỗi mục chỉ hiện đúng phần cần: In có máy in, số bản, trang, hai mặt; Xuất có định dạng, kèm theo, nơi lưu; một hộ không có tích chọn, hồ sơ kèm theo."""
        r = self._rail
        la_in, xuat, du_lieu = r == 'in', r == 'xuat', r == 'du_lieu'
        self.lb_tieu_de.setText({'in': 'In', 'xuat': 'Xuất', 'du_lieu': 'Xuất dữ liệu'}[r])
        for w, hien in ((self.khung_nut_in, la_in), (self.khung_may_in, la_in), (self.khung_in_them, la_in and self._in_pdf), (self.b_thiet_lap, la_in and bool(getattr(self.parent(), 'lenh', None))),
                        (self.khung_nut_xuat, xuat), (self.khung_xuat_them, xuat), (self.khung_thiet_dat, not du_lieu), (self.khung_du_lieu, du_lieu), (self.phai, not du_lieu),
                        (self.khung_chon_ho, self.b_chon_ho.isChecked() and not du_lieu)):
            w.setVisible(hien)
        self.o_che_cccd.setVisible(not du_lieu and self.che_do() == 'du_thao')
        nhieu = not self._mot
        for w in (self.b_chon_het, self.b_bo_chon, self.khung_kem, self.o_gop):
            w.setVisible(nhieu)
        self.o_bth_dc.setVisible(self.co_dieu_chinh)
        for w in (self.b_ho_truoc, self.b_ho_sau):
            w.setVisible(self._mot)
        self.bang_ho.setColumnHidden(0, not nhieu)
        self._dat_ds_tai_lieu()
        if self._mot and self.bang_ho.currentRow() < 0 and self.bang_ho.rowCount():
            r0 = next((i for i in range(self.bang_ho.rowCount()) if self.bang_ho.item(i, 0).data(Qt.ItemDataRole.UserRole) in self.ds_pa), 0)
            self.bang_ho.setCurrentCell(r0, 1)
        self._dem()

    def tai_lieu(self) -> str:
        return self.hang_tai_lieu.gia_tri() or 'ct'

    def _dat_ds_tai_lieu(self) -> None:
        """Tài liệu đang xem cũng là tài liệu sẽ in. Một hộ: phương án chi tiết; nhiều hộ: thêm gộp, bảng tổng hợp; Chính thức: thêm tờ trình, báo cáo ý kiến."""
        ds = [('ct', 'Phương án chi tiết', 'Word' if self._mot else 'Word, xem từng hộ')]
        if not self._mot:
            ds.append(('ct_gop', 'Phương án chi tiết', 'PDF gộp các hộ'))
        ds.append(('ct_excel', 'Phương án chi tiết', 'Excel, mỗi hộ một sheet'))
        if not self._mot:
            ds.append(('bth', 'Bảng tổng hợp', 'Excel, A3 ngang'))
            if self.co_dieu_chinh:
                ds.append(('dc', 'Bảng điều chỉnh', 'Excel, A3 ngang'))
            if self.che_do() == 'chinh_thuc':
                ds += [('tt', 'Tờ trình', 'Word'), ('bc', 'Báo cáo ý kiến', 'Word')]
        self.hang_tai_lieu.dat_ds(ds)

    def _theo_may_in(self) -> None:
        """Đổi máy in: hai mặt theo cài đặt của máy in đó, như Word."""
        from .thanh_phan_in import hai_mat_mac_dinh
        m = self.hang_may_in.gia_tri()
        if m:
            self.hang_mat.dat(hai_mat_mac_dinh(m), im=True)

    def mo_thuoc_tinh_may_in(self) -> None:
        from . import thanh_phan_in as tp
        m = self.hang_may_in.gia_tri()
        if not m:
            return
        try:
            tp.mo_thuoc_tinh(m)
        except OSError as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không mở được thuộc tính máy in', e))

    def _ve_noi_luu(self) -> None:
        """Hiện phần cuối đường dẫn (thư mục dự án \\\\ thư mục bản in), đủ đường dẫn ở chú thích."""
        p = Path(self.o_thu_muc.text())
        self.lb_luu.setText(f'{p.parent.name}\\{p.name}' if p.parent.name else str(p))
        self.lb_luu.setToolTip(str(p))

    # ---- ô Hộ: như ô Trang của Word
    def _stt_ho(self) -> dict:
        return {h['ma_ho']: h['thu_tu'] for h in self.ho}

    def _ve_o_ho(self) -> None:
        ds = self.ds_ho()
        stt = self._stt_ho()
        if self._mot:
            h = next((x for x in self.ho if ds and x['ma_ho'] == ds[0]), None)
            chu = f'{h["thu_tu"]}. {h["ho_ten"]}' if h else ''
        else:
            from .thanh_phan_in import chu_day_so
            chu = chu_day_so(stt[m] for m in ds if stt.get(m) is not None)
        self.o_ho.setText(chu)
        self.o_ho.setToolTip(chu or self.o_ho.placeholderText())
        self.o_ho.setCursorPosition(0)

    def _nhap_o_ho(self) -> None:
        """Gõ STT kiểu 1-3, 5 (một hộ: STT đầu); gõ chữ: tìm trong danh sách hộ."""
        from .thanh_phan_in import doc_day_so
        chu = self.o_ho.text().strip()
        try:
            so = doc_day_so(chu.split('.')[0] if self._mot else chu, 'Hộ')
        except LoiNhap:
            self.b_chon_ho.setChecked(True)
            self.o_tim.setText(chu)
            self._loc(chu)
            return
        theo_stt = {h['thu_tu']: h['ma_ho'] for h in self.ho}
        ds = [theo_stt[x] for x in so if x in theo_stt]
        if self._mot:
            if ds:
                self._den_ho(ds[0])
        else:
            self._danh_dau(ds)
        self._ve_o_ho()

    def _den_ho(self, ma) -> None:
        r = next((i for i in range(self.bang_ho.rowCount()) if self.bang_ho.item(i, 0).data(Qt.ItemDataRole.UserRole) == ma), -1)
        if r >= 0:
            self.bang_ho.setCurrentCell(r, 1)

    def sang_ho(self, buoc: int) -> None:
        """Hộ trước / hộ sau trong danh sách đang hiện (thẻ Một hộ)."""
        hien = [i for i in range(self.bang_ho.rowCount()) if not self.bang_ho.isRowHidden(i)]
        if not hien:
            return
        r = self.bang_ho.currentRow()
        k = hien.index(r) + buoc if r in hien else 0
        if 0 <= k < len(hien):
            self.bang_ho.setCurrentCell(hien[k], 1)

    # ---- xem trước = tài liệu sẽ in
    def _xem_lai(self, ngay: bool = False) -> None:
        if self._rail == 'du_lieu' or not hasattr(self, 'w_preview'):
            return
        k, ds = self.tai_lieu(), self.ds_ho()
        if k == 'ct':
            if self._ma_xem is None or (ds and self._ma_xem not in ds and self._mot):
                r = self.bang_ho.currentRow()
                it = self.bang_ho.item(r, 0) if r >= 0 else None
                self._ma_xem = it.data(Qt.ItemDataRole.UserRole) if it is not None else (ds[0] if ds else None)
            self._lam_moi_xem_truoc(ngay)
        elif not ds:
            self.w_preview.bao('Chọn hộ để xem trước.')
        elif k == 'ct_gop':
            self.xem_truoc_nhieu_ho(ngay)
        elif k == 'ct_excel':
            self.xem_truoc_excel_chi_tiet(ngay)
        elif k == 'bth':
            self.xem_truoc_bang_tong_hop(ngay)
        else:
            self.xem_truoc_van_ban(k, ngay)

    def xem_truoc_van_ban(self, k: str, ngay: bool = False, ds=None):
        """Xem trước tờ trình ('tt'), báo cáo ý kiến ('bc'), bảng điều chỉnh ('dc') của các hộ đã chọn."""
        ds = list(self.ds_ho() if ds is None else ds)
        if not ds:
            return None
        du_thao = self.che_do() == 'du_thao'
        dot = self.dot_chon() if not du_thao else None
        khoa = (k, tuple(ds), du_thao, dot.id if dot else None)
        self._ma_xem = None
        ten = {'tt': 'Tờ trình', 'bc': 'Báo cáo ý kiến', 'dc': 'Bảng điều chỉnh'}[k]

        def tao(thu_muc):
            from . import van_ban_trinh as vb
            if k == 'tt':
                return vb.lap_van_ban(self.con, 'to_trinh', ds, Path(thu_muc), dot)
            if k == 'bc':
                from . import bao_cao_y_kien as bc
                return bc.ghi_docx(self.con, ds, Path(thu_muc) / bc.TEN_FILE, dot)
            from . import bang_dieu_chinh as bdc
            return bdc.lap(self.con, Path(thu_muc) / 'BANG_DIEU_CHINH.xlsx', ds, du_thao=du_thao)
        self.w_preview.yeu_cau(khoa, tao, ten, ngay)
        return khoa

    # ---- in: bản đang xem ra máy in đã chọn, như nút In của Word
    def _hoi_tu_lap(self, ds, xac_nhan: bool) -> bool:
        tu_lap = [m for m in ds if self.lap.get(m) == 'tu_lap']
        return not (tu_lap and xac_nhan and QMessageBox.question(
            self, TEN_UD, f'Có {len(tu_lap)} / {len(ds)} hộ đang chọn là phương án phần mềm TỰ LẬP, chưa mở soát và lưu. Vẫn in?') != QMessageBox.StandardButton.Yes)

    def _lap_ban_in(self, k: str, ds: list) -> None:
        """Lập bản PDF ĐỦ các hộ (xem trước chỉ tối đa XEM_NHIEU_TOI_DA hộ)."""
        if k in ('ct', 'ct_gop'):
            if len(ds) == 1:
                self._ma_xem = ds[0]
                self._lam_moi_xem_truoc(True)
            else:
                self.xem_truoc_nhieu_ho(True, tat_ca=True)
        elif k == 'ct_excel':
            self.xem_truoc_excel_chi_tiet(True, tat_ca=True)
        elif k == 'bth':
            self.xem_truoc_bang_tong_hop(True)
        else:
            self.xem_truoc_van_ban(k, True)

    def in_ra_may(self, xac_nhan: bool = True):
        """In tài liệu đang chọn: vẽ bản PDF (đúng như xem trước) lên máy in đã chọn, một lệnh in, đủ số bản, trang, hai mặt, xếp bộ, khổ giấy.
        Bản Win 7 (không QtPdf) hoặc lô quá lớn: Word / Excel gửi máy in mặc định. Trả số trang đã in hoặc kết quả xuất; None: chưa in."""
        from . import xem_truoc_tai_lieu as xt
        from .thanh_phan_in import doc_day_so
        ds = self.ds_ho()
        k = self.tai_lieu()
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Chưa chọn hộ nào để in.')
            return None
        try:
            trang = doc_day_so(self.o_trang.text())
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        if not self._hoi_tu_lap(ds, xac_nhan):
            return None
        if not self._in_pdf or len(ds) > TOI_DA_IN_PDF:
            return self._in_qua_office(k, xac_nhan)
        if xac_nhan and len(ds) > 1 and QMessageBox.question(self, TEN_UD, f'In {len(ds)} hộ tới {self.hang_may_in.gia_tri() or "máy in mặc định"}?') != QMessageBox.StandardButton.Yes:
            return None
        self.b_in.setEnabled(False)
        try:
            with con_tro_cho():
                self._lap_ban_in(k, ds)
                if not self.w_preview.cho_xong(CHO_LAP_BAN_IN_GIAY) or not self.w_preview.so_trang():
                    QMessageBox.warning(self, TEN_UD, 'Chưa lập được bản in: ' + (self.w_preview.thong_bao() or 'hết thời gian chờ.'))
                    return None
                n = xt.in_theo_tuy_chon(self.w_preview.doc, self.hang_may_in.gia_tri(), self.o_so_ban.value(), self.hang_xep_bo.gia_tri(), self.hang_mat.gia_tri(),
                                        self.hang_kho.gia_tri(), trang, self.w_preview.ten_tai_lieu())
        except OSError as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Chưa in được', e))
            return None
        finally:
            self.b_in.setEnabled(True)
        self._luu_lua_chon(Path(self.o_thu_muc.text()))
        if xac_nhan:
            if n:
                QMessageBox.information(self, TEN_UD, f'Đã gửi {n} trang tới {self.hang_may_in.gia_tri() or "máy in mặc định"}.')
            else:
                QMessageBox.warning(self, TEN_UD, f'Không có trang nào để in: tài liệu có {self.w_preview.so_trang()} trang, xem lại ô Trang.')
        return n

    def in_hop_windows(self):
        """1.0.78: lập bản in rồi mở hộp in chuẩn của Windows (điền sẵn máy in, số bản, xếp bộ, hai mặt đang chọn). Trả số trang đã in / None."""
        from . import xem_truoc_tai_lieu as xt
        ds = self.ds_ho()
        k = self.tai_lieu()
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Chưa chọn hộ nào để in.')
            return None
        if not self._hoi_tu_lap(ds, True):
            return None
        if not self._in_pdf:
            return self._in_qua_office(k, True)
        if len(ds) > TOI_DA_IN_PDF:
            QMessageBox.information(self, TEN_UD, f'Hộp in Windows nhận tối đa {TOI_DA_IN_PDF} hộ một lệnh. Chia nhỏ danh sách, hoặc bấm nút In để gửi qua Word / Excel.')
            return None
        try:
            with con_tro_cho():
                self._lap_ban_in(k, ds)
                xong = self.w_preview.cho_xong(CHO_LAP_BAN_IN_GIAY) and self.w_preview.so_trang()
            if not xong:
                QMessageBox.warning(self, TEN_UD, 'Chưa lập được bản in: ' + (self.w_preview.thong_bao() or 'hết thời gian chờ.'))
                return None
            may = xt.may_in_theo_tuy_chon(self.hang_may_in.gia_tri(), self.o_so_ban.value(), self.hang_xep_bo.gia_tri(), self.hang_mat.gia_tri(),
                                          self.w_preview.ten_tai_lieu())
            n = xt.in_co_hop_thoai(self, self.w_preview.doc, self.w_preview.ten_tai_lieu(), may, kho=self.hang_kho.gia_tri())
        except OSError as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Chưa in được', e))
            return None
        self._luu_lua_chon(Path(self.o_thu_muc.text()))
        return n

    def _in_qua_office(self, k: str, xac_nhan: bool):
        """Word / Excel gửi tới máy in mặc định (bản Win 7, lô lớn)."""
        self.r_in.setChecked(True)
        try:
            return self.thuc_hien(xac_nhan, chi=k)
        finally:
            (self.r_pdf if self.o_pdf.isChecked() else self.r_excel).setChecked(True)

    # ---- xem trước A4 (khung bên phải)
    def xem_dong(self, r: int, c: int = 1) -> None:
        """Xem trước bản in phương án chi tiết của hộ ở dòng r danh sách."""
        it = self.bang_ho.item(r, 0) if r >= 0 else None
        if it is None:
            return
        ma = it.data(Qt.ItemDataRole.UserRole)
        if self._mot:
            self._dem()
        elif c == 0 and self.tai_lieu() != 'ct':        # đang xem tài liệu chung, bấm ô tích: không đổi bản đang xem
            return
        else:
            self.hang_tai_lieu.dat('ct', im=True)        # bấm tên hộ: xem riêng hộ đó
        if ma == self._ma_xem and self.w_preview.dang_lap():
            return
        self._ma_xem = ma
        self._xem_lai()

    def khoa_xem_truoc(self):
        """Khóa bản xem trước: (hộ, dự thảo?, mẫu, che CCCD?) - cùng khóa thì dùng lại bản đã lập trong phiên. Mẫu = None (mẫu
        chính - 16/10/2026 bỏ ô chọn mẫu)."""
        return (self._ma_xem, self.che_do() == 'du_thao', None, self.o_che_cccd.isChecked(), self.lan_in())

    def lan_in(self) -> str:
        """'moi_nhat' / 'cong_don' (du_lieu_in.chon_lan_in)."""
        return self.cb_lan.currentData() or 'moi_nhat'

    def _lam_moi_xem_truoc(self, ngay: bool = False) -> None:
        if self._ma_xem is None:
            return
        from . import in_word
        ma, du_thao, mau, che, lan = self.khoa_xem_truoc()
        ten = next((h['ho_ten'] for h in self.ho if h['ma_ho'] == ma), '')

        def tao(thu_muc):                       # 22/10/2026: phương án chi tiết = bản Word (in_word) - như file xuất ra
            return in_word.xuat_chi_tiet_docx(self.con, ma, Path(thu_muc) / f'{du_lieu_in.ten_file_ho(self.con, ma)}.docx',
                                              du_thao=du_thao, lan=lan)

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
        du_thao, mau = self.che_do() == 'du_thao', None
        khoa = ('bth', tuple(ds), du_thao, mau, self.lan_in())
        self.hang_tai_lieu.dat('bth', im=True)
        self._ma_xem = None                         # bấm lại một dòng hộ thì xem lại phương án chi tiết của hộ đó
        lan = self.lan_in()

        def tao(thu_muc):
            return in_an.lap_bang_tong_hop(self.con, Path(thu_muc) / 'BangTongHop.xlsx', ds, du_thao=du_thao, lan=lan)
        self.w_preview.yeu_cau(khoa, tao, f'Bảng tổng hợp {len(ds)} hộ ({"dự thảo" if du_thao else "chính thức"})', ngay)
        return khoa

    def xem_truoc_nhieu_ho(self, ngay: bool = False, tat_ca: bool = False):
        """Xem trước phương án chi tiết của NHIỀU HỘ đang đánh dấu trên một bản (gộp PDF, có ô nhảy tới hộ). Tối đa XEM_NHIEU_TOI_DA hộ
        đầu danh sách đánh dấu. Trả khóa đã yêu cầu (None: chưa đánh dấu hộ nào)."""
        from . import in_word
        ds = list(self.ds_ho())
        if not ds:
            if not getattr(self, 'im_lang', False):
                QMessageBox.information(self, TEN_UD, 'Đánh dấu ít nhất một hộ (cột "Chọn") để xem trước gộp.')
            return None
        tong = len(ds)
        ds = ds if tat_ca else ds[:XEM_NHIEU_TOI_DA]         # tat_ca: bản để in, đủ các hộ
        du_thao, lan = self.che_do() == 'du_thao', self.lan_in()
        khoa = ('nhieu', tuple(ds), du_thao, lan)
        if not tat_ca:
            self.hang_tai_lieu.dat('ct_gop', im=True)
        ten_ho = {h['ma_ho']: f'{h["thu_tu"]}. {h["ho_ten"]}' for h in self.ho}
        self._ma_xem = None                         # bấm lại một dòng hộ thì xem lại phương án của riêng hộ đó

        def tao(thu_muc):
            return [(in_word.xuat_chi_tiet_docx(self.con, m, Path(thu_muc) / f'{k:03d}_{du_lieu_in.ten_file_ho(self.con, m)}.docx',
                                                du_thao=du_thao, lan=lan), ten_ho.get(m, str(m))) for k, m in enumerate(ds, 1)]
        gioi_han = f' (hiện {len(ds)}/{tong} hộ đầu)' if tong > len(ds) else ''
        self.w_preview.yeu_cau(khoa, tao, f'{len(ds)} hộ gộp ({"dự thảo" if du_thao else "chính thức"}){gioi_han}', ngay)
        return khoa

    def xem_truoc_excel_chi_tiet(self, ngay: bool = False, tat_ca: bool = False):
        """Xem trước bản Excel phương án chi tiết (in_excel_chi_tiet - mỗi hộ một sheet) của các hộ đang đánh dấu, gộp một bản PDF có ô
        nhảy tới hộ (như xem_truoc_nhieu_ho). Tối đa XEM_NHIEU_TOI_DA hộ đầu. Trả khóa đã yêu cầu (None: chưa đánh dấu hộ nào)."""
        from . import in_excel_chi_tiet
        from .nghiep_vu import BoiCanh
        ds = list(self.ds_ho())
        if not ds:
            if not getattr(self, 'im_lang', False):
                QMessageBox.information(self, TEN_UD, 'Đánh dấu ít nhất một hộ (cột "Chọn") để xem trước bản Excel.')
            return None
        tong = len(ds)
        ds = ds if tat_ca else ds[:XEM_NHIEU_TOI_DA]
        du_thao, lan = self.che_do() == 'du_thao', self.lan_in()
        khoa = ('excel_ct', tuple(ds), du_thao, lan)
        self.hang_tai_lieu.dat('ct_excel', im=True)
        ten_ho = {h['ma_ho']: f'{h["thu_tu"]}. {h["ho_ten"]}' for h in self.ho}
        self._ma_xem = None

        def tao(thu_muc):
            bc = BoiCanh.tu(self.con)
            return [(in_excel_chi_tiet.xuat_chi_tiet_xlsx(self.con, [m], Path(thu_muc) / f'X{k:03d}_{du_lieu_in.ten_file_ho(self.con, m)}.xlsx',
                                                          bc, du_thao=du_thao, lan=lan), ten_ho.get(m, str(m)))
                    for k, m in enumerate(ds, 1)]
        gioi_han = f' (hiện {len(ds)}/{tong} hộ đầu)' if tong > len(ds) else ''
        self.w_preview.yeu_cau(khoa, tao, f'Excel {len(ds)} hộ ({"dự thảo" if du_thao else "chính thức"}){gioi_han}', ngay)
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

    def _ap_che_do(self) -> None:
        """DỰ THẢO: mẫu chính có chữ DỰ THẢO, chỉ phương án chi tiết + bảng tổng hợp (không có tờ trình, báo cáo tiếp thu).
        CHÍNH THỨC: mẫu chính (số PA chính thức, không chữ dự thảo), trọn bộ 4 tài liệu. Định dạng Word / Excel / PDF do người dùng chọn, đổi bản không đổi;
        Chính thức in đủ số CCCD; Dự thảo che số CCCD khi bật ô o_che_cccd (1.0.52). Mô tả ở chú thích hai thẻ (MO_TA_CHE_DO)."""
        self._ap_tai_lieu()
        if self.che_do() == 'du_thao':
            for o, v in ((self.o_bth, True), (self.o_tt, False), (self.o_bc, False)):
                o.setChecked(v)
        else:
            for o in (self.o_bth, self.o_tt, self.o_bc):
                o.setChecked(True)
        if not (self.o_ct.isChecked() or self.o_ct_excel.isChecked() or self.o_pdf.isChecked()):
            self.o_ct.setChecked(True)

    def _ap_tai_lieu(self) -> None:
        """Thẻ chế độ, tờ trình + báo cáo tiếp thu chỉ có ở Chính thức, che CCCD chỉ ở Dự thảo (không đổi ô đã chọn khác)."""
        du_thao = self.che_do() == 'du_thao'
        self.hang_che_do.dat(self.che_do(), im=True)
        self._dat_ds_tai_lieu()
        for o in (self.o_tt, self.o_bc):
            o.setEnabled(not du_thao)
            o.setVisible(not du_thao)
            if du_thao:
                o.setChecked(False)
        self.o_che_cccd.setVisible(du_thao and self._rail != 'du_lieu')   # 1.0.52: chỉ bản dự thảo (niêm yết) mới che CCCD

    def _doi_che_cccd(self, bat: bool) -> None:
        import sqlite3
        from .an_toan import che_cccd_niem_yet, dat_che_cccd_niem_yet
        if bool(bat) == che_cccd_niem_yet(self.con):
            return
        try:
            dat_che_cccd_niem_yet(self.con, bool(bat))
        except sqlite3.Error as e:                                       # dự án mở chỉ xem
            self.o_che_cccd.blockSignals(True)
            self.o_che_cccd.setChecked(not bat)
            self.o_che_cccd.blockSignals(False)
            if not getattr(self, 'im_lang', False):
                QMessageBox.warning(self, TEN_UD, chu_loi('Không lưu được tùy chọn che CCCD', e))
            return
        self._lam_moi_xem_truoc()

    # ---- danh sách hộ đánh dấu chọn
    def _theo_pham_vi(self):
        k = self.cb_pham_vi.currentData()
        if not self._mot:
            self.hang_pham_vi.dat(k, im=True)
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
            if self.tai_lieu() != 'ct':                 # tài liệu chung của các hộ đã chọn: lập lại khi ngừng tích
                self._xem_lai()

    def _ve_tu_chon(self):
        i = self.cb_pham_vi.findData('tu_chon')
        if self.cb_pham_vi.currentIndex() != i:
            self.cb_pham_vi.blockSignals(True)
            self.cb_pham_vi.setCurrentIndex(i)
            self.cb_pham_vi.blockSignals(False)
        if not self._mot:
            self.hang_pham_vi.dat('tu_chon', im=True)

    def _dang_hien(self) -> list:
        return [self.bang_ho.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(self.bang_ho.rowCount())
                if not self.bang_ho.isRowHidden(i)]

    def _loc(self, chu: str):
        k = bo_dau(chu).split()
        for i in range(self.bang_ho.rowCount()):
            dong = bo_dau(' '.join(self.bang_ho.item(i, c).text() for c in (1, 2, 4, 5)))
            self.bang_ho.setRowHidden(i, bool(k) and not all(x in dong for x in k))

    def _dem(self):
        ds = self.ds_ho()
        tong = sum((self.tong.get(m, D(0)) for m in ds), D(0))
        tu_lap = sum(1 for m in ds if self.lap.get(m) == 'tu_lap')
        chua = sum(1 for m in ds if self.lap.get(m) == 'chua')
        self._ve_o_ho()
        if hasattr(self, 'b_thuc_hien'):
            self.b_thuc_hien.setText('Xuất file' if self._mot else f'Xuất file\n({len(ds)} hộ)')
            self.b_in.setText('In' if self._mot else f'In\n({len(ds)} hộ)')
        self.lb_chon.setText(f'Đã chọn {len(ds)} hộ, tổng {vn(tong)} đồng' +
                             (f', {tu_lap} hộ tự lập CHƯA SOÁT' if tu_lap else '') +
                             (f', {chua} hộ chưa có phương án' if chua else '') + '.')

    def _bat_tuy_chon(self):
        self.o_gop.setEnabled(self.r_pdf.isChecked())

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
        self._mot = False
        self._danh_dau(quan_ly.ho_cua_dot(self.con, d.id))
        self.hang_pham_vi.dat(f'dot:{d.id}', im=True)
        self.chon_mau(True)
        # thư mục lưu theo đợt: <thư mục hồ sơ dự án>\<Tên đợt - k hộ> (thư mục cũ của đợt được đổi tên theo số hộ khi xuất)
        self.o_thu_muc.setText(str(quan_ly.thu_muc_ho_so(self.con, self.file_du_an) / d.ten_thu_muc))
        self._thu_muc_dot_mac_dinh = self.o_thu_muc.text()
        self.o_chia.setChecked(True)

    def chon_mau(self, co: bool):
        """Chọn / bỏ chọn mọi mẫu in (in đồng loạt), hoặc đánh dấu từng mẫu để in riêng lẻ. Bản Excel nhiều sheet là bản làm việc
        (không thuộc bộ hồ sơ trình): chỉ bỏ chọn, không tự chọn."""
        for o in (self.o_ct, self.o_ct_excel, self.o_bth, self.o_tt, self.o_bc):
            if (o.isEnabled() and o is not self.o_ct_excel) or not co:
                o.setChecked(co)

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

    def _chon_thu_muc(self):
        p = QFileDialog.getExistingDirectory(self, 'Chọn thư mục lưu bản in', self.o_thu_muc.text())
        if p:
            self.o_thu_muc.setText(p)

    def ds_ho(self) -> list:
        """Các hộ sẽ in: Một hộ: hộ đang trỏ; nhiều hộ: các hộ đang đánh dấu chọn, theo thứ tự danh sách."""
        if self._mot:
            r = self.bang_ho.currentRow()
            it = self.bang_ho.item(r, 0) if r >= 0 else None
            return [it.data(Qt.ItemDataRole.UserRole)] if it is not None else []
        return sorted((self.bang_ho.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(self.bang_ho.rowCount())
                       if self.bang_ho.item(i, 0).checkState() == Qt.CheckState.Checked), key=lambda m: self._stt.get(m, 0))

    # ---- sắp xếp bảng hộ, bộ đếm, gấp khung đầu ra, nhớ lựa chọn
    def _sap_xep(self, c: int) -> None:
        """Bấm tiêu đề cột: tăng dần -> giảm dần -> về thứ tự dự án (cột Chọn không sắp xếp). Danh sách xuất vẫn theo thứ tự dự án."""
        if c == 0:
            return
        tang, giam = Qt.SortOrder.AscendingOrder, Qt.SortOrder.DescendingOrder
        dau = self.bang_ho.horizontalHeader()
        if self._cot_sx == c and self._chieu_sx == giam:                     # lần thứ ba: về thứ tự gốc
            self._cot_sx, self._chieu_sx = None, tang
            self.bang_ho.sortItems(1, tang)
            dau.setSortIndicatorShown(False)
            return
        self._chieu_sx = giam if self._cot_sx == c and self._chieu_sx == tang else tang
        self._cot_sx = c
        self.bang_ho.sortItems(c, self._chieu_sx)
        dau.setSortIndicatorShown(True)
        dau.setSortIndicator(c, self._chieu_sx)

    def cap_nhat_bo_dem(self, bang, tk: dict) -> None:
        """Bộ đếm vùng chọn (giao_dien._BoChonVung gọi theo cửa sổ chứa bảng): hiện dưới bảng, không đè lên cột tiền."""
        if bang is self.bang_ho:
            self.lb_bo_dem.dat(tk)

    def _nap_lua_chon(self) -> None:
        """Nhớ lựa chọn lần trước (QSettings; kiểm thử / offscreen không đọc): máy in, định dạng Word / Excel / PDF, gộp PDF, số bản. Không nhớ thư mục: luôn theo file dự án."""
        from .giao_dien import cai_dat_nho
        cd = cai_dat_nho()
        if cd is None:
            return
        try:
            (self.r_excel if cd.value('in/dau_ra', 'pdf') == 'excel' else self.r_pdf).setChecked(True)
            self.o_gop.setChecked(str(cd.value('in/gop', 'true')).lower() in ('true', '1'))
            self.o_so_ban.setValue(int(cd.value('in/so_ban', 1)))
            self.o_ct.setChecked(str(cd.value('in/word', 'true')).lower() in ('true', '1'))
            self.hang_may_in.dat(str(cd.value('in/may_in', '') or ''))
            self.o_ct_excel.setChecked(str(cd.value('in/ct_excel', 'false')).lower() in ('true', '1'))
        except (TypeError, ValueError):                                      # cài đặt cũ / hỏng: dùng mặc định
            pass

    def _luu_lua_chon(self, thu_muc: Path) -> None:
        from .giao_dien import cai_dat_nho
        cd = cai_dat_nho()
        if cd is None:
            return
        cd.setValue('in/dau_ra', 'excel' if self.r_excel.isChecked() else 'pdf')
        cd.setValue('in/gop', self.o_gop.isChecked())
        cd.setValue('in/so_ban', self.o_so_ban.value())
        cd.setValue('in/word', self.o_ct.isChecked())
        cd.setValue('in/may_in', self.hang_may_in.gia_tri() or '')
        cd.setValue('in/ct_excel', self.o_ct_excel.isChecked())

    def thuc_hien(self, xac_nhan: bool = True, chi: str | None = None):
        from . import in_an
        from . import van_ban_trinh as vb
        ds = self.ds_ho()
        nhieu = not self.mot_ho()                            # thẻ Một hộ: chỉ phương án chi tiết
        chi_pdf = self.o_pdf.isChecked() and not self.o_ct.isChecked() and not self.chi_tiet_theo_word     # chỉ tích PDF: dựng từ bản Word rồi không để lại file Word
        chon = dict(chi_tiet=self.o_ct.isChecked() or chi_pdf, chi_tiet_excel=self.o_ct_excel.isChecked(), bang_tong_hop=self.o_bth.isChecked() and nhieu,
                    bang_dieu_chinh=self.o_bth_dc.isChecked() and self.co_dieu_chinh and nhieu,
                    to_trinh=self.o_tt.isChecked() and self.o_tt.isEnabled() and nhieu,
                    bao_cao_y_kien=self.o_bc.isChecked() and self.o_bc.isEnabled() and nhieu)
        if chi is not None:                                  # in qua Word / Excel: đúng tài liệu đang xem
            chi_pdf = False
            chon = dict(chi_tiet=chi in ('ct', 'ct_gop', 'ct_excel'), chi_tiet_excel=False, bang_tong_hop=chi == 'bth', bang_dieu_chinh=chi == 'dc',
                        to_trinh=chi == 'tt', bao_cao_y_kien=chi == 'bc')
        if not any(chon.values()):
            QMessageBox.information(self, TEN_UD, 'Chọn ít nhất một loại bản in.')
            return None
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Chưa chọn hộ nào để in: đánh dấu cột "Chọn" trong danh sách hộ.')
            return None
        if chi is None and not self._hoi_tu_lap(ds, xac_nhan):   # in_ra_may đã hỏi
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
            tien.setLabelText(f'Microsoft Excel / Word đang {viec}: xong {i}/{n} file…' +
                              ('\n(Đang dừng sau file hiện tại…)' if tien.wasCanceled() else ''))
            QApplication.processEvents()
            return tien.wasCanceled()
        try:
            with con_tro_cho():
                # PA CHI TIET\ phương án chi tiết; PA TONG\ bảng tổng hợp, tờ trình / văn bản trình, phương án tổng (số theo đợt)
                kq = vb.xuat_bo_ho_so(self.con, ds, thu_muc, dot=dot, pdf=self.r_pdf.isChecked(), in_may=in_may,
                                      lan=self.lan_in(),
                                      du_thao=self.che_do() == 'du_thao', so_ban=so_ban, chia_thu_muc=self.o_chia.isChecked() and nhieu, bao_tien_do=bao_tao, bao_excel=bao_excel,
                                      **chon)
                if chi_pdf and self.r_pdf.isChecked():
                    for f in list(kq['word']):
                        if f.name.startswith('PA_') and f.with_suffix('.pdf').exists():
                            f.unlink()
                            kq['word'].remove(f)
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
        self._luu_lua_chon(thu_muc)
        dung = any(x.startswith(('DA_DUNG', 'LOI_TREO')) for x in kq['loi'])
        tep = [f'{len(kq["word"])} file Word'] if kq.get('word') else []
        tep += [f'{len(kq["excel"])} file Excel'] if kq['excel'] else []
        tb = f'Đã tạo {", ".join(tep) or "0 file"}' + (f', {len(kq["pdf"])} file PDF' if kq['pdf'] else '') + \
             (f' (gộp: {kq["gop"].name})' if kq.get('gop') else '') + \
             (' và gửi tới máy in' if in_may and not kq['loi'] else '') + f'.\nThư mục: {thu_muc}'
        if kq.get('du_phong'):                          # Word treo / không có Word: hộ đó dựng PDF / in từ bản Excel lập tạm
            tb += f'\n\n{len(kq["du_phong"])} hộ Microsoft Word không xuất được: đã ' + \
                  ('in bản Excel thay.' if in_may else 'dựng PDF gần đúng từ bản Excel.')
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

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
                               QFileDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QRadioButton, QSpinBox,
                               QStyledItemDelegate, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from . import lap_pa, nghiep_vu
from .lap_pa import NHOM_TIM, BoSoan, DanhMuc, LoiNhap, bo_dau
# in_an (kéo theo openpyxl ~0,2 giây) chỉ nạp trong hộp In / Xuất: mở dự án, cửa sổ lập phương án không phải chờ
from .nghiep_vu import MA_TDC, NGUON_TAY, NGUON_TD, TEN_MUC
from .tien import D, lam_tron, so_vn, vn
from .giao_dien import con_tro_cho
from .thong_bao import TEN_UD, chu_loi

XAM, VANG, CAM = QColor('#F4F6F8'), QColor('#FFF6D6'), QColor('#FDEBDD')
COT_SO = {'dien_tich', 'gia_bang_gia', 'he_so_k', 'ty_le', 'thanh_tien', 'so_luong', 'don_gia'}

COT_GD = {
    1: [('thua', 'Thửa', 130), ('loai_dat', 'Loại đất', 70), ('dien_tich', 'DT thu hồi (m²)', 100), ('vi_tri', 'Vị trí', 260),
        ('gia_bang_gia', 'Giá đất (đ/m²)', 110), ('he_so_k', 'Hệ số K', 65), ('ty_le', 'Tỷ lệ %', 60),
        ('thanh_tien', 'Thành tiền (đ)', 120), ('ghi_chu', 'Ghi chú', 220)],
}
for _m in (2, 3):
    COT_GD[_m] = [('ma', 'Mã', 60), ('ten', {2: 'Tên nhà, công trình, tài sản', 3: 'Tên cây trồng'}[_m], 340),
                  ('dvt', 'ĐVT', 70), ('so_luong', 'Số lượng', 85), ('don_gia', 'Đơn giá (đ)', 110), ('ty_le', 'Tỷ lệ %', 60),
                  ('thanh_tien', 'Thành tiền (đ)', 120), ('nguon', 'Nguồn giá', 110), ('quy_cach', 'Quy cách', 170),
                  ('ghi_chu', 'Ghi chú (quy định, cách tính)', 240), ('can_cu_gia', 'Căn cứ giá', 200)]
COT_GD[4] = [('ma', 'Mã', 60), ('ten', 'Chính sách hỗ trợ', 300), ('cach_tinh', 'Cách tính', 280), ('dvt', 'ĐVT', 70),
             ('so_luong', 'Số lượng', 80), ('don_gia', 'Đơn giá (đ)', 110), ('ty_le', 'Tỷ lệ %', 60),
             ('thanh_tien', 'Thành tiền (đ)', 120), ('ghi_chu', 'Ghi chú (căn cứ)', 280)]
TEN_TAB = {0: 'Thông tin hộ, thửa đất', 1: '1. Đất', 2: '2. Nhà, công trình', 3: '3. Cây trồng', 4: '4. Hỗ trợ'}


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
        ds_nhom = [2, 3, 4, 9] if tuong_duong else ([nhom, 9] if nhom in (2, 3) else [nhom])
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
        self.o_tim.textChanged.connect(self.tim)
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
        cb = QComboBox(parent)
        cb.setEditable(self.sua_tay)
        cb.setMaxVisibleItems(18)
        for nhan, gt in self.ds_cua_dong(index.row()):
            cb.addItem(nhan, gt)
        if self.sua_tay:
            cb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            g = QCompleter(cb.model(), cb)
            g.setFilterMode(Qt.MatchFlag.MatchContains)
            g.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            g.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            cb.setCompleter(g)
        cb.view().setMinimumWidth(min(max(cb.view().sizeHintForColumn(0) + 30, 260), 980))
        from .giao_dien import mo_danh_sach
        mo_danh_sach(cb)                              # mở ô là hiện luôn danh sách
        return cb

    def setEditorData(self, cb, index):
        v = str(index.data() or '')
        i = cb.findText(v)
        cb.setCurrentIndex(i)
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
        r = option.rect
        o.setGeometry(r.x(), r.y(), r.width(), max(r.height(), 64))

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


COT_CHU_DAI = {'ten', 'quy_cach', 'can_cu_gia', 'ghi_chu', 'cach_tinh'}
COT_CONG_THUC = {'so_luong', 'dien_tich'}
KIEU_SL = [('sl', 'Số lượng'), ('dk', 'Đường kính (cm)'), ('cv', 'Chu vi (cm)')]


# ---------------------------------------------------------------- bảng một mục
def ds_chon_nhanh(dm: DanhMuc, muc: int) -> list:
    """Danh sách chọn nhanh của mục 2-4 [(nhãn, mục danh mục)]. Chỉ phụ thuộc danh mục (đối tượng DanhMuc dùng chung giữa
    các lần mở cửa sổ): dựng một lần rồi dùng lại; cửa sổ chính dựng sẵn lúc rảnh sau khi mở dự án (lam_san)."""
    from .cay_trong import BangCayDK, mo_ta_chu_vi
    nho = dm.__dict__.setdefault('_ds_chon', {})
    if muc in nho:
        return nho[muc]
    ds = []
    for m in dm.muc[muc]:
        if muc == 4 and m.ma in (MA_TDC + ('HT21', 'HT22', 'HT25', 'HT26')):
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
    if muc in (2, 3):
        # quy ước tương đương / đơn giá thẩm định của dự án (tài sản đặc biệt): đứng đầu danh sách để chọn nhanh
        qu = []
        for m in dm.muc[9]:
            if m.don_gia is None:
                continue
            nhan = 'Thẩm định' if bo_dau(m.phan_loai).startswith('don gia tham dinh') else 'Quy ước'
            qu.append((f'[{nhan}] {m.ten}  ·  {vn(m.don_gia)} đ/{m.dvt}'
                       + (f'  (theo {m.phan_loai})' if nhan == 'Quy ước' and m.phan_loai else ''), m))
        ds = qu + ds
    nho[muc] = ds
    return ds


def lam_san(dm: DanhMuc) -> None:
    for m in (2, 3, 4):
        ds_chon_nhanh(dm, m)


class BangMuc(QWidget):
    """Một thẻ mục: hàng nhập nhanh (chọn / gõ tên → số lượng → Thêm), bảng dòng phương án, nút Trở lại / Tiếp theo."""

    def __init__(self, man, muc: int):
        super().__init__()
        self.man, self.muc = man, muc
        self.cot = COT_GD[muc]
        self.bang = QTableWidget(0, len(self.cot))
        self.bang.setHorizontalHeaderLabels([c[1] for c in self.cot])
        for i, c in enumerate(self.cot):
            self.bang.setColumnWidth(i, c[2])
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
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
            from .loai_dat import ds_co_gia
            u = ChonXoXuong(ds_co_gia(man.bo.con), self.bang)
            self._uy_quyen.append(u)
            self.bang.setItemDelegateForColumn(khoa.index('loai_dat'), u)
        # ---- hàng nhập nhanh
        nhap = QHBoxLayout()
        nhap.setSpacing(8)
        self.nut = {}
        if muc == 1:
            self.cb_thua = QComboBox()
            self.cb_thua.setMinimumWidth(420)
            nhan = QLabel('Thửa:')
            nhan.setProperty('vai', 'nhan')
            nhap.addWidget(nhan)
            nhap.addWidget(self.cb_thua, 1)
            b = QPushButton('Thêm thửa vào mục 1')
            b.clicked.connect(lambda: man.them_thua(self.cb_thua.currentData()) if self.cb_thua.count() else man.them_thua())
            nhap.addWidget(b)
            self.nut['Thêm thửa…'] = b
        else:
            from .giao_dien import OTimChon
            # một hàng nhập gọn: tên (▼ danh sách) → [kiểu số đo] → số lượng → tỷ lệ → ghi chú → Thêm (Tab đi tiếp, Enter thêm)
            self.o_chon = OTimChon({2: 'Tên nhà, công trình (gõ không dấu, ▼ xem danh sách)',
                                    3: 'Tên cây trồng (gõ không dấu, vd: xoai 11-15, sao den)',
                                    4: 'Chính sách hỗ trợ (gõ không dấu, vd: on dinh, dao tao, thue nha)'}[muc])
            self.o_chon.khi_chon = lambda m: self._da_chon(m)
            self.o_chon.o.setProperty('nhap', '1')
            self.o_chon.nut.setMinimumSize(34, 34)
            self.o_sl = QLineEdit()
            self.o_sl.setPlaceholderText('Số lượng (=4,2*5,7)')
            self.o_sl.setMinimumWidth(150)
            self.o_sl.setMaximumWidth(200)
            self.o_sl.returnPressed.connect(lambda: man.them_nhanh(muc))
            self.o_tl = QLineEdit()
            self.o_tl.setPlaceholderText('Tỷ lệ %')
            self.o_tl.setMaximumWidth(80)
            self.o_tl.setToolTip('Tỷ lệ bồi thường, hỗ trợ (%) - để trống = 100%')
            self.o_tl.returnPressed.connect(lambda: man.them_nhanh(muc))
            self.nhan_tl = QLabel('')                        # (tỷ lệ ghi ngay trong ô)
            self.nhan_tl.setVisible(False)
            # ghi chú của dòng: quy định pháp luật, cách tính (in ở cột Ghi chú)
            self.o_gc = QLineEdit()
            self.o_gc.setPlaceholderText('Ghi chú: quy định, cách tính…')
            self.o_gc.setToolTip('Quy định pháp luật áp dụng, cách tính… (in ở cột Ghi chú của phương án)')
            self.o_gc.returnPressed.connect(lambda: man.them_nhanh(muc))
            nhap.addWidget(self.o_chon, 5)
            if muc == 3:
                self.cb_kieu = QComboBox()
                for k, t in KIEU_SL:
                    self.cb_kieu.addItem(t, k)
                self.cb_kieu.setToolTip('Nhập số cây, hoặc các số đo đường kính / chu vi thân (cm) cách nhau dấu phẩy, nhiều cây '
                                        'cùng số đo ghi 52x3: phần mềm tự xếp vào đúng quy cách đơn giá')
                self.cb_kieu.currentIndexChanged.connect(lambda *_: self._doi_kieu())
                self.cb_kieu.setProperty('nhap', '1')
                nhap.addWidget(self.cb_kieu)
            for o in (self.o_sl, self.o_tl, self.o_gc):
                o.setProperty('nhap', '1')
            nhap.addWidget(self.o_sl, 2)
            nhap.addWidget(self.o_tl, 1)
            nhap.addWidget(self.o_gc, 3)
            b = QPushButton('Thêm vào bảng')
            b.setMinimumHeight(34)
            b.clicked.connect(lambda: man.them_nhanh(muc))
            nhap.addWidget(b)
            self.nut['Thêm vào bảng'] = b
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
            nut.addWidget(b)
            self.nut[ten] = b
        nut.addStretch(1)
        self.lb_tong = QLabel('')
        self.lb_tong.setStyleSheet('QLabel { font-weight: bold; color: #1F4E79; }')
        nut.addWidget(self.lb_tong)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(10, 10, 10, 8)
        lo.setSpacing(8)
        if muc == 4:
            # một hàng: thông tin hộ dùng tính hỗ trợ + tình trạng tái định cư
            h = QHBoxLayout()
            h.setSpacing(8)
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
            lo.addLayout(h)
        khung_nhap = QWidget()                       # hàng nhập trong một khung nền nhạt, tách khỏi bảng
        khung_nhap.setObjectName('khung_nhap')
        khung_nhap.setStyleSheet('QWidget#khung_nhap { background: #F4F8FC; border: 1px solid #D5E1EC; border-radius: 8px; }')
        nhap.setContentsMargins(10, 8, 10, 8)
        khung_nhap.setLayout(nhap)
        lo.addWidget(khung_nhap)
        if muc == 1:
            self.cb_thua.setProperty('nhap', '1')
        if muc == 4:
            lo.addWidget(self._the_cach_tinh())
        lo.addLayout(nut)
        lo.addWidget(self.bang, 1)
        lo.addLayout(man.hang_dieu_huong(muc))
        from .giao_dien import nhap_bang_phim
        nhap_bang_phim(self.bang)                    # dòng cao; Tab / Enter đi giữa các ô, không cần chuột
        # ô xổ có chữ dài (câu tái định cư, mô tả thửa): không bắt cửa sổ rộng theo chữ dài nhất
        for cb in self.findChildren(QComboBox):
            cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            cb.setMinimumContentsLength(14)
        if muc == 4:
            man.o_dt_nn.setMinimumWidth(130)
        if muc != 1:
            # thứ tự Tab ở hàng nhập nhanh: tên → (kiểu số đo) → số lượng → tỷ lệ → ghi chú → Thêm vào bảng (Enter: thêm)
            chuoi = [self.o_chon.o] + ([self.cb_kieu] if muc == 3 else []) + [self.o_sl, self.o_tl, self.o_gc,
                                                                               self.nut['Thêm vào bảng']]
            for a, b in zip(chuoi, chuoi[1:]):
                QWidget.setTabOrder(a, b)
            self.o_chon.nut.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._dang_ve = False

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
                th, tl = lap_pa.doc_so(self.o_thang_od.text(), 'Số tháng'), lap_pa.doc_ty_le(self.o_tl_od.text())
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
        self.o_chon.dat_muc(ds_chon_nhanh(dm, self.muc))

    def _da_chon(self, m):
        from . import chinh_sach as cs
        if self.muc == 3:
            nhom = isinstance(m, tuple) and m[0] == 'nhom'
            if nhom and self.cb_kieu.currentData() == 'sl':
                self.cb_kieu.setCurrentIndex(1)
            elif not nhom and m is not None and self.cb_kieu.currentData() != 'sl':
                from .cay_trong import khoang_duong_kinh
                if khoang_duong_kinh(m.ten) is None:
                    self.cb_kieu.setCurrentIndex(0)
        if self.muc == 4:
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
                return
            if k == 'dt':
                self.nap_dao_tao(m.ma)
                return
            if k == 'tn':
                cb, them, _ = cs.gia_thue_nha(bo.bc, m.ma)
                self.o_co_ban.setText(vn(cb))
                self.o_them.setText(vn(them))
                self.o_thang_tn.setText(so_vn(bo.bc.so_ts('TULO_THANG') or 6) if m.ma in ('HT17', 'HT18') else '')
                self.xem_cach_tinh()
                self.o_thang_tn.setFocus()
                return
            if m is not None and not isinstance(m, tuple) and not self.o_sl.text().strip():
                from .nghiep_vu import goi_y_khoan
                g = goi_y_khoan(bo.pa, bo.bc, m.ma)
                if g.so_luong is not None:
                    self.o_sl.setText(so_vn(g.so_luong))
        self.o_sl.setFocus()
        self.o_sl.selectAll()

    def _doi_kieu(self):
        k = self.cb_kieu.currentData()
        self.o_sl.setPlaceholderText({'sl': 'Số lượng (=4,2*5,7)', 'dk': 'Đường kính: 15, 18x2, 22',
                                      'cv': 'Chu vi: 45, 52x3, 60'}[k])
        self.o_sl.setMaximumWidth(220 if k == 'sl' else 280)

    def xoa_nhap(self):
        if self.muc != 1:
            self.o_chon.xoa()
            self.o_sl.clear()
            self.o_tl.clear()
            self.o_gc.clear()
            if self.muc == 4:
                self._dat_loai_cs('')
            self.o_chon.o.setFocus()

    def dong_chon(self) -> int:
        return self.bang.currentRow()

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
        self.bang.resizeRowsToContents()
        if chon is not None and 0 <= chon < n:
            self.bang.setCurrentCell(chon, 1)

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
            self.bang.resizeRowToContents(r)

    def _bao_cong_thuc(self, r: int, c: int):
        """Chọn ô số lượng / diện tích: dòng thông báo cho biết số / công thức đã nhập ra số đó."""
        if self._dang_ve or not (0 <= c < len(self.cot)) or self.cot[c][0] not in COT_CONG_THUC:
            return
        it = self.bang.item(r, c)
        if it is None:
            return
        ct = it.data(Qt.ItemDataRole.UserRole)
        ten = self.cot[c][1]
        self.man.thong_bao(f'Dòng {self.muc}.{r + 1} – {ten}: {ct} = {it.text()}' if ct else
                           f'Dòng {self.muc}.{r + 1} – {ten}: {it.text()} (gõ số trực tiếp)')

    def _doi_o(self, r: int, c: int):
        if self._dang_ve:
            return
        self.man.sua_o(self.muc, r, self.cot[c][0], self.bang.item(r, c).text())


# ---------------------------------------------------------------- màn hình lập phương án hộ
class CuaSoLapPA(QDialog):
    """Hồ sơ và phương án một hộ trong một cửa sổ: thẻ 0 thông tin hộ, thửa đất → 1 đất → 2 nhà, công trình → 3 cây trồng →
    4 hỗ trợ (Tiếp theo / Trở lại, Lưu ở thẻ cuối)."""

    def __init__(self, con, ma_ho: int, parent=None, danh_muc: DanhMuc | None = None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.resize(1360, 840)
        self.bo = BoSoan(con, ma_ho, danh_muc)
        self.da_luu = False
        self.thay_doi_csdl = False
        # ---- dòng chọn hộ
        self.cb_ho = QComboBox()
        self.cb_ho.setMinimumWidth(320)
        self.cb_ho.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cb_ho.setMinimumContentsLength(24)
        self.cb_ho.setEditable(True)
        self.cb_ho.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._nap_ds_ho()
        self.cb_ho.activated.connect(self._chon_ho_tu_hop)
        self.b_truoc = QPushButton('◀ Hộ trước')
        self.b_sau = QPushButton('Hộ sau ▶')
        self.b_truoc.clicked.connect(lambda: self.sang_ho(-1))
        self.b_sau.clicked.connect(lambda: self.sang_ho(1))
        self.b_goi_y = QPushButton('Gợi ý hỗ trợ…')
        self.b_goi_y.clicked.connect(lambda: self.goi_y())
        self.b_luu = QPushButton('Lưu (Ctrl+S)')
        self.b_luu.clicked.connect(lambda: self.luu())
        self.b_bo = QPushButton('Bỏ thay đổi')
        self.b_bo.clicked.connect(lambda: self.bo_thay_doi())
        self.b_in = QPushButton('In / Xuất…')
        self.b_in.clicked.connect(lambda: self.in_xuat())
        self.b_dong = QPushButton('Đóng')
        self.b_dong.clicked.connect(lambda: self.close())
        h1 = QHBoxLayout()
        h1.setSpacing(8)
        nhan = QLabel('Hộ:')
        nhan.setProperty('vai', 'nhan')
        h1.addWidget(nhan)
        h1.addWidget(self.cb_ho, 1)
        for b in (self.b_truoc, self.b_sau, self.b_goi_y, self.b_luu, self.b_bo, self.b_in, self.b_dong):
            h1.addWidget(b)
        # ---- thông tin hộ dùng cho chính sách hỗ trợ
        self.o_nk = QSpinBox()
        self.o_nk.setRange(0, 200)
        self.o_nk.setSpecialValueText('chưa nhập')
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
        self.lb_tl = QLabel('')                     # các ô này đặt ở thẻ 4. Hỗ trợ (BangMuc)
        # ---- thẻ 0 hồ sơ hộ + 4 mục
        from .man_hinh_ho_so import KhungHoSo
        self.tab = QTabWidget()
        the0 = QWidget()
        lo0 = QVBoxLayout(the0)
        lo0.setContentsMargins(10, 10, 10, 8)
        self.ho_so = KhungHoSo(con, ma_ho, the0, an=('trang_thai', 'tai_dinh_cu'), khi_thay_doi_csdl=self._sau_ghi_ho_so,
                               khi_xoa_ho=self._sau_xoa_ho)
        lo0.addWidget(self.ho_so, 1)
        lo0.addLayout(self.hang_dieu_huong(0))
        self.tab.addTab(the0, TEN_TAB[0])
        self.bang = {}
        for m in (1, 2, 3, 4):
            self.bang[m] = BangMuc(self, m)
            self.tab.addTab(self.bang[m], TEN_TAB[m])
        # ---- tổng + cảnh báo
        self.lb_tong = QLabel('')
        self.lb_tong.setObjectName('tong_pa')
        self.lb_tong.setStyleSheet('QLabel#tong_pa { font-size: 14px; padding: 8px 10px; background: #EAF2FB; '
                                   'border: 1px solid #D3E2F1; border-radius: 6px; }')
        self.lb_tong.setWordWrap(True)
        self.lb_tb = QLabel('')
        self.lb_tb.setWordWrap(True)
        self.lb_tb.setStyleSheet('QLabel { color: #1F4E78; padding: 2px 6px; }')
        self.o_cb = QPlainTextEdit()
        self.o_cb.setReadOnly(True)
        from .giao_dien import kieu_trang_thai
        self.o_cb.setStyleSheet(kieu_trang_thai('canh_bao', 'QPlainTextEdit', dam=False))   # màu "cần xem lại" dùng chung
        self.o_cb.setVisible(False)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(14, 12, 14, 12)
        lo.setSpacing(8)
        lo.addLayout(h1)
        lo.addWidget(self.tab, 1)
        lo.addWidget(self.lb_tb)
        lo.addWidget(self.lb_tong)
        lo.addWidget(self.o_cb)
        self._phim = []
        for phim, ham in ((QKeySequence(QKeySequence.StandardKey.Save), lambda: self.luu()),
                          (QKeySequence('Ctrl+PgDown'), lambda: self.sang_ho(1)),
                          (QKeySequence('Ctrl+PgUp'), lambda: self.sang_ho(-1))):
            sc = QShortcut(phim, self)
            sc.activated.connect(ham)
            self._phim.append(sc)
        self._dang_nap = False
        for m in (2, 3, 4):
            self.bang[m].nap_danh_sach()
        self.nap_ho()
        self.tab.setCurrentIndex(1 if self.bo.pa.dat or any(self.bo.pa.khoan[m] for m in (2, 3, 4)) else 0)

    def _nap_ds_ho(self):
        self.cb_ho.blockSignals(True)
        self.cb_ho.clear()
        for ma, tt, ten in self.bo.danh_sach_ho():
            self.cb_ho.addItem(f'{tt}. {ten}  (mã {ma})', ma)
        self.cb_ho.blockSignals(False)

    def hang_dieu_huong(self, the: int) -> QHBoxLayout:
        """Nút ◀ Trở lại / Tiếp theo ▶ dưới mỗi thẻ (thẻ cuối: Lưu phương án)."""
        h = QHBoxLayout()
        h.setSpacing(8)
        if the > 0:
            b = QPushButton(f'◀ Trở lại: {TEN_TAB[the - 1]}')
            b.clicked.connect(lambda: self.sang_the(the - 1))
            h.addWidget(b)
        h.addStretch(1)
        if the < 4:
            b = QPushButton(f'Tiếp theo: {TEN_TAB[the + 1]} ▶')
            b.clicked.connect(lambda: self.sang_the(the + 1))
        else:
            b = QPushButton('Lưu phương án hộ')
            b.clicked.connect(lambda: self.luu())
        h.addWidget(b)
        return h

    def sang_the(self, the: int) -> bool:
        """Chuyển thẻ; rời thẻ hồ sơ hộ có sửa đổi thì lưu hồ sơ trước (để thửa mới dùng được ở mục 1)."""
        if self.tab.currentIndex() == 0 and the != 0 and self.ho_so.co_thay_doi() and not self.ho_so.luu():
            return False
        self.tab.setCurrentIndex(the)
        if the in (2, 3, 4):
            self.bang[the].o_chon.o.setFocus()
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
            for m in (1, 2, 3, 4):
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
        for m in (1, 2, 3, 4):
            self.bang[m].lb_tong.setText(f'Cộng mục {m}: {vn(kq.muc[m])} đ')
            self.tab.setTabText(m, f'{TEN_TAB[m]} ({len(self.bo.ds(m))})')
        self.tab.setTabText(0, f'{TEN_TAB[0]} ({self.ho_so.bang.rowCount()} thửa)')
        cach = '&nbsp;&nbsp;&nbsp;·&nbsp;&nbsp;&nbsp;'
        self.lb_tong.setText(
            cach.join([f'{m}. {vn(kq.muc[m])}' for m in (1, 2, 3, 4)] + [f'5. Thưởng {vn(kq.muc[5])}']) +
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
        self.b_luu.setEnabled(thay or self.ho_so.co_thay_doi())
        self.b_bo.setEnabled(thay)
        h = self.bo.pa.ho
        self.setWindowTitle(f'{"* " if thay else ""}Hồ sơ, phương án – hộ {h.ma_ho}: {h.ho_ten}  ·  {h.trang_thai}')

    def thong_bao(self, tb: str):
        self.lb_tb.setText(tb or '')

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
        try:
            tb = self.bo.sua_dat(r, cot, text) if muc == 1 else self.bo.sua_khoan(muc, r, cot, text)
            self.thong_bao(tb)
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
        self.bang[muc]._ve_dong(r)
        self.cap_nhat()

    def ds_thua_dong(self, r: int) -> list:
        return [(mo_ta, mt) for mt, mo_ta, _ in self.bo.thua_cua_ho()]

    def doi_thua_dong(self, r: int, ma_thua):
        self.sua_o(1, r, 'thua', ma_thua)

    def ds_vi_tri_dong(self, r: int) -> list:
        return [(nhan, ('nq28', x)) for nhan, x, _ in self.bo.ds_vi_tri_nq28(r)] if 0 <= r < len(self.bo.pa.dat) else []

    def doi_vi_tri_dong(self, r: int, gt):
        if isinstance(gt, tuple) and gt[0] == 'nq28':
            try:
                self.thong_bao(self.bo.chon_vi_tri_nq28(r, gt[1]))
            except LoiNhap as e:
                QMessageBox.warning(self, TEN_UD, str(e))
            self.bang[1]._ve_dong(r)
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
    def _sau_khi_them(self, muc, i, tb=''):
        self.tab.setCurrentIndex(muc)
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
        bm = self.bang[muc]
        m = bm.o_chon.chon if m is None else m
        ten = bm.o_chon.text().strip()
        sl = bm.o_sl.text().strip() if so_luong is None else str(so_luong)
        tl = bm.o_tl.text().strip() if ty_le is None else str(ty_le)
        kieu = kieu or (bm.cb_kieu.currentData() if muc == 3 else 'sl')
        gc = bm.o_gc.text().strip()
        tu_do = m is None or (isinstance(m, tuple) and m[0] == 'ten')     # tên gõ tự do / chính sách không có trong đơn giá
        try:
            ty = lap_pa.doc_ty_le(tl) if tl else None
            if kieu in ('dk', 'cv'):
                return self._them_theo_do(m, sl, kieu, ty, gc)
            if muc == 4 and not tu_do and bm.cs_loai in ('od', 'dt', 'tn'):
                return self._them_chinh_sach(m, bm, so_luong, gc)
            if isinstance(m, tuple) and m[0] == 'nhom':
                raise LoiNhap('Loại cây này nhập theo số đo: chọn "Đường kính (cm)" hoặc "Chu vi (cm)" rồi gõ các số đo.')
            if isinstance(m, tuple):
                ten = m[1]
            if tu_do and not ten:
                raise LoiNhap('Chọn trong danh sách hoặc gõ tên hạng mục.')
            if sl:
                lap_pa.doc_so_luong(sl, m.dvt if not tu_do else '')
            if tu_do:
                i = self.bo.them_hang_muc_khac(muc, ten)
                tb = f'"{ten}" không có trong đơn giá: gõ đơn giá ở cột Đơn giá; ghi quy định, cách tính ở cột Ghi chú.'
            else:
                i, tb = self.bo.them_tu_danh_muc(muc, m)
            if sl:
                self.bo.sua_khoan(muc, i, 'so_luong', sl)
            if ty is not None:
                self.bo.pa.khoan[muc][i].ty_le = ty
            if gc:
                self.bo.pa.khoan[muc][i].ghi_chu = gc
        except LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
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

    def _them_theo_do(self, m, text: str, kieu: str, ty, gc: str = ''):
        from . import cay_trong as ct
        bang = ct.BangCayDK(self.bo.dm.muc[3])
        if isinstance(m, tuple):
            ten_loai = m[1]
        elif m is not None and ct.khoang_duong_kinh(m.ten) is not None:
            ten_loai = ct.ten_loai_dk(m.ten)
        else:
            raise LoiNhap('Chọn loại cây có quy cách theo đường kính thân (tên loại không có mã, ví dụ "Sao đen"), chọn kiểu Đường kính / Chu vi.')
        try:
            ds = ct.doc_ds_chu_vi(text)
        except ValueError as e:
            raise LoiNhap(str(e).replace('chu vi (cm)', 'số đo (cm)')) from None
        if not ds:
            raise LoiNhap('Gõ các số đo (cm), cách nhau dấu phẩy; nhiều cây cùng số đo ghi 52x3.')
        la_dk = kieu == 'dk'
        nhom, loi = ct.gom_theo_kich_thuoc(bang, ten_loai, ds, la_dk)
        if not nhom:
            raise LoiNhap(f'Số đo không thuộc quy cách nào của {ten_loai}: ' + ', '.join(so_vn(x) for x in loi))
        moi = []
        for mm, so, a, z in nhom:
            i, _ = self.bo.them_tu_danh_muc(3, mm)
            self.bo.sua_khoan(3, i, 'so_luong', str(so))
            self.bo.sua_khoan(3, i, 'quy_cach', ct.mo_ta_do(a, z, la_dk))
            if ty is not None:
                self.bo.pa.khoan[3][i].ty_le = ty
            if gc:
                self.bo.pa.khoan[3][i].ghi_chu = gc
            moi.append(i)
        tb = f'Đã thêm {sum(x[1] for x in nhom)} cây vào {len(nhom)} quy cách.'
        if loi:
            tb += f' Không khớp quy cách nào (chưa thêm): {", ".join(so_vn(x) for x in loi)} cm.'
        self._sau_khi_them(3, moi[-1], tb)
        self.bang[3].xoa_nhap()
        return moi[-1]

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
            QMessageBox.information(self, TEN_UD, f'Chọn một dòng ở mục {muc} để {ten_viec}.')
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

    def xoa_dong(self, muc: int, i: int | None = None):
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
        self.tab.setCurrentIndex(4)
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
            e.accept()
            super().closeEvent(e)
        else:
            e.ignore()


# ---------------------------------------------------------------- thông tin dự án
class HopDuAn(QDialog):
    def __init__(self, con, parent=None):
        super().__init__(parent)
        self.con = con
        self.setWindowTitle('Thông tin dự án')
        self.resize(1080, 420)
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
            else:
                w = QLineEdit(gt[k])
                w.setCursorPosition(0)
            self.o[k] = w
            (don_vi if k in csdl.TRUONG_DON_VI else du_an).append((ten + ':', w))
        form = QVBoxLayout()
        form.addWidget(can_giua(the_form('Thông tin dự án', du_an, 110), the_form('Đơn vị lập, người ký', don_vi, 160)))
        ghi = QLabel('Cấp và tên xã, phường dùng trong mô tả thửa trên bản in và để chọn mức hỗ trợ theo địa bàn xã / phường.')
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

    def gia_tri(self) -> dict:
        return {k: (w.currentText() if isinstance(w, QComboBox) else w.text()) for k, w in self.o.items()}

    def accept(self):
        try:
            lap_pa.luu_du_an(self.con, self.gia_tri())
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

    def __init__(self, con, parent=None, ma_ho_chon: list | None = None, file_du_an=None):
        from . import in_an
        super().__init__(parent)
        self.con = con
        self.ket_qua = None
        self.setWindowTitle('In / xuất phương án')
        self.resize(1000, 880)
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
            self.cb_pham_vi.addItem(f'Hộ đang chọn: {ten} (mã {self.ma_ho_chon[0]})' if len(self.ma_ho_chon) == 1
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
        self.o_tim.textChanged.connect(self._loc)
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
        # văn bản trình của đợt (0.9.16): tờ trình / văn bản trình, phương án tổng - số, ngày lấy theo đợt trình đã chọn
        self.o_tt = QCheckBox('Tờ trình / văn bản trình (mẫu Word / Excel - sửa ở "Đợt trình…")')
        self.o_pat = QCheckBox('Phương án tổng (mẫu Word)')
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
        form.addRow('Đợt trình:', self.cb_dot)
        form.addRow('Hộ cần in:', self.cb_pham_vi)
        form.addRow('', hang_chon)
        form.addRow('', self.bang_ho)
        form.addRow('', self.lb_chon)
        form.addRow('Bản in:', self.o_ct)
        form.addRow('', self.o_bth)
        form.addRow('', self.o_tt)
        form.addRow('', self.o_pat)
        form.addRow('', hang_mau_in)
        form.addRow('Đầu ra:', self.r_excel)
        form.addRow('', self.r_pdf)
        form.addRow('', self.o_gop)
        form.addRow('', hang_in)
        form.addRow('Lưu vào thư mục:', hang)
        form.addRow('', self.o_chia)
        form.addRow('', self.o_mo)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText('Thực hiện')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Đóng')
        nut.accepted.connect(lambda: self.thuc_hien())
        nut.rejected.connect(self.reject)
        self.lb = QLabel('Bản in lấy đúng mẫu IN_CHITIET / IN_BANGTONGHOP của file PABT Excel (thư mục mau_in); tờ trình, phương án '
                         'tổng theo mẫu ở cửa sổ "Đợt trình…" (số văn bản, số phương án tổng lấy theo đợt đã chọn). PDF và máy in '
                         'cần Microsoft Excel (văn bản Word: Microsoft Word) trên máy.')
        self.lb.setWordWrap(True)
        b_xem = QPushButton('Xem trước bản in…')
        b_xem.setToolTip('In thử phương án chi tiết của hộ đầu tiên trong danh sách và mở ra xem (không lưu vào thư mục)')
        b_xem.clicked.connect(lambda: self.xem_truoc())
        b_mau = QPushButton('Sửa mẫu in trong Excel…')
        b_mau.setToolTip('Mở mẫu phương án chi tiết bằng Excel: sửa chữ, phông, lề, độ rộng cột, kéo đường kẻ... rồi Lưu. '
                         'Giữ nguyên các chỗ trống {du_an}, {ho_ten}, {nguon_goc}...')
        b_mau.clicked.connect(lambda: self.sua_mau())
        hang_mau = QHBoxLayout()
        hang_mau.addWidget(b_xem)
        hang_mau.addWidget(b_mau)
        for chu, loai in (('Sửa mẫu tờ trình…', 'to_trinh'), ('Sửa mẫu phương án tổng…', 'pa_tong')):
            b = QPushButton(chu)
            b.setToolTip('Mở mẫu bằng Word / Excel để sửa; thêm mẫu từ file Word / Excel / PDF ở cửa sổ "Đợt trình…"')
            b.clicked.connect(lambda _=False, x=loai: self.sua_mau_van_ban(x))
            hang_mau.addWidget(b)
        hang_mau.addStretch(1)
        lo = QVBoxLayout(self)
        lo.addLayout(form)
        lo.addLayout(hang_mau)
        lo.addWidget(self.lb)
        lo.addWidget(nut)
        self._theo_pham_vi()

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

    def chon_mau(self, co: bool):
        """Chọn / bỏ chọn mọi mẫu in (in đồng loạt), hoặc đánh dấu từng mẫu để in riêng lẻ."""
        for o in (self.o_ct, self.o_bth, self.o_tt, self.o_pat):
            o.setChecked(co)

    def sua_mau_van_ban(self, loai: str, mo: bool = True):
        from . import van_ban_trinh as vb
        from .in_an import mo_file
        p = vb.mau_de_sua(loai)
        if mo:
            QMessageBox.information(self, TEN_UD, f'Mở mẫu {vb.LOAI[loai][1].lower()} bằng {"Excel" if p.suffix == ".xlsx" else "Word"}:'
                                    f'\n{p}\n\nSửa xong bấm Lưu rồi đóng. Chỗ trống viết trong ngoặc nhọn, ví dụ {{so_to_trinh}} '
                                    '(danh sách ở cửa sổ "Đợt trình…" > "Chỗ trống dùng trong mẫu…").')
            mo_file(p)
        return p

    def xem_truoc(self, mo: bool = True):
        """In thử hộ đầu tiên của phạm vi đang chọn vào thư mục tạm và mở ra xem. Trả file đã tạo."""
        from . import in_an
        ds = self.ds_ho()
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Không có hộ nào để xem.')
            return None
        try:
            with con_tro_cho():
                f = in_an.xem_truoc(self.con, ds[0])
        except (in_an.LoiIn, OSError) as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        if mo:
            in_an.mo_file(f)
        return f

    def sua_mau(self, mo: bool = True):
        from . import in_an
        try:
            f = in_an.mau_de_sua()
        except (in_an.LoiIn, OSError) as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        if mo:
            QMessageBox.information(self, TEN_UD, f'Mở mẫu in bằng Excel:\n{f}\n\nSửa xong bấm Lưu (giữ định dạng .xlsx) rồi đóng Excel; '
                                    'lần in sau phần mềm dùng mẫu đã sửa. Giữ nguyên các chỗ trống trong ngoặc {…} '
                                    '(tên dự án, họ tên, nguồn gốc…). Bấm "Xem trước bản in…" để kiểm tra.')
            in_an.mo_file(f)
        return f

    def _chon_thu_muc(self):
        p = QFileDialog.getExistingDirectory(self, 'Chọn thư mục lưu bản in', self.o_thu_muc.text())
        if p:
            self.o_thu_muc.setText(p)

    def ds_ho(self) -> list:
        """Các hộ đang đánh dấu chọn, theo thứ tự danh sách."""
        return [self.bang_ho.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(self.bang_ho.rowCount())
                if self.bang_ho.item(i, 0).checkState() == Qt.CheckState.Checked]

    def thuc_hien(self, xac_nhan: bool = True):
        from . import in_an
        from . import van_ban_trinh as vb
        ds = self.ds_ho()
        chon = dict(chi_tiet=self.o_ct.isChecked(), bang_tong_hop=self.o_bth.isChecked(), to_trinh=self.o_tt.isChecked(),
                    pa_tong=self.o_pat.isChecked())
        if not any(chon.values()):
            QMessageBox.information(self, TEN_UD, 'Chọn ít nhất một loại bản in.')
            return None
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Chưa chọn hộ nào để in: đánh dấu cột "Chọn" trong danh sách hộ.')
            return None
        tu_lap = [m for m in ds if self.lap.get(m) == 'tu_lap']
        if tu_lap and xac_nhan and QMessageBox.question(
                self, TEN_UD, f'Có {len(tu_lap)} / {len(ds)} hộ đang chọn là phương án phần mềm TỰ LẬP, chưa mở soát và lưu. '
                              'Vẫn in / xuất các hộ này?') != QMessageBox.StandardButton.Yes:
            return None
        in_may = self.r_in.isChecked()
        so_ban = self.o_so_ban.value() if in_may else 1
        if in_may and xac_nhan:
            so = (len(ds) if chon['chi_tiet'] else 0) + sum(1 for k in ('bang_tong_hop', 'to_trinh', 'pa_tong') if chon[k])
            if QMessageBox.question(self, TEN_UD, f'Gửi {so} bản in' + (f' × {so_ban} bản' if so_ban > 1 else '') +
                                    ' tới máy in mặc định của Windows?') != QMessageBox.StandardButton.Yes:
                return None
        thu_muc = Path(self.o_thu_muc.text().strip() or '.')
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
                kq = vb.xuat_bo_ho_so(self.con, ds, thu_muc, dot=self.dot_chon(), pdf=self.r_pdf.isChecked(), in_may=in_may,
                                      so_ban=so_ban, chia_thu_muc=self.o_chia.isChecked(), bao_tien_do=bao_tao, bao_excel=bao_excel,
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
        tien.close()
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

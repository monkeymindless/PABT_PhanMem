"""Hộp chọn xã / phường sau khi đọc / scan văn bản giá đất hoặc hệ số K (1.1.06 - người dùng 12/11/2026: "khi scan file xong hiện danh
sách tích chọn những xã muốn làm bộ đơn giá, hệ số K, không phải xóa tay từng xã không dùng; có chọn từng xã và chọn tất cả").

Chỉ hiển thị, không ghi gì: trả danh sách địa bàn được chọn, nơi gọi lọc các dòng đã đọc trước khi đưa lên bảng xem trước.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

COT = ('Chọn', 'Xã / phường', 'Số dòng đọc được', 'Đang có trên máy')


def _so(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')          # 1.210: dấu chấm hàng nghìn kiểu Việt Nam


def dem_theo_dia_ban(dong: list, khoa: str) -> list:
    """[(địa bàn, số dòng)] theo thứ tự xuất hiện trong file; địa bàn trống gom thành ''."""
    dem = {}
    for r in dong:
        x = str(r.get(khoa) or '').strip()
        dem[x] = dem.get(x, 0) + 1
    return list(dem.items())


def loc_theo_dia_ban(dong: list, khoa: str, chon: list) -> list:
    """Các dòng thuộc địa bàn được chọn (giữ nguyên thứ tự, không chép / sửa dòng)."""
    tap = {str(x).strip() for x in chon}
    return [r for r in dong if str(r.get(khoa) or '').strip() in tap]


class HopChonDiaBan(QDialog):
    """Danh sách xã / phường vừa đọc: tích từng xã, Chọn tất cả, Bỏ chọn, lọc theo tên. accept -> self.chon (địa bàn đã tích)."""
    im_lang = False

    def __init__(self, parent=None, ds: list | None = None, chon_san=None, tren_may=None, loai: str = 'giá đất'):
        """ds: [(địa bàn, số dòng)]; chon_san(địa bàn) -> bool: tích sẵn; tren_may(địa bàn) -> số dòng đang có trên máy (0 = chưa có)."""
        super().__init__(parent)
        self.setWindowTitle(f'Chọn xã / phường đưa vào bảng {loai}')
        self.resize(640, 560)
        self.chon = []
        self._ds = list(ds or [])
        lo = QVBoxLayout(self)
        tong = sum(n for _, n in self._ds)
        self.lb = QLabel(f'File có {len(self._ds)} xã / phường ({_so(tong)} dòng {loai}). Tích các xã cần dùng - chỉ các xã này được đưa lên '
                         'bảng xem trước rồi mới ghi; xã không tích bỏ qua, không phải xóa tay từng dòng.')
        self.lb.setWordWrap(True)
        lo.addWidget(self.lb)
        hang = QHBoxLayout()
        self.o_loc = QLineEdit()
        self.o_loc.setPlaceholderText('Lọc theo tên xã / phường…')
        self.o_loc.setClearButtonEnabled(True)
        self.b_het = QPushButton('Chọn tất cả')
        self.b_het.setToolTip('Tích mọi xã / phường đang hiện (sau khi lọc)')
        self.b_bo = QPushButton('Bỏ chọn')
        self.b_bo.setToolTip('Bỏ tích mọi xã / phường đang hiện (sau khi lọc)')
        hang.addWidget(self.o_loc, 1)
        hang.addWidget(self.b_het)
        hang.addWidget(self.b_bo)
        lo.addLayout(hang)
        self.bang = QTableWidget(0, len(COT))
        self.bang.setHorizontalHeaderLabels(list(COT))
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.verticalHeader().setVisible(False)
        hh = self.bang.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c in (0, 2, 3):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        for x, n in self._ds:
            r = self.bang.rowCount()
            self.bang.insertRow(r)
            o = QTableWidgetItem()
            o.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            o.setCheckState(Qt.CheckState.Checked if chon_san and chon_san(x) else Qt.CheckState.Unchecked)
            o.setData(Qt.ItemDataRole.UserRole, x)
            self.bang.setItem(r, 0, o)
            self.bang.setItem(r, 1, QTableWidgetItem(x or '(không ghi tên địa bàn)'))
            for c, v in ((2, n), (3, tren_may(x) if tren_may else 0)):
                it = QTableWidgetItem(f'{_so(v)} dòng' if v else ('chưa có' if c == 3 else '0'))
                it.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
                self.bang.setItem(r, c, it)
        lo.addWidget(self.bang, 1)
        self.lb_dem = QLabel('')
        lo.addWidget(self.lb_dem)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.b_ok = nut.button(QDialogButtonBox.StandardButton.Ok)
        self.b_ok.setText('Dùng các xã đã chọn')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo.addWidget(nut)
        self.b_het.clicked.connect(lambda: self.dat_tat_ca(True))
        self.b_bo.clicked.connect(lambda: self.dat_tat_ca(False))
        self.o_loc.textChanged.connect(self.loc)
        self.bang.itemChanged.connect(lambda *_: self._dem())
        self.bang.cellDoubleClicked.connect(self._dao)
        self._dem()

    def _o(self, r: int) -> QTableWidgetItem:
        return self.bang.item(r, 0)

    def dat_tat_ca(self, chon: bool) -> None:
        """Tích / bỏ tích mọi dòng đang hiện (dòng bị lọc ẩn giữ nguyên)."""
        tt = Qt.CheckState.Checked if chon else Qt.CheckState.Unchecked
        self.bang.blockSignals(True)
        try:
            for r in range(self.bang.rowCount()):
                if not self.bang.isRowHidden(r):
                    self._o(r).setCheckState(tt)
        finally:
            self.bang.blockSignals(False)
        self._dem()

    def dat_chon(self, ds: list) -> None:
        """Tích đúng các địa bàn trong ds (kiểm thử, gọi từ mã)."""
        tap = set(ds)
        self.bang.blockSignals(True)
        try:
            for r in range(self.bang.rowCount()):
                o = self._o(r)
                o.setCheckState(Qt.CheckState.Checked if o.data(Qt.ItemDataRole.UserRole) in tap else Qt.CheckState.Unchecked)
        finally:
            self.bang.blockSignals(False)
        self._dem()

    def _dao(self, r: int, c: int) -> None:
        if c != 0:
            o = self._o(r)
            o.setCheckState(Qt.CheckState.Unchecked if o.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked)

    def loc(self, chu: str = '') -> None:
        from .lap_pa import bo_dau
        k = bo_dau((chu or '').strip()).lower()
        for r in range(self.bang.rowCount()):
            self.bang.setRowHidden(r, bool(k) and k not in bo_dau(self.bang.item(r, 1).text()).lower())

    def da_chon(self) -> list:
        return [self._o(r).data(Qt.ItemDataRole.UserRole) for r in range(self.bang.rowCount())
                if self._o(r).checkState() == Qt.CheckState.Checked]

    def _dem(self) -> None:
        ds = self.da_chon()
        so = sum(n for x, n in self._ds if x in set(ds))
        self.lb_dem.setText(f'Đã chọn {len(ds)} / {len(self._ds)} xã / phường - {_so(so)} dòng.')
        self.b_ok.setEnabled(bool(ds))

    def accept(self) -> None:
        self.chon = self.da_chon()
        if not self.chon:
            return
        super().accept()


def chon_dia_ban(cha, dong: list, khoa: str, chon_san=None, tren_may=None, loai: str = 'giá đất', chon=None):
    """Hiện HopChonDiaBan khi các dòng đọc được thuộc từ 2 địa bàn trở lên. Trả các dòng của địa bàn được chọn (một địa bàn: trả
    nguyên dong), hoặc None khi người dùng bấm Hủy. chon: danh sách địa bàn chọn thay người dùng (kiểm thử). Chế độ im lặng
    (cha.im_lang) không truyền chon: giữ nguyên mọi dòng như trước khi có hộp này."""
    ds = dem_theo_dia_ban(dong, khoa)
    if len(ds) < 2:
        return dong
    if chon is None and getattr(cha, 'im_lang', False):
        return dong
    from PySide6.QtWidgets import QWidget
    h = HopChonDiaBan(cha if isinstance(cha, QWidget) else None, ds, chon_san, tren_may, loai)
    try:
        if chon is not None:
            h.dat_chon(chon)
            return loc_theo_dia_ban(dong, khoa, h.da_chon())
        if h.exec() != QDialog.DialogCode.Accepted:
            return None
        return loc_theo_dia_ban(dong, khoa, h.chon)
    finally:
        h.deleteLater()

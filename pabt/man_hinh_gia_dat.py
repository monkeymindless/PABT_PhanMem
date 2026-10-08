"""Hộp tra bảng giá đất NQ 28/2025/NQ-HĐND: chọn địa bàn, loại giá, tìm theo tên đường; chọn một dòng -> lấy giá."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import gia_dat_nq28 as nq
from .tien import vn

XANH = QColor('#DDEBF7')


class HopTraGiaDat(QDialog):
    def __init__(self, parent=None, xa: str = '', loai_dat: str = '', chi_xem: bool = False):
        super().__init__(parent)
        self.chon = None                 # (dòng, cột) đã chọn
        self.setWindowTitle('Tra bảng giá đất - NQ 28/2025/NQ-HĐND')
        self.resize(1300, 700)
        self.o_xa = QComboBox()
        self.o_xa.addItems(['(Tất cả địa bàn)'] + nq.ds_xa())
        for i, x in enumerate(nq.ds_xa(), start=1):
            if nq.khop_xa(xa, x):
                self.o_xa.setCurrentIndex(i)
        self.o_cot = QComboBox()
        for k, t in nq.COT:
            self.o_cot.addItem(t, k)
        c = nq.cot_cua_loai(loai_dat)
        if c:
            self.o_cot.setCurrentIndex(self.o_cot.findData(c))
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm tên đường, điểm đầu / cuối (không cần dấu): vd "768", "huong lo 15", "MT"')
        hang = QHBoxLayout()
        for nhan, w in (('Địa bàn:', self.o_xa), ('Loại giá:', self.o_cot), ('Tìm:', self.o_tim)):
            l = QLabel(nhan)
            l.setProperty('vai', 'nhan')
            hang.addWidget(l)
            hang.addWidget(w, 1 if w is self.o_tim else 0)
        self.bang = QTableWidget(0, 7)
        self.bang.setHorizontalHeaderLabels(['Địa bàn', 'TT', 'Tên đường', 'Điểm đầu → điểm cuối', 'Vị trí', 'Điều kiện', 'Giá (đ/m²)'])
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.bang.verticalHeader().setVisible(False)
        for c, w in enumerate((110, 45, 190, 300, 50, 380, 110)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.doubleClicked.connect(lambda *_: None if chi_xem else self.accept())
        self.lb = QLabel(nq.VAN_BAN + '. Văn bản ghi giá theo nghìn đồng/m²; cột Giá đã quy ra đồng/m². '
                         'Nhấp đúp một dòng để lấy giá.' if not chi_xem else nq.VAN_BAN + '. Giá đồng/m².')
        self.lb.setWordWrap(True)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Close if chi_xem else
                               QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        if not chi_xem:
            nut.button(QDialogButtonBox.StandardButton.Ok).setText('Lấy giá dòng đang chọn')
            nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        else:
            nut.button(QDialogButtonBox.StandardButton.Close).setText('Đóng')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        lo.addLayout(hang)
        lo.addWidget(self.bang, 1)
        lo.addWidget(self.lb)
        lo.addWidget(nut)
        self.o_xa.currentIndexChanged.connect(self.ve)
        self.o_cot.currentIndexChanged.connect(self.ve)
        self.o_tim.textChanged.connect(self.ve)
        self.ve()

    def ve(self):
        xa = self.o_xa.currentText() if self.o_xa.currentIndex() > 0 else ''
        cot = self.o_cot.currentData()
        self.ds = nq.tim(xa, self.o_tim.text()) if xa or self.o_tim.text() else nq.tat_ca()
        if xa:
            self.ds = [r for r in self.ds if r['xa'] == xa]
        self.bang.setRowCount(len(self.ds))
        dam = QFont()
        dam.setBold(True)
        for i, r in enumerate(self.ds):
            o = [r['xa'], str(r['tt']), r['ten_duong'], f'{r["diem_dau"]} → {r["diem_cuoi"]}', r['vi_tri'],
                 nq.mo_ta_vi_tri(r), vn(nq.gia_dong(r, cot))]
            for c, v in enumerate(o):
                it = QTableWidgetItem(v)
                it.setToolTip(v)
                if c in (1, 6):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if r['vi_tri'] == 'MT':
                    it.setBackground(QBrush(XANH))
                    it.setFont(dam)
                self.bang.setItem(i, c, it)

    def accept(self):
        i = self.bang.currentRow()
        if 0 <= i < len(self.ds):
            self.chon = (self.ds[i], self.o_cot.currentData())
        super().accept()

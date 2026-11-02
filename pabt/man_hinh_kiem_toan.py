"""Cửa sổ "Nhật ký kiểm toán" (0.9.86): xem / lọc / xuất Excel nhật ký thay đổi số liệu (kiem_toan.audit_logs) - ai sửa, lúc nào,
máy nào, hộ / thửa / dòng phương án nào, giá trị cũ -> mới. Chỉ đọc (nhật ký không sửa / xóa được)."""
from __future__ import annotations
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import kiem_toan
from .giao_dien import TOKEN, con_tro_cho, loc_khi_ngung_go
from .thong_bao import TEN_UD, chu_loi

COT = ['Thời gian', 'Người sửa', 'Máy', 'Thao tác', 'Mã hộ', 'Đối tượng', 'Trường', 'Giá trị cũ', 'Giá trị mới', 'Ghi chú']
KY = [('Tất cả', None), ('Hôm nay', 0), ('7 ngày gần đây', 7), ('30 ngày gần đây', 30), ('Năm nay', 'nam')]
MAU_HANH_DONG = {'them': '#1B5E20', 'sua': TOKEN['chinh'], 'xoa': '#B3261E'}


class HopKiemToan(QDialog):
    def __init__(self, con, parent=None, ma_ho: int | None = None, ten_du_an: str = '', thu_muc=None):
        super().__init__(parent)
        self.con, self.ten_du_an, self.thu_muc = con, ten_du_an, thu_muc
        self.setWindowTitle('Nhật ký kiểm toán - thay đổi số liệu')
        self.resize(1250, 720)
        self.cb_ho = QComboBox()
        self.cb_ho.addItem('Mọi hộ và danh mục', None)
        for r in con.execute('SELECT ma_ho, thu_tu, ho_ten FROM ho ORDER BY thu_tu, ma_ho'):
            self.cb_ho.addItem(f'{r["thu_tu"]}. {r["ho_ten"]}', r['ma_ho'])
        if ma_ho is not None and self.cb_ho.findData(ma_ho) >= 0:
            self.cb_ho.setCurrentIndex(self.cb_ho.findData(ma_ho))
        self.cb_ky = QComboBox()
        for t, v in KY:
            self.cb_ky.addItem(t, v)
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm người sửa, đối tượng, giá trị (không cần dấu)…')
        loc_khi_ngung_go(self.o_tim, lambda _: self.nap())
        self.cb_ho.currentIndexChanged.connect(lambda _: self.nap())
        self.cb_ky.currentIndexChanged.connect(lambda _: self.nap())
        h = QHBoxLayout()
        for nhan, w, gian in (('Hộ:', self.cb_ho, 2), ('Thời gian:', self.cb_ky, 0), ('Tìm:', self.o_tim, 2)):
            lb = QLabel(nhan)
            lb.setProperty('vai', 'nhan')
            h.addWidget(lb)
            h.addWidget(w, gian)
        self.bang = QTableWidget(0, len(COT))
        self.bang.setHorizontalHeaderLabels(COT)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setWordWrap(True)
        for c, w in enumerate((140, 120, 110, 70, 60, 300, 140, 160, 160, 140)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        b_xuat = QPushButton('Xuất Excel…')
        b_xuat.clicked.connect(lambda: self.xuat())
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        hd = QHBoxLayout()
        hd.addWidget(self.lb, 1)
        hd.addWidget(b_xuat)
        hd.addWidget(b_dong)
        lo = QVBoxLayout(self)
        lo.addLayout(h)
        lo.addWidget(self.bang, 1)
        lo.addLayout(hd)
        self.ds = []
        self.nap()

    def _khoang(self) -> tuple:
        v = self.cb_ky.currentData()
        if v is None:
            return '', ''
        if v == 'nam':
            return f'{date.today().year}-01-01', ''
        return (date.today() - timedelta(days=int(v))).isoformat(), ''

    def nap(self) -> None:
        tu, den = self._khoang()
        with con_tro_cho():
            self.ds = kiem_toan.doc(self.con, self.cb_ho.currentData(), self.o_tim.text(), tu, den)
        self.bang.setRowCount(len(self.ds))
        for i, d in enumerate(self.ds):
            luc = str(d['luc'] or '')
            hien = f'{luc[8:10]}/{luc[5:7]}/{luc[:4]} {luc[11:19]}' if len(luc) >= 19 else luc
            gt = (hien, d['nguoi'], d['may'], kiem_toan.HANH_DONG.get(d['hanh_dong'], d['hanh_dong']),
                  '' if d['ma_ho'] is None else str(d['ma_ho']), d['doi_tuong'], kiem_toan.nhan(d), d['cu'], d['moi'], d['thao_tac'])
            for c, v in enumerate(gt):
                it = QTableWidgetItem('' if v is None else str(v))
                if c == 3:
                    it.setForeground(QColor(MAU_HANH_DONG.get(d['hanh_dong'], '#202124')))
                if c in (7, 8) and v is not None and len(str(v)) > 30:
                    it.setToolTip(str(v))
                self.bang.setItem(i, c, it)
        n = len(self.ds)
        self.lb.setText(f'{n} thay đổi' + (' (hiện 20.000 dòng mới nhất - lọc thêm để xem cũ hơn)' if n >= 20000 else '') +
                        '. Nhật ký ghi tự động khi thêm / sửa / xóa hộ, thửa, lưu phương án, sửa đơn giá danh mục; không sửa, '
                        'không xóa được (kể cả bằng công cụ khác).')

    def xuat(self, file=None) -> Path | None:
        if not self.ds:
            QMessageBox.information(self, TEN_UD, 'Không có dòng nào để xuất.')
            return None
        if file is None:
            goc = Path(self.thu_muc) if self.thu_muc else Path.home() / 'Documents'
            file, _ = QFileDialog.getSaveFileName(self, 'Xuất nhật ký kiểm toán', str(goc / f'NhatKyKiemToan_{datetime.now():%Y%m%d_%H%M}.xlsx'),
                                                  'Excel (*.xlsx)')
            if not file:
                return None
        try:
            with con_tro_cho():
                kiem_toan.xuat_excel(self.ds, file, self.ten_du_an)
        except OSError as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không ghi được file Excel', e))
            return None
        return Path(file)

"""Màn hình "Kiểm tra an toàn": phần mềm diệt virus của máy, quét file, kết nối HTTPS, toàn vẹn bản cài, chữ ký gói cập nhật
(pabt/an_toan.py); quét một file bất kỳ trước khi mở."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import an_toan

TEN_UD = 'PABT - Lập phương án bồi thường, hỗ trợ'
TT = {True: ('ĐẠT', '#E8F5E9', '#1B5E20'), False: ('CẢNH BÁO', '#FFEBEE', '#B71C1C'), None: ('LƯU Ý', '#FFF8E1', '#7A5B00')}


class HopAnToan(QDialog):
    im_lang = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Kiểm tra an toàn')
        self.resize(1050, 470)
        self.thong_bao_cuoi = ''
        lo = QVBoxLayout(self)
        gt = QLabel('PABT bảo vệ dữ liệu ở những chỗ nhận dữ liệu từ bên ngoài: file tải từ web, gói cập nhật, file Word / Excel cũ '
                    'được quét bằng phần mềm diệt virus của máy trước khi mở; kết nối mạng chỉ chấp nhận chứng chỉ hợp lệ; gói '
                    'cập nhật phải có chữ ký số của nhà phát triển. PABT không thay thế phần mềm diệt virus: hãy giữ Microsoft '
                    'Defender (hoặc phần mềm diệt virus khác) luôn bật và cập nhật.')
        gt.setWordWrap(True)
        lo.addWidget(gt)
        self.bang = QTableWidget(0, 3)
        self.bang.setHorizontalHeaderLabels(['Mục', 'Tình trạng', 'Chi tiết'])
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setWordWrap(True)
        for c, w in enumerate((240, 100, 650)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.verticalHeader().setVisible(False)
        lo.addWidget(self.bang, 1)
        nut = QHBoxLayout()
        b_quet = QPushButton('Quét một file…')
        b_quet.setToolTip('Quét file (văn bản nhận qua Zalo, email, USB...) bằng phần mềm diệt virus của máy trước khi mở')
        b_quet.clicked.connect(lambda: self.quet_file())
        nut.addWidget(b_quet)
        b_lai = QPushButton('Kiểm tra lại')
        b_lai.clicked.connect(lambda: self.nap())
        nut.addWidget(b_lai)
        nut.addStretch(1)
        dong = QPushButton('Đóng')
        dong.clicked.connect(self.accept)
        nut.addWidget(dong)
        lo.addLayout(nut)
        self.nap()

    def nap(self) -> list:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            ds = an_toan.tong_quan()
        finally:
            QApplication.restoreOverrideCursor()
        self.bang.setRowCount(len(ds))
        for i, (muc, dat, mt) in enumerate(ds):
            chu, nen, mau = TT[dat]
            for c, v in enumerate((muc, chu, mt)):
                it = QTableWidgetItem(v)
                it.setToolTip(mt)
                if c == 1:
                    it.setBackground(QBrush(QColor(nen)))
                    it.setForeground(QBrush(QColor(mau)))
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.bang.setItem(i, c, it)
        self.bang.resizeRowsToContents()
        self.ds = ds
        return ds

    def quet_file(self, p=None):
        if p is None:
            p, _ = QFileDialog.getOpenFileName(self, 'Chọn file cần quét')
            if not p:
                return None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            kq = an_toan.quet_file(p)
        finally:
            QApplication.restoreOverrideCursor()
        self.thong_bao_cuoi = kq.mo_ta
        if not self.im_lang:
            (QMessageBox.critical if kq.co_ma_doc else QMessageBox.information)(
                self, TEN_UD, f'{p}\n\n{kq.mo_ta}' + ('\n\nKHÔNG mở file này; xóa file và báo người gửi.' if kq.co_ma_doc else ''))
        return kq

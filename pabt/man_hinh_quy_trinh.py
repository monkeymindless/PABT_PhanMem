"""Hộp "Quy trình 16 bước QĐ 18": bảng 16 bước thu hồi đất, bồi thường, hỗ trợ và chỗ làm từng bước trong phần mềm (liên kết chân
trang màn hình chào)."""
from __future__ import annotations
from .giao_dien import vua_dong  # noqa: E402
from .giao_dien import dat_kieu_theo_tong  # noqa: E402  (kiểu riêng đổi theo tông nền)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from .quy_trinh_qd18 import BUOC, GHI_CHU, sla_buoc


class HopQuyTrinh(QDialog):
    im_lang = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Quy trình 16 bước thu hồi đất, bồi thường, hỗ trợ - QĐ 18/2026/QĐ-UBND')
        self.resize(1080, 620)
        tieu = QLabel('Quy trình 16 bước và chỗ thực hiện trong phần mềm')
        tieu.setProperty('vai', 'tieu_de')
        self.bang = QTableWidget(len(BUOC), 5)
        self.bang.setHorizontalHeaderLabels(['Bước', 'Công việc', 'Thời hạn (SLA)', 'Làm ở đâu trong phần mềm', 'Tài liệu, kết quả'])
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setWordWrap(True)
        for r, (so, viec, cho, tai_lieu) in enumerate(BUOC):
            for c, v in enumerate((f'Bước {so}', viec, sla_buoc(so), cho, tai_lieu)):
                it = QTableWidgetItem(v)
                if c in (0, 2):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.bang.setItem(r, c, it)
        h = self.bang.horizontalHeader()
        for c in (0, 2):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        for c in (1, 3, 4):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        vua_dong(self.bang, None, None)
        ghi_chu = QLabel(GHI_CHU)
        ghi_chu.setWordWrap(True)
        dat_kieu_theo_tong(ghi_chu, 'QLabel { color: #64748B; font-size: 12px; }')
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.accept)
        hn = QHBoxLayout()
        hn.addStretch(1)
        hn.addWidget(b_dong)
        lo = QVBoxLayout(self)
        lo.addWidget(tieu)
        lo.addWidget(self.bang, 1)
        lo.addWidget(ghi_chu)
        lo.addLayout(hn)

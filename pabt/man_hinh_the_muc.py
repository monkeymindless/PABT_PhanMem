"""Thanh 6 mục nhập nổi bật của cửa sổ lập phương án (1.0.69): thẻ dạng khối cao 36 px, màu theo trạng thái (đang chọn / có dữ liệu / trống), phím Alt+0..5, huy hiệu tổng kinh phí ở góc phải.
Dữ liệu vẫn ở QTabWidget của cửa sổ (thanh thẻ gốc ẩn): thanh này chỉ đọc chữ thẻ và gọi sang_the, không giữ trạng thái riêng. Biểu tượng bằng phông Segoe (Win 7 không có phông: chỉ chữ)."""
from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from .giao_dien import chu_hien, dat_kieu_theo_tong, icon_ky_hieu

CAO_THE = 36
# Segoe MDL2: hồ sơ, bản đồ, nhà, cây, vật nuôi (trái tim: phông không có hình con vật), hỗ trợ
BIEU_TUONG = (0xE8A5, 0xE826, 0xE80F, 0xE913, 0xEB51, 0xE8F1)
MAU_THE = {'chon': ('#1d4ed8', '#1e3a8a', '#ffffff', 'bold'), 'co': ('#f0fdf4', '#16a34a', '#15803d', 'bold'), 'trong': ('#f8fafc', '#cbd5e1', '#475569', '600')}
QSS_HUY_HIEU = 'QLabel { background: #fef3c7; border: 1px solid #f59e0b; border-radius: 6px; color: #b45309; font-weight: bold; padding: 2px 10px; }'


def _qss(trang: str) -> str:
    nen, vien, chu, dam = MAU_THE[trang]
    return (f'QPushButton {{ background: {nen}; border: 1px solid {vien}; color: {chu}; font-weight: {dam}; font-size: 13px; border-radius: 6px; padding: 2px 10px; }}'
            f'QPushButton:hover {{ border-width: 2px; }}')


TIEN_TO_TONG = 'Tổng kinh phí hộ: '
LE_THE_MUC, LE_HUY_HIEU = 44, 22                        # biểu tượng + lề trong một thẻ; lề huy hiệu (px)


class ThanhTheMuc(QWidget):
    """man: CuaSoLapPA. nut[i]: thẻ thứ i của man.tab. dat_chu(i, chu, so_dong): cập nhật chữ + màu."""

    def __init__(self, man, so_the: int):
        super().__init__()
        self.setObjectName('thanh_the_muc')
        self.man = man
        self.nut, self._trang, self._so, self._chu = [], {}, {}, {}
        self.h = QHBoxLayout(self)
        self.h.setContentsMargins(6, 2, 6, 2)
        self.h.setSpacing(4)
        self._phim = []
        for i in range(so_the):
            b = QPushButton('')
            b.setFixedHeight(CAO_THE)
            b.setCheckable(True)
            b.setProperty('khong_icon', True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(f'Alt+{i}')
            b.clicked.connect(lambda *_, k=i: self.bam(k))
            if i < len(BIEU_TUONG):
                ic = icon_ky_hieu(BIEU_TUONG[i], '#1E3A5F', 16)
                if ic is not None:
                    b.setIcon(ic)
            self.h.addWidget(b)
            self.nut.append(b)
            sc = QShortcut(QKeySequence(f'Alt+{i}'), man)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(lambda k=i: self.bam(k))
            self._phim.append(sc)
        self.h.addStretch(1)
        man.tab.currentChanged.connect(lambda *_: self.ve())

    def dat_huy_hieu(self, lb: QLabel) -> None:
        dat_kieu_theo_tong(lb, QSS_HUY_HIEU)
        lb.setFixedHeight(CAO_THE - 4)
        self.h.addWidget(lb)
        self._huy_hieu = lb

    @staticmethod
    def _chu_muc(chu: str, muc: int) -> str:
        """Chữ thẻ theo mức gọn: 0 '1. Đất (1 • 150,0 triệu)'; 1 '1. Đất (1)'; 2 '1. Đất'."""
        m = re.match(r'^(.*?) \((.*)\)$', chu)
        if muc == 0 or m is None:
            return chu
        return m.group(1) if muc == 2 else f'{m.group(1)} ({m.group(2).split(" • ")[0]})'

    def vua(self) -> None:
        """Chọn mức chữ đầy đủ nhất vừa bề rộng thanh (06/11/2026: 1366 @125% cắt chữ thẻ, huy hiệu mất số tiền). Chữ đầy đủ ở chú thích."""
        lb = getattr(self, '_huy_hieu', None)
        if not self.nut or self.width() <= 0:
            return
        chu = [self._chu.get(i, '') for i in range(len(self.nut))]
        tong = lb.property('chu_day_du') if lb is not None else ''
        if lb is not None and lb.text() != tong and lb.text().startswith(TIEN_TO_TONG):
            tong = lb.text()                            # phần mềm vừa đặt chữ đầy đủ mới
            lb.setProperty('chu_day_du', tong)
        tong = tong or ''
        chua = self.width() - self.h.contentsMargins().left() - self.h.contentsMargins().right() - self.h.spacing() * len(self.nut)
        fm = self.nut[0].fontMetrics()
        for muc in (0, 1, 2):
            hh = tong if muc < 2 else tong[len(TIEN_TO_TONG):]
            can = sum(fm.horizontalAdvance(self._chu_muc(c, muc).replace('&&', '&')) + LE_THE_MUC for c in chu)
            can += fm.horizontalAdvance(hh) + LE_HUY_HIEU if lb is not None else 0
            if can <= chua:
                break
        for b, c in zip(self.nut, chu):
            t = self._chu_muc(c, muc)
            if b.text() != t:
                b.setText(t)
        if lb is not None and lb.text() != hh:
            lb.setText(hh)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.vua()

    def bam(self, i: int) -> None:
        if not self.man.sang_the(i):
            self.ve()                # không chuyển được (hồ sơ chưa lưu được): trả thẻ về đúng trạng thái

    def dat_chu(self, i: int, chu: str, so_dong: int) -> None:
        self._chu[i] = chu_hien(chu)
        self.nut[i].setText(self._chu[i])
        self.nut[i].setToolTip(f'{chu} (Alt+{i})')
        self._so[i] = so_dong
        self.vua()
        self._to(i)

    def ve(self) -> None:
        for i in range(len(self.nut)):
            self._to(i)

    def _to(self, i: int) -> None:
        dang = self.man.tab.currentIndex() == i
        trang = 'chon' if dang else ('co' if self._so.get(i) else 'trong')
        b = self.nut[i]
        b.setChecked(dang)
        if self._trang.get(i) != trang:      # đặt kiểu chỉ khi đổi: gọi mỗi lần gõ ô là thừa
            self._trang[i] = trang
            dat_kieu_theo_tong(b, _qss(trang))
            if i < len(BIEU_TUONG):
                ic = icon_ky_hieu(BIEU_TUONG[i], '#ffffff' if dang else MAU_THE[trang][2], 16)
                if ic is not None:
                    b.setIcon(ic)

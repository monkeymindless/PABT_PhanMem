"""Hộp "Cỗ máy thời gian" (phương án đột phá 8, 30/10/2026): các mốc khôi phục của dự án đang mở (co_may_thoi_gian), xem khác biệt từ
mốc tới hiện tại, khôi phục về mốc (qua CuaSoChinh.khoi_phuc_moc). HopXemTruocThayDoi: hộp "thử trước" cho thao tác hàng loạt."""
from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from . import co_may_thoi_gian as cm
from .tien import D, vn

COT = ['Thời điểm', 'Lý do', 'Số hộ', 'Tổng kinh phí (đồng)', 'Cỡ']


class HopCoMayThoiGian(QDialog):
    im_lang = False

    def __init__(self, cua_so):
        super().__init__(cua_so)
        self.cs = cua_so
        self.setWindowTitle('Cỗ máy thời gian - mốc khôi phục dự án')
        self.resize(940, 600)
        gt = QLabel(f'Mốc tự lưu mỗi {cm.CHU_KY_PHUT} phút khi dự án có thay đổi, lúc mở / đóng dự án, trước thao tác hàng loạt và trước '
                    f'khi khôi phục. Giữ mọi mốc {cm.GIU_GIO} giờ gần nhất, sau đó mỗi ngày một mốc tới {cm.GIU_NGAY} ngày; mốc lưu '
                    'thủ công luôn được giữ. Chọn một mốc để xem thay đổi từ mốc đó tới hiện tại hoặc khôi phục.')
        gt.setWordWrap(True)
        self.bang = QTableWidget(0, len(COT))
        self.bang.setHorizontalHeaderLabels(COT)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for c, w in enumerate((150, 300, 70, 170)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.itemSelectionChanged.connect(lambda: self.o_kq.clear())
        self.bang.cellDoubleClicked.connect(lambda r, _c: self.xem_khac())
        self.o_kq = QPlainTextEdit()
        self.o_kq.setReadOnly(True)
        self.o_kq.setPlaceholderText('Bấm "Xem thay đổi tới hiện tại" để biết từ mốc đã chọn tới giờ những hộ nào đổi.')
        b_luu = QPushButton('Lưu mốc ngay')
        b_luu.clicked.connect(lambda: self.luu_moc())
        b_xem = QPushButton('Xem thay đổi tới hiện tại')
        b_xem.clicked.connect(lambda: self.xem_khac())
        self.b_kp = QPushButton('Khôi phục về mốc này…')
        self.b_kp.clicked.connect(lambda: self.khoi_phuc())
        b_tm = QPushButton('Mở thư mục mốc')
        b_tm.clicked.connect(self._mo_thu_muc)
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        hn = QHBoxLayout()
        for b in (b_luu, b_xem, self.b_kp, b_tm):
            hn.addWidget(b)
        hn.addStretch(1)
        hn.addWidget(b_dong)
        lo = QVBoxLayout(self)
        lo.addWidget(gt)
        lo.addWidget(self.bang, 3)
        lo.addWidget(self.o_kq, 2)
        lo.addLayout(hn)
        self.b_kp.setEnabled(not self.cs.chi_doc)
        b_luu.setEnabled(not self.cs.chi_doc)
        self.nap()

    def nap(self) -> list:
        self.ds = cm.ds_moc(self.cs.file)
        self.bang.setRowCount(len(self.ds))
        for r, m in enumerate(self.ds):
            tong = '' if m.tong in (None, '') else vn(D(m.tong))
            for c, chu in enumerate((f'{m.luc:%d/%m/%Y %H:%M:%S}', m.ten_ly_do, '' if m.so_ho is None else str(m.so_ho), tong,
                                     f'{max(1, m.co // 1024):,} KB'.replace(',', '.'))):
                self.bang.setItem(r, c, QTableWidgetItem(chu))
        if self.ds:
            self.bang.selectRow(0)
        return self.ds

    def _chon(self):
        r = self.bang.currentRow()
        return self.ds[r] if 0 <= r < len(self.ds) else None

    def luu_moc(self):
        m = self.cs.chup_moc('tay', bat_buoc=True)
        self.nap()
        if m is not None:
            self.o_kq.setPlainText(f'Đã lưu mốc {m.luc:%d/%m/%Y %H:%M:%S}.')
        return m

    def xem_khac(self):
        m = self._chon()
        if m is None:
            return None
        from .giao_dien import con_tro_cho
        try:
            with con_tro_cho():
                k = cm.so_sanh_moc(self.cs.con, m)
        except Exception as e:                          # noqa: BLE001 - mốc hỏng / file cũ
            from .thong_bao import chu_loi
            self.o_kq.setPlainText(chu_loi('Không so sánh được', e))
            return None
        self.o_kq.setPlainText(f'Từ mốc {m.luc:%d/%m/%Y %H:%M} tới hiện tại:\n' + '\n'.join(cm.chu_khac_biet(k)))
        return k

    def khoi_phuc(self, xac_nhan: bool = True) -> bool:
        m = self._chon()
        if m is None:
            return False
        if self.cs.khoi_phuc_moc(m, xac_nhan=xac_nhan and not self.im_lang):
            self.accept()
            return True
        return False

    def _mo_thu_muc(self):
        tm = cm.thu_muc_du_an(self.cs.file)
        if tm.is_dir() and not self.im_lang:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(tm)))


class HopXemTruocThayDoi(QDialog):
    """Thử trước thao tác hàng loạt: tóm tắt khác biệt (co_may_thoi_gian.KhacBiet) - Áp dụng vào dự án / Hủy."""

    def __init__(self, parent, viec: str, k, chu_dong_y: str = 'Áp dụng vào dự án'):
        super().__init__(parent)
        self.setWindowTitle(f'Xem trước: {viec}')
        self.resize(760, 520)
        lb = QLabel(f'<b>{viec}</b> - đã chạy thử trên BẢN SAO dự án (dự án chưa đổi). Kiểm tra kết quả rồi bấm "{chu_dong_y}". '
                    'Trước khi áp dụng, phần mềm lưu một mốc khôi phục (Tệp tin → Cỗ máy thời gian).')
        lb.setWordWrap(True)
        o = QPlainTextEdit('\n'.join(cm.chu_khac_biet(k)))
        o.setReadOnly(True)
        self.b_ok = QPushButton(chu_dong_y)
        self.b_ok.clicked.connect(self.accept)
        b_huy = QPushButton('Hủy')
        b_huy.clicked.connect(self.reject)
        hn = QHBoxLayout()
        hn.addStretch(1)
        hn.addWidget(self.b_ok)
        hn.addWidget(b_huy)
        lo = QVBoxLayout(self)
        lo.addWidget(lb)
        lo.addWidget(o, 1)
        lo.addLayout(hn)
        from .giao_dien import KieuNut, ap_kieu_nut
        ap_kieu_nut(self.b_ok, KieuNut.CHINH)

"""Hồ sơ scan của hộ (nút + menu dùng chung ở thẻ hồ sơ hộ, Trạng thái hộ, bảng Tiến độ) và hộp "Hoàn tất công tác bồi thường"
(chỉ xuất Excel) - 0.9.96. Logic ở ho_so_scan."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QLabel, QMenu, QMessageBox, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import ho_so_scan
from .thong_bao import TEN_UD, chu_loi


def mo_file(p) -> bool:
    """Mở file bằng chương trình mặc định của Windows. False: không mở được (file đã chuyển / xóa)."""
    import os
    p = Path(p)
    if not p.exists():
        return False
    try:
        os.startfile(str(p))                         # noqa: S606 - file người dùng tự đính kèm
    except (OSError, AttributeError):
        return False
    return True


class NutHoSoScan(QPushButton):
    """Nút "Hồ sơ scan (n)": menu đính kèm file PDF / ảnh, mở nhanh từng file, mở thư mục, bỏ đính kèm. dat(con, ma_ho, chi_doc)."""
    im_lang: bool = False

    def __init__(self, parent=None):
        super().__init__('Hồ sơ scan', parent)
        self.con, self.ma_ho, self.chi_doc = None, None, False
        self.setToolTip('Hồ sơ scan (PDF / ảnh) của hộ: đính kèm, mở nhanh (phần mềm ghi đường dẫn, không chép file)')
        self.menu = QMenu(self)
        self.menu.aboutToShow.connect(self._dung_menu)
        self.setMenu(self.menu)
        self.setEnabled(False)

    def dat(self, con, ma_ho, chi_doc: bool = False) -> None:
        self.con, self.ma_ho, self.chi_doc = con, ma_ho, chi_doc
        self.cap_nhat()

    def cap_nhat(self) -> None:
        n = len(ho_so_scan.ds_file(self.con, self.ma_ho)) if self.con is not None and self.ma_ho is not None else 0
        self.setText(f'Hồ sơ scan ({n})' if n else 'Hồ sơ scan')
        self.setEnabled(self.con is not None and self.ma_ho is not None)

    def _dung_menu(self) -> None:
        dung_menu(self.menu, self, self.con, self.ma_ho, self.chi_doc, sau=self.cap_nhat)

    def dinh_kem(self, files=None) -> int:
        return dinh_kem(self, self.con, self.ma_ho, files, sau=self.cap_nhat)


def dinh_kem(cha, con, ma_ho, files=None, sau=None) -> int:
    """Chọn (hoặc nhận) file PDF / ảnh -> đính kèm vào hộ. Trả số file thêm mới."""
    if files is None:
        files, _ = QFileDialog.getOpenFileNames(cha, 'Đính kèm hồ sơ scan (PDF / ảnh)', str(Path.home()), ho_so_scan.LOC_FILE)
    if not files:
        return 0
    try:
        n = ho_so_scan.them_file(con, ma_ho, files)
    except sqlite3.Error as e:
        if not getattr(cha, 'im_lang', False):
            QMessageBox.warning(cha, TEN_UD, chu_loi('Không đính kèm được hồ sơ scan', e))
        return 0
    if sau is not None:
        sau()
    return n


def dung_menu(menu: QMenu, cha, con, ma_ho, chi_doc: bool = False, sau=None) -> QMenu:
    """Dựng lại menu hồ sơ scan của hộ (gọi ở aboutToShow / trước exec)."""
    menu.clear()
    if con is None or ma_ho is None:
        return menu
    a = menu.addAction('Đính kèm file PDF / ảnh…')
    a.setEnabled(not chi_doc)
    a.triggered.connect(lambda: dinh_kem(cha, con, ma_ho, sau=sau))
    ds = ho_so_scan.ds_file(con, ma_ho)
    if ds:
        menu.addSeparator()
        for f in ds:
            x = menu.addAction(('' if f['con'] else '(không còn file) ') + f['ten_file'])
            x.setToolTip(f['duong_dan'])
            x.setEnabled(f['con'])
            x.triggered.connect(lambda _=False, p=f['duong_dan']: mo_file(p))
        menu.addSeparator()
        thu_muc = Path(ds[-1]['duong_dan']).parent
        x = menu.addAction('Mở thư mục chứa file')
        x.setEnabled(thu_muc.exists())
        x.triggered.connect(lambda: mo_file(thu_muc))
        bo = menu.addMenu('Bỏ đính kèm')
        bo.setEnabled(not chi_doc)
        for f in ds:
            x = bo.addAction(f['ten_file'])
            x.triggered.connect(lambda _=False, i=f['id']: (ho_so_scan.bo_file(con, ma_ho, [i]), sau and sau()))
    return menu


def mo_nhanh(cha, con, ma_ho, chi_doc: bool = False, sau=None):
    """Bảng tiến độ (bấm đúp cột Hồ sơ scan): một file -> mở luôn; nhiều / chưa có -> menu tại con trỏ. Trả số file của hộ."""
    ds = [f for f in ho_so_scan.ds_file(con, ma_ho) if f['con']]
    if len(ds) == 1:
        mo_file(ds[0]['duong_dan'])
        return 1
    if getattr(cha, 'im_lang', False):
        return len(ds)
    from PySide6.QtGui import QCursor
    m = dung_menu(QMenu(cha), cha, con, ma_ho, chi_doc, sau)
    m.exec(QCursor.pos())
    m.deleteLater()
    return len(ds)


class HopHoanTatCTBT(QDialog):
    """Danh sách hộ hoàn tất công tác bồi thường (đã có QĐ + đã bàn giao mặt bằng) theo từng đợt - xuất Excel (không có Word)."""
    im_lang: bool = False
    COT = ['Đợt', 'Mã hộ', 'Họ và tên', 'Địa chỉ', 'Quyết định', 'Ngày bàn giao', 'Hồ sơ scan']

    def __init__(self, con, parent=None, ds=None, thu_muc: str = '', ten_du_an: str = ''):
        super().__init__(parent)
        self.con, self.thu_muc, self.ten_du_an = con, thu_muc, ten_du_an
        self.setWindowTitle('Hộ hoàn tất công tác bồi thường')
        self.resize(900, 560)
        self.nhom = ho_so_scan.ds_hoan_tat(con, ds)
        scan = ho_so_scan.dem_theo_ho(con)
        n = sum(len(v) for _, v in self.nhom)
        self.lb = QLabel(f'<b>{n}</b> hộ hoàn tất (đã có quyết định phê duyệt, đã bàn giao mặt bằng - nhận tiền hay chưa không xét), '
                         f'{len(self.nhom)} đợt.')
        self.bang = QTableWidget(n, len(self.COT))
        self.bang.setHorizontalHeaderLabels(self.COT)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        r = 0
        for dot, ds_ho in self.nhom:
            for x in ds_ho:
                for c, v in enumerate((dot, x.ma_ho, x.ho_ten, x.dia_chi, '; '.join(q['so_qd'] for q in x.qd), x.ban_giao_ngay,
                                       scan.get(x.ma_ho, 0) or '')):
                    it = QTableWidgetItem(str(v))
                    if c in (1, 6):
                        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.bang.setItem(r, c, it)
                r += 1
        for c, w in enumerate((130, 60, 200, 220, 160, 100, 80)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.b_xuat = QPushButton('Xuất Excel…')
        self.b_xuat.clicked.connect(lambda: self.xuat())
        self.b_xuat.setEnabled(n > 0)
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(self.b_xuat)
        h.addWidget(b_dong)
        lo = QVBoxLayout(self)
        lo.addWidget(self.lb)
        lo.addWidget(self.bang, 1)
        lo.addLayout(h)

    def xuat(self, file_ra=None):
        """Xuất Excel; file_ra None -> hỏi nơi lưu. Trả đường dẫn đã ghi (None nếu hủy / lỗi)."""
        if file_ra is None:
            goi_y = str(Path(self.thu_muc or Path.home()) / 'HoanTat_CTBT.xlsx')
            file_ra, _ = QFileDialog.getSaveFileName(self, 'Xuất danh sách hộ hoàn tất', goi_y, 'Excel (*.xlsx)')
            if not file_ra:
                return None
        try:
            ho_so_scan.xuat_excel_hoan_tat_ctbt(self.con, file_ra, ten_du_an=self.ten_du_an)
        except OSError as e:
            if not self.im_lang:
                QMessageBox.warning(self, TEN_UD, chu_loi('Không ghi được file Excel', e))
            return None
        if not self.im_lang:
            QMessageBox.information(self, TEN_UD, f'Đã xuất: {file_ra}')
        return Path(file_ra)

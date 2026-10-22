"""Hộp Quản lý Mẫu in & Bản in (1.0.07, menu Công cụ, Ctrl+Shift+M): 3 mẫu - chi tiết chính thức, chi tiết dự thảo, bảng tổng hợp.

Mỗi mẫu: trạng thái "Mẫu nhúng chuẩn trong RAM" / "Mẫu tùy chỉnh người dùng"; Thay thế bằng file Excel khác (áp chuẩn: chi tiết A4 72%
lề 0,8 / 0,3 / 1,0 / 0,8 cm, tổng hợp A3 55% - nạp lại đệm RAM ngay); Xuất mẫu hiện tại ra Excel để sửa; Khôi phục mẫu chuẩn gốc. Logic ở
in_an (thay_mau, xuat_mau, khoi_phuc_mau, trang_thai_mau). Không emoji (Windows 7).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import dia_phuong, in_an, in_word
from .thong_bao import TEN_UD, chu_loi

MO_TA = {in_an.TEN_CT: 'A4 dọc, tỷ lệ 72%, chữ 14 / tiêu đề 16 pt',
         in_an.TEN_DT_QL: 'Bản niêm yết: chữ DỰ THẢO, không khối chữ ký',
         in_an.TEN_BTH: 'A3 ngang, tỷ lệ 55%, chữ 14 / tiêu đề 16 pt'}


class HopQuanLyMauIn(QDialog):
    def __init__(self, parent=None, im_lang: bool = False):
        super().__init__(parent)
        self.im_lang = im_lang
        self.setWindowTitle('Quản lý Mẫu in & Bản in')
        self.resize(880, 380)
        lo = QVBoxLayout(self)
        gt = QLabel('Phần mềm in theo bộ mẫu chuẩn nhúng sẵn (máy mới cài vẫn in được). Mẫu tùy chỉnh thay bằng file Excel khác '
                    'được tự áp chuẩn khổ giấy, tỷ lệ in, lề và dùng ngay lần in sau.')
        gt.setWordWrap(True)
        lo.addWidget(gt)
        self.bang = QTableWidget(len(in_an.MAU_QUAN_LY), 3)
        self.bang.setHorizontalHeaderLabels(['Mẫu', 'Quy cách', 'Trạng thái'])
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        hh = self.bang.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.bang.itemSelectionChanged.connect(self._cap_nhat_nut)
        lo.addWidget(self.bang, 1)
        # mẫu Word phương án chi tiết / bổ sung / điều chỉnh: nhúng sẵn, đổi quy cách bằng file thông số (không cần bản cập nhật)
        self.lb_word = QLabel()
        self.lb_word.setWordWrap(True)
        lo.addWidget(self.lb_word)
        hw = QHBoxLayout()
        self.b_w_xuat = QPushButton('Xuất thông số mẫu Word…')
        self.b_w_nhap = QPushButton('Nhập thông số mẫu Word…')
        self.b_w_khoi_phuc = QPushButton('Khôi phục thông số chuẩn')
        self.b_w_xuat.clicked.connect(lambda: self.xuat_word())
        self.b_w_nhap.clicked.connect(lambda: self.nhap_word())
        self.b_w_khoi_phuc.clicked.connect(lambda: self.khoi_phuc_word())
        for b in (self.b_w_xuat, self.b_w_nhap, self.b_w_khoi_phuc):
            hw.addWidget(b)
        hw.addStretch(1)
        lo.addLayout(hw)
        h = QHBoxLayout()
        self.b_thay = QPushButton('Thay thế bằng file Excel khác…')
        self.b_xuat = QPushButton('Xuất mẫu hiện tại ra Excel để chỉnh sửa…')
        self.b_khoi_phuc = QPushButton('Khôi phục mẫu chuẩn gốc')
        self.b_khoi_phuc.setToolTip('Bỏ mẫu tùy chỉnh (giữ bản sao trong thư mục mẫu\\cu) - in lại theo mẫu chuẩn nhúng')
        self.b_thay.clicked.connect(lambda: self.thay())
        self.b_xuat.clicked.connect(lambda: self.xuat())
        self.b_khoi_phuc.clicked.connect(lambda: self.khoi_phuc())
        from .giao_dien import KieuNut, ap_kieu_nut
        ap_kieu_nut(self.b_thay, KieuNut.CHINH)
        ap_kieu_nut(self.b_xuat, KieuNut.PHU)
        for b in (self.b_thay, self.b_xuat, self.b_khoi_phuc):
            h.addWidget(b)
        h.addStretch(1)
        dong = QPushButton('Đóng')
        dong.clicked.connect(self.accept)
        h.addWidget(dong)
        lo.addLayout(h)
        self.nap()
        self.bang.selectRow(0)

    def nap(self) -> None:
        for r, (ten, nhan, _) in enumerate(in_an.MAU_QUAN_LY):
            it = QTableWidgetItem(nhan)
            it.setData(Qt.ItemDataRole.UserRole, ten)
            self.bang.setItem(r, 0, it)
            self.bang.setItem(r, 1, QTableWidgetItem(MO_TA.get(ten, '')))
            tt, f = in_an.trang_thai_mau(ten)
            o = QTableWidgetItem(tt)
            o.setToolTip(str(f) if f else 'Bộ mẫu chuẩn nhúng trong phần mềm (không cần thư mục mẫu trên đĩa)')
            o.setForeground(Qt.GlobalColor.darkBlue if f is None else Qt.GlobalColor.darkYellow)
            self.bang.setItem(r, 2, o)
        self._cap_nhat_nut()
        tt = in_word.trang_thai_thong_so()
        self.lb_word.setText(f'Mẫu Word (phương án chi tiết, bổ sung, điều chỉnh): {tt}. Bố cục nhúng trong phần mềm; lề, cỡ chữ, trích yếu, '
                             f'thụt đầu dòng, độ hở gạch chân là thông số - đổi khi có quy định mới bằng "Nhập thông số mẫu Word…" '
                             f'hoặc gói .pabtcfg (Công cụ), không cần cập nhật phần mềm.')
        self.b_w_khoi_phuc.setEnabled(tt != 'Nhúng chuẩn')

    def ten_chon(self) -> str | None:
        r = self.bang.currentRow()
        it = self.bang.item(r, 0) if r >= 0 else None
        return it.data(Qt.ItemDataRole.UserRole) if it is not None else None

    def _cap_nhat_nut(self) -> None:
        ten = self.ten_chon()
        for b in (self.b_thay, self.b_xuat):
            b.setEnabled(ten is not None)
        self.b_khoi_phuc.setEnabled(ten is not None and in_an.trang_thai_mau(ten)[1] is not None)

    def _bao(self, chu: str, loi: bool = False) -> None:
        if self.im_lang:
            return
        (QMessageBox.warning if loi else QMessageBox.information)(self, TEN_UD, chu)

    def thay(self, file=None):
        ten = self.ten_chon()
        if ten is None:
            return None
        if file is None:
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn file Excel làm mẫu', str(Path.home()), 'Excel (*.xlsx *.xlsm)')
            if not file:
                return None
        try:
            p = in_an.thay_mau(ten, file)
        except Exception as e:
            self._bao(chu_loi('Không thay được mẫu in', e), True)
            return None
        self.nap()
        self._bao(f'Đã thay mẫu (áp chuẩn khổ giấy, tỷ lệ in, lề) - dùng ngay lần in sau:\n{p}')
        return p

    def xuat(self, file=None):
        ten = self.ten_chon()
        if ten is None:
            return None
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu mẫu ra Excel', str(Path.home() / 'Documents' / f'{ten}.xlsx'),
                                                  'Excel (*.xlsx)')
            if not file:
                return None
        try:
            p = in_an.xuat_mau(ten, file)
        except Exception as e:
            self._bao(chu_loi('Không xuất được mẫu in', e), True)
            return None
        self._bao(f'Đã xuất mẫu ra:\n{p}\n\nSửa trong Excel (giữ các chỗ trống {{…}}) rồi bấm "Thay thế bằng file Excel khác…".')
        return p

    def xuat_word(self, file=None):
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu thông số mẫu Word', str(Path.home() / 'Documents' / 'mau_word.json'),
                                                  'Thông số mẫu Word (*.json)')
            if not file:
                return None
        try:
            p = in_word.xuat_thong_so(file)
        except OSError as e:
            self._bao(chu_loi('Không xuất được thông số mẫu Word', e), True)
            return None
        self._bao(f'Đã xuất thông số mẫu Word:\n{p}\n\nSửa các giá trị cần đổi (lề mm, cỡ chữ pt, trích yếu…) rồi bấm "Nhập thông số mẫu Word…".')
        return p

    def nhap_word(self, file=None):
        if file is None:
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn file thông số mẫu Word', str(Path.home()), 'Thông số mẫu Word (*.json)')
            if not file:
                return None
        try:
            doi = in_word.nhap_thong_so(file)
        except (dia_phuong.LoiHoSo, OSError) as e:
            self._bao(chu_loi('Không nhập được thông số mẫu Word', e), True)
            return None
        self.nap()
        self._bao('Đã áp thông số mẫu Word - dùng ngay lần xuất / xem trước sau.\nMục đổi: ' + (', '.join(doi) or '(không có gì khác trước)'))
        return doi

    def khoi_phuc_word(self, xac_nhan=None) -> bool:
        if xac_nhan is None and not self.im_lang:
            xac_nhan = QMessageBox.question(self, TEN_UD, 'Bỏ thông số mẫu Word tùy chỉnh, dùng lại thông số chuẩn nhúng?') ==                 QMessageBox.StandardButton.Yes
        if xac_nhan is False:
            return False
        in_word.khoi_phuc_thong_so()
        self.nap()
        return True

    def khoi_phuc(self, xac_nhan=None) -> bool:
        ten = self.ten_chon()
        if ten is None:
            return False
        if xac_nhan is None and not self.im_lang:
            xac_nhan = QMessageBox.question(self, TEN_UD, 'Bỏ mẫu tùy chỉnh, in lại theo mẫu chuẩn gốc?') == \
                QMessageBox.StandardButton.Yes
        if xac_nhan is False:
            return False
        kq = in_an.khoi_phuc_mau(ten)
        self.nap()
        return kq

"""Hộp Quản lý Mẫu in & Bản in (menu Công cụ, Ctrl+Shift+M).

Từ 1.0.20 phần mềm KHÔNG đọc mẫu Excel nào: phương án chi tiết là bản Word nhúng sẵn (bố cục trong mã, quy cách là thông số hồ sơ
địa phương), bảng tổng hợp là Excel dựng hoàn toàn bằng mã (pabt/mau_bang_tong_hop.py). Hộp này chỉ còn quản lý THÔNG SỐ mẫu Word
(lề, cỡ chữ, trích yếu, thụt đầu dòng, độ hở gạch chân): xuất ra file .json để sửa, nhập lại, khôi phục thông số chuẩn - đổi khi có
quy định mới mà không cần cập nhật phần mềm. Logic ở in_word (xuat_thong_so, nhap_thong_so, khoi_phuc_thong_so, trang_thai_thong_so).
Không emoji (Windows 7).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout

from . import dia_phuong, in_word
from .thong_bao import TEN_UD, chu_loi


class HopQuanLyMauIn(QDialog):
    def __init__(self, parent=None, im_lang: bool = False):
        super().__init__(parent)
        self.im_lang = im_lang
        self.setWindowTitle('Quản lý Mẫu in & Bản in')
        self.resize(760, 260)
        lo = QVBoxLayout(self)
        gt = QLabel('Phần mềm in theo bộ mẫu nhúng sẵn, không đọc file mẫu Excel nào (máy mới cài vẫn in được, không lo mẫu bị sửa '
                    'sai hoặc chứa lệnh lạ). Phương án chi tiết, bổ sung, điều chỉnh là bản Word; bảng tổng hợp là Excel dựng bằng mã.')
        gt.setWordWrap(True)
        lo.addWidget(gt)
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
        from .giao_dien import KieuNut, ap_kieu_nut
        ap_kieu_nut(self.b_w_nhap, KieuNut.CHINH)
        ap_kieu_nut(self.b_w_xuat, KieuNut.PHU)
        for b in (self.b_w_xuat, self.b_w_nhap, self.b_w_khoi_phuc):
            hw.addWidget(b)
        hw.addStretch(1)
        dong = QPushButton('Đóng')
        dong.clicked.connect(self.accept)
        hw.addWidget(dong)
        lo.addStretch(1)
        lo.addLayout(hw)
        self.nap()

    def nap(self) -> None:
        tt = in_word.trang_thai_thong_so()
        self.lb_word.setText(f'Mẫu Word (phương án chi tiết, bổ sung, điều chỉnh): {tt}. Bố cục nhúng trong phần mềm; lề, cỡ chữ, trích yếu, '
                             f'thụt đầu dòng, độ hở gạch chân là thông số - đổi khi có quy định mới bằng "Nhập thông số mẫu Word…" '
                             f'hoặc gói .pabtcfg (Công cụ), không cần cập nhật phần mềm.')
        self.b_w_khoi_phuc.setEnabled(tt != 'Nhúng chuẩn')

    def _bao(self, chu: str, loi: bool = False) -> None:
        if self.im_lang:
            return
        (QMessageBox.warning if loi else QMessageBox.information)(self, TEN_UD, chu)

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
            xac_nhan = QMessageBox.question(self, TEN_UD, 'Bỏ thông số mẫu Word tùy chỉnh, dùng lại thông số chuẩn nhúng?') == \
                QMessageBox.StandardButton.Yes
        if xac_nhan is False:
            return False
        in_word.khoi_phuc_thong_so()
        self.nap()
        return True

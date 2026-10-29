"""Hộp Cài đặt > Giao diện (1.0.17, nền tảng giao diện 2.0): MẬT ĐỘ BẢNG (Gọn / Chuẩn / Thoáng - áp ngay), TÔNG NỀN (1.0.33: Sáng chuẩn /
Dịu mắt / Trắng tương phản - áp ngay) và TƯƠNG PHẢN CAO (theo Windows /
luôn bật / tắt - áp khi mở lại phần mềm). Logic ở chu_de (không Qt) và giao_dien.dat_mat_do."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QRadioButton,
                               QVBoxLayout)

from . import chu_de, giao_dien

GOI_Y_MAT_DO = {'gon': 'Dòng bảng thấp - xem được nhiều hộ hơn trên màn hình nhỏ (1366 x 768).',
                'chuan': 'Cân đối - mặc định.',
                'thoang': 'Dòng bảng cao - dễ bấm, dễ đọc trên màn hình lớn.'}


class HopGiaoDien(QDialog):
    def __init__(self, parent=None, im_lang: bool = False):
        super().__init__(parent)
        self.im_lang = im_lang
        self.setWindowTitle('Giao diện')
        lo = QVBoxLayout(self)
        nhom = QGroupBox('Mật độ bảng dữ liệu')
        hn = QVBoxLayout(nhom)
        self.nhom_mat_do = QButtonGroup(self)
        self.r_mat_do = {}
        hien = giao_dien.MAT_DO[0]
        for ten, (nhan, cao, _td) in chu_de.MAT_DO.items():
            r = QRadioButton(f'{nhan}  (dòng {cao} px) - {GOI_Y_MAT_DO[ten]}')
            r.setChecked(ten == hien)          # đặt trạng thái TRƯỚC khi nối tín hiệu: mở hộp không được tự đổi / lưu mật độ
            self.nhom_mat_do.addButton(r)
            self.r_mat_do[ten] = r
            r.toggled.connect(lambda dung, t=ten: dung and self.doi_mat_do(t))
            hn.addWidget(r)
        lo.addWidget(nhom)
        nhom_tn = QGroupBox('Tông nền bề mặt')                 # 1.0.33: áp ngay cho mọi cửa sổ đang mở
        hn = QVBoxLayout(nhom_tn)
        self.nhom_tong_nen = QButtonGroup(self)
        self.r_tong_nen = {}
        self.mau_xem = {}
        for ten, (nhan, nen, khung, vach, chu, _phu) in chu_de.TONG_NEN.items():
            r = QRadioButton(nhan)
            r.setChecked(ten == giao_dien.TONG_NEN[0])
            self.nhom_tong_nen.addButton(r)
            self.r_tong_nen[ten] = r
            r.toggled.connect(lambda dung, t=ten: dung and self.doi_tong_nen(t))
            xem = QLabel('Aa')                                   # 1.0.34: ô xem trước màu của tông (nền cửa sổ -> thẻ, chữ chính)
            xem.setFixedSize(44, 22)
            xem.setAlignment(Qt.AlignmentFlag.AlignCenter)
            xem.setStyleSheet(f'QLabel {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {nen}, stop:0.5 {nen}, '
                              f'stop:0.51 {khung}, stop:1 {khung}); color: {chu}; border: 1px solid {vach}; border-radius: 5px; '
                              'font-weight: 700; }')
            self.mau_xem[ten] = xem
            dong = QHBoxLayout()
            dong.addWidget(xem)
            dong.addWidget(r, 1)
            hn.addLayout(dong)
        lo.addWidget(nhom_tn)
        f = QFormLayout()
        self.cb_tuong_phan = QComboBox()
        cd = chu_de.doc(giao_dien.cai_dat_nho())
        for khoa, nhan in chu_de.TUONG_PHAN.items():
            self.cb_tuong_phan.addItem(nhan, khoa)
        self.cb_tuong_phan.setCurrentIndex(max(0, self.cb_tuong_phan.findData(cd['tuong_phan'])))
        self.cb_tuong_phan.setToolTip('Windows bật chủ đề tương phản cao (Cài đặt > Trợ năng): phần mềm dùng màu hệ thống thay cho màu riêng.')
        self.cb_tuong_phan.activated.connect(lambda *_: self.doi_tuong_phan(self.cb_tuong_phan.currentData()))
        f.addRow('Tương phản cao:', self.cb_tuong_phan)
        lo.addLayout(f)
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        self.lb.setProperty('vai', 'phu')
        lo.addWidget(self.lb)
        h = QHBoxLayout()
        h.addStretch(1)
        b = QPushButton('Đóng')
        b.clicked.connect(self.accept)
        h.addWidget(b)
        lo.addLayout(h)
        self._thong_bao()

    def _thong_bao(self, chu: str = '') -> None:
        hc = chu_de.tuong_phan_cao_windows()
        self.lb.setText((chu + '  ' if chu else '') + f'Windows hiện {"ĐANG" if hc else "không"} bật tương phản cao.')

    def doi_mat_do(self, ten: str) -> None:
        """Áp ngay mật độ cho mọi bảng đang mở và nhớ cho lần sau."""
        giao_dien.dat_mat_do(ten, ap_lai=True, luu=True)
        self._thong_bao('Đã áp mật độ bảng.')

    def doi_tong_nen(self, ten: str) -> None:
        """Áp ngay tông nền cho mọi cửa sổ đang mở và nhớ cho lần sau."""
        giao_dien.dat_tong_nen(ten, luu=True)
        self._thong_bao('Đã áp tông nền.')

    def doi_tuong_phan(self, khoa: str) -> None:
        chu_de.ghi(giao_dien.cai_dat_nho(), tuong_phan=khoa)
        self._thong_bao('Tương phản cao có hiệu lực khi mở lại phần mềm.')

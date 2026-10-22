"""Hộp Cài đặt > Giao diện (1.0.17, nền tảng giao diện 2.0): MẬT ĐỘ BẢNG (Gọn / Chuẩn / Thoáng - áp ngay) và TƯƠNG PHẢN CAO (theo Windows /
luôn bật / tắt - áp khi mở lại phần mềm). Logic ở chu_de (không Qt) và giao_dien.dat_mat_do."""
from __future__ import annotations

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

    def doi_tuong_phan(self, khoa: str) -> None:
        chu_de.ghi(giao_dien.cai_dat_nho(), tuong_phan=khoa)
        self._thong_bao('Tương phản cao có hiệu lực khi mở lại phần mềm.')

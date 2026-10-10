"""Hộp thoại "Cập nhật phần mềm": cài gói cập nhật .pabtcn (sửa lỗi, tính năng mới) hoặc gỡ về bản cài gốc."""
from __future__ import annotations
import sys

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QVBoxLayout)

from . import cap_nhat

TIEU_DE = 'Cập nhật phần mềm PABT'


class HopCapNhat(QDialog):
    im_lang = False          # kiểm thử: không hiện hộp thông báo

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(TIEU_DE)
        self.resize(620, 300)
        lo = QVBoxLayout(self)
        gt = QLabel('Gói cập nhật (file <b>.pabtcn</b>) dùng để sửa lỗi, bổ sung tính năng mà <b>không phải cài lại</b> '
                    'phần mềm. Dữ liệu dự án và bộ đơn giá đã cập nhật được giữ nguyên. Bản cập nhật có hiệu lực khi mở lại '
                    'phần mềm; nếu bản cập nhật lỗi, phần mềm tự quay về bản cài gốc.')
        gt.setWordWrap(True)
        lo.addWidget(gt)
        self.lb = QLabel()
        self.lb.setWordWrap(True)
        self.lb.setProperty('vai', 'nhan')
        lo.addWidget(self.lb)
        lo.addStretch()
        h = QHBoxLayout()
        self.b_cai = QPushButton('Cập nhật từ file…')
        self.b_cai.clicked.connect(lambda: self.cai_file())
        self.b_go = QPushButton('Gỡ bản cập nhật')
        self.b_go.clicked.connect(lambda: self.go_cap_nhat())
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        h.addWidget(self.b_cai)
        h.addWidget(self.b_go)
        h.addStretch()
        h.addWidget(b_dong)
        lo.addLayout(h)
        self.hien()

    def hien(self):
        tt = cap_nhat.trang_thai()
        dong = [f'Phiên bản đang chạy: <b>{tt["dang_chay"]}</b> &nbsp; (bản cài gốc {tt["ban_goc"]})']
        if tt['da_cai']:
            dong.append(f'Bản cập nhật đã cài: <b>{tt["da_cai"]}</b>' + (f' - ngày {tt["ngay"]}' if tt['ngay'] else ''))
            if tt['mo_ta']:
                dong.append('Nội dung: ' + tt['mo_ta'])
            if tt['da_cai'] != tt['dang_chay'] and not tt['loi']:
                dong.append('<span style="color:#E65100">Mở lại phần mềm để dùng bản cập nhật này.</span>')
        else:
            dong.append('Chưa cài bản cập nhật nào.')
        if tt['loi']:
            dong.append('<span style="color:#C62828">Bản cập nhật bị tắt do lỗi: ' + tt['loi'].splitlines()[0] + '</span>')
        self.lb.setText('<br>'.join(dong))
        self.b_go.setEnabled(bool(tt['da_cai']))

    def _bao(self, loai, chu):
        if not self.im_lang:
            getattr(QMessageBox, loai)(self, TIEU_DE, chu)

    def cai_file(self, p=None):
        if p is None:
            p, _ = QFileDialog.getOpenFileName(self, 'Chọn gói cập nhật PABT', '', f'Gói cập nhật PABT (*{cap_nhat.DUOI})')
            if not p:
                return None
        try:
            # luồng nền: đọc, kiểm tra SHA-256 từng file, nạp thử - cửa sổ không "Không phản hồi"
            from .giao_dien import chay_nen
            m = chay_nen(self, lambda: cap_nhat.cai(p), 'Đang kiểm tra và cài gói cập nhật…')
        except cap_nhat.LoiCapNhat as e:
            self._bao('warning', str(e))
            return None
        self.hien()
        if not self.im_lang:
            chu = f'Đã cài bản cập nhật {m["phien_ban"]}.' + (f'\n{m["mo_ta"]}' if m.get('mo_ta') else '')
            if QMessageBox.question(self, TIEU_DE, chu + '\n\nMở lại phần mềm ngay để dùng bản mới?') == \
                    QMessageBox.StandardButton.Yes:
                self.khoi_dong_lai()
        return m

    def go_cap_nhat(self, xac_nhan=True):
        if xac_nhan and not self.im_lang and QMessageBox.question(
                self, TIEU_DE, 'Gỡ bản cập nhật, quay về bản cài gốc từ lần mở phần mềm sau?') != QMessageBox.StandardButton.Yes:
            return False
        kq = cap_nhat.go()
        self.hien()
        self._bao('information', 'Đã gỡ bản cập nhật. Mở lại phần mềm để dùng bản cài gốc.')
        return kq

    def khoi_dong_lai(self):
        if not getattr(sys, 'frozen', False):
            self._bao('information', 'Đang chạy từ mã nguồn: hãy mở lại phần mềm.')
            return
        if self.parent() is not None:
            self.parent().close()
        QProcess.startDetached(sys.executable, [])
        QApplication.quit()

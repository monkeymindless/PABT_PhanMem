"""Hộp "Nhận kết quả kiểm đếm từ điện thoại qua Wi-Fi" (phương án đột phá 5, 30/10/2026) - mở từ hộp Phiếu kiểm đếm thực địa.

Mở hộp = bật máy chủ nhận (nhan_wifi.MayNhan) trên mạng nội bộ; đóng hộp = tắt. Hiện mã QR + địa chỉ để điện thoại mở bằng trình duyệt;
file .json nhận về liệt kê trong bảng, người dùng bấm Nhập (phieu_kiem_dem qua hàm nhap của hộp Phiếu kiểm đếm - kiểm đủ, hỏi thêm hộ mới)."""
from __future__ import annotations
from .giao_dien import dat_kieu_theo_tong  # noqa: E402  (kiểu riêng đổi theo tông nền)

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from . import nhan_wifi
from .ma_qr import ma_qr

O_QR = 6            # điểm ảnh mỗi ô QR (thu theo cỡ ô hiện)
COT = ['Giờ nhận', 'File', 'Cỡ', 'Trạng thái']


def anh_qr(chu: str, o_px: int = O_QR, le: int = 4) -> QPixmap:
    """Ảnh mã QR (nền trắng, lề 4 ô)."""
    g = ma_qr(chu)
    n = len(g) + 2 * le
    img = QImage(n, n, QImage.Format.Format_RGB32)
    img.fill(QColor('#FFFFFF'))
    den = QColor('#0F172A').rgb()
    for y, h in enumerate(g):
        for x, v in enumerate(h):
            if v:
                img.setPixel(x + le, y + le, den)
    return QPixmap.fromImage(img.scaled(n * o_px, n * o_px))


class HopNhanWifi(QDialog):
    im_lang = False

    def __init__(self, parent=None, nhap=None, im_lang: bool = False):
        super().__init__(parent)
        self.nhap, self.im_lang = nhap, im_lang
        self.may = None
        self.ds = []                                    # [dict(file, ten, co, luc, tt)]
        self.setWindowTitle('Nhận kết quả kiểm đếm từ điện thoại qua Wi-Fi')
        self.resize(900, 560)
        self.lb_qr = QLabel()
        self.lb_qr.setFixedSize(230, 230)
        self.lb_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb_url = QLabel('')
        self.lb_url.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        dat_kieu_theo_tong(self.lb_url, 'QLabel { font-size: 16px; font-weight: 600; color: #1E3A5F; }')
        self.cb_ip = QComboBox()
        self.cb_ip.setToolTip('Địa chỉ mạng của máy tính - chọn địa chỉ cùng mạng Wi-Fi với điện thoại')
        self.cb_ip.activated.connect(lambda _: self.bat_dau(self.cb_ip.currentData()))
        hd = QLabel('1. Điện thoại và máy tính dùng chung một mạng Wi-Fi (hoặc điện thoại phát Wi-Fi cho máy tính).\n'
                    '2. Mở camera điện thoại quét mã QR (hoặc gõ địa chỉ bên dưới vào trình duyệt).\n'
                    '3. Bấm "Bấm để chọn file .json" -> chọn file kết quả đã xuất từ LARC Mobile -> "Gửi về máy tính".\n'
                    '4. File nhận về hiện ở bảng dưới -> bấm "Nhập vào dự án".\n\n'
                    'Chỉ nhận trong lúc hộp này đang mở, chỉ nhận file .json. Lần đầu, Windows có thể hỏi cho phép chương trình '
                    'nhận kết nối: chọn "Mạng riêng" (Private) rồi Cho phép.')
        hd.setWordWrap(True)
        phai = QVBoxLayout()
        phai.addWidget(hd)
        h_ip = QHBoxLayout()
        h_ip.addWidget(QLabel('Địa chỉ:'))
        h_ip.addWidget(self.cb_ip, 1)
        phai.addLayout(h_ip)
        phai.addWidget(self.lb_url)
        phai.addStretch(1)
        tren = QHBoxLayout()
        tren.addWidget(self.lb_qr)
        tren.addLayout(phai, 1)
        self.bang = QTableWidget(0, len(COT))
        self.bang.setHorizontalHeaderLabels(COT)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        for c, w in enumerate((80, 300, 80)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.cellDoubleClicked.connect(lambda r, _c: self.nhap_dong([r]))
        self.lb_tt = QLabel('')
        self.lb_tt.setWordWrap(True)
        self.b_nhap = QPushButton('Nhập file đã chọn vào dự án')
        self.b_nhap.clicked.connect(lambda: self.nhap_dong(sorted({i.row() for i in self.bang.selectedIndexes()})))
        self.b_tat_ca = QPushButton('Nhập mọi file chưa nhập')
        self.b_tat_ca.clicked.connect(lambda: self.nhap_dong([r for r, x in enumerate(self.ds) if x['tt'] == 'moi' and x.get('ma_hoa', True)]))
        b_tm = QPushButton('Mở thư mục nhận')
        b_tm.clicked.connect(self._mo_thu_muc)
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        hn = QHBoxLayout()
        for b in (self.b_nhap, self.b_tat_ca, b_tm):
            hn.addWidget(b)
        hn.addStretch(1)
        hn.addWidget(b_dong)
        lo = QVBoxLayout(self)
        lo.addLayout(tren)
        lo.addWidget(self.bang, 1)
        lo.addWidget(self.lb_tt)
        lo.addLayout(hn)
        for b in (self.b_nhap, self.b_tat_ca):
            b.setEnabled(nhap is not None)
        self.nhip = QTimer(self)
        self.nhip.setInterval(400)
        self.nhip.timeout.connect(self.lay_file_moi)
        ds_ip = nhan_wifi.dia_chi_noi_bo()
        for ip in ds_ip:
            self.cb_ip.addItem(ip, ip)
        self.bat_dau(ds_ip[0] if ds_ip else None)

    def bat_dau(self, ip=None) -> str:
        """Bật (bật lại khi đổi địa chỉ) máy chủ nhận. Trả địa chỉ hoặc '' (không có mạng nội bộ)."""
        if self.may is not None:
            self.may.dung()
        thu_muc = self.may.thu_muc if self.may is not None else None
        self.may = nhan_wifi.MayNhan(ip, thu_muc)
        try:
            url = self.may.bat_dau()
        except nhan_wifi.LoiNhanWifi as e:
            self.lb_url.setText('')
            self.lb_qr.clear()
            self.lb_tt.setText(str(e))
            return ''
        self.lb_url.setText(url)
        self.lb_qr.setPixmap(anh_qr(self.may.url_qr or url))   # 1.0.55: QR mang khóa mã hóa (#k=…); chữ hiện không kèm khóa
        self.lb_tt.setText('Đang chờ điện thoại gửi file…')
        self.nhip.start()
        return url

    def lay_file_moi(self) -> int:
        """Lấy các file máy chủ vừa nhận (gọi theo nhịp). Trả số file mới."""
        if self.may is None:
            return 0
        n = 0
        while True:
            try:
                x = self.may.hang.get_nowait()
            except Exception:                           # noqa: BLE001 - queue.Empty
                break
            self.ds.append(dict(x, tt='moi', ket_qua='Chưa nhập'))
            n += 1
        if n:
            self._ve()
            self.lb_tt.setText(f'Đã nhận {len(self.ds)} file. Bấm "Nhập mọi file chưa nhập" để thêm vào phương án các hộ.')
        return n

    def _ve(self) -> None:
        self.bang.setRowCount(len(self.ds))
        for r, x in enumerate(self.ds):
            for c, chu in enumerate((x['luc'], x['file'].name + ('' if x.get('ma_hoa', True) else ' (KHÔNG mã hóa: chọn dòng rồi nhập nếu chắc chắn)'), f'{max(1, x["co"] // 1024):,} KB'.replace(',', '.'), x['ket_qua'])):
                it = QTableWidgetItem(chu)
                if c == 3:
                    it.setForeground(QColor({'moi': '#475569', 'xong': '#166534', 'loi': '#B91C1C'}[x['tt']]))
                self.bang.setItem(r, c, it)

    def nhap_dong(self, ds_dong: list) -> int:
        """Nhập các dòng (file) vào dự án qua hàm nhap của hộp Phiếu kiểm đếm. Trả số file nhập được."""
        if self.nhap is None:
            return 0
        n = 0
        for r in ds_dong:
            if not 0 <= r < len(self.ds) or self.ds[r]['tt'] == 'xong':
                continue
            x = self.ds[r]
            kq = self.nhap(str(x['file']))
            if kq is None:
                x['tt'], x['ket_qua'] = 'loi', 'Không nhập được - xem thông báo trong hộp Phiếu kiểm đếm'
            else:
                x['tt'], x['ket_qua'] = 'xong', f'Đã nhập: {kq.get("so_dong", 0)} dòng, {kq.get("so_ho", 0)} hộ'
                n += 1
        self._ve()
        return n

    def _mo_thu_muc(self) -> None:
        if self.may is not None and not self.im_lang:
            self.may.thu_muc.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.may.thu_muc)))

    def done(self, r):
        self.nhip.stop()
        if self.may is not None:
            self.may.dung()
        super().done(r)

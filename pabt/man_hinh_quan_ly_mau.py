"""Hộp Thiết lập trang (menu Công cụ "Quản lý Mẫu in & Bản in…", Ctrl+Shift+M; liên kết "Thiết lập trang" của bảng In / Xuất).

1.1.03 (người dùng 11/11/2026): bố cục ba thẻ như hộp Page Setup của Word - Lề | Giấy | Bố trí - thay hộp chỉ có ba nút xuất / nhập
file thông số. Phần mềm vẫn in theo bộ mẫu nhúng (phương án chi tiết, bổ sung, điều chỉnh là bản Word dựng bằng mã; bảng tổng hợp là
Excel dựng bằng mã): hộp này sửa THÔNG SỐ của mẫu ở hồ sơ địa phương của máy (ban_in.mau_word: lề, khổ giấy, hướng giấy, cỡ chữ, thụt
đầu dòng, độ hở gạch chân, tự co giãn cho khít trang; ban_in.le_trang.tong_hop: lề bảng tổng hợp) - không đổi bố cục, không cần bản cập
nhật phần mềm. Bấm OK: kiểm tra, ghi vào hồ sơ máy, dùng ngay cho lần xem trước / xuất sau. Xuất / nhập / khôi phục thông số như trước
(in_word.xuat_thong_so, nhap_thong_so, khoi_phuc_thong_so). Không emoji (Windows 7).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QLocale, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QTabWidget, QToolButton, QVBoxLayout, QWidget)

from . import dia_phuong, in_word
from .thong_bao import TEN_UD, chu_loi

KHO_MM = {'A4': (210.0, 297.0), 'A3': (297.0, 420.0)}           # (ngắn, dài) mm
AP_DUNG = (('word', 'Phương án chi tiết (Word)'), ('bth', 'Bảng tổng hợp (Excel)'), ('ca_hai', 'Toàn bộ tài liệu'))
CO_CHU_NHANH = (('co_quan', 'Cơ quan'), ('quoc_hieu', 'Quốc hiệu'), ('bang', 'Bảng tính toán'), ('ghi_chu', 'Ghi chú'), ('chu_ky', 'Chữ ký'))
LE_BTH = (('trai', 'left'), ('phai', 'right'), ('tren', 'top'), ('duoi', 'bottom'))
INCH_MM = 25.4


def _o_cm(gia_tri_cm: float, toi_da: float = 6.0, buoc: float = 0.1) -> QDoubleSpinBox:
    """Ô số đo cm: một chữ số lẻ, dấu phẩy thập phân kiểu Việt Nam ("1,9 cm"), bước 0,1 cm."""
    o = QDoubleSpinBox()
    o.setLocale(QLocale(QLocale.Language.Vietnamese, QLocale.Country.Vietnam))
    o.setDecimals(1)
    o.setRange(0.0, toi_da)
    o.setSingleStep(buoc)
    o.setSuffix(' cm')
    o.setValue(float(gia_tri_cm))
    o.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return o


def _o_pt(gia_tri: float, tu: float, den: float, buoc: float = 0.5, duoi: str = ' pt') -> QDoubleSpinBox:
    o = QDoubleSpinBox()
    o.setLocale(QLocale(QLocale.Language.Vietnamese, QLocale.Country.Vietnam))
    o.setDecimals(1)
    o.setRange(tu, den)
    o.setSingleStep(buoc)
    o.setSuffix(duoi)
    o.setValue(float(gia_tri))
    o.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return o


class _KhungXemTruocTrang(QWidget):
    """Tờ giấy thu nhỏ: khung giấy trắng trên nền xám, đường lề nét đứt và các vạch chữ giả lập trong vùng in - vẽ lại ngay khi đổi
    lề, khổ giấy, hướng giấy (như ô Preview của hộp Page Setup)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rong_mm, self.cao_mm = 210.0, 297.0
        self.le_mm = {'trai': 15.0, 'phai': 10.0, 'tren': 10.0, 'duoi': 10.0}
        self.setMinimumSize(170, 200)
        self.setAccessibleName('Xem trước trang giấy')

    def sizeHint(self) -> QSize:
        return QSize(200, 240)

    def dat(self, rong_mm: float, cao_mm: float, le_mm: dict) -> None:
        self.rong_mm, self.cao_mm, self.le_mm = float(rong_mm), float(cao_mm), dict(le_mm)
        self.update()

    def vung_in(self) -> tuple:
        """(rộng, cao) mm của vùng in sau khi trừ lề - để kiểm thử và ghi chú dưới hình."""
        return (self.rong_mm - self.le_mm['trai'] - self.le_mm['phai'], self.cao_mm - self.le_mm['tren'] - self.le_mm['duoi'])

    def paintEvent(self, _e) -> None:
        from .giao_dien import TOKEN
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            p.fillRect(self.rect(), self.palette().mid())
            dem = 10.0
            he = min((self.width() - 2 * dem) / max(1.0, self.rong_mm), (self.height() - 2 * dem) / max(1.0, self.cao_mm))
            w, h = self.rong_mm * he, self.cao_mm * he
            x0, y0 = (self.width() - w) / 2, (self.height() - h) / 2
            giay = QRectF(x0, y0, w, h)
            p.fillRect(giay.translated(2, 2), self.palette().dark())            # bóng tờ giấy
            p.fillRect(giay, QColor(Qt.GlobalColor.white))                     # giấy in luôn trắng, không theo tông nền
            p.setPen(QPen(QColor(Qt.GlobalColor.darkGray), 1))
            p.drawRect(giay)
            vung = QRectF(x0 + self.le_mm['trai'] * he, y0 + self.le_mm['tren'] * he,
                          max(1.0, w - (self.le_mm['trai'] + self.le_mm['phai']) * he),
                          max(1.0, h - (self.le_mm['tren'] + self.le_mm['duoi']) * he))
            but = QPen(QColor(TOKEN['nhan']), 1, Qt.PenStyle.DashLine)
            p.setPen(but)
            p.drawRect(vung)
            p.setPen(QPen(QColor(Qt.GlobalColor.gray), 1))
            y = vung.top() + 4
            k = 0
            while y < vung.bottom() - 2:                                        # vạch chữ giả lập: dòng cuối mỗi đoạn ngắn hơn
                phai = vung.right() - (vung.width() * 0.4 if k % 5 == 4 else 2)
                p.drawLine(int(vung.left() + 2), int(y), int(max(vung.left() + 3, phai)), int(y))
                y += 4
                k += 1
        finally:
            p.end()


class HopQuanLyMauIn(QDialog):
    """Hộp Thiết lập trang. Tên lớp và các hàm xuat_word / nhap_word / khoi_phuc_word giữ từ bản trước (nơi gọi, kiểm thử cũ)."""

    def __init__(self, parent=None, im_lang: bool = False):
        super().__init__(parent)
        self.im_lang = im_lang
        self.da_ap = []                                 # các mục đã đổi ở lần bấm OK gần nhất
        self.setWindowTitle('Thiết lập trang')
        self.resize(660, 470)
        lo = QVBoxLayout(self)
        self.the = QTabWidget()
        self.the.addTab(self._the_le(), 'Lề')
        self.the.addTab(self._the_giay(), 'Giấy')
        self.the.addTab(self._the_bo_tri(), 'Bố trí')
        lo.addWidget(self.the, 1)
        self.lb_word = QLabel()
        self.lb_word.setWordWrap(True)
        lo.addWidget(self.lb_word)
        from .giao_dien import KieuNut, ap_kieu_nut
        hn = QHBoxLayout()
        self.b_w_xuat = QPushButton('Xuất thông số…')
        self.b_w_nhap = QPushButton('Nhập thông số…')
        self.b_w_khoi_phuc = QPushButton('Khôi phục thông số chuẩn')
        self.b_w_xuat.setToolTip('Ghi thông số mẫu Word đang dùng ra file .json (đưa cho máy khác nhập)')
        self.b_w_nhap.setToolTip('Nhập file thông số mẫu Word .json (do nút Xuất tạo): áp dụng ngay')
        self.b_w_khoi_phuc.setToolTip('Bỏ thông số tùy chỉnh của máy này, dùng lại bộ chuẩn nhúng trong phần mềm')
        self.b_w_xuat.clicked.connect(lambda: self.xuat_word())
        self.b_w_nhap.clicked.connect(lambda: self.nhap_word())
        self.b_w_khoi_phuc.clicked.connect(lambda: self.khoi_phuc_word())
        for b in (self.b_w_xuat, self.b_w_nhap, self.b_w_khoi_phuc):
            ap_kieu_nut(b, KieuNut.PHU)
            hn.addWidget(b)
        hn.addStretch(1)
        self.b_ok = QPushButton('OK')
        self.b_ok.setDefault(True)
        self.b_ok.setToolTip('Ghi thông số và dùng ngay cho lần xem trước / xuất sau')
        self.b_ok.clicked.connect(lambda: self.dong_y())
        ap_kieu_nut(self.b_ok, KieuNut.CHINH)
        self.b_huy = QPushButton('Hủy bỏ')
        self.b_huy.clicked.connect(self.reject)
        hn.addWidget(self.b_ok)
        hn.addWidget(self.b_huy)
        lo.addLayout(hn)
        self._dang_nap = False
        self.nap()

    # ------------------------------------------------ dựng ba thẻ
    def _the_le(self) -> QWidget:
        w = QWidget()
        lo = QHBoxLayout(w)
        trai = QVBoxLayout()
        g_le = QGroupBox('Lề')
        f = QFormLayout(g_le)
        self.o_le = {k: _o_cm(1.0) for k in ('tren', 'duoi', 'trai', 'phai')}
        for k, nhan in (('tren', 'Trên:'), ('duoi', 'Dưới:'), ('trai', 'Trái:'), ('phai', 'Phải:')):
            self.o_le[k].setAccessibleName('Lề ' + nhan.rstrip(':').lower())
            self.o_le[k].valueChanged.connect(lambda _v: self._doi())
            f.addRow(nhan, self.o_le[k])
        trai.addWidget(g_le)
        g_huong = QGroupBox('Hướng')
        hh = QHBoxLayout(g_huong)
        self.b_doc = self._nut_huong('Dọc', False)
        self.b_ngang = self._nut_huong('Ngang', True)
        self.b_doc.clicked.connect(lambda: self.dat_huong(False))
        self.b_ngang.clicked.connect(lambda: self.dat_huong(True))
        hh.addWidget(self.b_doc)
        hh.addWidget(self.b_ngang)
        hh.addStretch(1)
        trai.addWidget(g_huong)
        fa = QFormLayout()
        self.cb_ap = QComboBox()
        for khoa, chu in AP_DUNG:
            self.cb_ap.addItem(chu, khoa)
        self.cb_ap.setToolTip('Lề đang sửa thuộc tài liệu nào. Bảng tổng hợp luôn in A3 ngang - chỉ đổi được lề.')
        self.cb_ap.currentIndexChanged.connect(lambda _i: self._doi_ap_dung())
        fa.addRow('Áp dụng cho:', self.cb_ap)
        trai.addLayout(fa)
        trai.addStretch(1)
        lo.addLayout(trai, 1)
        g_xem = QGroupBox('Xem trước')
        vx = QVBoxLayout(g_xem)
        self.xem = _KhungXemTruocTrang()
        vx.addWidget(self.xem, 1)
        self.lb_vung = QLabel()
        self.lb_vung.setWordWrap(True)
        vx.addWidget(self.lb_vung)
        lo.addWidget(g_xem, 1)
        return w

    def _nut_huong(self, chu: str, ngang: bool) -> QToolButton:
        from PySide6.QtGui import QIcon, QPixmap
        b = QToolButton()
        b.setText(chu)
        b.setCheckable(True)
        b.setAutoExclusive(True)
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        b.setToolTip('Giấy ' + ('ngang' if ngang else 'dọc'))
        pm = QPixmap(44, 44)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        try:
            r = QRectF(6, 12, 32, 22) if ngang else QRectF(11, 5, 22, 32)
            p.fillRect(r, QColor(Qt.GlobalColor.white))
            p.setPen(QPen(QColor(Qt.GlobalColor.darkGray), 1))
            p.drawRect(r)
            for i in range(3):
                y = r.top() + 6 + i * 5
                p.drawLine(int(r.left() + 4), int(y), int(r.right() - 4), int(y))
        finally:
            p.end()
        b.setIcon(QIcon(pm))
        b.setIconSize(QSize(44, 44))
        b.setMinimumWidth(76)
        return b

    def _the_giay(self) -> QWidget:
        w = QWidget()
        lo = QVBoxLayout(w)
        g = QGroupBox('Khổ giấy')
        f = QFormLayout(g)
        self.cb_kho = QComboBox()
        self.cb_kho.addItem('A4 (210 x 297 mm)', 'A4')
        self.cb_kho.addItem('A3 (297 x 420 mm)', 'A3')
        self.cb_kho.currentIndexChanged.connect(lambda _i: self._doi())
        f.addRow('Khổ giấy:', self.cb_kho)
        self.lb_rong, self.lb_cao = QLabel(), QLabel()
        f.addRow('Rộng:', self.lb_rong)
        f.addRow('Cao:', self.lb_cao)
        lo.addWidget(g)
        self.lb_giay = QLabel('Khổ giấy và hướng giấy ở đây là của phương án chi tiết, bổ sung, điều chỉnh (bản Word). Bảng tổng hợp luôn là A3 '
                              'ngang. Khổ giấy của máy in khi in ra chọn ở dòng "Khổ giấy" của bảng In.')
        self.lb_giay.setWordWrap(True)
        lo.addWidget(self.lb_giay)
        lo.addStretch(1)
        return w

    def _the_bo_tri(self) -> QWidget:
        w = QWidget()
        lo = QVBoxLayout(w)
        g = QGroupBox('Dàn trang dọc')
        vg = QVBoxLayout(g)
        self.o_co_gian = QCheckBox('Tự co giãn dòng và đoạn cho khít trang (không hở chân trang, giữ nguyên lề)')
        self.o_co_gian.setToolTip('Bật: phương án tràn ít sang trang cuối được thu gọn về trang trước; phương án nhiều trang được giãn đều '
                                  'cho khung bảng xuống sát lề dưới. Lề và bề rộng bảng không đổi. Tắt: bố cục cố định như bản 1.1.02.')
        self.o_co_gian.toggled.connect(lambda _b: self._doi())
        vg.addWidget(self.o_co_gian)
        lo.addWidget(g)
        g2 = QGroupBox('Cỡ chữ và khoảng cách')
        f = QFormLayout(g2)
        self.o_co = {}
        for khoa, nhan in CO_CHU_NHANH:
            self.o_co[khoa] = _o_pt(13, 6, 24)
            self.o_co[khoa].setAccessibleName('Cỡ chữ ' + nhan.lower())
            f.addRow(nhan + ':', self.o_co[khoa])
        self.o_thut = _o_cm(1.0, 3.0)
        self.o_thut.setDecimals(2)                       # mặc định 0,85 cm: một chữ số lẻ sẽ làm tròn mất nửa mm khi bấm OK
        self.o_thut.setAccessibleName('Thụt đầu dòng')
        f.addRow('Thụt đầu dòng:', self.o_thut)
        self.o_ho = _o_pt(2, 0, 8, 1.0)
        self.o_ho.setDecimals(0)
        self.o_ho.setAccessibleName('Độ hở gạch chân')
        f.addRow('Độ hở gạch chân:', self.o_ho)
        from PySide6.QtWidgets import QSpinBox
        self.o_dong_ky = QSpinBox()                      # 1.1.07: khoảng trống ký tên, đóng dấu
        self.o_dong_ky.setRange(in_word.DONG_KY_MIN, in_word.DONG_KY_MAX)
        self.o_dong_ky.setSuffix(' dòng')
        self.o_dong_ky.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)     # thẳng cột với các ô số trên
        self.o_dong_ky.setAccessibleName('Khoảng trống ký tên')
        self.o_dong_ky.setToolTip('Số dòng trống giữa chức danh (LẬP BIỂU, KIỂM TRA, chức vụ) và họ tên người ký - chỗ ký và đóng dấu')
        f.addRow('Khoảng trống ký tên:', self.o_dong_ky)
        lo.addWidget(g2)
        lo.addStretch(1)
        return w

    # ------------------------------------------------ nạp / đọc thông số
    def nap(self) -> None:
        """Điền các ô từ thông số đang dùng (hồ sơ địa phương)."""
        self._dang_nap = True
        try:
            mw = in_word.thong_so_mau()
            self._le_word = {k: float(v) for k, v in mw['le_mm'].items()}
            self._le_bth = self._doc_le_bth()
            self.cb_kho.setCurrentIndex(max(0, self.cb_kho.findData(str(mw.get('kho_giay', 'A4')).upper())))
            ngang = str(mw.get('huong_giay', 'doc')) == 'ngang'
            self.b_ngang.setChecked(ngang)
            self.b_doc.setChecked(not ngang)
            self.o_co_gian.setChecked(bool(mw.get('tu_co_gian', True)))
            for khoa, o in self.o_co.items():
                o.setValue(float(mw['co_chu'][khoa]))
            self.o_thut.setValue(float(mw['thut_dau_dong_mm']) / 10)
            self.o_ho.setValue(float(mw['gach_chan_ho_pt']))
            try:
                self.o_dong_ky.setValue(int(mw.get('dong_ky', in_word.DONG_KY_MAC_DINH)))
            except (TypeError, ValueError):
                self.o_dong_ky.setValue(in_word.DONG_KY_MAC_DINH)
            self._dien_le()
        finally:
            self._dang_nap = False
        tt = in_word.trang_thai_thong_so()
        self.lb_word.setText(f'Mẫu in nhúng trong phần mềm ({tt}). Thông số lưu ở hồ sơ của máy này; đưa sang máy khác bằng '
                             '"Xuất thông số…" / "Nhập thông số…" hoặc gói .pabtcfg.')
        self.b_w_khoi_phuc.setEnabled(tt != 'Nhúng chuẩn' or self._le_bth != self._le_bth_chuan())
        self._ve_xem_truoc()

    @staticmethod
    def _le_bth_chuan() -> dict:
        le = (dia_phuong.mac_dinh()['ban_in'].get('le_trang') or {}).get('tong_hop') or {}
        return {k: round(float(le.get(ten, 0.5)) * INCH_MM, 1) for k, ten in LE_BTH}

    def _doc_le_bth(self) -> dict:
        le = (dia_phuong.lay('ban_in.le_trang') or {}).get('tong_hop') or {}
        chuan = self._le_bth_chuan()
        return {k: round(float(le[ten]) * INCH_MM, 1) if isinstance(le.get(ten), (int, float)) else chuan[k] for k, ten in LE_BTH}

    def tai_lieu(self) -> str:
        """'word' / 'bth' / 'ca_hai' - mục "Áp dụng cho"."""
        return self.cb_ap.currentData() or 'word'

    def _dien_le(self) -> None:
        le = self._le_bth if self.tai_lieu() == 'bth' else self._le_word
        cu, self._dang_nap = self._dang_nap, True
        try:
            for k, o in self.o_le.items():
                o.setValue(float(le[k]) / 10)
        finally:
            self._dang_nap = cu
        chi_bth = self.tai_lieu() == 'bth'
        for b in (self.b_doc, self.b_ngang):
            b.setEnabled(not chi_bth)

    def _doi_ap_dung(self) -> None:
        if self._dang_nap:
            return
        self._dien_le()
        self._ve_xem_truoc()

    def _doi(self) -> None:
        """Một ô vừa đổi: ghi lề vào bản nháp của tài liệu đang chọn, vẽ lại tờ giấy."""
        if self._dang_nap:
            return
        le = {k: round(o.value() * 10, 1) for k, o in self.o_le.items()}
        td = self.tai_lieu()
        if td in ('word', 'ca_hai'):
            self._le_word = dict(le)
        if td in ('bth', 'ca_hai'):
            self._le_bth = dict(le)
        self._ve_xem_truoc()

    def dat_huong(self, ngang: bool) -> None:
        self.b_ngang.setChecked(bool(ngang))
        self.b_doc.setChecked(not ngang)
        self._doi()

    def kho_trang_mm(self) -> tuple:
        """(rộng, cao) mm của tờ giấy đang xem trước: bảng tổng hợp A3 ngang; bản Word theo khổ + hướng đang chọn."""
        if self.tai_lieu() == 'bth':
            return KHO_MM['A3'][1], KHO_MM['A3'][0]
        ngan, dai = KHO_MM[self.cb_kho.currentData() or 'A4']
        return (dai, ngan) if self.b_ngang.isChecked() else (ngan, dai)

    def _ve_xem_truoc(self) -> None:
        rong, cao = self.kho_trang_mm()
        le = self._le_bth if self.tai_lieu() == 'bth' else self._le_word
        self.xem.dat(rong, cao, le)
        vr, vc = self.xem.vung_in()
        from .tien import so_vn
        from decimal import Decimal

        def cm(mm):
            return so_vn(Decimal(str(round(mm / 10, 1))))
        self.lb_vung.setText(f'Giấy {cm(rong)} x {cm(cao)} cm, vùng in {cm(vr)} x {cm(vc)} cm.')
        ngan, dai = KHO_MM[self.cb_kho.currentData() or 'A4']
        ng = self.b_ngang.isChecked()
        self.lb_rong.setText(f'{cm(dai if ng else ngan)} cm')
        self.lb_cao.setText(f'{cm(ngan if ng else dai)} cm')

    def thong_so(self) -> dict:
        """Thông số mẫu Word theo các ô đang hiện (bản đầy đủ - chưa ghi)."""
        mw = in_word.thong_so_mau()
        mw['le_mm'] = {k: (int(v) if float(v).is_integer() else round(float(v), 1)) for k, v in self._le_word.items()}
        # ba mục của 1.1.03: hồ sơ đơn vị soạn từ bản trước chưa có - chỉ ghi khi khác mặc định (mở hộp rồi bấm OK không đổi gì)
        for khoa, gt, mac_dinh in (('kho_giay', self.cb_kho.currentData() or 'A4', 'A4'),
                                   ('huong_giay', 'ngang' if self.b_ngang.isChecked() else 'doc', 'doc'),
                                   ('tu_co_gian', self.o_co_gian.isChecked(), True),
                                   ('dong_ky', self.o_dong_ky.value(), in_word.DONG_KY_MAC_DINH)):
            if khoa in mw or gt != mac_dinh:
                mw[khoa] = gt
        for khoa, o in self.o_co.items():
            v = round(o.value(), 1)
            mw['co_chu'][khoa] = int(v) if float(v).is_integer() else v
        t = round(self.o_thut.value() * 10, 2)
        mw['thut_dau_dong_mm'] = int(t) if float(t).is_integer() else t
        mw['gach_chan_ho_pt'] = int(round(self.o_ho.value()))
        return mw

    # ------------------------------------------------ OK / xuất / nhập / khôi phục
    def _bao(self, chu: str, loi: bool = False) -> None:
        if self.im_lang:
            return
        (QMessageBox.warning if loi else QMessageBox.information)(self, TEN_UD, chu)

    def ap_dung(self) -> list | None:
        """Ghi thông số đang hiện vào hồ sơ máy, áp dụng ngay. Trả danh sách mục đã đổi; None nếu chưa hợp lệ (đã báo, chưa ghi gì)."""
        le_w, le_b = self._le_word, self._le_bth
        for ten, le, kho in (('phương án chi tiết', le_w, self._kho_word_mm()), ('bảng tổng hợp', le_b, (KHO_MM['A3'][1], KHO_MM['A3'][0]))):
            if le['trai'] + le['phai'] > kho[0] - 60 or le['tren'] + le['duoi'] > kho[1] - 60:
                self._bao(f'Lề của {ten} quá lớn: vùng in còn lại phải rộng và cao ít nhất 6 cm.', True)
                return None
        try:
            doi = in_word.dat_thong_so(self.thong_so())
            if le_b != self._doc_le_bth():
                chuan = self._le_bth_chuan()
                khac = {ten: round(le_b[k] / INCH_MM, 4) for k, ten in LE_BTH if le_b[k] != chuan[k]}
                dia_phuong.dat_muc_may(('ban_in', 'le_trang', 'tong_hop'), khac or None)
                doi = list(doi) + ['le_trang.tong_hop']
        except (dia_phuong.LoiHoSo, OSError) as e:
            self._bao(chu_loi('Không ghi được thông số trang', e), True)
            return None
        self.da_ap = list(doi)
        return self.da_ap

    def _kho_word_mm(self) -> tuple:
        ngan, dai = KHO_MM[self.cb_kho.currentData() or 'A4']
        return (dai, ngan) if self.b_ngang.isChecked() else (ngan, dai)

    def dong_y(self) -> bool:
        """Nút OK: ghi và đóng. Chưa hợp lệ thì ở lại hộp."""
        if self.ap_dung() is None:
            return False
        self.accept()
        return True

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
        self._bao(f'Đã xuất thông số mẫu Word:\n{p}\n\nĐưa file này cho máy khác rồi bấm "Nhập thông số…" ở máy đó.')
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
            xac_nhan = QMessageBox.question(self, TEN_UD, 'Bỏ thông số trang tùy chỉnh của máy này, dùng lại thông số chuẩn nhúng?') == \
                QMessageBox.StandardButton.Yes
        if xac_nhan is False:
            return False
        in_word.khoi_phuc_thong_so()
        try:
            dia_phuong.dat_muc_may(('ban_in', 'le_trang', 'tong_hop'), None)
        except (dia_phuong.LoiHoSo, OSError):
            pass
        self.nap()
        return True

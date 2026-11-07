"""Thành phần bảng In kiểu Word / Excel (1.0.66, người dùng 05/11/2026 kèm ảnh bảng In của Word: cấu trúc quen thuộc với người dùng Office).
HangChon: dòng chọn biểu tượng + hai hàng chữ + mũi tên; NutLon: nút In lớn; nut_rail: mục cột trái. doc_day_so / chu_day_so: ô "Trang", "Hộ" kiểu 1-3, 5. Máy in: danh sách, trạng thái, thuộc tính. In ở xem_truoc_tai_lieu.in_theo_tuy_chon."""
from __future__ import annotations

import re
import subprocess

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QPushButton, QToolButton, QVBoxLayout

from .giao_dien import TOKEN, NhanRutGon, dat_kieu_theo_tong, icon_ky_hieu
from .lap_pa import LoiNhap

# ký hiệu Segoe MDL2
IC_IN, IC_XUAT, IC_DU_LIEU, IC_LUI = 0xE749, 0xEDE1, 0xE8A5, 0xE72B
IC_HO, IC_TAI_LIEU, IC_BAN, IC_MAT, IC_XEP_BO, IC_KHO = 0xE716, 0xE8A5, 0xE70F, 0xE8C8, 0xE8FD, 0xE7C3
HAI_MAT = (('mot', 'In một mặt', 'Chỉ in một mặt của trang'), ('dai', 'In cả hai mặt', 'Lật trang trên cạnh dài'), ('ngan', 'In cả hai mặt', 'Lật trang trên cạnh ngắn'))
XEP_BO = ((True, 'Xếp bộ', '1,2,3   1,2,3   1,2,3'), (False, 'Không xếp bộ', '1,1,1   2,2,2   3,3,3'))
KHO_GIAY = (('', 'Khổ theo bản in', 'A4 dọc; bảng tổng hợp A3 ngang'), ('A4', 'A4 (21 x 29,7 cm)', 'Thu vừa khổ A4'), ('A3', 'A3 (29,7 x 42 cm)', 'Phóng vừa khổ A3'))


def doc_day_so(chu: str, ten: str = 'Trang') -> list:
    """'1-3, 5' -> [1, 2, 3, 5] (giữ thứ tự, bỏ trùng); trống: []. Sai: LoiNhap."""
    kq = []
    for phan in re.split(r'[,;]', str(chu or '')):
        phan = phan.strip()
        if not phan:
            continue
        m = re.fullmatch(r'(\d+)\s*-\s*(\d+)', phan)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a > b or b - a > 100000:
                raise LoiNhap(f'{ten}: khoảng "{phan}" không đúng.')
            so = range(a, b + 1)
        elif phan.isdigit():
            so = [int(phan)]
        else:
            raise LoiNhap(f'{ten}: "{phan}" không đúng. Ghi kiểu 1-3, 5.')
        kq += [x for x in so if x not in kq]
    if any(x <= 0 for x in kq):
        raise LoiNhap(f'{ten}: số phải từ 1 trở lên.')
    return kq


def chu_day_so(ds) -> str:
    """[1, 2, 3, 5] -> '1-3, 5'."""
    ds = sorted({int(x) for x in ds})
    kq, i = [], 0
    while i < len(ds):
        j = i
        while j + 1 < len(ds) and ds[j + 1] == ds[j] + 1:
            j += 1
        kq.append(str(ds[i]) if i == j else f'{ds[i]}-{ds[j]}')
        i = j + 1
    return ', '.join(kq)


# ---------------------------------------------------------------- máy in (bản Win 7 không có QtPrintSupport: danh sách rỗng)
def _qprinter_info():
    try:
        from PySide6.QtPrintSupport import QPrinterInfo
        return QPrinterInfo
    except ImportError:
        return None


def ds_may_in() -> list:
    q = _qprinter_info()
    return list(q.availablePrinterNames()) if q is not None else []


def may_in_mac_dinh() -> str:
    q = _qprinter_info()
    return q.defaultPrinterName() if q is not None else ''


def trang_thai_may_in(ten: str) -> str:
    q = _qprinter_info()
    if q is None:
        return ''
    try:
        from PySide6.QtPrintSupport import QPrinter
        tt = q.printerInfo(ten).state()
        return {QPrinter.PrinterState.Idle: 'Sẵn sàng', QPrinter.PrinterState.Active: 'Đang in', QPrinter.PrinterState.Aborted: 'Đã dừng',
                QPrinter.PrinterState.Error: 'Lỗi'}.get(tt, '')
    except (AttributeError, TypeError):
        return ''


def hai_mat_mac_dinh(ten: str) -> str:
    """Theo cài đặt của máy in: 'mot' | 'dai' | 'ngan'."""
    q = _qprinter_info()
    if q is None:
        return 'mot'
    try:
        from PySide6.QtPrintSupport import QPrinter
        return {QPrinter.DuplexMode.DuplexLongSide: 'dai', QPrinter.DuplexMode.DuplexShortSide: 'ngan'}.get(q.printerInfo(ten).defaultDuplexMode(), 'mot')
    except (AttributeError, TypeError):
        return 'mot'


def mo_thuoc_tinh(ten: str) -> None:
    """Hộp thuộc tính máy in của Windows (như link Thuộc tính Máy in của Word)."""
    subprocess.Popen(['rundll32.exe', 'printui.dll,PrintUIEntry', '/e', '/n', ten])


# ---------------------------------------------------------------- thành phần giao diện
class HangChon(QPushButton):
    """Dòng chọn kiểu bảng In của Office: biểu tượng, hai hàng chữ, mũi tên; bấm mở danh sách. ds: [(giá trị, tiêu đề, mô tả)]. doi: chọn mục khác (người dùng bấm hoặc dat)."""
    doi = Signal(object)
    CAO = 42

    def __init__(self, ma_icon=None, ds=(), parent=None):
        super().__init__(parent)
        self.setProperty('khong_icon', True)
        self.setFixedHeight(self.CAO)
        dat_kieu_theo_tong(self, f'QPushButton {{ background: {TOKEN["khung"]}; border: 1px solid {TOKEN["vach"]}; border-radius: 4px; text-align: left; padding: 0; }}'
                                 f'QPushButton:hover {{ border-color: {TOKEN["chinh"]}; background: {TOKEN["chinh_nhat"]}; }}'
                                 f'QPushButton:disabled {{ background: {TOKEN["nen"]}; }}'
                                 'QPushButton::menu-indicator { subcontrol-origin: padding; subcontrol-position: center right; right: 8px; }')
        self._ds = []
        self._gt = None
        h = QHBoxLayout(self)
        h.setContentsMargins(8, 1, 24, 1)
        h.setSpacing(8)
        self.lb_icon = QLabel()
        self.lb_icon.setFixedWidth(24)
        ic = icon_ky_hieu(ma_icon, TOKEN['chinh'], 20) if ma_icon else None
        if ic is not None:
            self.lb_icon.setPixmap(ic.pixmap(QSize(20, 20)))
        self.lb_1, self.lb_2 = NhanRutGon(''), NhanRutGon('')
        dat_kieu_theo_tong(self.lb_2, f'QLabel {{ color: {TOKEN["chu_phu"]}; background: transparent; }}')
        dat_kieu_theo_tong(self.lb_1, f'QLabel {{ color: {TOKEN["chu"]}; background: transparent; }}')
        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self.lb_1)
        v.addWidget(self.lb_2)
        h.addWidget(self.lb_icon)
        h.addLayout(v, 1)
        for w in (self.lb_icon, self.lb_1, self.lb_2):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.menu = QMenu(self)
        self.setMenu(self.menu)
        self.dat_ds(ds)

    def dat_ds(self, ds, gt=None) -> None:
        """Đặt lại danh sách, giữ mục đang chọn nếu còn (không phát doi); hết thì mục đầu (phát doi)."""
        self._ds = list(ds)
        self.menu.clear()
        for x, t, m in self._ds:
            a = self.menu.addAction(f'{t}  ·  {m}' if m else t)
            a.triggered.connect(lambda _=False, g=x: self.dat(g))
        co = {x for x, _, _ in self._ds}
        moi = gt if gt in co else (self._gt if self._gt in co else (self._ds[0][0] if self._ds else None))
        doi = moi != self._gt
        self._gt = moi
        self._ve()
        if doi and gt is None and self._ds:
            self.doi.emit(moi)

    def gia_tri(self):
        return self._gt

    def dat(self, gt, im: bool = False) -> None:
        if gt == self._gt or gt not in {x for x, _, _ in self._ds}:
            return
        self._gt = gt
        self._ve()
        if not im:
            self.doi.emit(gt)

    def _ve(self) -> None:
        x = next(((t, m) for g, t, m in self._ds if g == self._gt), ('', ''))
        self.lb_1.setText(x[0])
        self.lb_2.setText(x[1])
        self.lb_2.setVisible(bool(x[1]))
        self.setToolTip(f'{x[0]}: {x[1]}' if x[1] else x[0])


class NutLon(QToolButton):
    """Nút lớn biểu tượng trên, chữ dưới, như nút In của Word."""

    def __init__(self, chu: str, ma_icon: int, parent=None):
        super().__init__(parent)
        self.setText(chu)
        self.setFixedSize(84, 76)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        ic = icon_ky_hieu(ma_icon, TOKEN['chinh'], 30)
        if ic is not None:
            self.setIcon(ic)
            self.setIconSize(QSize(30, 30))
        self.setProperty('khong_icon', True)
        dat_kieu_theo_tong(self, f'QToolButton {{ background: {TOKEN["khung"]}; color: {TOKEN["chu"]}; border: 1px solid {TOKEN["vach"]}; border-radius: 4px; padding: 4px; }}'
                                 f'QToolButton:hover {{ background: {TOKEN["chinh_nhat"]}; border-color: {TOKEN["chinh"]}; }}'
                                 f'QToolButton:pressed {{ background: {TOKEN["vach"]}; }}')


def nut_rail(chu: str, ma_icon: int, chon_duoc: bool = True) -> QPushButton:
    """Mục cột trái kiểu Office: đang chọn có vạch đậm bên trái."""
    b = QPushButton(chu)
    b.setProperty('khong_icon', True)
    b.setCheckable(chon_duoc)
    b.setMinimumHeight(40)
    ic = icon_ky_hieu(ma_icon, TOKEN['chinh'], 18)
    if ic is not None:
        b.setIcon(ic)
        b.setIconSize(QSize(18, 18))
    dat_kieu_theo_tong(b, f'QPushButton {{ background: transparent; color: {TOKEN["chu"]}; border: 0; border-left: 3px solid transparent; border-radius: 0; text-align: left; padding: 6px 10px; }}'
                          f'QPushButton:hover {{ background: {TOKEN["vach"]}; }}'
                          f'QPushButton:checked {{ background: {TOKEN["chinh_nhat"]}; color: {TOKEN["chinh"]}; border-left: 3px solid {TOKEN["chinh"]}; font-weight: 600; }}')
    return b


def nhan_de_muc(chu: str, lon: bool = False) -> QLabel:
    """Đề mục như Word: chữ đậm, không băng màu. lon: tên mục đầu cột (In, Xuất)."""
    n = QLabel(chu)
    dat_kieu_theo_tong(n, f'QLabel {{ color: {TOKEN["chu"]}; background: transparent; border: 0; font-size: {18 if lon else 14}px; font-weight: 600; }}')
    return n


def nut_lien_ket(chu: str) -> QPushButton:
    """Nút dạng chữ gạch chân như link Thuộc tính Máy in, Thiết lập Trang của Word."""
    b = QPushButton(chu)
    b.setProperty('khong_icon', True)
    b.setMinimumWidth(b.fontMetrics().horizontalAdvance(chu) + 14)      # đủ chữ cả khi hàng máy in hẹp
    b.setMinimumHeight(24)                              # vùng bấm tối thiểu (WCAG 2.2): trước 17 px
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    dat_kieu_theo_tong(b, f'QPushButton {{ background: transparent; color: {TOKEN["nhan"]}; border: 0; text-decoration: underline; padding: 0 2px; }}'
                          f'QPushButton:disabled {{ color: {TOKEN["chu_phu"]}; }}')
    return b

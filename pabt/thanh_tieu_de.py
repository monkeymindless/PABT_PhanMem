"""Thanh tiêu đề hợp nhất kiểu VS Code (người dùng 12/10/2026): MỘT hàng = biểu tượng + menu | tiêu đề giữa cửa sổ | nút
thu nhỏ / phóng to / đóng (0.9.66: bỏ nút Hoàn tác / Làm lại, Hướng dẫn, Cài đặt - trùng menu).

Cửa sổ vẫn là cửa sổ có khung của Windows (WS_THICKFRAME | WS_CAPTION…), chỉ bỏ phần vẽ thanh tiêu đề: kéo mép đổi cỡ,
Aero Snap (kéo lên đỉnh / sang cạnh, Win + mũi tên), hiệu ứng thu / phóng, bóng đổ, bo góc Windows 11, menu hệ thống
(Alt + Space, chuột phải vùng trống), bấm đúp vùng trống phóng to - đều do Windows làm. Bản 0.9.58-0.9.63 dùng cửa sổ không
khung thuần (tự kéo bằng startSystemMove) nên mất các thứ đó và phải quay lại thanh tiêu đề Windows ở 0.9.64.

Cách làm: thay thủ tục cửa sổ (SetWindowLongPtrW GWLP_WNDPROC, ctypes) - Qt 6.11 tự xử lý WM_NCCALCSIZE / WM_NCHITTEST
TRƯỚC nativeEvent và bộ lọc QAbstractNativeEventFilter (đã thử: không nhận được hai thông điệp này).
  - WM_NCCALCSIZE: cả cửa sổ là vùng client (không còn thanh tiêu đề / viền vẽ); khi phóng to Windows đặt cửa sổ tràn ra
    ngoài màn hình đúng bề dày khung -> thu vùng client lại bằng ấy (không thì mất ~9 px mỗi cạnh).
  - WM_NCHITTEST: mép cửa sổ (VIEN_KEO) = kéo đổi cỡ, vùng trống của thanh = HTCAPTION, còn lại trả cho Qt.
Chỉ bản Qt 6 (Windows 10 1809+). Bản Qt 5 (Win 7/8, PySide2 32-bit) và khi chạy `--khung-windows` / biến môi trường
PABT_KHUNG_WINDOWS giữ thanh tiêu đề Windows + hàng menu trắng như 0.9.64 (`dung_thanh_hop_nhat`). Gắn thủ tục lỗi -> trả
lại khung Windows, ẩn nút cửa sổ tự vẽ (không bao giờ để cửa sổ mất nút đóng).
"""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMenuBar, QSizePolicy, QToolButton, QWidget)

CAO = 34                 # chiều cao thanh (điểm logic) - như VS Code; 0.9.82: 38; 17/10/2026 Hybrid Enterprise Navy: 34 (1366x768)
RONG_NUT_CUA_SO = 46     # nút thu nhỏ / phóng to / đóng
VIEN_KEO = 5             # mép cửa sổ dùng để kéo đổi cỡ (điểm logic)
MAU_NEN = '#F3F6FA'      # 1.0.42: cùng TOKEN['nen'] — tông Tối đổi qua _mau_chrome
MAU_VACH = '#D5DEE8'
MAU_CHU = '#0F172A'
MAU_CHU_MO = '#475569'   # cửa sổ không hoạt động
MAU_DONG = '#C42B1C'     # nền nút Đóng khi rê chuột (màu Windows 11)


def _mau_chrome():
    """(nền, vạch, chữ, chữ mờ) theo tông đang dùng — thanh tiêu đề cùng hệ TOKEN, không còn #F8F8F8 cứng."""
    from . import giao_dien as gd
    if gd.TONG_NEN[0] == 'toi':
        return '#0B1120', '#334155', '#E2E8F0', '#94A3B8'
    T = gd.TOKEN
    return T['nen'], T['vach'], T['chu'], T['chu_phu']

# ký hiệu Segoe Fluent Icons / Segoe MDL2 Assets (Windows 10+); máy không có phông -> chữ thường
KY = dict(thu_nho=(0xE921, '–'), phong_to=(0xE922, '□'), tra_lai=(0xE923, '❐'), dong=(0xE8BB, '✕'))


def dung_thanh_hop_nhat() -> bool:
    """Dùng thanh hợp nhất? Bản Qt 5 (Win 7/8) và khi người dùng chọn khung Windows thì không."""
    import pabt
    if getattr(pabt, 'QT5', False):
        return False
    if '--khung-windows' in sys.argv or os.environ.get('PABT_KHUNG_WINDOWS'):
        return False
    return True


def _phong_ky_hieu() -> str:
    from .giao_dien import _phong_ky_hieu as p
    return p()


def _chu_ky(ten: str) -> tuple:
    """(chữ, phông) cho nút: ký hiệu nếu máy có phông biểu tượng, không thì ký tự thường."""
    ma, du_phong = KY[ten]
    phong = _phong_ky_hieu()
    return (chr(ma), phong) if phong else (du_phong, '')


class _NutThanh(QToolButton):
    """Nút trên thanh tiêu đề: ký hiệu phông, nền trong suốt, rê chuột nền xám nhạt (Đóng: đỏ chữ trắng)."""

    def __init__(self, ten: str, goi_y: str, rong: int, cao: int, dong: bool = False, co: float = 10.0, parent=None):
        super().__init__(parent)
        self.ten = ten
        self.setToolTip(goi_y)
        self.setAccessibleName(goi_y)
        self.setFixedSize(rong, cao)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoRaise(True)
        self._co = co
        self._dong = dong
        self._rong = rong
        self.dat_ky(ten)
        self.ap_mau()

    def ap_mau(self) -> None:
        _nen, _vach, chu, chu_mo = _mau_chrome()
        nen = MAU_DONG if self._dong else 'rgba(0,0,0,0.07)'
        chu_re = '#FFFFFF' if self._dong else chu
        bo = '0px' if self._rong == RONG_NUT_CUA_SO else '5px'
        self.setStyleSheet(
            f'QToolButton {{ color: {chu}; background: transparent; border: 0; border-radius: {bo}; padding: 0; }}'
            f'QToolButton:hover {{ background: {nen}; color: {chu_re}; }}'
            f'QToolButton:pressed {{ background: {"#A82315" if self._dong else "rgba(0,0,0,0.12)"}; color: {chu_re}; }}'
            f'QToolButton:disabled {{ color: {chu_mo}; }}')

    def dat_ky(self, ten: str) -> None:
        chu, phong = _chu_ky(ten)
        f = QFont(phong) if phong else QFont(self.font())
        f.setPointSizeF(self._co if phong else self._co + 2)
        self.setFont(f)
        self.setText(chu)


class ThanhTieuDe(QWidget):
    """Hàng trên cùng của cửa sổ chính. `mb` = QMenuBar của cửa sổ (cửa sổ trả nó ở menuBar())."""

    def __init__(self, cua, mb: QMenuBar):
        super().__init__(cua)
        self.cua = cua
        self.mb = mb
        self.setObjectName('thanh_tieu_de')
        self.setFixedHeight(CAO)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._kieu(True)
        lo = QHBoxLayout(self)
        lo.setContentsMargins(10, 0, 0, 0)
        lo.setSpacing(2)
        from .giao_dien import KhungLogo
        self.logo = KhungLogo(20)
        self.logo.setToolTip('LARC')
        lo.addWidget(self.logo, 0, Qt.AlignmentFlag.AlignVCenter)
        lo.addSpacing(6)
        mb.setParent(self)
        mb.setNativeMenuBar(False)
        mb.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self._kieu_menu()
        mb.setProperty('trong_thanh_td', True)       # giao_dien.vua_cao_menu: cao đúng bằng mục menu, canh giữa thanh
        from .giao_dien import vua_cao_menu
        vua_cao_menu(mb)
        lo.addWidget(mb, 0, Qt.AlignmentFlag.AlignVCenter)
        # 0.9.66 (người dùng 12/10/2026 - bỏ lệnh trùng): không đặt nút Hoàn tác / Làm lại, Hướng dẫn, Cài đặt trên thanh này -
        # đã có ở menu Chỉnh sửa / Trợ giúp / Cài đặt ngay bên cạnh (Ctrl+Z / Ctrl+Y / F1 vẫn dùng được)
        lo.addStretch(1)
        # tiêu đề nằm GIỮA CỬA SỔ (không giữa phần còn trống) - đặt tay trong resizeEvent, không trong bố cục
        self.lb_tieu_de = QLabel(self)
        self.lb_tieu_de.setObjectName('tieu_de_cua_so')
        self.lb_tieu_de.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb_tieu_de.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.nut_cua_so = {}
        for k, goi_y, ham in (('thu_nho', 'Thu nhỏ', cua.showMinimized), ('phong_to', 'Phóng to', self.lat_phong_to),
                              ('dong', 'Đóng', cua.close)):
            b = _NutThanh(k, goi_y, RONG_NUT_CUA_SO, CAO, dong=(k == 'dong'))
            b.setProperty('nut_cua_so', True)               # kiem_tra_giao_dien bỏ qua (bấm sẽ đóng / thu nhỏ cửa sổ)
            b.clicked.connect(ham)
            lo.addWidget(b, 0, Qt.AlignmentFlag.AlignTop)
            self.nut_cua_so[k] = b
        cua.windowTitleChanged.connect(self._dat_tieu_de)
        cua.installEventFilter(self)
        self._dat_tieu_de(cua.windowTitle())
        self.khung_windows = False               # True: đang dùng khung Windows (gắn thủ tục lỗi / không phải Windows)
        from .giao_dien import KHI_DOI_TONG_NEN
        KHI_DOI_TONG_NEN.append(self.ap_tong)

    # ------------------------------------------------------------------ hiển thị
    def _kieu_menu(self) -> None:
        _nen, _vach, chu, _mo = _mau_chrome()
        self.mb.setStyleSheet(
            'QMenuBar { background: transparent; color: %s; font-size: 13px; font-weight: 400; border: 0; padding: 0; }'
            'QMenuBar::item { background: transparent; padding: 4px 8px; margin: 0 1px; border-radius: 5px; }'
            'QMenuBar::item:selected { background: rgba(0,0,0,0.07); }'
            'QMenuBar::item:pressed { background: rgba(0,0,0,0.12); }' % chu)

    def _kieu(self, hoat_dong: bool) -> None:
        nen, vach, chu, chu_mo = _mau_chrome()
        mau = chu if hoat_dong else chu_mo
        self.setStyleSheet(
            f'#thanh_tieu_de {{ background: {nen}; border: 0; border-bottom: 1px solid {vach}; }}'
            f'#tieu_de_cua_so {{ color: {mau}; font-size: 12.5px; background: transparent; }}')
        if getattr(self, 'mb', None) is not None:
            self._kieu_menu()
        for b in getattr(self, 'nut_cua_so', {}).values():
            b.ap_mau()

    def ap_tong(self, _ten=None) -> None:
        """Đổi tông nền: thanh tiêu đề theo TOKEN / tông Tối (gắn KHI_DOI_TONG_NEN)."""
        self._kieu(True)

    def _dat_tieu_de(self, chu: str) -> None:
        self.lb_tieu_de.setToolTip(chu)
        self.lb_tieu_de.setProperty('chu_day_du', chu)
        self._dat_vi_tri()

    def tieu_de(self) -> str:
        return self.lb_tieu_de.property('chu_day_du') or ''

    def _dat_vi_tri(self) -> None:
        """Tiêu đề canh giữa cửa sổ; đè lên menu / nút thì dời sang phần trống, chữ dài rút "…" ở giữa."""
        chu = self.lb_tieu_de.property('chu_day_du') or ''
        trai = (self.mb.geometry().right() if self.mb.isVisible() else 0) + 12
        phai = min([w.geometry().left() for w in self.nut_cua_so.values() if w.isVisible()] or [self.width()]) - 12
        con = max(phai - trai, 0)
        fm = self.lb_tieu_de.fontMetrics()
        hien = fm.elidedText(chu, Qt.TextElideMode.ElideMiddle, con)   # giữ "PABT - …" và "(tên file)" khi rút gọn
        rong = min(fm.horizontalAdvance(hien) + 8, con)
        x = min(max((self.width() - rong) // 2, trai), max(phai - rong, trai))
        self.lb_tieu_de.setText(hien)
        self.lb_tieu_de.setGeometry(x, 0, rong, CAO)
        self.lb_tieu_de.setVisible(con > 40 and bool(hien))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._dat_vi_tri()

    def showEvent(self, e):
        super().showEvent(e)
        self._dat_vi_tri()

    def eventFilter(self, obj, e):
        if obj is self.cua:
            t = e.type()
            if t == QEvent.Type.WindowStateChange:
                self._dat_nut_phong_to()
            elif t == QEvent.Type.ActivationChange:
                self._kieu(self.cua.isActiveWindow())
        return False

    def _dat_nut_phong_to(self) -> None:
        b = self.nut_cua_so['phong_to']
        lon = self.cua.isMaximized()
        b.dat_ky('tra_lai' if lon else 'phong_to')
        b.setToolTip('Thu về' if lon else 'Phóng to')

    def lat_phong_to(self) -> None:
        if self.cua.isMaximized():
            self.cua.showNormal()
            self._ve_kich_thuoc_thuong()
        else:
            self.cua.showMaximized()

    def _ve_kich_thuoc_thuong(self) -> None:
        """Thu về từ chế độ phóng to: kích thước thường mà bằng (gần) cả màn hình - không có gì để "thu về" - thì dùng kích thước chuẩn
        1200 x 740 canh giữa màn hình (đặc tả V10); người dùng đã tự đặt kích thước nhỏ hơn thì giữ."""
        from .giao_dien import kich_thuoc_thuong
        man = self.cua.screen()
        g = self.cua.geometry()
        if man is not None:
            v = man.availableGeometry()
            if g.width() >= v.width() * 0.97 and g.height() >= v.height() * 0.97:
                self.cua.setGeometry(kich_thuoc_thuong(self.cua))

    # ------------------------------------------------------------------ vùng kéo cửa sổ (WM_NCHITTEST)
    def la_vung_keo(self, p: QPoint) -> bool:
        """p theo tọa độ thanh. Vùng trống (không phải mục menu / nút) = kéo cửa sổ như thanh tiêu đề Windows."""
        if not self.rect().contains(p):
            return False
        w = self.childAt(p)
        if w is None or w is self.lb_tieu_de:
            return True
        if w is self.mb:
            return self.mb.actionAt(self.mb.mapFrom(self, p)) is None
        return False

    def gan_khung(self) -> bool:
        """Bỏ thanh tiêu đề Windows (giữ khung). Gọi TRƯỚC khi hiện cửa sổ. Lỗi -> khung Windows như cũ, ẩn nút tự vẽ."""
        ok = False
        if sys.platform == 'win32' and QApplication.platformName() == 'windows':
            try:
                ok = _KhungWin32(self.cua, self).gan()
            except Exception:                   # noqa: BLE001 - mọi lỗi Win32 / ctypes: giữ khung Windows
                ok = False
        if not ok:
            self.dung_khung_windows()
        return ok

    def dung_khung_windows(self) -> None:
        """Khung Windows vẽ thanh tiêu đề (có nút của Windows): ẩn nút cửa sổ tự vẽ, không trùng."""
        self.khung_windows = True
        if self.cua.windowFlags() & Qt.WindowType.FramelessWindowHint:
            self.cua.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)
        for b in self.nut_cua_so.values():
            b.hide()
        self._dat_vi_tri()


class _KhungWin32:
    """Thủ tục cửa sổ thay thế (giữ tham chiếu trên cửa sổ - bộ thu gom xóa hàm gọi lại = Windows gọi vào vùng nhớ đã giải phóng)."""

    WM_NCCALCSIZE, WM_NCHITTEST, WM_NCDESTROY = 0x0083, 0x0084, 0x0082
    HTCLIENT, HTCAPTION = 1, 2
    HTLEFT, HTRIGHT, HTTOP, HTTOPLEFT, HTTOPRIGHT, HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT = 10, 11, 12, 13, 14, 15, 16, 17
    GWL_STYLE, GWLP_WNDPROC = -16, -4
    KIEU_KHUNG = 0x00C00000 | 0x00040000 | 0x00020000 | 0x00010000 | 0x00080000   # CAPTION THICKFRAME MIN MAX SYSMENU

    def __init__(self, cua, thanh: ThanhTieuDe):
        self.cua = cua
        self.thanh = thanh

    def gan(self) -> bool:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        if not hasattr(u, 'SetWindowLongPtrW') or not hasattr(u, 'GetDpiForWindow'):
            return False                                        # Windows 32-bit / trước Windows 10 1607
        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        u.CallWindowProcW.restype = LRESULT
        u.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        u.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        u.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        u.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        u.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        u.GetDpiForWindow.argtypes = [wintypes.HWND]
        u.IsZoomed.argtypes = [wintypes.HWND]
        u.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        u.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]

        class NCCALCSIZE_PARAMS(ctypes.Structure):
            _fields_ = [('rgrc', wintypes.RECT * 3), ('lppos', ctypes.c_void_p)]

        class MARGINS(ctypes.Structure):
            _fields_ = [('trai', ctypes.c_int), ('phai', ctypes.c_int), ('tren', ctypes.c_int), ('duoi', ctypes.c_int)]

        self.cua.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        hwnd = int(self.cua.winId())                            # tạo cửa sổ thật (chưa hiện)
        cu = u.GetWindowLongPtrW(hwnd, self.GWLP_WNDPROC)
        if not cu:
            return False
        cua, K = self.cua, self

        def khung(dpi):
            fx = u.GetSystemMetricsForDpi(32, dpi) + u.GetSystemMetricsForDpi(92, dpi)    # SM_CXSIZEFRAME + PADDEDBORDER
            fy = u.GetSystemMetricsForDpi(33, dpi) + u.GetSystemMetricsForDpi(92, dpi)
            return fx, fy

        def thu_tuc(h, msg, wp, lp):
            try:
                if msg == K.WM_NCCALCSIZE and wp:
                    if u.IsZoomed(h):                       # phóng to: Windows đặt cửa sổ tràn màn hình đúng bề dày khung
                        r = NCCALCSIZE_PARAMS.from_address(lp).rgrc[0]
                        fx, fy = khung(u.GetDpiForWindow(h))
                        r.left += fx
                        r.right -= fx
                        r.top += fy
                        r.bottom -= fy
                    return 0
                if msg == K.WM_NCHITTEST:
                    kq = K.vung(h, lp, u, wintypes)
                    if kq is not None:
                        return kq
                elif msg == K.WM_NCDESTROY:
                    u.SetWindowLongPtrW(h, K.GWLP_WNDPROC, cu)
            except Exception:                               # noqa: BLE001 - lỗi trong thủ tục cửa sổ: để Qt xử lý
                pass
            return u.CallWindowProcW(cu, h, msg, wp, lp)

        self._thu_tuc = WNDPROC(thu_tuc)
        cua._khung_win32 = self                             # giữ hàm gọi lại sống cùng cửa sổ
        u.SetWindowLongPtrW(hwnd, self.GWLP_WNDPROC, ctypes.cast(self._thu_tuc, ctypes.c_void_p).value)
        u.SetWindowLongPtrW(hwnd, self.GWL_STYLE, u.GetWindowLongPtrW(hwnd, self.GWL_STYLE) | self.KIEU_KHUNG)
        try:
            dwm = ctypes.windll.dwmapi
            dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(MARGINS(0, 0, 0, 1)))   # bóng đổ của Windows
            bo = ctypes.c_int(2)                                                        # DWMWCP_ROUND (Windows 11)
            dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(bo), ctypes.sizeof(bo))
        except (OSError, AttributeError):
            pass
        u.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)  # FRAMECHANGED
        self.hwnd = hwnd
        return True

    def vung(self, h, lp, u, wintypes):
        """WM_NCHITTEST: mép = đổi cỡ, vùng trống thanh tiêu đề = HTCAPTION, còn lại None (Qt xử lý)."""
        import ctypes
        pt = wintypes.POINT(ctypes.c_short(lp & 0xFFFF).value, ctypes.c_short((lp >> 16) & 0xFFFF).value)
        u.ScreenToClient(h, ctypes.byref(pt))
        rc = wintypes.RECT()
        u.GetClientRect(h, ctypes.byref(rc))
        dpr = self.cua.devicePixelRatioF() or 1.0
        x, y, w, hh = pt.x, pt.y, rc.right, rc.bottom
        if not u.IsZoomed(h) and not self.cua.isFullScreen():
            b = max(int(VIEN_KEO * dpr), 2)
            tren, duoi, trai, phai = y < b, y >= hh - b, x < b, x >= w - b
            if tren and trai:
                return self.HTTOPLEFT
            if tren and phai:
                return self.HTTOPRIGHT
            if duoi and trai:
                return self.HTBOTTOMLEFT
            if duoi and phai:
                return self.HTBOTTOMRIGHT
            if tren:
                return self.HTTOP
            if duoi:
                return self.HTBOTTOM
            if trai:
                return self.HTLEFT
            if phai:
                return self.HTRIGHT
        p = QPoint(int(x / dpr), int(y / dpr))
        t = self.thanh
        if t.isVisible() and t.la_vung_keo(t.mapFrom(self.cua, p)):
            return self.HTCAPTION
        return None


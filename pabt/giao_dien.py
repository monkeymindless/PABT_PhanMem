"""Màu giao diện: nút bấm tô theo nhóm chức năng, tiêu đề bảng / thuộc tính đậm màu, bảng xen màu dòng.

Nút được tô tự động theo chữ trên nút (Lưu, Thêm, Xóa, Gộp, In…) khi cửa sổ hiện ra, nên mọi hộp thoại đều thống nhất
mà không phải sửa từng màn hình. Muốn đổi màu một nhóm: sửa MAU.
"""
from __future__ import annotations
import re
from contextlib import contextmanager
from enum import Enum

from PySide6.QtCore import QEvent, QLibraryInfo, QLocale, QObject, QPoint, QRect, QSettings, QSize, QTimer, QTranslator, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLayout, QPushButton, QRadioButton,
                               QLineEdit, QSpinBox, QStyledItemDelegate, QToolButton, QVBoxLayout, QWidget)

from .lap_pa import bo_dau

# Hệ thống thiết kế (đặc tả ARCH-PABT-2026-V4 mục 3, người dùng 11/10/2026): MỘT nguồn màu cho cả phần mềm
TOKEN = dict(
    chinh='#0F3866',          # Primary - Deep Navy (ARCH-PABT-2026-V5)
    chinh_nhat='#E8F0FE',     # Primary Light: nền mục đang chọn
    nhan='#2563EB',           # Accent - Royal Blue: tab chọn, link, vạch chỉ thị menu
    phu='#107C41',            # Success - Forest Green: Lưu, Duyệt
    nguy_hiem='#DC2626',      # Danger - Vivid Red
    chu='#1E293B',            # Neutral Dark: chữ chính
    chu_phu='#64748B',        # Neutral Medium: chữ phụ
    vach='#E2E8F0',           # Divider
    nen='#F8FAFC',            # Surface
    khung='#FFFFFF',          # Panel
)
CAO_NUT_MENU = 27             # nút điều hướng menu trái (0.9.95 gọn: 36 -> 27, đủ 6 nhóm không phải cuộn)
RONG_MENU_TRAI = 175          # bề rộng menu trái mở (0.9.95: 248 -> 175; thu gọn: 44)
RONG_MENU_GON = 44
RONG_MENU_TOI_DA = 248        # lệnh dài ("Bảng tổng hợp kinh phí" ~189 px ở 125%) nới menu tới mức này - không cắt chữ
CAO_DONG_BANG = 32            # chiều cao dòng bảng dữ liệu
CHINH = TOKEN['chinh']       # xanh đậm: tiêu đề bảng, nhãn thuộc tính, tab đang chọn
# nhóm nút: (nền, chữ, nền khi rê chuột)
MAU = {                                            # tông dịu kiểu phần mềm quản lý: chỉ nút Lưu nền đặc, nút khác nền nhạt
    'luu':    ('#107C41', '#FFFFFF', '#0D6B37'),   # Lưu, Áp dụng (Secondary - Forest Green)
    'them':   ('#1D7A6C', '#FFFFFF', '#17675B'),   # Thêm…
    'xoa':    ('#D83B01', '#FFFFFF', '#B83201'),   # Xóa… (Danger - Crimson)
    'sua':    ('#B8651F', '#FFFFFF', '#9C551A'),   # Gộp, Chuyển, Tách, Bỏ thay đổi
    'in':     ('#6950A1', '#FFFFFF', '#594389'),   # In / Xuất, PDF
    'nhap':   ('#2D64A6', '#FFFFFF', '#26558D'),   # Nhập, Mở, Nạp, Cập nhật
    'hoso':   ('#1F7A86', '#FFFFFF', '#1A6872'),   # Hồ sơ hộ
    'pa':     ('#2F7A4F', '#FFFFFF', '#27673F'),   # Lập phương án
    'tra':    ('#4E5D6C', '#FFFFFF', '#424F5C'),   # Thông tin, Rà soát, Đối chiếu, Gợi ý, Chọn, Hộ trước / sau
    'nhat':   ('#ECEFF1', '#263238', '#CFD8DC'),   # Hủy, Đóng, Giới thiệu
}
DAC = ('luu',)                                     # nhóm nút nền đặc (thao tác chính); các nhóm khác nền nhạt, chữ màu
# (mẫu trên chữ đã bỏ dấu, nhóm) - xét theo thứ tự
LUAT = [
    (r'^xoa|xoa ho|xoa thua|xoa dong|^go ban cap nhat', 'xoa'),
    (r'^(luu|ap dung|save|thuc hien)', 'luu'),
    (r'^(huy|dong|cancel|close|khong luu|bo qua|gioi thieu)', 'nhat'),
    (r'^them', 'them'),
    (r'^(gop|chuyen|tach|bo thay doi|sua|ap bo|ap don gia|dua |bo ho)', 'sua'),
    (r'du an moi|du toan', 'pa'),
    (r'^(dot trinh|trang thai ho|nhap quyet dinh)', 'hoso'),
    (r'kiem tra cap nhat|bo don gia|cap nhat tu trang web|^tu (du an|file|danh sach)|^mo du toan', 'nhap'),
    (r'tra bang gia|lay gia|tra gia|kiem tra loi|kiem tra lai|quy chuan|tinh mat do', 'tra'),
    (r'^cap nhat', 'nhap'),
    (r'(^|\W)in(\W|$)|xuat|pdf|bao cao', 'in'),
    (r'^ho so', 'hoso'),
    (r'lap phuong an', 'pa'),
    (r'^(nhap|mo du an|nap|cap nhat)', 'nhap'),
    (r'goi y|chon|ra soat|thong tin|doi chieu|ho truoc|ho sau|tim|tra cuu|quay lai|^tiep', 'tra'),
]


class KieuNut(Enum):
    """Biến thể nút KHAI BÁO TƯỜNG MINH (đặc tả mục 6.1) - ưu tiên hơn màu đoán theo chữ (LUAT, giữ cho các nút chưa khai báo)."""
    CHINH = 'primary'          # nền Primary đặc, chữ trắng: thao tác chính của màn hình
    PHU = 'secondary'          # nền trắng, viền xám, chữ đen
    LUU = 'success'            # nền xanh lá: Lưu, Duyệt, Thêm
    NGUY_HIEM = 'danger'       # nền đỏ nhạt: Xóa


def ap_kieu_nut(w, kieu: KieuNut) -> None:
    """Gán biến thể cho nút (QPushButton / QToolButton) - setProperty + unpolish / polish để QSS áp ngay."""
    w.setProperty('bien_the', kieu.value)
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()
    if kieu in (KieuNut.CHINH, KieuNut.LUU):           # nền đặc: biểu tượng trắng (màu nhóm trên nền cùng màu thì mất)
        k = ky_hieu_nut(w.text())
        ic = icon_ky_hieu(k, '#FFFFFF', max(16, w.iconSize().width())) if k else None
        if ic is not None:
            w.setIcon(ic)
            a = w.defaultAction() if isinstance(w, QToolButton) else None
            if a is not None:                           # lệnh đổi (bật / tắt): Qt chép lại biểu tượng của lệnh - gắn lại màu trắng

                def gan_lai(w=w, ic=ic):
                    try:
                        w.setIcon(ic)
                    except RuntimeError:                # nút đã bị hủy
                        pass
                a.changed.connect(lambda: QTimer.singleShot(0, gan_lai))


def _qss_kieu_nut() -> str:
    """QSS các biến thể KieuNut: đặt CUỐI bảng kiểu (cùng độ ưu tiên thì quy tắc sau thắng màu đoán theo chữ / ribbon)."""
    t = TOKEN
    kieu = {'primary': (t['chinh'], '#FFFFFF', t['chinh'], '#1A4C85'),
            'success': (t['phu'], '#FFFFFF', t['phu'], '#0D6B37'),
            'danger': ('#FDECE7', '#B32D00', '#F3B9A6', '#FAD9CE'),
            'secondary': (t['khung'], t['chu'], t['vach'], '#F1F3F4')}
    qss = ''
    for k, (nen, chu, vien, re_) in kieu.items():
        for loai in ('QPushButton', 'QToolButton'):
            sel = f'{loai}[bien_the="{k}"]'
            qss += f'''
    {sel}, {sel}[ribbon="0"], {sel}[ribbon="1"] {{ color: {chu}; background: {nen}; border: 1px solid {vien}; border-radius: 5px;
        padding: 4px 10px; font-weight: 600; }}
    {sel}:hover, {sel}[ribbon="0"]:hover, {sel}[ribbon="1"]:hover {{ background: {re_}; }}
    {sel}:disabled, {sel}[ribbon="0"]:disabled, {sel}[ribbon="1"]:disabled {{ color: #9AA0A6; background: #F1F3F4;
        border-color: {t['vach']}; }}'''
    return qss


@contextmanager
def chan_tin_hieu(widget):
    """with chan_tin_hieu(w): cập nhật hàng loạt không phát tín hiệu (đặc tả mục 6.3) - luôn trả lại trạng thái cũ kể cả khi lỗi."""
    cu = widget.blockSignals(True)
    try:
        yield widget
    finally:
        widget.blockSignals(cu)


class OTimKiemThongMinh(QLineEdit):
    """Ô tìm có chờ ngừng gõ (đặc tả mục 6.2): bộ gõ tiếng Việt (Unikey...) gửi nhiều phím cho một chữ có dấu (xóa + gõ lại) -
    lọc sau MỖI phím làm bảng nháy, con trỏ giật. chuoi_da_doi phát sau CHO_MS ms kể từ phím cuối; phat_ngay() phát luôn."""
    chuoi_da_doi = Signal(str)
    CHO_MS = 200

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hen = QTimer(self)
        self._hen.setSingleShot(True)
        self._hen.setInterval(self.CHO_MS)
        self._hen.timeout.connect(self.phat_ngay)
        self.textChanged.connect(lambda *_: self._hen.start())
        # 0.9.82 (đặc tả V10): kính lúp đầu ô + nút xóa nhanh cuối ô. Ký hiệu phông Segoe MDL2 (không emoji: Windows 7 không có phông)
        ic = icon_ky_hieu(0xE721, '#64748B', 16)
        if ic is not None:
            self.addAction(ic, QLineEdit.ActionPosition.LeadingPosition)
        self.setClearButtonEnabled(True)

    def phat_ngay(self) -> None:
        self._hen.stop()
        self.chuoi_da_doi.emit(self.text().strip())


def loc_khi_ngung_go(o: QLineEdit, ham, ms: int = OTimKiemThongMinh.CHO_MS, kinh_lup: bool = True) -> QTimer:
    """Ô tìm có sẵn (QLineEdit) lọc khi NGỪNG GÕ (0.9.82, đặc tả V10 trụ cột 3): người dùng đang gõ (ô có con trỏ) -> chờ ms kể từ phím
    cuối (bộ gõ tiếng Việt gửi nhiều phím cho một chữ có dấu - trước đây bảng 5.666 mục đơn giá lọc lại sau MỖI phím); chữ đặt bằng mã
    (setText khi mở hộp, kiểm thử) -> lọc ngay. ham(chữ) như slot textChanged cũ. kinh_lup: biểu tượng kính lúp + nút xóa nhanh."""
    import inspect
    try:                                                # như Qt: slot không nhận tham số (vd. ve(self)) thì gọi không đối số
        ts = inspect.signature(ham).parameters.values()
        nhan_chu = any(p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.VAR_POSITIONAL) for p in ts)
    except (TypeError, ValueError):
        nhan_chu = True

    def goi():
        return ham(o.text()) if nhan_chu else ham()
    hen = QTimer(o)
    hen.setSingleShot(True)
    hen.setInterval(ms)
    hen.timeout.connect(goi)

    def doi(_chu):
        if o.hasFocus():
            hen.start()
        else:
            hen.stop()
            goi()
    o.textChanged.connect(doi)
    if kinh_lup:
        ic = icon_ky_hieu(0xE721, '#64748B', 16)
        if ic is not None:
            o.addAction(ic, QLineEdit.ActionPosition.LeadingPosition)
        o.setClearButtonEnabled(True)
    o._hen_loc = hen
    return hen


class OSoChuaNhap(QSpinBox):
    """Ô số nguyên hiện chữ (vd. "chưa nhập") khi bằng giá trị nhỏ nhất. QSpinBox để nguyên chữ đó khi bấm vào ô - con trỏ
    đặt giữa chữ, gõ 5 thành "ch5ưa nhập" (không hợp lệ): bấm chuột / Tab vào ô hoặc gõ phím thì chữ mất, chỉ còn số gõ vào.
    Rời ô khi chưa gõ gì: Qt hiện lại chữ, giá trị không đổi."""

    def __init__(self, chu: str = 'chưa nhập', parent=None):
        super().__init__(parent)
        self.setSpecialValueText(chu)
        self.lineEdit().installEventFilter(self)

    def _bo_chu(self) -> None:
        if self.value() == self.minimum() and self.lineEdit().text() == self.specialValueText():
            self.lineEdit().clear()

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self._bo_chu()

    def keyPressEvent(self, e):
        if e.text() and e.text().isprintable():
            self._bo_chu()
        super().keyPressEvent(e)

    def eventFilter(self, o, e):
        if o is self.lineEdit() and e.type() == QEvent.Type.MouseButtonPress:
            self._bo_chu()
        return super().eventFilter(o, e)


def nhom_nut(chu: str) -> str | None:
    s = bo_dau(re.sub(r'[&….]', ' ', chu or '')).strip(' ◀▶')
    return next((n for m, n in LUAT if re.search(m, s)), None)


def _tron(mau: str, t: float, voi: str = '#FFFFFF') -> str:
    """Trộn màu: t = 0 giữ nguyên, t = 1 thành màu 'voi' (mặc định trắng) - tạo nền nhạt / viền cho nút."""
    a, b = QColor(mau), QColor(voi)
    return QColor(round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t)).name()


def _nut_qss(n: str, nen: str, chu: str, re_: str) -> str:
    """QSS nút QPushButton theo nhóm: nhóm DAC nền đặc; nhóm khác nền nhạt + chữ, viền cùng màu (dịu mắt, tập trung dữ liệu)."""
    if n == 'nhat':
        return ''
    if n in DAC:
        return f'''QPushButton[nhom="{n}"] {{ color: {chu}; background: {nen}; border: 1px solid {re_}; border-radius: 5px;
            padding: 4px 10px; font-weight: 600; }}
        QPushButton[nhom="{n}"]:hover {{ background: {re_}; }}
        QPushButton[nhom="{n}"]:pressed {{ background: {_tron(re_, 0.12, '#000000')}; }}'''
    # nút viền (outline): nền trắng, chữ trung tính, chỉ biểu tượng mang màu nhóm; rê chuột mới hiện nền nhạt cùng màu
    return f'''QPushButton[nhom="{n}"] {{ color: #253545; background: #FFFFFF; border: 1px solid #CDD6E0; border-radius: 5px;
            padding: 4px 10px; font-weight: 600; }}
        QPushButton[nhom="{n}"]:hover {{ background: {_tron(nen, 0.93)}; border-color: {_tron(nen, 0.55)}; color: {_tron(nen, 0.15, '#000000')}; }}
        QPushButton[nhom="{n}"]:pressed {{ background: {_tron(nen, 0.86)}; }}'''


def mau_chu_nut(n: str | None) -> str:
    """Màu biểu tượng trên QPushButton theo nhóm (nền đặc: chữ trắng; nền nhạt: màu nhóm)."""
    if not n or n == 'nhat':
        return CHINH
    return MAU[n][1] if n in DAC else _tron(MAU[n][0], 0.08, '#000000')


# thẻ số liệu màn hình chính (app.CuaSoChinh.THE_SO): màu viền trái + màu số. Kiểu nằm trong QSS chung (trước 0.9.18: mỗi
# thẻ 3 lần setStyleSheet riêng = 18 kiểu cục bộ, phóng to / thu nhỏ phải co giãn lại từng cái)
MAU_THE_SO = {'so_ho': '#2D64A6', 'da_pa': '#2F7A4F', 'tong': '#6950A1', 'da_pd': '#1F7A86', 'da_ct': '#B8651F', 'da_bg': '#4E5D6C'}
# QSS thẻ Card màn hình chào (ARCH-PABT-2026-V5; 0.9.79: thẻ 210 x 135, bo 12px, mỗi thẻ một màu, mô tả nằm TRONG thẻ).
# loại -> (nền, viền, nền khi rê chuột, viền khi rê chuột, màu biểu tượng). Qt làm tròn viền 1,5px lên 2px: ghi 2px cho đúng thực tế.
KICH_THE_CHAO = (210, 135)
CO_ICON_THE_CHAO = 38
MAU_THE_CHAO = {
    'moi': ('#F0FDF4', '#BBF7D0', '#DCFCE7', '#16A34A', '#15803D'),
    'mo': ('#EFF6FF', '#BFDBFE', '#DBEAFE', '#2563EB', '#1D4ED8'),
    'excel': ('#F8FAFC', '#CBD5E1', '#F1F5F9', '#0F3866', '#0F3866'),
}
QSS_THE_CHAO = (
    f'QFrame[vai="the_chao"] {{ background: {TOKEN["khung"]}; border: 2px solid {TOKEN["vach"]}; border-radius: 12px; }}'
    f'QFrame[vai="the_chao"][hover="1"] {{ border-color: {TOKEN["nhan"]}; background: #F8FAFC; }}'
    + ''.join(
        f'QFrame[vai="the_chao"][loai="{k}"] {{ background-color: {nen}; border: 2px solid {vien}; border-radius: 12px; }}'
        f'QFrame[vai="the_chao"][loai="{k}"][hover="1"] {{ background-color: {nen_ro}; border-color: {vien_ro}; }}'
        for k, (nen, vien, nen_ro, vien_ro, _icon) in MAU_THE_CHAO.items())
    # nút lệnh trong thẻ: trong suốt (thẻ là khối nhìn thấy duy nhất); bộ chọn #id thắng mọi bộ chọn thuộc tính của nút ribbon
    + 'QToolButton#the_chao_nut, QToolButton#the_chao_nut:hover, QToolButton#the_chao_nut:pressed, QToolButton#the_chao_nut:disabled '
      '{ background: transparent; border: 0; padding: 0; }'
      'QToolButton#the_chao_nut { color: #0F172A; font-family: "Segoe UI"; font-size: 14.5pt; font-weight: 700; }'
      'QToolButton#the_chao_nut:disabled { color: #94A3B8; }'
)


def _qss_the_so() -> str:
    return '''
    QWidget[vai="the_so"] { background: #FFFFFF; border: 1px solid #DCE3EA; border-left: 4px solid #4E5D6C; border-radius: 6px; }
    QWidget[vai="the_so"] QLabel { background: transparent; border: 0; }
    QLabel[vai="so_the"] { font-size: 13.5px; font-weight: 700; }
    QLabel[vai="nhan_the"] { color: #4A5B6C; font-size: 11px; font-weight: 600; }''' + ''.join(
        f'''
    QWidget[vai="the_so"][the="{k}"] {{ border-left-color: {m}; }}
    QWidget[vai="the_so"][the="{k}"] QLabel[vai="so_the"] {{ color: {m}; }}''' for k, m in MAU_THE_SO.items())


def _qss_day_du() -> str:
    """Bảng kiểu cả phần mềm: kiểu chung + biến thể nút KieuNut (đặt cuối). Mọi chỗ đặt / dựng lại bảng kiểu (phóng to, thu
    nhỏ) dùng hàm này - trước đây phong_to dựng lại thiếu phần biến thể."""
    return _qss() + _qss_kieu_nut()


def _qss() -> str:
    nut = '\n'.join(
        f'''{_nut_qss(n, nen, chu, re_)}
        QToolButton[nhom="{n}"] {{ background: {nen}; color: {chu}; border: 1px solid {re_}; border-radius: 5px; padding: 4px 10px;
            font-weight: 600; }}
        QToolButton[nhom="{n}"]:hover {{ background: {re_}; }}
        QToolButton[ribbon="1"][nhom="{n}"] {{ background: {_tron(nen, 0.9) if n != 'nhat' else '#F3F6F9'};
            color: {nen if n != 'nhat' else CHINH}; border: 1px solid {_tron(nen, 0.72) if n != 'nhat' else '#D5DEE7'};
            border-radius: 5px; padding: 4px 10px; font-weight: 600; text-align: left; }}
        QToolButton[ribbon="1"][nhom="{n}"]:hover {{ background: {_tron(nen, 0.8) if n != 'nhat' else '#E7EDF3'};
            border-color: {nen if n != 'nhat' else '#9FB3C8'}; }}
        QToolButton[ribbon="1"][nhom="{n}"]:pressed {{ background: {_tron(nen, 0.68) if n != 'nhat' else '#DCE5EE'}; }}
        QPushButton[nhom="{n}"]:disabled, QToolButton[nhom="{n}"]:disabled {{ background: #ECEFF3; color: #A0AAB4;
            border-color: #DDE3EA; }}'''
        for n, (nen, chu, re_) in MAU.items())
    return nut + f'''
    QMainWindow {{ background: #EEF2F7; }}
    QDialog {{ background: #F4F7FB; }}
    QToolBar {{ background: #FFFFFF; border-bottom: 2px solid {CHINH}; spacing: 4px; padding: 5px; }}
    QPushButton {{ border-radius: 5px; padding: 4px 10px; border: 1px solid #CBD5E0; background: #FFFFFF; color: #1F2D3A; }}
    QPushButton:hover {{ background: #F1F5FA; border-color: #A9BCD0; }}
    QPushButton:pressed {{ background: #E4ECF5; }}
    QPushButton:disabled {{ color: #A0AAB4; background: #F4F6F8; border-color: #E3E8EE; }}
    QHeaderView::section {{ background: #EEF3F8; color: #24415E; font-weight: 600; padding: 7px 6px; border: 0;
        border-right: 1px solid #DDE5EE; border-bottom: 2px solid #C9D6E3; }}
    QTableView, QTreeView, QTableWidget, QTreeWidget {{ background: #FFFFFF; alternate-background-color: #F7FAFC;
        gridline-color: #E6ECF2; selection-background-color: #DCEBFA; selection-color: #0F2A44; border: 1px solid #DCE3EA;
        border-radius: 6px; }}
    QTableCornerButton::section {{ background: #EEF3F8; border: 0; }}
    QLineEdit[nhap="1"], QComboBox[nhap="1"], QSpinBox[nhap="1"] {{ min-height: 24px; font-size: 13px; padding: 4px 10px; }}
    QTableView QLineEdit, QTableView QComboBox, QTableView QPlainTextEdit {{ font-size: 13px; padding: 2px 6px;
        border: 2px solid #2E75B6; border-radius: 3px; background: #FFFFFF; }}
    QTabBar::tab {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F4F7FB, stop:1 #E3EAF2); color: #33495F;
        padding: 9px 22px; margin-right: 6px; margin-top: 3px; font-weight: 600; font-size: 13px; min-height: 18px;
        border: 1px solid #C6D2DF; border-bottom: 1px solid #C6D2DF; border-top-left-radius: 8px; border-top-right-radius: 8px; }}
    QTabBar::tab:hover {{ color: {CHINH}; background: #EAF2FB; border-color: #9FB9D4; }}
    QTabBar::tab:selected {{ color: #FFFFFF; background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2E75B6, stop:1 {CHINH});
        border: 1px solid {CHINH}; margin-top: 0px; }}
    QTabWidget::pane {{ border: 1px solid #D5DEE7; border-radius: 0 8px 8px 8px; background: #FFFFFF; top: -1px; }}
    QLabel[vai="nhan"] {{ color: {CHINH}; font-weight: 600; }}
    QLabel[vai="tieu_de"] {{ color: {CHINH}; background: #EEF3F8; font-weight: 600; padding: 7px 10px; border-radius: 6px;
        border-left: 3px solid #2E75B6; }}
    QLabel[vai="bang_ten"] {{ color: #0F3A63; background: #FFFFFF; font-size: 13px; padding: 8px 12px; border-radius: 8px;
        border: 1px solid #D5E1ED; border-left: 4px solid {TOKEN['nhan']}; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QPlainTextEdit, QTextEdit {{ background: #FFFFFF;
        border: 1px solid #C9D3DD; border-radius: 6px; padding: 4px 8px; selection-background-color: #2E75B6; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{ min-height: 20px; }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QPlainTextEdit:hover {{ border-color: #9FB6CC; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{
        border: 1px solid #2E75B6; background: #FBFDFF; }}
    QLineEdit:read-only {{ background: #F1F4F7; color: #4A5866; }}
    QToolButton[nho="1"] {{ font-size: 11px; padding: 3px 6px 2px 6px; }}
    QToolButton[menu="1"] {{ background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 2px 6px;
        text-align: left; font-weight: 600; font-size: 12px; color: #172A3D; }}
    QToolButton[menu="1"]:hover {{ background: #E8F0F8; border-color: #C9D9EA; }}
    QToolButton[menu="1"]:pressed {{ background: #D6E4F2; }}
    QToolButton[menu="1"]:disabled {{ color: #A8B3BF; background: transparent; border-color: transparent; }}
    QToolButton[menu="1"]:checked {{ background: {TOKEN['chinh_nhat']}; border: 0; border-left: 3px solid {TOKEN['nhan']};
        border-radius: 0 7px 7px 0; font-weight: 600; }}
    QTabBar[vai="lam_viec"] {{ background: transparent; }}
    QTabBar[vai="lam_viec"]::tab {{ background: transparent; color: {TOKEN['chu_phu']}; border: 0;
        border-bottom: 2px solid transparent; padding: 7px 14px; margin: 0; font-weight: 600; }}
    QTabBar[vai="lam_viec"]::tab:selected {{ color: {TOKEN['chinh']}; background: #FFFFFF;
        border-bottom: 2px solid {TOKEN['nhan']}; }}
    QTabBar[vai="lam_viec"]::tab:hover {{ color: {TOKEN['chinh']}; }}
    {QSS_THE_CHAO}
    QLabel[vai="the_chao_phu"] {{ color: #64748B; font-family: "Segoe UI"; font-size: 10.5pt; font-weight: 400; background: transparent;
        border: 0; }}
    QLabel[vai="lien_ket"] {{ color: {TOKEN['chu_phu']}; font-size: 12px; background: transparent; text-decoration: underline; }}
    QToolButton[xo="1"] {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0A2747, stop:1 #1B5A92);
        border: 1px solid #0A2747; border-left: 5px solid {TOKEN['nhan']}; border-radius: 8px; padding: 7px 10px;
        color: #FFFFFF; font-weight: 700; font-size: 14px; }}
    QToolButton[xo="1"]:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #113D6A, stop:1 #2672B4);
        border-color: {TOKEN['nhan']}; }}
    QToolButton[xo="1"]:pressed {{ background: #0A2747; }}
    QToolButton[xo="1"]::menu-indicator {{ image: none; width: 0; }}
    QCheckBox, QRadioButton {{ spacing: 7px; }}
    QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: #C3CFDB; border-radius: 4px; min-height: 28px; }}
    QScrollBar::handle:vertical:hover {{ background: #9FB3C8; }}
    QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: #C3CFDB; border-radius: 4px; min-width: 28px; }}
    QScrollBar::handle:horizontal:hover {{ background: #9FB3C8; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    QProgressBar {{ border: 1px solid #C9D3DD; border-radius: 6px; background: #FFFFFF; text-align: center; height: 16px; }}
    QProgressBar::chunk {{ background: #2E75B6; border-radius: 5px; }}
    QSplitter::handle {{ background: #DCE4EC; }}
    QComboBox QAbstractItemView, QListView, QListWidget, QTreeView {{ background: #FFFFFF; color: #1A1A1A;
        selection-background-color: #BBDEFB; selection-color: #0B2E4F; outline: 0; }}
    QComboBox QAbstractItemView::item {{ min-height: 24px; padding: 2px 6px; color: #1A1A1A; }}
    QComboBox QAbstractItemView::item:hover, QComboBox QAbstractItemView::item:selected,
    QListView::item:hover, QListView::item:selected, QListWidget::item:hover, QListWidget::item:selected {{
        background: #BBDEFB; color: #0B2E4F; }}
    QTableView::item:hover, QTreeView::item:hover {{ background: #EEF5FC; color: #1A1A1A; }}
    QTableView::item:selected, QTreeView::item:selected {{ background: #DCEBFA; color: #0F2A44; }}
    QMenu {{ background: #FFFFFF; color: #1A1A1A; border: 1px solid #C9D3DD; }}
    QMenu::item {{ padding: 6px 24px 6px 12px; }}
    QMenu::item:selected {{ background: #DCEBFA; color: #0B2E4F; }}
    QToolTip {{ background: #FFFFFF; color: #1F2D3A; border: 1px solid #C9D3DD; padding: 4px 6px; }}
    QGroupBox {{ font-weight: 600; color: {CHINH}; background: #FFFFFF; border: 1px solid #D5DEE7; border-radius: 8px;
        margin-top: 22px; padding: 16px 8px 8px 8px; }}
    QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 4px 8px;
        background: #FFFFFF; }}
    QStatusBar {{ background: #FFFFFF; color: {CHINH}; border-top: 1px solid #DCE4EC; }}
    QStatusBar QToolButton {{ border-radius: 6px; padding: 3px 10px; }}
    QFrame[vai="bang_to_chuc"] {{ background: transparent; border: 0; }}
    QFrame[vai="bang_to_chuc"] QLabel {{ color: #FFFFFF; background: transparent; border: 0; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="logo"] {{ background: transparent; border: 0; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="ten_phan_mem"] {{ color: #FFFFFF; font-size: 12.5px; font-weight: 700; letter-spacing: 0.3px; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="ten_to_chuc"] {{ color: {MAU_PHU_DE}; font-size: 11px; font-weight: 500; letter-spacing: 0.3px; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="dong_phu"] {{ color: #E2E8F0; font-size: 11px; font-weight: 500; letter-spacing: 0.3px; }}
    QFrame[vai="bang_to_chuc"] QToolButton[vai="nut_bang"] {{ color: #FFFFFF; background: rgba(255, 255, 255, 26);
        border: 1px solid rgba(255, 255, 255, 70); border-radius: 6px; padding: 2px 8px; font-weight: 600; font-size: 12px; }}
    QFrame[vai="bang_to_chuc"] QToolButton[vai="nut_bang"]:hover {{ background: rgba(255, 255, 255, 52);
        border-color: {TOKEN['nhan']}; }}
    QFrame[vai="bang_to_chuc"] QToolButton[vai="nut_bang"]:pressed {{ background: rgba(255, 255, 255, 80); }}
    QFrame[vai="bang_to_chuc"] QToolButton[vai="nut_bang"]:disabled {{ color: rgba(255, 255, 255, 110);
        background: transparent; border-color: rgba(255, 255, 255, 40); }}
    QLabel[vai="nhom_menu"] {{ color: #4A6785; font-size: 11px; font-weight: 700; letter-spacing: 0.6px;
        background: transparent; border: 0; border-radius: 5px; padding: 5px 4px 3px 4px; }}
    QLabel[vai="nhom_menu"]:hover {{ color: {CHINH}; background: #EEF3F8; }}
    QLabel[vai="nhom_menu"][dong="1"] {{ color: #6D8299; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="phien_ban"] {{ color: #E2E8F0; background: rgba(255, 255, 255, 18); font-weight: 600;
        font-size: 11px; border: 1px solid rgba(37, 99, 235, 150); border-radius: 10px; padding: 2px 10px; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="thu_nghiem"] {{ color: #FFFFFF; background: {TOKEN['nhan']}; font-weight: 800;
        font-size: 12px; letter-spacing: 0.8px; border: 1px solid {TOKEN['nhan']}; border-radius: 6px; padding: 2px 10px; }}
    QFrame[vai="vach_vang"] {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {TOKEN['nhan']}, stop:0.7 rgba(37,99,235,90),
        stop:1 rgba(37,99,235,0)); border: 0; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="ban_quyen"] {{ color: #E2E8F0; background: rgba(255, 255, 255, 14); font-weight: 600;
        font-size: 11px; border: 1px solid rgba(37, 99, 235, 160); border-radius: 10px; padding: 2px 10px; }}
    QFrame[vai="ribbon"] {{ background: #FFFFFF; border: 1px solid #DCE4EC; border-radius: 10px; }}
    QFrame[vai="nhom_ribbon"] {{ background: #F7FAFD; border: 1px solid #E5ECF3; border-radius: 8px; }}
    QLabel[vai="nhan_ribbon"] {{ color: #4A6785; font-size: 11px; font-weight: 700; letter-spacing: 0.6px;
        background: transparent; border: 0; }}
    QLabel[vai="dong_phu"] {{ color: #DCEBFA; font-size: 12px; }}
    ''' + _qss_the_so()


_BIEU_TUONG = []


def bieu_tuong():
    """Biểu tượng phần mềm: ve_bieu_tuong.icon() - nhiều cỡ từ pabt/bieu_tuong.png (cùng nguồn với file .ico của exe / Desktop), nhớ lại
    sau lần đầu; lỗi vẽ thì dùng ảnh pabt/bieu_tuong.png."""
    if not _BIEU_TUONG:
        try:
            from .ve_bieu_tuong import icon
            _BIEU_TUONG.append(icon())
        except Exception:                               # noqa: BLE001 - biểu tượng không được làm hỏng khởi động
            from PySide6.QtGui import QIcon
            from . import tai_nguyen
            _BIEU_TUONG.append(QIcon(str(tai_nguyen('bieu_tuong.png'))))
    return _BIEU_TUONG[0]


class KhungLogo(QWidget):
    """Logo phần mềm (thanh tiêu đề 20 px, banner 22 / 32 px). Nền trong suốt, KHÔNG cắt khung (0.9.87 Mẫu 3: khối pha lê nghiêng có
    viền sáng - cắt bo góc cố định xén mất viền); ảnh lấy theo tỷ lệ màn hình (devicePixelRatioF) cho nét ở 125 / 150%."""

    def __init__(self, canh: int = 32, parent=None):
        super().__init__(parent)
        self._canh = canh
        self.setFixedSize(canh, canh)
        self.setProperty('vai', 'logo')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._pm = None

    def paintEvent(self, e):
        from PySide6.QtGui import QPainter
        tl = self.devicePixelRatioF() if hasattr(self, 'devicePixelRatioF') else 1.0
        n = max(1, int(round(self._canh * tl)))
        if self._pm is None or self._pm.width() != n:
            self._pm = bieu_tuong().pixmap(n, n)
            self._pm.setDevicePixelRatio(self._pm.width() / self._canh if self._pm.width() else 1.0)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawPixmap(self.rect(), self._pm)
        p.end()


# ---------------------------------------------------------------- biểu tượng nút (ký hiệu Segoe Fluent Icons / MDL2 Assets)
# (mẫu trên chữ đã bỏ dấu, mã ký hiệu) - xét theo thứ tự; Windows 7 không có các phông này thì nút chỉ hiện chữ
KY_HIEU = [
    (r'^danh sach ho', 0xE716), (r'tong quat ho', 0xE8FD), (r'^quyet dinh( phe duyet)?$', 0xE8A5), (r'tong hop tien', 0xE9F9),
    (r'theo doi tien do|^tien do|theo doi chi tra', 0xE9D2), (r'^mau in', 0xE72C), (r'^bang tong hop', 0xE80A), (r'^hoan tac', 0xE7A7), (r'^lam lai', 0xE7A6),
    (r'du an tren may chu', 0xE839), (r'mang ve lam offline', 0xE896), (r'dua len may chu', 0xE898),
    (r'^dang nhap', 0xE77B), (r'du an moi', 0xE710), (r'^mo du an|^mo du toan', 0xE8E5), (r'luu du an thanh', 0xE792), (r'^(luu|save)', 0xE74E),
    (r'^thuc hien', 0xE768),
    (r'nhap file excel|^nhap tu|^tu file|^tu danh sach|^tu du an', 0xE8B5), (r'thong tin du an|gioi thieu', 0xE946),
    (r'^ho so ho', 0xE77B), (r'^them ho', 0xE8FA), (r'lap phuong an', 0xE70F), (r'kiem tra loi|kiem tra lai', 0xE9D5),
    (r'bo don gia|don gia boi thuong', 0xE8FD), (r'don gia rieng|don gia dac biet', 0xE8EC), (r'ra soat', 0xE721), (r'quy chuan|tinh mat do', 0xE8F1), (r'du toan', 0xE8EF),
    (r'^xuat danh sach', 0xEDE1), (r'^trang chu|^man hinh chinh', 0xE80F),
    (r'thay bang gia', 0xE895), (r'bang gia gan san', 0xE7A7), (r'^bang gia dat', 0xE707), (r'^ban do thua|ban ve cad', 0xE826),
    (r'du thao|niem yet', 0xE8A5), (r'^so sanh', 0xE8AB),
    (r'^dot trinh', 0xE8B7), (r'trang thai ho', 0xE73A), (r'nhap quyet dinh', 0xE8A5), (r'bao cao tong hop|bao cao tien do', 0xE9F9),
    (r'doi chieu', 0xE7C3), (r'cap nhat mau in', 0xE72C), (r'cap nhat phan mem|^cap nhat', 0xE895),
    (r'^(in|xuat)\b|pdf', 0xE749), (r'^xoa|^go ban', 0xE74D), (r'^them', 0xE710), (r'^(sua|ap don gia|ap dung)', 0xE70F),
    (r'^(huy|dong|cancel|close)', 0xE711), (r'goi y', 0xE82F), (r'^chon tat ca', 0xE73E), (r'^(chon|tra |tim)', 0xE721),
    (r'^tach', 0xE8C6),
    (r'^(gop|chuyen|dua |bo ho)', 0xE8AB), (r'mo thu muc', 0xE838),
]
_PHONG_KY_HIEU = None


def _phong_ky_hieu():
    global _PHONG_KY_HIEU
    if _PHONG_KY_HIEU is None:
        from PySide6.QtGui import QFontDatabase
        try:
            ds = set(QFontDatabase.families())               # Qt6: hàm tĩnh
        except TypeError:
            ds = set(QFontDatabase().families())             # Qt5 (bản Windows 7/8)
        _PHONG_KY_HIEU = next((f for f in ('Segoe Fluent Icons', 'Segoe MDL2 Assets') if f in ds), '')
    return _PHONG_KY_HIEU


def icon_ky_hieu(ma: int, mau: str = '#FFFFFF', co: int = 24):
    """QIcon vẽ từ ký hiệu của phông biểu tượng Windows, hoặc None nếu máy không có phông / ký hiệu."""
    from PySide6.QtGui import QFont, QFontMetrics, QIcon, QPainter, QPixmap
    phong = _phong_ky_hieu()
    if not phong:
        return None
    f = QFont(phong)
    f.setPixelSize(int(co * 0.8))
    if not QFontMetrics(f).inFontUcs4(ma):
        return None
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPainterPath, QPen
    pm = QPixmap(co * 2, co * 2)                     # vẽ gấp đôi cho nét mịn trên màn hình phóng to
    pm.fill(Qt.GlobalColor.transparent)
    f.setPixelSize(int(co * 1.5))
    # ký hiệu Segoe Fluent / MDL2 nét mảnh: vẽ thành đường viền rồi tô kèm nét bút ~1,6 px (cỡ 1x) để mọi biểu tượng
    # có độ dày nét đồng nhất, dễ nhìn (giống bộ Lucide / Material)
    duong = QPainterPath()
    duong.addText(QPointF(0, 0), f, chr(ma))
    hop = duong.boundingRect()
    duong.translate(pm.width() / 2 - hop.center().x(), pm.height() / 2 - hop.center().y())
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    mau_ = QColor(mau)
    p.setPen(QPen(mau_, max(1.6, co * 0.13), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(mau_)
    p.drawPath(duong)
    p.end()
    return QIcon(pm)


def ky_hieu_nut(chu: str):
    s = bo_dau(re.sub(r'[&….]', ' ', chu or '')).strip(' ◀▶▲▼')
    return next((k for m, k in KY_HIEU if re.search(m, s)), None)


def to_mau(goc: QWidget) -> None:
    """Gán nhóm màu (và biểu tượng) cho các nút trong cửa sổ theo chữ trên nút."""
    for b in [goc, *goc.findChildren(QAbstractButton)]:
        if not isinstance(b, (QPushButton, QToolButton)) or isinstance(b, (QCheckBox, QRadioButton)):
            continue
        n = nhom_nut(b.text())
        if n and b.property('nhom') != n:
            b.setProperty('nhom', n)
            b.style().unpolish(b)
            b.style().polish(b)
        if isinstance(b, QPushButton) and b.icon().isNull() and not b.property('khong_icon'):
            k = ky_hieu_nut(b.text())
            ic = icon_ky_hieu(k, mau_chu_nut(n), 16) if k else None
            if ic is not None:
                b.setIcon(ic)
            else:
                b.setProperty('khong_icon', True)


# Trạng thái của băng / nhãn thông báo: (chữ, nền, viền) - một bảng màu cho cả phần mềm (trước: chuỗi QSS chép tay từng nơi)
MAU_TRANG_THAI = {
    'dat': ('#1E6B34', '#EAF6EC', '#CDE8D2'),          # xong, khớp
    'tin': ('#1F4E79', '#EAF2FB', '#C9DCF2'),          # thông tin trung tính
    'canh_bao': ('#7A4B00', '#FFF4DB', '#F1D9A0'),     # cần xem lại (không phải lỗi của người dùng)
    'loi': ('#A12A1F', '#FCEDEB', '#F3CFCA'),          # lỗi phải xử lý mới làm tiếp được
}


def kieu_trang_thai(muc: str, loai: str = 'QLabel', dam: bool = True) -> str:
    """QSS màu trạng thái (MAU_TRANG_THAI) cho một loại thành phần - một nguồn màu cho băng kết quả, ô cảnh báo..."""
    chu_mau, nen, vien = MAU_TRANG_THAI[muc]
    return (f'{loai} {{ {"font-weight: 600; " if dam else ""}padding: 5px 8px; color: {chu_mau}; background: {nen}; '
            f'border: 1px solid {vien}; border-radius: 6px; }}')


def dat_trang_thai(nhan, muc: str, chu: str) -> None:
    """Đặt chữ + màu trạng thái cho QLabel (băng kết quả, dòng báo trong hộp thoại). muc: dat / tin / canh_bao / loi."""
    nhan.setText(chu)
    nhan.setStyleSheet(kieu_trang_thai(muc))


class con_tro_cho:
    """Con trỏ chờ (đồng hồ cát) trong khối `with`; LUÔN trả lại con trỏ thường kể cả khi lỗi.

        with con_tro_cho():
            ket_qua = viec_lau()

    Trước đây 16 hàm viết tay setOverrideCursor / restoreOverrideCursor (trả lại ở từng nhánh except): lỗi bất ngờ ngoài các
    nhánh đó làm con trỏ kẹt đồng hồ cát - người dùng tưởng phần mềm treo. Lồng nhau được (Qt đếm số lần đặt / trả)."""

    def __enter__(self):
        from PySide6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        return self

    def __exit__(self, *_):
        from PySide6.QtWidgets import QApplication
        QApplication.restoreOverrideCursor()
        return False                                    # không nuốt lỗi: để nơi gọi xử lý / báo


HIEN_CHO_SAU_MS = 400                                   # chay_nen: việc lâu hơn bấy nhiêu ms thì hiện hộp "Đang xử lý…"


def chay_nen(cha, ham, chu: str = 'Đang xử lý…'):
    """Chạy ham() ở luồng nền, cửa sổ vẫn vẽ lại / không bị Windows báo "Không phản hồi" (việc nặng: tạo dự án, nhập Excel hàng nghìn
    hộ). Quá HIEN_CHO_SAU_MS hiện hộp chờ; trong lúc chờ không nhận bấm phím / chuột (tránh bấm chồng lệnh). Trả giá trị của ham,
    lỗi của ham ném lại ở đây như gọi thẳng. ham KHÔNG được đụng widget Qt hay kết nối CSDL của cửa sổ - tự mở kết nối riêng."""
    import threading
    import time
    from PySide6.QtCore import QEventLoop
    from PySide6.QtWidgets import QProgressDialog
    kq = {}

    def chay():
        try:
            kq['gt'] = ham()
        except BaseException as e:                      # noqa: B036 - chuyển mọi lỗi về luồng giao diện
            kq['loi'] = e
    luong = threading.Thread(target=chay, daemon=True)
    luong.start()
    luong.join(0.05)                                    # việc nhanh: xong luôn, không dựng vòng chờ
    if luong.is_alive():
        vong = QEventLoop()
        hop = []
        bat_dau = time.monotonic()
        dong_ho = QTimer()
        dong_ho.setInterval(50)

        def kiem():
            if not luong.is_alive():
                vong.quit()
            elif not hop and (time.monotonic() - bat_dau) * 1000 >= HIEN_CHO_SAU_MS:
                h = QProgressDialog(chu, None, 0, 0, cha)              # 0..0: thanh chạy qua lại (không biết trước thời gian)
                h.setWindowTitle('LARC')
                h.setWindowModality(Qt.WindowModality.WindowModal)
                h.setMinimumDuration(0)
                h.setCancelButton(None)
                h.show()
                hop.append(h)
        dong_ho.timeout.connect(kiem)
        dong_ho.start()
        vong.exec(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
        dong_ho.stop()
        for h in hop:
            h.close()
            h.deleteLater()
    luong.join()
    if 'loi' in kq:
        raise kq['loi']
    return kq.get('gt')


def vai(w: QWidget, ten: str) -> QWidget:
    """Đặt vai trò hiển thị (nhan / tieu_de / bang_ten) cho nhãn."""
    w.setProperty('vai', ten)
    w.style().unpolish(w)
    w.style().polish(w)
    return w


TEN_PHAN_MEM = 'PHẦN MỀM LẬP PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ'


class KhungCao(QFrame):
    """Khung tự tăng chiều cao khi nội dung xuống dòng (chữ dài, nhóm nút) lúc cửa sổ hẹp."""

    def _cao(self):
        lo = self.layout()
        if lo is not None and lo.hasHeightForWidth():
            h = lo.totalHeightForWidth(self.width())
            if h != self.minimumHeight() or h != self.maximumHeight():
                self.setFixedHeight(h)          # đúng bằng nội dung: không bị ép thấp, không bị nới thừa khoảng trống

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._cao()

    def showEvent(self, e):
        super().showEvent(e)
        self._cao()


MAU_BANG = ('#0F3866', '#154D8C', '#1A5FA6')   # banner: xanh sapphire
VIEN_DAY = '#38BDF8'                           # viền đáy banner, 2px
MAU_PHU_DE = '#E0F2FE'                         # dòng cơ quan: xanh băng trắng sáng
MAU_DON_VI_BANNER = '#FCD34D'                  # 0.9.80: tên đơn vị trên banner navy - vàng kim nhạt (đọc rõ hơn xanh băng)
VANG = TOKEN['nhan']                           # điểm nhấn nút (không còn tô dòng cơ quan)
QSS_CHIP = (
    'background: rgba(15, 23, 42, 0.45); border: 1px solid rgba(148, 163, 184, 0.25); '
    'border-radius: 8px; padding: 1px 8px; font-size: 10.5px; font-weight: 500;')
MAU_MENU = '#081226'
VIEN_MENU = '#1A2846'


def _luoi_thua(cot: int = 7, hang: int = 3, hat: int = 7) -> list:
    """Họa tiết bản đồ địa chính: lưới thửa đất méo nhẹ (tọa độ 0..1), cố định theo hạt để lần vẽ nào cũng giống nhau."""
    import random
    r = random.Random(hat)
    diem = [[(i / cot + (r.uniform(-0.35, 0.35) / cot if 0 < i < cot else 0),
              j / hang + (r.uniform(-0.3, 0.3) / hang if 0 < j < hang else 0)) for j in range(hang + 1)] for i in range(cot + 1)]
    thua = []
    for i in range(cot):
        for j in range(hang):
            a, b, c, d = diem[i][j], diem[i + 1][j], diem[i + 1][j + 1], diem[i][j + 1]
            if r.random() < 0.3:                        # thửa chia đôi theo đường chéo (thửa tam giác, hình thể không đều)
                thua += [[a, b, c], [a, c, d]]
            else:
                thua.append([a, b, c, d])
    return thua


_THUA = _luoi_thua()
_THUA_THU_HOI = 9                                       # thửa tô vàng nét đứt: thửa đất thu hồi


class BangToChuc(KhungCao):
    """Băng tiêu đề nền xanh đậm, họa tiết thửa đất địa chính mờ bên phải (một thửa viền vàng: đất thu hồi), vạch vàng chân băng."""

    def paintEvent(self, e):
        from PySide6.QtCore import QPointF, QRectF
        from PySide6.QtGui import QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        w, h = r.width(), r.height()
        khung = QPainterPath()
        khung.addRoundedRect(r, 12, 12)
        g = QLinearGradient(r.topLeft(), r.topRight())
        for t, m in zip((0, 0.55, 1), MAU_BANG):
            g.setColorAt(t, QColor(m))
        p.fillPath(khung, g)
        p.setClipPath(khung)
        sang = QRadialGradient(QPointF(r.left() + 35, r.top() + h * 0.5), h * 1.5)    # quầng sáng sau biểu tượng
        sang.setColorAt(0, QColor(255, 255, 255, 34))
        sang.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(r, sang)
        x0, rong = r.left() + w * 0.62, w * 0.38 + 2
        for i, pts in enumerate(_THUA):
            da_giac = QPolygonF([QPointF(x0 + u * rong, r.top() - 4 + v * (h + 8)) for u, v in pts])
            if i == _THUA_THU_HOI:
                p.setPen(QPen(QColor(37, 99, 235, 190), 1.6, Qt.PenStyle.DashLine))
                p.setBrush(QColor(37, 99, 235, 40))
            else:
                p.setPen(QPen(QColor(255, 255, 255, 40), 1))
                p.setBrush(QColor(255, 255, 255, 12 if i % 4 == 0 else 0))
            p.drawPolygon(da_giac)
        mo = QLinearGradient(QPointF(x0, 0), QPointF(x0 + rong * 0.45, 0))            # họa tiết mờ dần về phía chữ
        mo.setColorAt(0, QColor(MAU_BANG[1]))
        mo.setColorAt(1, QColor(17, 61, 106, 0))
        p.fillRect(QRectF(x0 - 1, r.top(), rong * 0.45 + 1, h), mo)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(VIEN_DAY))
        p.fillRect(QRectF(r.left(), r.bottom() - 2, w, 2), QColor(VIEN_DAY))
        p.end()


class NhanRutGon(QLabel):
    """Nhãn một dòng tự rút gọn "…" khi không đủ chỗ (chữ đầy đủ ở tooltip): chữ dài không ép cửa sổ rộng hơn màn hình
    1366 px. text() trả chữ đầy đủ."""

    def __init__(self, chu: str = '', parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(60)
        self._chu = ''
        self.setText(chu)

    def setText(self, chu: str):
        self._chu = chu
        self.setToolTip(chu)
        self._ve()

    def text(self) -> str:
        return self._chu

    def sizeHint(self):                             # bố cục cấp đủ chỗ cho cả dòng khi còn rộng
        return QSize(self.fontMetrics().horizontalAdvance(self._chu) + 4, super().sizeHint().height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._ve()

    def changeEvent(self, e):                       # đổi phông (QSS, phóng to / thu nhỏ): đo lại
        super().changeEvent(e)
        if e.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._ve()

    def _ve(self):
        QLabel.setText(self, self.fontMetrics().elidedText(self._chu, Qt.TextElideMode.ElideRight, max(self.width(), 1)))


def bang_to_chuc(phai: str = '', nut: tuple = ()) -> QFrame:
    """Băng tiêu đề GỌN (~60 px, trước 0.9.18: 112 px - màn hình 1366x768 mất gần 1/5 chiều cao): biểu tượng | dòng 1: tên
    phần mềm + nút nếu có (nut; Hoàn tác / Làm lại từ 11/10/2026 ở menu Chỉnh sửa) / dòng 2: tổ chức làm nhiệm vụ bồi thường (vàng) ·
    trực thuộc - địa chỉ (rút gọn "…" khi hẹp, đủ ở tooltip) | phiên bản + BẢN THỬ NGHIỆM cùng một hàng (pabt/to_chuc.py)."""
    from . import to_chuc
    khung = BangToChuc()
    khung.setProperty('vai', 'bang_to_chuc')
    lo = QHBoxLayout(khung)
    lo.setContentsMargins(10, 4, 12, 5)
    lo.setSpacing(8)
    lo.addWidget(KhungLogo(), 0, Qt.AlignmentFlag.AlignVCenter)
    cot = QVBoxLayout()
    cot.setSpacing(1)
    tieu_de = NhanRutGon(TEN_PHAN_MEM)
    tieu_de.setProperty('vai', 'ten_phan_mem')
    dong_dau = QHBoxLayout()
    dong_dau.setSpacing(6)
    dong_dau.addWidget(tieu_de, 1)
    if nut:
        dong_dau.addSpacing(8)
    for b in nut:
        b.setProperty('vai', 'nut_bang')
        dong_dau.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
    dong_dau.addStretch(0)
    cot.addLayout(dong_dau)
    dong2 = QHBoxLayout()
    dong2.setSpacing(10)
    ten = QLabel(f'{to_chuc.TEN}')
    ten.setProperty('vai', 'ten_to_chuc')
    dong2.addWidget(ten)
    phu = NhanRutGon(f'Trực thuộc {to_chuc.TRUC_THUOC}   •   {to_chuc.DIA_CHI}')
    phu.setProperty('vai', 'dong_phu')
    dong2.addWidget(phu, 1)
    khung.nhan_to_chuc, khung.nhan_phu = ten, phu       # dat_to_chuc: đơn vị của dự án đang mở
    cot.addLayout(dong2)
    lo.addLayout(cot, 1)
    from . import BAN_THU_NGHIEM, NHAN_THU_NGHIEM
    hang_phai = QHBoxLayout()
    hang_phai.setSpacing(8)
    if phai:
        p = QLabel(phai)
        p.setProperty('vai', 'phien_ban')
        p.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hang_phai.addWidget(p, 0, Qt.AlignmentFlag.AlignVCenter)
    if BAN_THU_NGHIEM:                                  # nhãn vàng đặc cạnh phiên bản: nhìn là biết không phải bản chính thức
        tn = QLabel(NHAN_THU_NGHIEM)
        tn.setProperty('vai', 'thu_nghiem')
        tn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tn.setToolTip('Bản thử nghiệm: dùng để kiểm tra trước khi phát hành chính thức.')
        khung.nhan_thu_nghiem = tn
        hang_phai.addWidget(tn, 0, Qt.AlignmentFlag.AlignVCenter)
    else:                                               # bản phát hành: gói bản quyền (ban_quyen.mo_ta - cổng chờ bản quyền)
        from .ban_quyen import mo_ta
        bq = QLabel(mo_ta())
        bq.setProperty('vai', 'ban_quyen')
        bq.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bq.setToolTip('Chế độ sử dụng nội bộ - chưa kích hoạt bản quyền thương mại.')
        khung.nhan_ban_quyen = bq
        hang_phai.addWidget(bq, 0, Qt.AlignmentFlag.AlignVCenter)
    if hang_phai.count():
        lo.addLayout(hang_phai)
    return khung


def dat_to_chuc(khung, ten: str = '', phu: str = '') -> None:
    """Dòng đơn vị trên băng tiêu đề theo dự án đang mở (0.9.23 - lộ trình người dùng: thông tin đơn vị lấy theo dự án, không cố
    định một đơn vị); trống = đơn vị mặc định của máy (to_chuc.py)."""
    from . import to_chuc
    khung.nhan_to_chuc.setText(ten or to_chuc.TEN)
    khung.nhan_phu.setText(phu or f'Trực thuộc {to_chuc.TRUC_THUOC}   •   {to_chuc.DIA_CHI}')


class XepDong(QLayout):
    """Bố cục xếp nối tiếp, hết chỗ thì xuống dòng (màn hình hẹp không làm cửa sổ tràn ra ngoài)."""

    def __init__(self, parent=None, cach: int = 6):
        super().__init__(parent)
        self._muc = []
        self._cach = cach

    def addItem(self, it):
        self._muc.append(it)

    def count(self):
        return len(self._muc)

    def itemAt(self, i):
        return self._muc[i] if 0 <= i < len(self._muc) else None

    def takeAt(self, i):
        return self._muc.pop(i) if 0 <= i < len(self._muc) else None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, rong):
        return self._xep(QRect(0, 0, rong, 0), True)

    def setGeometry(self, r):
        super().setGeometry(r)
        self._xep(r, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        s = QSize()
        for it in self._muc:
            s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return s + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _xep(self, r, chi_tinh: bool) -> int:
        """Xếp theo dòng; phần rộng còn thừa của mỗi dòng chia đều cho các mục để dàn kín chiều ngang."""
        m = self.contentsMargins()
        vung = r.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        dong, hang, rong = [], [], 0
        for it in self._muc:
            w = it.sizeHint().width()
            if hang and rong + self._cach + w > vung.width():
                dong.append(hang)
                hang, rong = [], 0
            rong += (self._cach if hang else 0) + w
            hang.append(it)
        if hang:
            dong.append(hang)
        y = vung.y()
        for i, hang in enumerate(dong):
            ws = [it.sizeHint().width() for it in hang]
            du = max(vung.width() - sum(ws) - self._cach * (len(hang) - 1), 0)
            cao = max(it.sizeHint().height() for it in hang)
            x = vung.x()
            for it, w in zip(hang, ws):
                them = du * w // sum(ws) if sum(ws) else 0
                if not chi_tinh:
                    it.setGeometry(QRect(QPoint(x, y), QSize(w + them, cao)))
                x += w + them + self._cach
            y += cao + (self._cach if i < len(dong) - 1 else 0)
        return y - r.y() + m.bottom()


def mau_icon(chu: str) -> str:
    """Màu biểu tượng nút lệnh trên thanh (nút nền nhạt): màu chính của nhóm."""
    n = nhom_nut(chu)
    return MAU[n][0] if n and n != 'nhat' else CHINH


def nut_lenh(a, co_icon: int = 18, duoi: bool = False, mau: str | None = None) -> QToolButton:
    """Nút lệnh trên thanh / menu, nền nhạt theo màu nhóm. duoi: biểu tượng trên, chữ dưới (kiểu ribbon nhỏ, nút hẹp).
    mau: ép màu biểu tượng (menu trái đơn sắc Deep Navy)."""
    from PySide6.QtWidgets import QSizePolicy
    b = QToolButton()
    a.setIconText(a.text().rstrip('…').rstrip('.'))     # Qt5 không tự bỏ dấu "…" như Qt6
    k = ky_hieu_nut(a.text())
    ic = icon_ky_hieu(k, mau or mau_icon(a.text()), co_icon) if k else None
    if ic is not None:
        a.setIcon(ic)
    b.setDefaultAction(a)
    b.setProperty('ribbon', '1')
    if ic is None:
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
    else:
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon if duoi else Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    b.setIconSize(QSize(co_icon, co_icon))
    b.setMinimumHeight(46 if duoi and ic is not None else 32)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return b


def do_bong(w: QWidget, mo: int = 18, lech: int = 3, dam: int = 38) -> QWidget:
    """Bóng đổ nhẹ dưới khung (chỉ Qt6: Qt5 trên màn hình phóng to làm mờ chữ trong khung)."""
    import pabt
    if not getattr(pabt, 'QT5', False):
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        e = QGraphicsDropShadowEffect(w)
        e.setBlurRadius(mo)
        e.setOffset(0, lech)
        e.setColor(QColor(16, 42, 70, dam))
        w.setGraphicsEffect(e)
    return w


class TheChao(QFrame):
    """Thẻ tác vụ màn hình chào (210 x 135, bo 12px, đổ bóng): biểu tượng 38px + tên lệnh đậm + mô tả phụ, TẤT CẢ nằm trong thẻ;
    mỗi loại ('moi' / 'mo' / 'excel', `MAU_THE_CHAO`) một màu, viền đậm khi rê chuột; bấm ở đâu trong thẻ cũng chạy lệnh.
    Lưu ý: kiểu viết trong QSS là QFrame[vai="the_chao"][loai=…] - bộ chọn theo tên lớp Python (TheChao) Qt không hiểu."""

    def __init__(self, parent=None, loai: str | None = None):
        super().__init__(parent)
        self.setProperty('vai', 'the_chao')
        if loai:
            self.setProperty('loai', loai)
        self._loai = loai
        self._nut = None
        self.setFixedSize(*KICH_THE_CHAO)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        do_bong(self, 22, 3, 42)

    def dat_noi_dung(self, nut: QToolButton, phu: str) -> QLabel:
        """Xếp nút lệnh (biểu tượng trên, chữ dưới) và dòng mô tả vào thẻ; nút lấy tên #the_chao_nut (kiểu trong suốt, chữ 14,5pt đậm)
        và biểu tượng 38px màu của loại thẻ (vẽ lại khi lệnh đổi trạng thái: Qt chép biểu tượng của QAction đè lên). Trả nhãn mô tả."""
        from PySide6.QtWidgets import QSizePolicy
        self._nut = nut
        nut.setObjectName('the_chao_nut')
        nut.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        nut.setMinimumHeight(0)
        nut.setIconSize(QSize(CO_ICON_THE_CHAO, CO_ICON_THE_CHAO))
        a = nut.defaultAction()
        k = ky_hieu_nut(a.text()) if a is not None else None
        mau = MAU_THE_CHAO.get(self._loai or '', ('', '', '', '', CHINH))[4]
        ic = icon_ky_hieu(k, mau, CO_ICON_THE_CHAO) if k else None
        if ic is not None:
            nut.setIcon(ic)
            if a is not None:
                def gan_lai(nut=nut, ic=ic):
                    try:
                        nut.setIcon(ic)
                    except RuntimeError:                # nút đã bị hủy
                        pass
                a.changed.connect(lambda: QTimer.singleShot(0, gan_lai))
        lo = QVBoxLayout(self)
        lo.setContentsMargins(10, 10, 10, 12)
        lo.setSpacing(4)
        lo.addWidget(nut, 1)
        lb = QLabel(phu)
        lb.setProperty('vai', 'the_chao_phu')
        lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)      # bấm vào mô tả = bấm thẻ
        lo.addWidget(lb)
        return lb

    def mouseReleaseEvent(self, e):
        if (self._nut is not None and e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.pos())
                and self._nut.isEnabled()):
            self._nut.click()
        super().mouseReleaseEvent(e)

    def enterEvent(self, e):
        self.setProperty('hover', '1')
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.setProperty('hover', '0')
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(e)


def tao_dai_nhan_dien(mb=None):
    """Chỉ biểu tượng, canh giữa hàng menu 28px."""
    dai = QFrame()
    dai.setObjectName('dai_nhan_dien')
    dai.setFixedHeight(28)
    dai.setStyleSheet('QFrame#dai_nhan_dien { background: transparent; border: 0; }')
    lo = QHBoxLayout(dai)
    lo.setContentsMargins(6, 0, 2, 0)
    lo.setSpacing(0)
    lo.addWidget(KhungLogo(22), 0, Qt.AlignmentFlag.AlignVCenter)
    return dai


CAO_MENU = 28          # hàng menu trắng tối thiểu; thực tế = max(CAO_MENU, sizeHint): DPI 125% mục menu cao 30 px - ép 28 px
                       # làm Qt dồn MỌI mục (Tệp tin, Chỉnh sửa…) vào nút "»" (0.9.63-0.9.64 trên máy dựng)
CAO_BANNER = 48        # banner xanh: tên phần mềm + cơ quan canh giữa theo chiều dọc (0.9.82: 60 -> 48 theo đặc tả V10 Brand Strip)


def tao_banner_ten():
    """Banner xanh dưới menu trắng. Trái: tên phần mềm + cơ quan (rút "…" khi hẹp). Phải: khung `goc_phai` KHÓA CỨNG - ô dự
    án, phiên bản, tem bản quyền (trạng thái máy đơn / LAN: chỉ ở thanh trạng thái): kích thước cố định theo nội dung, không bao giờ co / bị cắt; phần chữ bên trái
    nhường chỗ (người dùng 12/10/2026). Nút thu nhỏ / phóng to / đóng là của thanh tiêu đề Windows (cửa sổ có khung) - đừng
    đổi sang cửa sổ không khung."""
    from . import __version__, to_chuc
    from .ban_quyen import mo_ta
    from PySide6.QtWidgets import QSizePolicy
    k = QFrame()
    k.setObjectName('banner_ten')
    k.setFixedHeight(CAO_BANNER)
    k.setStyleSheet(
        '#banner_ten { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, '
        f'stop:0 {MAU_BANG[0]}, stop:0.5 {MAU_BANG[1]}, stop:1 {MAU_BANG[2]}); '
        f'border: 0; border-bottom: 2px solid {VIEN_DAY}; }}')
    hang = QHBoxLayout(k)
    hang.setContentsMargins(18, 0, 14, 2)           # 2 px dưới = viền đáy: chữ nằm giữa phần nền xanh
    hang.setSpacing(16)
    cot = QVBoxLayout()
    cot.setSpacing(1)
    cot.setContentsMargins(0, 0, 0, 0)
    ten = NhanRutGon(TEN_PHAN_MEM)                  # sizePolicy Ignored: chữ dài không ép cửa sổ rộng ra
    ten.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    ten.setStyleSheet(
        'QLabel { color: #FFFFFF; font-size: 15px; font-weight: 700; letter-spacing: 0.4px; '
        'background: transparent; border: 0; }')
    co_quan = NhanRutGon(to_chuc.TEN)
    co_quan.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    co_quan.setStyleSheet(
        f'QLabel {{ color: {MAU_DON_VI_BANNER}; font-size: 11.5px; font-weight: 600; letter-spacing: 0.6px; '
        'background: transparent; border: 0; }')
    cot.addStretch(1)
    cot.addWidget(ten)
    cot.addWidget(co_quan)
    cot.addStretch(1)
    hang.addLayout(cot, 1)

    goc = QWidget()
    goc.setObjectName('goc_phai')
    goc.setStyleSheet('#goc_phai { background: transparent; }')
    goc.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    lo = QHBoxLayout(goc)
    lo.setContentsMargins(0, 0, 0, 0)
    lo.setSpacing(12)
    # 15/10/2026 (người dùng): bỏ ô "Dự án: …" - tên dự án ở MỘT chỗ: tiêu đề giữa thanh menu trắng (CuaSoChinh.dat_tieu_de)
    phien = QLabel(f'Phiên bản {__version__}')
    phien.setStyleSheet(
        'QLabel { color: #E2E8F0; font-size: 12px; font-weight: 500; background: transparent; border: 0; }')
    bq = QLabel(mo_ta())
    bq.setFixedHeight(24)
    bq.setStyleSheet(
        'QLabel { color: #FFFFFF; background: rgba(255,255,255,0.14); border: 1px solid rgba(255,255,255,0.35); '
        'border-radius: 10px; padding: 0px 10px; font-size: 11px; font-weight: 600; }')
    for w in (phien, bq):                             # 0.9.80: bỏ "● Máy đơn" - trạng thái máy đơn / LAN chỉ ở nút nut_tk thanh trạng thái
        lo.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)
    hang.addWidget(goc, 0, Qt.AlignmentFlag.AlignVCenter)
    k.goc_phai = goc
    k.lb_ten, k.lb_don_vi, k.lb_phien_ban, k.lb_ban_quyen = ten, co_quan, phien, bq
    return k


def vua_cao_menu(mb) -> None:
    """Hàng menu trắng: tối thiểu CAO_MENU, đủ cao cho mục menu theo phông / DPI (thấp hơn thì Qt dồn mục vào nút "»").
    Menu trong thanh tiêu đề hợp nhất (property trong_thanh_td): cao ĐÚNG bằng mục menu - QMenuBar vẽ mục sát mép trên, cao dư
    dồn xuống dưới làm chữ menu cao hơn chữ tiêu đề (người dùng 15/10/2026, màn hình 125%: lệch 4-5 px); bố cục canh giữa thanh."""
    try:
        if mb.property('trong_thanh_td'):
            mb.setFixedHeight(mb.sizeHint().height())
            return
        mb.setFixedHeight(max(CAO_MENU, mb.sizeHint().height()))
    except RuntimeError:
        pass


def _vua_moi_menu(_t=None) -> None:
    from PySide6.QtWidgets import QApplication, QMenuBar
    app = QApplication.instance()
    if app is None:
        return
    for w in app.topLevelWidgets():
        mb = w.menuBar() if hasattr(w, 'menuBar') else None
        if isinstance(mb, QMenuBar):
            vua_cao_menu(mb)


class _BamMenu(QObject):
    """Windows (DPI 125%, hai màn hình): bấm Tệp tin không mở menu — Qt nhận nút nhấn rồi thả chuột làm menu đóng ngay.
    Nuốt nhấn, mở menu khi thả chuột, neo ngay dưới thanh."""

    def __init__(self, mb):
        super().__init__(mb)
        self.mb = mb
        mb.installEventFilter(self)

    def eventFilter(self, obj, e):
        if obj is not self.mb:
            return False
        if e.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange, QEvent.Type.Show):
            QTimer.singleShot(0, lambda mb=self.mb: vua_cao_menu(mb))     # phông đổi lúc hiện (_BoToMau) / phóng to
            return False
        if e.type() == QEvent.Type.MouseButtonDblClick and e.button() == Qt.MouseButton.LeftButton:
            pos = e.position().toPoint() if hasattr(e, 'position') else e.pos()
            a = self.mb.actionAt(pos)
            if a is None or a.menu() is None:
                cua = self.mb.window()
                if cua is not None:
                    if cua.isMaximized():
                        cua.showNormal()
                    else:
                        cua.showMaximized()
                return True
        if e.type() not in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
            return False
        if e.button() != Qt.MouseButton.LeftButton:
            return False
        if any(a.menu() is not None and a.menu().isVisible() for a in self.mb.actions()):
            return False
        # Nuốt nhấn: Qt mở menu lúc nhấn, rồi chính cú thả chuột làm menu đóng ngay (DPI 125%).
        if e.type() == QEvent.Type.MouseButtonPress:
            pos = e.position().toPoint() if hasattr(e, 'position') else e.pos()
            a = self.mb.actionAt(pos) or self.mb.actionAt(QPoint(pos.x(), max(0, self.mb.height() // 2)))
            if a is None or a.menu() is None:
                cua = self.mb.window()
                wh = cua.windowHandle() if cua is not None else None
                if wh is not None and hasattr(wh, 'startSystemMove'):
                    wh.startSystemMove()
            return True
        pos = e.position().toPoint() if hasattr(e, 'position') else e.pos()
        a = self.mb.actionAt(pos) or self.mb.actionAt(QPoint(pos.x(), max(0, self.mb.height() // 2)))
        if a is None or a.menu() is None:
            return True
        menu = a.menu()
        g = self.mb.actionGeometry(a)
        diem = self.mb.mapToGlobal(QPoint(g.x(), self.mb.height()))
        # Mở sau khi cú thả chuột đã xử lý xong. Mở ngay trong sự kiện thả thì menu nhận cú thả và đóng liền.
        QTimer.singleShot(0, lambda m=menu, d=diem: m.popup(d))
        return True


def kieu_menu_bar(mb) -> None:
    """Thanh menu trên dải nhận diện. Vùng bấm trùng chữ mục; cao theo cỡ chữ để không cắt tiêu đề."""
    mb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    mb.setStyleSheet(
        'QMenuBar { background: #FFFFFF; color: #1E293B; font-size: 12.5px; font-weight: 600; border: 0; '
        'border-bottom: 1px solid #E2E8F0; padding: 0px 4px; }'
        'QMenuBar::item { background: transparent; color: #1E293B; font-size: 12.5px; font-weight: 600; '
        'padding: 4px 12px; margin: 0px; border-radius: 4px; }'
        'QMenuBar::item:selected { background: #F1F5F9; color: #0F172A; }'
        'QMenuBar::item:pressed { background: #E2E8F0; color: #0F172A; }')
    vua_cao_menu(mb)
    if getattr(mb, '_bam_menu', None) is None:
        mb._bam_menu = _BamMenu(mb)
    if _vua_moi_menu not in KHI_DOI_TY_LE:
        KHI_DOI_TY_LE.append(_vua_moi_menu)


class KhungLamViecDaTab(QWidget):
    """Bộ điều khiển trang làm việc: trang chính (số nguyên) + widget phụ (hộ / bộ đơn giá / niêm yết) giữ nguyên trong RAM.
    Từ 15/10/2026 (người dùng: thu hồi chiều cao) KHÔNG còn thanh tab hiện trên màn hình - chuyển trang bằng menu trái / thanh
    menu; `bar` chỉ còn là danh sách các trang đang mở (Ctrl+Tab), luôn ẩn, con của khung ẩn này."""
    da_doi = Signal(object)          # khoa đang chọn
    yeu_cau_dong = Signal(int)       # chỉ số tab (cửa sổ chính hỏi lưu rồi mới bo)

    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QStackedWidget, QTabBar
        self.bar = QTabBar(self)
        self.bar.setProperty('vai', 'lam_viec')
        self.bar.setDocumentMode(True)
        self.bar.setExpanding(False)
        self.bar.setDrawBase(False)
        self.bar.setTabsClosable(True)
        self.bar.setMovable(True)
        self.bar.setUsesScrollButtons(True)
        self.bar.tabMoved.connect(self._doi_cho)
        self.stack_phu = QStackedWidget()
        self.khoa = []
        self.widget = {}
        self.bar.currentChanged.connect(self._doi)
        self.bar.tabCloseRequested.connect(self.yeu_cau_dong.emit)
        # chỉ là bộ điều khiển: bar / stack_phu nằm trong bố cục của cửa sổ chính, khung này KHÔNG xếp ở đâu cả. Để hiện thì nó nằm
        # ở góc (0, 0) cửa sổ (100 x 30, trong suốt) và nuốt cú bấm vào "Tệp tin" (0.9.32-0.9.67; người dùng 12/10/2026 - 0.9.51
        # tưởng do DPI). Ẩn hẳn + chuột đi xuyên.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setVisible(False)

    def dam_bao(self, khoa, ten: str | None = None, widget=None, dong_duoc: bool | None = None):
        """Mở hoặc chuyển tab. widget: gắn vào stack phụ (hộ / bộ đơn giá). dong_duoc=False: ẩn nút đóng."""
        from PySide6.QtWidgets import QTabBar
        if khoa in self.khoa:
            i = self.khoa.index(khoa)
        else:
            i = self.bar.addTab(ten or str(khoa))
            self.khoa.append(khoa)
            if dong_duoc is False or (dong_duoc is None and isinstance(khoa, int) and khoa < 0):
                ben = QTabBar.ButtonPosition.RightSide if hasattr(QTabBar, 'ButtonPosition') else QTabBar.RightSide
                self.bar.setTabButton(i, ben, None)
        if widget is not None:
            self.widget[khoa] = widget
            if self.stack_phu.indexOf(widget) < 0:
                self.stack_phu.addWidget(widget)
            self.stack_phu.setCurrentWidget(widget)
        elif self.widget.get(khoa) is not None:
            # trang phụ đã mở (hộ đang soạn / Niêm yết / Đơn giá): chuyển khung hiển thị về đúng trang đó. Trước 16/10/2026 chỉ đổi
            # tab ẩn (thanh tab đã bỏ, tín hiệu bị chặn) -> mở Niêm yết rồi bấm lại Lập phương án vẫn thấy Niêm yết
            self.stack_phu.setCurrentWidget(self.widget[khoa])
        if ten:
            self.bar.setTabText(i, ten)
        self.bar.blockSignals(True)
        self.bar.setCurrentIndex(i)
        self.bar.blockSignals(False)
        self._hien_thanh()
        return i

    def _hien_thanh(self):
        """Thanh tab không hiện nữa (15/10/2026): mọi trang mở bằng menu trái / thanh menu - trước đây hiện khi có từ 2 tab."""
        self.bar.setVisible(False)

    def chon(self, khoa) -> bool:
        if khoa not in self.khoa:
            return False
        self.bar.setCurrentIndex(self.khoa.index(khoa))
        return True

    def bo(self, i: int, xoa_widget: bool = True):
        """Gỡ tab thứ i. Trả (khoa, widget) hoặc None."""
        if i < 0 or i >= len(self.khoa):
            return None
        khoa = self.khoa.pop(i)
        self.bar.removeTab(i)
        self._hien_thanh()
        w = self.widget.pop(khoa, None)
        if w is not None and xoa_widget:
            self.stack_phu.removeWidget(w)
            w.setProperty('nhung_tab', False)
            w.deleteLater()
        return khoa, w

    def _doi_cho(self, tu: int, den: int):
        """Kéo tab đổi vị trí: khóa đi cùng chỉ số tab."""
        if tu == den or tu < 0 or den < 0 or tu >= len(self.khoa) or den >= len(self.khoa):
            return
        k = self.khoa.pop(tu)
        self.khoa.insert(den, k)

    def ke(self, buoc: int = 1):
        n = self.bar.count()
        if n:
            self.bar.setCurrentIndex((self.bar.currentIndex() + buoc) % n)

    def doi_khoa(self, cu, moi, ten: str | None = None):
        """Đổi khóa tab (vd. hộ A → hộ B trong cùng cửa sổ soạn) mà không tạo widget mới."""
        if cu not in self.khoa:
            return
        i = self.khoa.index(cu)
        w = self.widget.pop(cu, None)
        self.khoa[i] = moi
        if w is not None:
            self.widget[moi] = w
        if ten:
            self.bar.setTabText(i, ten)

    def _doi(self, i: int):
        if i < 0 or i >= len(self.khoa):
            return
        khoa = self.khoa[i]
        w = self.widget.get(khoa)
        if w is not None:
            self.stack_phu.setCurrentWidget(w)
        self.da_doi.emit(khoa)


def thanh_lenh(nhom: list) -> QFrame:
    """Khu vực nút lệnh: một khung trắng, mỗi nhóm một thẻ có tên nhóm (chữ nhỏ) phía trên và hàng nút biểu tượng + chữ;
    các thẻ dàn kín chiều ngang, màn hình hẹp thì tự xuống dòng. nhom: [(tên nhóm, [QAction...])]."""
    khung = KhungCao()
    khung.setProperty('vai', 'ribbon')
    lo = XepDong(khung, 6)
    lo.setContentsMargins(7, 6, 7, 7)
    for ten, ds in nhom:
        the = QFrame()
        the.setProperty('vai', 'nhom_ribbon')
        o = QVBoxLayout(the)
        o.setContentsMargins(7, 4, 7, 6)
        o.setSpacing(3)
        nhan = QLabel((ten or '').upper())              # nhóm không tên (Màn hình chính, 0.9.70): thẻ không chữ nhóm
        nhan.setProperty('vai', 'nhan_ribbon')
        o.addWidget(nhan)
        hang = QHBoxLayout()
        hang.setSpacing(4)
        for a in ds:
            b = nut_lenh(a, 20, duoi=True)
            b.setProperty('nho', '1')
            hang.addWidget(b)
        o.addLayout(hang)
        lo.addWidget(the)
    return do_bong(khung, 16, 2, 30)


class NhanBam(QLabel):
    """Nhãn bấm được (tiêu đề nhóm menu trái): gọi self.bam() khi nhả chuột trái."""

    def __init__(self, *a):
        super().__init__(*a)
        self.bam = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.bam is not None and self.rect().contains(e.pos()):
            self.bam()
        super().mouseReleaseEvent(e)


# QSettings: tên các nhóm menu trái đang đóng, nối bằng "|". 0.9.23 menu 5 nhóm mới: khóa mới (nhóm cũ không còn) - lần đầu
# dùng nhóm đóng sẵn mặc định
KHOA_NHOM_DONG = 'giao_dien/menu_trai_dong_4'    # 0.9.88: đổi thứ tự nhóm (Đơn giá & bảng giá xuống cuối) - đóng sẵn theo NHOM_DONG_MAC_DINH mới


def _doc_nhom_dong(mac_dinh: tuple) -> set:
    from PySide6.QtCore import QSettings
    try:
        v = QSettings('PABT', 'PABT').value(KHOA_NHOM_DONG, None)
    except Exception:
        v = None
    if v is None:
        return set(mac_dinh)
    return {TEN_NHOM_CU.get(x, x) for x in str(v).split('|') if x}


# tên nhóm menu trước 0.9.20 (đã nhớ trong QSettings) -> tên ngắn mới: nhóm người dùng đã đóng vẫn đóng
TEN_NHOM_CU = {'Hồ sơ và phương án': 'Hồ sơ, phương án', 'Bảng tổng hợp': 'Tổng hợp',
               'Trình, theo dõi tiến độ': 'Trình duyệt, tiến độ', 'In ấn, báo cáo': 'In, báo cáo',
               # 0.9.88: tên nhóm đánh số cũ -> số mới (Đơn giá & bảng giá 3 -> 6, các nhóm 4, 5, 6 lên 3, 4, 5)
               '3. Đơn giá & bảng giá': '6. Đơn giá & bảng giá', '4. Lập phương án': '3. Lập phương án',
               '5. Tổng hợp & trình duyệt': '4. Tổng hợp & trình duyệt', '6. Phê duyệt & bàn giao': '5. Phê duyệt & bàn giao'}


def _ghi_nhom_dong(dong: set) -> None:
    from PySide6.QtCore import QSettings
    try:
        QSettings('PABT', 'PABT').setValue(KHOA_NHOM_DONG, '|'.join(sorted(dong)) or '|')    # '|' = không nhóm nào đóng
    except Exception:
        pass


def menu_trai(nhom: list, thu_gon_luc_dau: bool = False, xo: tuple = (), dong_mac_dinh: tuple = ()) -> QFrame:
    """Khu vực lệnh dạng cột dọc bên trái (mặc định từ 0.9.3; thanh_lenh là kiểu thanh nút phía trên): nhóm có tiêu đề, mỗi lệnh một dòng (biểu tượng + chữ);
    nút "Thu gọn" chuyển sang chỉ hiện biểu tượng (rê chuột hiện tên lệnh).
    xo: tên nhóm hiện thành MỘT nút có danh sách xổ xuống (lệnh ít dùng: Dự án mới, Mở, Lưu thành…) để menu không tràn màn hình.
    Nhóm khác: bấm tiêu đề nhóm để đóng / mở; nhóm đang đóng nhớ ở QSettings (lần đầu: dong_mac_dinh)."""
    from PySide6.QtWidgets import QMenu, QScrollArea, QSizePolicy
    khung = QFrame()
    khung.setProperty('vai', 'ribbon')
    ngoai = QVBoxLayout(khung)
    ngoai.setContentsMargins(4, 4, 4, 4)
    ngoai.setSpacing(2)
    b_gon = QToolButton()
    b_gon.setProperty('ribbon', '1')
    b_gon.setProperty('nhom', 'nhat')
    b_gon.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    b_gon.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    ngoai.addWidget(b_gon)
    cuon = QScrollArea()
    cuon.setWidgetResizable(True)
    cuon.setFrameShape(QFrame.Shape.NoFrame)
    cuon.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    trong = QWidget()
    trong.setObjectName('menu_trong')
    # có bộ chọn: kiểu không có bộ chọn bị truyền sang ô gợi ý (tooltip) của các nút con -> ô gợi ý nền đen
    trong.setStyleSheet('QWidget#menu_trong { background: transparent; }')
    lo = QVBoxLayout(trong)
    lo.setContentsMargins(0, 0, 0, 0)
    lo.setSpacing(2)
    nut, tieu_de = [], []                                    # tieu_de: (nút tiêu đề nhóm, tên nhóm, [nút lệnh của nhóm])
    dong = _doc_nhom_dong(dong_mac_dinh)

    def nut_menu(a) -> QToolButton:
        b = nut_lenh(a, 18, mau=TOKEN['chinh'])              # icon đơn sắc Deep Navy + vạch trái khi chọn
        if a.icon().isNull():
            # lệnh chưa có ký hiệu / máy không có phông biểu tượng (Win 7): Qt căn chữ ra giữa nút - lệch so với các dòng khác
            # (11/10/2026 "Bảng giá đất"). Biểu tượng trống cùng cỡ giữ chữ thẳng hàng; khi thu gọn vẫn hiện chữ (icon_trong)
            from PySide6.QtGui import QIcon, QPixmap
            pm = QPixmap(18, 18)
            pm.fill(Qt.GlobalColor.transparent)
            a.setIcon(QIcon(pm))                             # trên QAction: nút lấy lại biểu tượng của lệnh mỗi khi lệnh đổi
            b.setProperty('icon_trong', True)
        b.setProperty('ribbon', '0')
        b.setProperty('menu', '1')                           # kiểu danh sách: không viền, rê chuột mới hiện nền
        b.setMinimumHeight(CAO_NUT_MENU)
        b.setMaximumHeight(CAO_NUT_MENU + 3)
        b.setToolTip(a.text().rstrip('…'))
        nut.append(b)
        return b

    for ten, ds in nhom:
        if not ten:                                          # 0.9.70: nhóm không tên = nút độc lập (Màn hình chính) + vạch ngăn
            for a in ds:
                lo.addWidget(nut_menu(a))
            vach = QFrame()
            vach.setFrameShape(QFrame.Shape.HLine)
            vach.setObjectName('vach_menu')
            vach.setStyleSheet(f'QFrame#vach_menu {{ color: {TOKEN["vach"]}; margin: 2px 4px; }}')
            lo.addWidget(vach)
            continue
        if ten in xo:                                        # một nút, bấm xổ danh sách lệnh của nhóm
            b = QToolButton()
            # nổi bật (nền xanh đậm như băng tiêu đề, vạch vàng, chữ trắng): nơi mở / tạo / lưu dự án - người dùng hay tìm
            b.setText(f'{ten.upper()}   ▾')
            k = ky_hieu_nut('Mở dự án') if ten == 'Dự án' else ky_hieu_nut(ten)
            ic = icon_ky_hieu(k, '#FFFFFF', 22) if k else None
            if ic is not None:
                b.setIcon(ic)
                b.setIconSize(QSize(22, 22))
            m = QMenu(b)
            for a in ds:
                ka = ky_hieu_nut(a.text())
                ica = icon_ky_hieu(ka, mau_icon(a.text()), 18) if ka and a.icon().isNull() else None
                if ica is not None:
                    a.setIcon(ica)
                m.addAction(a)
            b.setMenu(m)
            b.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            b.setProperty('menu', '1')
            b.setProperty('xo', '1')
            b.setMinimumHeight(40)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.setToolTip(f'{ten}: ' + ', '.join(a.text().rstrip('…') for a in ds))
            lo.addWidget(b)
            nut.append(b)
            khung.nut_xo = getattr(khung, 'nut_xo', {})
            khung.nut_xo[ten] = b
            continue
        t = NhanBam()                                        # nhãn (không phải nút): to_mau không tô màu theo chữ
        t.setProperty('vai', 'nhom_menu')
        t.setWordWrap(True)                                  # tên nhóm dài xuống dòng, không bị cắt (menu 175 px)
        lo.addWidget(t)
        con = [nut_menu(a) for a in ds]
        for b in con:
            lo.addWidget(b)
        tieu_de.append((t, ten, con))
    lo.addStretch(1)
    cuon.setWidget(trong)
    ngoai.addWidget(cuon, 1)

    def ve_nhom():
        for t, ten, con in tieu_de:
            d = ten in dong
            t.setText(('▸' if d else '▾') + ('' if khung.thu_gon else '  ' + ten.upper()))
            t.setToolTip(f'{"Mở" if d else "Đóng"} nhóm "{ten}"')
            t.setProperty('dong', '1' if d else '0')
            t.style().unpolish(t)
            t.style().polish(t)
            for b in con:
                b.setVisible(not d)

    def bam_nhom(ten: str):
        dong.symmetric_difference_update({ten})
        _ghi_nhom_dong(dong)
        ve_nhom()
    for t, ten, _ in tieu_de:
        t.bam = lambda x=ten: bam_nhom(x)
    khung.nhom_dong = dong
    khung.tieu_de_nhom = {ten: t for t, ten, _ in tieu_de}

    def dat(gon: bool):
        khung.thu_gon = gon
        for b in nut:
            co_icon = not b.icon().isNull() and not b.property('icon_trong')
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly if gon and co_icon
                                 else Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        ve_nhom()
        khung.setFixedWidth(RONG_MENU_GON if gon else khung.rong_mo())
        b_gon.setText('' if gon else '  Thu gọn menu')
        ic = icon_ky_hieu(0xE76C if gon else 0xE76B, CHINH, 16)       # mũi tên mở rộng / thu gọn
        b_gon.setIcon(ic) if ic is not None else b_gon.setText('»' if gon else '«  Thu gọn menu')
        b_gon.setToolTip('Mở rộng menu' if gon else 'Thu gọn menu (chỉ hiện biểu tượng)')
    def rong_mo() -> int:
        """Bề rộng menu mở: RONG_MENU_TRAI, nới theo lệnh dài nhất (chữ đo theo phông / tỷ lệ phóng to hiện tại), tối đa
        RONG_MENU_TOI_DA - không cắt chữ lệnh."""
        can = max([b.sizeHint().width() for b in nut if b.toolButtonStyle() != Qt.ToolButtonStyle.ToolButtonIconOnly] or [0])
        return min(max(RONG_MENU_TRAI, can + 8 + 10), RONG_MENU_TOI_DA)     # lề 2 x 4 + chỗ thanh cuộn
    khung.rong_mo = rong_mo
    khung._vua_rong = _VuaRongMenu(khung)
    khung.installEventFilter(khung._vua_rong)
    b_gon.clicked.connect(lambda: dat(not khung.thu_gon))
    dat(thu_gon_luc_dau)
    return do_bong(khung, 16, 2, 30)



DEM_TIEU_DE = 30             # chữ tiêu đề (đo bằng phông ĐẬM như QSS tiêu đề) + mũi tên sắp xếp / lề ô


def san_tieu_de(b, rieng: dict | None = None) -> None:
    """Sàn bảo vệ tiêu đề cột (0.9.94-0.9.95): cột không giãn nào hẹp hơn chữ tiêu đề thì nới ra. Đo bằng phông ĐẬM (tiêu đề in
    đậm qua QSS, fontMetrics của widget là phông thường - đo thiếu ~10%: "Tổng tiền dự thảo" -> "ổng tiền dự thả"). rieng:
    {cột: bề rộng tối thiểu riêng}. Gọi lại sau khi nạp / đổi cỡ chữ (phóng to)."""
    from PySide6.QtGui import QFont, QFontMetrics
    from PySide6.QtWidgets import QHeaderView
    hd = b.horizontalHeader()
    f = QFont(hd.font())
    f.setBold(True)
    fm = QFontMetrics(f)
    for c in range(b.columnCount()):
        if hd.sectionResizeMode(c) == QHeaderView.ResizeMode.Stretch:
            continue
        it = b.horizontalHeaderItem(c)
        chu = it.text() if it is not None else str(b.model().headerData(c, Qt.Orientation.Horizontal) or '')
        can = max([fm.horizontalAdvance(t) for t in chu.split('\n')] or [0]) + DEM_TIEU_DE
        can = max(can, (rieng or {}).get(c, 0))
        if b.columnWidth(c) < can:
            b.setColumnWidth(c, can)

class _VuaRongMenu(QObject):
    """Đo lại bề rộng menu trái khi hiện / đổi kiểu / đổi phông (phóng to): sizeHint của nút chỉ đúng sau khi áp QSS."""

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.Type.Show, QEvent.Type.StyleChange, QEvent.Type.FontChange) and not getattr(obj, 'thu_gon', True):
            w = obj.rong_mo()
            if obj.width() != w:
                obj.setFixedWidth(w)
        return False


def ve_mui_ten(delegate_cha, p, option, index) -> None:
    """Vẽ ô bảng có danh sách xổ xuống: nội dung như thường, thêm mũi tên ▾ ở mép phải (nhìn là biết bấm để chọn)."""
    from PySide6.QtWidgets import QStyleOptionViewItem
    o = QStyleOptionViewItem(option)
    o.rect = option.rect.adjusted(0, 0, -18, 0)
    delegate_cha.paint(p, o, index)
    if not (index.flags() & Qt.ItemFlag.ItemIsEditable):
        return
    p.save()
    r = option.rect
    p.setPen(QColor('#4F7FAE'))
    f = p.font()
    f.setPointSizeF(f.pointSizeF() * 1.15)
    p.setFont(f)
    p.drawText(QRect(r.right() - 18, r.top(), 16, r.height()), int(Qt.AlignmentFlag.AlignCenter), '▾')
    p.restore()


def nhap_mot_lan(delegate, event, option, index) -> bool:
    """Nhấp một lần vào mũi tên ▾ (hoặc vào ô đang chọn) của ô có danh sách: mở ngay danh sách chọn."""
    if event.type() != QEvent.Type.MouseButtonRelease or event.button() != Qt.MouseButton.LeftButton \
            or not (index.flags() & Qt.ItemFlag.ItemIsEditable):
        return False
    view = delegate.parent()
    if view is None or not hasattr(view, 'edit'):
        return False
    tren_mui_ten = event.pos().x() >= option.rect.right() - 22
    if not tren_mui_ten and view.currentIndex() != index:
        return False
    QTimer.singleShot(0, lambda: (view.setCurrentIndex(index), view.edit(index)))
    return True


def neo_popup(cb, so_dong: int = 14) -> None:
    """Kéo danh sách xổ vào trong màn hình và bật thanh cuộn (vị trí NQ 28 hơn nghìn dòng, đủ 4 xã)."""
    try:
        view = cb.view()
        pop = view.parentWidget()
        while pop is not None and not pop.isWindow():
            pop = pop.parentWidget()
        man = cb.screen() or QApplication.primaryScreen()
        if pop is None or man is None or pop is cb.window() or not pop.isVisible():
            return
        vung = man.availableGeometry()
        if vung.height() < 80:
            return
        dong = max(view.sizeHintForRow(0), 24)
        cao = min(so_dong * dong + 8, vung.height() - 24)
        rong = 640 if cb.count() > 40 else min(max(view.sizeHintForColumn(0) + 36, cb.width(), 280), 720)
        rong = min(rong, vung.width() - 16)
        goc = cb.mapToGlobal(cb.rect().bottomLeft())
        y = goc.y()
        if y + cao > vung.bottom() - 4:
            y = max(vung.top() + 4, goc.y() - cb.height() - cao)
        x = min(max(goc.x(), vung.left() + 4), max(vung.left() + 4, vung.right() - rong - 4))
        pop.setGeometry(x, y, rong, cao)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    except RuntimeError:
        pass


class HopXo(QComboBox):
    """Ô xổ: danh sách luôn nằm trong màn hình, có thanh cuộn."""

    def showPopup(self):
        self.setMaxVisibleItems(14)
        self.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        super().showPopup()
        QTimer.singleShot(0, lambda: neo_popup(self))


def mo_danh_sach(cb, so_dong: int = 14) -> None:
    """Ô xổ vừa mở để sửa: hiện luôn danh sách (không phải bấm thêm lần nữa)."""
    def mo():
        try:
            if cb.isVisible():
                cb.showPopup()
        except RuntimeError:
            pass
    QTimer.singleShot(0, mo)


class ChonXoXuong(QStyledItemDelegate):
    """Ô bảng có danh sách xổ xuống (vẫn gõ tay được). muc: [(giá trị lưu, nhãn hiển thị)]."""

    def __init__(self, muc: list, parent=None):
        super().__init__(parent)
        self.muc = muc

    def paint(self, p, option, index):
        ve_mui_ten(super(), p, option, index)

    def editorEvent(self, event, model, option, index):
        return nhap_mot_lan(self, event, option, index) or super().editorEvent(event, model, option, index)

    def createEditor(self, parent, option, index):
        cb = HopXo(parent)
        cb.setEditable(True)
        cb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        cb.setMaxVisibleItems(14)
        for gt, nhan in self.muc:
            cb.addItem(nhan, gt)
        cb.view().setMinimumWidth(max(cb.view().sizeHintForColumn(0) + 30, 180))     # danh sách rộng: đủ "mã – tên"
        cb.activated.connect(lambda i: cb.setEditText(str(cb.itemData(i))))          # ô chỉ hiện giá trị lưu (mã)
        mo_danh_sach(cb)
        return cb

    def setEditorData(self, cb, index):
        v = str(index.data() or '')
        i = cb.findData(v)
        if i >= 0:
            cb.setCurrentIndex(i)
        cb.setEditText(v)

    def setModelData(self, cb, model, index):
        chu = cb.currentText().strip()
        i = cb.findText(chu)
        model.setData(index, cb.itemData(i) if i >= 0 else chu)


class OTimChon(QWidget):
    """Ô gõ để tìm và chọn trong danh sách dài (không cần dấu, khớp mọi từ), có nút ▼ xem cả danh sách.
    Danh sách gợi ý là cửa sổ nổi không giữ bàn phím: mọi phím gõ vẫn vào ô nhập, nên gõ tiếng Việt bằng Unikey / EVKey
    (bộ gõ xóa rồi gõ lại ký tự) không bị mất chữ. Phím ↑ ↓ chọn, Enter lấy mục, Esc đóng danh sách.
    dat_muc([(nhãn, dữ liệu)]); .chon = dữ liệu mục đã chọn (None nếu gõ tự do); khi_chon(dữ liệu) gọi khi chọn một mục."""
    TOI_DA = 20000                                  # hiện đủ danh sách (cây trồng vài nghìn mục); quá nữa mới cắt

    def __init__(self, goi_y: str = '', parent=None):
        from PySide6.QtWidgets import QLineEdit, QListWidget
        super().__init__(parent)
        self.chon = None
        self.khi_chon = None
        self._muc = []                              # [(nhãn, chữ không dấu, dữ liệu)]
        self._theo_nhan = {}
        self.o = QLineEdit()
        self.o.setPlaceholderText(goi_y)
        self.o.setClearButtonEnabled(True)
        self.nut = QToolButton()
        self.nut.setText('▼')
        self.nut.setToolTip('Xem cả danh sách')
        self.nut.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ds = QListWidget()
        self.ds.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.ds.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ds.setMouseTracking(True)                 # rê chuột: tô dòng dưới chuột; bánh xe / thanh cuộn dùng được
        self.ds.itemEntered.connect(self.ds.setCurrentItem)
        self.ds.setObjectName('ds_goi_y')
        self.ds.setStyleSheet('QListWidget#ds_goi_y { background: #FFFFFF; color: #1A1A1A; border: 1px solid #9FB6CC; }'
                              'QListWidget#ds_goi_y::item { padding: 4px 6px; }'
                              'QListWidget#ds_goi_y::item:selected { background: #DCEBFA; color: #0B2E4F; }')
        self.ds.itemClicked.connect(lambda it: self._chon_nhan(it.text()))
        self.o.textEdited.connect(self._go)
        self.o.installEventFilter(self)
        self.nut.clicked.connect(self.xem_tat_ca)
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(2)
        lo.addWidget(self.o, 1)
        lo.addWidget(self.nut)

    # ---------------------------------------------- danh sách
    def dat_muc(self, ds: list) -> None:
        self._ds_hien = None
        self._muc = [(nhan, bo_dau(nhan), gt) for nhan, gt in ds]
        self._theo_nhan = {nhan: gt for nhan, gt in ds}
        self.chon = None

    def loc(self, chu: str) -> list:
        """Các nhãn khớp mọi từ đã gõ (không dấu); mục bắt đầu bằng từ đầu tiên xếp trước."""
        tu = bo_dau(chu).split()
        if not tu:
            return [m[0] for m in self._muc]
        ds = [m for m in self._muc if all(t in m[1] for t in tu)]
        ds.sort(key=lambda m: not m[1].startswith(tu[0]))
        return [m[0] for m in ds]

    def _hien(self, ds: list):
        if not ds:
            self.ds.hide()
            return
        cua_so = self.window()
        if self.ds.parentWidget() is not cua_so:
            # cửa sổ con nổi (thuộc cửa sổ đang dùng) không nhận tiêu điểm: chuột cuộn / bấm chọn được, phím gõ vẫn vào ô nhập
            self.ds.setParent(cua_so, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                              Qt.WindowType.WindowDoesNotAcceptFocus)
            self.ds.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.ds.setUniformItemSizes(True)                # danh sách dài (vài nghìn cây): dựng, cuộn nhanh
        ds = ds[:self.TOI_DA]
        if ds != getattr(self, '_ds_hien', None) or self.ds.count() != len(ds):
            # gõ thêm chữ mà kết quả lọc không đổi: giữ nguyên danh sách (không dựng lại vài nghìn dòng mỗi phím - 0.9.87)
            self.ds.clear()
            self.ds.addItems(ds)
            for i, nhan in enumerate(ds):               # nhãn dài: xem đủ khi rê chuột (chỉ chạm Qt ở các dòng này)
                if len(nhan) > 60:
                    self.ds.item(i).setToolTip(nhan)
            self._ds_hien = ds
        self.ds.setCurrentRow(0)
        cao = min(16, self.ds.count()) * (self.ds.sizeHintForRow(0) or 24) + 6
        self.ds.resize(max(self.width(), 640), cao)
        self.ds.move(self.o.mapToGlobal(self.o.rect().bottomLeft()))
        self.ds.show()
        self.ds.raise_()

    def _go(self, chu: str):
        self.chon = self._theo_nhan.get(chu)
        self._hien(self.loc(chu) if chu.strip() else [])

    khi_trong = None            # bấm ▼ khi danh sách rỗng: hàm của màn hình chủ (vd: bổ sung vật nuôi); None = chỉ báo
    goi_y_trong = 'Danh mục đơn giá chưa có mục nào cho phần này: gõ tên để nhập hạng mục ngoài danh mục.'

    def xem_tat_ca(self):
        self.o.setFocus()
        ds = self.loc('')
        if not ds:
            # 0.9.69 (người dùng: "không bấm được mũi tên xổ xuống" - thẻ Vật nuôi của dự án lập trước QĐ 31/2025): danh sách rỗng
            # thì trước đây nút ▼ không làm gì
            if self.khi_trong is not None and self.khi_trong():
                ds = self.loc('')
            else:
                from PySide6.QtWidgets import QToolTip
                QToolTip.showText(self.nut.mapToGlobal(self.nut.rect().bottomLeft()), self.goi_y_trong, self.nut)
                return
        self._hien(ds)

    def eventFilter(self, obj, e):
        if obj is self.o:
            t = e.type()
            if t == QEvent.Type.KeyPress and self.ds.isVisible():
                k = e.key()
                if k in (Qt.Key.Key_Down, Qt.Key.Key_Up, Qt.Key.Key_PageDown, Qt.Key.Key_PageUp):
                    buoc = {Qt.Key.Key_Down: 1, Qt.Key.Key_Up: -1, Qt.Key.Key_PageDown: 10, Qt.Key.Key_PageUp: -10}[k]
                    self.ds.setCurrentRow(max(0, min(self.ds.count() - 1, self.ds.currentRow() + buoc)))
                    return True
                if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                    it = self.ds.currentItem()
                    if it is not None:
                        self._chon_nhan(it.text())
                        return True
                if k == Qt.Key.Key_Escape:
                    self.ds.hide()
                    return True
            elif t == QEvent.Type.FocusOut:
                QTimer.singleShot(150, self._an_neu_roi)     # nhấp chuột vào danh sách: chọn trước rồi mới ẩn
        return super().eventFilter(obj, e)

    def _an_neu_roi(self):
        if self.ds.isVisible() and (self.ds.underMouse() or self.ds.isActiveWindow()):
            self.o.setFocus()                           # đang thao tác chuột trên danh sách (cuộn, kéo thanh cuộn): giữ mở
            return
        if not self.o.hasFocus():
            self.ds.hide()

    def _chon_nhan(self, nhan: str):
        self.ds.hide()
        self.o.setFocus()
        self.o.setText(nhan)
        self.o.setCursorPosition(0)
        self.chon = self._theo_nhan.get(nhan)
        if self.khi_chon:
            self.khi_chon(self.chon)

    def chon_du_lieu(self, gt) -> bool:
        """Chọn mục có dữ liệu gt (kiểm thử / chọn sẵn)."""
        for nhan, x in self._theo_nhan.items():
            if x == gt or x is gt:
                self._chon_nhan(nhan)
                return True
        return False

    def text(self) -> str:
        return self.o.text()

    def setText(self, chu: str):
        self.o.setText(chu)
        self.chon = self._theo_nhan.get(chu)

    def xoa(self):
        self.ds.hide()
        self.o.clear()
        self.chon = None

    def hideEvent(self, e):
        try:
            self.ds.hide()
        except RuntimeError:                            # danh sách đã bị xóa cùng cửa sổ (lúc đóng chương trình)
            pass
        super().hideEvent(e)


def the_form(tieu_de: str, dong: list, rong_nhan: int = 150) -> QWidget:
    """Thẻ nhập liệu gọn: khung trắng bo góc có tiêu đề, nhãn canh phải cột cố định. dong: [(nhãn, widget hoặc layout)]."""
    from PySide6.QtWidgets import QFormLayout, QGroupBox
    g = QGroupBox(tieu_de)
    f = QFormLayout(g)
    f.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    f.setHorizontalSpacing(10)
    f.setVerticalSpacing(7)
    f.setContentsMargins(12, 14, 12, 10)
    for nhan, w in dong:
        if nhan is None:
            f.addRow(w)
            continue
        n = QLabel(nhan)
        n.setProperty('vai', 'nhan')
        n.setMinimumWidth(rong_nhan)
        n.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        f.addRow(n, w)
    return g


def can_giua(*the, rong_toi_da: int = 1180) -> QWidget:
    """Đặt các thẻ cạnh nhau, giới hạn chiều rộng và canh giữa (không trải ô nhập hết màn hình rộng)."""
    w = QWidget()
    ngoai = QHBoxLayout(w)
    ngoai.setContentsMargins(0, 0, 0, 0)
    ngoai.addStretch(1)
    trong = QWidget()
    trong.setMaximumWidth(rong_toi_da)
    h = QHBoxLayout(trong)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(12)
    for t in the:
        h.addWidget(t, 1, Qt.AlignmentFlag.AlignTop)
    ngoai.addWidget(trong, 100)
    ngoai.addStretch(1)
    return w


def hop_ket_qua(cha, tom_tat: str, chi_tiet: list | None = None, tieu_de_ds: str = 'Cần xem lại', canh_bao: bool = False,
                hien: bool = True, tieu_de: str = 'LARC - Lập phương án bồi thường, hỗ trợ', nut_them=()):
    """Hộp kết quả không bao giờ cao quá màn hình (QMessageBox giãn theo chữ: danh sách dài đẩy nút OK ra ngoài màn hình):
    tóm tắt ngắn ở trên, danh sách ĐẦY ĐỦ trong ô cuộn, nút Chép (dán sang Excel / Zalo) và Đóng. hien=False: chỉ tạo (kiểm thử).
    nut_them: [(chữ, hàm(hộp))] nút thêm ở hàng nút (hộp báo lỗi: xuất gói chẩn đoán) - giữ ở d.nut_them {chữ: nút}."""
    from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QPlainTextEdit, QStyle, QVBoxLayout)
    d = QDialog(cha)
    d.setWindowTitle(tieu_de)
    lo = QVBoxLayout(d)
    dau = QHBoxLayout()
    bt = QLabel()
    kieu = QStyle.StandardPixmap.SP_MessageBoxWarning if canh_bao else QStyle.StandardPixmap.SP_MessageBoxInformation
    bt.setPixmap(d.style().standardIcon(kieu).pixmap(40, 40))
    dau.addWidget(bt, 0, Qt.AlignmentFlag.AlignTop)
    nhan = QLabel(tom_tat)
    nhan.setWordWrap(True)
    nhan.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    dau.addWidget(nhan, 1)
    lo.addLayout(dau)
    ds = list(chi_tiet or [])
    o = None
    if ds:
        tieu = QLabel(f'<b>{tieu_de_ds} ({len(ds)}):</b>')
        lo.addWidget(tieu)
        o = QPlainTextEdit('\n'.join('- ' + x for x in ds))
        o.setReadOnly(True)
        o.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        lo.addWidget(o, 1)
    nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    nut.button(QDialogButtonBox.StandardButton.Close).setText('Đóng')
    nut.rejected.connect(d.reject)
    if ds:
        chep = nut.addButton('Chép danh sách', QDialogButtonBox.ButtonRole.ActionRole)
        chep.clicked.connect(lambda: QApplication.clipboard().setText(tom_tat + '\n\n' + o.toPlainText()))
    d.nut_them = {}
    for chu, ham in nut_them:
        b = nut.addButton(chu, QDialogButtonBox.ButtonRole.ActionRole)
        b.clicked.connect(lambda _=False, ham=ham: ham(d))
        d.nut_them[chu] = b
    lo.addWidget(nut)
    d.resize(760, 560 if ds else 220)
    vua_man_hinh(d)
    d.o_ds = o
    if hien:
        d.exec()
    return d


def vua_man_hinh(w: QWidget) -> None:
    """Cửa sổ / hộp thoại lớn hơn màn hình đang dùng (laptop nhỏ, phóng to 125-150%): thu vừa 94% màn hình và canh giữa."""
    from PySide6.QtWidgets import QApplication
    man = (w.screen() if hasattr(w, 'screen') else None) or QApplication.primaryScreen()
    if man is None or w.isMaximized():
        return
    vung = man.availableGeometry()
    rong, cao = min(w.width(), int(vung.width() * 0.94)), min(w.height(), int(vung.height() * 0.94))
    if (rong, cao) != (w.width(), w.height()):
        w.resize(rong, cao)
        w.move(vung.x() + (vung.width() - rong) // 2, vung.y() + (vung.height() - cao) // 2)


# ---------------------------------------------------------------- nhập liệu bằng bàn phím trong bảng
class _PhimBang(QObject):
    """Enter ở ô đang đứng: mở sửa ô (ô tự tính: sang ô kế). Sửa xong bấm Enter: ghi và sang ô nhập kế tiếp (hết dòng thì
    xuống dòng dưới). Tab / Shift+Tab: sang ô kế / ô trước như bình thường."""

    def __init__(self, bang):
        super().__init__(bang)
        self.bang = bang

    def eventFilter(self, obj, e):
        from PySide6.QtWidgets import QAbstractItemView
        b = self.bang
        if e.type() != QEvent.Type.KeyPress:
            return False
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) \
                and b.state() != QAbstractItemView.State.EditingState and b.currentIndex().isValid():
            idx = b.currentIndex()
            if idx.flags() & Qt.ItemFlag.ItemIsEditable:
                b.edit(idx)
            else:
                o_ke(b)
            return True
        return False


def o_ke(bang) -> None:
    """Chuyển tới ô sửa được kế tiếp bên phải (hết dòng: ô sửa được đầu tiên của dòng dưới)."""
    idx = bang.currentIndex()
    if not idx.isValid():
        return
    m = bang.model()
    r, c = idx.row(), idx.column() + 1
    while r < m.rowCount():
        while c < m.columnCount():
            j = m.index(r, c)
            if not bang.isColumnHidden(c) and j.flags() & Qt.ItemFlag.ItemIsEditable:
                bang.setCurrentIndex(j)
                return
            c += 1
        r, c = r + 1, 0


def nhap_bang_phim(bang) -> None:
    """Bảng nhập số liệu: dòng cao, dễ nhìn; Tab / Enter để đi giữa các ô, không cần chuột."""
    from PySide6.QtWidgets import QAbstractItemDelegate
    vh = bang.verticalHeader()
    vh.setMinimumSectionSize(34)
    vh.setDefaultSectionSize(36)
    bang.setTabKeyNavigation(True)
    bang._phim = _PhimBang(bang)
    bang.installEventFilter(bang._phim)
    ds = {bang.itemDelegate()} | {bang.itemDelegateForColumn(c) for c in range(bang.columnCount())}

    def sau_khi_sua(*a):
        hint = a[1] if len(a) > 1 else QAbstractItemDelegate.EndEditHint.SubmitModelCache
        if hint == QAbstractItemDelegate.EndEditHint.SubmitModelCache:
            QTimer.singleShot(0, lambda: o_ke(bang))
    for d in ds:
        if d is not None:
            d.closeEditor.connect(sau_khi_sua)


# ---------------------------------------------------------------- phóng to / thu nhỏ giao diện (màn hình độ phân giải khác nhau)
TY_LE = [1.0]                                   # tỷ lệ hiện tại (0,8 - 1,6)
KHI_DOI_TY_LE = []                              # hàm gọi lại khi đổi tỷ lệ (cập nhật nhãn "100%")
_CO_CHU_GOC = 9.5


def _co_gian(qss: str, t: float) -> str:
    """Nhân các kích thước 'px' trong QSS (cỡ chữ, khoảng đệm, bo góc) theo tỷ lệ."""
    if t == 1:
        return qss
    return re.sub(r'(\d+(?:\.\d+)?)px', lambda m: f'{max(1, round(float(m.group(1)) * t))}px', qss)


def _co_gian_widget(w, t: float) -> None:
    """Kiểu riêng của từng widget (setStyleSheet có 'px'): co giãn theo tỷ lệ, giữ bản gốc để đổi tỷ lệ nhiều lần."""
    s = w.styleSheet()
    if not s or 'px' not in s:
        return
    goc = w.property('qss_goc')
    if goc is None or w.property('qss_da') != s:          # chưa co giãn, hoặc mã vừa đặt kiểu mới
        goc = s
    moi = _co_gian(goc, t)
    w.setProperty('qss_goc', goc)
    w.setProperty('qss_da', moi)
    if moi != s:
        w.setStyleSheet(moi)


def dat_ty_le(t: float, luu: bool = True) -> float:
    """Đổi tỷ lệ giao diện (cỡ chữ, khoảng đệm) cho mọi cửa sổ; luu: nhớ cho lần mở sau.
    Việc tốn nhất là Qt áp lại kiểu (QSS) cho mọi widget: tắt vẽ lại các cửa sổ trong lúc đổi (không chớp, không vẽ dở),
    bảng chỉ giãn lại dòng cho bảng đang hiện, làm sau khi đã vẽ xong (_gian_bang)."""
    from PySide6.QtCore import QSettings, QTimer
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    t = round(min(1.6, max(0.8, t)), 2)
    _CHO[0] = None
    if t == TY_LE[0] and app.property('pabt_ty_le') == t:
        _bao_ty_le(t)
        return t
    TY_LE[0] = t
    cua_so = [w for w in app.topLevelWidgets() if w.isVisible()]
    for w in cua_so:
        w.setUpdatesEnabled(False)
    try:
        f = QFont(app.font())
        f.setPointSizeF(_CO_CHU_GOC * t)
        app.setFont(f)
        app.setStyleSheet(_co_gian(_qss_day_du(), t))
        for w in app.allWidgets():
            _co_gian_widget(w, t)
    finally:
        for w in cua_so:
            w.setUpdatesEnabled(True)
    app.setProperty('pabt_ty_le', t)
    if app.platformName() == 'offscreen':
        _gian_bang()
    else:
        QTimer.singleShot(0, _gian_bang)
    if luu:
        QSettings('PABT', 'PABT').setValue('giao_dien/ty_le', t)
    _bao_ty_le(t)
    return t


CAO_DONG_CHUAN = 32             # bảng nhập phương án: dòng một dòng chữ
CAO_DONG_TOI_THIEU = 30
CAO_DONG_TOI_DA = 88            # chữ dài hơn: xem đủ ở chú thích / bấm đúp sửa (khung sửa cao theo chữ)


def _rong_do(b, c: int) -> int:
    """Bề rộng để đo chữ cột c: cột chưa xếp xong (bảng chưa hiện, cột giãn còn ~0) lấy max(160, sizeHint tiêu đề)."""
    w = b.columnWidth(c)
    if w < 100:
        w = max(160, b.horizontalHeader().sectionSizeHint(c))
    return max(20, w - 10)


def cao_can_dong(b, r: int, cao_chuan: int = CAO_DONG_CHUAN, cao_toi_da: int | None = CAO_DONG_TOI_DA, nho: dict | None = None) -> int:
    """Chiều cao cần cho dòng r: đo chữ từng ô bằng QFontMetrics.boundingRect trên bề rộng thật của cột (ô trống, chữ ngắn không
    làm dòng cao). Một dòng chữ: cao_chuan (tối đa 36 khi phông lớn); nhiều dòng: min(cao_toi_da, max(cao_chuan, chữ + 10))."""
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QFontMetrics
    nho = {} if nho is None else nho                    # nhiều dòng (vua_dong): QFontMetrics / bề rộng cột dùng chung một lượt
    if 'bang' not in nho:
        nho['bang'] = (b.fontMetrics(), b.font().key())
        nho['rong'] = {}
    fm_bang, khoa_bang = nho['bang']
    mot = fm_bang.height()
    can = 0
    for c in range(b.columnCount()):
        if b.isColumnHidden(c):
            continue
        it = b.item(r, c)
        t = it.text() if it is not None else ''
        if not t or not t.strip():
            continue
        f = it.font()
        k = f.key()
        if k == khoa_bang:
            fm = fm_bang
        else:
            fm = nho.get(k)
            if fm is None:
                fm = nho[k] = QFontMetrics(f)
        w = nho['rong'].get(c)
        if w is None:
            w = nho['rong'][c] = _rong_do(b, c)
        if '\n' not in t and (len(t) * fm.maxWidth() <= w or fm.horizontalAdvance(t) <= w):
            continue                                    # vừa một dòng (ô ngắn: khỏi đo chữ): không cần đo ngắt dòng
        h = fm.boundingRect(QRect(0, 0, w, 100000), int(Qt.TextFlag.TextWordWrap), t).height()
        can = max(can, h)
    if can <= mot * 1.2:                                # một dòng chữ
        return min(max(cao_chuan, mot + 12), max(cao_chuan, 36))
    kq = max(cao_chuan, can + 10)
    return kq if cao_toi_da is None else min(cao_toi_da, kq)


def vua_dong(b, cao_chuan: int | None = CAO_DONG_CHUAN, cao_toi_da: int | None = CAO_DONG_TOI_DA) -> None:
    """Chiều cao dòng bảng QTableWidget theo chữ thật (cao_can_dong) - thay resizeRowsToContents (đo sizeHint mọi ô: cột giãn /
    tiêu đề dài làm dòng trống cũng cao 60-90 px; 5.000 dòng × 11 cột ~0,4-1,5 giây). cao_chuan None = defaultSectionSize của
    bảng; cao_toi_da None = không giới hạn."""
    if cao_chuan is None:
        cao_chuan = b.verticalHeader().defaultSectionSize()
    vh = b.verticalHeader()
    nho = {}
    for r in range(b.rowCount()):
        h = cao_can_dong(b, r, cao_chuan, cao_toi_da, nho)
        if vh.sectionSize(r) != h:
            b.setRowHeight(r, h)


def dat_dong_gon(b, cao_chuan: int = CAO_DONG_CHUAN, cao_toi_thieu: int = CAO_DONG_TOI_THIEU) -> None:
    """Bảng nhập phương án: dòng 30-32 px, KHÔNG giãn dòng cuối, chiều cao do vua_dong đặt (không ResizeToContents)."""
    from PySide6.QtWidgets import QHeaderView
    vh = b.verticalHeader()
    vh.setStretchLastSection(False)
    vh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    vh.setMinimumSectionSize(cao_toi_thieu)
    vh.setDefaultSectionSize(cao_chuan)


def _gian_bang() -> None:
    """Chữ to / nhỏ hơn: dòng bảng (chữ xuống dòng) cao theo cho đủ chữ - chỉ bảng đang hiện, bảng quá dài thì bỏ qua."""
    from PySide6.QtWidgets import QApplication, QTableView
    for w in QApplication.instance().allWidgets():
        if isinstance(w, QTableView) and w.wordWrap() and w.isVisible() and w.model() is not None \
                and w.model().rowCount() <= 1500:
            w.resizeRowsToContents()


def _bao_ty_le(t: float) -> None:
    for ham in list(KHI_DOI_TY_LE):
        try:
            ham(t)
        except RuntimeError:                            # nhãn đã bị xóa cùng cửa sổ
            KHI_DOI_TY_LE.remove(ham)


_CHO = [None]                                           # tỷ lệ đang chờ áp (lăn chuột liên tục: gộp thành một lần)
_HEN = []


def phong_to(buoc: int, cho_ms: int = 220) -> float:
    """buoc: +1 phóng to, -1 thu nhỏ (mỗi bước 10%), 0 về 100%. Lăn chuột / bấm liên tục: số % đổi ngay, giao diện chỉ áp
    lại một lần khi ngừng (cho_ms) - không giật, không dồn nhiều lần áp kiểu. cho_ms=0: áp ngay."""
    goc = _CHO[0] if _CHO[0] is not None else TY_LE[0]
    t = round(min(1.6, max(0.8, 1.0 if buoc == 0 else goc + 0.1 * buoc)), 2)
    if cho_ms <= 0:
        return dat_ty_le(t)
    from PySide6.QtCore import QTimer
    _CHO[0] = t
    _bao_ty_le(t)
    if not _HEN:
        hen = QTimer()
        hen.setSingleShot(True)
        hen.timeout.connect(lambda: _CHO[0] is not None and dat_ty_le(_CHO[0]))
        _HEN.append(hen)
    _HEN[0].start(cho_ms)
    return t


def gian_cach(goc: QWidget) -> None:
    """Khoảng cách thoáng, đồng bộ giữa các phần tử: hàng ngang ≥ 10 px, cột dọc ≥ 8 px. Bỏ qua bố cục cố ý xếp sát
    (khoảng cách ≤ 3: ô nhập + nút ▼, menu trái, khung thẻ)."""
    from PySide6.QtWidgets import QBoxLayout, QHBoxLayout, QLayout
    ds = goc.findChildren(QLayout)
    if goc.layout() is not None:
        ds.append(goc.layout())
    for lo in ds:
        if not isinstance(lo, QBoxLayout):
            continue
        cha = lo.parentWidget()
        if cha is not None and (cha.objectName() == 'menu_trong' or cha.property('vai') in ('ribbon', 'nhom_ribbon')):
            continue
        if lo.property('giu_khoang_cach'):              # hàng cố ý xếp gọn (thẻ KPI 6 px - người dùng 15/10/2026)
            continue
        sp = lo.spacing()
        toi_thieu = 10 if isinstance(lo, QHBoxLayout) else 8
        if 3 < sp < toi_thieu:
            lo.setSpacing(toi_thieu)


# ---------------------------------------------------------------- cửa sổ chính / cửa sổ con chuẩn thương mại (đặc tả V10 mục I.5, I.6)
TOI_THIEU_CUA_SO = (1024, 680)        # cửa sổ chính không thu nhỏ hơn mức này (trừ khi màn hình nhỏ hơn)
KICH_THUOC_THUONG = (1200, 740)       # Restore Down của cửa sổ chính: kích thước chuẩn, canh giữa màn hình
_QWIDGETSIZE_MAX = 16777215


def kich_thuoc_thuong(w, rong: int = KICH_THUOC_THUONG[0], cao: int = KICH_THUOC_THUONG[1]) -> QRect:
    """Hình chữ nhật 1200 x 740 canh giữa vùng làm việc của màn hình chứa w (màn hình nhỏ hơn: thu vừa màn hình)."""
    man = (w.screen() if hasattr(w, 'screen') else None) or QApplication.primaryScreen()
    vung = man.availableGeometry()
    r, c = min(rong, vung.width()), min(cao, vung.height())
    return QRect(vung.x() + (vung.width() - r) // 2, vung.y() + (vung.height() - c) // 2, r, c)


def dat_toi_thieu_cua_so(w) -> None:
    """minimumSize 1024 x 680, nhưng không lớn hơn vùng làm việc của màn hình (1366 x 768 phóng 125%: chỉ ~1093 x 614 điểm)."""
    man = (w.screen() if hasattr(w, 'screen') else None) or QApplication.primaryScreen()
    vung = man.availableGeometry() if man is not None else None
    w.setMinimumSize(min(TOI_THIEU_CUA_SO[0], vung.width()) if vung else TOI_THIEU_CUA_SO[0],
                     min(TOI_THIEU_CUA_SO[1], vung.height()) if vung else TOI_THIEU_CUA_SO[1])


def _cai_dat_cua_so():
    """QSettings nhớ kích thước cửa sổ con; chạy không màn hình (offscreen - kiểm thử) thì không đọc / ghi."""
    app = QApplication.instance()
    if app is None or app.platformName() == 'offscreen':
        return None
    return QSettings('PABT', 'PABT')


def khoa_kich_thuoc(dlg) -> str:
    return f'cua_so/{type(dlg).__name__}'


def khoi_phuc_kich_thuoc(dlg, cai=None) -> bool:
    """Đặt lại kích thước / vị trí cửa sổ con đã nhớ (cai: QSettings; None = QSettings của phần mềm). True nếu có bản nhớ."""
    cai = cai if cai is not None else _cai_dat_cua_so()
    if cai is None:
        return False
    try:
        b = cai.value(khoa_kich_thuoc(dlg), None)
        if not b or not dlg.restoreGeometry(b):
            return False
    except (TypeError, ValueError):
        return False
    vua_man_hinh(dlg)                                       # màn hình đổi (rút màn hình phụ, đổi độ phân giải): vẫn nằm trong màn hình
    return True


def nho_kich_thuoc(dlg, cai=None) -> bool:
    cai = cai if cai is not None else _cai_dat_cua_so()
    if cai is None:
        return False
    cai.setValue(khoa_kich_thuoc(dlg), dlg.saveGeometry())
    return True


def la_cua_so_con_pabt(obj) -> bool:
    """Hộp thoại / cửa sổ con nghiệp vụ của PABT (lớp trong gói pabt): không đụng QMessageBox, QFileDialog… của Qt."""
    from PySide6.QtWidgets import QDialog
    return isinstance(obj, QDialog) and type(obj).__module__.split('.')[0] == 'pabt' and obj.isWindow()


def chuan_hoa_cua_so_con(dlg, cai=None) -> bool:
    """Mọi cửa sổ con nghiệp vụ: đủ nút Thu nhỏ, Phóng to, Đóng (Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint), tay nắm
    co giãn ở góc dưới phải (setSizeGripEnabled), nhớ kích thước qua QSettings. Hộp thoại cố định kích thước (min = max) giữ nguyên.
    Gọi một lần cho mỗi cửa sổ, ở sự kiện Polish (trước khi hiện: đổi cờ cửa sổ không làm cửa sổ chớp). True nếu đã xử lý."""
    if dlg.property('pabt_cua_so_con'):
        return False
    dlg.setProperty('pabt_cua_so_con', True)
    if not (dlg.minimumSize() == dlg.maximumSize() and dlg.maximumSize().width() < _QWIDGETSIZE_MAX):
        co = dlg.windowFlags()
        W = Qt.WindowType                                   # CustomizeWindowHint: chỉ định tường minh từng nút (không thì Qt tự chọn)

        def so(x) -> int:                                   # Flag -> số nguyên (PySide6: .value; PySide2: int())
            return int(getattr(x, 'value', x))
        # tính bằng số nguyên: toán tử ~ của enum Flag (PySide6) chỉ giữ các bit "có tên", làm rơi mất WindowCloseButtonHint
        them = (W.CustomizeWindowHint, W.WindowTitleHint, W.WindowSystemMenuHint, W.WindowMinimizeButtonHint,
                W.WindowMaximizeButtonHint, W.WindowCloseButtonHint)
        bit = so(co)
        for x in them:
            bit |= so(x)
        moi = W(bit & ~so(W.WindowContextHelpButtonHint))
        if moi != co:
            dlg.setWindowFlags(moi)
        dlg.setSizeGripEnabled(True)
        khoi_phuc_kich_thuoc(dlg, cai)
    return True


_SU_KIEN = (QEvent.Type.Wheel, QEvent.Type.KeyPress, QEvent.Type.Show, QEvent.Type.Polish, QEvent.Type.Hide)
XU_LY_HOAN_TAC = []        # hàm (lam_lai) -> bool của cửa sổ chính: hoàn tác thao tác đã ghi vào file dự án


def _dang_go_chu(w) -> bool:
    """Ô đang gõ chữ: Ctrl+Z / Ctrl+Y để ô tự hoàn tác chữ vừa gõ."""
    from PySide6.QtWidgets import QAbstractSpinBox, QComboBox, QLineEdit, QPlainTextEdit, QTextEdit
    if isinstance(w, QLineEdit):
        return not w.isReadOnly()
    if isinstance(w, (QPlainTextEdit, QTextEdit)):
        return not w.isReadOnly()
    if isinstance(w, QAbstractSpinBox):
        return True
    return isinstance(w, QComboBox) and w.isEditable()


def xu_ly_hoan_tac(lam_lai: bool) -> bool:
    """Ctrl+Z / Ctrl+Y ngoài ô chữ: khung / cửa sổ gần nhất (từ ô đang chọn đi lên) có hàm hoan_tac_phim(lam_lai) -> True nếu
    đã xử lý; không có thì cửa sổ chính (hoàn tác thao tác đã ghi file) - chỉ khi đang ở cửa sổ chính, để hộp thoại đang mở
    không hiện số liệu cũ."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    w = app.focusWidget() or app.activeWindow()
    while w is not None:
        ham = getattr(w, 'hoan_tac_phim', None)
        if ham is not None and ham(lam_lai):
            return True
        w = w.parentWidget()
    cs = app.activeWindow()
    if cs is not None and getattr(cs, 'la_cua_so_chinh', False):
        return any(h(lam_lai) for h in list(XU_LY_HOAN_TAC))
    return False


class BangHoanTac(QObject):
    """Hoàn tác / làm lại sửa ô cho một QTableWidget (bảng nhập chưa ghi file: thửa đất, dữ liệu thô...)."""
    VAI = Qt.ItemDataRole.UserRole + 50

    def __init__(self, bang):
        super().__init__(bang)
        self.bang = bang
        self.lui, self.toi = [], []
        self._dang = False
        bang.itemChanged.connect(self._doi)
        self.ghi_nho()

    def ghi_nho(self):
        """Ghi lại chữ hiện tại của mọi ô làm mốc (gọi sau khi nạp lại bảng); xóa lịch sử."""
        self._dang = True
        try:
            for r in range(self.bang.rowCount()):
                for c in range(self.bang.columnCount()):
                    it = self.bang.item(r, c)
                    if it is not None:
                        it.setData(self.VAI, it.text())
        finally:
            self._dang = False
        self.lui, self.toi = [], []

    def _doi(self, it):
        if self._dang:
            return
        cu = it.data(self.VAI)
        moi = it.text()
        if cu is None or cu == moi:
            self._dang = True
            it.setData(self.VAI, moi)
            self._dang = False
            return
        self.lui.append((it.row(), it.column(), cu, moi))
        self.toi = []
        self._dang = True
        it.setData(self.VAI, moi)
        self._dang = False

    def _dat(self, r, c, chu):
        it = self.bang.item(r, c)
        if it is None:
            return
        self._dang = True
        try:
            it.setText(chu)
            it.setData(self.VAI, chu)
        finally:
            self._dang = False
        self.bang.setCurrentCell(r, c)

    def hoan_tac(self) -> bool:
        if not self.lui:
            return False
        r, c, cu, moi = self.lui.pop()
        self._dat(r, c, cu)
        self.toi.append((r, c, cu, moi))
        return True

    def lam_lai(self) -> bool:
        if not self.toi:
            return False
        r, c, cu, moi = self.toi.pop()
        self._dat(r, c, moi)
        self.lui.append((r, c, cu, moi))
        return True


def _tieu_diem():
    """Widget nhận phím: ô đang chọn, không có thì cửa sổ đang dùng (sự kiện phím chỉ xử lý một lần, không lặp ở cha)."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    return app.focusWidget() or app.activeWindow()


class _BoToMau(QObject):
    def eventFilter(self, obj, ev):
        t = ev.type()
        if t not in _SU_KIEN:                           # bộ lọc chạy với MỌI sự kiện của phần mềm: thoát sớm cho nhanh
            return False
        # Ctrl + con lăn chuột / Ctrl + "+" "-" "0": phóng to, thu nhỏ, về 100% ở mọi cửa sổ
        if t == QEvent.Type.Wheel and ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
            d = ev.angleDelta().y()
            if d:
                phong_to(1 if d > 0 else -1)
            return True
        if t == QEvent.Type.KeyPress and ev.modifiers() & Qt.KeyboardModifier.ControlModifier and isinstance(obj, QWidget):
            k = ev.key()
            if k in (Qt.Key.Key_Z, Qt.Key.Key_Y) and obj is _tieu_diem():
                if _dang_go_chu(obj):
                    return False                          # ô chữ tự hoàn tác chữ vừa gõ
                lai = k == Qt.Key.Key_Y or bool(ev.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                xu_ly_hoan_tac(lai)
                return True
            if k in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                phong_to(1)
                return True
            if k == Qt.Key.Key_Minus:
                phong_to(-1)
                return True
            if k == Qt.Key.Key_0:
                phong_to(0)
                return True
        if t == QEvent.Type.Polish:                     # sắp hiện lần đầu: cửa sổ con có đủ nút Thu nhỏ / Phóng to / Đóng
            if la_cua_so_con_pabt(obj):
                chuan_hoa_cua_so_con(obj)
            return False
        if t == QEvent.Type.Hide:                       # đóng cửa sổ con: nhớ kích thước cho lần mở sau
            if isinstance(obj, QWidget) and obj.property('pabt_cua_so_con') and obj.isWindow():
                nho_kich_thuoc(obj)
            return False
        if t == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow():
            to_mau(obj)
            for bang in obj.findChildren(QAbstractItemView):    # dòng bảng dữ liệu 32 px (đặc tả mục 3.3)
                vh = getattr(bang, 'verticalHeader', None)
                if vh is not None and vh().defaultSectionSize() < CAO_DONG_BANG:
                    vh().setDefaultSectionSize(CAO_DONG_BANG)
            gian_cach(obj)
            if TY_LE[0] != 1:
                for w in [obj, *obj.findChildren(QWidget)]:
                    _co_gian_widget(w, TY_LE[0])
            from PySide6.QtWidgets import QDialog, QLineEdit, QMessageBox
            for o in obj.findChildren(QLineEdit):        # chữ dài: hiện từ đầu chữ thay vì phần cuối
                if not o.hasFocus() and o.text():
                    o.setCursorPosition(0)
            if isinstance(obj, QDialog) and not isinstance(obj, QMessageBox):
                vua_man_hinh(obj)
        return False


_BAO_LOI = {'dang': False, 'luc': 0.0}


def cai_bat_loi() -> None:
    """Lỗi không bắt được trong nút bấm / sự kiện Qt: chạy bằng pythonw / bản exe (không có cửa sổ lệnh) trước đây mất im lặng -
    người dùng thấy nút "không phản ứng". Nay ghi <thư mục máy>\\loi.log và hiện hộp báo lỗi (một lần mỗi 5 giây, không lồng nhau)."""
    import sys
    import time
    import traceback
    from datetime import datetime
    goc = sys.excepthook

    def bat(loai, gia_tri, tb):
        if issubclass(loai, KeyboardInterrupt):
            return goc(loai, gia_tri, tb)
        chu = ''.join(traceback.format_exception(loai, gia_tri, tb))
        file_log = None
        try:
            from .may_chu import thu_muc_may
            file_log = thu_muc_may() / 'loi.log'
            file_log.parent.mkdir(parents=True, exist_ok=True)
            with open(file_log, 'a', encoding='utf-8') as f:
                f.write(f'==== {datetime.now():%d/%m/%Y %H:%M:%S}\n{chu}\n')
        except OSError:
            file_log = None
        if _BAO_LOI['dang'] or time.time() - _BAO_LOI['luc'] < 5:
            return
        _BAO_LOI['dang'], _BAO_LOI['luc'] = True, time.time()
        try:
            from PySide6.QtWidgets import QApplication
            if QApplication.instance() is not None:
                them = []
                try:                                    # nút gói chẩn đoán: lỗi nạp module thì vẫn hiện hộp báo lỗi
                    from .man_hinh_chan_doan import NUT_GOI, xuat_goi_chan_doan
                    file_da = next((w.file for w in QApplication.topLevelWidgets()
                                    if getattr(w, 'file', None) and hasattr(w, 'khung_menu')), None)   # dự án đang mở
                    them = [(NUT_GOI, lambda d: xuat_goi_chan_doan(d, file_da, loi_text=chu))]
                except Exception:                       # noqa: BLE001
                    pass
                hop_ket_qua(QApplication.activeWindow(), f'Có lỗi không mong muốn: {loai.__name__}: {gia_tri}\n\nThao tác vừa '
                            'rồi có thể chưa hoàn tất; dữ liệu đã lưu trước đó không bị ảnh hưởng.' +
                            (f' Chi tiết đã ghi vào {file_log}.' if file_log else ''), chu.splitlines(),
                            'Chi tiết lỗi (bấm Chép, gửi cho người hỗ trợ)', canh_bao=True,
                            nut_them=them)
        except Exception:                               # noqa: BLE001 - báo lỗi không được thì thôi, không gây lỗi chồng
            pass
        finally:
            _BAO_LOI['dang'] = False
    sys.excepthook = bat


def bo_ap_dung(app) -> None:
    """Gỡ những gì ap_dung đã đặt (bảng kiểu, bộ lọc sự kiện) - cho kiểm thử; sau đó gọi ap_dung lại sẽ áp từ đầu."""
    app.setStyleSheet('')
    bo = getattr(app, '_bo_to_mau', None)
    if bo is not None:
        app.removeEventFilter(bo)
        app._bo_to_mau = None


def ap_dung(app) -> None:
    """Gọi một lần khi khởi động: kiểu Fusion sáng, bảng màu, tiếng Việt cho nút chuẩn (Yes/No…), tô màu nút.
    Gọi lại (kiểm thử gọi trong setUp) không làm gì: trước 0.9.80 mỗi lần gọi CÀI THÊM một bộ lọc sự kiện _BoToMau (bộ cũ không gỡ) và
    đặt lại bảng kiểu toàn ứng dụng -> mọi sự kiện bị xử lý N lần, mọi widget tô lại kiểu; bộ test chậm theo bậc hai tới mức tưởng treo."""
    if getattr(app, '_bo_to_mau', None) is not None:
        return
    app.setStyle('Fusion')
    app.setWindowIcon(bieu_tuong())
    # phông Segoe UI (có đủ dấu tiếng Việt, có sẵn từ Windows 7): tránh Qt chọn phông thay thế làm lệch / mất dấu
    from PySide6.QtGui import QFont
    f = QFont('Segoe UI')
    f.setPointSizeF(9.5)
    f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(f)
    p = QPalette()
    for vai_, mau in ((QPalette.ColorRole.Window, TOKEN['nen']), (QPalette.ColorRole.Base, TOKEN['khung']),
                      (QPalette.ColorRole.AlternateBase, '#F3F6FB'), (QPalette.ColorRole.Text, TOKEN['chu']),
                      (QPalette.ColorRole.WindowText, TOKEN['chu']), (QPalette.ColorRole.ButtonText, TOKEN['chu']),
                      (QPalette.ColorRole.Button, '#FFFFFF'), (QPalette.ColorRole.Highlight, '#2E75B6'),
                      (QPalette.ColorRole.HighlightedText, '#FFFFFF'), (QPalette.ColorRole.ToolTipBase, '#FFFDE7'),
                      (QPalette.ColorRole.ToolTipText, '#1A1A1A')):
        p.setColor(vai_, QColor(mau))
    app.setPalette(p)
    app.setStyleSheet(_qss_day_du())
    tr = QTranslator(app)
    if tr.load(QLocale('vi'), 'qtbase', '_', QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(tr)
    app._bo_to_mau = _BoToMau(app)
    app.installEventFilter(app._bo_to_mau)
    from PySide6.QtCore import QSettings
    try:
        t = float(QSettings('PABT', 'PABT').value('giao_dien/ty_le', 1.0) or 1.0)
    except (TypeError, ValueError):
        t = 1.0
    if abs(t - 1) > 0.001:
        dat_ty_le(t, luu=False)

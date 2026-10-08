"""Màu giao diện: nút bấm tô theo nhóm chức năng, tiêu đề bảng / thuộc tính đậm màu, bảng xen màu dòng.

Nút được tô tự động theo chữ trên nút (Lưu, Thêm, Xóa, Gộp, In…) khi cửa sổ hiện ra, nên mọi hộp thoại đều thống nhất
mà không phải sửa từng màn hình. Muốn đổi màu một nhóm: sửa MAU.
"""
from __future__ import annotations
import re

from PySide6.QtCore import QEvent, QLibraryInfo, QLocale, QObject, QPoint, QRect, QSize, QTimer, QTranslator
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractButton, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLayout, QPushButton, QRadioButton,
                               QStyledItemDelegate, QToolButton, QVBoxLayout, QWidget)

from .lap_pa import bo_dau

CHINH = '#1F4E79'           # xanh đậm: tiêu đề bảng, nhãn thuộc tính, tab đang chọn
# nhóm nút: (nền, chữ, nền khi rê chuột)
MAU = {                                            # tông dịu kiểu phần mềm quản lý: chỉ nút Lưu nền đặc, nút khác nền nhạt
    'luu':    ('#2F7A4F', '#FFFFFF', '#27673F'),   # Lưu, Áp dụng
    'them':   ('#1D7A6C', '#FFFFFF', '#17675B'),   # Thêm…
    'xoa':    ('#B8433A', '#FFFFFF', '#9C3830'),   # Xóa…
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
    (r'tra bang gia|lay gia|tra gia|kiem tra loi|kiem tra lai|kiem tra an toan|quy chuan|tinh mat do', 'tra'),
    (r'^cap nhat', 'nhap'),
    (r'(^|\W)in(\W|$)|xuat|pdf|bao cao', 'in'),
    (r'^ho so', 'hoso'),
    (r'lap phuong an', 'pa'),
    (r'^(nhap|mo du an|nap|cap nhat)', 'nhap'),
    (r'goi y|chon|ra soat|thong tin|doi chieu|ho truoc|ho sau|tim|tra cuu|quay lai|^tiep', 'tra'),
]


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
        return f'''QPushButton[nhom="{n}"] {{ color: {chu}; background: {nen}; border: 1px solid {re_}; border-radius: 6px;
            padding: 6px 16px; font-weight: 600; }}
        QPushButton[nhom="{n}"]:hover {{ background: {re_}; }}
        QPushButton[nhom="{n}"]:pressed {{ background: {_tron(re_, 0.12, '#000000')}; }}'''
    # nút viền (outline): nền trắng, chữ trung tính, chỉ biểu tượng mang màu nhóm; rê chuột mới hiện nền nhạt cùng màu
    return f'''QPushButton[nhom="{n}"] {{ color: #253545; background: #FFFFFF; border: 1px solid #CDD6E0; border-radius: 6px;
            padding: 6px 14px; font-weight: 600; }}
        QPushButton[nhom="{n}"]:hover {{ background: {_tron(nen, 0.93)}; border-color: {_tron(nen, 0.55)}; color: {_tron(nen, 0.15, '#000000')}; }}
        QPushButton[nhom="{n}"]:pressed {{ background: {_tron(nen, 0.86)}; }}'''


def mau_chu_nut(n: str | None) -> str:
    """Màu biểu tượng trên QPushButton theo nhóm (nền đặc: chữ trắng; nền nhạt: màu nhóm)."""
    if not n or n == 'nhat':
        return CHINH
    return MAU[n][1] if n in DAC else _tron(MAU[n][0], 0.08, '#000000')


def _qss() -> str:
    nut = '\n'.join(
        f'''{_nut_qss(n, nen, chu, re_)}
        QToolButton[nhom="{n}"] {{ background: {nen}; color: {chu}; border: 1px solid {re_}; border-radius: 6px; padding: 4px 8px;
            font-weight: 600; }}
        QToolButton[nhom="{n}"]:hover {{ background: {re_}; }}
        QToolButton[ribbon="1"][nhom="{n}"] {{ background: {_tron(nen, 0.9) if n != 'nhat' else '#F3F6F9'};
            color: {nen if n != 'nhat' else CHINH}; border: 1px solid {_tron(nen, 0.72) if n != 'nhat' else '#D5DEE7'};
            border-radius: 7px; padding: 4px 10px; font-weight: 600; text-align: left; }}
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
    QPushButton {{ border-radius: 6px; padding: 6px 14px; border: 1px solid #CBD5E0; background: #FFFFFF; color: #1F2D3A; }}
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
        border: 1px solid #D5E1ED; border-left: 4px solid #F2B705; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QPlainTextEdit, QTextEdit {{ background: #FFFFFF;
        border: 1px solid #C9D3DD; border-radius: 6px; padding: 4px 8px; selection-background-color: #2E75B6; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{ min-height: 20px; }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QPlainTextEdit:hover {{ border-color: #9FB6CC; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{
        border: 1px solid #2E75B6; background: #FBFDFF; }}
    QLineEdit:read-only {{ background: #F1F4F7; color: #4A5866; }}
    QToolButton[nho="1"] {{ font-size: 11px; padding: 3px 6px 2px 6px; }}
    QToolButton[menu="1"] {{ background: transparent; border: 1px solid transparent; border-radius: 7px; padding: 5px 10px;
        text-align: left; font-weight: 600; font-size: 13px; color: #172A3D; }}
    QToolButton[menu="1"]:hover {{ background: #E8F0F8; border-color: #C9D9EA; }}
    QToolButton[menu="1"]:pressed {{ background: #D6E4F2; }}
    QToolButton[menu="1"]:checked {{ background: #DCEBFA; border-color: #9FC3E8; font-weight: 600; }}
    QToolButton[xo="1"] {{ background: #EEF3F8; border-color: #D5E1ED; padding-right: 22px; color: {CHINH}; }}
    QToolButton[xo="1"]::menu-indicator {{ subcontrol-position: right center; right: 8px; }}
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
        margin-top: 14px; padding: 10px 8px 6px 8px; }}
    QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 6px;
        background: transparent; }}
    QStatusBar {{ background: #FFFFFF; color: {CHINH}; border-top: 1px solid #DCE4EC; }}
    QStatusBar QToolButton {{ border-radius: 6px; padding: 3px 10px; }}
    QFrame[vai="bang_to_chuc"] {{ background: transparent; border: 0; }}
    QFrame[vai="bang_to_chuc"] QLabel {{ color: #FFFFFF; background: transparent; border: 0; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="logo"] {{ background: #FFFFFF; border: 2px solid #F2B705; border-radius: 16px; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="ten_phan_mem"] {{ color: #FFFFFF; font-size: 22px; font-weight: 700; letter-spacing: 0.5px;
        min-height: 32px; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="ten_to_chuc"] {{ color: #FFD54F; font-size: 16px; font-weight: 700; letter-spacing: 0.6px; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="dong_phu"] {{ color: #C7DBEF; font-size: 13px; }}
    QFrame[vai="bang_to_chuc"] QToolButton[vai="nut_bang"] {{ color: #FFFFFF; background: rgba(255, 255, 255, 26);
        border: 1px solid rgba(255, 255, 255, 70); border-radius: 7px; padding: 3px 10px; font-weight: 600; font-size: 13px; }}
    QFrame[vai="bang_to_chuc"] QToolButton[vai="nut_bang"]:hover {{ background: rgba(255, 255, 255, 52);
        border-color: #FFD54F; }}
    QFrame[vai="bang_to_chuc"] QToolButton[vai="nut_bang"]:pressed {{ background: rgba(255, 255, 255, 80); }}
    QFrame[vai="bang_to_chuc"] QToolButton[vai="nut_bang"]:disabled {{ color: rgba(255, 255, 255, 110);
        background: transparent; border-color: rgba(255, 255, 255, 40); }}
    QLabel[vai="nhom_menu"] {{ color: #4A6785; font-size: 11px; font-weight: 700; letter-spacing: 0.6px;
        background: transparent; border: 0; border-radius: 5px; padding: 5px 4px 3px 4px; }}
    QLabel[vai="nhom_menu"]:hover {{ color: {CHINH}; background: #EEF3F8; }}
    QLabel[vai="nhom_menu"][dong="1"] {{ color: #6D8299; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="phien_ban"] {{ color: #FFE082; background: rgba(255, 255, 255, 18); font-weight: 600;
        font-size: 11px; border: 1px solid rgba(255, 213, 79, 150); border-radius: 10px; padding: 2px 10px; }}
    QFrame[vai="vach_vang"] {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F2B705, stop:0.7 rgba(242,183,5,90),
        stop:1 rgba(242,183,5,0)); border: 0; }}
    QFrame[vai="ribbon"] {{ background: #FFFFFF; border: 1px solid #DCE4EC; border-radius: 10px; }}
    QFrame[vai="nhom_ribbon"] {{ background: #F7FAFD; border: 1px solid #E5ECF3; border-radius: 8px; }}
    QLabel[vai="nhan_ribbon"] {{ color: #4A6785; font-size: 11px; font-weight: 700; letter-spacing: 0.6px;
        background: transparent; border: 0; }}
    QLabel[vai="dong_phu"] {{ color: #DCEBFA; font-size: 12px; }}
    '''


def bieu_tuong():
    """Biểu tượng phần mềm (pabt/bieu_tuong.png, vẽ bằng tao_bieu_tuong.py)."""
    from PySide6.QtGui import QIcon
    from . import tai_nguyen
    return QIcon(str(tai_nguyen('bieu_tuong.png')))


# ---------------------------------------------------------------- biểu tượng nút (ký hiệu Segoe Fluent Icons / MDL2 Assets)
# (mẫu trên chữ đã bỏ dấu, mã ký hiệu) - xét theo thứ tự; Windows 7 không có các phông này thì nút chỉ hiện chữ
KY_HIEU = [
    (r'an toan', 0xEA18),
    (r'^danh sach ho', 0xE716), (r'tong quat ho', 0xE8FD), (r'^quyet dinh phe duyet', 0xE8A5), (r'tong hop tien', 0xE9F9),
    (r'theo doi tien do', 0xE9D2), (r'^bang tong hop', 0xE80A), (r'^hoan tac', 0xE7A7), (r'^lam lai', 0xE7A6),
    (r'du an tren may chu', 0xE839), (r'mang ve lam offline', 0xE896), (r'dua len may chu', 0xE898),
    (r'^dang nhap', 0xE77B), (r'du an moi', 0xE710), (r'^mo du an|^mo du toan', 0xE8E5), (r'luu du an thanh', 0xE792), (r'^(luu|save)', 0xE74E),
    (r'^thuc hien', 0xE768),
    (r'nhap file excel|^nhap tu|^tu file|^tu danh sach|^tu du an', 0xE8B5), (r'thong tin du an|gioi thieu', 0xE946),
    (r'^ho so ho', 0xE77B), (r'^them ho', 0xE8FA), (r'lap phuong an', 0xE70F), (r'kiem tra loi|kiem tra lai', 0xE9D5),
    (r'bo don gia', 0xE8FD), (r'don gia rieng', 0xE8EC), (r'ra soat', 0xE721), (r'quy chuan|tinh mat do', 0xE8F1), (r'du toan', 0xE8EF),
    (r'^dot trinh', 0xE8B7), (r'trang thai ho', 0xE73A), (r'nhap quyet dinh', 0xE8A5), (r'bao cao tong hop', 0xE9F9),
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
                h.setWindowTitle('PABT')
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


MAU_BANG = ('#0A2747', '#113D6A', '#1B5A92')       # nền băng tiêu đề: xanh đậm -> xanh (đồng bộ màu bộ cài)
VANG = '#F2B705'


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
        sang = QRadialGradient(QPointF(r.left() + 58, r.top() + h * 0.5), h * 1.5)    # quầng sáng sau biểu tượng
        sang.setColorAt(0, QColor(255, 255, 255, 34))
        sang.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(r, sang)
        x0, rong = r.left() + w * 0.62, w * 0.38 + 2
        for i, pts in enumerate(_THUA):
            da_giac = QPolygonF([QPointF(x0 + u * rong, r.top() - 4 + v * (h + 8)) for u, v in pts])
            if i == _THUA_THU_HOI:
                p.setPen(QPen(QColor(242, 183, 5, 190), 1.6, Qt.PenStyle.DashLine))
                p.setBrush(QColor(242, 183, 5, 40))
            else:
                p.setPen(QPen(QColor(255, 255, 255, 40), 1))
                p.setBrush(QColor(255, 255, 255, 12 if i % 4 == 0 else 0))
            p.drawPolygon(da_giac)
        mo = QLinearGradient(QPointF(x0, 0), QPointF(x0 + rong * 0.45, 0))            # họa tiết mờ dần về phía chữ
        mo.setColorAt(0, QColor(MAU_BANG[1]))
        mo.setColorAt(1, QColor(17, 61, 106, 0))
        p.fillRect(QRectF(x0 - 1, r.top(), rong * 0.45 + 1, h), mo)
        vach = QLinearGradient(r.bottomLeft(), r.bottomRight())
        vach.setColorAt(0, QColor(VANG))
        vach.setColorAt(0.65, QColor('#FFD54F'))
        vach.setColorAt(1, QColor(242, 183, 5, 70))
        p.fillRect(QRectF(r.left(), r.bottom() - 4, w, 4), vach)
        p.end()


def bang_to_chuc(phai: str = '', nut: tuple = ()) -> QFrame:
    """Băng tiêu đề: biểu tượng (khung trắng viền vàng) | tên phần mềm (trắng) + nút (nut: Hoàn tác / Làm lại, cùng dòng) /
    tổ chức làm nhiệm vụ bồi thường (vàng) / trực thuộc - địa chỉ | phiên bản. Mọi dòng chữ canh trái cùng một cột (pabt/to_chuc.py)."""
    from . import to_chuc
    khung = BangToChuc()
    khung.setProperty('vai', 'bang_to_chuc')
    lo = QHBoxLayout(khung)
    lo.setContentsMargins(18, 12, 20, 16)
    lo.setSpacing(18)
    logo = QLabel()
    logo.setProperty('vai', 'logo')
    logo.setFixedSize(84, 84)
    logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
    logo.setPixmap(bieu_tuong().pixmap(72, 72))
    lo.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)
    cot = QVBoxLayout()
    cot.setSpacing(3)
    tieu_de = QLabel(TEN_PHAN_MEM)
    tieu_de.setProperty('vai', 'ten_phan_mem')
    dong_dau = QHBoxLayout()
    dong_dau.setSpacing(6)
    dong_dau.addWidget(tieu_de)
    if nut:
        dong_dau.addSpacing(14)
    for b in nut:
        b.setProperty('vai', 'nut_bang')
        dong_dau.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
    dong_dau.addStretch(1)
    cot.addLayout(dong_dau)
    ten = QLabel(f'{to_chuc.TEN}')
    ten.setProperty('vai', 'ten_to_chuc')
    cot.addWidget(ten)
    phu = QLabel(f'Trực thuộc {to_chuc.TRUC_THUOC}   •   {to_chuc.DIA_CHI}')
    phu.setProperty('vai', 'dong_phu')
    phu.setWordWrap(True)
    cot.addWidget(phu)
    lo.addLayout(cot, 1)
    if phai:
        p = QLabel(phai)
        p.setProperty('vai', 'phien_ban')
        p.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lo.addWidget(p, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
    return khung


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


def nut_lenh(a, co_icon: int = 18, duoi: bool = False) -> QToolButton:
    """Nút lệnh trên thanh / menu, nền nhạt theo màu nhóm. duoi: biểu tượng trên, chữ dưới (kiểu ribbon nhỏ, nút hẹp)."""
    from PySide6.QtWidgets import QSizePolicy
    b = QToolButton()
    a.setIconText(a.text().rstrip('…').rstrip('.'))     # Qt5 không tự bỏ dấu "…" như Qt6
    k = ky_hieu_nut(a.text())
    ic = icon_ky_hieu(k, mau_icon(a.text()), co_icon) if k else None
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
        nhan = QLabel(ten.upper())
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


KHOA_NHOM_DONG = 'giao_dien/menu_trai_dong'            # QSettings: tên các nhóm menu trái đang đóng, nối bằng "|"


def _doc_nhom_dong(mac_dinh: tuple) -> set:
    from PySide6.QtCore import QSettings
    try:
        v = QSettings('PABT', 'PABT').value(KHOA_NHOM_DONG, None)
    except Exception:
        v = None
    if v is None:
        return set(mac_dinh)
    return {x for x in str(v).split('|') if x}


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
    ngoai.setContentsMargins(6, 6, 6, 6)
    ngoai.setSpacing(4)
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
        b = nut_lenh(a, 22)                                  # biểu tượng 22 px, nét dày (icon_ky_hieu)
        b.setProperty('ribbon', '0')
        b.setProperty('menu', '1')                           # kiểu danh sách: không viền, rê chuột mới hiện nền
        b.setMinimumHeight(32)
        b.setToolTip(a.text().rstrip('…'))
        nut.append(b)
        return b

    for ten, ds in nhom:
        if ten in xo:                                        # một nút, bấm xổ danh sách lệnh của nhóm
            b = QToolButton()
            b.setText(ten)
            k = ky_hieu_nut('Mở dự án') if ten == 'Dự án' else ky_hieu_nut(ten)
            ic = icon_ky_hieu(k, CHINH, 22) if k else None
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
            b.setMinimumHeight(34)
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
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly if gon and not b.icon().isNull()
                                 else Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        ve_nhom()
        khung.setFixedWidth(70 if gon else 248)
        b_gon.setText('' if gon else '  Thu gọn menu')
        ic = icon_ky_hieu(0xE76C if gon else 0xE76B, CHINH, 16)       # mũi tên mở rộng / thu gọn
        b_gon.setIcon(ic) if ic is not None else b_gon.setText('»' if gon else '«  Thu gọn menu')
        b_gon.setToolTip('Mở rộng menu' if gon else 'Thu gọn menu (chỉ hiện biểu tượng)')
    b_gon.clicked.connect(lambda: dat(not khung.thu_gon))
    dat(thu_gon_luc_dau)
    return do_bong(khung, 16, 2, 30)


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


def mo_danh_sach(cb) -> None:
    """Ô xổ vừa mở để sửa: hiện luôn danh sách (không phải bấm thêm lần nữa)."""
    QTimer.singleShot(0, lambda: cb.showPopup() if cb.isVisible() else None)


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
        cb = QComboBox(parent)
        cb.setEditable(True)
        cb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        cb.setMaxVisibleItems(20)
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
        self.ds.clear()
        self.ds.addItems(ds[:self.TOI_DA])
        for i in range(self.ds.count()):                # nhãn dài: xem đủ khi rê chuột
            it = self.ds.item(i)
            if len(it.text()) > 60:
                it.setToolTip(it.text())
        self.ds.setCurrentRow(0)
        cao = min(16, self.ds.count()) * (self.ds.sizeHintForRow(0) or 24) + 6
        self.ds.resize(max(self.width(), 640), cao)
        self.ds.move(self.o.mapToGlobal(self.o.rect().bottomLeft()))
        self.ds.show()
        self.ds.raise_()

    def _go(self, chu: str):
        self.chon = self._theo_nhan.get(chu)
        self._hien(self.loc(chu) if chu.strip() else [])

    def xem_tat_ca(self):
        self.o.setFocus()
        self._hien(self.loc(''))

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
                hien: bool = True, tieu_de: str = 'PABT - Lập phương án bồi thường, hỗ trợ'):
    """Hộp kết quả không bao giờ cao quá màn hình (QMessageBox giãn theo chữ: danh sách dài đẩy nút OK ra ngoài màn hình):
    tóm tắt ngắn ở trên, danh sách ĐẦY ĐỦ trong ô cuộn, nút Chép (dán sang Excel / Zalo) và Đóng. hien=False: chỉ tạo (kiểm thử)."""
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
        app.setStyleSheet(_co_gian(_qss(), t))
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
        sp = lo.spacing()
        toi_thieu = 10 if isinstance(lo, QHBoxLayout) else 8
        if 3 < sp < toi_thieu:
            lo.setSpacing(toi_thieu)


_SU_KIEN = (QEvent.Type.Wheel, QEvent.Type.KeyPress, QEvent.Type.Show)
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
        if t == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow():
            to_mau(obj)
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
                hop_ket_qua(QApplication.activeWindow(), f'Có lỗi không mong muốn: {loai.__name__}: {gia_tri}\n\nThao tác vừa '
                            'rồi có thể chưa hoàn tất; dữ liệu đã lưu trước đó không bị ảnh hưởng.' +
                            (f' Chi tiết đã ghi vào {file_log}.' if file_log else ''), chu.splitlines(),
                            'Chi tiết lỗi (bấm Chép, gửi cho người hỗ trợ)', canh_bao=True)
        except Exception:                               # noqa: BLE001 - báo lỗi không được thì thôi, không gây lỗi chồng
            pass
        finally:
            _BAO_LOI['dang'] = False
    sys.excepthook = bat


def ap_dung(app) -> None:
    """Gọi một lần khi khởi động: kiểu Fusion sáng, bảng màu, tiếng Việt cho nút chuẩn (Yes/No…), tô màu nút."""
    app.setStyle('Fusion')
    app.setWindowIcon(bieu_tuong())
    # phông Segoe UI (có đủ dấu tiếng Việt, có sẵn từ Windows 7): tránh Qt chọn phông thay thế làm lệch / mất dấu
    from PySide6.QtGui import QFont
    f = QFont('Segoe UI')
    f.setPointSizeF(9.5)
    f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(f)
    p = QPalette()
    for vai_, mau in ((QPalette.ColorRole.Window, '#F7F9FC'), (QPalette.ColorRole.Base, '#FFFFFF'),
                      (QPalette.ColorRole.AlternateBase, '#EEF4FA'), (QPalette.ColorRole.Text, '#1A1A1A'),
                      (QPalette.ColorRole.WindowText, '#1A1A1A'), (QPalette.ColorRole.ButtonText, '#1A1A1A'),
                      (QPalette.ColorRole.Button, '#FFFFFF'), (QPalette.ColorRole.Highlight, '#2E75B6'),
                      (QPalette.ColorRole.HighlightedText, '#FFFFFF'), (QPalette.ColorRole.ToolTipBase, '#FFFDE7'),
                      (QPalette.ColorRole.ToolTipText, '#1A1A1A')):
        p.setColor(vai_, QColor(mau))
    app.setPalette(p)
    app.setStyleSheet(_qss())
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

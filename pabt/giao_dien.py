"""Màu giao diện: nút bấm tô theo nhóm chức năng, tiêu đề bảng / thuộc tính đậm màu, bảng xen màu dòng.

Nút được tô tự động theo chữ trên nút (Lưu, Thêm, Xóa, Gộp, In…) khi cửa sổ hiện ra, nên mọi hộp thoại đều thống nhất
mà không phải sửa từng màn hình. Muốn đổi màu một nhóm: sửa MAU.
"""
from __future__ import annotations
import re
from contextlib import contextmanager
from enum import Enum

from PySide6.QtCore import QEvent, QLibraryInfo, QLocale, QObject, QPoint, QRect, QSettings, QSize, QTimer, QTranslator, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPolygon, QStandardItem, QStandardItemModel
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLayout, QPushButton, QRadioButton,
                               QSplitter, QSplitterHandle, QStyle, QStyleOptionViewItem, QTableView,
                               QLineEdit, QSpinBox, QStyledItemDelegate, QToolButton, QVBoxLayout, QWidget)

from .lap_pa import bo_dau
from .csdl import giai_phong_bo_nho, la_may_yeu  # noqa: F401  (1.0.08: máy cấu hình yếu)

# Hệ thống thiết kế (đặc tả ARCH-PABT-2026-V4 mục 3, người dùng 11/10/2026): MỘT nguồn màu cho cả phần mềm.
# 22/10/2026 "Ultra-Compact + UI/UX Pro Max": bảng màu tương phản WCAG AAA (chữ chính / navy trên nền trắng >= 7:1)
# 1.0.34 (người dùng 29/10/2026) "Flagship Sapphire": Royal Sapphire #1E3A5F (trước #2F5F9E), Electric Indigo #2563EB, Emerald,
# nền Cool Porcelain #F1F5F9 làm nổi thẻ trắng. nen / khung / vach / chu / chu_phu do tông nền đặt (dat_tong_nen, chu_de.TONG_NEN)
TOKEN = dict(
    chinh='#1E3A5F',          # Primary - Slate-Navy hạ bão hòa (1.0.35, PA1; 1.0.34: #1E3A8A) - mỗi tông đổi màu này (chu_de.MAU_TONG)
    chinh_re='#152C48',       # Deep Midnight Sapphire: rê chuột / đang nhấn
    chinh_nhat='#EFF6FF',     # Primary Light: nền mục đang chọn
    nhan='#2563EB',           # Accent - Electric Indigo: thẻ chọn, vòng focus, link, vạch chỉ thị
    phu='#059669',            # Success - Emerald: viền vùng chọn kiểu Excel, trạng thái hoàn thành
    thanh_cong='#059669',
    thanh_cong_nhat='#ECFDF5',
    canh_bao='#D97706',        # vạch / biểu tượng / viền cảnh báo (làm CHỮ chỉ 3,2:1 trên trắng - dùng canh_bao_chu)
    # 1.0.93 (kiểm toán 09/11/2026): chữ trạng thái đạt AA 4,5:1 trên nền sáng; tông Tối đổi qua TOI_CHU
    canh_bao_chu='#9A5A12',
    thanh_cong_chu='#047857',
    nguy_hiem_chu='#B91C1C',
    canh_bao_nhat='#FFFBEB',   # nền ô vàng (trước #FFF2CC rải rác)
    nguy_hiem='#DC2626',      # Danger
    nguy_hiem_nhat='#FEF2F2',
    chu='#0F172A',            # Neutral Dark: chữ chính
    chu_phu='#475569',        # Neutral Medium: chữ phụ
    vach='#D5DEE8',           # Divider / viền (tông mặc định 1.0.35: Sáng dịu Slate-Navy)
    vien='#D5DEE8',
    nen='#F3F6FA',            # Surface: nền cửa sổ
    nen_the='#FFFFFF',
    khung='#FFFFFF',          # Panel: thẻ, ô, bảng
)
CHINH_GOC = ('#1E3A5F', '#152C48')     # màu chính GỐC viết thẳng trong bảng kiểu (1.0.35) -> chu_de.MAU_TONG[tông]['chinh' / 'chinh_re']
# Hằng màu dùng trong bảng kiểu lấy CHINH_GOC, KHÔNG lấy TOKEN: TOKEN['chinh'] đã là màu của phương án, _bang_doi_mau không ánh xạ được theo tông (1.0.80: nhãn tối mờ ở tông Tối)
# 1.0.79: màu chính khởi đầu theo phương án Navy mặc định (dat_tong_nen đặt lại khi áp giao diện); bảng kiểu vẫn dựng từ CHINH_GOC
from . import chu_de as _chu_de  # noqa: E402
TOKEN.update(chinh=_chu_de.mau_tong('sang')['chinh'], chinh_re=_chu_de.mau_tong('sang')['chinh_re'])
CHINH_RE = CHINH_GOC[1]  # navy khi rê chuột (nút nền navy, tiêu đề bảng) - cũng là vạch ngăn cột tiêu đề bảng
CAO_NUT_MENU = 32             # nút điều hướng menu trái (0.9.95: 27; 17/10/2026 Hybrid Enterprise Navy: 32 - vùng cuộn có thanh 6 px)
CAO_HANG_GON = 32             # hàng nút "Thu gọn menu" trên đỉnh menu trái (ngoài vùng cuộn, vạch ngăn dưới)
LE_VIEN_MENU = 6              # lề ngang mỗi viên thuốc trong menu trái (rong_mo cộng thêm 2 x lề)
THOI_GIAN_MENU_MS = 160       # thu gọn / mở rộng menu trái trượt mượt (QVariantAnimation, OutCubic)
RONG_MENU_TRAI = 175          # bề rộng menu trái mở (0.9.95: 248 -> 175; thu gọn: 44)
RONG_MENU_GON = 60            # thu gọn (1.0.34: 44 -> 60 - viên thuốc có lề 2 x 6 px)
RONG_MENU_TOI_DA = 248        # lệnh dài ("Bảng tổng hợp kinh phí" ~189 px ở 125%) nới menu tới mức này - không cắt chữ
CAO_DONG_BANG = 30            # chiều cao dòng bảng dữ liệu (17/10/2026 Hybrid Enterprise Navy: 32 -> 30)
CAO_TIEU_DE_BANG = 34         # hàng tiêu đề cột bảng (nền navy, chữ trắng)
MAT_DO = ['chuan']            # 1.0.17: mật độ bảng đang dùng (chu_de.MAT_DO): gon / chuan / thoang - dat_mat_do()
CHINH = CHINH_GOC[0]       # xanh đậm: tiêu đề bảng, nhãn thuộc tính, tab đang chọn


def gan_dinh_dang_nghin(o) -> None:
    """Ô nhập số tiền: tự chấm hàng nghìn khi gõ (230.000), giữ con trỏ theo số chữ số bên trái. Công thức (=...) và chữ lạ giữ nguyên để lap_pa.doc_so báo lỗi."""
    def doi(chu):
        s = chu.strip()
        if not s or not re.fullmatch(r'[\d.]+', s):
            return
        so = s.replace('.', '')
        moi = f'{int(so):,}'.replace(',', '.')
        if moi == chu:
            return
        ben_trai = sum(c.isdigit() for c in chu[:o.cursorPosition()])
        o.setText(moi)
        vt, dem = 0, 0
        while vt < len(moi) and dem < ben_trai:
            dem += moi[vt].isdigit()
            vt += 1
        o.setCursorPosition(vt)
    o.textEdited.connect(doi)


def chu_hien(s: str) -> str:
    """Hiện dấu & trên QLabel / QPushButton / QAction (Qt lấy & làm phím tắt). Idempotent với && đã có."""
    return (s or '').replace('&&', '\x00').replace('&', '&&').replace('\x00', '&&')
# thẻ (QTabBar) cửa sổ con / trang nhúng (1.0.02): chưa chọn nền slate nhạt chữ slate; đang chọn nền trắng chữ navy + vạch trên navy.
# PHÔNG THẺ (cỡ, độ đậm) khai ở mức QTabBar, KHÔNG trong ::tab: Qt5 đo bề rộng thẻ theo phông của thanh thẻ, phông trong ::tab chỉ dùng
# lúc vẽ -> cắt chữ hai đầu (bản Win7); thẻ đang chọn cùng độ đậm
THE_TAB = dict(nen='#F1F5F9', chu='#475569', vien='#E2E8F0', nen_re='#E2E8F0', chu_re='#0F172A')
# nhóm nút: (nền, chữ, nền khi rê chuột)
MAU = {                                            # (màu biểu tượng / nền đặc, chữ, nền rê chuột) theo nhóm nút
    # 1.0.02 (người dùng 17/10/2026, Hybrid Enterprise Navy cho cửa sổ con): bỏ nền / biểu tượng cam, tím, vàng, xanh lá. Chỉ
    # nhóm DAC nền navy đặc; nhóm 'xoa' viền đỏ nhạt chữ đỏ; các nhóm khác nền trắng viền slate, biểu tượng navy / slate / teal
    'luu':    ('#1E3A5F', '#FFFFFF', '#152C48'),   # Lưu, Áp dụng, Thực hiện, Tạo dự án: hành động chính
    'them':   ('#1E3A5F', '#FFFFFF', '#152C48'),   # Thêm…
    'xoa':    ('#B83A3A', '#FFFFFF', '#991B1B'),   # Xóa…
    'sua':    ('#334155', '#FFFFFF', '#1E293B'),   # Gộp, Chuyển, Tách, Bỏ thay đổi
    'in':     ('#1E3A5F', '#FFFFFF', '#152C48'),   # In / Xuất, PDF
    'nhap':   ('#1E3A5F', '#FFFFFF', '#152C48'),   # Nhập, Mở, Nạp, Cập nhật
    'hoso':   ('#1F6F66', '#FFFFFF', '#115E59'),   # Hồ sơ hộ
    'pa':     ('#1E3A5F', '#FFFFFF', '#152C48'),   # Lập phương án
    'tra':    ('#475569', '#FFFFFF', '#334155'),   # Thông tin, Rà soát, Đối chiếu, Gợi ý, Chọn, Hộ trước / sau
    'nhat':   ('#ECEFF1', '#263238', '#CFD8DC'),   # Hủy, Đóng, Giới thiệu
}
DAC = ('luu',)                                     # nhóm nút nền đặc (thao tác chính); các nhóm khác nền trắng viền slate
# nút phụ / nút viền (1.0.02): (nền, chữ, viền, nền rê chuột, viền rê chuột, nền khi bấm); nút xóa: viền đỏ nhạt chữ đỏ
NUT_PHU = ('#FFFFFF', '#0F172A', '#8696AB', '#F1F5F9', '#64748B', '#E2E8F0')  # 1.0.42: viền ≥ 3:1 WCAG 1.4.11
NUT_XOA = ('#FFFFFF', '#B83A3A', '#E35D5D', '#FEF2F2', '#FCA5A5', '#FEE2E2')   # 1.0.51: viền 3,5:1 (trước #FECACA 1,45:1 - WCAG 1.4.11)
NUT_TAT = ('#94A3B8', '#F8FAFC', '#E2E8F0')        # (chữ, nền, viền) nút đang tắt
# (mẫu trên chữ đã bỏ dấu, nhóm) - xét theo thứ tự
LUAT = [
    (r'^xoa|xoa ho|xoa thua|xoa dong|^go ban cap nhat', 'xoa'),
    (r'^(luu|ap dung|save|thuc hien|tao du an|xuat ban ho so)', 'luu'),
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
    LUU = 'success'            # Lưu: 1.0.52 (người dùng 02/11/2026) nền xanh lục MAU_LUU - khác nút chính navy (1.0.02 - 1.0.51: navy)
    NGUY_HIEM = 'danger'       # nền trắng, viền đỏ nhạt, chữ đỏ: Xóa


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


# cửa sổ lập phương án (06/11/2026, gói V3.3 - màu theo người dùng)
QSS_NUT_THEM_HANG = 'QPushButton { background: #1E3A8A; color: #FFFFFF; border: 1px solid #1E3A8A; border-radius: 5px; padding: 2px 10px; font-weight: 700; } QPushButton:hover { background: #1E40AF; } QPushButton:disabled { background: #CBD5E1; border-color: #CBD5E1; }'
QSS_VACH_HANG_NHAP = 'QFrame { background: #CBD5E1; border: 0; }'
QSS_NUT_LUU_DOI = 'QPushButton { background: #16A34A; color: #FFFFFF; border: 1px solid #16A34A; border-radius: 5px; padding: 2px 10px; font-weight: 700; } QPushButton:hover { background: #15803D; }'
QSS_NUT_DA_LUU = 'QPushButton, QPushButton:disabled { background: #F1F5F9; color: #64748B; border: 1px solid #E2E8F0; border-radius: 5px; padding: 2px 10px; }'
# 1.0.93 (người dùng 10/11/2026 chọn hệ nút 3 cấp - thay phân cấp V3.3): nút phiên bản, In / Xuất = cấp PHỤ (nền khung, viền >= 3:1);
# Đóng = cấp BA (phẳng, không đỏ - Đóng không phá hủy dữ liệu). Mỗi thanh chỉ Lưu nền đặc.
QSS_NUT_PHIEN_BAN = 'QPushButton { background: #FFFFFF; color: #0F172A; border: 1px solid #8696AB; border-radius: 5px; padding: 2px 8px; font-weight: 600; } QPushButton:hover { background: #F1F5F9; border-color: #64748B; } QPushButton:disabled { color: #94A3B8; border-color: #E2E8F0; background: #F8FAFC; font-weight: 400; }'
QSS_NUT_IN_THANH = 'QPushButton { background: #FFFFFF; color: #0F172A; border: 1px solid #8696AB; border-radius: 5px; padding: 2px 8px; font-weight: 600; } QPushButton:hover { background: #F1F5F9; border-color: #64748B; }'
QSS_NUT_DONG_THANH = 'QPushButton { background: transparent; color: #334155; border: 1px solid transparent; border-radius: 5px; padding: 2px 10px; } QPushButton:hover { background: #F1F5F9; color: #0F172A; border-color: #E2E8F0; }'
# cột Nguồn giá: (nền, chữ)
MAU_NGUON_GIA = {'dm': ('#DCFCE7', '#166534'), 'td': ('#FEF9C3', '#854D0E'), 'tay': ('#FFEDD5', '#9A3412')}
MAU_CHU_VUNG_CHON = '#1D4ED8'
MAU_DONG_TONG_BANG = '#EFF6FF'     # dòng tổng cố định dưới bảng (Bảng kinh phí chi tiết)
MAU_CHU_PHU_BANG = '#64748B'       # dòng chữ phụ trong ô
# nút chuyển bảng con (thẻ Niêm yết, 06/11/2026 - màu theo người dùng); canh_bao="1": bảng hộ vướng có hộ
QSS_NUT_BANG_CON = ('QPushButton#nut_bang_con { background: #FFFFFF; color: #334155; border: 1px solid #CBD5E1; border-radius: 13px; '
                    'padding: 2px 10px; font-size: 12px; font-weight: 600; }'
                    'QPushButton#nut_bang_con:hover { background: #F1F5F9; }'
                    'QPushButton#nut_bang_con[canh_bao="1"] { color: #B45309; border: 1px solid #F59E0B; font-weight: 700; }'
                    'QPushButton#nut_bang_con:checked { background: #1E3A5F; color: #FFFFFF; border: 1px solid #1E3A5F; font-weight: 700; }'
                    'QPushButton#nut_bang_con[loai="vuong"]:checked { background: #D97706; color: #FFFFFF; border: 1px solid #D97706; }')
MAU_NUT_BANG_CON = {'thuong': '#334155', 'canh': '#B45309', 'chon': '#FFFFFF'}
MAU_LUU = ('#0F6E56', '#0B5340')       # 1.0.52: nút Lưu (KieuNut.LUU): nền, rê chuột - chữ trắng 6,3:1 (WCAG AA)


def _qss_kieu_nut() -> str:
    """QSS các biến thể KieuNut: đặt CUỐI bảng kiểu (cùng độ ưu tiên thì quy tắc sau thắng màu đoán theo chữ / ribbon)."""
    t = TOKEN
    # (nền, chữ, viền, nền rê chuột, (chữ, nền, viền khi tắt)). Hybrid Enterprise Navy (17/10/2026): nút phụ nền trắng viền #CBD5E1
    # chữ #0F172A; nút xóa viền mảnh đỏ nhạt chữ đỏ, tắt thì mờ hẳn (không còn nền cam nhạt gây chú ý khi chưa chọn hộ)
    tat = ('#9AA0A6', '#F1F3F4', t['vach'])
    kieu = {'primary': (t['chinh'], '#FFFFFF', t['chinh'], '#152C48', tat),
            'success': (MAU_LUU[0], '#FFFFFF', MAU_LUU[0], MAU_LUU[1], tat),   # 1.0.52: nút Lưu (KieuNut.LUU) xanh lục
            'danger': (NUT_XOA[0], NUT_XOA[1], NUT_XOA[2], NUT_XOA[3], ('#94A3B8', '#FFFFFF', '#E2E8F0')),
            'secondary': (NUT_PHU[0], NUT_PHU[1], NUT_PHU[2], NUT_PHU[3], ('#94A3B8', '#FFFFFF', '#E2E8F0'))}
    qss = ''
    for k, (nen, chu, vien, re_, (chu_tat, nen_tat, vien_tat)) in kieu.items():
        for loai in ('QPushButton', 'QToolButton'):
            sel = f'{loai}[bien_the="{k}"]'
            qss += f'''
    {sel}, {sel}[ribbon="0"], {sel}[ribbon="1"] {{ color: {chu}; background: {nen}; border: 1px solid {vien}; border-radius: 5px;
        padding: 4px 10px; font-weight: 600; }}
    {sel}:hover, {sel}[ribbon="0"]:hover, {sel}[ribbon="1"]:hover {{ background: {re_}; }}
    {sel}:disabled, {sel}[ribbon="0"]:disabled, {sel}[ribbon="1"]:disabled {{ color: {chu_tat}; background: {nen_tat};
        border-color: {vien_tat}; }}'''
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
        dat_ten_nut_xoa(self)

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
        dat_ten_nut_xoa(o)
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
    return _qss_nut_loai('QPushButton', n, nen, re_)


def _qss_nut_loai(loai: str, n: str, nen: str, re_: str, them: str = '') -> str:
    """QSS một nhóm nút cho một loại nút (QPushButton / QToolButton, them = bộ chọn thêm vd. '[ribbon="1"]'). 1.0.02: nhóm DAC
    nền navy đặc chữ trắng; 'xoa' nền trắng viền đỏ nhạt chữ đỏ; nhóm khác nền trắng viền slate chữ #0F172A, rê chuột #F1F5F9."""
    s = f'{loai}{them}[nhom="{n}"]'
    if n in DAC:
        return f'''{s} {{ color: #FFFFFF; background: {nen}; border: 1px solid {nen}; border-radius: 5px; padding: 4px 10px;
            font-weight: 600; }}
        {s}:hover {{ background: {re_}; border-color: {re_}; }}
        {s}:pressed {{ background: {_tron(nen, 0.12, '#000000')}; }}'''
    nen_, chu, vien, nen_re, vien_re, nen_bam = NUT_XOA if n == 'xoa' else NUT_PHU
    return f'''{s} {{ color: {chu}; background: {nen_}; border: 1px solid {vien}; border-radius: 5px; padding: 4px 10px;
            font-weight: 600; }}
        {s}:hover {{ background: {nen_re}; border-color: {vien_re}; }}
        {s}:pressed {{ background: {nen_bam}; }}'''


def mau_chu_nut(n: str | None) -> str:
    """Màu biểu tượng trên QPushButton theo nhóm (nền đặc: chữ trắng; nền nhạt: màu nhóm)."""
    toi = TONG_NEN[0] == 'toi'                      # 1.0.51: tông Tối - biểu tượng sáng (trước navy trên nền tối 1,18:1)
    if not n or n == 'nhat' or n not in MAU:
        return mau_theo_tong(CHINH_GOC[0], 'chu') if toi else CHINH
    if n in DAC:
        return MAU[n][1]
    if toi:
        m = mau_theo_tong(MAU[n][0], 'chu')
        return m if m.upper() != MAU[n][0].upper() else _tron(MAU[n][0], 0.55, '#FFFFFF')
    return _tron(MAU[n][0], 0.08, '#000000')


# thẻ số liệu màn hình chính (app.CuaSoChinh.THE_SO): màu viền trái + màu số. Kiểu nằm trong QSS chung (trước 0.9.18: mỗi
# thẻ 3 lần setStyleSheet riêng = 18 kiểu cục bộ, phóng to / thu nhỏ phải co giãn lại từng cái)
# 1.0.34: dải màu định danh mỗi thẻ (vạch trái + thanh tiến độ): Tổng hộ xanh Sapphire, đã lập teal, phê duyệt / bàn giao emerald,
# chi trả xanh trời, Tổng kinh phí hổ phách
MAU_THE_SO = {'so_ho': '#2563EB', 'da_pa': '#0D9488', 'da_pd': '#059669', 'da_ct': '#0284C7', 'da_bg': '#059669', 'tong': '#D97706'}
# 1.0.33: nhóm ngữ nghĩa của thẻ KPI (property nhom_kpi) - thắng màu theo thẻ: tiền / đã xong / đang chờ; thẻ không nhóm giữ MAU_THE_SO
MAU_NHOM_KPI = {'tien': '#D97706', 'xong': '#059669', 'cho': '#0284C7'}
NHOM_KPI_THE = {'tong': 'tien', 'da_bg': 'xong'}
# QSS thẻ Card màn hình chào (ARCH-PABT-2026-V5; 0.9.79: thẻ 210 x 135, bo 12px, mỗi thẻ một màu, mô tả nằm TRONG thẻ).
# loại -> (nền, viền, nền khi rê chuột, viền khi rê chuột, màu biểu tượng). Qt làm tròn viền 1,5px lên 2px: ghi 2px cho đúng thực tế.
KICH_THE_CHAO = (210, 135)
CO_ICON_THE_CHAO = 38
# 1.0.34 (người dùng 29/10/2026): mỗi thẻ một màu điểm nhấn - dải 4 px cạnh trên, nền trắng chuyển sắc xuống màu nhạt, huy hiệu biểu tượng
# 44 px nền nhạt; rê chuột viền sáng màu điểm nhấn. (nền trên, viền, nền nhạt dưới / rê chuột, màu điểm nhấn, màu biểu tượng)
MAU_THE_CHAO = {
    'moi': ('#FFFFFF', '#E2E8F0', '#EFF6FF', '#2563EB', '#2563EB'),        # Sapphire Blue - Dự án mới
    'mo': ('#FFFFFF', '#E2E8F0', '#ECFDF5', '#059669', '#059669'),         # Emerald - Mở dự án
    'excel': ('#FFFFFF', '#E2E8F0', '#FFFBEB', '#D97706', '#D97706'),      # Amber Gold - Nhập Excel
    'phap_ly': ('#FFFFFF', '#E2E8F0', '#F5F3FF', '#7C3AED', '#7C3AED'),    # Royal Violet - tiếp nhận hồ sơ pháp lý (1.0.04)
}
CO_HUY_HIEU_THE_CHAO = 44            # huy hiệu biểu tượng (ô bo 12 px nền nhạt) chứa biểu tượng 26 px
CO_ICON_TRONG_HUY_HIEU = 26
QSS_THE_CHAO = (
    f'QFrame[vai="the_chao"] {{ background: {TOKEN["khung"]}; border: 1px solid #E2E8F0; border-radius: 12px; }}'
    + ''.join(
        f'QFrame[vai="the_chao"][loai="{k}"] {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {nen}, stop:1 {nhat}); '
        f'border: 1px solid {vien}; border-top: 4px solid {nhan}; border-radius: 12px; }}'
        f'QFrame[vai="the_chao"][loai="{k}"][hover="1"] {{ background: {nhat}; border: 1px solid {nhan}; border-top: 4px solid {nhan}; }}'
        for k, (nen, vien, nhat, nhan, _icon) in MAU_THE_CHAO.items())
    # nút lệnh trong thẻ: trong suốt (thẻ là khối nhìn thấy duy nhất); bộ chọn #id thắng mọi bộ chọn thuộc tính của nút ribbon
    + 'QToolButton#the_chao_nut, QToolButton#the_chao_nut:hover, QToolButton#the_chao_nut:pressed, QToolButton#the_chao_nut:disabled '
      '{ background: transparent; border: 0; padding: 0; }'
      'QToolButton#the_chao_nut { color: #0F172A; font-family: "Segoe UI"; font-size: 14.5pt; font-weight: 700; }'
      'QToolButton#the_chao_nut:disabled { color: #94A3B8; }'
      'QLabel[vai="phim_the_chao"] { background: rgba(15, 23, 42, 0.06); color: #475569; border: 1px solid #E2E8F0; '
      'border-radius: 8px; padding: 0 6px; font-size: 11px; font-weight: 700; }'
)


def _qss_menu_trai(ten: str | None = None) -> str:
    """Menu trái theo tông (1.0.35, chu_de.MAU_TONG[...]['menu']): tông sáng (PA1 mặc định, Ấm, Xanh ngọc…) nền sáng liền mạch với vùng
    làm việc, tông Titan / Tối nền tối. Mỗi lệnh một viên bo 8 px, lệnh đang chọn nền nhấn + vạch trái 4 px, tiêu đề nhóm chữ in hoa.
    Đặt SAU khi đổi màu theo tông (_qss_day_du): màu ở đây đã là màu của tông. Cỡ chữ ghi bằng px (phong_to nhân px)."""
    from . import chu_de
    m = chu_de.mau_tong(TONG_NEN[0] if ten is None else ten)['menu']
    return f'''
    QFrame[vai="menu_trai"] {{ background: {m['nen']}; border: 0; border-right: 1px solid {m['vien']}; border-radius: 0; }}
    QFrame#hang_gon_menu {{ background: transparent; border: 0; border-bottom: 1px solid {m['vien']}; }}
    QToolButton#nut_thu_gon {{ background: transparent; border: 1px solid transparent; border-radius: 8px; padding: 2px 8px;
        text-align: left; color: {m['icon']}; font-size: 12px; font-weight: 600; }}
    QToolButton#nut_thu_gon:hover {{ background: {m['re']}; color: {m['chon_chu'] if m['toi'] else m['nhom']}; }}
    QScrollArea#cuon_menu, QScrollArea#cuon_menu > QWidget {{ background: transparent; border: 0; }}
    QFrame[vai="menu_trai"] QScrollBar:vertical {{ background: transparent; width: 6px; margin: 2px 0; }}
    QFrame[vai="menu_trai"] QScrollBar::handle:vertical {{ background: {m['cuon']}; border-radius: 3px; min-height: 24px; }}
    QFrame#vach_menu {{ color: {m['vien']}; margin: 2px 6px; }}
    QToolButton[menu="1"] {{ background: transparent; border: 1px solid transparent; border-radius: 8px; margin: 0 {LE_VIEN_MENU}px;
        padding: 2px 6px 2px 10px; text-align: left; font-weight: 500; font-size: 13px; color: {m['chu']}; }}
    QToolButton[menu="1"]:focus {{ outline: none; border: 2px solid {m['vach_chon']}; }}
    QToolButton[menu="1"]:hover {{ background: {m['re']}; color: {m['chon_chu']}; }}
    QToolButton[menu="1"]:pressed {{ background: {m['chon_nen']}; }}
    QToolButton[menu="1"]:disabled {{ color: {m['tat']}; background: transparent; border-color: transparent; }}
    QToolButton[menu="1"]:checked {{ background: {m['chon_nen']}; color: {m['chon_chu']}; font-weight: 700; border: 0;
        border-left: 4px solid {m['vach_chon']}; padding-left: 7px; }}
    QLabel[vai="nhom_menu"] {{ color: {m['nhom']}; font-size: 12px; font-weight: 700; letter-spacing: 0; background: transparent;
        border: 0; border-radius: 4px; margin: 12px {LE_VIEN_MENU}px 4px {LE_VIEN_MENU}px; padding: 3px 4px; }}
    QLabel[vai="nhom_menu"]:hover {{ background: {m['re']}; }}
    QLabel[vai="nhom_menu"][dong="1"] {{ color: {m['nhom']}; font-weight: 600; }}'''


_O_TICH_TOI = {}        # cờ: đã vẽ bộ ảnh ô tích (thư mục) - vẽ một lần mỗi tiến trình


def _anh_o_tich_toi():
    """Bộ ảnh ô tích / nút chọn cho tông Tối (QSS ::indicator cần ảnh: kiểu gốc của Windows vẽ ô tích không thấy khung trên nền tối). Vẽ bằng
    QPainter ra thư mục máy, trả thư mục (hoặc None khi chưa có QGuiApplication / không ghi được)."""
    if 'thu_muc' in _O_TICH_TOI:
        return _O_TICH_TOI['thu_muc']
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QGuiApplication, QPen, QPixmap
    if QGuiApplication.instance() is None:
        return None
    _O_TICH_TOI['thu_muc'] = None
    try:
        from . import dia_phuong
        d = dia_phuong.thu_muc_may() / 'bieu_tuong_o_tich'
        d.mkdir(parents=True, exist_ok=True)
        c = 18
        for ten, (nen, vien, dau) in {'tt': ('#0F172A', '#94A3B8', None), 'tt_chon': ('#2563EB', '#93C5FD', '#FFFFFF'),
                                      'tt_tat': ('#162033', '#475569', None), 'tt_chon_tat': ('#334155', '#64748B', '#94A3B8')}.items():
            for hinh in ('vuong', 'tron'):
                pm = QPixmap(c, c)
                pm.fill(Qt.GlobalColor.transparent)
                p = QPainter(pm)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                p.setPen(QPen(QColor(vien), 1.5))
                p.setBrush(QColor(nen))
                r = QRectF(1.5, 1.5, c - 3, c - 3)
                if hinh == 'vuong':
                    p.drawRoundedRect(r, 3, 3)
                    if dau:
                        p.setPen(QPen(QColor(dau), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                        p.drawPolyline([QPointF(4.8, 9.4), QPointF(7.8, 12.4), QPointF(13.2, 5.8)])
                else:
                    p.drawEllipse(r)
                    if dau:
                        p.setPen(Qt.PenStyle.NoPen)
                        p.setBrush(QColor(dau))
                        p.drawEllipse(QPointF(c / 2, c / 2), 3.6, 3.6)
                p.end()
                pm.save(str(d / f'{hinh}_{ten}.png'))
        _O_TICH_TOI['thu_muc'] = d.as_posix()
    except Exception:  # noqa: BLE001 - không vẽ được ảnh thì giữ kiểu gốc
        _O_TICH_TOI['thu_muc'] = None
    return _O_TICH_TOI['thu_muc']


def _qss_o_tich_toi() -> str:
    """QSS ô tích / nút chọn tông Tối (khung sáng, ô chọn nền xanh + dấu ✓ trắng); rỗng nếu không vẽ được ảnh."""
    d = _anh_o_tich_toi()
    if not d:
        return ''
    kq = ''
    for lop, hinh in (('QCheckBox', 'vuong'), ('QRadioButton', 'tron')):
        kq += (f'{lop}::indicator {{ width: 18px; height: 18px; image: url({d}/{hinh}_tt.png); }}'
               f'{lop}::indicator:checked {{ image: url({d}/{hinh}_tt_chon.png); }}'
               f'{lop}::indicator:disabled {{ image: url({d}/{hinh}_tt_tat.png); }}'
               f'{lop}::indicator:checked:disabled {{ image: url({d}/{hinh}_tt_chon_tat.png); }}')
    return kq


def mau_menu() -> dict:
    """Màu menu trái của tông đang dùng (biểu tượng lệnh, lệnh tắt…)."""
    from . import chu_de
    return chu_de.mau_tong(TONG_NEN[0])['menu']


def _qss_the_so() -> str:
    """Thẻ KPI cửa sổ chính + hàng công cụ / dải cộng danh sách hộ (Hybrid Enterprise Navy, 17/10/2026)."""
    c = TOKEN['chinh']
    return '''
    QWidget[vai="the_so"] { background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 3px solid #1E3A5F; border-radius: 6px; }
    QWidget[vai="the_so"]:hover { background: #F8FAFC; border-color: #CBD5E1; }
    QWidget[vai="the_so"] QLabel { background: transparent; border: 0; }
    QLabel[vai="so_the"] { font-family: "Segoe UI"; font-size: 16px; font-weight: 700; color: #0F172A; }
    QLabel[vai="nhan_the"] { color: #475569; font-size: 12px; font-weight: 600; }
    QLabel[vai="phu_the"] { color: #64748B; font-size: 11px; font-weight: 700; }
    QLabel[vai="huy_hieu_the"] { background: #F1F5F9; color: #5B6B82; border-radius: 4px; padding: 0 6px; font-size: 11px;
        font-weight: 700; }
    QWidget[vai="the_so"] QLabel[vai="huy_hieu_the"][co="1"] { background: #DBEAFE; color: #2F5DB5; }
    QWidget[vai="the_so"] QLabel[vai="huy_hieu_the"][co="ha"] { background: #FEF3C7; color: #7C4A12; }
    QLabel[vai="vach_the"] { background: #E2E8F0; }
    QWidget[vai="the_so"] QLabel[vai="vach_the"] { background: #E2E8F0; }
    QLabel[vai="dia_chinh_the"] { font-size: 11px; font-weight: 700; color: #1E293B; margin: 0; padding: 0; }
    QLabel[vai="dt_the"] { font-size: 11px; font-weight: 600; color: #334155; margin: 0; padding: 0; }
    QLabel#lb_bo_dem_excel { background: #F0FDF4; border: 1px solid #2F7D54; color: #276348; font-weight: 700;
        border-radius: 4px; padding: 2px 10px; }
    QLabel#lb_bo_dem_excel:hover { background: #DCFCE7; }
    QProgressBar[vai="thanh_tien_do"] { background: #E2E8F0; border: 0; border-radius: 2px; max-height: 5px; min-height: 5px; }
    QProgressBar[vai="thanh_tien_do"]::chunk { border-radius: 2px; background: #2563EB; }''' + ''.join(
        f'''
    QProgressBar[vai="thanh_tien_do"][mau="{m}"]::chunk {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {m},
        stop:1 {_sang_hon(m)}); }}''' for m in sorted(set(MAU_THE_SO.values()) | set(MAU_NHOM_KPI.values()) | set(MAU_KPI_TONG_QUAN))) + ''.join(
        f'''
    QWidget[vai="the_so"][the="{k}"] {{ border-left-color: {m}; }}''' for k, m in MAU_THE_SO.items()) + ''.join(
        f'''
    QWidget[vai="the_so"][nhom_kpi="{k}"] {{ border-left-color: {m}; }}''' for k, m in MAU_NHOM_KPI.items()) + f'''
    QWidget[vai="the_so"][dang_loc="1"] {{ background: #F0F6FF; border: 1px solid {c}; border-left: 4px solid {c}; }}
    QLabel[vai="huy_hieu_loc"] {{ background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 5px; padding: 0 10px;
        color: #334155; font-size: 12px; }}
    QLabel[vai="huy_hieu_loc"]:hover {{ background: #EFF6FF; border-color: {c}; }}
    QComboBox[loc_ds="1"] {{ background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 5px; padding: 0 8px; }}
    QLineEdit[loc_ds="1"] {{ background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 5px; padding: 0 6px; }}
    QComboBox[loc_ds="1"]:hover, QLineEdit[loc_ds="1"]:hover {{ border-color: #94A3B8; }}
    QComboBox[loc_ds="1"]:focus {{ border: 2px solid {TOKEN['nhan']}; padding: 0 7px; }}
    QLineEdit[loc_ds="1"]:focus {{ border: 2px solid {TOKEN['nhan']}; padding: 0 5px; }}
    QFrame#dai_cong_ds {{ background: #F1F5F9; border: 1px solid #DCE3EA; border-top: 2px solid #CBD5E1;
        border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; }}
    QFrame#dai_cong_ds QLabel {{ background: transparent; border: 0; color: #0F172A; font-weight: 700; }}
    QFrame#dai_cong_ds QLabel[vai="vach_cong"] {{ color: #94A3B8; font-weight: 400; }}
    QFrame#dai_cong_ds QLabel[vai="o_cong_tong"] {{ color: {c}; font-weight: 800; }}'''


# ô của hàng nhập nhanh (hang_nhap_nhanh.HangNhapNhanh, property hang_nhap="1"): viền slate, đang gõ vòng focus 2 px xanh hoàng gia
# (padding bớt 1 px để chữ không nhảy); thắng kiểu ô lớn QLineEdit[nhap="1"] (bộ chọn con cháu có thêm tên lớp)
QSS_HANG_NHAP = '''
    QWidget[hang_nhap="1"] QLineEdit, QWidget[hang_nhap="1"] QComboBox { background: #FFFFFF; border: 1px solid #CBD5E1;
        border-radius: 5px; padding: 0 8px; min-height: 0; }
    QWidget[hang_nhap="1"] QLineEdit:hover, QWidget[hang_nhap="1"] QComboBox:hover { border-color: #94A3B8; }
    QWidget[hang_nhap="1"] QLineEdit:focus, QWidget[hang_nhap="1"] QComboBox:focus { border: 2px solid #2563EB;
        padding: 0 7px; background: #FFFFFF; }'''
# thẻ kiểu gạch chân (cửa sổ lập phương án - ảnh mẫu 17/10/2026): QTabBar có property vai="gach_chan". Ở QSS chung: kiểu cục bộ trên
# QTabWidget làm chậm (tính lại kiểu cả cây con). Phông (cỡ, độ đậm) khai ở MỨC QTabBar, không ở ::tab: Qt5 đo bề rộng thẻ theo phông
# của chính thanh thẻ, phông khai trong ::tab chỉ dùng lúc vẽ -> chữ rộng hơn ô, cắt hai đầu (bản Win7, 18/10/2026). Thẻ đang chọn
# cùng độ đậm (phân biệt bằng màu xanh hoàng gia + vạch dưới 3 px, nền trắng - 22/10/2026), px nguyên. Thẻ chưa chọn giữ vạch
# trong suốt cùng bề dày để thẻ không đổi cao khi chọn
QSS_THE_GACH_CHAN = '''
    QTabBar[vai="gach_chan"] { font-weight: 600; font-size: 13px; }
    QTabBar[vai="gach_chan"]::tab { background: transparent; color: #475569; border: 1px solid transparent;
        border-bottom: 3px solid transparent; padding: 5px 14px 4px 14px; margin-right: 2px; }
    QTabBar[vai="gach_chan"]::tab:hover:!selected { background: #F1F5F9; color: #0F172A; }
    QTabBar[vai="gach_chan"]::tab:selected { background: #FFFFFF; color: #2563EB;
        border: 1px solid transparent; border-bottom: 3px solid #2563EB; }'''
# khung tùy chọn của Xuất hồ sơ & Bản in (man_hinh.HopIn): thẻ trắng viền slate. Ở QSS chung theo objectName - setStyleSheet trên khung
# chứa bắt Qt tính lại kiểu cả cây con (chậm; đo 1.0.02 ở cửa sổ lập phương án)
# thẻ thông tin chủ hộ + dải cộng bảng thửa (man_hinh_ho_so.KhungHoSo, 1.0.03)
# 20/10/2026: khối I #khung_chu_ho (lưới 3 cột), thẻ nhỏ [the_nho], ô tên / CCCD / pháp lý, dải tổng hợp địa chính #thanh_tom_tat_thua
QSS_HO_SO_HO = '''
    QFrame#khung_chu_ho, QFrame#the_chu_ho { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; }
    QLineEdit#o_ten { font-weight: 700; color: #1E3A5F; }
    QLineEdit#o_cccd { font-family: "Segoe UI", Tahoma; letter-spacing: 1px; }
    QLineEdit#o_cccd[hop_le="0"] { border: 1px solid #C94545; background: #FEF2F2; }
    QLineEdit#o_phap_ly { color: #2F7D54; font-weight: 600; }
    QLabel[the_nho] { border-radius: 9px; padding: 2px 9px; font-size: 11px; font-weight: 600; }
    QLabel[the_nho="vang"] { background: #FEF3C7; color: #7C4A12; border: 1px solid #FDE68A; }
    QLabel[the_nho="xanh"] { background: #DCFCE7; color: #276348; border: 1px solid #BBF7D0; }
    QLabel[the_nho="do"] { background: #FEE2E2; color: #B83A3A; border: 1px solid #FECACA; }
    QLabel[the_nho="lam"] { background: #EFF6FF; color: #2F5DB5; border: 1px solid #BFDBFE; }
    QLabel[the_nho="xam"] { background: #F1F5F9; color: #475569; border: 1px solid #E2E8F0; }
    QLabel[the_nho="loai"] { border: 1px solid #E2E8F0; }
    QFrame#thanh_tom_tat_thua { background: #F1F5F9; border: 1px solid #E2E8F0; border-top: 1px solid #CBD5E1;
        border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; }
    QLabel#tom_tat_thua { background: transparent; border: none; color: #0F172A; }'''
# cửa sổ lập phương án (20/10/2026, ảnh mẫu): dải định danh hộ #dai_dinh_danh (38 px, nền #F1F5F9), tổng kinh phí khung vàng,
# dải chân bảng mục #dai_cong_muc
QSS_LAP_PA_DAI = '''
    QFrame#dai_dinh_danh { background: #F1F5F9; border: 0; border-bottom: 1px solid #E2E8F0; }
    QLabel[vai_dd="nhan"] { color: #64748B; }
    QLabel[vai_dd="ten"] { color: #1E3A5F; font-weight: 700; }
    QLabel[vai_dd="cccd"] { font-family: "Segoe UI", Tahoma; font-weight: 600; color: #0F172A; }
    QLabel[vai_dd="dia_chi"] { color: #0F172A; font-weight: 600; }
    QLabel[vai_dd="dot"] { color: #1F76A6; font-weight: 700; }
    QLabel#tong_dinh_danh { background: #FEF3C7; border: 1px solid #E5A93A; border-radius: 5px; padding: 2px 10px;
        color: #7C4A12; font-family: "Segoe UI", Tahoma; font-weight: 700; }
    QFrame#dai_cong_muc { background: #F0FDF4; border: 1px solid #BBF7D0; border-top: 0;
        border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; }
    QLabel#dem_muc { color: #276348; }
    QLabel#cong_muc { color: #1E3A5F; font-weight: 700; }'''
# bảng tổng hợp kinh phí (20/10/2026): khung an toàn nguồn vốn cạnh cơ cấu, dòng chân "Lần tính toán gần nhất"
QSS_TONG_HOP_KP = '''
    QFrame#khung_an_toan_von { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; }
    QLabel#tom_tat_an_toan_von { background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 5px; padding: 8px 10px;
        color: #14532D; }
    QLabel#chan_tong_hop { color: #475569; padding: 2px 4px; }
    QLabel#quy_tac_che_do { background: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 5px; padding: 6px 10px; color: #075985; }
    QFrame#khung_tai_lieu { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 5px; }
    QTabBar#the_che_do_in::tab { padding: 6px 12px; }
    QFrame#khung_chi_so_cd { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; }
    QFrame#khung_hop_den { background: #FFFBEB; border: 1px solid #FCD34D; border-radius: 6px; }
    QLabel#tieu_de_hop_den { color: #9A5A12; font-weight: 700; }
    QLabel#mo_ta_hop_den { color: #78350F; }
    QPushButton#nut_goi_chan_doan { background: #1F76A6; color: #FFFFFF; border: 1px solid #1A5C85; font-weight: 700; }
    QPushButton#nut_goi_chan_doan:hover { background: #1A5C85; }
    QFrame#khung_so_vd { background: #FFFFFF; border: 1px solid #1E3A5F; border-radius: 6px; }
    QFrame#dau_so_vd { background: #EAF1F8; border: 0; border-left: 4px solid #1E3A5F; border-bottom: 1px solid #CBD9E8;
        border-top-left-radius: 5px; border-top-right-radius: 5px; }
    QLabel#tieu_de_so_vd { color: #1E3A5E; font-weight: 700; background: transparent; }
    QLabel#the_ho_vd { background: #E5A93A; color: #0F172A; font-weight: 700; border-radius: 4px; padding: 1px 8px; }
    QLabel#thong_tin_ho_vd { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 5px; padding: 6px 8px; color: #0F172A; }
    QLabel#ket_luan_vd { background: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 5px; padding: 6px 8px; color: #075985; }
    QLabel#ket_luan_vd[du="1"] { background: #FEF2F2; border: 1px solid #FCA5A5; color: #991B1B; }
    QFrame#chan_so_vd { background: #F8FAFC; border: 0; border-top: 1px solid #E2E8F0; }'''


def dat_the_nho(lb, loai: str) -> None:
    """Đổi màu thẻ nhỏ QLabel[the_nho] (vang / xanh / do / lam / xam - QSS_HO_SO_HO) và vẽ lại kiểu."""
    if lb.property('the_nho') != loai:
        lb.setProperty('the_nho', loai)
        lb.style().unpolish(lb)
        lb.style().polish(lb)


QSS_THE_TUY_CHON_IN = '''
    QWidget#the_tuy_chon_in { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; }'''


_CAO_DONG_MAC_DINH = {26, 30, 32}                          # (36 = bảng mục của CuaSoLapPA tự đặt - không đụng)                    # cỡ dòng mặc định của Qt / của các mật độ: bảng chưa chỉnh riêng thì theo mật độ


def dat_mat_do(ten: str, ap_lai: bool = True, luu: bool = False) -> str:
    """Đặt mật độ bảng (chu_de.MAT_DO: gon / chuan / thoang): cao dòng + hàng tiêu đề; ap_lai -> áp ngay cho bảng đang mở (bảng đã chỉnh
    cỡ dòng riêng - chữ nhiều dòng, bảng nhập phương án - giữ nguyên) và dựng lại bảng kiểu. luu: nhớ cho lần mở sau."""
    global CAO_DONG_BANG, CAO_TIEU_DE_BANG
    from . import chu_de
    ten = ten if ten in chu_de.MAT_DO else chu_de.MAC_DINH_MAT_DO
    cu = CAO_DONG_BANG
    MAT_DO[0] = ten
    CAO_DONG_BANG, CAO_TIEU_DE_BANG = chu_de.cao_dong(ten), chu_de.cao_tieu_de(ten)
    if luu:
        chu_de.ghi(cai_dat_nho(), mat_do=ten)
    app = QApplication.instance()
    if ap_lai and app is not None:
        for w in app.allWidgets():
            if isinstance(w, QAbstractItemView) and hasattr(w, 'verticalHeader'):
                vh = w.verticalHeader()
                if vh.defaultSectionSize() in (cu, CAO_DONG_BANG):
                    vh.setMinimumSectionSize(CAO_DONG_BANG - 4)
                    vh.setDefaultSectionSize(CAO_DONG_BANG)
        if not getattr(app, '_tuong_phan_cao', False):
            app.setStyleSheet(_co_gian(_qss_day_du(), TY_LE[0]) if TY_LE[0] != 1 else _qss_day_du())
    return ten


def _qss_tuong_phan_cao() -> str:
    """Windows tương phản cao: KHÔNG đặt màu (bảng màu hệ thống), chỉ kích thước / khoảng đệm / phông đậm tiêu đề để bố cục giữ nguyên."""
    return f'''
    QPushButton, QToolButton {{ padding: 4px 10px; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{ padding: 4px 8px; min-height: 20px; }}
    QHeaderView::section {{ padding: 4px 8px; font-weight: 600; min-height: {CAO_TIEU_DE_BANG - 10}px; }}
    QTabBar::tab {{ padding: 5px 14px; }}
    QMenu::item {{ padding: 5px 24px 5px 12px; }}
    '''


TONG_NEN = ['sang']            # 1.0.33: tông nền bề mặt đang dùng (chu_de.TONG_NEN) - dat_tong_nen()
_KHOA_MAU_NEN = ('nen', 'khung', 'vach', 'chu', 'chu_phu')
# màu GỐC mà bảng kiểu chung viết thẳng (#F8FAFC, #E2E8F0…): bảng kiểu dựng bằng màu này rồi đổi theo tông (ap_tong_nen). Từ 1.0.34
# tông mặc định 'sang' (Sáng Sapphire) KHÁC màu gốc: nền #F1F5F9, viền #CBD5E1 - mở phần mềm là thấy giao diện mới
_TOKEN_GOC = dict(nen='#F8FAFC', khung='#FFFFFF', vach='#E2E8F0', chu='#0F172A', chu_phu='#475569')
# 1.0.79: màu GIỮ CHỖ trong bảng kiểu chung, chỉ dùng ở các khai báo này; _bang_doi_mau thay theo tông + phương án Navy
TD_GOC = dict(nen='#1E3A5D', chu='#FFFFFE', vach='#1E3A5C', day='#1E3A5B', re='#1E3A5A')     # tiêu đề bảng ngang
DAU_GOC = dict(nen='#EAF1F8', chu='#1E3A5E', vien='#CBD9E8')                                  # đầu khung Sổ nhật ký vận động
TOKEN_NHAN_GOC = '#2563EB'
_NHO_BANG_DOI_MAU: dict = {}                                                                   # (tông, phương án) -> bảng đổi màu; xem _bang_doi_mau
_RE_KHAI_BAO = re.compile(r'([A-Za-z-]+)(\s*:\s*)([^;{}]+)')
_RE_MAU_HEX = re.compile(r'#[0-9A-Fa-f]{6}\b')
# tông Tối chuyên gia (Dark Studio): ngoài 5 màu tông, các màu sáng viết thẳng khác trong bảng kiểu cũng đổi sang màu tối tương ứng
# (nền nhạt, viền, chữ đậm, chữ navy trên nền trắng) - màu nền nút xanh / chữ trắng / huy hiệu ngữ nghĩa (vàng, đỏ nhạt) giữ nguyên
TOI_NEN = {'#F1F3F4': '#1E293B', '#CBD5E1': '#334155', '#FFF1F2': '#3A1414', '#ECFCCB': '#1F2E0F', '#EEF3FA': '#24324A', '#E5A93A': '#854D0E', '#FFEBEE': '#3A1414', '#F4F6F8': '#162033', '#FFF6D6': '#3B2F12', '#FDEBDD': '#3A2414', '#F1F4F7': '#162033', '#F0FDF4': '#0F2A1F', '#ECFDF5': '#0F2A1F', '#DCFCE7': '#14532D', '#FFFBEB': '#2A2210', '#FEF3C7': '#3B2F12',
           '#FEF2F2': '#3A1414', '#FEE2E2': '#4C1D1D', '#F0FDFA': '#0F2A28', '#FFFDE7': '#2A2210', '#F5F3FF': '#2A1F4A',
           '#F1F5F9': '#162033', '#EEF2F7': '#24324A', '#E2E8F0': '#2A3A52', '#EFF6FF': '#1E3A5F', '#F0F6FF': '#1E3A5F',
            '#DBEAFE': '#1E40AF', '#F0F9FF': '#0C2A3F', '#EEF5FC': '#24324A', '#DCEBFA': '#1E40AF', '#FAFBFC': '#0F172A', '#F8F9FA': '#0B1120',
           '#F8F8F8': '#0B1120', '#F3F6FA': '#0B1120', '#FFF2CC': '#2A2210',
           '#EAF6EC': '#062E1E', '#FFF4DB': '#332407', '#FCEDEB': '#3B1219',          # 1.0.51: nền dat_trang_thai
           # P1: nền ô trạng thái của các bảng (xanh = khớp / đã xong, cam đỏ = lệch, vàng = cần xem, xám = chỉ đọc) - mau_o_theo_tong
           '#E2EFDA': '#14331F', '#F8CBAD': '#4A2414', '#F2F2F2': '#1E293B', '#DDEBF7': '#1E3A5F', '#E8F5E9': '#14331F',
           '#E3F2FD': '#1E3A5F', '#FCE4D6': '#3A2414', '#EEF1F4': '#1E293B', '#EEF6FF': '#1E3A5F', '#FFF3C4': '#3B2F12',
           '#DFF0D8': '#14331F', '#FFF4D6': '#3B2F12', '#FFF8E1': '#2A2210', '#F5F5F5': '#1E293B', '#F2F4F7': '#1E293B'}
TOI_VIEN = {'#FECDD3': '#7F1D1D', '#BBF7D0': '#166534', '#86EFAC': '#15803D', '#A7F3D0': '#047857', '#FDE68A': '#854D0E', '#FECACA': '#7F1D1D',
            '#99F6E4': '#0F766E', '#BAE6FD': '#075985', '#CBD5E1': '#475569', '#DCE3EA': '#334155', '#94A3B8': '#64748B', '#BFDBFE': '#1E40AF',
            '#8696AB': '#64748B', '#E5E5E5': '#334155', '#E35D5D': '#F87171',
            '#CDE8D2': '#166534', '#F1D9A0': '#854D0E', '#F3CFCA': '#7F1D1D'}
TOI_CHU = {'#0F3A63': '#93C5FD', '#991B1B': '#FCA5A5', '#1F76A6': '#7DD3FC', '#4A6785': '#A5B4C8', '#1F4E79': '#93C5FD',
           '#4A5B6C': '#CBD5E1', '#2F7A4F': '#86EFAC', '#7A1B12': '#FCA5A5', '#1E5E2F': '#86EFAC', '#5B6B7A': '#CBD5E1',
           '#08345F': '#BFDBFE', '#14532D': '#86EFAC', '#075985': '#7DD3FC', '#4A5866': '#CBD5E1', '#276348': '#86EFAC', '#2F7D54': '#86EFAC', '#065F46': '#6EE7B7', '#047857': '#6EE7B7', '#7C4A12': '#FCD34D',
           '#9A5A12': '#FCD34D', '#78350F': '#FCD34D', '#B83A3A': '#FCA5A5', '#1F6F66': '#5EEAD4', '#2F5DB5': '#93C5FD',
           '#1A5C85': '#7DD3FC', '#0284C7': '#7DD3FC', '#1E293B': '#E2E8F0', '#334155': '#CBD5E1', '#64748B': '#94A3B8', '#1E3A5F': '#93C5FD', '#2563EB': '#60A5FA',
           '#3B3B3B': '#E2E8F0', '#8B8B8B': '#94A3B8',
           '#152C48': '#BFDBFE', '#202124': '#F1F5F9', '#1A1A1A': '#F1F5F9', '#0B2E4F': '#E2E8F0', '#5B6B82': '#A5B4C8',
           '#8A5A00': '#FCD34D', '#1F4E78': '#93C5FD', '#D97706': '#FCD34D',
           # 1.0.51: chữ dat_trang_thai (tin 1,57:1 trên nền tối trước đây), đỏ / cam đậm
           '#0C4A6E': '#7DD3FC', '#1E6B34': '#86EFAC', '#7A4B00': '#FCD34D', '#A12A1F': '#FCA5A5', '#7C2D12': '#FDBA74',
           '#7F1D1D': '#FCA5A5',
           # 1.0.80: chữ bảng / thanh trạng thái viết màu tối chưa có trong bảng đổi
           '#1B5E20': '#86EFAC', '#B3261E': '#FCA5A5', '#5F6368': '#CBD5E1', '#107C41': '#86EFAC', '#BE123C': '#FDA4AF', '#008000': '#86EFAC', '#800000': '#FCA5A5',
           '#1F5FA0': '#93C5FD', '#3F6212': '#BEF264',
           '#B8433A': '#FCA5A5', '#2E7D32': '#86EFAC', '#1F5FA0': '#93C5FD',      # P1: chữ ô bảng (mau_o_theo_tong 'chu')
           # 1.0.93: chữ tối chưa có trong bảng đổi (Tối 1,9 - 2,9:1 trước đây)
           '#1D4ED8': '#93C5FD', '#B71C1C': '#FCA5A5', '#B45309': '#FCD34D', '#B91C1C': '#FCA5A5', '#166534': '#86EFAC',
           '#475569': '#CBD5E1', '#0F6E56': '#6EE7B7'}


def _bang_doi_mau(ten: str) -> dict:
    """{'nen': {màu gốc: màu mới}, 'vien': {…}, 'chu': {…}} của một tông (màu gốc của bảng kiểu -> màu tông). Nền đổi cả nền cửa sổ
    lẫn nền khung; viền đổi vạch ngăn; chữ chỉ đổi chữ chính / chữ phụ - chữ trắng trên nút xanh giữ nguyên. Tông 'toi' thêm
    TOI_NEN / TOI_VIEN / TOI_CHU."""
    from . import chu_de
    # 1.0.79: nhớ theo (tông, phương án): mau_theo_tong gọi cho từng ô khi vẽ bảng, không dựng lại từ điển mỗi lần. KHÔNG sửa bảng trả về
    khoa = (ten, chu_de.phuong_an_hien())
    kq = _NHO_BANG_DOI_MAU.get(khoa)
    if kq is not None:
        return kq
    _, nen, khung, vach, chu, chu_phu = chu_de.TONG_NEN.get(ten, chu_de.TONG_NEN[chu_de.MAC_DINH_TONG_NEN])
    g = _TOKEN_GOC
    loc = lambda d: {k.upper(): v.upper() for k, v in d.items() if k.upper() != v.upper()}   # noqa: E731
    them = ten == 'toi'
    mt = chu_de.mau_tong(ten)
    pa = chu_de.mau_phuong_an(ten)
    chinh = {CHINH_GOC[0]: mt['chinh'], CHINH_GOC[1]: mt['chinh_re']}       # mọi thuộc tính; riêng từng loại (nền / viền / chữ) thắng
    # tiêu đề bảng, đầu khung: tông không theo phương án giữ cách cũ (nền màu chính, chữ trắng, vạch màu chính đậm, viền đáy màu nhấn)
    td = dict(nen=pa['td_nen'], chu=pa['td_chu'], vach=pa['td_vach'], day=pa['td_day'], re=pa['td_re']) if pa else \
        dict(nen=mt['chinh'], chu='#FFFFFF', vach=mt['chinh_re'], day=TOKEN_NHAN_GOC, re=mt['chinh_re'])
    dau = dict(nen=pa['dau_nen'], chu=pa['dau_chu'], vien=pa['dau_vien']) if pa else \
        (dict(nen='#24324A', chu='#93C5FD', vien='#334155') if them else dict(nen=DAU_GOC['nen'], chu=mt['chinh'], vien=DAU_GOC['vien']))
    kq = {'nen': loc({**chinh, **(TOI_NEN if them else {}), g['nen']: nen, g['khung']: khung, TD_GOC['nen']: td['nen'], TD_GOC['re']: td['re'], DAU_GOC['nen']: dau['nen']}),
          'vien': loc({**chinh, **(TOI_VIEN if them else {}), g['vach']: vach, TD_GOC['vach']: td['vach'], TD_GOC['day']: td['day'], DAU_GOC['vien']: dau['vien']}),
          'chu': loc({**chinh, **(TOI_CHU if them else {}), g['chu']: chu, g['chu_phu']: chu_phu, TD_GOC['chu']: td['chu'], DAU_GOC['chu']: dau['chu']})}
    _NHO_BANG_DOI_MAU[khoa] = kq
    return kq


def mau_theo_tong(mau: str, loai: str = 'nen') -> str:
    """Một màu GỐC (viết theo tông mặc định) -> màu của tông đang dùng. loai: 'nen' / 'vien' / 'chu'. Dùng cho màu đặt trong MÔ HÌNH
    bảng / rich text (BackgroundRole, ForegroundRole, <span style>) mà bảng kiểu không đổi được (1.0.35)."""
    return _bang_doi_mau(TONG_NEN[0]).get(loai, {}).get(mau.upper(), mau)


def qmau_theo_tong(mau: str, loai: str = 'nen') -> QColor:
    return QColor(mau_theo_tong(mau, loai))


# khối thêm cho tông Tối (đặt CUỐI bảng kiểu): bảng, tiêu đề bảng, ô nhập, menu trái, hộp thoại, chú thích
QSS_TOI = '''
    QDialog, QMainWindow, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget { background: #0B1120; }
    QWidget#nut_phong_bd { background: rgba(30, 41, 59, 230); }
    QTableWidget, QTableView, QListWidget, QTreeWidget, QTreeView { background: #1E293B; alternate-background-color: #0F172A;
        color: #F1F5F9; gridline-color: #334155; border: 1px solid #334155; selection-background-color: #1E40AF;
        selection-color: #FFFFFF; }
    QHeaderView::section, QHeaderView::section:horizontal { background: #0F172A; color: #93C5FD; border: 0;
        border-right: 1px solid #334155; border-bottom: 2px solid #2563EB; }
    QTableCornerButton::section { background: #0F172A; border: 0; }
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit, QPlainTextEdit { background: #0F172A; color: #F8FAFC;
        border: 1px solid #475569; selection-background-color: #1E40AF; }
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled { background: #162033; color: #64748B; }
    QComboBox QAbstractItemView { background: #1E293B; color: #F1F5F9; selection-background-color: #1E40AF; }
    QMenu { background: #1E293B; color: #F1F5F9; border: 1px solid #334155; }
    QMenu::item:selected { background: #1E40AF; color: #FFFFFF; }
    QMenuBar { background: #0F172A; color: #E2E8F0; }
    QMenuBar::item:selected { background: #1E293B; }
    QToolTip { background: #1E293B; color: #F1F5F9; border: 1px solid #475569; }
    QCheckBox, QRadioButton, QLabel { color: #E2E8F0; background: transparent; }
    QGroupBox { color: #E2E8F0; }
'''


def ap_tong_nen(qss: str, ten: str | None = None) -> str:
    """Đổi màu nền / viền / chữ của bảng kiểu theo tông (một lượt cho mỗi khai báo - màu đã đổi không đổi tiếp). Màu trong
    setStyleSheet riêng của từng widget không đổi (giữ nguyên ý nghĩa: cảnh báo, trạng thái)."""
    doi = _bang_doi_mau(TONG_NEN[0] if ten is None else ten)
    if not any(doi.values()):
        return qss

    def khai_bao(m):
        ten_tt = m.group(1).lower()
        if ten_tt.startswith('background') or ten_tt in ('alternate-background-color', 'selection-background-color'):
            bang = doi['nen']
        elif ten_tt.startswith('border') or ten_tt == 'gridline-color' or ten_tt.startswith('outline'):
            bang = doi['vien']
        elif ten_tt in ('color', 'selection-color'):
            bang = doi['chu']
        else:
            return m.group(0)
        if not bang:
            return m.group(0)
        return m.group(1) + m.group(2) + _RE_MAU_HEX.sub(lambda h: bang.get(h.group(0).upper(), h.group(0)), m.group(3))
    return _RE_KHAI_BAO.sub(khai_bao, qss)


# 1.0.51 (WCAG 2.4.7): nút đang có tiêu điểm bàn phím có vòng xanh rõ (Tab đi qua các nút) - viền 2px, đệm bớt 1px cho chữ không nhảy.
# Đặt sau kiểu nút + biến thể KieuNut (thắng màu nhóm / biến thể cùng độ ưu tiên; khối tông Tối / menu trái vẫn ở cuối); nút nền đặc dùng vòng xanh nhạt để thấy trên nền navy
QSS_TIEU_DIEM_NUT = '''
    QPushButton:focus { border: 2px solid #2563EB; padding: 3px 9px; }
    QPushButton[bien_the="primary"]:focus, QPushButton[bien_the="success"]:focus, QPushButton[nhom="luu"]:focus {
        border: 2px solid #93C5FD; }
'''


def _qss_day_du() -> str:
    """Bảng kiểu cả phần mềm: kiểu chung + biến thể nút KieuNut (đặt cuối). Mọi chỗ đặt / dựng lại bảng kiểu (phóng to, thu
    nhỏ) dùng hàm này - trước đây phong_to dựng lại thiếu phần biến thể. 1.0.33: dựng bằng màu gốc rồi đổi theo tông nền."""
    moi = {k: TOKEN[k] for k in (*_KHOA_MAU_NEN, 'chinh', 'chinh_re')}
    TOKEN.update(_TOKEN_GOC, chinh=CHINH_GOC[0], chinh_re=CHINH_GOC[1])
    try:
        qss = _qss() + _qss_kieu_nut() + QSS_TIEU_DIEM_NUT
    finally:
        TOKEN.update(moi)
    return ap_tong_nen(qss) + (QSS_TOI + _qss_o_tich_toi() if TONG_NEN[0] == 'toi' else '') + _qss_menu_trai()


def bang_mau_ung_dung():
    """QPalette của phần mềm theo TOKEN hiện tại (nền cửa sổ, nền ô, chữ) - ap_dung lúc mở, dat_tong_nen khi đổi tông."""
    p = QPalette()
    toi = TONG_NEN[0] == 'toi'
    for vai_, mau in ((QPalette.ColorRole.Window, TOKEN['nen']), (QPalette.ColorRole.Base, TOKEN['khung']),
                      (QPalette.ColorRole.AlternateBase, '#0F172A' if toi else '#F8FAFC'), (QPalette.ColorRole.Text, TOKEN['chu']),
                      (QPalette.ColorRole.WindowText, TOKEN['chu']), (QPalette.ColorRole.ButtonText, TOKEN['chu']),
                      (QPalette.ColorRole.Button, '#1E293B' if toi else '#FFFFFF'), (QPalette.ColorRole.Highlight, '#1E40AF' if toi else MAU_CHON_DIU[0]),
                      (QPalette.ColorRole.HighlightedText, '#FFFFFF' if toi else MAU_CHON_DIU[1]),
                      (QPalette.ColorRole.ToolTipBase, '#1E293B' if toi else '#FFFDE7'),
                      (QPalette.ColorRole.ToolTipText, '#F1F5F9' if toi else '#1A1A1A')):
        p.setColor(vai_, QColor(mau))
    return p


def dat_tong_nen(ten: str, luu: bool = False, ap_lai: bool = True) -> str:
    """Đặt tông nền bề mặt (chu_de.TONG_NEN: sang / diu / am / toi / trang): TOKEN nen / khung / vach / chu / chu_phu, bảng màu và bảng kiểu chung
    của mọi cửa sổ đang mở (ap_lai). luu: nhớ cho lần mở sau (chạy không màn hình - kiểm thử - không ghi máy thật). Windows tương
    phản cao: chỉ nhớ, không áp (đang dùng màu hệ thống)."""
    from . import chu_de
    ten = ten if ten in chu_de.TONG_NEN else chu_de.MAC_DINH_TONG_NEN
    TONG_NEN[0] = ten
    _, nen, khung, vach, chu, chu_phu = chu_de.TONG_NEN[ten]
    mt = chu_de.mau_tong(ten)
    TOKEN.update(nen=nen, khung=khung, vach=vach, vien=vach, chu=chu, chu_phu=chu_phu, chinh=mt['chinh'], chinh_re=mt['chinh_re'])
    if luu:
        chu_de.ghi(cai_dat_nho(), tong_nen=ten)
    app = QApplication.instance()
    if ap_lai and app is not None and getattr(app, '_bo_to_mau', None) is not None and not getattr(app, '_tuong_phan_cao', False):
        app.setPalette(bang_mau_ung_dung())
        app.setStyleSheet(_co_gian(_qss_day_du(), TY_LE[0]) if TY_LE[0] != 1 else _qss_day_du())
    if ap_lai:
        _ap_lai_kieu_theo_tong()
    for ham in list(KHI_DOI_TONG_NEN):
        try:
            ham(ten)
        except RuntimeError:                              # widget đã bị hủy
            KHI_DOI_TONG_NEN.remove(ham)
    return ten


def dat_phuong_an_navy(ma: str, luu: bool = False, ap_lai: bool = True) -> str:
    """Đổi phương án Navy: áp ngay cho mọi cửa sổ đang mở (qua dat_tong_nen), luu: nhớ cho lần mở sau."""
    from . import chu_de
    ma = chu_de.dat_phuong_an(ma)
    if luu:
        chu_de.ghi(cai_dat_nho(), phuong_an_navy=ma)
    dat_tong_nen(TONG_NEN[0], ap_lai=ap_lai)
    return ma


KHI_DOI_TONG_NEN = []          # hàm(tên tông) gọi sau mỗi lần đổi tông (nút đổi nhanh trên banner cập nhật chữ / biểu tượng)


def mau_o_theo_tong(g: dict, loai: str = 'nen', **ten_mau) -> tuple:
    """P1: hằng QColor cấp module của màn hình (nền ô trạng thái XANH / DO / VANG…, chữ liên kết) theo tông nền đang dùng. Gán vào
    globals() g của module NGAY và gán lại sau mỗi lần đổi tông - mã trong module đọc tên hằng lúc vẽ bảng nên tự theo tông mới
    (trước đây QColor('#E2EFDA') tính một lần lúc nạp: tông Tối ô vẫn nền sáng dưới chữ sáng). Viết:
        XANH, DO = mau_o_theo_tong(globals(), XANH='#E2EFDA', DO='#F8CBAD')
    Module khác cần hằng này thì đọc thuộc tính lúc dùng (man_hinh_theo_doi.XANH), không `from … import XANH` ở cấp module."""
    def gan(_ten=None):
        for k, v in ten_mau.items():
            g[k] = qmau_theo_tong(v, loai)
    gan()
    KHI_DOI_TONG_NEN.append(gan)
    return tuple(g[k] for k in ten_mau)
_KIEU_THEO_TONG = []            # [(weakref widget, qss gốc)] - kiểu riêng của widget đổi theo tông (dat_kieu_theo_tong)


def dat_kieu_theo_tong(w: QWidget, qss: str) -> None:
    """setStyleSheet riêng của widget (dải, thẻ viết bằng màu gốc #F8FAFC / #E2E8F0…) đổi theo tông nền đang dùng - lúc đặt và mỗi lần
    đổi tông (dat_tong_nen). Kiểu riêng đặt thẳng bằng setStyleSheet thì giữ nguyên màu khi đổi tông (1.0.34)."""
    import weakref
    _dat_kieu_co_gian(w, ap_tong_nen(qss))
    # P1: mỗi widget một mục (đặt lại kiểu nhiều lần - nhãn so sánh khái toán đổi màu theo kết quả - không dồn mục cũ)
    _KIEU_THEO_TONG[:] = [x for x in _KIEU_THEO_TONG if x[0]() is not None and x[0]() is not w]
    _KIEU_THEO_TONG.append((weakref.ref(w), qss))


def nut_co_mo_ta(nut, mo_ta: str) -> QWidget:
    """Ô tích / nút chọn có DÒNG MÔ TẢ PHỤ (Đợt B 09/11/2026): tiêu đề ngắn trên nút, giải thích dài xuống dòng bên dưới (chữ phụ 12 px,
    thụt theo chữ nút, tự xuống dòng - không bị cắt, không làm nút rộng thêm). Trả về khung chứa; thêm KHUNG vào bố cục, giữ `nut` để đọc
    trạng thái. Mô tả cũng là tooltip của nút."""
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)
    v.addWidget(nut)
    if mo_ta:
        lb = QLabel(mo_ta)
        lb.setWordWrap(True)
        lb.setContentsMargins(24, 0, 0, 4)
        dat_kieu_theo_tong(lb, f'QLabel {{ color: {TOKEN["chu_phu"]}; background: transparent; font-size: 12px; }}')
        v.addWidget(lb)
        if not nut.toolTip():
            nut.setToolTip(mo_ta)
    return w


def _dat_kieu_co_gian(w: QWidget, qss: str) -> None:
    """setStyleSheet rồi co giãn theo tỷ lệ chữ đang dùng (A+ / A−) - trước đây kiểu đặt sau khi cửa sổ hiện, và kiểu đặt lại khi đổi
    tông, về cỡ 100% dù người dùng đang để 120%."""
    w.setStyleSheet(qss)
    if TY_LE[0] != 1:
        _co_gian_widget(w, TY_LE[0])


def _ap_lai_kieu_theo_tong() -> None:
    con = []
    for ref, qss in _KIEU_THEO_TONG:
        w = ref()
        if w is None:
            continue
        try:
            if w.isVisible():
                _dat_kieu_co_gian(w, ap_tong_nen(qss))
            else:                                         # P1: widget đang ẩn: đổi màu khi nó hiện ra (_BoToMau, sự kiện Show)
                w.setProperty('qss_cho_tong', qss)
            con.append((ref, qss))
        except RuntimeError:                              # widget đã bị hủy (C++)
            pass
    _KIEU_THEO_TONG[:] = con


def _ap_kieu_cho(w: QWidget) -> None:
    """Widget vừa hiện: áp kiểu riêng đã hoãn lúc nó đang ẩn (đổi tông nền, đổi tỷ lệ chữ)."""
    qss = w.property('qss_cho_tong')
    if qss:
        w.setProperty('qss_cho_tong', None)
        w.setProperty('qss_cho_ty_le', None)
        _dat_kieu_co_gian(w, ap_tong_nen(qss))           # đã gồm co giãn theo tỷ lệ chữ
    elif w.property('qss_cho_ty_le'):
        w.setProperty('qss_cho_ty_le', None)
        _co_gian_widget(w, TY_LE[0])


def doi_nhanh_tong_nen() -> str:
    """1.0.34: một cú bấm đổi Sáng <-> Tối (chu_de.dao_nhanh_tong_nen), áp ngay và nhớ cho lần mở sau. Trả tông mới."""
    from . import chu_de
    return dat_tong_nen(chu_de.dao_nhanh_tong_nen(TONG_NEN[0]), luu=True)


_MUI_TEN = {}


def _anh_mui_ten(mau: str, len_: bool = False) -> str:
    """Ảnh mũi tên xuống (chevron) cho ô chọn - đường dẫn dạng '/' dùng trong url() của QSS; '' nếu không tạo được. Vẽ một lần mỗi
    phiên bằng QPainter (2 cỡ: tên@2x.png cho màn hình phóng to) vào thư mục tạm: đặt kiểu ::drop-down thì Qt bỏ mũi tên gốc của
    Fusion (kèm vạch đen dày cạnh mũi tên - 22/10/2026 người dùng: giao diện tinh gọn)."""
    khoa = (mau, len_)
    if khoa in _MUI_TEN:
        return _MUI_TEN[khoa]
    duong = ''
    try:
        import tempfile
        from pathlib import Path
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QPen, QPixmap, QPolygonF
        if QApplication.instance() is None:
            return ''
        d = Path(tempfile.gettempdir()) / 'pabt_qss'
        d.mkdir(parents=True, exist_ok=True)
        ten = ('mui_len_' if len_ else 'mui_ten_') + mau.lstrip('#')
        if all((d / f'{ten}{h}.png').exists() for h in ('', '@2x')):
            _MUI_TEN[khoa] = str(d / f'{ten}.png').replace('\\', '/')    # đã vẽ ở lần chạy trước: bỏ qua (khởi động nhanh hơn)
            return _MUI_TEN[khoa]
        for he_so, hau_to in ((1, ''), (2, '@2x')):
            n = 12 * he_so
            pm = QPixmap(n, n)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(QColor(mau), 1.6 * he_so, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            y1, y2 = (7.5, 4.5) if len_ else (4.5, 7.5)       # len_: mũi tên lên (nút tăng của ô số)
            p.drawPolyline(QPolygonF([QPointF(3 * he_so, y1 * he_so), QPointF(6 * he_so, y2 * he_so), QPointF(9 * he_so, y1 * he_so)]))
            p.end()
            f = d / f'{ten}{hau_to}.png'
            pm.save(str(f), 'PNG')
        duong = str(d / f'{ten}.png').replace('\\', '/')
    except Exception:                                   # noqa: BLE001 - không tạo được ảnh: ô chọn giữ mũi tên gốc của Qt
        duong = ''
    _MUI_TEN[khoa] = duong
    return duong


def _qss_o_chon() -> str:
    """Ô chọn (QComboBox) tinh gọn: phần mũi tên trong suốt, không vạch ngăn, chevron slate (tắt: nhạt hơn)."""
    thuong, tat = _anh_mui_ten('#64748B'), _anh_mui_ten('#CBD5E1')
    if not thuong:
        return ''
    return f'''
    QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 24px; border: 0;
        background: transparent; }}
    QComboBox::down-arrow {{ image: url({thuong}); width: 12px; height: 12px; }}
    QComboBox::down-arrow:disabled {{ image: url({tat or thuong}); }}
    QComboBox::down-arrow:on {{ top: 1px; }}
    ''' + _qss_o_so()


def _qss_o_so() -> str:
    """Nút tăng / giảm của ô số (QSpinBox): ô có kiểu viền riêng thì Qt vẽ nút mặc định thành vạch đen "–|" (30/10/2026 người dùng: ô
    Nhân khẩu) - vẽ chevron lên / xuống nhỏ như ô chọn, nền trong suốt, rê chuột nền nhạt."""
    len_, xuong = _anh_mui_ten('#64748B', True), _anh_mui_ten('#64748B')
    len_tat, xuong_tat = _anh_mui_ten('#CBD5E1', True), _anh_mui_ten('#CBD5E1')
    if not (len_ and xuong):
        return ''
    return f'''
    QSpinBox::up-button, QDoubleSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; width: 18px;
        border: 0; background: transparent; }}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; width: 18px;
        border: 0; background: transparent; }}
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover,
        QDoubleSpinBox::down-button:hover {{ background: #EEF3FA; }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url({len_}); width: 10px; height: 10px; }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url({xuong}); width: 10px; height: 10px; }}
    QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled {{ image: url({len_tat or len_}); }}
    QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{ image: url({xuong_tat or xuong}); }}
    '''


def _qss() -> str:
    chu_tat, nen_tat, vien_tat = NUT_TAT
    # 1.0.02: QToolButton (thường / ribbon) cùng bộ màu với QPushButton - không còn nền đặc / nền nhạt cam, tím, vàng theo nhóm
    nut = '\n'.join(
        f'''{_nut_qss(n, nen, chu, re_)}
        {_qss_nut_loai('QToolButton', n, nen, re_) if n != 'nhat' else ''}
        {_qss_nut_loai('QToolButton', n, nen, re_, '[ribbon="1"]') if n != 'nhat' else ''}
        QToolButton[ribbon="1"][nhom="{n}"] {{ text-align: left; }}
        QPushButton[nhom="{n}"]:disabled, QToolButton[nhom="{n}"]:disabled {{ background: {nen_tat}; color: {chu_tat};
            border-color: {vien_tat}; }}'''
        for n, (nen, chu, re_) in MAU.items())
    return nut + f'''
    QMainWindow {{ background: #EEF2F7; }}
    QDialog {{ background: #F8FAFC; }}
    QToolBar {{ background: #FFFFFF; border-bottom: 2px solid {CHINH}; spacing: 4px; padding: 5px; }}
    QPushButton {{ border-radius: 5px; padding: 4px 10px; border: 1px solid {NUT_PHU[2]}; background: {NUT_PHU[0]};
        color: {NUT_PHU[1]}; }}
    QPushButton:hover {{ background: {NUT_PHU[3]}; border-color: {NUT_PHU[4]}; }}
    QPushButton:pressed {{ background: {NUT_PHU[5]}; }}
    QPushButton:disabled {{ color: {chu_tat}; background: {nen_tat}; border-color: {vien_tat}; }}
    QHeaderView::section {{ background: #EEF3F8; color: #24415E; font-weight: 600; padding: 7px 6px; border: 0;
        border-right: 1px solid #DDE5EE; border-bottom: 2px solid #C9D6E3; }}
    QHeaderView::section:horizontal {{ background: {TD_GOC['nen']}; color: {TD_GOC['chu']}; font-weight: 600; padding: 4px 8px;
        min-height: {CAO_TIEU_DE_BANG - 10}px; border: 0; border-right: 1px solid {TD_GOC['vach']}; border-bottom: 2px solid {TD_GOC['day']}; }}
    QHeaderView::section:horizontal:hover {{ background: {TD_GOC['re']}; }}
    QHeaderView {{ color: {TD_GOC['chu']}; }}
    QTableView, QTreeView, QTableWidget, QTreeWidget {{ background: #FFFFFF; alternate-background-color: #F8FAFC;
        gridline-color: #E2E8F0; selection-background-color: #DBEAFE; selection-color: #0F172A; border: 1px solid #DCE3EA;
        border-radius: 6px; }}
    QTableCornerButton::section {{ background-color: {CHINH}; border: none; }}
    QHeaderView::section:vertical {{ background-color: #F8FAFC; color: {TOKEN['chu_phu']}; font-weight: 500; border: 0;
        border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0; padding: 0 4px; }}
    QTableView::item:focus, QTableWidget::item:focus {{ border: 1px solid {TOKEN['nhan']}; }}
    QLineEdit[nhap="1"], QComboBox[nhap="1"], QSpinBox[nhap="1"] {{ min-height: 24px; font-size: 13px; padding: 4px 10px; }}
    QTableView QLineEdit, QTableView QComboBox, QTableView QPlainTextEdit {{ font-size: 13px; padding: 2px 6px;
        border: 2px solid #2563EB; border-radius: 3px; background: #FFFFFF; selection-background-color: #DBEAFE; selection-color: #0F172A; }}
    QTabBar {{ font-weight: 600; font-size: 13px; }}
    QTabBar::tab {{ background: {THE_TAB['nen']}; color: {THE_TAB['chu']}; padding: 5px 14px; margin-right: 2px; margin-top: 2px;
        border: 1px solid {THE_TAB['vien']}; border-bottom: 0;
        border-top-left-radius: 5px; border-top-right-radius: 5px; }}
    QTabBar::tab:hover:!selected {{ background: {THE_TAB['nen_re']}; color: {THE_TAB['chu_re']}; }}
    QTabBar::tab:selected {{ background: #FFFFFF; color: {CHINH}; border: 1px solid {THE_TAB['vien']};
        border-bottom: 0; border-top: 2px solid {CHINH}; margin-top: 0px; }}
    QTabWidget::pane {{ border: 1px solid {THE_TAB['vien']}; border-radius: 0 6px 6px 6px; background: #FFFFFF; top: -1px; }}
    QLabel[vai="nhan"] {{ color: {CHINH}; font-weight: 600; }}
    QWidget#nut_phong_bd {{ background: rgba(255, 255, 255, 230); }}
    QLabel[vai="tieu_de"] {{ color: {CHINH}; background: #F1F5F9; font-weight: 700; padding: 6px 10px; border-radius: 5px;
        border-left: 3px solid {CHINH}; }}
    QLabel[vai="bang_ten"] {{ color: #0F3A63; background: #FFFFFF; font-size: 13px; padding: 8px 12px; border-radius: 8px;
        border: 1px solid #D5E1ED; border-left: 4px solid {TOKEN['nhan']}; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QPlainTextEdit, QTextEdit {{ background: #FFFFFF; color: {TOKEN['chu']};
        border: 1px solid #8696AB; border-radius: 6px; padding: 4px 8px; selection-background-color: {MAU_CHON_DIU[0]};
        selection-color: {MAU_CHON_DIU[1]}; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{ min-height: 20px; }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QPlainTextEdit:hover {{ border-color: #64748B; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
        border: 2px solid {TOKEN['nhan']}; padding: 3px 7px; background: #FFFFFF; }}
    QLineEdit[nhap="1"]:focus, QComboBox[nhap="1"]:focus, QSpinBox[nhap="1"]:focus {{ padding: 3px 9px; }}
    QTableView QLineEdit:focus, QTableView QComboBox:focus, QTableView QPlainTextEdit:focus {{ padding: 2px 6px; }}
    QLineEdit:read-only {{ background: #F1F4F7; color: #4A5866; }}
    QToolButton[nho="1"] {{ font-size: 11px; padding: 3px 6px 2px 6px; }}
    QTabBar[vai="lam_viec"] {{ background: transparent; }}
    QTabBar[vai="lam_viec"]::tab {{ background: transparent; color: {TOKEN['chu_phu']}; border: 0;
        border-bottom: 2px solid transparent; padding: 7px 14px; margin: 0; font-weight: 600; }}
    QTabBar[vai="lam_viec"]::tab:selected {{ color: {TOKEN['chinh']}; background: #FFFFFF;
        border-bottom: 2px solid {TOKEN['nhan']}; }}
    QTabBar[vai="lam_viec"]::tab:hover {{ color: {TOKEN['chinh']}; }}
    {QSS_THE_CHAO}
    {QSS_THE_KPI_GON_CHUNG}
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
    QCheckBox, QRadioButton {{ spacing: 7px; min-height: 24px; }}      /* 1.0.16: vùng bấm >= 24 px (WCAG 2.2) */
    QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: #C3CFDB; border-radius: 4px; min-height: 28px; }}
    QScrollBar::handle:vertical:hover {{ background: #9FB3C8; }}
    QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: #C3CFDB; border-radius: 4px; min-width: 28px; }}
    QScrollBar::handle:horizontal:hover {{ background: #9FB3C8; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    QProgressBar {{ border: 1px solid #C9D3DD; border-radius: 6px; background: #FFFFFF; text-align: center; height: 16px; }}
    QProgressBar::chunk {{ background: #2563EB; border-radius: 5px; }}
    QSplitter::handle {{ background: #E2E8F0; }}
    QSplitter::handle:hover {{ background: #94A3B8; }}
    QComboBox {{ combobox-popup: 0; }}
    QComboBox QAbstractItemView, QListView, QListWidget, QTreeView {{ background: #FFFFFF; color: #1A1A1A;
        selection-background-color: {MAU_CHON_DIU[0]}; selection-color: {MAU_CHON_DIU[1]}; outline: 0; }}
    QComboBox QAbstractItemView {{ border: 1px solid #CBD5E1; }}
    QComboBox QAbstractItemView::item {{ min-height: 24px; padding: 2px 8px; color: #1A1A1A; }}
    QComboBox QAbstractItemView::item:hover, QListView::item:hover, QListWidget::item:hover {{
        background: {MAU_RE_DIU}; color: #0F172A; }}
    QComboBox QAbstractItemView::item:selected, QListView::item:selected, QListWidget::item:selected {{
        background: {MAU_CHON_DIU[0]}; color: {MAU_CHON_DIU[1]}; }}
    QTableView::item:hover, QTreeView::item:hover {{ background: #EEF5FC; color: #1A1A1A; }}
    QTableView::item:selected, QTreeView::item:selected {{ background: #DBEAFE; color: #0F172A; }}
    QMenu {{ background: #FFFFFF; color: #1A1A1A; border: 1px solid #C9D3DD; }}
    QMenu::item {{ padding: 6px 24px 6px 12px; }}
    QMenu::item:selected {{ background: #DCEBFA; color: #0B2E4F; }}
    QToolTip {{ background: #FFFFFF; color: #1F2D3A; border: 1px solid #C9D3DD; padding: 4px 6px; }}
    QGroupBox {{ font-weight: 600; color: {CHINH}; background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px;
        margin-top: 6px; padding: 26px 8px 8px 8px; }}
    QGroupBox::title {{ subcontrol-origin: border; subcontrol-position: top left; left: 12px; top: 7px; padding: 0 4px;
        background: transparent; border: none; color: {CHINH}; font-weight: 700; }}
    QStatusBar {{ background: #FFFFFF; color: {CHINH}; border-top: 1px solid #DCE4EC; }}
    QStatusBar QToolButton {{ border-radius: 6px; padding: 3px 10px; }}
    QFrame[vai="bang_to_chuc"] {{ background: transparent; border: 0; }}
    QFrame[vai="bang_to_chuc"] QLabel {{ color: #FFFFFF; background: transparent; border: 0; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="logo"] {{ background: transparent; border: 0; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="ten_phan_mem"] {{ color: #FFFFFF; font-size: 13px; font-weight: 700; letter-spacing: 0.3px; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="ten_to_chuc"] {{ color: {MAU_PHU_DE}; font-size: 11px; font-weight: 500; letter-spacing: 0.3px; }}
    QFrame[vai="bang_to_chuc"] QLabel[vai="dong_phu"] {{ color: #E2E8F0; font-size: 11px; font-weight: 500; letter-spacing: 0.3px; }}
    QFrame[vai="bang_to_chuc"] QToolButton[vai="nut_bang"] {{ color: #FFFFFF; background: rgba(255, 255, 255, 26);
        border: 1px solid rgba(255, 255, 255, 70); border-radius: 6px; padding: 2px 8px; font-weight: 600; font-size: 12px; }}
    QFrame[vai="bang_to_chuc"] QToolButton[vai="nut_bang"]:hover {{ background: rgba(255, 255, 255, 52);
        border-color: {TOKEN['nhan']}; }}
    QFrame[vai="bang_to_chuc"] QToolButton[vai="nut_bang"]:pressed {{ background: rgba(255, 255, 255, 80); }}
    QFrame[vai="bang_to_chuc"] QToolButton[vai="nut_bang"]:disabled {{ color: rgba(255, 255, 255, 110);
        background: transparent; border-color: rgba(255, 255, 255, 40); }}
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
    ''' + _qss_o_chon() + _qss_the_so() + QSS_HANG_NHAP + QSS_THE_TUY_CHON_IN + QSS_THE_GACH_CHAN + QSS_O_TIM_CHON + QSS_HO_SO_HO + QSS_LAP_PA_DAI + QSS_TONG_HOP_KP


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
    (r'^tinh don gia dat', 0xE8EF),       # 1.0.70: máy tính, cùng biểu tượng nút Bảng tính giá đất trong mục 1. Đất
    (r'tiep nhan', 0xE8F0),               # 1.0.04: Tiếp nhận hồ sơ pháp lý
    (r'^danh sach ho', 0xE716), (r'tong quat ho', 0xE8FD), (r'^quyet dinh( phe duyet)?$', 0xE8A5), (r'tong hop tien', 0xE9F9),
    (r'theo doi tien do|^tien do|theo doi chi tra', 0xE9D2), (r'^mau in', 0xE72C), (r'^bang tong hop', 0xE80A), (r'^hoan tac', 0xE7A7), (r'^lam lai', 0xE7A6),
    (r'du an tren may chu', 0xE839), (r'mang ve lam offline', 0xE896), (r'dua len may chu', 0xE898),
    (r'^dang nhap', 0xE77B), (r'du an moi', 0xE710), (r'^mo du an|^mo du toan', 0xE8E5), (r'luu du an thanh', 0xE792), (r'^(luu|save)', 0xE74E),
    (r'^thuc hien', 0xE768),
    (r'nhap file excel|nhap phuong an chi tiet|^nhap tu|^tu file|^tu danh sach|^tu du an', 0xE8B5), (r'thong tin du an|gioi thieu', 0xE946),
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


_NHO_ICON = {}                  # 1.0.51: (ký hiệu, màu, cỡ) -> QIcon đã vẽ (menu / nút dựng lại không vẽ lại bằng QPainter)


def icon_ky_hieu(ma: int, mau: str = '#FFFFFF', co: int = 24):
    """QIcon vẽ từ ký hiệu của phông biểu tượng Windows, hoặc None nếu máy không có phông / ký hiệu. Trả BẢN SAO của QIcon đã nhớ
    (dữ liệu dùng chung, nơi gọi thêm ảnh vào không làm đổi bản nhớ)."""
    from PySide6.QtGui import QIcon
    khoa = (ma, str(mau).upper(), int(co))
    if khoa in _NHO_ICON:
        ic = _NHO_ICON[khoa]
        return QIcon(ic) if ic is not None else None
    ic = _ve_icon_ky_hieu(ma, mau, co)
    if len(_NHO_ICON) > 600:
        _NHO_ICON.clear()
    _NHO_ICON[khoa] = ic
    return QIcon(ic) if ic is not None else None


def _ve_icon_ky_hieu(ma: int, mau: str = '#FFFFFF', co: int = 24):
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


def icon_hai_trang_thai(ma: int, mau_thuong: str, mau_chon: str, co: int = 18):
    """QIcon hai màu theo trạng thái nút checkable: chưa chọn (State.Off) mau_thuong, đang chọn (State.On) mau_chon - mục menu trái
    đang chọn đổi màu biểu tượng cùng màu chữ. None nếu máy không có phông ký hiệu."""
    from PySide6.QtGui import QIcon
    thuong, chon = icon_ky_hieu(ma, mau_thuong, co), icon_ky_hieu(ma, mau_chon, co)
    if thuong is None or chon is None:
        return None
    ic = QIcon()
    for mode in (QIcon.Mode.Normal, QIcon.Mode.Active, QIcon.Mode.Selected):
        ic.addPixmap(thuong.pixmap(co * 2, co * 2), mode, QIcon.State.Off)
        ic.addPixmap(chon.pixmap(co * 2, co * 2), mode, QIcon.State.On)
    return ic


def huy_hieu_bieu_tuong(ma: int, mau: str, nen: str, co: int = 44, bo: int = 12):
    """QIcon: biểu tượng ký hiệu màu `mau` giữa ô vuông bo góc nền `nen`, viền sáng + viền mảnh màu điểm nhấn (huy hiệu thẻ chào
    1.0.34). None nếu máy không có phông ký hiệu (Windows 7)."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QIcon, QPen, QPixmap
    ic = icon_ky_hieu(ma, mau, CO_ICON_TRONG_HUY_HIEU)
    if ic is None:
        return None
    kq = QIcon()
    for he in (1, 2):
        n = co * he
        pm = QPixmap(n, n)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(255, 255, 255, 200), 1.2 * he))
        p.setBrush(QColor(nen))
        p.drawRoundedRect(QRectF(0.6 * he, 0.6 * he, n - 1.2 * he, n - 1.2 * he), bo * he, bo * he)
        vien = QColor(mau)
        vien.setAlpha(60)
        p.setPen(QPen(vien, 1 * he))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(1.5 * he, 1.5 * he, n - 3 * he, n - 3 * he), (bo - 1) * he, (bo - 1) * he)
        c = CO_ICON_TRONG_HUY_HIEU * he
        p.drawPixmap(int((n - c) / 2), int((n - c) / 2), ic.pixmap(c, c))
        p.end()
        kq.addPixmap(pm)
    return kq


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
    'tin': ('#0C4A6E', '#F0F9FF', '#BAE6FD'),          # thông tin trung tính (1.0.02: thanh thông báo xanh trời nhạt)
    'canh_bao': ('#7A4B00', '#FFF4DB', '#F1D9A0'),     # cần xem lại (không phải lỗi của người dùng)
    'loi': ('#A12A1F', '#FCEDEB', '#F3CFCA'),          # lỗi phải xử lý mới làm tiếp được
}


MAU_HE_SO_K = '#1F76A6'                                  # cột Hệ số K (bảng giá NQ 28, bảng hệ số K): căn giữa, đậm, xanh trời
MAU_GIA_K = CHINH_GOC[0]                                 # cột Giá × K: căn phải, đậm, navy


def _o_dam(it, mau: str, can) -> None:
    from PySide6.QtGui import QBrush
    f = it.font()
    f.setBold(True)
    it.setFont(f)
    it.setForeground(QBrush(QColor(mau_theo_tong(mau, 'chu'))))
    it.setTextAlignment(can)


def kieu_o_he_so_k(it) -> None:
    """Ô Hệ số K (QTableWidgetItem): căn giữa, chữ đậm xanh trời (1.0.02 - nổi giữa các cột giá)."""
    _o_dam(it, MAU_HE_SO_K, Qt.AlignmentFlag.AlignCenter)


def kieu_o_gia_k(it) -> None:
    """Ô Giá × K: căn phải, chữ đậm navy (giá dùng để lập phương án)."""
    _o_dam(it, MAU_GIA_K, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


# --------------------------------------------------------------------- phông số đồng bộ (người dùng 20/10/2026)
# MỘT nguồn cho mọi ô số tiền / diện tích / khối lượng (danh sách hộ BangHo, BangAo các trang tổng hợp, BangMuc, Khái toán): phông
# 1.0.77 (người dùng 07/11/2026: Consolas khó xem, số 0 có gạch chéo): Segoe UI (chữ số cùng bề rộng nên cột vẫn thẳng hàng, dấu chấm hẹp, số gọn), máy thiếu -> Tahoma; canh phải; số 0 xám nhạt, tiền dương navy,
# vượt / cảnh báo đỏ. Phông nhớ theo phông gốc (QFont.key): Phóng to / Thu nhỏ đổi cỡ thì tự dựng lại.
PHONG_SO = 'Segoe UI'
PHONG_SO_DU_PHONG = 'Tahoma'
MAU_SO_KHONG = '#64748B'          # 1.0.42: WCAG AA 4,76:1 trên trắng (trước #94A3B8 = 2,56:1)
MAU_SO_TIEN = '#1E3A5F'
MAU_SO_VUOT = '#B83A3A'
SO_KHONG = frozenset(('0', '0,0', '0,00', '0,0%', '0.0%', '0%', '-', '—'))
CAN_SO = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)     # số nguyên: PySide2 bỏ qua cờ ghép kiểu enum
# cảnh báo tức thời KHÔNG chặn (diện tích dòng đất vượt DT thu hồi / nguyên thửa, DT còn lại âm, bàn giao thiếu ngày biên bản): hổ phách
MAU_CANH_BAO_NEN = '#FEF3C7'
MAU_CANH_BAO_VIEN = '#E5A93A'
MAU_CANH_BAO_CHU = '#7C4A12'
_NHO_PHONG_SO: dict = {}
_NHO_BUT_SO: dict = {}


def phong_so(goc=None, dam: bool = False):
    """QFont số (Segoe UI, dự phòng Tahoma) cùng cỡ với phông goc (mặc định phông ứng dụng); dam = đậm (thành tiền)."""
    goc = QFont(goc) if goc is not None else QApplication.font()
    khoa = (goc.key(), dam)
    f = _NHO_PHONG_SO.get(khoa)
    if f is None:
        f = QFont(goc)
        if hasattr(f, 'setFamilies'):
            f.setFamilies([PHONG_SO, PHONG_SO_DU_PHONG])
        else:                                           # Qt < 5.13
            f.setFamily(PHONG_SO)
        f.setStyleHint(QFont.StyleHint.SansSerif)
        f.setBold(dam)
        if len(_NHO_PHONG_SO) > 64:
            _NHO_PHONG_SO.clear()
        _NHO_PHONG_SO[khoa] = f
    return f


def mau_so(chu, tien: bool = False, vuot: bool = False):
    """Màu chữ (hex) của một ô số: vượt -> đỏ; số 0 / gạch -> xám nhạt; cột tiền có số -> navy; còn lại None (màu mặc định)."""
    if vuot:
        return mau_theo_tong(MAU_SO_VUOT, 'chu')
    v = str(chu if chu is not None else '').strip()
    if v in SO_KHONG:
        return mau_theo_tong(MAU_SO_KHONG, 'chu')
    if tien and v and (v[0].isdigit() or (v[0] in '+-' and v[1:2].isdigit())):
        return mau_theo_tong(MAU_SO_TIEN, 'chu')          # 1.0.35: theo tông (Tối: xanh sáng)
    return None


def but_so(mau: str):
    """QBrush theo màu hex (nhớ - data() của mô hình gọi mỗi ô mỗi lần vẽ)."""
    from PySide6.QtGui import QBrush
    b = _NHO_BUT_SO.get(mau)
    if b is None:
        b = _NHO_BUT_SO[mau] = QBrush(QColor(mau))
    return b


def kieu_o_so(it, tien: bool = False, vuot: bool = False, goc=None, dam: bool | None = None) -> None:
    """QTableWidgetItem số: phông số, canh phải, màu theo giá trị (mau_so). dam None = đậm khi là cột tiền."""
    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)   # CAN_SO (số nguyên) cho mô hình
    it.setFont(phong_so(goc, dam=tien if dam is None else dam))
    m = mau_so(it.text(), tien, vuot)
    if m is not None:
        it.setForeground(but_so(m))


def kieu_o_canh_bao(it, chu: str) -> None:
    """Ô có cảnh báo tức thời (không chặn gõ): nền hổ phách, chữ nâu đậm, chú thích = lý do."""
    it.setBackground(but_so(MAU_CANH_BAO_NEN))
    it.setForeground(but_so(MAU_CANH_BAO_CHU))
    it.setToolTip(chu)
    it.setData(Qt.ItemDataRole.UserRole + 2, chu)


def qss_canh_bao(loai: str = 'QLabel') -> str:
    """QSS ô / nhãn cảnh báo hổ phách (viền + nền) - cùng màu với kieu_o_canh_bao."""
    return (f'{loai} {{ color: {MAU_CANH_BAO_CHU}; background: {MAU_CANH_BAO_NEN}; border: 1px solid {MAU_CANH_BAO_VIEN}; '
            'border-radius: 6px; padding: 5px 8px; font-weight: 600; }')


def kieu_trang_thai(muc: str, loai: str = 'QLabel', dam: bool = True) -> str:
    """QSS màu trạng thái (MAU_TRANG_THAI) cho một loại thành phần - một nguồn màu cho băng kết quả, ô cảnh báo..."""
    chu_mau, nen, vien = MAU_TRANG_THAI[muc]
    return (f'{loai} {{ {"font-weight: 600; " if dam else ""}padding: 5px 8px; color: {chu_mau}; background: {nen}; '
            f'border: 1px solid {vien}; border-radius: 6px; }}')


def dat_trang_thai(nhan, muc: str, chu: str) -> None:
    """Đặt chữ + màu trạng thái cho QLabel (băng kết quả, dòng báo trong hộp thoại). muc: dat / tin / canh_bao / loi."""
    nhan.setText(chu)
    nhan.setStyleSheet(ap_tong_nen(kieu_trang_thai(muc)))           # 1.0.35: theo tông nền (Tối: dải tối)


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
        try:
            co_su_kien = QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
        except AttributeError:                          # Qt5: cờ int, không có ProcessEventsFlag
            co_su_kien = QEventLoop.ExcludeUserInputEvents
        vong.exec(co_su_kien)
        dong_ho.stop()
        for h in hop:
            h.close()
            h.deleteLater()
    luong.join()
    if 'loi' in kq:
        raise kq['loi']
    return kq.get('gt')


CHO_SAU_HUY_GIAY = 3.0          # 1.0.51: sau khi bấm Dừng, chờ hàm nền trả phần đã làm (trang OCR đang đọc) tối đa chừng này


def _co_su_kien_khong_nhap():
    """Cờ processEvents: vẽ cửa sổ / kéo được, không nhận bấm chồng lệnh (Qt5: int)."""
    from PySide6.QtCore import QEventLoop
    try:
        return QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
    except AttributeError:
        return QEventLoop.ExcludeUserInputEvents


def _cho_luong(luong, moi_nhip, nhip: float = 0.05, hop=None):
    """Chờ luồng nền: processEvents (cửa sổ vẽ / kéo được, không bấm chồng), không QEventLoop.exec (dễ kẹt khi QTimer không chạy).
    hop: hộp tiến độ có nút Dừng / Bỏ qua - 1.0.51: hộp chặn mọi cửa sổ khác (ApplicationModal) và vòng chờ nhận cả sự kiện chuột /
    phím, để nút Dừng bấm được (trước đây ExcludeUserInputEvents làm nút Dừng không phản hồi tới khi luồng nền tự xong)."""
    import time
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    co = _co_su_kien_khong_nhap()
    if hop is not None:
        hop.setWindowModality(Qt.WindowModality.ApplicationModal)
    while luong.is_alive():
        if moi_nhip():
            break
        if app is not None:
            if hop is not None and hop.isVisible():
                app.processEvents()
            else:
                app.processEvents(co)
        time.sleep(nhip)


def chay_nen_tien_do(cha, ham, tien=None, gioi_han: float | None = None):
    """Chạy ham(bao, cho) ở luồng nền (Tesseract / đọc file). tien: QProgressDialog đã hiện, nút Dừng.
    tien is None (kiểm thử im_lang): gọi thẳng trên luồng hiện tại. ham không đụng widget / CSDL cửa sổ."""
    import threading
    import time
    if tien is None:
        return ham(lambda *_a: None, lambda: False)
    kq, tien_do, huy = {}, [0, 1], threading.Event()

    def bao(i, n):
        tien_do[0], tien_do[1] = int(i or 0), max(int(n or 1), 1)

    def cho() -> bool:
        return huy.is_set()

    def chay():
        try:
            kq['gt'] = ham(bao, cho)
        except BaseException as e:                      # noqa: B036
            kq['loi'] = e

    luong = threading.Thread(target=chay, daemon=True)
    luong.start()
    bat_dau = time.monotonic()
    luc_huy = []

    def moi_nhip():
        if not huy.is_set() and (tien.wasCanceled() or (gioi_han is not None and time.monotonic() - bat_dau > gioi_han)):
            huy.set()
            luc_huy.append(time.monotonic())
        if luc_huy and time.monotonic() - luc_huy[0] > CHO_SAU_HUY_GIAY:
            return True                                 # bấm Dừng: chờ hàm nền trả kết quả đã có tối đa vài giây, không treo cửa sổ
        n = max(int(tien_do[1] or 1), 1)
        tien.setMaximum(n)
        tien.setValue(min(max(int(tien_do[0] or 0), 0), n))
        return not luong.is_alive()

    _cho_luong(luong, moi_nhip, hop=tien)
    luong.join(0.2 if luc_huy else 30)
    if luc_huy and luong.is_alive():                    # hàm nền chưa kịp dừng: bỏ kết quả, báo đã dừng như hàm tự dừng
        from .ocr import DaHuy
        raise DaHuy()
    if 'loi' in kq:
        raise kq['loi']
    return kq.get('gt')


def chay_nen_huy(cha, ham, chu: str = 'Đang xử lý…', nut_huy: str = 'Bỏ qua',
                 gioi_han: float | None = 45):
    """Như chay_nen nhưng có nút hủy + hết giờ. Trả None nếu bỏ qua / hết giờ (luồng nền daemon tiếp tục).
    Dùng Trợ lý AI sau OCR: mạng cắt không treo cửa sổ."""
    import threading
    import time
    from PySide6.QtWidgets import QProgressDialog
    kq = {}

    def chay():
        try:
            kq['gt'] = ham()
        except BaseException as e:                      # noqa: B036
            kq['loi'] = e

    luong = threading.Thread(target=chay, daemon=True)
    luong.start()
    luong.join(0.05)
    if not luong.is_alive():
        if 'loi' in kq:
            raise kq['loi']
        return kq.get('gt')
    hop = QProgressDialog(chu, nut_huy, 0, 0, cha)
    hop.setWindowTitle('LARC')
    hop.setWindowModality(Qt.WindowModality.WindowModal)
    hop.setMinimumDuration(0)
    hop.show()
    bat_dau = time.monotonic()

    def moi_nhip():
        if hop.wasCanceled() or (gioi_han is not None and time.monotonic() - bat_dau > gioi_han):
            kq['bo'] = True
            return True
        return not luong.is_alive()

    try:
        _cho_luong(luong, moi_nhip, hop=hop)
    finally:
        hop.close()
        hop.deleteLater()
    if kq.get('bo'):
        return None
    luong.join()
    if 'loi' in kq:
        raise kq['loi']
    return kq.get('gt')


def ghi_loi_log(chu: str) -> None:
    """Ghi một đoạn vào <thư mục máy>\\loi.log (không hiện hộp). Đường dự phòng: tải lại từng hộ lỗi, OCR hủy…"""
    try:
        from datetime import datetime
        from .may_chu import thu_muc_may
        p = thu_muc_may() / 'loi.log'
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'a', encoding='utf-8') as f:
            f.write('==== %s\n%s\n\n' % (datetime.now().strftime('%d/%m/%Y %H:%M:%S'), (chu or '').rstrip()))
    except OSError:
        pass


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


MAU_BANG = ('#0B192C', '#1E3A5F', '#0F766E')   # banner: xanh sapphire
VIEN_DAY = '#38BDF8'                           # viền đáy banner, 2px
MAU_PHU_DE = '#E0F2FE'                         # dòng cơ quan: xanh băng trắng sáng
MAU_DON_VI_BANNER = '#FCD34D'                  # 0.9.80: tên đơn vị trên banner navy - vàng kim nhạt (đọc rõ hơn xanh băng)
VANG = TOKEN['nhan']                           # điểm nhấn nút (không còn tô dòng cơ quan)
QSS_CHIP = (
    'background: rgba(15, 23, 42, 0.45); border: 1px solid rgba(148, 163, 184, 0.25); '
    'border-radius: 8px; padding: 1px 8px; font-size: 11px; font-weight: 500;')
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


RONG_THE_CHAO_TOI_THIEU = 168                           # thẻ bắt đầu co tới đây khi cửa sổ hẹp (không chồng lên nhau)


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


# ---------------------------------------------------------------- 1.0.03: thẻ KPI 2 tầng + dải cộng chân bảng (trang nhúng)
CAO_THE_KPI_GON = 60       # 1.0.34: 54 -> 60 (thanh tiến độ 5 px dưới số)
MAU_SO_THE = '#0F172A'      # số trên mọi thẻ số liệu (22/10/2026): một màu; màu riêng của thẻ chỉ ở vạch trái / thanh tiến độ
# 1.0.34: kiểu thẻ ở bảng kiểu CHUNG (đổi theo tông nền, kể cả Tối); riêng mỗi thẻ chỉ màu vạch trái
QSS_THE_KPI_GON_CHUNG = '''
    QFrame#the_kpi_gon { background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 3px solid #2563EB; border-radius: 6px;
        border-top-left-radius: 3px; border-bottom-left-radius: 3px; }
    QFrame#the_kpi_gon:hover { border-color: #CBD5E1; }
    QFrame#the_kpi_gon QLabel { background: transparent; border: 0; }
    QLabel#kpi_ten { color: #475569; font-size: 12px; font-weight: 600; }
    QLabel#kpi_so { color: ''' + MAU_SO_THE + '''; font-family: "Segoe UI"; font-size: 16px; font-weight: 700; }
    QLabel#kpi_phu { color: #64748B; font-size: 12px; }'''
QSS_THE_KPI_GON = 'QFrame#the_kpi_gon {{ border-left-color: {m}; }}'
MAU_KPI_TONG_QUAN = ('#2563EB', '#059669', '#0D9488', '#D97706')    # 4 thẻ màn hình Tổng quan (man_hinh_tong_quan.MAU_KPI)


def _sang_hon(mau: str, he: float = 0.35) -> str:
    """Màu sáng hơn (pha trắng) cho đầu cuối gradient thanh tiến độ."""
    c = QColor(mau)
    return QColor(int(c.red() + (255 - c.red()) * he), int(c.green() + (255 - c.green()) * he),
                  int(c.blue() + (255 - c.blue()) * he)).name().upper()


def tao_thanh_tien_do(mau: str):
    """Thanh tiến độ mảnh 5 px (QProgressBar không chữ) màu gradient theo thẻ - property vai="thanh_tien_do", mau=<màu>."""
    from PySide6.QtWidgets import QProgressBar
    t = QProgressBar()
    t.setRange(0, 100)
    t.setTextVisible(False)
    t.setFixedHeight(5)
    t.setProperty('vai', 'thanh_tien_do')
    t.setProperty('mau', mau.upper())
    t.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    return t
CAO_DAI_CONG_BANG = 32
QSS_DAI_CONG_BANG = ('QFrame#dai_cong_bang { background: #F1F5F9; border: 1px solid #DCE3EA; border-top: 2px solid #CBD5E1; '
                     'border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; }'
                     'QFrame#dai_cong_bang QLabel { background: transparent; border: 0; color: #0F172A; }')


class TheKpiGon(QFrame):
    """Thẻ chỉ số 2 tầng cao 54 px (cùng kiểu thẻ số màn hình chính / Niêm yết): tên trên; số lớn + chữ phụ dưới. Vạch trái 3 px
    màu `mau`, góc trái bo 3 px (vạch thẳng). Chữ dài rút "…", đủ ở chú thích."""

    def __init__(self, ten: str, mau: str = '#1E3A5F', goi_y: str = ''):
        super().__init__()
        self.setObjectName('the_kpi_gon')
        dat_kieu_theo_tong(self, QSS_THE_KPI_GON.format(m=mau))
        do_bong(self, 14, 2, 26)
        self.setFixedHeight(CAO_THE_KPI_GON)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(10, 6, 10, 6)
        lo.setSpacing(2)
        self.lb_ten = NhanRutGon(ten)
        self.lb_ten.setObjectName('kpi_ten')
        self.lb_so = NhanRutGon('—')
        self.lb_so.setObjectName('kpi_so')
        self.lb_phu = NhanRutGon('')
        self.lb_phu.setObjectName('kpi_phu')
        self.lb_phu.setMinimumWidth(0)
        lo.addWidget(self.lb_ten)
        duoi = QHBoxLayout()
        duoi.setSpacing(6)
        duoi.addWidget(self.lb_so, 3)
        duoi.addWidget(self.lb_phu, 2, Qt.AlignmentFlag.AlignBottom)
        lo.addLayout(duoi)
        self.thanh_tien_do = tao_thanh_tien_do(mau)  # 1.0.34: chỉ hiện khi dat(..., tien_do=) có tỷ lệ
        self.thanh_tien_do.setVisible(False)
        lo.addWidget(self.thanh_tien_do)
        self._goi_y = goi_y
        self.setToolTip(goi_y or ten)

    def dat(self, so: str, phu: str = '', goi_y: str = '', tien_do=None) -> None:
        """tien_do: tỷ lệ hoàn thành 0-100 (None: ẩn thanh tiến độ)."""
        if tien_do is None:
            self.thanh_tien_do.setVisible(False)
        else:
            self.thanh_tien_do.setValue(max(0, min(100, int(round(float(tien_do))))))
            self.thanh_tien_do.setVisible(True)
        self.lb_so.setText(so)
        self.lb_phu.setText(phu)
        self.lb_phu.setVisible(bool(phu))
        dau = goi_y or self._goi_y
        self.setToolTip((dau + '\n' if dau else '') + f'{self.lb_ten.text()}: {so}' + (f' · {phu}' if phu else ''))


class HangKpi(QWidget):
    """Hàng thẻ KPI: ds = [(khóa, tên, màu vạch)] -> self.the[khóa] = TheKpiGon."""

    def __init__(self, ds: list, parent=None):
        super().__init__(parent)
        self.setObjectName('hang_kpi')
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(8)
        self.the = {}
        for k, ten, mau, *goi_y in ds:
            t = TheKpiGon(ten, mau, goi_y[0] if goi_y else '')
            self.the[k] = t
            lo.addWidget(t, 1)
        self.setFixedHeight(CAO_THE_KPI_GON)

    def dat(self, khoa: str, so: str, phu: str = '', goi_y: str = '', tien_do=None) -> None:
        self.the[khoa].dat(so, phu, goi_y, tien_do)


class DaiCongBang(QFrame):
    """Dải cộng chân bảng cao 32 px (nền slate, vạch trên 2 px): các phần "nhãn: số" cách "·", phần TỔNG navy đậm ở cuối. Bề rộng
    Ignored - chữ dài không đẩy cửa sổ rộng ra; hẹp thì dùng chữ gọn (nếu có), đủ số ở chú thích."""

    def __init__(self, ten: str = 'dai_cong_bang'):
        super().__init__()
        self.setObjectName('dai_cong_bang')
        self.setProperty('ten', ten)
        dat_kieu_theo_tong(self, QSS_DAI_CONG_BANG)
        self.setFixedHeight(CAO_DAI_CONG_BANG)
        from PySide6.QtWidgets import QSizePolicy
        lo = QHBoxLayout(self)
        lo.setContentsMargins(10, 0, 10, 0)
        self.lb = QLabel('')
        self.lb.setTextFormat(Qt.TextFormat.RichText)
        self.lb.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        lo.addWidget(self.lb, 1)
        self._chu = ('', '', '')

    @staticmethod
    def _html(phan: list, tong) -> str:
        chu = '&nbsp;&nbsp;·&nbsp;&nbsp;'.join(f'<span style="color:{mau_theo_tong("#475569", "chu")}">{n}:</span> <b>{v}</b>' for n, v in phan)
        if tong:
            chu += ('&nbsp;&nbsp;|&nbsp;&nbsp;' if chu else '') + \
                f'<span style="color:{mau_theo_tong("#1E3A5F", "chu")}; font-weight:800">{tong[0]}: {tong[1]}</span>'
        return chu

    def dat(self, phan: list, tong=None, phan_gon: list | None = None, tong_gon=None) -> None:
        """phan: [(nhãn, chữ số)]; tong: (nhãn, chữ số) hoặc None; phan_gon / tong_gon: bản gọn khi hẹp (số kiểu "1,3 tỷ"). Hẹp
        nữa: chỉ phần tổng (gọn). Đủ số ở chú thích."""
        tg = tong_gon or tong
        self._chu = (self._html(phan, tong), self._html(phan_gon if phan_gon is not None else phan, tg),
                     self._html(phan_gon[:1] if phan_gon else [], tg))
        self.setToolTip('\n'.join(f'{n}: {v}' for n, v in phan) + (f'\n{tong[0]}: {tong[1]}' if tong else ''))
        self._chon()

    def text(self) -> str:
        return self.lb.text()

    def _chon(self) -> None:
        from PySide6.QtGui import QTextDocument
        doc = QTextDocument()
        doc.setDefaultFont(self.lb.font())
        rong = max(1, self.lb.width() - 4)
        for chu in self._chu:
            doc.setHtml(chu)
            if doc.idealWidth() <= rong:
                break
        self.lb.setText(chu)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._chu[0]:
            self._chon()


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
    tieu_de = NhanRutGon(to_chuc.TEN_PHAN_MEM or TEN_PHAN_MEM)
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
    phu = NhanRutGon(to_chuc.dong_phu())
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
    khung.nhan_phu.setText(phu or to_chuc.dong_phu())


def dat_ten_nut_xoa(o) -> None:
    """Nút xóa chữ (dấu x) tự có của QLineEdit là một QToolButton không tên: đặt chú thích + tên cho người dùng bàn phím / trình đọc màn hình."""
    for b in o.findChildren(QToolButton):
        if not b.toolTip():
            b.setToolTip('Xóa chữ đã gõ')
            b.setAccessibleName('Xóa chữ đã gõ')


class XepDong(QLayout):
    """Bố cục xếp nối tiếp, hết chỗ thì xuống dòng (màn hình hẹp không làm cửa sổ tràn ra ngoài)."""

    def __init__(self, parent=None, cach: int = 6):
        super().__init__(parent)
        self._muc = []
        self._cach = cach
        self._gian = set()

    def gian(self, w) -> None:
        """Khối w nhận TOÀN BỘ phần rộng còn thừa của dòng nó nằm (các khối khác giữ đúng cỡ cần) - 30/10/2026: ô Tái định cư giãn,
        nhãn các khối khác không bị kéo rộng tạo khoảng trống."""
        self._gian.add(id(w))

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
            gian = [it for it in hang if it.widget() is not None and id(it.widget()) in self._gian]
            for it, w in zip(hang, ws):
                if gian:
                    them = du // len(gian) if it in gian else 0
                else:
                    them = du * w // sum(ws) if sum(ws) else 0
                if not chi_tinh:
                    it.setGeometry(QRect(QPoint(x, y), QSize(w + them, cao)))
                x += w + them + self._cach
            y += cao + (self._cach if i < len(dong) - 1 else 0)
        return y - r.y() + m.bottom()


def mau_icon(chu: str) -> str:
    """Màu biểu tượng nút lệnh trên thanh (nút nền nhạt): màu chính của nhóm."""
    n = nhom_nut(chu)
    # 1.0.94: theo tông (tông Tối trước đây biểu tượng navy trên nền tối - 4 nút lớn màn chính, nút thanh lệnh)
    return mau_theo_tong(MAU[n][0] if n and n != 'nhat' else CHINH_GOC[0], 'chu')


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


def co_bong_do() -> bool:
    """Có vẽ bóng đổ dưới thẻ không. 1.0.34: BẬT mặc định trên màn hình thật (thẻ chào, thẻ KPI có chiều sâu) - chỉ đặt cho thẻ nhỏ,
    không đặt cho khung chứa bảng (QGraphicsDropShadowEffect làm mờ bằng CPU mỗi lần vẽ lại - cuộn bảng sẽ giật). Tắt khi: chạy không
    màn hình (kiểm thử), PABT_HIEU_UNG_BONG=0, máy cấu hình yếu (16/10/2026), bản Qt5 (Windows 7: màn hình phóng to làm mờ chữ)."""
    import os
    import pabt
    if os.environ.get('PABT_HIEU_UNG_BONG') == '0' or os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
        return False
    app = QApplication.instance()
    if app is not None and app.platformName() in ('offscreen', 'minimal'):
        return False
    return not getattr(pabt, 'QT5', False) and not la_may_yeu()


def do_bong(w: QWidget, mo: int = 18, lech: int = 3, dam: int = 38) -> QWidget:
    """Bóng đổ nhẹ dưới thẻ (co_bong_do). Trả w."""
    if co_bong_do():
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
        # 22/10/2026: rộng co được tới RONG_THE_CHAO_TOI_THIEU (cửa sổ hẹp 1366 @125%: 4 thẻ 210 px chồng lên nhau), cao cố định
        self.setMinimumWidth(RONG_THE_CHAO_TOI_THIEU)
        self.setMaximumWidth(KICH_THE_CHAO[0])
        self.setFixedHeight(KICH_THE_CHAO[1])
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        do_bong(self, 22, 3, 42)

    def sizeHint(self):
        """Đúng cỡ thiết kế khi có chỗ, chỉ co tới RONG_THE_CHAO_TOI_THIEU khi cửa sổ hẹp (trước: theo chữ, phông thật làm thẻ hẹp 168 px, tên lệnh dài bị cắt giữa chữ)."""
        return QSize(*KICH_THE_CHAO)

    def dat_noi_dung(self, nut: QToolButton, phu: str, chu: str = '') -> QLabel:
        """Xếp nút lệnh (biểu tượng trên, chữ dưới) và dòng mô tả vào thẻ; nút lấy tên #the_chao_nut (kiểu trong suốt, chữ 14,5pt đậm)
        và biểu tượng 38px màu của loại thẻ (vẽ lại khi lệnh đổi trạng thái: Qt chép biểu tượng của QAction đè lên). Trả nhãn mô tả."""
        from PySide6.QtWidgets import QSizePolicy
        self._nut = nut
        nut.setObjectName('the_chao_nut')
        nut.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        nut.setMinimumHeight(0)
        nut.setIconSize(QSize(CO_HUY_HIEU_THE_CHAO, CO_HUY_HIEU_THE_CHAO))
        a = nut.defaultAction()
        k = ky_hieu_nut(a.text()) if a is not None else None
        if chu:                                         # chữ riêng của thẻ, ngắn hơn tên lệnh ở menu
            nut.setText(chu)
        bo = MAU_THE_CHAO.get(self._loai or '', ('', '', '#EFF6FF', CHINH, CHINH))
        ic = huy_hieu_bieu_tuong(k, bo[4], bo[2], CO_HUY_HIEU_THE_CHAO) if k else None
        if ic is not None:
            nut.setIcon(ic)
            if a is not None:
                def gan_lai(nut=nut, ic=ic):
                    try:
                        nut.setIcon(ic)
                        if chu:
                            nut.setText(chu)
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
        from PySide6.QtGui import QKeySequence
        phim = a.shortcut().toString(QKeySequence.SequenceFormat.NativeText) if a is not None else ''
        self.lb_phim = None
        if phim:                                        # phím tắt THẬT của lệnh: viên thuốc góc trên phải (con của thẻ, ngoài bố cục)
            self.lb_phim = QLabel(phim, self)
            self.lb_phim.setProperty('vai', 'phim_the_chao')
            self.lb_phim.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._dat_phim()
        return lb

    def _dat_phim(self):
        if getattr(self, 'lb_phim', None) is not None:
            self.lb_phim.adjustSize()
            x = self.width() - self.lb_phim.width() - 10
            self.lb_phim.move(x, 10)
            self.lb_phim.setVisible(x >= (self.width() + CO_HUY_HIEU_THE_CHAO) // 2 + 2)     # thẻ hẹp: không đè biểu tượng; phím tắt vẫn ở chú thích

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._dat_phim()

    def mouseReleaseEvent(self, e):
        if (self._nut is not None and e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.pos())
                and self._nut.isEnabled()):
            self._nut.click()
        super().mouseReleaseEvent(e)

    def _bong(self, noi: bool):
        e = self.graphicsEffect()
        if e is not None and hasattr(e, 'setBlurRadius'):          # rê chuột: bóng sâu hơn (thẻ "nổi" lên)
            e.setBlurRadius(30 if noi else 22)
            e.setOffset(0, 6 if noi else 3)

    def enterEvent(self, e):
        self.setProperty('hover', '1')
        self.style().unpolish(self)
        self.style().polish(self)
        self._bong(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.setProperty('hover', '0')
        self.style().unpolish(self)
        self.style().polish(self)
        self._bong(False)
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
CAO_BANNER = 42        # banner xanh: tên phần mềm + cơ quan canh giữa theo chiều dọc (0.9.82: 60 -> 48; 17/10/2026: 42)


class KhungBanner(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        KHI_DOI_TONG_NEN.append(lambda _t: self.update())          # đổi tông: vẽ lại dải màu của tông mới

    """Banner tên phần mềm (1.0.34): dải chuyển màu ba tầng MAU_BANG (đêm sâu -> Royal Sapphire -> teal), lưới tọa độ trắc địa mờ,
    ba vòng cung đồng mức bản đồ ở góc phải, dải sáng mép trên và viền đáy VIEN_DAY."""

    def paintEvent(self, e):
        from PySide6.QtCore import QPointF, QRectF
        from PySide6.QtGui import QLinearGradient, QPainter, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        w, h = r.width(), r.height()
        g = QLinearGradient(r.topLeft(), r.topRight())
        from . import chu_de
        for t, m in zip((0, 0.52, 1), chu_de.mau_tong(TONG_NEN[0])['banner']):
            g.setColorAt(t, QColor(m))
        p.fillRect(r, g)
        p.setPen(QPen(QColor(147, 197, 253, 22), 1))           # lưới tọa độ
        buoc = 28
        x = buoc
        while x < w:
            p.drawLine(QPointF(x, 0), QPointF(x, h))
            x += buoc
        y = buoc / 2
        while y < h:
            p.drawLine(QPointF(0, y), QPointF(w, y))
            y += buoc
        p.setPen(QPen(QColor(56, 189, 248, 34), 1.4))          # vòng cung đồng mức
        tam = QPointF(w - 40, h * 1.15)
        for i, bk in enumerate((h * 0.9, h * 1.6, h * 2.4)):
            p.drawEllipse(tam, bk * 1.6, bk)
        p.setPen(QPen(QColor(255, 255, 255, 45), 1))           # dải sáng mép trên
        p.drawLine(QPointF(0, 0.5), QPointF(w, 0.5))
        p.fillRect(QRectF(0, h - 2, w, 2), QColor(VIEN_DAY))
        p.end()


class NutDoiGiaoDien(QToolButton):
    """Nút đổi nhanh giao diện Sáng <-> Tối (1.0.34) trên banner: chữ + biểu tượng theo tông đang dùng (MDL2 mặt trăng / mặt trời -
    không emoji: Windows 7 không có phông emoji). Bấm = doi_nhanh_tong_nen (áp ngay, nhớ cho lần mở sau)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('btn_doi_giao_dien')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setFixedHeight(24)
        self.setProperty('khong_icon', True)
        self.setStyleSheet(
            'QToolButton#btn_doi_giao_dien { color: #FFFFFF; background: rgba(255,255,255,0.12); '
            'border: 1px solid rgba(255,255,255,0.32); border-radius: 10px; padding: 0 10px; font-size: 11px; font-weight: 600; }'
            'QToolButton#btn_doi_giao_dien:hover { background: rgba(255,255,255,0.24); }')
        self.clicked.connect(doi_nhanh_tong_nen)
        KHI_DOI_TONG_NEN.append(self.ve)
        self.ve(TONG_NEN[0])

    def ve(self, ten: str) -> None:
        toi = ten == 'toi'
        self.setText('Sáng' if toi else 'Tối')
        ic = icon_ky_hieu(0xE706 if toi else 0xE708, '#FFFFFF', 14)     # Brightness / QuietHours (mặt trăng)
        if ic is not None:
            self.setIcon(ic)
        self.setToolTip('Chuyển sang giao diện Sáng Sapphire' if toi else 'Chuyển sang giao diện Tối chuyên gia (Dark Studio)')


def tao_banner_ten():
    """Banner xanh dưới menu trắng. Trái: tên phần mềm + cơ quan (rút "…" khi hẹp). Phải: khung `goc_phai` KHÓA CỨNG - ô dự
    án, phiên bản, tem bản quyền (trạng thái máy đơn / LAN: chỉ ở thanh trạng thái): kích thước cố định theo nội dung, không bao giờ co / bị cắt; phần chữ bên trái
    nhường chỗ (người dùng 12/10/2026). Nút thu nhỏ / phóng to / đóng là của thanh tiêu đề Windows (cửa sổ có khung) - đừng
    đổi sang cửa sổ không khung."""
    from . import __version__, to_chuc
    from .ban_quyen import mo_ta
    from PySide6.QtWidgets import QSizePolicy
    k = KhungBanner()
    k.setObjectName('banner_ten')
    k.setFixedHeight(CAO_BANNER)
    k.setStyleSheet('#banner_ten { background: transparent; border: 0; }')     # nền, lưới, vòng cung: KhungBanner.paintEvent
    hang = QHBoxLayout(k)
    hang.setContentsMargins(18, 0, 14, 2)           # 2 px dưới = viền đáy: chữ nằm giữa phần nền xanh
    hang.setSpacing(16)
    cot = QVBoxLayout()
    cot.setSpacing(1)
    cot.setContentsMargins(0, 0, 0, 0)
    ten = NhanRutGon(to_chuc.TEN_PHAN_MEM or TEN_PHAN_MEM)    # sizePolicy Ignored: chữ dài không ép cửa sổ rộng ra
    ten.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    ten.setStyleSheet(
        'QLabel { color: #FFFFFF; font-size: 14px; font-weight: 700; letter-spacing: 0.4px; '
        'background: transparent; border: 0; }')
    co_quan = NhanRutGon(to_chuc.TEN)
    co_quan.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    co_quan.setStyleSheet(
        f'QLabel {{ color: {MAU_DON_VI_BANNER}; font-size: 11px; font-weight: 600; letter-spacing: 0.6px; '
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
    nut_gd = NutDoiGiaoDien()                         # 1.0.34: đổi nhanh Sáng <-> Tối một cú bấm
    for w in (nut_gd, phien, bq):                     # 0.9.80: bỏ "● Máy đơn" - trạng thái máy đơn / LAN chỉ ở nút nut_tk thanh trạng thái
        lo.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)
    hang.addWidget(goc, 0, Qt.AlignmentFlag.AlignVCenter)
    k.goc_phai = goc
    k.btn_doi_giao_dien = nut_gd
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
        'QMenuBar { background: #FFFFFF; color: #1E293B; font-size: 13px; font-weight: 600; border: 0; '
        'border-bottom: 1px solid #E2E8F0; padding: 0px 4px; }'
        'QMenuBar::item { background: transparent; color: #1E293B; font-size: 13px; font-weight: 600; '
        'padding: 4px 12px; margin: 0px; border-radius: 4px; }'
        'QMenuBar::item:selected { background: #F1F5F9; color: #0F172A; }'
        'QMenuBar::item:pressed { background: #E2E8F0; color: #0F172A; }')
    vua_cao_menu(mb)
    if getattr(mb, '_bam_menu', None) is None:
        mb._bam_menu = _BamMenu(mb)
    if _vua_moi_menu not in KHI_DOI_TY_LE:
        KHI_DOI_TY_LE.append(_vua_moi_menu)


_THUNG_CHO_XOA: list = []


def _thung_cho_xoa():
    """Widget ẩn, ngoài cây cửa sổ chính, chứa hộp đã gỡ tab trong lúc chờ deleteLater chạy. findChildren của tổ tiên gặp widget đang chờ xóa làm vỏ
    Python của nó sống mãi, giữ cả dữ liệu (06/11/2026: tab Bộ đơn giá rồi lệnh Đóng dự án: ~3 MB / lần, đo được; _chay_lenh gọi findChildren cuối lệnh)."""
    from PySide6.QtWidgets import QWidget
    if _THUNG_CHO_XOA:
        try:
            _THUNG_CHO_XOA[0].objectName()
            return _THUNG_CHO_XOA[0]
        except RuntimeError:                            # đã hủy (đóng mọi cửa sổ cấp cao lúc thoát / giữa các module kiểm thử)
            _THUNG_CHO_XOA.clear()
    _THUNG_CHO_XOA.append(QWidget())
    return _THUNG_CHO_XOA[0]


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
            w.hide()
            w.setParent(_thung_cho_xoa())               # xem _thung_cho_xoa: không để findChildren của cửa sổ chính gặp hộp đang chờ xóa
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
        nhan = QLabel(chu_hien(ten or ''))              # 1.0.42: Title Case, hiện & (không IN HOA)
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


def co_hoat_anh() -> bool:
    """Có chạy hoạt ảnh không (1.0.34): tắt khi chạy không màn hình (kiểm thử offscreen), máy cấu hình yếu, PABT_HOAT_ANH=0."""
    import os
    if os.environ.get('PABT_HOAT_ANH') == '0' or os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
        return False
    app = QApplication.instance()
    if app is None or app.platformName() in ('offscreen', 'minimal'):
        return False
    return not la_may_yeu()


def dat_rong_muot(w: QWidget, rong: int, thoi_luong: int | None = None) -> None:
    """Đặt bề rộng cố định của w, trượt mượt (QVariantAnimation OutCubic) khi w đang hiện và có hoạt ảnh; không thì đặt ngay."""
    from PySide6.QtCore import QEasingCurve, QVariantAnimation
    cu = getattr(w, '_hoat_anh_rong', None)
    if cu is not None:
        cu.stop()
        w._hoat_anh_rong = None
    if not co_hoat_anh() or not w.isVisible() or w.width() == rong:
        w.setFixedWidth(rong)
        return
    a = QVariantAnimation(w)
    a.setDuration(THOI_GIAN_MENU_MS if thoi_luong is None else thoi_luong)
    a.setStartValue(w.width())
    a.setEndValue(rong)
    a.setEasingCurve(QEasingCurve.Type.OutCubic)
    a.valueChanged.connect(lambda v, w=w: w.setFixedWidth(int(v)))
    a.finished.connect(lambda w=w, r=rong: w.setFixedWidth(r))
    w._hoat_anh_rong = a
    a.start()


THOI_GIAN_TRANG_MS = 160        # giữ hằng (API cũ); từ 1.0.44 không còn trượt trang
DICH_TRANG_PX = 14              # giữ tên: test / mã gọi cũ còn đọc; không dùng để move() widget trong layout


@contextmanager
def dung_ve(w: QWidget):
    """Tạm tắt vẽ widget (và con) để đổi trang / ẩn hiện hàng không bị nhấp nháy giữa chừng. Trả lại trạng thái cũ."""
    cu = w.updatesEnabled()
    w.setUpdatesEnabled(False)
    try:
        yield
    finally:
        w.setUpdatesEnabled(cu)


def chuyen_trang_muot(stack, chi_so: int, thoi_luong: int = THOI_GIAN_TRANG_MS) -> None:
    """Chuyển ô QStackedWidget ngay (setCurrentIndex).

    Trước 1.0.44: trượt widget 14 px / 160 ms bằng QWidget.move(). Widget trang nằm trong layout của QStackedWidget: layout kéo
    về chỗ cũ mỗi lần vẽ, cộng ẩn/hiện hàng thẻ số → cửa sổ nhấp nháy, cảm giác chậm khi bấm menu trái. Phản hồi tức thì
    (< 100 ms trang đã nạp) là ngưỡng tốc độ; dấu chọn menu trái đã báo trang đang xem. thoi_luong giữ chữ ký cũ, không dùng."""
    if stack.currentIndex() == chi_so:
        return
    cu = getattr(stack, '_hoat_anh_trang', None)
    if cu is not None:
        try:
            cu.stop()
        except RuntimeError:
            pass
        stack._hoat_anh_trang = None
    stack.setCurrentIndex(chi_so)


def menu_trai(nhom: list, thu_gon_luc_dau: bool = False, xo: tuple = (), dong_mac_dinh: tuple = ()) -> QFrame:
    """Khu vực lệnh dạng cột dọc bên trái (mặc định từ 0.9.3; thanh_lenh là kiểu thanh nút phía trên): nhóm có tiêu đề, mỗi lệnh một dòng (biểu tượng + chữ);
    nút "Thu gọn" chuyển sang chỉ hiện biểu tượng (rê chuột hiện tên lệnh).
    xo: tên nhóm hiện thành MỘT nút có danh sách xổ xuống (lệnh ít dùng: Dự án mới, Mở, Lưu thành…) để menu không tràn màn hình.
    Nhóm khác: bấm tiêu đề nhóm để đóng / mở; nhóm đang đóng nhớ ở QSettings (lần đầu: dong_mac_dinh)."""
    from PySide6.QtWidgets import QMenu, QScrollArea, QSizePolicy
    khung = QFrame()
    khung.setProperty('vai', 'menu_trai')                    # Hybrid Enterprise Navy (17/10/2026): nền #F8FAFC, viền phải - QSS_MENU_TRAI
    ngoai = QVBoxLayout(khung)
    ngoai.setContentsMargins(0, 0, 1, 0)                     # 1 px phải = viền phải của khung
    ngoai.setSpacing(0)
    # nút Thu gọn ở HÀNG RIÊNG trên đỉnh, ngoài vùng cuộn (người dùng 17/10/2026: nút đè lên tiêu đề nhóm đầu) - xếp trong bố cục,
    # không đặt tọa độ nổi; vạch ngăn dưới hàng
    hang_gon = QFrame()
    hang_gon.setObjectName('hang_gon_menu')
    hang_gon.setFixedHeight(CAO_HANG_GON)
    hg = QHBoxLayout(hang_gon)
    hg.setContentsMargins(4, 0, 4, 1)                        # 1 px dưới = vạch ngăn
    hg.setSpacing(0)
    b_gon = QToolButton()
    b_gon.setObjectName('nut_thu_gon')
    b_gon.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    b_gon.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    b_gon.setFixedHeight(CAO_HANG_GON - 5)
    b_gon.setCursor(Qt.CursorShape.PointingHandCursor)
    hg.addWidget(b_gon)
    ngoai.addWidget(hang_gon)
    cuon = QScrollArea()
    cuon.setObjectName('cuon_menu')
    cuon.setWidgetResizable(True)
    cuon.setFrameShape(QFrame.Shape.NoFrame)
    cuon.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    cuon.viewport().setAutoFillBackground(False)
    trong = QWidget()
    trong.setObjectName('menu_trong')
    # có bộ chọn: kiểu không có bộ chọn bị truyền sang ô gợi ý (tooltip) của các nút con -> ô gợi ý nền đen
    trong.setStyleSheet('QWidget#menu_trong { background: transparent; }')
    lo = QVBoxLayout(trong)
    lo.setContentsMargins(4, 2, 4, 6)
    lo.setSpacing(2)
    nut, tieu_de = [], []                                    # tieu_de: (nút tiêu đề nhóm, tên nhóm, [nút lệnh của nhóm])
    bieu_tuong = []                                          # (QAction, ký hiệu): tô lại biểu tượng khi đổi tông (1.0.35)
    dong = _doc_nhom_dong(dong_mac_dinh)

    def nut_menu(a) -> QToolButton:
        mm = mau_menu()
        b = nut_lenh(a, 18, mau=mm['icon'])                 # icon đơn sắc theo tông, mục đang chọn đổi màu (icon_hai_trang_thai)
        k = ky_hieu_nut(a.text())
        ic = icon_hai_trang_thai(k, mm['icon'], mm['icon_chon'], 18) if k else None
        if k:
            bieu_tuong.append((a, k))
        if ic is not None:
            a.setIcon(ic)
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
        b.setMaximumHeight(CAO_NUT_MENU)
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
            lo.addWidget(vach)
            continue
        if ten in xo:                                        # một nút, bấm xổ danh sách lệnh của nhóm
            b = QToolButton()
            # nổi bật (nền xanh đậm như băng tiêu đề, vạch vàng, chữ trắng): nơi mở / tạo / lưu dự án - người dùng hay tìm
            b.setText(f'{chu_hien(ten)}   ▾')
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
            t.setText(('▸' if d else '▾') + ('' if khung.thu_gon else '  ' + ten))
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
        dat_rong_muot(khung, RONG_MENU_GON if gon else khung.rong_mo())
        b_gon.setText('' if gon else '  Thu gọn menu')
        ic = icon_ky_hieu(0xE76C if gon else 0xE76B, mau_menu()['icon'], 16)    # mũi tên mở rộng / thu gọn
        b_gon.setIcon(ic) if ic is not None else b_gon.setText('»' if gon else '«  Thu gọn menu')
        b_gon.setToolTip('Mở rộng menu' if gon else 'Thu gọn menu (chỉ hiện biểu tượng)')
    def rong_mo() -> int:
        """Bề rộng menu mở: RONG_MENU_TRAI, nới theo lệnh dài nhất (chữ đo theo phông / tỷ lệ phóng to hiện tại), tối đa
        RONG_MENU_TOI_DA - không cắt chữ lệnh."""
        can = max([b.sizeHint().width() for b in nut if b.toolButtonStyle() != Qt.ToolButtonStyle.ToolButtonIconOnly] or [0])
        return min(max(RONG_MENU_TRAI, can + 8 + 10 + 2 * LE_VIEN_MENU), RONG_MENU_TOI_DA)   # lề 2 x 4 + thanh cuộn + lề viên thuốc
    khung.rong_mo = rong_mo
    khung._vua_rong = _VuaRongMenu(khung)
    khung.installEventFilter(khung._vua_rong)
    b_gon.clicked.connect(lambda: dat(not khung.thu_gon))
    khung.dat_thu_gon = dat                                  # 1.0.16: app tự thu gọn / mở lại menu theo trang (màn hình hẹp)

    def to_lai(_ten=None):
        mm = mau_menu()
        for a, k in bieu_tuong:
            ic = icon_hai_trang_thai(k, mm['icon'], mm['icon_chon'], 18)
            if ic is not None:
                a.setIcon(ic)
        dat(khung.thu_gon)                                  # mũi tên thu gọn
    khung.to_lai_bieu_tuong = to_lai
    KHI_DOI_TONG_NEN.append(to_lai)
    khung.nut_thu_gon, khung.hang_gon, khung.vung_cuon = b_gon, hang_gon, cuon
    dat(thu_gon_luc_dau)
    return khung



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


RONG_GIAN_TOI_THIEU = 150       # cột giãn (Stretch) không bóp dưới mức này (22/10/2026 - cột "Vị trí" mục 1 từng còn ~40 px)


class _GiuCotGian(QObject):
    """Bảng có cột giãn: khi các cột cố định (đã nới theo chữ tiêu đề) chiếm gần hết bề rộng, Qt bóp cột giãn tới mức tối thiểu
    của tiêu đề -> chữ nát. Thiếu chỗ thì cột giãn chuyển Interactive với bề rộng RONG_GIAN_TOI_THIEU (bảng cuộn ngang); đủ chỗ
    thì lại Stretch."""

    def __init__(self, bang, cot: list, toi_thieu: int):
        super().__init__(bang)
        self.bang, self.cot, self.toi_thieu = bang, list(cot), toi_thieu
        self._dang = False
        bang.viewport().installEventFilter(self)

    def ap(self) -> None:
        from PySide6.QtWidgets import QHeaderView
        if self._dang or not self.cot or not self.bang.isVisible():
            return                                      # chưa hiện: bề rộng chưa đúng - giữ Stretch, đo lại khi hiện / đổi cỡ
        self._dang = True
        try:
            b, hd = self.bang, self.bang.horizontalHeader()
            co_dinh = sum(b.columnWidth(c) for c in range(b.columnCount()) if c not in self.cot and not b.isColumnHidden(c))
            # bề rộng nhìn thấy của bảng (không trừ thanh cuộn dọc - tránh dao động khi thanh cuộn hiện / ẩn)
            con = b.width() - b.verticalHeader().width() - 2 * b.frameWidth() - co_dinh
            du = con >= self.toi_thieu * len(self.cot) + 24
            for c in self.cot:
                mode = QHeaderView.ResizeMode.Stretch if du else QHeaderView.ResizeMode.Interactive
                if hd.sectionResizeMode(c) != mode:
                    hd.setSectionResizeMode(c, mode)
                    if not du:
                        b.setColumnWidth(c, self.toi_thieu)
        finally:
            self._dang = False

    def eventFilter(self, o, e):
        if e.type() == QEvent.Type.Resize:
            self.ap()
        return False


def giu_cot_gian(bang, cot=None, toi_thieu: int = RONG_GIAN_TOI_THIEU):
    """Gắn _GiuCotGian cho bảng: cot = các cột giãn (None: mọi cột đang Stretch). Trả bộ giữ (gọi .ap() sau khi đổi bề rộng cột)."""
    from PySide6.QtWidgets import QHeaderView
    hd = bang.horizontalHeader()
    if cot is None:
        cot = [c for c in range(bang.columnCount()) if hd.sectionResizeMode(c) == QHeaderView.ResizeMode.Stretch]
    g = _GiuCotGian(bang, cot, toi_thieu)
    g.ap()
    return g


class _VuaRongMenu(QObject):
    """Đo lại bề rộng menu trái khi hiện / đổi kiểu / đổi phông (phóng to): sizeHint của nút chỉ đúng sau khi áp QSS."""

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.Type.Show, QEvent.Type.StyleChange, QEvent.Type.FontChange) and not getattr(obj, 'thu_gon', True):
            w = obj.rong_mo()
            if obj.width() != w:
                obj.setFixedWidth(w)
        return False


# ---------------------------------------------------------------- 1.0.03: hiển thị bảng kiểu Enterprise Financial Desktop
# Viên thuốc (pill badge) cho ô trạng thái / ý kiến / nhóm vướng: (mẫu trên chữ đã bỏ dấu, (nền, viền, chữ)) - xét theo thứ tự.
# "chua dong thuan" / "khong dong y" trước "dong thuan" / "dong y"; "tu lap" trước "da lap"; ô có "chua" mà không khớp mẫu nào -> xám.
# 1.0.93 (người dùng 10/11/2026 chọn hệ màu 4 nhóm): chưa làm = trung tính, đang xử lý = thông tin (xanh dương), cần chú ý = cảnh báo (vàng),
# xong = thành công (xanh lục); đỏ chỉ cho trường hợp chặn (không đồng ý, cưỡng chế). Chữ đạt 4,5:1 trên nền viên thuốc; tông Tối đổi qua TOI_*.
_VT_DO, _VT_TRUNG, _VT_DANG = ('#FEF2F2', '#FECACA', '#B91C1C'), ('#F1F5F9', '#E2E8F0', '#475569'), ('#EFF6FF', '#BFDBFE', '#1D4ED8')
_VT_CHU_Y, _VT_XONG = ('#FFFBEB', '#FDE68A', '#9A5A12'), ('#ECFDF5', '#A7F3D0', '#047857')
MAU_VIEN_THUOC = (
    (('khong dong y', 'cuong che'), _VT_DO),
    (('chua dong thuan', 'chua danh dau', 'chua lay y kien'), _VT_TRUNG),
    (('da trinh tham dinh', 'da trinh'), _VT_DANG),
    (('da niem yet', 'lay y kien'), _VT_DANG),
    (('da ban giao', 'hoan thanh', 'hoan tat', 'dong thuan', 'dong y', 'du dieu kien'), _VT_XONG),
    (('da chi tra', 'da nhan tien', 'da phe duyet'), _VT_XONG),
    (('tu lap', 'y kien khac', 'v1', 'v2', 'v3', 'v4', 'v5', 'dang van dong'), _VT_CHU_Y),
    (('da lap',), _VT_DANG),
)
MAU_VIEN_THUOC_XAM = _VT_TRUNG
CAO_VIEN_THUOC = 22             # chiều cao viên thuốc (px, kẹp theo chiều cao dòng)
BO_VIEN_THUOC = 10
LE_VIEN_THUOC = 8               # lề ngang trong viên thuốc
DAU_THANH_NAC = '■□'            # ô Trạng thái danh sách hộ bắt đầu bằng thanh 6 nấc "■■□□□□"
MAU_THANH_TY_LE = '#1F76A6'
MAU_RANH_TY_LE = '#E2E8F0'
_RE_SO_TY_LE = re.compile(r'-?\d+(?:[.,]\d+)?')
_RE_NHOM_VUONG = re.compile(r'^v\d$')


def mau_vien_thuoc(chu: str) -> tuple:
    """(nền, viền, chữ) của viên thuốc theo nội dung ô (bỏ dấu, không phân biệt hoa thường)."""
    t = bo_dau(chu or '')
    for mau, bo in MAU_VIEN_THUOC:
        for m in mau:
            if _RE_NHOM_VUONG.match(m):                  # "v1".."v5": đứng riêng (không khớp chữ trong từ khác)
                if re.search(r'(^|\W)' + m + r'(\W|$)', t):
                    return bo
            elif m in t:
                return bo
    return MAU_VIEN_THUOC_XAM


def so_ty_le(chu: str):
    """Số phần trăm trong chữ ô ("50,0%", "2,5", "102,5") -> float; không có số: None."""
    m = _RE_SO_TY_LE.search(chu or '')
    if m is None:
        return None
    try:
        return float(m.group(0).replace(',', '.'))
    except ValueError:
        return None


class VeOBangChuyenNghiep(QStyledItemDelegate):
    """Vẽ ô bảng bằng QPainter, KHÔNG đổi dữ liệu của mô hình (text() / DisplayRole giữ nguyên - kiểm thử đọc chữ như cũ).
    kieu='vien_thuoc': chữ trong khung viên thuốc bo tròn, màu theo nội dung (MAU_VIEN_THUOC); ô bắt đầu bằng thanh nấc "■■□□□□" (danh
    sách hộ) vẽ từng vạch tiến độ nhỏ trước viên thuốc; ký hiệu "●" đầu chữ (ý kiến) bỏ - màu đã nói lên loại. Ô trống: vẽ như thường.
    kieu='ty_le': vẽ như thường + thanh tỷ trọng mảnh (cao 3 px) sát mép dưới, dài theo min(100, số %) của ô."""

    def __init__(self, parent=None, kieu: str = 'vien_thuoc', mau_thanh: str = MAU_THANH_TY_LE):
        super().__init__(parent)
        self.kieu = kieu
        self.mau_thanh = QColor(mau_thanh)
        self._mau = {}                   # nhớ QColor theo mã màu (paint gọi mỗi ô mỗi lần vẽ)

    def _c(self, m: str) -> QColor:
        c = self._mau.get(m)
        if c is None:
            c = self._mau[m] = QColor(m)
        return c

    def paint(self, p, option, index):
        if self.kieu == 'ty_le':
            super().paint(p, option, index)
            v = so_ty_le(index.data(Qt.ItemDataRole.DisplayRole))
            if v is None:
                return
            r = option.rect.adjusted(6, 0, -6, 0)
            if r.width() < 8:
                return
            from PySide6.QtCore import QRectF
            ranh = QRectF(r.left(), r.bottom() - 4, r.width(), 3)
            p.save()
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._c(MAU_RANH_TY_LE))
            p.drawRoundedRect(ranh, 1.5, 1.5)
            dai = ranh.width() * max(0.0, min(100.0, v)) / 100.0
            if dai > 0:
                p.setBrush(self.mau_thanh)
                p.drawRoundedRect(QRectF(ranh.left(), ranh.top(), dai, 3), 1.5, 1.5)
            p.restore()
            return
        from PySide6.QtWidgets import QStyle, QStyleOptionViewItem
        o = QStyleOptionViewItem(option)
        self.initStyleOption(o, index)
        chu = (o.text or '').strip()
        if not chu:
            super().paint(p, option, index)
            return
        nac = ''
        while chu and chu[0] in DAU_THANH_NAC:
            nac += chu[0]
            chu = chu[1:]
        chu = chu.lstrip('● ').strip() if chu.startswith('●') else chu.strip()
        o.text = ''                                         # nền ô, dòng chọn, tiêu điểm: do kiểu Qt vẽ như mọi ô
        w = option.widget
        st = w.style() if w is not None else QApplication.style()
        st.drawControl(QStyle.ControlElement.CE_ItemViewItem, o, p, w)
        nen, vien, mau_chu = mau_vien_thuoc(chu)
        # 1.0.93: đổi theo tông lúc vẽ (trước đây tông Tối vẫn viên thuốc nền sáng - cùng lớp lỗi ô Thành tiền)
        nen, vien, mau_chu = mau_theo_tong(nen, 'nen'), mau_theo_tong(vien, 'vien'), mau_theo_tong(mau_chu, 'chu')
        r = option.rect
        fm = o.fontMetrics
        x = r.left() + 6
        from PySide6.QtCore import QRectF
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if nac:                                             # vạch tiến độ (6 nấc): đã qua = màu chữ viên thuốc, chưa = xám nhạt
            cao_v = min(12, r.height() - 8)
            y_v = r.top() + (r.height() - cao_v) / 2
            p.setPen(Qt.PenStyle.NoPen)
            for k in nac:
                p.setBrush(self._c(mau_chu if k == '■' else mau_theo_tong('#CBD5E1', 'vien')))
                p.drawRoundedRect(QRectF(x, y_v, 4, cao_v), 1.5, 1.5)
                x += 6
            x += 4
        cao = min(CAO_VIEN_THUOC, r.height() - 4)
        rong_toi_da = r.right() - 4 - x
        if rong_toi_da > 2 * LE_VIEN_THUOC + 8 and chu:
            chu_ve = fm.elidedText(chu, Qt.TextElideMode.ElideRight, rong_toi_da - 2 * LE_VIEN_THUOC)
            rong = fm.horizontalAdvance(chu_ve) + 2 * LE_VIEN_THUOC
            khung = QRectF(x + 0.5, r.top() + (r.height() - cao) / 2 + 0.5, rong - 1, cao - 1)
            p.setPen(self._c(vien))
            p.setBrush(self._c(nen))
            bo = min(BO_VIEN_THUOC, cao / 2)
            p.drawRoundedRect(khung, bo, bo)
            f = QFont(o.font)
            f.setWeight(QFont.Weight.DemiBold)
            p.setFont(f)
            p.setPen(self._c(mau_chu))
            p.drawText(khung, int(Qt.AlignmentFlag.AlignCenter), chu_ve)
        p.restore()

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        if self.kieu == 'vien_thuoc':
            s.setWidth(s.width() + 2 * LE_VIEN_THUOC + 8)
        return s


def gan_vien_thuoc(bang, *cot: int) -> VeOBangChuyenNghiep:
    """Gắn delegate viên thuốc cho các cột (giữ đối tượng trên bảng - PySide không giữ delegate)."""
    d = VeOBangChuyenNghiep(bang, 'vien_thuoc')
    for c in cot:
        bang.setItemDelegateForColumn(c, d)
    bang._ve_vien_thuoc = d
    return d


def gan_thanh_ty_le(bang, *cot: int, mau: str = MAU_THANH_TY_LE) -> VeOBangChuyenNghiep:
    """Gắn delegate thanh tỷ trọng cho các cột tỷ lệ %."""
    d = VeOBangChuyenNghiep(bang, 'ty_le', mau)
    for c in cot:
        bang.setItemDelegateForColumn(c, d)
    bang._ve_ty_le = d
    return d


CO_MINH_HOA = 72                 # hình minh họa khi bảng trống (1.0.34)
CAO_TOI_THIEU_MINH_HOA = 180     # vùng bảng thấp hơn: chỉ lời hướng dẫn


class _ChuKhiTrong(QWidget):
    """Lớp phủ trong suốt (không nhận chuột) trên viewport của bảng: vẽ lời hướng dẫn giữa vùng trắng khi bảng chưa có dòng."""

    def __init__(self, bang, chu_chinh: str, chu_phu: str = ''):
        super().__init__(bang.viewport())
        self.bang, self.chu_chinh, self.chu_phu = bang, chu_chinh, chu_phu
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setObjectName('chu_khi_trong')
        self.hide()

    def cap_nhat(self, *_):
        """Slot nối với tín hiệu mô hình (đổi số dòng). Là phương thức của QObject: bảng / lớp phủ bị hủy thì Qt tự ngắt - lambda giữ
        bảng làm lỗi "already deleted" khi mô hình phát rowsRemoved lúc bảng đang bị hủy."""
        try:
            cap_nhat_chu_khi_trong(self.bang)
        except RuntimeError:
            pass

    def paintEvent(self, e):
        from PySide6.QtGui import QPainter
        p = QPainter(self)
        r = self.rect()
        f = QFont(self.font())
        f.setPixelSize(13)
        f.setBold(True)
        f2 = QFont(self.font())
        f2.setPixelSize(12)
        from PySide6.QtGui import QFontMetrics
        h1 = QFontMetrics(f).lineSpacing()
        h2 = QFontMetrics(f2).lineSpacing() * (1 + self.chu_phu.count('\n')) if self.chu_phu else 0
        hinh = None
        if r.height() >= CAO_TOI_THIEU_MINH_HOA:                 # 1.0.34: hình minh họa vector phía trên lời hướng dẫn
            from .ve_bieu_tuong import ve_minh_hoa_trong
            hinh = ve_minh_hoa_trong(getattr(self, 'loai', 'bang'), CO_MINH_HOA)
        cao_hinh = CO_MINH_HOA + 8 if hinh is not None else 0
        y = r.center().y() - (cao_hinh + h1 + (h2 + 4 if h2 else 0)) // 2
        if hinh is not None:
            p.drawPixmap(r.center().x() - CO_MINH_HOA // 2, y, hinh)
            y += cao_hinh
        p.setFont(f)
        p.setPen(qmau_theo_tong('#64748B', 'chu'))           # 1.0.93: đổi theo tông
        p.drawText(QRect(r.left() + 12, y, r.width() - 24, h1), int(Qt.AlignmentFlag.AlignCenter), self.chu_chinh)
        if self.chu_phu:
            p.setFont(f2)
            p.setPen(qmau_theo_tong('#64748B', 'chu'))       # 1.0.93: #94A3B8 chỉ 2,6:1 trên nền sáng
            p.drawText(QRect(r.left() + 12, y + h1 + 4, r.width() - 24, h2),
                       int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop) | int(Qt.TextFlag.TextWordWrap), self.chu_phu)
        p.end()


class _TheoDoiTrong(QObject):
    """Bộ lọc sự kiện trên viewport (Resize / Show / Paint): đặt cỡ lớp phủ và hiện khi bảng trống."""

    def __init__(self, phu):
        super().__init__(phu)
        self.phu = phu

    def eventFilter(self, obj, e):
        t = e.type()
        if t in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Paint):
            try:
                cap_nhat_chu_khi_trong(self.phu.bang)
            except RuntimeError:
                pass
        return False


def _so_dong_bang(bang) -> int:
    m = bang.model()
    return m.rowCount() if m is not None else 0


def cap_nhat_chu_khi_trong(bang) -> None:
    phu = getattr(bang, '_chu_khi_trong', None)
    if phu is None:
        return
    trong = _so_dong_bang(bang) == 0
    if trong:
        vp = bang.viewport()
        if phu.geometry() != vp.rect():
            phu.setGeometry(vp.rect())
    if phu.isVisibleTo(bang.viewport()) != trong:
        phu.setVisible(trong)


def gan_chu_khi_trong(bang, chu_chinh: str, chu_phu: str = '', loai: str = 'bang') -> QWidget:
    """1.0.03: bảng chưa có dòng nào hiện lời hướng dẫn nhẹ giữa vùng trắng (chữ chính 13 px đậm #64748B, chữ phụ 12 px #94A3B8).
    Lớp phủ trong suốt với chuột trên viewport; theo dõi số dòng qua tín hiệu của mô hình + bộ lọc sự kiện (Resize / Show / Paint)
    của viewport. Gọi lại: chỉ đổi chữ."""
    phu = getattr(bang, '_chu_khi_trong', None)
    if phu is not None:
        phu.chu_chinh, phu.chu_phu, phu.loai = chu_chinh, chu_phu, loai
        phu.update()
        cap_nhat_chu_khi_trong(bang)
        return phu
    phu = _ChuKhiTrong(bang, chu_chinh, chu_phu)
    phu.loai = loai                                     # 1.0.34: hình minh họa ve_bieu_tuong.ve_minh_hoa_trong
    bang._chu_khi_trong = phu
    loc = _TheoDoiTrong(phu)
    bang.viewport().installEventFilter(loc)
    m = bang.model()
    if m is not None:
        for ten in ('rowsInserted', 'rowsRemoved', 'modelReset', 'layoutChanged'):
            getattr(m, ten).connect(phu.cap_nhat)
    cap_nhat_chu_khi_trong(bang)
    return phu


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


def vi_tri_danh_sach_noi(o: QWidget, rong: int, cao: int) -> tuple:
    """1.0.51: vị trí danh sách gợi ý nổi dưới ô nhập `o` -> (x, (y, cao)): không tràn khỏi vùng làm việc (màn hình 1366 x 768 @125% chỉ
    ~600 điểm cao - ô ở gần đáy thì danh sách bị thanh tác vụ che). Dưới không đủ chỗ: lật lên trên ô nếu trên rộng hơn, rồi co vừa chỗ."""
    goc = o.mapToGlobal(o.rect().bottomLeft())
    man = o.screen() or QApplication.primaryScreen()
    if man is None:
        return goc.x(), (goc.y(), cao)
    vung = man.availableGeometry()
    duoi = vung.bottom() - goc.y() - 4
    tren = goc.y() - o.height() - vung.top() - 4
    x = min(max(goc.x(), vung.left()), max(vung.left(), vung.right() - rong))
    if cao <= duoi or duoi >= tren:
        return x, (goc.y(), max(60, min(cao, duoi)))
    cao = max(60, min(cao, tren))
    return x, (goc.y() - o.height() - cao, cao)


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


RONG_NUT_XO, CAO_NUT_XO = 28, 30          # nút ▼ của OTimChon
QSS_O_TIM_CHON = '''
    QWidget[o_tim_chon="1"] QLineEdit, QWidget[hang_nhap="1"] QWidget[o_tim_chon="1"] QLineEdit {
        border-top-right-radius: 0; border-bottom-right-radius: 0; border-top-left-radius: 6px; border-bottom-left-radius: 6px; }
    QToolButton#nut_xo_tim_chon { background: #FFFFFF; border: 1px solid #CBD5E1; border-left: none;
        border-top-left-radius: 0; border-bottom-left-radius: 0; border-top-right-radius: 6px; border-bottom-right-radius: 6px;
        color: #475569; padding: 0; }
    QToolButton#nut_xo_tim_chon:hover { background: #F1F5F9; border-color: #94A3B8; }
    QToolButton#nut_xo_tim_chon:pressed { background: #E2E8F0; }
    QToolButton#nut_xo_tim_chon:disabled { background: #F8FAFC; }'''


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
        self.khi_can_ds = None                      # 1.0.47: hàng nhập nhanh nạp danh mục lúc gõ / chọn, không lúc mở cửa sổ
        self._muc = []                              # [(nhãn, chữ không dấu, dữ liệu)]
        self._theo_nhan = {}
        self.o = QLineEdit()
        self.o.setPlaceholderText(goi_y)
        self.o.setClearButtonEnabled(True)
        dat_ten_nut_xoa(self.o)
        self.nut = QToolButton()
        self.nut.setText('▼')
        self.nut.setToolTip('Xem cả danh sách')
        self.nut.setAccessibleName('Xem cả danh sách')
        self.nut.setCursor(Qt.CursorShape.PointingHandCursor)
        # 1.0.03 (Ảnh 6): ô chữ + nút ▼ liền một khối như ô chọn - ô bo góc trái, nút bo góc phải, không khe; mũi tên mảnh MDL2
        self.setProperty('o_tim_chon', '1')
        self.nut.setObjectName('nut_xo_tim_chon')
        self.nut.setFixedSize(RONG_NUT_XO, CAO_NUT_XO)
        ic = icon_ky_hieu(0xE70D, '#475569', 14)
        if ic is not None:
            self.nut.setIcon(ic)
            self.nut.setText('')
        self.ds = QListWidget()
        self.ds.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.ds.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ds.setMouseTracking(True)                 # rê chuột: tô dòng dưới chuột; bánh xe / thanh cuộn dùng được
        self.ds.itemEntered.connect(self.ds.setCurrentItem)
        self.ds.setObjectName('ds_goi_y')
        dat_kieu_theo_tong(self.ds,
            'QListWidget#ds_goi_y { background: #FFFFFF; color: #1A1A1A; border: 1px solid #9FB6CC; }'
            'QListWidget#ds_goi_y::item { padding: 4px 6px; }'
            'QListWidget#ds_goi_y::item:selected { background: #DCEBFA; color: #0B2E4F; }')
        self.ds.itemClicked.connect(lambda it: self._chon_nhan(it.text()))
        self.o.textEdited.connect(self._go)
        self.o.installEventFilter(self)
        self.nut.clicked.connect(self.xem_tat_ca)
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)
        lo.addWidget(self.o, 1)
        lo.addWidget(self.nut)

    # ---------------------------------------------- danh sách
    def _dam_bao_ds(self):
        f = self.khi_can_ds
        if f is not None:
            f()

    def dat_muc(self, ds: list) -> None:
        self._ds_hien = None
        self._muc = [(nhan, bo_dau(nhan), gt) for nhan, gt in ds]
        self._theo_nhan = {nhan: gt for nhan, gt in ds}
        self.chon = None

    def loc(self, chu: str) -> list:
        """Các nhãn khớp mọi từ đã gõ (không dấu); mục bắt đầu bằng từ đầu tiên xếp trước."""
        self._dam_bao_ds()
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
        rong = max(self.width(), 640)
        x, y = vi_tri_danh_sach_noi(self.o, rong, cao)
        self.ds.resize(rong, y[1])
        self.ds.move(x, y[0])
        self.ds.show()
        self.ds.raise_()

    def _go(self, chu: str):
        self._dam_bao_ds()
        self.chon = self._theo_nhan.get(chu)
        self._hien(self.loc(chu) if chu.strip() else [])

    khi_trong = None            # bấm ▼ khi danh sách rỗng: hàm của màn hình chủ (vd: bổ sung vật nuôi); None = chỉ báo
    goi_y_trong = 'Danh mục đơn giá chưa có mục nào cho phần này: gõ tên để nhập hạng mục ngoài danh mục.'

    def xem_tat_ca(self):
        self._dam_bao_ds()
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
        self._dam_bao_ds()
        for nhan, x in self._theo_nhan.items():
            if x == gt or x is gt:
                self._chon_nhan(nhan)
                return True
        return False

    def text(self) -> str:
        return self.o.text()

    def setText(self, chu: str):
        self._dam_bao_ds()
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


# ---------------------------------------------------------------- hộp thoại cao hơn màn hình (1.0.07: laptop 1366 x 768 @ 125%)
QSS_THAN_CUON = (
    'QScrollArea#than_cuon_hop { background: transparent; border: 0; }'
    'QScrollArea#than_cuon_hop > QWidget > QWidget { background: transparent; }'
    'QScrollArea#than_cuon_hop QScrollBar:vertical { width: 6px; background: transparent; margin: 0; }'
    'QScrollArea#than_cuon_hop QScrollBar::handle:vertical { background: #CBD5E1; border-radius: 3px; min-height: 30px; }'
    'QScrollArea#than_cuon_hop QScrollBar::handle:vertical:hover { background: #94A3B8; }'
    'QScrollArea#than_cuon_hop QScrollBar::add-line:vertical, QScrollArea#than_cuon_hop QScrollBar::sub-line:vertical '
    '{ height: 0; }')
CHUA_TIEU_DE_HOP = 48           # chừa thanh tiêu đề + khung cửa sổ (px) khi so chiều cao hộp với vùng làm việc màn hình


def _co_nut(item) -> bool:
    """Mục bố cục (hàng cuối của hộp thoại) là hàng nút lệnh: có nút, không có bảng / ô chữ nhiều dòng."""
    from PySide6.QtWidgets import QAbstractButton as N, QPlainTextEdit, QTextEdit
    ds = []
    w, lo = item.widget(), item.layout()
    if w is not None:
        ds = [w, *w.findChildren(QWidget)]
    elif lo is not None:
        def gom(l):
            for i in range(l.count()):
                it = l.itemAt(i)
                if it.widget() is not None:
                    ds.extend([it.widget(), *it.widget().findChildren(QWidget)])
                elif it.layout() is not None:
                    gom(it.layout())
        gom(lo)
    return any(isinstance(x, N) for x in ds) and not any(isinstance(x, (QAbstractItemView, QTextEdit, QPlainTextEdit)) for x in ds)


def cuon_than_hop(dlg, cao_toi_da: int | None = None) -> bool:
    """Hộp thoại cao hơn vùng làm việc màn hình (cao_toi_da, mặc định theo màn hình): đưa phần thân (mọi mục bố cục trừ hàng nút cuối)
    vào QScrollArea thanh cuộn mảnh 6 px, kẹp chiều cao hộp - hàng nút lệnh luôn nằm trọn trên màn hình. Chỉ bố cục dọc có hàng nút
    ở cuối; đã làm thì không làm lại. Trả True nếu đã bọc."""
    from PySide6.QtWidgets import QBoxLayout, QScrollArea, QVBoxLayout as V
    lo = dlg.layout()
    if dlg.property('_than_cuon') or not isinstance(lo, QBoxLayout) or lo.count() < 2 \
            or lo.direction() != QBoxLayout.Direction.TopToBottom:
        return False
    if cao_toi_da is None:
        man = dlg.screen() or QApplication.primaryScreen()
        if man is None:
            return False
        cao_toi_da = man.availableGeometry().height() - CHUA_TIEU_DE_HOP
    if max(dlg.minimumSizeHint().height(), dlg.minimumHeight()) <= cao_toi_da or not _co_nut(lo.itemAt(lo.count() - 1)):
        return False
    dlg.setProperty('_than_cuon', True)
    than = QWidget()
    tv = V(than)
    tv.setContentsMargins(0, 0, 0, 0)
    tv.setSpacing(lo.spacing())
    while lo.count() > 1:
        st = lo.stretch(0)
        it = lo.takeAt(0)
        if it.widget() is not None:
            tv.addWidget(it.widget(), st, it.alignment())
        elif it.layout() is not None:
            tv.addLayout(it.layout(), st)
        else:
            tv.addItem(it)
    sc = QScrollArea()
    sc.setObjectName('than_cuon_hop')
    sc.setWidgetResizable(True)
    sc.setFrameShape(QFrame.Shape.NoFrame)
    sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    sc.setStyleSheet(QSS_THAN_CUON)
    sc.setWidget(than)
    lo.insertWidget(0, sc, 1)
    dlg.setMinimumHeight(0)
    dlg.setMaximumHeight(max(200, cao_toi_da))
    if dlg.height() > cao_toi_da:
        dlg.resize(dlg.width(), cao_toi_da)
    return True


def _nen_cuon_hop() -> bool:
    """Kiểm thử chạy offscreen (màn hình ảo 800 x 600): không tự bọc - trừ khi đặt PABT_CUON_HOP=1 (kiểm thử riêng tính năng này)."""
    import os
    if os.environ.get('PABT_CUON_HOP') == '1':
        return True
    return QApplication.platformName() != 'offscreen'


# ---------------------------------------------------------------- thông báo nổi (HUD) góc dưới phải (1.0.07)
MAU_HUD = {'tin': ('#0F172A', '#FFFFFF', '#38BDF8'), 'dat': ('#1E3A5F', '#FFFFFF', '#34D399'),
           'canh_bao': ('#78350F', '#FFFFFF', '#FBBF24')}
HUD_MS = 2200                   # thời gian hiện (ms)
LE_HUD = 18                     # cách mép phải / đáy cửa sổ (px)


class ThongBaoNoiHUD(QLabel):
    """Thông báo nổi ngắn ở góc dưới phải cửa sổ (Ctrl+S lưu, Ctrl+Z hoàn tác): tự ẩn sau HUD_MS, không nhận chuột, không lấy tiêu
    điểm bàn phím. Dùng qua thong_bao_noi(cửa sổ, chữ)."""

    def __init__(self, cha: QWidget):
        super().__init__(cha)
        self.setObjectName('thong_bao_noi')
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWordWrap(False)
        self.hide()
        self._hen = QTimer(self)
        self._hen.setSingleShot(True)
        self._hen.timeout.connect(self.hide)
        cha.installEventFilter(self)

    def hien(self, chu: str, loai: str = 'tin', ms: int = HUD_MS) -> None:
        nen, mau, vach = MAU_HUD.get(loai, MAU_HUD['tin'])
        self.setStyleSheet(f'QLabel#thong_bao_noi {{ background: {nen}; color: {mau}; border-left: 4px solid {vach}; '
                           'border-radius: 6px; padding: 9px 16px; font-size: 13px; font-weight: 600; }')
        self.setText(chu)
        self.adjustSize()
        self._dat_vi_tri()
        self.raise_()
        self.show()
        self._hen.start(max(300, int(ms)))

    def _dat_vi_tri(self) -> None:
        cha = self.parentWidget()
        if cha is None:
            return
        day = cha.height()
        sb = cha.statusBar() if hasattr(cha, 'statusBar') and callable(cha.statusBar) else None
        if sb is not None and sb.isVisible():
            day -= sb.height()
        self.move(max(0, cha.width() - self.width() - LE_HUD), max(0, day - self.height() - LE_HUD))

    def eventFilter(self, obj, ev):
        if obj is self.parentWidget() and ev.type() == QEvent.Type.Resize and self.isVisible():
            self._dat_vi_tri()
        return False


def thong_bao_noi(cua_so: QWidget | None, chu: str, loai: str = 'tin', ms: int = HUD_MS):
    """Hiện thông báo nổi trên cửa sổ cấp cao nhất chứa cua_so. Trả ThongBaoNoiHUD (None nếu không có cửa sổ)."""
    if cua_so is None:
        return None
    try:
        w = cua_so.window()
    except RuntimeError:                                # cửa sổ đã hủy
        return None
    hud = getattr(w, '_hud', None)
    try:
        if hud is None or hud.parentWidget() is not w:
            hud = ThongBaoNoiHUD(w)
            w._hud = hud
    except RuntimeError:
        hud = ThongBaoNoiHUD(w)
        w._hud = hud
    hud.hien(chu, loai, ms)
    return hud


BIEN_MAN_HINH = 32             # 05/11/2026 (CenteredResponsiveModal của đặc tả): hộp con cao / rộng tối đa = vùng làm việc - 32 px
CHUA_TIEU_DE_TOI_THIEU = 30    # khung + thanh tiêu đề của cửa sổ hệ điều hành khi chưa hiện (frameGeometry chưa biết)


def _man_hinh_mo(w: QWidget):
    """Màn hình người đang nhìn: màn hình cửa sổ cha, rồi cửa sổ đang dùng, rồi màn hình chính."""
    from PySide6.QtWidgets import QApplication
    cha = w.parentWidget()
    while cha is not None:
        try:
            if cha.isWindow() and cha.screen() is not None:
                return cha.screen()
        except RuntimeError:
            break
        cha = cha.parentWidget()
    app = QApplication.instance()
    if app is not None:
        dang = app.activeWindow()
        try:
            if dang is not None and dang is not w and dang.screen() is not None:
                return dang.screen()
        except RuntimeError:
            pass
    rieng = w.screen() if hasattr(w, 'screen') else None
    return rieng or (app.primaryScreen() if app is not None else None)


def vua_man_hinh(w: QWidget, bien: int = BIEN_MAN_HINH, giua: bool = True) -> None:
    """Cửa sổ / hộp thoại: cao và rộng tối đa = vùng làm việc của màn hình đang dùng - `bien` (32 px, tính cả khung và thanh tiêu đề -
    laptop nhỏ, phóng to 125-150% vẫn không tràn), và CANH GIỮA màn hình (giua=True). Phần thân cuộn riêng, hàng nút cố định: `cuon_than_hop`."""
    man = _man_hinh_mo(w)
    if man is None or w.isMaximized():
        return
    vung = man.availableGeometry()
    kg = w.frameGeometry().size() - w.geometry().size()
    them_r, them_c = max(0, kg.width()), max(0, kg.height())
    if them_c < CHUA_TIEU_DE_TOI_THIEU:
        them_c = CHUA_TIEU_DE_TOI_THIEU
    rong = max(200, min(w.width(), vung.width() - bien - them_r))
    cao = max(120, min(w.height(), vung.height() - bien - them_c))
    if w.minimumWidth() > rong:
        w.setMinimumWidth(rong)
    if w.minimumHeight() > cao:
        w.setMinimumHeight(cao)
    khoa_co = w.minimumSize() == w.maximumSize() and 0 < w.maximumWidth() < _QWIDGETSIZE_MAX
    if not khoa_co:
        # 1.0.90: trần = vùng làm việc của màn hình (trước = đúng cỡ lúc mở: hộp con không kéo giãn / phóng to được)
        w.setMaximumSize(max(vung.width() - bien - them_r, w.minimumWidth()), max(vung.height() - bien - them_c, w.minimumHeight()))
    if (rong, cao) != (w.width(), w.height()):
        w.resize(rong, cao)
    rong, cao = w.width(), w.height()
    if giua:
        x = vung.x() + (vung.width() - rong - them_r) // 2
        y = vung.y() + (vung.height() - cao - them_c) // 2
        x = max(vung.x(), min(x, vung.x() + vung.width() - rong - them_r))
        y = max(vung.y(), min(y, vung.y() + vung.height() - cao - them_c))
        w.move(x, y)


def hen_giua_man_hinh(w: QWidget) -> None:
    """Windows đặt lại vị trí sau sự kiện hiện (bám cửa sổ cha, lệch góc). Hẹn một nhịp, khi kích thước đã chốt, kéo về giữa."""
    def lan(hop=w):
        try:
            if hop.isVisible() and not hop.isMaximized():
                vua_man_hinh(hop)
        except RuntimeError:
            return
    QTimer.singleShot(0, lan)


# ---------------------------------------------------------------- nhập liệu bằng bàn phím trong bảng
class _PhimBang(QObject):
    """Enter ở ô đang đứng: mở sửa ô (ô tự tính: xuống ô dưới). Sửa xong bấm Enter: ghi và XUỐNG Ô DƯỚI cùng cột (như Excel - 1.0.07;
    trước: sang ô kế bên phải). Tab / Shift+Tab: sang ô kế / ô trước như bình thường."""

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
                o_duoi(b)
            return True
        return False


def o_duoi(bang) -> bool:
    """Chuyển xuống ô cùng cột của dòng hiện kế tiếp (bỏ dòng ẩn) - Enter kiểu Excel. Trả True nếu đã chuyển."""
    try:
        idx = bang.currentIndex()
    except RuntimeError:                                  # bảng đã hủy
        return False
    if not idx.isValid():
        return False
    m = bang.model()
    r = idx.row() + 1
    while r < m.rowCount() and bang.isRowHidden(r):
        r += 1
    if r >= m.rowCount():
        return False
    bang.setCurrentIndex(m.index(r, idx.column()))
    return True


def gan_enter_xuong(bang) -> None:
    """Sửa ô xong bấm Enter (ô sửa đóng với gợi ý SubmitModelCache): ghi rồi xuống ô dưới cùng cột. Gọi lại không gắn thêm."""
    from PySide6.QtWidgets import QAbstractItemDelegate
    if bang.property('_enter_xuong'):
        return
    bang.setProperty('_enter_xuong', True)
    m = bang.model()
    ds = {bang.itemDelegate()} | {bang.itemDelegateForColumn(c) for c in range(m.columnCount() if m is not None else 0)}

    def sau_khi_sua(*a):
        hint = a[1] if len(a) > 1 else QAbstractItemDelegate.EndEditHint.SubmitModelCache
        if hint == QAbstractItemDelegate.EndEditHint.SubmitModelCache:
            QTimer.singleShot(0, lambda: o_duoi(bang))
    for d in ds:
        if d is not None:
            d.closeEditor.connect(sau_khi_sua)


def dien_xuong(bang) -> int:
    """Ctrl+D kiểu Excel: chép giá trị ô TRÊN CÙNG của vùng chọn (mỗi cột) xuống các ô chọn bên dưới; chọn một ô thì chép ô ngay
    phía trên xuống. Chỉ ô sửa được (bảng chỉ xem không đổi). Trả số ô đã điền."""
    sm = bang.selectionModel()
    m = bang.model()
    if sm is None or m is None:
        return 0
    chon = [i for i in sm.selectedIndexes() if i.isValid()] or ([bang.currentIndex()] if bang.currentIndex().isValid() else [])
    theo_cot = {}
    for i in chon:
        if not bang.isRowHidden(i.row()):
            theo_cot.setdefault(i.column(), set()).add(i.row())
    viec = []
    for c, dong in theo_cot.items():
        dong = sorted(dong)
        if len(dong) == 1:
            nguon = dong[0] - 1
            while nguon >= 0 and bang.isRowHidden(nguon):
                nguon -= 1
            dich = dong
        else:
            nguon, dich = dong[0], dong[1:]
        if nguon < 0:
            continue
        j = m.index(nguon, c)
        v = m.data(j, Qt.ItemDataRole.EditRole)
        if v is None:
            v = m.data(j, Qt.ItemDataRole.DisplayRole)
        viec += [(m.index(r, c), v) for r in dich]
    n = 0
    for idx, v in viec:                                   # đọc hết giá trị trước khi ghi (bảng có thể vẽ lại dòng khi ghi)
        if idx.isValid() and idx.flags() & Qt.ItemFlag.ItemIsEditable and m.setData(idx, '' if v is None else v,
                                                                                      Qt.ItemDataRole.EditRole):
            n += 1
    return n


def nhap_bang_phim(bang) -> None:
    """Bảng nhập số liệu: dòng cao, dễ nhìn; Tab sang ngang, Enter xuống ô dưới (kiểu Excel), không cần chuột."""
    vh = bang.verticalHeader()
    vh.setMinimumSectionSize(34)
    vh.setDefaultSectionSize(36)
    bang.setTabKeyNavigation(True)
    bang._phim = _PhimBang(bang)
    bang.installEventFilter(bang._phim)
    gan_enter_xuong(bang)                               # sửa xong Enter: ghi + xuống ô dưới (1.0.07; trước: sang ô kế bên phải)


# ---------------------------------------------------------------- phóng to / thu nhỏ giao diện (màn hình độ phân giải khác nhau)
TY_LE = [1.0]                                   # tỷ lệ hiện tại (0,8 - 1,6)
KHI_DOI_TY_LE = []                              # hàm gọi lại khi đổi tỷ lệ (cập nhật nhãn "100%")
_CO_CHU_GOC = 9.5
# P1: thang cỡ chữ (px) cho mọi 'font-size' viết trong QSS - nhãn phụ / huy hiệu 11, chữ thường 12-13, tiêu đề 14-16, số / tiêu đề lớn 18.
# Không dùng cỡ lẻ (10,5 / 12,5 / 15 / 17) và chữ dưới 11 px (khó đọc trên màn hình 1366 x 768). tests/test_p1_giao_dien.py kiểm.
THANG_CO_CHU = (11, 12, 13, 14, 16, 18)


def _co_gian(qss: str, t: float) -> str:
    """Nhân các kích thước 'px' và 'pt' trong QSS (cỡ chữ, khoảng đệm, bo góc) theo tỷ lệ. 1.0.32: cả 'pt' - trước đây chữ viết
    bằng pt (thẻ màn hình chào 14,5 / 10,5 pt) không to lên khi bấm A+ trong khi chữ px và phông ứng dụng đều to lên."""
    if t == 1:
        return qss
    s = re.sub(r'(\d+(?:\.\d+)?)px', lambda m: f'{max(1, round(float(m.group(1)) * t))}px', qss)
    return re.sub(r'(?<![\w.])(\d+(?:\.\d+)?)pt\b', lambda m: f'{round(float(m.group(1)) * t, 1):g}pt', s)


def _co_gian_widget(w, t: float) -> None:
    """Kiểu riêng của từng widget (setStyleSheet có 'px'): co giãn theo tỷ lệ, giữ bản gốc để đổi tỷ lệ nhiều lần."""
    s = w.styleSheet()
    if not s or ('px' not in s and 'pt' not in s):
        return
    goc = w.property('qss_goc')
    if goc is None or w.property('qss_da') != s:          # chưa co giãn, hoặc mã vừa đặt kiểu mới
        goc = s
    moi = _co_gian(goc, t)
    w.setProperty('qss_goc', goc)
    w.setProperty('qss_da', moi)
    if moi != s:
        w.setStyleSheet(moi)


def ty_le_da_luu() -> float:
    """Tỷ lệ cỡ chữ người dùng đã chọn (A+ / A−) trong QSettings; chạy không màn hình (kiểm thử): luôn 1.0 - không đọc máy thật."""
    cd = cai_dat_nho()
    try:
        return float(cd.value('giao_dien/ty_le', 1.0) or 1.0) if cd is not None else 1.0
    except (TypeError, ValueError):
        return 1.0


def luu_ty_le(t: float) -> bool:
    """Nhớ tỷ lệ cỡ chữ cho lần mở sau; chạy không màn hình (kiểm thử): không ghi máy thật (trả False)."""
    cd = cai_dat_nho()
    if cd is None:
        return False
    cd.setValue('giao_dien/ty_le', t)
    return True


TRUOC_DOI_TY_LE = []            # 1.0.08: hàm gọi TRƯỚC khi áp kiểu mới - cửa sổ chính bỏ các trang ẩn (tạo lại khi mở tới)


def dat_ty_le(t: float, luu: bool = True) -> float:
    """Đổi tỷ lệ giao diện (cỡ chữ, khoảng đệm) cho mọi cửa sổ; luu: nhớ cho lần mở sau.
    Việc tốn nhất là Qt áp lại kiểu (QSS) cho mọi widget: tắt vẽ lại các cửa sổ trong lúc đổi (không chớp, không vẽ dở),
    bảng chỉ giãn lại dòng cho bảng đang hiện, làm sau khi đã vẽ xong (_gian_bang)."""
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    t = round(min(1.6, max(0.8, t)), 2)
    _CHO[0] = None
    if t == TY_LE[0] and app.property('pabt_ty_le') == t:
        _bao_ty_le(t)
        return t
    TY_LE[0] = t
    for ham in list(TRUOC_DOI_TY_LE):                   # 1.0.08: Qt áp lại kiểu cho MỌI widget (~1,2 ms / widget): bớt trang ẩn trước
        try:
            ham()
        except RuntimeError:                            # cửa sổ đã hủy
            TRUOC_DOI_TY_LE.remove(ham)
    if TRUOC_DOI_TY_LE:
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)     # hủy ngay các trang vừa bỏ (deleteLater), không chờ vòng sự kiện
    cua_so = [w for w in app.topLevelWidgets() if w.isVisible()]
    for w in cua_so:
        w.setUpdatesEnabled(False)
    # Qt áp lại bảng kiểu cho MỌI widget đã hiện (kể cả trang giữ trong RAM): ~0,5 ms / widget - con trỏ chờ cho người dùng biết đang
    # đổi cỡ (đo 16/10/2026: 785 widget ~0,9 s; bảng kiểu rỗng vẫn ~0,2 s - chi phí theo số widget, không theo số quy tắc)
    from PySide6.QtCore import Qt
    app.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        f = QFont(app.font())
        f.setPointSizeF(_CO_CHU_GOC * t)
        app.setFont(f)
        app.setStyleSheet(_co_gian(_qss_day_du(), t))
        for w in app.allWidgets():
            if not isinstance(w, QWidget):              # PySide có lúc trả vỏ Python cũ đã gắn lại (QSpacerItem) - bỏ qua
                continue
            if w.isVisible():
                _co_gian_widget(w, t)
            elif w.styleSheet():                       # P1: widget đang ẩn (trang / thẻ / menu chưa mở): co giãn khi nó hiện ra
                w.setProperty('qss_cho_ty_le', True)     # (_BoToMau, sự kiện Show) - mỗi setStyleSheet riêng là một lần Qt áp lại kiểu
    finally:
        for w in cua_so:
            w.setUpdatesEnabled(True)
        app.restoreOverrideCursor()
    app.setProperty('pabt_ty_le', t)
    if app.platformName() == 'offscreen':
        _gian_bang()
    else:
        QTimer.singleShot(0, _gian_bang)
    if luu:
        luu_ty_le(t)
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


def nap_o_chon(o: QComboBox, ds) -> None:
    """1.0.79: nạp QComboBox danh sách dài một lần: `ds` = [(chữ, dữ liệu, chú thích)].
    addItem từng mục + đo từng dòng của danh sách xổ tốn ~110 ms với 3.000 hộ (đo 07/11/2026), mô hình dựng sẵn + dòng cùng chiều cao 12 ms.
    Thay toàn bộ mục; ai cần giữ im tín hiệu thì tự blockSignals như trước."""
    mo_hinh = QStandardItemModel(o)
    for chu, du_lieu, chu_thich in ds:
        muc = QStandardItem(chu)
        muc.setData(du_lieu, Qt.ItemDataRole.UserRole)
        if chu_thich:
            muc.setData(chu_thich, Qt.ItemDataRole.ToolTipRole)
        mo_hinh.appendRow(muc)
    o.view().setUniformItemSizes(True)
    o.setModel(mo_hinh)


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
    from PySide6.QtWidgets import QApplication, QTableView, QTableWidget
    for w in QApplication.instance().allWidgets():
        if isinstance(w, QTableView) and w.wordWrap() and w.isVisible() and w.model() is not None \
                and w.model().rowCount() <= 1500:
            if isinstance(w, QTableWidget):
                vua_dong(w, None, None)                 # P1: đo chữ thật (không hỏi sizeHint mọi ô như resizeRowsToContents)
            else:
                w.resizeRowsToContents()


def _bao_ty_le(t: float) -> None:
    for ham in list(KHI_DOI_TY_LE):
        try:
            ham(t)
        except RuntimeError:                            # nhãn đã bị xóa cùng cửa sổ
            KHI_DOI_TY_LE.remove(ham)


_CHO = [None]                                           # tỷ lệ đang chờ áp (lăn chuột liên tục: gộp thành một lần)
_HEN = []


def phong_to(buoc: int, cho_ms: int = 150) -> float:
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
        if cha is not None and not isinstance(cha, QWidget):  # phòng vỏ Python cũ PySide trả nhầm (xem nhan_cua_o_nhap)
            continue
        if cha is not None and (cha.objectName() in ('menu_trong', 'hang_gon_menu')
                                or cha.property('vai') in ('ribbon', 'nhom_ribbon', 'menu_trai')):
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


def cai_dat_nho():
    """QSettings('PABT', 'PABT') nhớ lựa chọn của người dùng (kích thước cửa sổ con, tùy chọn xuất bản…); chạy không màn hình
    (offscreen - kiểm thử) thì None: không đọc / ghi máy thật."""
    app = QApplication.instance()
    if app is None or app.platformName() == 'offscreen':
        return None
    return QSettings('PABT', 'PABT')


def _cai_dat_cua_so():
    """QSettings nhớ kích thước cửa sổ con (cai_dat_nho)."""
    return cai_dat_nho()


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


# ---------------------------------------------------------------- sao chép ô / dòng trên MỌI bảng (1.0.04 - người dùng 19/10/2026)
# Nhấp MỘT lần vào ô rồi Ctrl+C: chép chữ hiển thị (DisplayRole) của ô; chọn nhiều ô / dòng: ghép Tab + xuống dòng (dán thẳng vào
# Excel); Ctrl+Shift+C: cả dòng hiện tại. Menu chuột phải có "Sao chép ô" / "Sao chép cả dòng" đứng đầu. Gắn tự động cho mọi QTableView
# khi cửa sổ hiện (ap_kieu_cay); bảng tự dựng menu chuột phải gọi them_muc_sao_chep(menu, bang, pos) ở đầu menu.
def _chu_o_bang(bang, idx) -> str:
    if idx is None or not idx.isValid():
        return ''
    v = idx.data(Qt.ItemDataRole.DisplayRole)
    if v is None:
        if idx.data(Qt.ItemDataRole.CheckStateRole) is not None:
            c = idx.data(Qt.ItemDataRole.CheckStateRole)
            return 'x' if c in (Qt.CheckState.Checked, 2) or getattr(c, 'value', None) == 2 else ''
        return ''
    return str(v).replace(' ', ' ').replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')


def _cot_hien(bang) -> list:
    m = bang.model()
    return [c for c in range(m.columnCount()) if not bang.isColumnHidden(c)] if m is not None else []


def chu_sao_chep_bang(bang) -> str:
    """Chữ sẽ chép khi Ctrl+C: một ô (ô hiện tại khi vùng chọn chỉ một dòng / một ô), nhiều ô -> Tab giữa ô, xuống dòng giữa dòng."""
    sm, m = bang.selectionModel(), bang.model()
    if m is None:
        return ''
    chon = sm.selectedIndexes() if sm is not None else []
    hang = sorted({i.row() for i in chon})
    cot = sorted({i.column() for i in chon if not bang.isColumnHidden(i.column())})
    hien_tai = bang.currentIndex()
    if len(hang) <= 1 and (bang.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectRows or len(cot) <= 1):
        idx = hien_tai if hien_tai.isValid() else (chon[0] if chon else None)
        return _chu_o_bang(bang, idx)
    co = {(i.row(), i.column()) for i in chon}
    dong = []
    for r in hang:
        dong.append('\t'.join(_chu_o_bang(bang, m.index(r, c)) if (r, c) in co else '' for c in cot))
    return '\n'.join(dong)


def chu_dong_bang(bang, r: int | None = None) -> str:
    """Cả dòng r (mặc định dòng hiện tại), các cột đang hiện, ghép Tab."""
    m = bang.model()
    if m is None:
        return ''
    if r is None:
        r = bang.currentIndex().row()
    if r < 0:
        return ''
    return '\t'.join(_chu_o_bang(bang, m.index(r, c)) for c in _cot_hien(bang))


def _ghi_clipboard(chu: str) -> None:
    QApplication.clipboard().setText(chu)


def sao_chep_bang(bang, ca_dong: bool = False) -> str:
    chu = chu_dong_bang(bang) if ca_dong else chu_sao_chep_bang(bang)
    _ghi_clipboard(chu)
    return chu


def them_muc_sao_chep(menu, bang, pos=None) -> list:
    """Hai mục đầu menu chuột phải: 'Sao chép ô: "<giá trị>" (Ctrl+C)', 'Sao chép cả dòng (Ctrl+Shift+C)'. pos: điểm bấm (tọa độ
    viewport) - ô dưới chuột thành ô hiện tại. Trả [QAction]."""
    if pos is not None:
        idx = bang.indexAt(pos)
        if idx.isValid() and idx != bang.currentIndex():
            sm = bang.selectionModel()
            if sm is None or not sm.isSelected(idx):
                bang.setCurrentIndex(idx)
            else:                                         # bấm trong vùng đang chọn: giữ vùng chọn, chỉ đổi ô hiện tại
                sm.setCurrentIndex(idx, sm.SelectionFlag.NoUpdate)
    gt = chu_sao_chep_bang(bang)
    ngan = gt if len(gt) <= 40 else gt[:38] + '…'
    ngan = ngan.replace('\t', ' ').replace('\n', ' ').replace('&', '&&')
    from PySide6.QtWidgets import QMenu
    if not isinstance(menu, QMenu):                     # menu giả của kiểm thử
        return []
    cu = menu.actions()
    dau = cu[0] if cu else None
    a1 = menu.addAction(f'Sao chép ô: "{ngan}"\tCtrl+C' if '\n' not in gt else 'Sao chép các ô đã chọn\tCtrl+C')
    a1.triggered.connect(lambda _=False, b=bang: sao_chep_bang(b))
    a2 = menu.addAction('Sao chép cả dòng\tCtrl+Shift+C')
    a2.triggered.connect(lambda _=False, b=bang: sao_chep_bang(b, True))
    a1.setEnabled(bool(gt))
    a2.setEnabled(bang.currentIndex().isValid())
    if dau is not None:                                   # đưa lên đầu menu đã có mục
        menu.removeAction(a1)
        menu.removeAction(a2)
        menu.insertAction(dau, a1)
        menu.insertAction(dau, a2)
        menu.insertSeparator(dau)
    return [a1, a2]


def menu_sao_chep(bang, pos, hien: bool = True):
    """Menu chuột phải mặc định của bảng không có menu riêng."""
    from PySide6.QtWidgets import QMenu
    menu = QMenu(bang)
    them_muc_sao_chep(menu, bang, pos)
    if hien:
        menu.exec(bang.viewport().mapToGlobal(pos))
        menu.deleteLater()
    return menu


class _BoSaoChep(QObject):
    """Ctrl+C / Ctrl+Shift+C trên bảng, Ctrl+D chép ô trên xuống (1.0.07); mở ô sửa (QLineEdit) bằng chuột / F2 thì bôi đen sẵn cả
    chữ."""

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress) and isinstance(obj, QAbstractItemView):
            k, md = ev.key(), ev.modifiers()
            ctrl = bool(md & Qt.KeyboardModifier.ControlModifier)
            if ctrl and k == Qt.Key.Key_C and not (md & Qt.KeyboardModifier.AltModifier):
                if t == QEvent.Type.ShortcutOverride:
                    ev.accept()                           # bảng nhận phím trước phím tắt của cửa sổ
                    return False
                sao_chep_bang(obj, bool(md & Qt.KeyboardModifier.ShiftModifier))
                return True
            if ctrl and k == Qt.Key.Key_D and not (md & (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier)) \
                    and obj.state() != QAbstractItemView.State.EditingState:
                if t == QEvent.Type.ShortcutOverride:     # 1.0.07: Ctrl+D chép ô trên xuống (Excel)
                    ev.accept()
                    return False
                dien_xuong(obj)
                return True
            if t == QEvent.Type.KeyPress and ev.text() and ev.text().isprintable() and not ctrl:
                obj.setProperty('_go_phim', True)         # mở ô sửa bằng gõ phím: không bôi đen (chữ gõ thay chữ cũ)
                QTimer.singleShot(0, lambda o=obj: _xoa_co_phim(o))
            return False
        if t == QEvent.Type.MouseButtonPress and obj.property('_bang_sao_chep'):
            gan_bo_dem(obj.parent())                      # bảng đổi mô hình (selectionModel mới) sau khi gắn: gắn lại bộ đếm
            return False
        if t == QEvent.Type.ChildAdded and obj.property('_bang_sao_chep'):
            from PySide6.QtWidgets import QLineEdit
            w = ev.child()
            if isinstance(w, QLineEdit):
                bang = obj.parent()
                if not (bang is not None and bang.property('_go_phim')):
                    QTimer.singleShot(0, w.selectAll)
        return False


def _xoa_co_phim(o) -> None:
    try:
        o.setProperty('_go_phim', False)
    except RuntimeError:                                  # bảng đã hủy
        pass


_BO_SAO_CHEP = []


BUOC_CUON = 20                  # bước cuộn (px) mỗi nấc lăn chuột / mũi tên thanh cuộn


def cuon_muot(bang, buoc: int = BUOC_CUON) -> None:
    """Bảng cuộn từng điểm ảnh (không nhảy cả dòng - dòng cao nhiều dòng chữ không bị "giật"), bước cuộn buoc px."""
    from PySide6.QtWidgets import QAbstractItemView as V
    bang.setVerticalScrollMode(V.ScrollMode.ScrollPerPixel)
    bang.setHorizontalScrollMode(V.ScrollMode.ScrollPerPixel)
    bang.verticalScrollBar().setSingleStep(buoc)
    bang.horizontalScrollBar().setSingleStep(buoc)


def cho_phep_sao_chep_bang(bang) -> None:
    """Gắn sao chép ô / dòng cho một bảng (QTableView / QTableWidget / BangAo). Gọi lại không gắn thêm."""
    from PySide6.QtWidgets import QTableView
    if not isinstance(bang, QTableView) or bang.property('_co_sao_chep'):
        return
    bang.setProperty('_co_sao_chep', True)
    cuon_muot(bang)                                       # 1.0.07: cuộn từng điểm ảnh, bước lăn chuột 20 px
    gan_enter_xuong(bang)                                 # 1.0.07: sửa ô xong Enter -> xuống ô dưới cùng cột
    cho_chon_vung_o(bang)                                 # 21/10/2026: bôi đen vùng ô kiểu Excel + bộ đếm
    gan_bo_dem(bang)
    if not _BO_SAO_CHEP:
        _BO_SAO_CHEP.append(_BoSaoChep())
    bo = _BO_SAO_CHEP[0]
    bang.installEventFilter(bo)
    bang.viewport().setProperty('_bang_sao_chep', True)
    bang.viewport().installEventFilter(bo)
    if bang.contextMenuPolicy() == Qt.ContextMenuPolicy.DefaultContextMenu:
        bang.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        bang.customContextMenuRequested.connect(lambda p, b=bang: menu_sao_chep(b, p))


# ---------------------------------------------------------------- ô Họ và tên hai tầng (1.0.78)
from PySide6.QtGui import QFontMetrics as _QFM  # noqa: E402
from PySide6.QtWidgets import QStyle as _QStyle, QStyledItemDelegate as _QDeleg, QStyleOptionViewItem as _QOpt  # noqa: E402

VAI_PHU_TEN = Qt.ItemDataRole.UserRole + 21      # dòng dưới tên; không có vai này thì lấy phần sau "\n" của chữ ô
_CO_XUONG_DONG = int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)


def _phong_phu_ten(f):
    f2 = QFont(f)
    f2.setPixelSize(11)
    return f2


def cao_ten_hai_tang(ten, phu, f, rong: int) -> tuple:
    """Chiều cao (px) phần tên, dòng dưới tên khi xuống dòng trong bề rộng rong, đo bằng đúng phông vẽ. Tên in đậm khi có dòng dưới."""
    fb = QFont(f)
    if phu:
        fb.setBold(True)
    rong = max(20, rong)
    h1 = _QFM(fb).boundingRect(0, 0, rong, 10 ** 6, _CO_XUONG_DONG, ten or '').height()
    h2 = _QFM(_phong_phu_ten(f)).boundingRect(0, 0, rong, 10 ** 6, _CO_XUONG_DONG, phu).height() if phu else 0
    return h1, h2


class OTenHaiTang(_QDeleg):
    """Ô Họ và tên: dòng 1 tên, dòng 2 chữ nhỏ ghi chú dưới tên; chữ dài xuống dòng, không rút "…". Chiều cao dòng do bảng đặt (cao_ten_hai_tang)."""

    def paint(self, p, option, index):
        ten, _, phu = str(index.data() or '').partition('\n')
        phu = index.data(VAI_PHU_TEN) or phu
        opt = _QOpt(option)
        self.initStyleOption(opt, index)
        f = QFont(opt.font)
        opt.text = ''
        (opt.widget.style() if opt.widget is not None else QApplication.style()).drawControl(_QStyle.ControlElement.CE_ItemViewItem, opt, p, opt.widget)
        r = option.rect.adjusted(5, 2, -5, -2)
        chon = bool(option.state & _QStyle.StateFlag.State_Selected)
        h1, h2 = cao_ten_hai_tang(ten, phu, f, r.width())
        y = r.top() + max(0, (r.height() - h1 - h2) // 2)
        mau = option.palette.highlightedText().color() if chon else opt.palette.text().color()
        vai_mau = index.data(Qt.ItemDataRole.ForegroundRole)
        if vai_mau is not None and not chon:
            mau = vai_mau.color()
        p.save()
        if phu:
            f.setBold(True)
        p.setFont(f)
        p.setPen(mau)
        p.drawText(r.left(), y, r.width(), h1, _CO_XUONG_DONG, ten)
        if phu:
            p.setFont(_phong_phu_ten(opt.font))
            p.setPen(mau if chon else qmau_theo_tong(MAU_CHU_PHU_BANG, 'chu'))
            p.drawText(r.left(), y + h1, r.width(), h2, _CO_XUONG_DONG, phu)
        p.restore()


# ---------------------------------------------------------------- cắt / dán ô kiểu Excel (1.0.78)
def doc_o_clipboard(chu: str) -> list:
    """Chữ dán (Excel, Word, chính bảng này: tab giữa ô, xuống dòng giữa dòng, ô có xuống dòng nằm trong "...") -> [[ô]]."""
    import csv
    import io
    chu = str(chu or '').replace('\r\n', '\n').replace('\r', '\n')
    if chu.endswith('\n'):
        chu = chu[:-1]
    if not chu:
        return []
    try:
        return [list(d) or [''] for d in csv.reader(io.StringIO(chu, newline=''), delimiter='\t')]
    except csv.Error:
        return [d.split('\t') for d in chu.split('\n')]


def _o_duoc_ghi(bang, r: int, c: int, bo_cot=()) -> bool:
    it = bang.item(r, c)
    return it is not None and c not in bo_cot and bool(it.flags() & Qt.ItemFlag.ItemIsEditable)


def _ghi_cac_o(bang, viec: list, ghi=None) -> int:
    """Ghi [(r, c, chữ)]; bỏ chọn trong lúc ghi (bảng áp một ô cho mọi dòng đang chọn không được áp nhầm), xong chọn lại."""
    sm = bang.selectionModel()
    chon = sm.selection()
    hien = bang.currentIndex()
    sm.clearSelection()
    n = 0
    try:
        for r, c, chu in viec:
            if ghi is not None:
                ghi(r, c, chu)
            else:
                bang.item(r, c).setText(chu)
            n += 1
    finally:
        if hien.isValid():
            bang.setCurrentIndex(hien)
        sm.clearSelection()
        sm.select(chon, sm.SelectionFlag.Select)
    return n


def dan_vao_bang(bang, chu=None, ghi=None, bo_cot=()) -> dict:
    """Ctrl+V: một giá trị + nhiều ô đang chọn -> điền mọi ô chọn; còn lại dán khối từ ô trên cùng bên trái vùng chọn. Bỏ qua cột ẩn
    (dán theo cột đang thấy), ô không sửa được, phần tràn ngoài bảng. Trả {'da_ghi', 'bo_qua'}."""
    from PySide6.QtWidgets import QAbstractItemView, QApplication
    if bang.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers:
        return dict(da_ghi=0, bo_qua=0)
    dl = doc_o_clipboard(QApplication.clipboard().text() if chu is None else chu)
    chon = bang.selectionModel().selectedIndexes()
    if not chon and bang.currentIndex().isValid():
        chon = [bang.currentIndex()]
    if not dl or not chon:
        return dict(da_ghi=0, bo_qua=0)
    viec, bo = [], 0
    if len(dl) == 1 and len(dl[0]) == 1:
        for i in chon:
            if bang.isColumnHidden(i.column()) or bang.isRowHidden(i.row()):
                continue
            if _o_duoc_ghi(bang, i.row(), i.column(), bo_cot):
                viec.append((i.row(), i.column(), dl[0][0]))
            else:
                bo += 1
    else:
        r0, c0 = min(i.row() for i in chon), min(i.column() for i in chon)
        cot = [c for c in range(c0, bang.columnCount()) if not bang.isColumnHidden(c)]
        dong = [r for r in range(r0, bang.rowCount()) if not bang.isRowHidden(r)]
        for k, hang in enumerate(dl):
            for j, gt in enumerate(hang):
                if k < len(dong) and j < len(cot) and _o_duoc_ghi(bang, dong[k], cot[j], bo_cot):
                    viec.append((dong[k], cot[j], gt))
                else:
                    bo += 1
    return dict(da_ghi=_ghi_cac_o(bang, viec, ghi), bo_qua=bo)


def cat_khoi_bang(bang, ghi=None, bo_cot=()) -> dict:
    """Ctrl+X: chép vùng chọn rồi xóa chữ các ô sửa được (ô không sửa được: chỉ chép)."""
    from PySide6.QtWidgets import QAbstractItemView
    sao_chep_bang(bang)
    if bang.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers:
        return dict(da_ghi=0, bo_qua=0)
    chon = bang.selectionModel().selectedIndexes() or ([bang.currentIndex()] if bang.currentIndex().isValid() else [])
    viec = [(i.row(), i.column(), '') for i in chon if _o_duoc_ghi(bang, i.row(), i.column(), bo_cot)]
    return dict(da_ghi=_ghi_cac_o(bang, viec, ghi), bo_qua=len(chon) - len(viec))


def gan_cat_dan(bang, dan, cat) -> tuple:
    """Ctrl+V, Ctrl+X trên ô bảng (WidgetShortcut: đang sửa trong ô thì ô chữ tự xử lý như thường)."""
    from PySide6.QtGui import QKeySequence, QShortcut
    kq = []
    for phim, ham in ((QKeySequence.StandardKey.Paste, dan), (QKeySequence.StandardKey.Cut, cat)):
        sc = QShortcut(QKeySequence(phim), bang)
        sc.setContext(Qt.ShortcutContext.WidgetShortcut)
        sc.activated.connect(ham)
        kq.append(sc)
    return tuple(kq)


# ---------------------------------------------------------------- bôi đen vùng ô + bộ đếm kiểu Excel (người dùng 21/10/2026)
# Mọi bảng chọn TỪNG Ô (SelectItems) + nhiều vùng (ExtendedSelection): kéo chuột / Shift / Ctrl như Excel; bấm tiêu đề hàng dọc hoặc
# ô cột STT chọn nguyên dòng. Vùng chọn có viền xanh lá (lớp phủ _VienVungChon). Lệnh theo hộ đọc DÒNG qua cac_dong_da_chon (chọn
# 1 ô của 3 hộ = 3 hộ) - KHÔNG dùng selectionModel().selectedRows() (chỉ trả dòng chọn trọn mọi cột).
# Bộ đếm (thong_ke_vung_chon): Trung bình / Tổng số đếm / Tổng của vùng chọn - cửa sổ có hàm cap_nhat_bo_dem(bảng, tk) (cửa sổ
# chính, hộp Thống kê) tự hiện; hộp thoại khác: nhãn nổi góc dưới phải bảng.
MAU_VIEN_CHON = TOKEN['phu']    # Emerald Teal (22/10/2026; trước #2F7D54)
CHON_TOI_DA_NGAY = 3000          # vùng chọn tới bấy nhiêu ô: đếm ngay; lớn hơn (Ctrl+A bảng 5.000 hộ): chờ CHO_BO_DEM_MS
CHO_BO_DEM_MS = 120
VUNG_VE_TOI_DA = 200             # số vùng chọn (Ctrl + bấm từng ô) vẽ viền tối đa
SO_LE_DEM_TOI_DA = 4
# cột định danh (tiêu đề so không dấu, chữ thường): có số nhưng KHÔNG cộng (vẫn tính vào "Tổng số đếm"). "Số thửa" của danh sách
# hộ là SỐ LƯỢNG thửa (cộng được); bảng có cột số hiệu thửa tên "Số thửa" đặt property cot_dinh_danh = [cột]
COT_DINH_DANH = frozenset((
    'stt', 'tt', '#', 'ma ho', 'so cccd', 'cccd', 'cmnd', 'so cmnd', 'cccd/cmnd', 'so cccd/cmnd', 'dien thoai', 'so dien thoai', 'sdt',
    'to', 'to bd', 'so to', 'to ban do', 'so to ban do', 'thua', 'thua so', 'so hieu thua', 'so thua hieu', 'ma thua', 'to/thua',
    'nam', 'ngay', 'vi tri', 'he so', 'he so k', 'ty le', 'ty le %', 'ty le (%)', '%', 'chon'))
TU_DAU_DINH_DANH = ('ngay', 'nam')          # tiêu đề bắt đầu bằng từ này: "Ngày PA", "Ngày ban hành", "Năm sinh"
COT_CHON_DONG = ('stt', 'tt', '#')           # bấm ô cột này = chọn cả dòng
_RE_SO_O = re.compile(r'([-+−]?\d[\d.,]*)\s*(đồng|đ|m²|m2|ha|%|cây|hộ|thửa)?', re.IGNORECASE)


def cac_dong_da_chon(bang, hien_tai: bool = True) -> list:
    """Các dòng (của mô hình bảng - với bảng lọc / sắp xếp là dòng proxy) có ít nhất một ô đang chọn, tăng dần, bỏ dòng ẩn. Không
    có vùng chọn mà ô hiện tại hợp lệ: dòng của ô hiện tại (hien_tai=False: [] - lệnh "không chọn thì cả đợt")."""
    try:
        sm = bang.selectionModel() if bang is not None else None
    except RuntimeError:
        return []
    if sm is None:
        return []
    dong = {i.row() for i in sm.selectedIndexes() if i.isValid()}
    if not dong and hien_tai:
        idx = bang.currentIndex()
        if idx.isValid():
            dong = {idx.row()}
    return sorted(r for r in dong if not bang.isRowHidden(r))


def _ten_cot_chuan(bang, c: int) -> str:
    m = bang.model()
    h = m.headerData(c, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) if m is not None else None
    return ' '.join(bo_dau(str(h or '')).lower().replace('\n', ' ').split())


def la_cot_dinh_danh(bang, c: int) -> bool:
    """Cột định danh (STT, mã hộ, CCCD, điện thoại, tờ, thửa, ngày, năm): bộ đếm không cộng."""
    rieng = bang.property('cot_dinh_danh')
    if rieng and c in [int(x) for x in rieng]:
        return True
    t = _ten_cot_chuan(bang, c)
    return t in COT_DINH_DANH or (t.split()[0] in TU_DAU_DINH_DANH if t else False)


def nhom_cot_dem(bang, c: int) -> str:
    """Bản chất cột với bộ đếm: 'kl' (diện tích, số lượng, khối lượng), 'gia' (đơn giá), 'tien' (thành tiền), '' (cột khác). Khác bản chất không cộng chung."""
    t = _ten_cot_chuan(bang, c)
    if not t or la_cot_dinh_danh(bang, c):
        return ''
    if 'thanh tien' in t or 'so tien' in t or t.startswith(('tong tien', 'kinh phi', 'tien ')):
        return 'tien'
    if 'don gia' in t or t.startswith('gia '):
        return 'gia'
    if t.startswith(('dt ', 'dien tich', 'so luong', 'khoi luong')) or t in ('dt', 'sl', 'kl'):
        return 'kl'
    return ''


def doc_so_o(chu):
    """Chữ hiển thị của ô -> (Decimal, số chữ số lẻ) hoặc None (không phải số). Kiểu VN (tien.doc_so_vn); bỏ hậu tố đ / đồng / m² /
    ha / % / cây / hộ / thửa; ô gạch '-' = 0."""
    from .tien import D, doc_so_vn
    s = str(chu).replace(' ', ' ').strip()
    if s in ('-', '–', '—'):
        return D(0), 0
    mt = _RE_SO_O.fullmatch(s)
    if not mt:
        return None
    try:
        x = doc_so_vn(mt.group(1).replace('−', '-'))
    except (ValueError, ArithmeticError):
        return None
    return x, max(0, -x.as_tuple().exponent) if x.is_finite() else 0


def _goc_gop(bang, r: int, c: int) -> tuple:
    """Ô trên cùng bên trái của vùng gộp chứa ô (r, c)."""
    m = bang.model()
    vung = bang.visualRect(m.index(r, c))
    while r > 0 and bang.visualRect(m.index(r - 1, c)) == vung:
        r -= 1
    while c > 0 and bang.visualRect(m.index(r, c - 1)) == vung:
        c -= 1
    return r, c


def thong_ke_vung_chon(bang) -> dict:
    """Bộ đếm kiểu Excel của vùng đang chọn: so_dem (ô có chữ hiển thị), so_so (ô số được cộng), tong, trung_binh (Decimal / None),
    so_le (chữ số lẻ nhiều nhất của các số), chuoi ("Trung bình: …     Tổng số đếm: n     Tổng: …"; chỉ chữ: "Tổng số đếm: n"; dưới
    2 ô có chữ: ''). Bỏ dòng / cột ẩn; ô gộp tính một lần (ô trên trái); cột định danh (la_cot_dinh_danh) chỉ đếm, không cộng."""
    from .tien import D
    kq = dict(so_dem=0, so_so=0, tong=D(0), trung_binh=None, so_le=0, chuoi='', so_dong=0, nhom={})
    try:
        sm, m = bang.selectionModel(), bang.model()
    except RuntimeError:
        return kq
    if sm is None or m is None:
        return kq
    dinh_danh, da_gop, nhom_cua, dong = {}, set(), {}, set()
    for i in sm.selectedIndexes():
        r, c = i.row(), i.column()
        if bang.isRowHidden(r) or bang.isColumnHidden(c):
            continue
        if bang.rowSpan(r, c) > 1 or bang.columnSpan(r, c) > 1:
            r, c = _goc_gop(bang, r, c)
            if (r, c) in da_gop:
                continue
            da_gop.add((r, c))
            i = m.index(r, c)
        v = i.data(Qt.ItemDataRole.DisplayRole)
        chu = '' if v is None else str(v).strip()
        if not chu:
            continue
        kq['so_dem'] += 1
        dong.add(r)
        if c not in dinh_danh:
            dinh_danh[c] = la_cot_dinh_danh(bang, c)
            nhom_cua[c] = nhom_cot_dem(bang, c)
        if dinh_danh[c]:
            continue
        so = doc_so_o(chu)
        if so is None:
            continue
        if nhom_cua[c]:
            g = kq['nhom'].setdefault(nhom_cua[c], dict(tong=D(0), n=0, so_le=0))
            g['tong'] += so[0]
            g['n'] += 1
            g['so_le'] = max(g['so_le'], min(so[1], SO_LE_DEM_TOI_DA))
        kq['so_so'] += 1
        kq['tong'] += so[0]
        kq['so_le'] = max(kq['so_le'], min(so[1], SO_LE_DEM_TOI_DA))
    kq['so_dong'] = len(dong)
    if kq['nhom']:                                      # có cột biết bản chất: "Tổng" là tổng đúng loại, không phải cộng mọi cột số
        g = kq['nhom'].get('tien') or kq['nhom'].get('kl') or kq['nhom']['gia']
        kq['tong'], kq['so_le'] = g['tong'], g['so_le']
    if kq['so_so']:
        kq['trung_binh'] = kq['tong'] / (g['n'] if kq['nhom'] else kq['so_so'])
    kq['chuoi'] = chu_thong_ke(kq)
    return kq


def so_bo_dem(x, so_le: int) -> str:
    """Số trên bộ đếm: theo số chữ số lẻ của dữ liệu (215,1 + 459,4 -> "674,5"; số nguyên -> không lẻ); số lẻ hơn mà dữ liệu nguyên
    (trung bình 7 / 2) -> 1 chữ số lẻ."""
    from .tien import lam_tron, vn
    if not so_le and x != x.to_integral_value():
        so_le = 1
    return vn(lam_tron(x, so_le), so_le) if so_le else vn(x)


def chu_thong_ke(kq: dict) -> str:
    n = kq['so_dem']
    if n < 2:
        return ''
    if not kq['so_so']:
        return f'Tổng số đếm: {n}'
    nhom = kq.get('nhom')
    if nhom:
        phan = [f'Đang chọn: {kq["so_dong"]} dòng ({n} ô)']
        if 'kl' in nhom:
            phan.append(f'Tổng DT/KL: {so_bo_dem(nhom["kl"]["tong"], nhom["kl"]["so_le"])}')
        if 'gia' in nhom:
            phan.append(f'Đơn giá TB: {so_bo_dem(nhom["gia"]["tong"] / nhom["gia"]["n"], 0)} đ')
        if 'tien' in nhom:
            phan.append(f'Tổng Thành tiền: {so_bo_dem(nhom["tien"]["tong"], nhom["tien"]["so_le"])} đồng')
        return '  |  '.join(phan)
    return (f'Trung bình: {so_bo_dem(kq["trung_binh"], kq["so_le"])}     Tổng số đếm: {n}     '
            f'Tổng: {so_bo_dem(kq["tong"], kq["so_le"])}')


class NhanBoDem(QLabel):
    """Nhãn bộ đếm (nền xanh lá nhạt): bấm -> chép Tổng vào clipboard + thông báo nổi. Ẩn khi không có gì để đếm."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('lb_bo_dem_excel')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip('Bộ đếm vùng chọn (như thanh trạng thái Excel). Bấm để sao chép Tổng')
        self.tk = None
        self.hide()

    def dat(self, tk: dict | None) -> None:
        self.tk = tk
        chu = (tk or {}).get('chuoi') or ''
        self.setText(chu)
        self.setVisible(bool(chu))

    def chu_tong(self) -> str:
        tk = self.tk or {}
        return so_bo_dem(tk['tong'], tk['so_le']) if tk.get('so_so') else ''

    def sao_chep_tong(self) -> str:
        chu = self.chu_tong()
        if chu:
            _ghi_clipboard(chu)
            thong_bao_noi(self, f'Đã sao chép tổng: {chu}')
        return chu

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.pos()):
            self.sao_chep_tong()
        super().mouseReleaseEvent(e)


class _VienVungChon(QWidget):
    """Viền xanh lá quanh từng vùng chọn (kiểu Excel). Con của BẢNG (không phải viewport: viewport.scroll dời cả widget con), phủ
    đúng vùng viewport, trong suốt với chuột; vẽ lại khi vùng chọn / cuộn / đổi cỡ cột, dòng."""

    def __init__(self, bang):
        super().__init__(bang)
        self.bang = bang
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.vua()
        self.show()

    def vua(self, *a) -> None:
        try:
            self.setGeometry(self.bang.viewport().geometry())
        except RuntimeError:
            pass

    def ve_lai(self, *a) -> None:
        self.update()

    def paintEvent(self, e):
        b = self.bang
        sm = b.selectionModel()
        if sm is None or not sm.hasSelection():
            return
        from PySide6.QtGui import QPen
        p = QPainter(self)
        p.setPen(QPen(QColor(MAU_VIEN_CHON), 2))
        for vung in list(sm.selection())[:VUNG_VE_TOI_DA]:
            tren, duoi, trai, phai = vung.top(), vung.bottom(), vung.left(), vung.right()
            x0, y0 = b.columnViewportPosition(trai), b.rowViewportPosition(tren)
            x1 = b.columnViewportPosition(phai) + b.columnWidth(phai)
            y1 = b.rowViewportPosition(duoi) + b.rowHeight(duoi)
            if x1 <= x0 or y1 <= y0 or x0 < -100000:
                continue
            p.drawRect(QRect(x0 + 1, y0 + 1, x1 - x0 - 2, y1 - y0 - 2))
        p.end()


class _BoChonVung(QObject):
    """Gắn trên mỗi bảng (con của bảng - hủy cùng bảng, tín hiệu tự ngắt): bấm cột STT chọn cả dòng, viền vùng chọn, bộ đếm."""

    def __init__(self, bang):
        super().__init__(bang)
        self.bang = bang
        self.sm = None
        self.neo = -1
        self.vien = _VienVungChon(bang)
        self.nhan_noi = None
        self.hen = QTimer(self)
        self.hen.setSingleShot(True)
        self.hen.setInterval(CHO_BO_DEM_MS)
        self.hen.timeout.connect(self.dem)
        bang.pressed.connect(self.bam)
        for sb in (bang.verticalScrollBar(), bang.horizontalScrollBar()):
            sb.valueChanged.connect(self.vien.ve_lai)
        for h in (bang.horizontalHeader(), bang.verticalHeader()):
            h.sectionResized.connect(self.vien.ve_lai)
            h.sectionMoved.connect(self.vien.ve_lai)
        bang.installEventFilter(self)

    def gan_sm(self) -> None:
        sm = self.bang.selectionModel()
        # 31/10/2026 (kiểm tra giao diện): mô hình chọn cũ vừa bị hủy, PySide trả về đối tượng khác cùng địa chỉ (QWidgetItem…): bỏ qua
        if sm is None or sm is self.sm or not hasattr(sm, 'selectionChanged'):
            return
        self.sm = sm
        sm.selectionChanged.connect(self.doi)
        m = sm.model()
        if m is not None:
            m.modelReset.connect(self.doi)
            m.layoutChanged.connect(self.doi)

    def eventFilter(self, obj, ev):
        if obj is self.bang and ev.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.LayoutRequest):
            self.vien.vua()
            self._dat_nhan_noi()
        return False

    def bam(self, idx) -> None:
        """Bấm ô cột STT: chọn nguyên dòng (Ctrl: thêm dòng, Shift: dải dòng từ dòng bấm trước)."""
        b = self.bang
        if not idx.isValid() or _ten_cot_chuan(b, idx.column()) not in COT_CHON_DONG:
            return
        from PySide6.QtCore import QItemSelection, QItemSelectionModel
        md = QApplication.keyboardModifiers()
        m, sm = b.model(), b.selectionModel()
        if sm is None or m is None or m.columnCount() == 0:
            return
        r = idx.row()
        r0 = r
        if md & Qt.KeyboardModifier.ShiftModifier and 0 <= self.neo < m.rowCount():
            r0 = self.neo
        else:
            self.neo = r
        F = QItemSelectionModel.SelectionFlag
        co = F.Select if md & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) else F.ClearAndSelect
        sm.select(QItemSelection(m.index(min(r0, r), 0), m.index(max(r0, r), m.columnCount() - 1)), co | F.Rows)

    def doi(self, *a) -> None:
        self.vien.ve_lai()
        sm = self.sm
        try:
            n = len(sm.selectedIndexes()) if sm is not None else 0
        except RuntimeError:
            return
        if n <= CHON_TOI_DA_NGAY:
            self.hen.stop()
            self.dem()
        else:
            self.hen.start()

    def dem(self) -> None:
        b = self.bang
        try:
            w = b.window()
        except RuntimeError:
            return
        tk = thong_ke_vung_chon(b)
        # cha gần nhất có dải đếm: cửa sổ lập phương án nhúng trong cửa sổ chính dùng dải của nó. Dừng ở biên cửa sổ: bảng trong hộp thoại con
        # (_BangDong của HopTinhGiaDat) không gọi hàm của cửa sổ đã mở hộp, không có hàm thì dùng nhãn riêng dưới bảng
        cha = None if b.isWindow() else b.parentWidget()
        while cha is not None and not callable(getattr(cha, 'cap_nhat_bo_dem', None)):
            cha = None if cha.isWindow() else cha.parentWidget()
        ham = getattr(cha if cha is not None else w, 'cap_nhat_bo_dem', None)
        if callable(ham):
            ham(b, tk)
            return
        if self.nhan_noi is None:
            if not tk['chuoi']:
                return
            self.nhan_noi = self._tao_nhan_chan_bang()
        self.nhan_noi.dat(tk)
        if self.nhan_noi.property('chan_bang'):
            self.nhan_noi.setVisible(True)       # giữ chỗ khi không có chữ: kéo chọn không làm bảng co giãn dưới tay
        self._dat_nhan_noi()

    def _tao_nhan_chan_bang(self):
        """Nhãn đếm nằm NGAY DƯỚI bảng trong bố cục dọc chứa bảng (1.0.69, trước đây nổi trong lòng bảng, che dòng cuối)."""
        b = self.bang
        cha = b.parentWidget()
        lo = _bo_cuc_doc_chua(cha.layout(), b) if cha is not None and cha.layout() is not None else None
        if lo is None:
            return NhanBoDem(b)
        n = NhanBoDem(cha)
        lo.insertWidget(lo.indexOf(b) + 1, n)
        n.setProperty('chan_bang', True)
        return n

    def _dat_nhan_noi(self) -> None:
        n = self.nhan_noi
        if n is None or not n.isVisible() or n.property('chan_bang'):
            return
        n.adjustSize()
        vp = self.bang.viewport().geometry()
        n.move(max(0, vp.right() - n.width() - 6), max(0, vp.bottom() - n.height() - 6))
        n.raise_()


def _bo_cuc_doc_chua(lo, w):
    """Bố cục dọc (kể cả lồng) chứa trực tiếp widget w. Duyệt bằng children() + indexOf: không lấy QLayoutItem (xem CLAUDE.md)."""
    from PySide6.QtWidgets import QBoxLayout
    if isinstance(lo, QBoxLayout) and lo.indexOf(w) >= 0:
        return lo if lo.direction() in (QBoxLayout.Direction.TopToBottom, QBoxLayout.Direction.Down) else None
    for con in lo.children():
        if isinstance(con, QBoxLayout):
            kq = _bo_cuc_doc_chua(con, w)
            if kq is not None:
                return kq
    return None


def cho_chon_vung_o(bang) -> None:
    """Bảng chọn từng ô + nhiều vùng (Excel); tiêu đề hàng dọc bấm được. Gọi lại không làm gì."""
    from PySide6.QtWidgets import QTableView
    if not isinstance(bang, QTableView) or bang.property('_chon_vung'):
        return
    bang.setProperty('_chon_vung', True)
    V = QAbstractItemView
    bang.setSelectionBehavior(V.SelectionBehavior.SelectItems)
    if bang.selectionMode() != V.SelectionMode.NoSelection:
        bang.setSelectionMode(V.SelectionMode.ExtendedSelection)
    vh = bang.verticalHeader()
    vh.setSectionsClickable(True)                       # QTableView tự nối sectionPressed -> selectRow
    vh.setHighlightSections(True)


def gan_bo_dem(bang) -> None:
    """Gắn bộ đếm + viền vùng chọn + bấm STT chọn dòng cho bảng (gọi lại: chỉ nối lại khi bảng đã đổi selectionModel)."""
    from PySide6.QtWidgets import QTableView
    if not isinstance(bang, QTableView):
        return
    bo = next((x for x in bang.children() if isinstance(x, _BoChonVung)), None)
    if bo is None:
        bo = _BoChonVung(bang)
    bo.gan_sm()


# ---------------------------------------------------------------- bảng xem trước dữ liệu thô (1.0.04): lọc nhanh + tô dòng lỗi
MAU_DONG_CANH_BAO = '#FEF3C7'          # vàng nhạt: dòng thiếu tờ / thửa, sai loại đất
MAU_DONG_LOI = '#FEE2E2'               # đỏ nhạt: dòng lỗi không nhập được


def loc_dong_bang(bang, chu: str) -> int:
    """Ẩn các dòng QTableWidget không chứa chu (so không dấu, mọi cột). Trả số dòng còn hiện."""
    k = ' '.join(bo_dau(chu or '').lower().split())
    n = 0
    for r in range(bang.rowCount()):
        if not k:
            bang.setRowHidden(r, False)
            n += 1
            continue
        co = any(k in bo_dau(bang.item(r, c).text() if bang.item(r, c) else '').lower() for c in range(bang.columnCount()))
        bang.setRowHidden(r, not co)
        n += co
    return n


def gan_o_loc_bang(bang, o_tim, khi_loc=None) -> None:
    """Ô tìm QLineEdit lọc dòng của bảng (chờ ngừng gõ như các ô tìm khác - loc_khi_ngung_go). khi_loc(số dòng hiện)."""
    def loc(chu=None):
        n = loc_dong_bang(bang, o_tim.text())
        if khi_loc is not None:
            khi_loc(n)
    loc_khi_ngung_go(o_tim, loc)


class _TayNam(QSplitterHandle):
    """Thanh ngăn có biểu tượng nắm kéo: hai vạch đôi + hình thoi giữa (vẽ tay, không phụ thuộc phông Win 7)."""

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        mau = QColor(TOKEN['chu_phu'])
        p.setPen(mau)
        p.setBrush(mau)
        x, y = self.width() // 2, self.height() // 2
        for dau, cuoi in ((x - 62, x - 12), (x + 12, x + 62)):
            p.drawLine(dau, y - 2, cuoi, y - 2)
            p.drawLine(dau, y + 2, cuoi, y + 2)
        p.drawPolygon(QPolygon([QPoint(x, y - 5), QPoint(x + 5, y), QPoint(x, y + 5), QPoint(x - 5, y)]))


class TachCoNam(QSplitter):
    """QSplitter có tay nắm nhìn thấy được."""

    def createHandle(self):
        return _TayNam(self.orientation(), self)


def nhan_xuong_dong(chu: str):
    """QLabel xuống dòng: chữ dài không ép hộp thoại rộng hơn màn hình 1366 @125%."""
    n = QLabel(chu)
    n.setWordWrap(True)
    return n


def to_dong_bang(bang, r: int, loi: list, muc: str = 'canh_bao') -> None:
    """Tô nền cả dòng r (vàng: cảnh báo, đỏ: lỗi) + chú thích danh sách vấn đề; loi rỗng = bỏ tô."""
    from PySide6.QtGui import QBrush
    mau = QBrush(qmau_theo_tong(MAU_DONG_LOI if muc == 'loi' else MAU_DONG_CANH_BAO)) if loi else QBrush()      # 1.0.58: tông Tối đọc được
    goi_y = '\n'.join(loi)
    for c in range(bang.columnCount()):
        it = bang.item(r, c)
        if it is None:
            continue
        it.setBackground(mau)
        if loi or it.toolTip().startswith('Cần xem lại:'):
            it.setToolTip(('Cần xem lại:\n' + goi_y) if loi else '')


# 30/10/2026 (người dùng): ô chọn xổ xuống hiện đủ mục và đủ chữ (trước: kiểu "menu đè lên ô" của Fusion - vài mục, mũi tên cuộn,
# chữ dài bị cắt), màu chọn / rê chuột dịu mắt (trước: xanh sáng chữ trắng)
MAU_CHON_DIU = ('#D6E4F5', '#0F2A47')       # mục đang chọn: nền xanh xám nhạt, chữ xanh đậm
MAU_RE_DIU = '#EEF3FA'                       # mục dưới con trỏ chuột
SO_MUC_XO = 20                               # số mục danh sách xổ hiện cùng lúc (ô chọn để mặc định 10 của Qt)
LE_DANH_SACH_XO = 28                         # px cộng thêm vào bề rộng chữ dài nhất (lề mục + thanh cuộn)


def vua_danh_sach_xo(khung) -> None:
    """Danh sách xổ của ô chọn (khung = QComboBoxPrivateContainer đang hiện) rộng đủ chữ dài nhất (không hẹp hơn ô chọn, không rộng
    hơn màn hình), dời vào trong màn hình nếu tràn phải."""
    cb = khung.parent()
    if not isinstance(cb, QComboBox):
        return
    v = cb.view()
    try:
        v.setTextElideMode(Qt.TextElideMode.ElideNone)
        chu = max(v.sizeHintForColumn(cb.modelColumn()), 0)
    except Exception:                                   # noqa: BLE001 - mô hình lạ: giữ bề rộng Qt
        return
    rong = chu + LE_DANH_SACH_XO + v.verticalScrollBar().sizeHint().width() + 2 * khung.frameWidth()
    man = khung.screen().availableGeometry() if khung.screen() is not None else None
    if man is not None:
        rong = min(rong, man.width() - 16)
    if rong <= khung.width():
        return
    g = khung.geometry()
    g.setWidth(rong)
    if man is not None and g.right() > man.right():
        g.moveRight(man.right())
    if man is not None and g.left() < man.left():
        g.moveLeft(man.left())
    khung.setGeometry(g)


def chuan_o_chon(cb) -> None:
    """Mọi ô chọn (1.0.69): gọn khi đóng, không giãn theo chữ dài nhất (nguyên nhân cửa sổ bị đẩy rộng ra); khi xổ, vua_danh_sach_xo mở rộng đủ chữ."""
    if cb.sizeAdjustPolicy() != QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon:
        cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    if cb.minimumContentsLength() == 0:
        cb.setMinimumContentsLength(16)


class OChonGiua(QStyledItemDelegate):
    """Ô đánh dấu nằm giữa ô (cột "Chọn"). Mô hình nhận trạng thái 0 / 2."""

    @staticmethod
    def _vung(opt, w):
        st = w.style() if w is not None else QApplication.style()
        r = QRect(0, 0, st.pixelMetric(QStyle.PixelMetric.PM_IndicatorWidth, None, w), st.pixelMetric(QStyle.PixelMetric.PM_IndicatorHeight, None, w))
        r.moveCenter(opt.rect.center())
        return r

    def paint(self, p, opt, idx):
        v = idx.data(Qt.ItemDataRole.CheckStateRole)
        if v is None:
            return super().paint(p, opt, idx)
        w = opt.widget
        st = w.style() if w is not None else QApplication.style()
        o = QStyleOptionViewItem(opt)
        self.initStyleOption(o, idx)
        o.features &= ~QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
        o.text = ''
        st.drawControl(QStyle.ControlElement.CE_ItemViewItem, o, p, w)
        c = QStyleOptionViewItem(opt)
        c.rect = self._vung(opt, w)
        c.state = (opt.state & ~QStyle.StateFlag.State_On & ~QStyle.StateFlag.State_Off) | (QStyle.StateFlag.State_On if int(getattr(v, 'value', v)) == 2 else QStyle.StateFlag.State_Off)
        st.drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorItemViewItemCheck, c, p, w)
        return None

    def editorEvent(self, ev, model, opt, idx):
        if ev.type() in (QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonDblClick) and idx.data(Qt.ItemDataRole.CheckStateRole) is not None:
            if not idx.flags() & Qt.ItemFlag.ItemIsUserCheckable or not self._vung(opt, opt.widget).contains(ev.pos()):
                return False
            if ev.type() == QEvent.Type.MouseButtonDblClick:
                return True
            v = idx.data(Qt.ItemDataRole.CheckStateRole)
            return model.setData(idx, Qt.CheckState.Unchecked if int(getattr(v, 'value', v)) == 2 else Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
        return super().editorEvent(ev, model, opt, idx)


def chuan_cot_chon(w) -> None:
    """Cột tiêu đề "Chọn" của các bảng trong w: rộng tối thiểu 50 px, ô đánh dấu giữa ô."""
    from PySide6.QtWidgets import QTableView
    for b in w.findChildren(QTableView):
        m = b.model()
        if m is None or b.property('_cot_chon_xong'):
            continue
        b.setProperty('_cot_chon_xong', True)
        for c in range(m.columnCount()):
            if str(m.headerData(c, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) or '').strip().lower() == 'chọn':
                if b.itemDelegateForColumn(c) is None:
                    b.setItemDelegateForColumn(c, OChonGiua(b))
                b.setColumnWidth(c, max(50, b.columnWidth(c)))


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
            if isinstance(obj, QComboBox) and obj.maxVisibleItems() == 10:
                obj.setMaxVisibleItems(SO_MUC_XO)        # 30/10/2026: danh sách xổ hiện nhiều mục hơn (mặc định Qt 10)
            if isinstance(obj, QComboBox):
                chuan_o_chon(obj)
            if la_cua_so_con_pabt(obj):
                chuan_hoa_cua_so_con(obj)
            return False
        if t == QEvent.Type.Hide:                       # đóng cửa sổ con: nhớ kích thước cho lần mở sau
            if isinstance(obj, QWidget) and obj.property('pabt_cua_so_con') and obj.isWindow():
                nho_kich_thuoc(obj)
            return False
        if t == QEvent.Type.Show and isinstance(obj, QWidget) and (obj.property('qss_cho_ty_le') or obj.property('qss_cho_tong')):
            _ap_kieu_cho(obj)                            # P1: kiểu riêng của widget ẩn lúc bấm A+ / A− hay đổi tông nền
        if t == QEvent.Type.Show and isinstance(obj, QTableView) and not obj.property('_co_sao_chep'):
            cho_phep_sao_chep_bang(obj)                  # 1.0.81: bảng thêm sau / hộp nhúng - bôi đen vẫn hiện tổng nhanh, Ctrl+C
        if t == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow() and \
                obj.metaObject().className() == 'QComboBoxPrivateContainer':
            vua_danh_sach_xo(obj)                       # 30/10/2026: danh sách xổ rộng đủ chữ dài nhất
        if t == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow():
            if obj.property('_da_to_mau'):              # hiện lại cửa sổ đã xử lý: chỉ nút mới (máy yếu - không duyệt lại cả cây)
                to_mau(obj)
                from PySide6.QtWidgets import QDialog as _QD, QMessageBox as _QM
                if isinstance(obj, _QD) and not isinstance(obj, _QM):
                    vua_man_hinh(obj)                   # hộp con luôn nằm giữa màn hình mỗi lần hiện
                    hen_giua_man_hinh(obj)
                return False
            ap_kieu_cay(obj)
            chuan_cot_chon(obj)
            obj.setProperty('_da_to_mau', True)
            from PySide6.QtWidgets import QDialog, QMessageBox
            if isinstance(obj, QDialog) and not isinstance(obj, QMessageBox):
                if la_cua_so_con_pabt(obj) and _nen_cuon_hop():
                    cuon_than_hop(obj)                     # 1.0.07: hộp cao hơn màn hình - thân cuộn, hàng nút luôn hiện
                vua_man_hinh(obj)
                hen_giua_man_hinh(obj)
        return False


def ap_kieu_cay(obj: QWidget) -> None:
    """Kiểu áp khi cửa sổ hiện lần đầu (_BoToMau) cho cả cây widget obj: màu + biểu tượng nút theo chữ, dòng bảng 32 px, khoảng
    cách hàng ngang, co giãn theo tỷ lệ giao diện, ô chữ hiện từ đầu. Gọi thêm cho khung TẠO SAU khi cửa sổ đã hiện (trang cửa sổ chính
    tạo khi mở lần đầu - 16/10/2026)."""
    to_mau(obj)
    for bang in obj.findChildren(QAbstractItemView):    # dòng bảng dữ liệu 32 px (đặc tả mục 3.3)
        cho_phep_sao_chep_bang(bang)                    # 1.0.04: nhấp một lần + Ctrl+C chép ô; menu chuột phải sao chép
        vh = getattr(bang, 'verticalHeader', None)
        if vh is not None and (vh().defaultSectionSize() < CAO_DONG_BANG or vh().defaultSectionSize() in _CAO_DONG_MAC_DINH):
            vh().setDefaultSectionSize(CAO_DONG_BANG)          # 1.0.17: bảng để cỡ mặc định (hoặc cỡ của một mật độ) theo mật độ đang dùng
    gian_cach(obj)
    if TY_LE[0] != 1:
        for w in [obj, *obj.findChildren(QWidget)]:
            _co_gian_widget(w, TY_LE[0])
    from PySide6.QtWidgets import QLineEdit
    for o in obj.findChildren(QLineEdit):                # chữ dài: hiện từ đầu chữ thay vì phần cuối
        if not o.hasFocus() and o.text():
            o.setCursorPosition(0)
    dat_ten_truy_cap(obj)


_RE_THE_HTML = re.compile(r'<[^>]+>')


def _chu_nhan(lb) -> str:
    """Chữ của nhãn làm tên truy cập: bỏ thẻ HTML, ký hiệu phím tắt '&', dấu ':' / '*' cuối."""
    t = _RE_THE_HTML.sub('', lb.text() or '').replace('&&', '\x01').replace('&', '').replace('\x01', '&')
    return t.split('\n')[0].strip().rstrip(':*').strip()[:120]


def nhan_cua_o_nhap(obj: QWidget) -> dict:
    """{ô nhập: QLabel} cho các ô nhập trong cây obj có nhãn đứng ngay trước nó: QFormLayout (nhãn của hàng), QGridLayout (ô bên
    trái cùng hàng), QHBoxLayout (phần tử liền trước). 1.0.55: KHÔNG lấy QLayoutItem (itemAt / itemAtPosition) - vỏ Python của mục
    bố cục (QSpacerItem, QWidgetItem không phải QObject) sống lâu hơn đối tượng C++, widget mới cấp phát trùng địa chỉ bị PySide trả
    nhầm vỏ cũ ("QSpacerItem không có objectName", có lúc sập 0xC0000005). Chỉ dùng indexOf(widget) / getItemPosition / labelForField."""
    from PySide6.QtWidgets import (QAbstractSpinBox, QBoxLayout, QComboBox, QDateEdit, QFormLayout, QGridLayout, QLabel, QLayout,
                                   QPlainTextEdit, QTextEdit)
    loai_o = (QLineEdit, QComboBox, QAbstractSpinBox, QDateEdit, QPlainTextEdit, QTextEdit)
    ds = obj.findChildren(QLayout)
    if obj.layout() is not None:
        ds.append(obj.layout())
    kq = {}
    con_cua = {}                                            # widget cha -> widget con trực tiếp (ứng viên trong các bố cục của nó)
    for lo in ds:
        pw = lo.parentWidget()
        if not isinstance(pw, QWidget):
            continue
        if pw not in con_cua:
            con_cua[pw] = [w for w in pw.children() if isinstance(w, QWidget) and not w.isWindow()]
        vt = {}
        for w in con_cua[pw]:
            i = lo.indexOf(w)
            if i >= 0:
                vt[w] = i
        if not vt:
            continue
        if isinstance(lo, QFormLayout):
            for o in vt:
                if isinstance(o, loai_o) and o not in kq:
                    lb = lo.labelForField(o)
                    if isinstance(lb, QLabel) and _chu_nhan(lb):
                        kq[o] = lb
        elif isinstance(lo, QGridLayout):
            o_tai = {}
            for w, i in vt.items():
                r, c = lo.getItemPosition(i)[:2]
                o_tai[(r, c)] = w
            for (r, c), o in o_tai.items():
                lb = o_tai.get((r, c - 1))
                if isinstance(o, loai_o) and isinstance(lb, QLabel) and o not in kq and _chu_nhan(lb):
                    kq[o] = lb
        elif isinstance(lo, QBoxLayout) and lo.direction() in (QBoxLayout.Direction.LeftToRight, QBoxLayout.Direction.RightToLeft):
            theo_vt = {i: w for w, i in vt.items()}
            for i, o in theo_vt.items():
                lb = theo_vt.get(i - 1)
                if isinstance(o, loai_o) and isinstance(lb, QLabel) and o not in kq and _chu_nhan(lb):
                    kq[o] = lb
    return kq


def gan_nhan_o_nhap(obj: QWidget) -> int:
    """Ô nhập chưa có tên truy cập lấy tên theo nhãn đứng cạnh (nhan_cua_o_nhap) và nhãn nhận ô đó làm buddy (trình đọc màn hình đọc
    "Họ tên, ô nhập" thay vì chỉ "ô nhập"; nhãn có '&' thì Alt + chữ nhảy tới ô). Không ghi đè tên / buddy đã đặt tay. Trả số ô đã gắn."""
    n = 0
    for o, lb in nhan_cua_o_nhap(obj).items():
        if lb.buddy() is None:
            lb.setBuddy(o)
        if not o.accessibleName():
            o.setAccessibleName(_chu_nhan(lb))
            n += 1
        if not o.accessibleDescription():
            mo_ta = (o.toolTip() or getattr(o, 'placeholderText', lambda: '')() or '').split('\n')[0].strip()
            if mo_ta:
                o.setAccessibleDescription(mo_ta[:200])
    return n


def dat_ten_truy_cap(obj: QWidget) -> None:
    """Tên truy cập (trình đọc màn hình / Narrator / phím tắt giọng nói) cho mọi nút và ô nhập CHƯA có tên: nút = chữ hiện trên nút, nút chỉ
    có biểu tượng = dòng đầu chú thích; ô nhập = chữ gợi ý hoặc chú thích. Không ghi đè tên đã đặt tay. Ô sửa bên trong QComboBox / QSpinBox
    bỏ qua (ô tổ hợp đã có tên của nó)."""
    from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox
    gan_nhan_o_nhap(obj)                                 # P1: ô nhập lấy tên theo nhãn đứng cạnh (đặt trước chữ gợi ý / chú thích)
    for b in obj.findChildren(QAbstractButton):
        if not b.accessibleName():
            chu = (b.text() or '').replace('&&', '\x01').replace('&', '').replace('\x01', '&').strip() or \
                (b.toolTip() or '').split('\n')[0].strip()
            if chu:
                b.setAccessibleName(chu[:120])
    for o in obj.findChildren(QLineEdit):
        if o.accessibleName() or isinstance(o.parentWidget(), (QComboBox, QSpinBox, QDoubleSpinBox)):
            continue
        chu = (o.placeholderText() or o.toolTip() or '').split('\n')[0].strip()
        if chu:
            o.setAccessibleName(chu[:120])
    for c in obj.findChildren(QComboBox):
        if not c.accessibleName() and c.toolTip():
            c.setAccessibleName(c.toolTip().split('\n')[0].strip()[:120])


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
    from . import chu_de
    ct = chu_de.doc(cai_dat_nho())
    chu_de.dat_phuong_an(ct['phuong_an_navy'])
    dat_mat_do(ct['mat_do'], ap_lai=False)
    dat_tong_nen(ct['tong_nen'], ap_lai=False)          # 1.0.33: tông nền đã chọn (offscreen / kiểm thử: luôn 'sang')
    p = bang_mau_ung_dung()
    app._tuong_phan_cao = chu_de.dang_tuong_phan_cao(ct['tuong_phan'])
    if app._tuong_phan_cao:                              # Windows tương phản cao: bảng màu hệ thống, chỉ giữ kích thước / khoảng đệm
        app.setPalette(app.style().standardPalette())
        app.setStyleSheet(_qss_tuong_phan_cao())
    else:
        app.setPalette(p)
        app.setStyleSheet(_qss_day_du())
    tr = QTranslator(app)
    if tr.load(QLocale('vi'), 'qtbase', '_', QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(tr)
    app._bo_to_mau = _BoToMau(app)
    app.installEventFilter(app._bo_to_mau)
    # tỷ lệ cỡ chữ người dùng đã chọn (A+ / A−). Chạy không màn hình (kiểm thử, 1.0.32): KHÔNG đọc của máy thật - trước đây lượt
    # kiểm thử chạy ở 110% khi máy phát triển đặt 110%, kết quả bài kiểm kiểu chữ phụ thuộc máy / thứ tự bài
    t = ty_le_da_luu()
    if abs(t - 1) > 0.001:
        dat_ty_le(t, luu=False)

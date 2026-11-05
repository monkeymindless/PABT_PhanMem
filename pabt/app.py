"""Cửa sổ chính phần mềm PABT: nhập file Excel, danh sách hộ, lập phương án từng hộ, thông tin dự án, rà soát giá, đối chiếu."""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QEvent, QModelIndex, QSortFilterProxyModel, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QBrush, QColor, QFont, QKeySequence
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel,
                               QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QSizePolicy,
                               QStackedWidget, QTableView, QTableWidget, QTableWidgetItem, QToolButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import BAN_THU_NGHIEM, NHAN_THU_NGHIEM, __version__, csdl, khoa, lap_pa, may_chu, nghiep_vu
from .tien import D, so_luong_vn, so_vn, vn, vn_gon
from .giao_dien import TOKEN, chuyen_trang_muot, chu_hien, con_tro_cho, dat_kieu_theo_tong, dung_ve, phong_so
from .giao_dien import mau_o_theo_tong  # noqa: E402  (màu ô đổi theo tông nền)
from .thong_bao import TEN_UD, chu_loi

# doi_chieu, nhap_excel, nhap_tho (kéo theo openpyxl ~0,2 giây - 60% thời gian nạp mã lúc mở phần mềm) nạp khi dùng tới

TIEU_DE_CUA_SO = 'LARC' + (f' ({NHAN_THU_NGHIEM})' if BAN_THU_NGHIEM else '')   # tên hiển thị (15/10/2026: PABT -> LARC)
MO_TA_UD = 'Lập phương án bồi thường, hỗ trợ'      # tiêu đề cửa sổ khi chưa mở dự án
# danh sách hộ ở màn hình chính: gọn (0.9.12). Tiền từng mục, quyết định, chi trả, bàn giao, ghi chú: menu "Bảng tổng hợp",
# "Theo dõi tiến độ" (man_hinh_theo_doi)
COT = ['STT', 'Họ và tên', 'Địa chỉ', 'Số thửa', 'DT thu hồi (m²)', 'Trạng thái', 'Ghi chú']
MAU_LECH = mau_o_theo_tong(globals(), MAU_LECH='#F8CBAD')[0]          # vàng cam: hộ lệch so với file Excel đối chiếu
COT_SO = {4}
# cột Trạng thái danh sách hộ (Hybrid Enterprise Navy, 17/10/2026): thanh tiến độ 4 ô bằng ký tự khối Unicode (■ □ - có trong
# Segoe UI / Arial của Windows 7, KHÔNG phải emoji) + màu theo nấc. Chữ trạng thái và giá trị lọc giữ nguyên (BangHo.dong[r]['o'][5])
THANH_NAC = ('□□□□', '■□□□', '■■□□', '■■■□', '■■■■')
NHAN_NAC = ('Chưa lập PA', 'Đã lập PA', 'Đã phê duyệt', 'Đã chi trả', 'Đã bàn giao')
MAU_NAC = ('#64748B', '#1F76A6', '#1E3A5F', '#1F6F66', '#2F7D54')
MAU_MA_HO = '#1F76A6'                    # cột STT (định danh hộ trên danh sách)
CAN_PHAI = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
CAN_TRAI = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
CAN_GIUA = int(Qt.AlignmentFlag.AlignCenter)
COT_GIUA = {0, 3}             # 1.0.03: STT, Số thửa căn giữa (tiêu đề + dữ liệu); DT thu hồi căn phải
# bề rộng cột danh sách hộ sau khi tự canh: {cột: (tối thiểu, tối đa)} - Ghi chú (cột cuối) giãn lấp phần còn lại
RONG_COT_DS = {0: (48, 64), 3: (64, 80), 4: (100, 120), 5: (200, 250), 6: (90, 150)}      # 1.0.16: hẹp hơn - Họ và tên / Địa chỉ (giãn) nhận thêm chỗ trên 1366 @125%
COT_GIAN_DS = (1, 2)          # Họ và tên, Địa chỉ: giãn / co theo khung nhìn
TAT_CA_DOT, TAT_CA_TRANG_THAI = 'Đợt: Tất cả', 'Trạng thái: Tất cả'     # mục đầu ô lọc (thay nhãn "Đợt:" riêng)
CAO_DAI_CONG_CU = 32                    # hàng công cụ + lọc danh sách hộ, dải cộng dưới bảng
# nút "Mở" của bảng dự án gần đây: viền + chữ navy, rê chuột nền navy chữ trắng (bộ chọn #id thắng tô màu theo chữ "Mở" của _BoToMau)
QSS_NUT_MO_GAN = ('QPushButton#nut_mo_gan { padding: 2px 14px; border: 1px solid #1E3A5F; border-radius: 4px; color: #1E3A5F; '
                  'background: #FFFFFF; font-weight: 600; } '
                  'QPushButton#nut_mo_gan:hover { background: #1E3A5F; color: #FFFFFF; } '
                  'QPushButton#nut_mo_gan:pressed { background: #092240; color: #FFFFFF; }')
# dải cộng dưới danh sách hộ: (khóa, nhãn). Tài sản & Cây = mục 2 nhà + 3 cây + vật nuôi (MUC_VN 7); Hỗ trợ & Thưởng = mục 4 + 5
O_DAI_CONG = (('so_ho', 'CỘNG'), ('dt', 'Tổng DT'), ('dat', 'Đất'), ('tai_san', 'Tài sản & Cây'),
              ('ho_tro', 'HT & Thưởng'), ('tong', 'TỔNG CỘNG'))


def so_thua_dong(d: dict) -> int:
    """Số thửa của một dòng danh sách hộ (dòng cũ / dựng tay chưa có khóa so_thua: cột Số thửa)."""
    v = d.get('so_thua')
    if v is None:
        o = d.get('o') or ()
        v = o[3] if len(o) > 3 else 0
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def dia_chinh(dong: list) -> tuple:
    """(số hộ, số thửa, tổng DT thu hồi Decimal) của các dòng danh sách hộ (21/10/2026: thẻ KPI, thanh trạng thái, thống kê)."""
    return len(dong), sum(so_thua_dong(d) for d in dong), sum((D(d.get('dt') or 0) for d in dong), D(0))


def chu_tinh_lai_cong_thuc(kq: dict) -> str:
    """Câu báo sau khi mở dự án đã tính lại số lượng nhập bằng công thức (lap_pa.tinh_lai_cong_thuc)."""
    chu = []
    if kq.get('so_dong'):
        chu.append(f"Đã tính lại {kq['so_dong']} số lượng / diện tích nhập bằng công thức ({kq['so_ho']} hộ) theo 2 chữ số lẻ; "
                   'thành tiền đã cập nhật (Hoàn tác được: Ctrl+Z).')
    if kq.get('bo_qua_khoa'):
        chu.append(f"{kq['bo_qua_khoa']} dòng thuộc lần phương án đã phê duyệt: giữ nguyên số đã trình.")
    return ' '.join(chu)


def so_ha(dt) -> str:
    """m² -> chữ héc-ta: "14,64 ha" (từ 1 ha: 2 chữ số lẻ; nhỏ hơn: 4 chữ số lẻ - "0,0325 ha")."""
    ha = D(dt) / 10000
    return f'{vn(ha, 2 if abs(ha) >= 1 else 4)} ha'


# nhóm hộ của 6 thẻ KPI (cùng cờ với bộ lọc trạng thái): (số hộ, số thửa, DT) - Tổng kinh phí = toàn dự án
def nhom_dia_chinh(dong: list, lap: dict | None = None) -> dict:
    """{khóa thẻ: (số hộ, số thửa, DT)}; lap = lap_pa.phan_loai_lap (đã lập = 'da_lap'; không có: tổng > 0)."""
    if lap:
        da_pa = [d for d in dong if lap.get(d['ma_ho']) == 'da_lap']
    else:
        da_pa = [d for d in dong if d.get('tong', 0) > 0]
    return dict(so_ho=dia_chinh(dong), da_pa=dia_chinh(da_pa),
                da_pd=dia_chinh([d for d in dong if d.get('da_phe_duyet')]),
                da_ct=dia_chinh([d for d in dong if d.get('da_chi_tra')]),
                da_bg=dia_chinh([d for d in dong if d.get('da_ban_giao')]), tong=dia_chinh(dong))


def cong_dai_cong(dong: list) -> dict:
    """Cộng các dòng danh sách hộ (BangHo.dong) cho dải cộng - Decimal (tien.D), không float. Mục theo nghiep_vu (1 đất, 2 nhà,
    3 cây, 7 vật nuôi, 4 hỗ trợ, 5 thưởng); TỔNG CỘNG = cộng tổng từng hộ (đã làm tròn như cột tổng phương án)."""
    kq = dict(dt=D(0), dat=D(0), tai_san=D(0), ho_tro=D(0), tong=D(0), so_thua=0)
    for d in dong:
        m = d.get('muc') or {}
        kq['so_thua'] += so_thua_dong(d)
        kq['dt'] += D(d.get('dt') or 0)
        kq['dat'] += D(m.get(1) or 0)
        kq['tai_san'] += D(m.get(2) or 0) + D(m.get(3) or 0) + D(m.get(nghiep_vu.MUC_VN) or 0)
        kq['ho_tro'] += D(m.get(4) or 0) + D(m.get(5) or 0)
        kq['tong'] += D(d.get('tong') or 0)
    return kq


def chu_dai_cong(n: int, tong: dict | None) -> dict:
    """{khóa: (chữ đầy đủ, chữ gọn)} của dải cộng; tong None = chưa có dữ liệu. Chữ gọn (màn hình hẹp 1366): nhãn ngắn, tiền
    vn_gon ("23,0 tỷ") - số đủ ở chú thích."""
    kq = {}
    for k, ten in O_DAI_CONG:
        if k == 'so_ho':
            t = tong.get('so_thua', 0) if tong is not None else 0
            kq[k] = (f'CỘNG ({n} HỘ · {t} THỬA)', f'CỘNG {n} HỘ · {t} THỬA') if tong is not None else ('CỘNG', 'CỘNG')
        elif tong is None:
            kq[k] = (f'{ten}: –', f'{NHAN_GON_CONG[k]}: –')
        elif k == 'dt':
            kq[k] = (f'{ten}: {so_luong_vn(tong["dt"])} m² ({so_ha(tong["dt"])})', f'{NHAN_GON_CONG[k]}: {so_luong_vn(tong["dt"])} m²')
        else:
            kq[k] = (f'{ten}: {vn(tong[k])} đ', f'{NHAN_GON_CONG[k]}: {vn_gon(tong[k])}')
    return kq


NHAN_GON_CONG = {'dt': 'DT', 'dat': 'Đất', 'tai_san': 'TS & Cây', 'ho_tro': 'HT & Thưởng', 'tong': 'TỔNG'}


class DaiCong(QFrame):
    """Dải cộng dưới danh sách hộ: đủ chỗ thì chữ đầy đủ, hẹp thì chữ gọn (chú thích luôn đầy đủ); vẫn thiếu thì rút "…"."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from .giao_dien import NhanRutGon
        self.setObjectName('dai_cong_ds')
        self.setFixedHeight(CAO_DAI_CONG_CU)
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 0, 10, 0)
        h.setSpacing(8)
        h.setProperty('giu_khoang_cach', True)
        self.o, self.vach, self.chu = {}, [], {}
        for i, (k, _ten) in enumerate(O_DAI_CONG):
            if i:
                v = QLabel('|')
                v.setProperty('vai', 'vach_cong')
                h.addWidget(v)
                self.vach.append(v)
            o = NhanRutGon('')
            o.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)     # đủ chỗ: hiện đủ; hẹp: rút "…"
            o.setProperty('vai', 'o_cong_tong' if k == 'tong' else 'o_cong')
            h.addWidget(o)
            self.o[k] = o
        h.addStretch(1)
        self.gon = False

    def dat(self, chu: dict) -> None:
        self.chu = chu
        self._chon()

    def _chon(self) -> None:
        if not self.chu:
            return
        m = self.layout().contentsMargins()
        con = self.width() - m.left() - m.right() - sum(v.sizeHint().width() + 2 * self.layout().spacing() for v in self.vach)
        can = sum(self.o[k].fontMetrics().horizontalAdvance(day) + 4 for k, (day, _gon) in self.chu.items())
        self.gon = can > con
        for k, (day, gon) in self.chu.items():
            self.o[k].setText(gon if self.gon else day)
            self.o[k].setToolTip(day)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._chon()

    def changeEvent(self, e):                           # phông đổi (QSS áp lúc hiện, phóng to): đo lại
        super().changeEvent(e)
        if e.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._chon()
# các trang bên phải cửa sổ chính (chọn ở menu trái). 0.9.76 (Mục IV QĐ 18/2026, Nhóm 5 - 6): Bảng tổng hợp kinh phí là MỘT trang 3 thẻ
# (cơ cấu, chi tiết hộ, đối soát khái toán); Quyết định phê duyệt; Tiến độ chi trả & Bàn giao (1.0.00: gộp trang "Báo cáo tiến độ
# GPMB" - thẻ chỉ số + chế độ xem "Thửa còn vướng" - vào trang theo dõi; man_hinh_theo_doi.KhungTienDo); Dự toán / khái toán (0.9.23 -
# lộ trình người dùng: mục tiêu tài chính của DỰ ÁN, trang trong cửa sổ chính). Ctrl+1..5 theo thứ tự này
TRANG = ['Danh sách hộ', 'Tổng hợp tiền theo phương án', 'Quyết định phê duyệt', 'Theo dõi tiến độ', 'Dự toán & khái toán']
TRANG_DS, TRANG_TONG_HOP, TRANG_QUYET_DINH, TRANG_THEO_DOI, TRANG_DU_TOAN = range(5)
TRANG_CHAO = 4                     # chỉ số trong self.trang (QStackedWidget) của màn hình chào khi chưa mở dự án
SAO_LUU_SAU_MS = 1500             # 1.0.08: sao lưu tự động dự án vừa mở để sửa - sau khi cửa sổ đã vẽ xong
DUOI_KEO_THA = ('.larc', '.pabt', '.larcud', '.pabtcn', '.pabtcfg', '.xlsx', '.xlsm')   # file kéo thả nhận được
# chỉ số TRANG -> chỉ số trong self.trang (QStackedWidget): 0 danh sách, 1 bảng tổng hợp, 2 theo dõi, 3 dự toán, 4 chào, 5 quyết định
# (các trang mới thêm cuối để giữ nguyên chỉ số cũ)
STACK_CUA_TRANG = (0, 1, 5, 2, 3)
# phím tắt nhanh (người dùng 20/10/2026): Ctrl+1 Danh sách hộ, Ctrl+2 Khái toán & Dự toán, Ctrl+3 Đơn giá bồi thường (tab bộ đơn
# giá), Ctrl+4 Niêm yết & Lấy ý kiến (tab), Ctrl+5 Tiến độ & Bàn giao; Ctrl+K Tìm nhanh (CCCD, mã hộ, họ tên, tờ/thửa, chức năng).
# Tổng hợp tiền / Quyết định phê duyệt không có phím số - mở bằng menu trái hoặc Ctrl+K
PHIM_NHANH = (('Danh sách hộ', 'Ctrl+1'), ('Dự toán & khái toán', 'Ctrl+2'), ('Bộ đơn giá…', 'Ctrl+3'),
              ('Dự thảo PABT…', 'Ctrl+4'), ('Theo dõi tiến độ', 'Ctrl+5'), ('Tìm nhanh…', 'Ctrl+K'))
STACK_TONG_HOP, STACK_THEO_DOI, STACK_DU_TOAN, STACK_QUYET_DINH = 1, 2, 3, 5
XANH, DO, VANG = mau_o_theo_tong(globals(), XANH='#E2EFDA', DO='#F8CBAD', VANG=TOKEN['canh_bao_nhat'])
# menu trái: nhóm đóng sẵn lần đầu mở phần mềm (sau đó nhớ theo người dùng) - vừa màn hình 1366x768 không phải cuộn
# 0.9.70 (6 nhóm): nhóm ít dùng hằng ngày đóng sẵn - Khái toán (giai đoạn chuẩn bị đầu tư), Đơn giá, Phê duyệt & bàn giao
# 0.9.88 (người dùng 15/10/2026): nhóm Đơn giá & bảng giá xuống cuối (6); đóng sẵn 1, 5, 6 - mở sẵn 2, 3, 4 (thao tác hằng ngày)
NHOM_DONG_MAC_DINH = ('1. Khái toán & dự toán', '5. Phê duyệt & bàn giao', '6. Đơn giá & bảng giá')
GAN_DAY_TOI_DA = 30                # số dự án nhớ trong danh sách "Dự án làm việc gần đây" (26/10/2026: 8 -> 30, bảng giãn hết màn hình chào)
# 0.9.80: chưa mở dự án thì các lệnh của dự án bị làm mờ (QAction tắt); mở / đóng dự án thì bật / tắt lại. Từ 0.9.88 (thứ tự nhóm
# mới): nhóm 3 (Lập phương án), 4 (Tổng hợp & trình duyệt), 5 (Phê duyệt & bàn giao) + Đơn giá đặc biệt của nhóm 6. Nhóm 1 (khái
# toán), 2, Đơn giá bồi thường, Bảng giá đất và Màn hình chính vẫn dùng được khi chưa có dự án
LENH_CAN_DU_AN = ('Lập phương án hộ…', 'Dự thảo PABT…', 'Kiểm tra lỗi…', 'Xuất báo cáo đối chiếu…',
                  'Tổng hợp tiền theo phương án', 'Đợt trình…', 'In / Xuất…',
                  'Quyết định phê duyệt', 'Theo dõi tiến độ', 'Nhật ký kiểm toán…', 'Xem hộ trên bản đồ…',
                  # nhóm 6 Đơn giá & bảng giá: Đơn giá đặc biệt là của DỰ ÁN (tắt khi chưa mở); Đơn giá bồi thường, Bảng giá đất vẫn
                  # bật (liên kết chân màn hình chào, tra cứu khi chưa có dự án)
                  'Đơn giá riêng dự án…',
                  # 21/10/2026: thống kê Hộ · Thửa · Diện tích (menu Dữ liệu + huy hiệu "Lọc:" cuối hàng lọc danh sách hộ)
                  'Thống kê Hộ · Thửa · Diện tích…',
                  # 30/10/2026: mốc khôi phục của dự án đang mở (menu Tệp tin)
                  'Cỗ máy thời gian (mốc khôi phục)…',
                  'Chọn hộ niêm yết…')
LENH_THONG_KE = 'Thống kê Hộ · Thửa · Diện tích…'
# Nhập bản vẽ CAD, Phiếu kiểm đếm (menu Dữ liệu / Công cụ, 0.9.87): KHÔNG tắt khi chưa mở dự án - mục menu mờ bấm không có phản
# ứng, người dùng tưởng hỏng; bấm thì báo "mở dự án trước" (_can_du_an).
# nút A− / A+ trên thanh trạng thái: khung nút nhỏ, viền nhẹ, bo 4px
QSS_NUT_ZOOM = ('QToolButton#nut_zoom { border: 1px solid #8696AB; border-radius: 4px; padding: 1px 8px; background: #FFFFFF; '
                'color: #1E293B; font-weight: 600; }'
                'QToolButton#nut_zoom:hover { background: #F1F5F9; border-color: #94A3B8; }'
                'QToolButton#nut_zoom:pressed { background: #E2E8F0; }')
# chữ ngắn trên menu (khóa = tên lệnh đầy đủ trong self.lenh, hiện ở gợi ý khi rê chuột)
NHAN_MENU = {'Lập phương án hộ…': 'Lập phương án chi tiết', 'Thêm hộ…': 'Thêm hộ', 'Xóa hộ…': 'Xóa hộ',
             'Tiếp nhận & Kiểm tra pháp lý dự án…': 'Tiếp nhận hồ sơ pháp lý',
             'Kiểm tra lỗi…': 'Kiểm tra lỗi pháp lý',
             # 0.9.70 (đặc tả ARCH-PABT-2026-V7, người dùng 12/10/2026): chữ trên menu trái theo 6 nhóm nghiệp vụ
             'Dự toán & khái toán': 'Lập khái toán & Dự toán', 'Danh sách hộ': 'Danh sách hộ và Thửa',
             'Theo dõi tiến độ': 'Tiến độ chi trả & Bàn giao',
             'Bộ đơn giá…': 'Đơn giá bồi thường', 'Đơn giá riêng dự án…': 'Đơn giá đặc biệt', 'Rà soát giá…': 'Rà soát giá',
             'Thông tin dự án…': 'Thông tin dự án',
             'Bảng giá đất NQ 28…': 'Bảng giá đất',
             'Cập nhật bảng giá đất…': 'Cập nhật giá đất',
             'Tính đơn giá đất QĐ 03…': 'Tính đơn giá đất',
             'Dự thảo PABT…': 'Niêm yết & Lấy ý kiến',
             'Tổng hợp tiền theo phương án': 'Bảng tổng hợp kinh phí',
             'Quyết định phê duyệt': 'Quyết định phê duyệt', 'Đợt trình…': 'Đợt trình thẩm định',
             'Trạng thái hộ…': 'Trạng thái hộ',
             'In / Xuất…': 'Xuất hồ sơ & Bản in', 'Quản lý Mẫu in & Bản in…': 'Quản lý Mẫu in & Bản in…',
             'Xuất báo cáo đối chiếu…': 'Đối chiếu số liệu',
             'Nhập bản vẽ CAD (.dxf)…': 'Nhập bản đồ (.dxf, .kml, .kmz)…'}      # 1.0.32: cả bản đồ KML / KMZ (Google Earth)
# 0.9.69 (người dùng 12/10/2026 đổi tên): gợi ý khi rê chuột theo tên mới (khóa self.lenh giữ tên cũ - mã / test gọi theo khóa)
GOI_Y_MENU = {'Bộ đơn giá…': 'Đơn giá bồi thường (bộ đơn giá nhà, cây, vật nuôi, chính sách hỗ trợ)',
              'Đơn giá riêng dự án…': 'Đơn giá đặc biệt của dự án (nhập tay, thẩm định giá)',
              'Dự thảo PABT…': 'Niêm yết công khai dự thảo phương án và lấy ý kiến',
              'Đợt trình…': 'Đợt trình thẩm định: đợt trình, số phương án, văn bản trình',
              'Dự toán & khái toán': 'Lập khái toán & dự toán (giai đoạn chuẩn bị đầu tư - file .pabtdt riêng)',
              'So sánh với thực tế': 'So sánh khái toán đã duyệt với số liệu áp giá thực tế của dự án',
              'Tiếp nhận & Kiểm tra pháp lý dự án…': 'Tiếp nhận & kiểm tra pháp lý hồ sơ đầu vào (32 mục, thời hạn chủ trương, '
                                                      'kỹ thuật địa chính) - dùng được khi chưa có dự án (Ctrl+Shift+L)',
              'Danh sách hộ': 'Danh sách hộ và thửa đất của dự án',
              'Tổng hợp tiền theo phương án': 'Bảng tổng hợp kinh phí: cơ cấu, chi tiết từng hộ, đối soát khái toán',
              'Xuất báo cáo đối chiếu…': 'Đối chiếu số liệu với file Excel kiểm đếm (xuất báo cáo)',
              'In / Xuất…': 'Xuất hồ sơ & bản in: phương án chi tiết, bảng tổng hợp, tờ trình',
              'Theo dõi tiến độ': 'Tiến độ chi trả & bàn giao: tỷ lệ giải ngân, mặt bằng sạch, thửa còn vướng, mốc thu hồi đất, vận '
                                  'động và cưỡng chế; báo cáo tiến độ GPMB',
              'Quyết định phê duyệt': 'Quản lý quyết định phê duyệt phương án và các hộ của từng quyết định'}
# 1.0.03: lệnh menu trái mở trang nhúng / chế độ - đánh dấu khi đang xem (cùng TRANG và 'Màn hình chính'; app._dong_bo_menu_trai)
LENH_DANH_DAU_PHU = ('Lập phương án hộ…', 'Dự thảo PABT…', 'Bộ đơn giá…', 'So sánh với thực tế')
TEN_TAB = {'don_gia': 'Đơn giá bồi thường', 'du_thao': 'Niêm yết && Lấy ý kiến'}   # "&&": QTabBar hiện "&"


def _file_gan_day() -> Path:
    return may_chu.thu_muc_may() / 'du_an_gan_day.json'


def doc_gan_day() -> list:
    """Đường dẫn các dự án mở gần đây (mới nhất trước) - màn hình chào."""
    import json
    try:
        ds = json.loads(_file_gan_day().read_text(encoding='utf-8'))
        return [str(x) for x in ds if isinstance(x, str)]
    except (OSError, ValueError):
        return []


def _con_tren_dia(x) -> bool:
    """False chỉ khi CHẮC file đã mất: ổ đĩa / thư mục dùng chung còn truy cập được mà không có file. Ổ mạng / USB đang ngắt
    -> giữ lại trong danh sách (cắm lại là mở được)."""
    f = Path(x)
    try:
        return f.is_file() or not Path(f.anchor).exists()
    except OSError:
        return True


def ghi_gan_day(p) -> None:
    import json
    try:
        moi = str(Path(p).resolve())
        # bỏ file không còn trên đĩa (15/10/2026): trước đây file tạm đã xóa vẫn chiếm chỗ trong GAN_DAY_TOI_DA mục, đẩy dự án thật
        # ra khỏi danh sách -> bảng "Dự án làm việc gần đây" trống dù vừa mở dự án
        ds = [moi] + [x for x in doc_gan_day() if x.lower() != moi.lower() and _con_tren_dia(x)]
        f = _file_gan_day()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(ds[:GAN_DAY_TOI_DA], ensure_ascii=False, indent=1), encoding='utf-8')
    except OSError:                                     # thư mục máy không ghi được: bỏ qua, không ảnh hưởng mở dự án
        pass


def bo_gan_day(p) -> list:
    """Xóa một đường dẫn khỏi danh sách dự án gần đây (file trên đĩa giữ nguyên)."""
    import json
    ds = [x for x in doc_gan_day() if x.lower() != str(Path(p)).lower()]
    try:
        f = _file_gan_day()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(ds[:GAN_DAY_TOI_DA], ensure_ascii=False, indent=1), encoding='utf-8')
    except OSError:
        pass
    return ds


def _file_ghim() -> Path:
    return may_chu.thu_muc_may() / 'du_an_ghim.json'


def doc_ghim() -> list:
    """Đường dẫn dự án được ghim lên đầu lưới gần đây."""
    import json
    try:
        ds = json.loads(_file_ghim().read_text(encoding='utf-8'))
        return [str(x) for x in ds if isinstance(x, str)]
    except (OSError, ValueError):
        return []


def ghim_du_an(p, ghim: bool = True) -> list:
    """Ghim / bỏ ghim một file .pabt. Trả danh sách ghim mới."""
    import json
    moi = str(Path(p).resolve())
    ds = [x for x in doc_ghim() if x.lower() != moi.lower()]
    if ghim:
        ds.insert(0, moi)
    try:
        f = _file_ghim()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(ds, ensure_ascii=False, indent=1), encoding='utf-8')
    except OSError:
        pass
    return ds


def _file_tong_du_an() -> Path:
    return may_chu.thu_muc_may() / 'tong_du_an.json'


def _doc_tong_nho() -> dict:
    import json
    try:
        d = json.loads(_file_tong_du_an().read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi_tong_nho(p, so_ho: int, tong, chu_tim: str | None = None, hien: str | None = None) -> None:
    """Nhớ tổng kinh phí CHUẨN (cùng cách tính danh sách hộ: mọi mục kể cả thưởng, làm tròn như dự án) của file dự án theo thời
    điểm sửa + cỡ file - màn hình chào hiện đúng số mà không tính lại cả dự án (0.9.95). 16/10/2026 (máy yếu): nhớ cả chữ tìm và tên
    hiển thị - file không đổi thì màn hình chào KHÔNG mở file dự án nào (ổ mạng / Google Drive / HDD chậm). Lỗi ghi: bỏ qua."""
    import json
    try:
        st = Path(p).stat()
        d = _doc_tong_nho()
        k = str(Path(p).resolve()).lower()
        cu = d.get(k)
        if chu_tim is None and isinstance(cu, list) and len(cu) >= 6 and cu[:2] == [st.st_mtime_ns, st.st_size]:
            chu_tim, hien = cu[4], cu[5]                # dự án đang mở ghi lại tổng: giữ tên đã nhớ
        d[k] = [st.st_mtime_ns, st.st_size, int(so_ho), str(tong)] + ([chu_tim, hien] if chu_tim is not None else [])
        if len(d) > 60:                                 # chỉ giữ các file gần đây
            for k in list(d)[:len(d) - 60]:
                d.pop(k, None)
        f = _file_tong_du_an()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
    except (OSError, ValueError):
        pass


def _tom_tat_pabt(p) -> tuple:
    """(số hộ, chuỗi tổng tiền, chữ để tìm: tên dự án + địa bàn, tên hiển thị) đọc file dự án chỉ xem; lỗi / khóa ->
    (None, None, '', tên file). Tổng = tổng kinh phí như danh sách hộ (0.9.95: trước đây cộng thô ct_dat / ct_khoan - thiếu thưởng
    bàn giao mặt bằng, không làm tròn, lệch số danh sách hộ). Tính một lần mỗi khi file đổi (ghi_tong_nho), lần sau đọc nhớ.
    Tên hiển thị: "<tên dự án> · <địa bàn> (<tên file>)" khi có tên dự án."""
    p = Path(p)
    try:                                                # file không đổi từ lần đọc trước: lấy ngay, không mở SQLite
        st = p.stat()
        nho = _doc_tong_nho().get(str(p.resolve()).lower())
        if isinstance(nho, list) and len(nho) >= 6 and nho[0] == st.st_mtime_ns and nho[1] == st.st_size:
            tong = D(nho[3])
            return int(nho[2]), (vn(tong) if tong else None), str(nho[4]), str(nho[5])
    except (OSError, ValueError, TypeError, ArithmeticError):
        pass
    try:
        con = csdl.mo(str(p), chi_doc=True)
        try:
            n = con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
            ten = dia_ban = ''
            try:
                r = con.execute('SELECT ten, cap_dia_ban, ten_dia_ban FROM du_an WHERE id = 1').fetchone()
                chu_tim = ' '.join(x for x in (r or ()) if x)
                if r is not None:
                    ten, dia_ban = str(r[0] or '').strip(), str(r[2] or '').strip()
            except sqlite3.Error:
                chu_tim = ''
            hien = (f'{ten}' + (f' · {dia_ban}' if dia_ban else '') + f' ({p.name})') if ten else p.name
            tong = None
            try:
                st = p.stat()
                nho = _doc_tong_nho().get(str(p.resolve()).lower())
                if nho and nho[0] == st.st_mtime_ns and nho[1] == st.st_size:
                    tong = D(nho[3])
            except (OSError, ValueError, IndexError, TypeError):
                pass
            if tong is None and n:
                try:
                    tong = sum((k.tong for k in nghiep_vu.tinh_tat_ca(con)), D('0'))
                except Exception:                       # file cũ / hỏng: không hiện tổng, vẫn liệt kê
                    tong = None
            if tong is not None or not n:
                ghi_tong_nho(p, n, tong if tong is not None else D('0'), chu_tim, hien)
            return n, (vn(tong) if tong else None), chu_tim, hien
        finally:
            con.close()
    except Exception:
        return None, None, '', p.name


def file_huong_dan():
    """HUONG_DAN.md: đóng gói cạnh mã (bản cài: _internal) hoặc ở gốc mã nguồn."""
    ds = [Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)) / 'HUONG_DAN.md'] if getattr(sys, 'frozen', False) else []
    ds.append(Path(__file__).resolve().parents[1] / 'HUONG_DAN.md')
    return next((f for f in ds if f.exists()), None)


class TheSo(QWidget):
    """Thẻ số liệu ở đầu cửa sổ chính - bấm để lọc danh sách hộ theo chỉ số đó (0.9.23: thẻ tương tác, lộ trình người dùng)."""
    bam = Signal()
    thanh = None                    # 1.0.52: thanh tiến độ NỔI sát mép dưới (không trong bố cục - không đè dòng diện tích)
    LE_THANH = (10, 3)              # (lề trái / phải, cách mép dưới) của thanh tiến độ

    cao_toi_thieu = 62              # = CuaSoChinh.CAO_THE_SO (cỡ chữ 100%)
    _hen_vua = False

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._dat_thanh()

    def event(self, e):
        # 1.0.52: cỡ chữ của phần mềm 110 - 140% (A+): chữ 3 dòng cần cao hơn 62 px - thẻ cao theo nội dung (100% vẫn 62 px)
        if e.type() in (QEvent.Type.Show, QEvent.Type.StyleChange, QEvent.Type.FontChange) and not self._hen_vua:
            self._hen_vua = True
            QTimer.singleShot(0, self.vua_cao)
        return super().event(e)

    def vua_cao(self):
        self._hen_vua = False
        lo = self.layout()
        if lo is None:
            return
        lo.activate()
        can = max(self.cao_toi_thieu, lo.minimumSize().height() + 8)    # + chỗ thanh tiến độ nổi ở đáy (cách chữ 3 px)
        if self.height() != can or self.minimumHeight() != can:
            self.setFixedHeight(can)

    def _dat_thanh(self):
        t = self.thanh
        if t is None:
            return
        le, duoi = self.LE_THANH
        cao = max(3, t.maximumHeight() if t.maximumHeight() < 50 else 5)
        t.setGeometry(le, self.height() - duoi - cao, max(10, self.width() - 2 * le), cao)
        t.raise_()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint() if hasattr(e, 'position')
                                                                          else e.pos()):
            self.bam.emit()
        super().mouseReleaseEvent(e)


class LocHo(QSortFilterProxyModel):
    """Lọc danh sách hộ theo đợt trình, trạng thái xử lý và từ khóa."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dot = ''                  # '' tất cả / 'chua' chưa xếp đợt / id đợt
        self.trang_thai = ''           # khóa trong quan_ly.TRANG_THAI
        self.tu_khoa = []
        self.chi_ma = None             # 1.0.29: tập mã hộ chỉ hiện (bản offline theo hộ - "Chỉ hiện hộ tôi nhận"); None = mọi hộ
        self._hop_tt = None            # quan_ly.hop_trang_thai - nạp khi lần đầu lọc theo trạng thái (không nạp lúc mở phần mềm)

    def dat(self, dot=None, trang_thai=None, tu_khoa=None, chi_ma=False):
        moi = hasattr(self, 'endFilterChange')          # Qt 6.10+: invalidateFilter() lỗi thời; Qt5 / Qt6 cũ chưa có begin/end
        if moi:
            self.beginFilterChange()
        if dot is not None:
            self.dot = dot
        if trang_thai is not None:
            self.trang_thai = trang_thai
            if trang_thai and self._hop_tt is None:
                from .quan_ly import hop_trang_thai
                self._hop_tt = hop_trang_thai
        if tu_khoa is not None:
            self.tu_khoa = lap_pa.bo_dau(tu_khoa).split()
        if chi_ma is not False:                         # False = giữ nguyên; None = bỏ lọc theo mã hộ
            self.chi_ma = chi_ma
        if moi:
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)
        else:
            self.invalidateFilter()

    def filterAcceptsRow(self, r, parent):
        # gọi cho TỪNG dòng mỗi lần lọc (5.000 hộ x mỗi phím gõ): không import / tra thuộc tính thừa ở đây
        d = self.sourceModel().dong[r]
        if self.chi_ma is not None and d.get('ma_ho') not in self.chi_ma:
            return False
        dot = self.dot
        if dot:
            if dot == 'chua':
                if d.get('dot_id'):
                    return False
            elif d.get('dot_id') != dot:
                return False
        if self.trang_thai and not self._hop_tt(d, self.trang_thai):
            return False
        tu_khoa = self.tu_khoa
        if tu_khoa:
            chu = d.get('_tim')
            if chu is None:                             # chuỗi tìm không dấu: tính một lần cho mỗi dòng rồi nhớ trên dòng
                chu = d['_tim'] = lap_pa.bo_dau(' '.join(str(x) for x in d['o']) + ' ' + d.get('tim', ''))
            return all(t in chu for t in tu_khoa)
        return True


class BangHo(QAbstractTableModel):
    """Danh sách hộ: mỗi dòng dict(ma_ho, tong, các trường trạng thái, o=[giá trị các cột COT], tim=chữ để tìm thêm)."""

    def __init__(self, dong=None):
        super().__init__()
        self.dong = dong or []

    def dat_du_lieu(self, dong):
        self.beginResetModel()
        self.dong = dong
        self.endResetModel()

    def thay_dong(self, r: int, dong: dict):
        """Thay một dòng (hộ vừa đổi): bảng lọc / sắp xếp tự cập nhật dòng đó, không dựng lại cả danh sách."""
        self.dong[r] = dong
        self.dataChanged.emit(self.index(r, 0), self.index(r, len(COT) - 1))

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.dong)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COT)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return COT[section]
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return CAN_GIUA if section in COT_GIUA else None
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        d, c = self.dong[index.row()], index.column()
        v = d['o'][c]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if c == 4:
                return so_vn(v)
            if c == 5 and role == Qt.ItemDataRole.DisplayRole:      # thanh tiến độ 4 ô + trạng thái (giá trị gốc ở d['o'][5])
                return f'{THANH_NAC[d.get("nac", 0)]}  {v}'
            return str(v)
        if role == Qt.ItemDataRole.ForegroundRole:
            if c in COT_SO:                                        # số 0 xám nhạt (giao_dien.mau_so - một nguồn)
                from .giao_dien import mau_so
                m = mau_so(so_vn(v))
                return self._but(m) if m else None
            if c == 5:
                return self._but(MAU_NAC[d.get('nac', 0)])
            if c == 0:
                return self._but(MAU_MA_HO)
            if c == 1:
                return self._but(TOKEN['chu'])                 # 1.0.34: theo tông nền (Tối: chữ sáng)
            return None
        if role == Qt.ItemDataRole.FontRole and c == 1:
            return self._phong()
        if role == Qt.ItemDataRole.FontRole and c in COT_SO:
            from .giao_dien import phong_so
            return phong_so()
        if role == Qt.ItemDataRole.ToolTipRole:
            if c == 6 and v:
                return str(v)
            if c == 5:
                return (d.get('goi_y_tt') or str(v)) + f'\nTiến độ: {NHAN_NAC[d.get("nac", 0)]} ({d.get("nac", 0)}/4)'
            if c in (1, 2):
                dau = d.get('dia_chi') or v if c == 2 else v             # cột Địa chỉ: địa chỉ đầy đủ (0.9.72)
                return f'{dau}\nMã hộ {d["ma_ho"]}' + (f'\nGhi chú: {d["theo_doi"]}' if d.get('theo_doi') else '')
            return None
        if role == Qt.ItemDataRole.UserRole:                       # giá trị để sắp xếp
            if c == 5:                                             # trạng thái: theo nấc tiến độ rồi theo chữ
                return f'{d.get("nac", 0)} {v}'
            if c in COT_SO or c in (0, 3):
                if isinstance(v, (int, float)):
                    return float(v)
                try:
                    return float(D(v))
                except Exception:
                    return 0.0
            return str(v)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            # số nguyên (như bang_ao): Qt5 / PySide2 bỏ qua cờ ghép kiểu enum -> cột số canh trái-trên (17/10/2026)
            return CAN_GIUA if c in COT_GIUA else CAN_PHAI if c in COT_SO else CAN_TRAI
        if role == Qt.ItemDataRole.BackgroundRole and c == 6 and d.get('mau_gc') is not None:
            return QBrush(d['mau_gc'])
        return None

    def _but(self, mau: str):
        b = self._nho_but.get(mau) if hasattr(self, '_nho_but') else None
        if b is None:
            self._nho_but = getattr(self, '_nho_but', {})
            b = self._nho_but[mau] = QBrush(QColor(mau))
        return b

    def _phong(self):
        """Chủ hộ: đậm nhẹ (DemiBold). Phông nhớ theo phông ứng dụng (data gọi mỗi ô mỗi lần vẽ; phóng to / thu nhỏ đổi phông)."""
        goc = QApplication.font()
        k = goc.key()
        if getattr(self, '_nho_phong', (None,))[0] != k:
            f = QFont(goc)
            f.setWeight(QFont.Weight.DemiBold)
            self._nho_phong = (k, f)
        return self._nho_phong[1]


class ChiTietHo(QDialog):
    def __init__(self, con, ma_ho, parent=None):
        super().__init__(parent)
        k = nghiep_vu.tinh_ho(con, ma_ho)
        self.setWindowTitle(f'Hộ {ma_ho} - {k.ho_ten}')
        self.resize(1050, 640)
        cay = QTreeWidget()
        cay.setColumnCount(7)
        cay.setHeaderLabels(['STT', 'Tên tài sản, khoản', 'ĐVT', 'Số lượng', 'Đơn giá', 'Tỷ lệ', 'Thành tiền (đồng)'])
        dam = QFont()
        dam.setBold(True)
        # 1.0.55: rê chuột lên dòng tiền = giải trình công thức, thay số, căn cứ (nghiep_vu.giai_trinh_dong_pa) - dòng nối theo id CSDL
        pa, bc = nghiep_vu.doc_phuong_an(con, ma_ho), nghiep_vu.BoiCanh.tu(con)
        vi_tri = {(1, r.id): (1, i) for i, r in enumerate(pa.dat) if r.id}
        vi_tri.update({(m, r.id): (m, i) for m in nghiep_vu.MUC_KHOAN for i, r in enumerate(pa.khoan[m]) if r.id})
        for muc in nghiep_vu.THU_TU_MUC:                # 1 đất, 2 nhà, 3 cây, 4 vật nuôi, 5 hỗ trợ, 6 thưởng
            goc = QTreeWidgetItem([str(nghiep_vu.so_muc(muc)), nghiep_vu.TEN_MUC[muc], '', '', '', '', vn(k.muc[muc])])
            for i in (0, 1, 6):
                goc.setFont(i, dam)
            goc.setTextAlignment(6, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            for d in (x for x in k.dong if x.muc == muc):
                tl = lap_pa.hien_ty_le(d.ty_le)
                it = QTreeWidgetItem([d.stt, d.ten, d.dvt, so_vn(d.so_luong), vn(d.don_gia),
                                      f'{tl}%' if tl else '', vn(d.thanh_tien)])
                for i in (3, 4, 5, 6):
                    it.setTextAlignment(i, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    it.setFont(i, phong_so())          # 1.0.51: số canh cột (phông số dùng chung)
                vt = vi_tri.get((muc, getattr(d, 'id', 0) or 0))
                if vt is not None:
                    chu = '\n'.join(nghiep_vu.giai_trinh_dong_pa(pa, bc, *vt)['dong'])
                    for i in (1, 6):
                        it.setToolTip(i, chu)
                if d.thanh_tien_excel is not None and d.thanh_tien_excel != d.thanh_tien:
                    it.setBackground(6, QBrush(DO))
                    it.setToolTip(6, f'Excel: {vn(d.thanh_tien_excel)}' + (f'\n\n{it.toolTip(6)}' if it.toolTip(6) else ''))
                goc.addChild(it)
            cay.addTopLevelItem(goc)
        tong = QTreeWidgetItem(['', 'TỔNG CỘNG', '', '', '', '', vn(k.tong)])
        for i in (1, 6):
            tong.setFont(i, dam)
        tong.setTextAlignment(6, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        cay.addTopLevelItem(tong)
        cay.expandAll()
        cay.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in (0, 2, 3, 4, 5, 6):
            cay.resizeColumnToContents(i)
        ghi = QPlainTextEdit()
        ghi.setReadOnly(True)
        ct = nghiep_vu.kiem_tra_ho(con, ma_ho)
        ghi.setPlainText('Cần xem lại:\n' + '\n'.join('- ' + x for x in ct) if ct else 'Không có điểm cần xem lại.')
        ghi.setMaximumHeight(120)
        lo = QVBoxLayout(self)
        lo.addWidget(cay)
        lo.addWidget(ghi)


class CuaSoChinh(QMainWindow):
    def __init__(self, menu_trai: bool = False):
        """menu_trai: các lệnh thành cột dọc bên trái (kiểu mặc định khi mở phần mềm từ 0.9.3); False: thanh nút phía trên."""
        super().__init__()
        self.menu_trai = menu_trai
        self.la_cua_so_chinh = True
        self.ht = None                                   # hoan_tac.HoanTac của dự án đang mở (Ctrl+Z / Ctrl+Y)
        self.dv = None                                   # csdl.DauVetHo: hộ vừa đổi -> tai_lai chỉ tính lại các hộ đó
        self.con = None
        self.file = None
        self.kq = None
        self.khoa = None
        self.chi_doc = False
        self.vai_tro = None                             # 1.0.57: vai trò tài khoản máy chủ cho dự án đang mở (phan_quyen)
        self.nhan_viec = None                           # 1.0.29: bản offline theo hộ - frozenset mã hộ đã nhận (may_chu.ho_nhan_viec)
        self.dong_ho = QTimer(self)                      # làm mới khóa file mỗi phút
        self.dong_ho.setInterval(khoa.LAM_MOI * 1000)
        self.dong_ho.timeout.connect(self.lam_moi_khoa)
        from .co_may_thoi_gian import CHU_KY_PHUT
        self.dong_ho_moc = QTimer(self)                  # phương án đột phá 8: mốc tự động mỗi giờ khi dự án có thay đổi
        self.dong_ho_moc.setInterval(CHU_KY_PHUT * 60 * 1000)
        self.dong_ho_moc.timeout.connect(lambda: self.chup_moc('tu_dong'))
        self.setWindowTitle(TIEU_DE_CUA_SO)
        man = QApplication.primaryScreen()
        vung = man.availableGeometry() if man else None
        self.resize(min(1360, vung.width() - 40) if vung else 1360, min(760, vung.height() - 40) if vung else 760)
        from .giao_dien import dat_toi_thieu_cua_so
        dat_toi_thieu_cua_so(self)          # đặc tả V10: tối thiểu 1024 x 680 (màn hình nhỏ hơn thì theo màn hình)
        self.lenh = {}
        from .lenh import ds_lenh
        for ten, ham in ds_lenh(self):
            a = QAction(ten, self)
            a.triggered.connect(lambda _=False, ham=ham: self._chay_lenh(ham))
            self.lenh[ten] = a
        for k, t in enumerate(TRANG):                   # mục trang ở menu trái: đánh dấu trang đang xem
            self.lenh[t].setCheckable(True)
            self.lenh[t].setChecked(k == 0)
            self.addAction(self.lenh[t])
        for t, phim in PHIM_NHANH:                      # Ctrl+1..5, Ctrl+K: gắn lên cửa sổ (chạy cả khi menu chưa từng mở)
            self.lenh[t].setShortcut(QKeySequence(phim))
            if self.lenh[t] not in self.actions():
                self.addAction(self.lenh[t])
        self.lenh['Màn hình chính'].setCheckable(True)
        # 1.0.03: mục menu trái mở TRANG NHÚNG / chế độ (hộ đang soạn, Niêm yết, Đơn giá, So sánh) cũng đánh dấu khi đang xem -
        # trước đây mở tab hộ / Niêm yết mà menu trái vẫn sáng mục trang cũ (Ảnh 6, 7, 9). Một nguồn: _dong_bo_menu_trai
        for t in LENH_DANH_DAU_PHU:
            self.lenh[t].setCheckable(True)
        # 1.0.44: nhóm độc quyền tùy chọn - bấm mục đang chọn không tự bỏ dấu (trước: QAction đảo dấu rồi _dong_bo_menu_trai
        # gắn lại = nhấp nháy nút menu trái)
        nhom_trang = QActionGroup(self)
        if hasattr(nhom_trang, 'setExclusionPolicy'):
            nhom_trang.setExclusionPolicy(QActionGroup.ExclusionPolicy.ExclusiveOptional)
        else:
            nhom_trang.setExclusive(True)
        for t in (*TRANG, 'Màn hình chính', *LENH_DANH_DAU_PHU):
            a = self.lenh.get(t)
            if a is not None:
                nhom_trang.addAction(a)
        self._nhom_trang = nhom_trang
        self.lenh['Màn hình chính'].setToolTip('Về màn hình bắt đầu (dự án mới, mở dự án, nhập Excel, dự án gần đây)')
        for ten, phim in (('Dự án mới…', 'Ctrl+N'), ('Mở dự án…', 'Ctrl+O'), ('Dự án trên máy chủ…', 'Ctrl+Shift+O'),
                          ('Lưu dự án', 'Ctrl+S'),
                          ('Lưu dự án thành…', 'Ctrl+Shift+S'), ('Hướng dẫn sử dụng', 'F1'),
                          ('Tiếp nhận & Kiểm tra pháp lý dự án…', 'Ctrl+Shift+L'), ('Quản lý Mẫu in & Bản in…', 'Ctrl+Shift+M'),
                          (LENH_THONG_KE, 'Ctrl+Shift+T')):
            self.lenh[ten].setShortcut(QKeySequence(phim))
        # 1.0.58: lệnh này chỉ gắn nút ở nhóm menu đóng sẵn: nút ẩn thì phím tắt không chạy - gắn vào cửa sổ
        self.addAction(self.lenh['Tiếp nhận & Kiểm tra pháp lý dự án…'])
        self._i_trang = 0                                # trang (chỉ số TRANG) đang chọn - mở lại dự án thì về trang này
        self.khung_du_toan = None                        # trang Dự toán: tạo khi mở lần đầu (không làm chậm lúc khởi động)
        self.dm = None
        self.lb_ket_qua = QLabel('')
        self.lb_ket_qua.setStyleSheet('QLabel { font-weight: bold; padding: 5px 8px; }')
        self.lb_ket_qua.setWordWrap(True)               # chữ đối chiếu dài (~980 điểm) không ép cửa sổ rộng hơn màn hình 1366
        from .giao_dien import OTimKiemThongMinh
        self.o_tim = OTimKiemThongMinh()                 # chờ ngừng gõ 200 ms: bộ gõ tiếng Việt gửi nhiều phím / chữ có dấu
        self.o_tim.setPlaceholderText('Tìm mã hộ, chủ hộ, CCCD, tờ/thửa...')
        self.o_tim.setToolTip('Tìm theo mã hộ, họ tên chủ hộ, CCCD, tờ / thửa, trạng thái, ghi chú - không cần gõ dấu')
        self.o_tim.setClearButtonEnabled(True)
        self.o_tim.setMinimumWidth(220)
        self.o_tim.setObjectName('o_tim_ds')
        self.mo_hinh = BangHo()
        self.loc = LocHo(self)
        self.loc.setSourceModel(self.mo_hinh)
        self.loc.setSortRole(Qt.ItemDataRole.UserRole)
        self.o_tim.chuoi_da_doi.connect(lambda t: self._loc(tu_khoa=t))
        self.cb_dot = QComboBox()
        self.cb_dot.setMinimumWidth(120)
        self.cb_dot.addItem(TAT_CA_DOT, '')
        self.cb_dot.currentIndexChanged.connect(lambda *_: self._loc(dot=self.cb_dot.currentData()))
        self.cb_tt = QComboBox()
        self.cb_tt.addItem(TAT_CA_TRANG_THAI, '')
        from .thong_bao import TRANG_THAI
        for k, t in TRANG_THAI:
            self.cb_tt.addItem(t, k)
        self.cb_tt.currentIndexChanged.connect(lambda *_: self._loc(trang_thai=self.cb_tt.currentData()))
        from .giao_dien import NhanBam
        self.lb_loc = NhanBam('')                        # 21/10/2026: "Lọc: k/N hộ · t thửa ↗" - bấm mở Thống kê Hộ · Thửa · Diện tích
        self.lb_loc.bam = lambda: self.lenh[LENH_THONG_KE].trigger()      # cùng QAction với menu Dữ liệu (tắt khi chưa mở dự án)
        self.lb_loc.setToolTip('Bấm để xem bảng thống kê Hộ · Thửa · Diện tích (Ctrl+Shift+T)')
        self.bang = QTableView()
        self.bang.setModel(self.loc)
        self.bang.setSortingEnabled(True)
        self.bang.setAlternatingRowColors(True)
        # dòng một hàng chữ 30 px (17/10/2026): không xuống dòng - giao_dien._gian_bang (đổi cỡ chữ) giãn dòng bảng có xuống dòng
        # thành ~41 px; chữ dài rút "…", đủ ở chú thích (họ tên, địa chỉ, trạng thái, ghi chú)
        self.bang.setWordWrap(False)
        # 21/10/2026: bôi đen vùng ô kiểu Excel (chọn 1 ô của 3 hộ = 3 hộ cho Xóa hộ / Chọn hộ niêm yết - ho_da_chon); bấm ô STT
        # chọn cả dòng; bộ đếm Trung bình / Tổng số đếm / Tổng ở thanh trạng thái (giao_dien.cho_phep_sao_chep_bang)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.bang.verticalHeader().setVisible(False)
        from .giao_dien import CAO_DONG_BANG
        self.bang.verticalHeader().setMinimumSectionSize(CAO_DONG_BANG - 4)
        self.bang.verticalHeader().setDefaultSectionSize(CAO_DONG_BANG)       # dòng 30 px (Hybrid Enterprise Navy)
        self.bang.horizontalHeader().setResizeContentsPrecision(300)    # tự canh cột: đo 300 dòng mẫu, không đo hết (3.000 hộ)
        self.bang.horizontalHeader().setStretchLastSection(True)
        # 1.0.03: cột Trạng thái vẽ thanh 4 nấc + viên thuốc màu (QPainter - chữ của mô hình giữ nguyên: lọc, tìm, kiểm thử)
        from .giao_dien import gan_vien_thuoc
        gan_vien_thuoc(self.bang, 5)
        self.bang.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.bang.doubleClicked.connect(lambda idx: self._chay_lenh(lambda: self.mo_chi_tiet(idx)))
        self.bang.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bang.customContextMenuRequested.connect(lambda p: self._menu_ho(self.bang, p))
        from PySide6.QtGui import QShortcut
        phim_xoa = QShortcut(QKeySequence(QKeySequence.StandardKey.Delete), self.bang)    # phím Delete trên danh sách hộ
        phim_xoa.setContext(Qt.ShortcutContext.WidgetShortcut)                            # (không áp khi đang sửa ô ghi chú)
        phim_xoa.activated.connect(lambda: self.lenh['Xóa hộ…'].isEnabled() and self._chay_lenh(self.xoa_ho))
        from .giao_dien import cho_phep_sao_chep_bang
        cho_phep_sao_chep_bang(self.bang)                # gắn ngay (không chờ cửa sổ hiện): bộ đếm, viền vùng chọn, Ctrl+C
        self._vua_tieu_de()
        # trang bên phải: danh sách hộ / bảng tổng hợp (3 mục) / theo dõi tiến độ - chọn ở menu trái. Bảng tổng hợp, theo dõi tiến độ,
        # quyết định TẠO KHI MỞ LẦN ĐẦU (máy yếu - 16/10/2026: mở phần mềm không dựng ~200 thành phần và nạp ~10
        # module chưa dùng); chỗ của chúng trong self.trang là khung trống giữ chỉ số (_dam_bao_trang). self.khung_trang chỉ chứa
        # trang đã tạo; self.bang_tong_hop / tien_do / quyet_dinh (property) tạo khi được hỏi tới
        self.khung_trang = {}
        self._cho_trang = {}
        for i in (STACK_TONG_HOP, STACK_THEO_DOI, STACK_QUYET_DINH):
            cho = QWidget()
            lo_cho = QVBoxLayout(cho)
            lo_cho.setContentsMargins(0, 0, 0, 0)
            self._cho_trang[i] = cho
        hang = self._thanh_cong_cu_ds()                  # Thêm hộ, Lập phương án, Xóa hộ (theo ngữ cảnh) | bộ lọc
        nen = QWidget()
        vo = QVBoxLayout(nen)
        vo.setContentsMargins(0, 0, 0, 0)
        vo.setSpacing(0)
        than = QWidget()
        lo = QVBoxLayout(than)
        lo.setContentsMargins(10, 8, 10, 6)
        lo.setSpacing(7)
        from .giao_dien import bang_to_chuc, thanh_lenh
        from .giao_dien import menu_trai as tao_menu_trai
        L = self.lenh
        # 0.9.20 (người dùng yêu cầu "gọn chữ"): chữ trên menu ngắn (NHAN_MENU, tên đầy đủ ở gợi ý); khóa self.lenh giữ tên cũ
        for k, ngan in NHAN_MENU.items():
            L[k].setText(ngan.replace('&', '&&'))      # "&" trên chữ QAction là phím tắt gạch dưới
            L[k].setToolTip(GOI_Y_MENU.get(k, k.rstrip('…')))
        for k in TRANG:                                  # "&" trong chữ QAction = phím tắt gạch dưới: viết "&&" để hiện "&"
            if '&' in k and k not in NHAN_MENU:
                L[k].setText(k.replace('&', '&&'))
        from .giao_dien import chu_hien
        da = set(NHAN_MENU) | {k for k in TRANG if '&' in k}
        for k, a in L.items():
            if k not in da:
                a.setText(chu_hien(a.text()))
        # 0.9.23 (lộ trình người dùng): 5 nhóm theo vòng đời nghiệp vụ - dự án -> bảng giá -> lập phương án -> tổng hợp, trình ->
        # tiến độ. Thao tác file (tạo / mở / lưu / nhập) lên thanh menu Tệp tin / Dữ liệu (trước: nút xổ "DỰ ÁN ▾" đầu menu trái,
        # danh sách xổ đè lên các nút bên dưới); Thêm hộ / Xóa hộ (thao tác theo hộ đang chọn) ở thanh công cụ của danh sách hộ.
        # Mọi nơi dùng chung MỘT QAction mỗi lệnh (cùng trạng thái tắt khi chỉ xem).
        # 0.9.70 (đặc tả ARCH-PABT-2026-V7 - người dùng 12/10/2026): "Màn hình chính" là nút độc lập đầu menu (nhóm không tên),
        # rồi 6 nhóm theo 16 bước của QĐ 18/2026. Cập nhật bảng giá đất -> menu Công cụ, Trạng thái hộ -> menu Dữ liệu (vẫn ở
        # chuột phải danh sách hộ). Khái toán tách nhóm riêng: dữ liệu .pabtdt độc lập với dự án triển khai .pabt
        nhom = [
            (None, [L['Màn hình chính']]),
            ('1. Khái toán & dự toán', [L['Dự toán & khái toán'], L['So sánh với thực tế'],
                                        L['Tiếp nhận & Kiểm tra pháp lý dự án…']]),
            ('2. Dự án triển khai', [L['Thông tin dự án…'], L['Danh sách hộ']]),
            # 18/10/2026 (người dùng): "Bản đồ thửa đất" rời menu trái -> menu Dữ liệu, cạnh Nhập bản vẽ CAD (menu trái gọn)
            ('3. Lập phương án', [L['Lập phương án hộ…'], L['Dự thảo PABT…'], L['Kiểm tra lỗi…'], L['Xuất báo cáo đối chiếu…']]),
            ('4. Tổng hợp & trình duyệt', [L['Tổng hợp tiền theo phương án'], L['Đợt trình…'], L['In / Xuất…']]),
            # mọi việc về quyết định ở MỘT chỗ: trang "Quyết định phê duyệt" (Thêm / Nhập từ file / Sửa / Xóa)
            # 1.0.00: "Báo cáo tiến độ GPMB" gộp vào "Tiến độ chi trả & Bàn giao" (thẻ chỉ số, chế độ Thửa còn vướng, Xuất báo cáo)
            ('5. Phê duyệt & bàn giao', [L['Quyết định phê duyệt'], L['Theo dõi tiến độ']]),
            ('6. Đơn giá & bảng giá', [L['Bộ đơn giá…'], L['Đơn giá riêng dự án…'], L['Bảng giá đất NQ 28…'],
                                         L['Tính đơn giá đất QĐ 03…']]),
        ]
        # hoàn tác / làm lại thao tác đã ghi vào file dự án: menu Chỉnh sửa trên thanh menu (người dùng 11/10/2026 - như các phần
        # mềm khác; trước đây nút trên băng tiêu đề). Chữ "Ctrl+Z" sau "\t" chỉ để hiện: KHÔNG gắn phím tắt cho QAction - phím
        # tắt của QAction được xử lý trước KeyPress, làm hỏng giao_dien.xu_ly_hoan_tac (Ctrl+Z theo khung đang làm việc)
        from .giao_dien import XU_LY_HOAN_TAC, icon_ky_hieu, ky_hieu_nut, mau_icon
        self.nut_ht = {}
        for k, chu, lai in (('lui', 'Hoàn tác', False), ('toi', 'Làm lại', True)):
            a = QAction(chu, self)
            ic = icon_ky_hieu(ky_hieu_nut(chu), mau_icon(chu), 18)
            if ic is not None:
                a.setIcon(ic)
            a.triggered.connect(lambda _=False, x=lai: self.hoan_tac(x))
            self.nut_ht[k] = a
        self._thanh_menu()
        self.bang_tieu_de = bang_to_chuc(f'Phiên bản {__version__}')
        self.bang_tieu_de.setParent(self)                 # giữ cho test / dat_to_chuc; không xếp vào layout (V5: header 38px)
        self.bang_tieu_de.hide()
        vo.addWidget(self.banner_ten)
        vo.addWidget(than, 1)
        if self.menu_trai:
            # 17/10/2026 (Hybrid Enterprise Navy): menu trái sát mép trái / dưới cửa sổ (thanh bên, viền phải 1 px); lề chỉ ở phần nội dung
            lo.setContentsMargins(0, 0, 0, 0)
            ngang = QHBoxLayout()
            ngang.setSpacing(0)
            # bấm tiêu đề nhóm để đóng / mở - menu không tràn màn hình 1366x768
            self.khung_menu = tao_menu_trai(nhom, dong_mac_dinh=NHOM_DONG_MAC_DINH)
            self.khung_menu.nut_thu_gon.clicked.connect(lambda: setattr(self, '_menu_tu_thu_gon', False))   # người dùng tự chọn: không tự mở lại
            ngang.addWidget(self.khung_menu)
            phai = QVBoxLayout()
            phai.setContentsMargins(10, 8, 10, 6)
            phai.setSpacing(7)
            ngang.addLayout(phai, 1)
            lo.addLayout(ngang, 1)
        else:                                           # kiểu cũ (--menu-tren): thanh nút, kèm nhóm Dự án như trước
            lo.addWidget(thanh_lenh([('Dự án', [L['Dự án mới…'], L['Mở dự án…'], L['Lưu dự án thành…'],
                                                L['Nhập file Excel…'], L['Nhập phương án chi tiết…']]), *nhom]))
            phai = lo
        self.hang_the = QWidget()                        # thẻ số liệu (ẩn ở màn hình chào)
        self.hang_the.setLayout(self._hang_the_so())
        self.hang_the.layout().setContentsMargins(0, 0, 0, 0)
        phai.addWidget(self.hang_the)
        trang_ds = QWidget()
        lo_ds = QVBoxLayout(trang_ds)
        lo_ds.setContentsMargins(0, 0, 0, 0)
        lo_ds.setSpacing(7)
        # băng kết quả đối chiếu; Lập phương án / Thêm hộ chỉ ở menu trái (+ bấm đúp, chuột phải) - không lặp nút ở đây
        hang_kq = QHBoxLayout()                         # kết quả đối chiếu (số hộ đang lọc: huy hiệu cuối hàng công cụ)
        hang_kq.addWidget(self.lb_ket_qua, 1)
        lo_ds.addLayout(hang_kq)
        lo_ds.addLayout(hang)
        # bảng + dải cộng cố định ngay dưới (không cách): cộng các hộ ĐANG HIỆN theo bộ lọc
        khoi_bang = QVBoxLayout()
        khoi_bang.setSpacing(0)
        khoi_bang.setProperty('giu_khoang_cach', True)
        khoi_bang.addWidget(self.bang, 1)
        khoi_bang.addWidget(self._dai_cong())
        lo_ds.addLayout(khoi_bang, 1)
        # tiêu đề trang: luôn ẩn (16/10/2026), chỉ giữ chữ tên trang hiện tại - con của cửa sổ, KHÔNG xếp vào bố cục (1.0.32)
        self.lb_trang = QLabel('', self)
        self.lb_trang.setProperty('vai', 'tieu_de')
        self.lb_trang.setVisible(False)
        from .giao_dien import KhungLamViecDaTab
        self.khung_tab = KhungLamViecDaTab(self)         # V5: tab trang chính + hộ / bộ đơn giá (giữ RAM)
        self.thanh_tab = self.khung_tab.bar
        self._tab_khoa = self.khung_tab.khoa
        self.khung_tab.da_doi.connect(self._tab_doi_khoa)
        self.khung_tab.yeu_cau_dong.connect(self._tab_dong)
        from PySide6.QtGui import QShortcut
        for chu, buoc in (('Ctrl+Tab', 1), ('Ctrl+Shift+Tab', -1)):
            phim = QShortcut(QKeySequence(chu), self)
            phim.activated.connect(lambda b=buoc: self._tab_ke(b))
        # thanh tab KHÔNG xếp vào bố cục (15/10/2026, người dùng: thu hồi ~40 px chiều cao) - chuyển trang bằng menu trái /
        # thanh menu (Ctrl+1..5 = các trang); khung_tab chỉ giữ danh sách trang / tab hộ đang mở trong RAM
        self.trang = QStackedWidget()
        self.trang_dt = QWidget()                        # trang Dự toán & khái toán (KhungDuToan tạo khi mở lần đầu)
        lo_dt = QVBoxLayout(self.trang_dt)
        lo_dt.setContentsMargins(0, 0, 0, 0)
        for w in (trang_ds, self._cho_trang[STACK_TONG_HOP], self._cho_trang[STACK_THEO_DOI], self.trang_dt, self._trang_chao(),
                  self._cho_trang[STACK_QUYET_DINH]):
            self.trang.addWidget(w)
        self.ngan_lv = QStackedWidget()
        self.trang.currentChanged.connect(lambda *_: self._cap_nhat_hien_hang_the())
        self.ngan_lv.currentChanged.connect(lambda *_: self._cap_nhat_hien_hang_the())
        self.ngan_lv.addWidget(self.trang)
        self.ngan_lv.addWidget(self.khung_tab.stack_phu)
        phai.addWidget(self.ngan_lv, 1)
        self.bang.selectionModel().selectionChanged.connect(lambda *_: self._cap_nhat_chon())
        self.setCentralWidget(nen)
        self.lb_tom_tat = QLabel('Sẵn sàng')             # thanh trạng thái: Sẵn sàng · tổng số hộ | đã chọn
        self.lb_tom_tat.setToolTip('Nhấp đúp một hộ để lập / sửa phương án.')
        self.statusBar().addWidget(self.lb_tom_tat, 1)
        # cỡ giao diện: nút − / + , bấm vào % để về 100%; phím Ctrl + con lăn chuột, Ctrl + "+" / "-" / "0"
        from .giao_dien import KHI_DOI_TY_LE, TY_LE, phong_to
        goi_y = 'Cỡ giao diện: Ctrl + con lăn chuột, hoặc Ctrl + "+" / Ctrl + "-"; Ctrl + 0 về 100%'
        # 21/10/2026: bộ đếm kiểu Excel (Trung bình / Tổng số đếm / Tổng) của vùng đang chọn ở MỌI bảng trong cửa sổ chính - ngay trái
        # cụm A− / A+; bấm = chép Tổng. Bảng gọi cap_nhat_bo_dem qua giao_dien._BoChonVung
        from .giao_dien import NhanBoDem
        self.lb_bo_dem_excel = NhanBoDem()
        self._bang_bo_dem = None
        self.statusBar().addPermanentWidget(self.lb_bo_dem_excel)
        self.nut_ty_le = {}
        for k, chu, buoc in (('nho', 'A−', -1), ('ty_le', '', 0), ('to', 'A+', 1)):
            b = QToolButton()
            b.setText(chu)
            b.setToolTip(goi_y)
            b.setAutoRaise(True)
            if k != 'ty_le':                            # 0.9.80: A− / A+ có khung nút (viền nhẹ, bo 4px); "110%" là chữ bấm về 100%
                b.setObjectName('nut_zoom')
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                dat_kieu_theo_tong(b, QSS_NUT_ZOOM)
            b.clicked.connect(lambda _=False, x=buoc: phong_to(x))
            self.statusBar().addPermanentWidget(b)
            self.nut_ty_le[k] = b
        self._hien_ty_le(TY_LE[0])
        KHI_DOI_TY_LE.append(self._hien_ty_le)
        XU_LY_HOAN_TAC.append(self.hoan_tac_phim)
        self.setAcceptDrops(True)                        # 1.0.08: kéo thả .larc / .pabt / .larcud / .pabtcfg / .xlsx từ Explorer
        from .giao_dien import TRUOC_DOI_TY_LE
        TRUOC_DOI_TY_LE.append(self._bo_trang_an)        # 1.0.08: đổi cỡ chữ nhanh hơn - trang ẩn tạo lại khi mở tới
        self._cap_nhat_nut_ht()
        self.nut_tk = QToolButton()                            # tài khoản / máy chủ LAN
        self.nut_tk.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.nut_tk.setMenu(QMenu(self.nut_tk))
        self.nut_tk.menu().aboutToShow.connect(self._menu_tai_khoan)
        self.statusBar().addPermanentWidget(self.nut_tk)
        self.cap_nhat_tai_khoan()
        # Cập nhật phần mềm / Giới thiệu: menu Trợ giúp (trước 0.9.23 thêm hai nút ở góc dưới - mỗi lệnh một chỗ)
        self._cap_nhat_lenh_theo_du_an()                # chưa mở dự án: làm mờ nhóm 3, 4, 5 + Đơn giá đặc biệt
        self._hien_trang_chao()

    # ------------------------------------------------ lệnh
    def nhap_excel(self, xl=None, dich=None):
        """Nhập file PABT Excel (mẫu .xlsm) hoặc file Excel bất kỳ có họ tên, địa chỉ, tờ, thửa, DT thu hồi, loại đất."""
        if xl is None:
            xl, _ = QFileDialog.getOpenFileName(self, 'Chọn file Excel (file PABT hoặc danh sách hộ, thửa)', '',
                                                'File Excel (*.xlsm *.xlsx)')
            if not xl:
                return
        from . import nhap_excel, nhap_tho
        try:
            tho = not nhap_tho.la_file_pabt(xl)
        except Exception as e:
            QMessageBox.critical(self, TEN_UD, chu_loi('Không đọc được file', e))
            return
        from . import nhap_chi_tiet
        if tho and dich is None and nhap_chi_tiet.la_file_chi_tiet(xl):    # mỗi sheet một phương án chi tiết
            return self.nhap_chi_tiet(xl)
        if dich is None:
            mac_dinh = str(self.file if tho and self.file else Path(xl).with_suffix(csdl.DUOI_DU_AN))
            hoi = {'options': QFileDialog.Option.DontConfirmOverwrite} if tho else {}   # tự hỏi "xóa trắng" bên dưới
            dich, _ = QFileDialog.getSaveFileName(self, 'Lưu vào file dự án', mac_dinh, csdl.LOC_LUU, **hoi)
            if not dich:
                return
            if tho and Path(dich).exists() and QMessageBox.question(
                    self, TEN_UD, f'XÓA TRẮNG toàn bộ hồ sơ hộ, thửa, phương án trong\n{dich}\nrồi nhập danh sách mới?\n\n'
                                  'Danh mục đơn giá, tham số của file được giữ nguyên.') != QMessageBox.StandardButton.Yes:
                return
        k = khoa.KhoaFile(dich).nguoi_khac()
        if k:
            QMessageBox.warning(self, TEN_UD, f'File dự án đang được sửa trên {khoa.mo_ta(k)}.\nKhông ghi đè được.')
            return
        danh_muc = self.file if tho and self.file and not Path(dich).exists() else None
        try:
            with con_tro_cho():
                self.dong_du_an()
                from .giao_dien import chay_nen                 # luồng nền (tự mở kết nối file đích): file lớn không làm treo cửa sổ
                bc = chay_nen(self, lambda: nhap_tho.nhap(xl, dich, danh_muc=danh_muc) if tho else nhap_excel.nhap(xl, dich),
                              f'Đang nhập {Path(xl).name}…')
        except Exception as e:                       # file hỏng, đang mở khóa...
            QMessageBox.critical(self, TEN_UD, chu_loi('Không nhập được file', e))
            return
        if bc.loi:
            from .giao_dien import hop_ket_qua
            hop_ket_qua(self, 'Không nhập được file.', bc.loi, 'Lý do', canh_bao=True, tieu_de=TEN_UD)
            return
        tb = f'Đã nhập {bc.so_ho} hộ, {bc.so_thua} thửa, {sum(bc.so_dong.values())} dòng phương án.'
        if tho:
            tb += '\n\nNhận cột: ' + bc.nhan_cot
        from .giao_dien import hop_ket_qua                  # ô cuộn: đủ mọi lưu ý, nút Đóng luôn trong màn hình
        hop_ket_qua(self, tb, bc.canh_bao, 'Lưu ý', tieu_de=TEN_UD)
        self.mo(dich)

    def _ghi_chi_tiet_co_tien_do(self, nhap_chi_tiet, kq, cach: str, nguon: str, hien: bool = True):
        """nhap_chi_tiet.ghi vào dự án đang mở với QProgressDialog (hiện sau 0,5 s, nút Dừng)."""
        hop = None
        if hien and len(kq.ho) > nhap_chi_tiet.BAO_MOI:
            from PySide6.QtWidgets import QApplication, QProgressDialog
            hop = QProgressDialog('Đang ghi phương án chi tiết vào dự án…', 'Dừng', 0, len(kq.ho), self)
            hop.setWindowTitle(TEN_UD)
            hop.setWindowModality(Qt.WindowModality.WindowModal)
            hop.setMinimumDuration(500)

        def bao(i, n):
            if hop is None:
                return False
            hop.setValue(i)
            hop.setLabelText(f'Đang ghi phương án chi tiết: hộ {i + 1} / {n}…')
            QApplication.processEvents()
            return hop.wasCanceled()
        try:
            return nhap_chi_tiet.ghi(self.con, kq.ho, cach, nguon, kq.du_an, bao_tien_do=bao)
        finally:
            if hop is not None:
                hop.close()
                hop.deleteLater()

    def nhap_chi_tiet(self, xl=None, dich=None, sheet: list | None = None, trung: str | None = None, cho: bool = True):
        """Nhập file Excel phương án chi tiết (mỗi sheet một hộ) vào dự án đang mở, hoặc dự án mới khi chưa mở dự án.
        Kiểm thử: dich (file dự án mới), sheet (tên sheet), trung, cho=False (không hiện hộp thoại)."""
        from . import nhap_chi_tiet
        if xl is None:
            xl, _ = QFileDialog.getOpenFileName(self, 'Chọn file Excel phương án chi tiết (mỗi sheet một hộ)', '',
                                                'File Excel (*.xlsm *.xlsx)')
            if not xl:
                return None
        try:
            with con_tro_cho():
                from .giao_dien import chay_nen                 # chỉ đọc file Excel: chạy nền, cửa sổ không treo khi file nhiều sheet
                kq = chay_nen(self, lambda: nhap_chi_tiet.doc(xl), f'Đang đọc {Path(xl).name}…')
        except Exception as e:
            QMessageBox.critical(self, TEN_UD, chu_loi('Không đọc được file', e))
            return None
        if not kq.ho:
            QMessageBox.warning(self, TEN_UD, 'File không có sheet phương án chi tiết nào (bảng STT / Tên tài sản / Số lượng / '
                                              'Thành tiền và dòng "Họ và tên").')
            return None
        vao_mo = self.con is not None and not self.chi_doc and dich is None
        if not vao_mo and dich is None:
            dich, _ = QFileDialog.getSaveFileName(self, 'Lưu vào file dự án', str(Path(xl).with_suffix(csdl.DUOI_DU_AN)),
                                                  csdl.LOC_LUU)
            if not dich:
                return None
        con_xem = self.con if vao_mo else (csdl.mo(dich, chi_doc=True) if dich and Path(dich).exists() else None)
        try:
            ten = con_xem.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()[0] if con_xem is not None else ''
            from .man_hinh_nhap_chi_tiet import HopNhapChiTiet
            hop = HopNhapChiTiet(kq, con_xem, self, ten)
            if cho and hop.exec() != QDialog.DialogCode.Accepted:
                return None
            if sheet is not None:
                for h in kq.ho:
                    h.chon = h.sheet in sheet and not h.loi
                cach = trung or 'bo_qua'
            else:
                cach = trung or hop.ap_dung()
        finally:
            if con_xem is not None and con_xem is not self.con:
                con_xem.close()
        if not vao_mo:
            k = khoa.KhoaFile(dich).nguoi_khac()
            if k:
                QMessageBox.warning(self, TEN_UD, f'File dự án đang được sửa trên {khoa.mo_ta(k)}.\nKhông ghi được.')
                return None
        elif cho:                                       # phương án đột phá 8: thử trên bản sao, xem hộ nào đổi rồi mới ghi thật
            from copy import deepcopy
            if not self.xem_truoc_thao_tac(f'Nhập phương án chi tiết từ {Path(xl).name}',
                                           lambda c: nhap_chi_tiet.ghi(c, deepcopy(kq.ho), cach, Path(xl).name, kq.du_an)):
                return None
        try:
            with con_tro_cho():
                if vao_mo:
                    # dự án đang mở: ghi ở luồng giao diện (giữ Hoàn tác) + hộp tiến trình mỗi 10 hộ, Dừng = hoàn tác cả lô
                    bc = self._ghi_chi_tiet_co_tien_do(nhap_chi_tiet, kq, cach, Path(xl).name, cho)
                else:
                    if self.file is not None and Path(dich).resolve() == self.file.resolve():
                        self.dong_du_an()
                    from .giao_dien import chay_nen         # file khác (kết nối riêng): ghi ở luồng nền, cửa sổ không treo
                    bc = chay_nen(self, lambda: nhap_chi_tiet.ghi_file(kq, dich, cach), f'Đang ghi vào {Path(dich).name}…')
        except nhap_chi_tiet.DaDung as e:
            QMessageBox.information(self, TEN_UD, str(e))
            return None
        except Exception as e:
            QMessageBox.critical(self, TEN_UD, chu_loi('Không nhập được', e))
            return None
        if vao_mo:
            self.tai_lai()
        else:
            self.mo(dich)
        if cho:                                         # hộp có ô cuộn: danh sách dài không đẩy nút Đóng ra ngoài màn hình
            from .giao_dien import hop_ket_qua
            ngan, ds = nhap_chi_tiet.ket_qua(bc)
            hop_ket_qua(self, ngan, ds, tieu_de=TEN_UD)
        return bc

    def mo_du_an(self):
        tm = self.file.parent if self.file else may_chu.thu_muc_mac_dinh()
        p, _ = QFileDialog.getOpenFileName(self, 'Mở dự án', str(tm), csdl.LOC_MO)
        if p:
            self.mo(p)

    def mo(self, p, chi_doc: bool | None = None):
        """Mở dự án. File đang được máy khác sửa thì hỏi: mở chỉ xem / vẫn mở để sửa (chi_doc: bỏ qua câu hỏi)."""
        try:
            if self.dong_du_an() is False:
                return
            kf = khoa.KhoaFile(p)
            k = kf.nguoi_khac()
            if k and chi_doc is None:
                hop = QMessageBox(QMessageBox.Icon.Warning, TEN_UD, f'File dự án đang được sửa trên {khoa.mo_ta(k)}.\n\n'
                                  'Mở chỉ xem để tránh hai người cùng sửa ghi đè lên nhau.', parent=self)
                nut_xem = hop.addButton('Mở chỉ xem', QMessageBox.ButtonRole.AcceptRole)
                nut_sua = hop.addButton('Vẫn mở để sửa', QMessageBox.ButtonRole.DestructiveRole)
                hop.addButton('Hủy', QMessageBox.ButtonRole.RejectRole)
                hop.exec()
                if hop.clickedButton() not in (nut_xem, nut_sua):
                    return
                chi_doc = hop.clickedButton() is nut_xem
            chi_doc = bool(chi_doc)
            # 1.0.57: vai trò tài khoản máy chủ LAN (phan_quyen) - Thanh tra / vai trò không ghi gì: mở CHỈ XEM
            from . import phan_quyen
            vai_tro = phan_quyen.vai_tro_cho_file(p)
            if phan_quyen.chi_xem(vai_tro):
                chi_doc = True
            from .an_toan import la_goi_sao_luu
            if not chi_doc and la_goi_sao_luu(p):        # 1.0.55: bản sao lưu / mốc nén luôn mở chỉ xem (Lưu dự án thành… để dùng tiếp)
                chi_doc = True
            if not chi_doc:
                # 1.0.58: chỉ ép khi người dùng đã chọn "Vẫn mở để sửa"; máy khác vừa lấy trước: mở chỉ xem (trước đây luôn ép, hai máy cùng sửa)
                duoc, k2 = kf.lay(ep=bool(k))
                if duoc:
                    self.khoa = kf
                    self.dong_ho.start()
                else:
                    chi_doc = True
                    QTimer.singleShot(0, lambda: self.statusBar().showMessage(f'Mở chỉ xem: dự án vừa được mở để sửa trên {khoa.mo_ta(k2)}.', 10000))
            self.chi_doc = chi_doc
            tinh_lai = None
            self.con = csdl.mo(p, chi_doc=chi_doc)
            yc = '' if chi_doc else csdl.qua_cu_de_ghi(self.con, __version__)
            if yc:                                      # 01/11/2026: file đã được phần mềm mới hơn ghi - bản này chỉ được xem
                self.con.close()
                if self.khoa is not None:
                    self.khoa.nha()
                    self.khoa = None
                self.dong_ho.stop()
                chi_doc = self.chi_doc = True
                self.con = csdl.mo(p, chi_doc=True)
                from .giao_dien import thong_bao_noi as tb_noi
                QTimer.singleShot(0, lambda yc=yc: tb_noi(
                    self, f'File dự án đã được cập nhật bằng LARC {yc} trở lên: phiên bản {__version__} chỉ MỞ XEM để không ghi sai dữ '
                          f'liệu. Cập nhật phần mềm để sửa.', 'canh_bao', 9000))
            elif not chi_doc:
                csdl.dat_ghi_toi_thieu(self.con)        # trước khi gắn Hoàn tác: không thành một bước hoàn tác
            # 1.0.29: bản offline THEO HỘ (máy chủ LAN): chỉ các hộ đã nhận được lưu (lap_pa.kiem_ho_nhan_viec đọc thuộc tính này)
            self.nhan_viec = may_chu.ho_nhan_viec(p)
            self.con._ho_nhan_viec = self.nhan_viec
            if not chi_doc:
                from .hoan_tac import HoanTac
                self.ht = HoanTac(self.con, hen=lambda ham: QTimer.singleShot(0, ham))
                self.ht.khi_doi.append(self._cap_nhat_nut_ht)
                try:
                    self.dv = csdl.DauVetHo(self.con)
                except Exception:                      # không tạo được: vẫn mở dự án, tai_lai nạp toàn bộ như trước
                    self.dv = None
                try:                                   # nhật ký kiểm toán (0.9.86): ai sửa, cũ -> mới
                    from . import kiem_toan
                    csdl.go_trigger_la(self.con)
                    kiem_toan.gan(self.con)
                except sqlite3.Error:                  # file đang khóa / lỗi: vẫn mở dự án (nhat_ky vẫn ghi thao tác)
                    pass
                try:                                   # 16/10/2026: quy ước tương đương mẫu (bộ đơn giá / Excel cũ) -> bỏ
                    from .don_gia_rieng import bo_quy_uoc_cu
                    bo_quy_uoc_cu(self.con)
                except sqlite3.Error:
                    pass
                try:                                   # 26/10/2026: tên khác cây lâm nghiệp (Phụ lục VI QĐ 48/2025) cho danh mục dự án
                    from .ten_cay_lam_nghiep import ap_ten_khac_khi_can
                    ap_ten_khac_khi_can(self.con, p)
                except sqlite3.Error:
                    pass
                try:                                   # 29/10/2026: số lượng / diện tích nhập bằng công thức tính lại (2 chữ số lẻ)
                    tinh_lai = lap_pa.tinh_lai_cong_thuc(self.con)
                except sqlite3.Error:
                    pass
                if self.nhan_viec is not None:         # 01/11/2026: bản offline theo hộ - CSDL tự chặn ghi hộ không nhận (lớp cuối)
                    try:
                        lap_pa.gan_chan_ho_nhan_viec(self.con, self.nhan_viec)
                    except sqlite3.Error:
                        pass
                try:                                   # 1.0.57: vai trò máy chủ - hàm ghi kiểm (lap_pa.kiem_quyen) + trigger tạm (lớp cuối)
                    phan_quyen.gan(self.con, vai_tro)
                except sqlite3.Error:
                    pass
            else:
                self.con._vai_tro = vai_tro
            self.vai_tro = vai_tro
            self._cap_nhat_nut_ht()
            self.file = Path(p)
            self.dm = lap_pa.DanhMuc(self.con)
            # chỉ xem: tắt mọi lệnh ghi. Mỗi lệnh một QAction dùng chung cho menu trái / chuột phải - không còn nút gọi thẳng
            # hàm (trước 0.9.18 hai nút nhanh "Thêm hộ…", "Lập phương án hộ đang chọn" vẫn bật khi chỉ xem -> lỗi ghi CSDL)
            for ten in ('Thêm hộ…', 'Xóa hộ…', 'Lập phương án hộ…', 'Thông tin dự án…', 'Trạng thái hộ…'):
                self.lenh[ten].setEnabled(not chi_doc)
            self.lenh['Đóng dự án'].setEnabled(True)
            self.lenh['Xóa dự án…'].setEnabled(True)
            self._ap_vai_tro_lenh()
            self._cap_nhat_lenh_theo_du_an()            # mở dự án: bật sáng toàn bộ menu (Lập phương án vẫn tắt khi chỉ xem)
            for k in self.khung_trang.values():
                k.dat_du_an(self.con, chi_doc)
            if self.khung_du_toan is not None:
                self.khung_du_toan.dat_du_an(self.con, self.file)
            self._cap_nhat_nhan_viec()
            self.tai_lai()
            # mở / nhập dự án: luôn vào Màn hình chính = tổng quan + phễu tiến độ (người dùng 31/10/2026; 12/10/2026 - 30/10/2026:
            # Danh sách hộ; trước nữa: trang chọn lần trước, ví dụ Dự toán)
            self.mo_trang(0)                            # đặt trang Danh sách hộ làm trang đang chọn (bấm menu trái quay lại)
            self.ve_trang_chu()
            ghi_gan_day(self.file)
            if tinh_lai and (tinh_lai['so_dong'] or tinh_lai['bo_qua_khoa']):
                from .giao_dien import thong_bao_noi
                thong_bao_noi(self, chu_tinh_lai_cong_thuc(tinh_lai), 'canh_bao' if tinh_lai['bo_qua_khoa'] else 'tin', 12000)
            if not chi_doc:                                 # 1.0.08: bản sao lưu tự động (máy HDD cũ, mất điện) - sau khi cửa sổ đã vẽ
                c, f = self.con, self.file
                QTimer.singleShot(SAO_LUU_SAU_MS, lambda: c is self.con and (self._sao_luu_tu_dong(c, f), self.chup_moc('mo')))
                self.dong_ho_moc.start()
            from .hang_nhap_nhanh import lam_san_nen      # lúc rảnh, luồng nền: dựng sẵn danh sách chọn của cửa sổ lập phương án
            dm = self.dm
            QTimer.singleShot(400, lambda: dm is self.dm and lam_san_nen(dm))
            if may_chu.PHIEN is not None:                   # đăng nhập máy chủ: máy khác đăng nhập cùng tài khoản sẽ mở tiếp dự án
                import threading                            # luồng riêng: máy chủ chậm / mất mạng không làm chậm việc mở dự án
                threading.Thread(target=may_chu.ghi_mo_du_an, args=(self.file,), daemon=True).start()
        except Exception as e:
            self.dong_du_an()
            QMessageBox.critical(self, TEN_UD, chu_loi('Không mở được dự án', e))

    def chup_moc(self, ly_do: str = 'tu_dong', ghi_chu: str = '', bat_buoc: bool = False):
        """Chụp mốc cỗ máy thời gian cho dự án đang mở để sửa (co_may_thoi_gian.chup_moc). Không đổi từ mốc trước / chỉ xem: không
        chụp. Lỗi ghi đĩa: chỉ báo ở thanh trạng thái. Trả Moc hoặc None."""
        if self.con is None or self.file is None or self.chi_doc:
            return None
        from . import co_may_thoi_gian
        try:
            return co_may_thoi_gian.chup_moc(self.con, self.file, ly_do, ghi_chu, bat_buoc)
        except (OSError, sqlite3.Error) as e:
            self.statusBar().showMessage(chu_loi('Không lưu được mốc khôi phục', e), 8000)
            return None

    def xem_truoc_thao_tac(self, viec: str, ham, hoi: bool = True) -> bool:
        """Thử trước thao tác hàng loạt (phương án đột phá 8): chạy ham(kết nối) trên BẢN SAO dự án, hiện các hộ thêm / bỏ / đổi tiền;
        người dùng đồng ý thì lưu mốc "trước thao tác" rồi trả True để nơi gọi làm thật trên dự án. Chạy thử lỗi: báo, trả False.
        hoi=False (kiểm thử): không hiện hộp, coi như đồng ý."""
        from . import co_may_thoi_gian
        with con_tro_cho():
            thu = co_may_thoi_gian.thu_truoc(self.con, ham)
        if thu.loi is not None:
            if hoi:
                QMessageBox.warning(self, TEN_UD, chu_loi(f'{viec}: chạy thử không được', thu.loi))
            return False
        if hoi:
            from .man_hinh_co_may_thoi_gian import HopXemTruocThayDoi
            if HopXemTruocThayDoi(self, viec, thu.khac).exec() != QDialog.DialogCode.Accepted:
                return False
        self.chup_moc('truoc_thao_tac', viec, bat_buoc=True)
        return True

    def tro_ly(self, ma_ho=None, cho: bool = True):
        """Công cụ → Trợ lý: giải thích số tiền hộ (mặc định hộ đang chọn), nháp tờ trình, đọc văn bản (phương án đột phá 9)."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Mở dự án trước.')
            return None
        from .man_hinh_tro_ly import HopTroLy
        if ma_ho is None:
            ds = self.ho_da_chon()
            ma_ho = ds[0] if ds else None
        h = HopTroLy(self.con, self, ma_ho)
        if ma_ho is not None:
            h.giai_thich()
        if cho:
            h.exec()
        return h

    def co_may_thoi_gian(self, cho: bool = True):
        """Tệp tin → Cỗ máy thời gian: danh sách mốc, xem khác biệt tới hiện tại, khôi phục (phương án đột phá 8)."""
        if self.con is None or self.file is None:
            QMessageBox.information(self, TEN_UD, 'Mở dự án trước.')
            return None
        from .man_hinh_co_may_thoi_gian import HopCoMayThoiGian
        h = HopCoMayThoiGian(self)
        if cho:
            h.exec()
        return h

    def khoi_phuc_moc(self, moc, xac_nhan: bool = True) -> bool:
        """Đóng dự án, thay file bằng bản của mốc (chụp mốc "trước khi khôi phục" để quay lại được), mở lại."""
        if self.file is None:
            return False
        if self.chi_doc:
            QMessageBox.information(self, TEN_UD, 'Dự án đang mở chỉ xem: không khôi phục được.')
            return False
        if xac_nhan and QMessageBox.question(
                self, TEN_UD, f'Khôi phục dự án về mốc {moc.luc:%d/%m/%Y %H:%M:%S} ({moc.ten_ly_do})?\n\nTrạng thái hiện tại được lưu '
                'thành mốc "Trước khi khôi phục" - quay lại được bằng chính cửa sổ này.') != QMessageBox.StandardButton.Yes:
            return False
        from . import co_may_thoi_gian
        f = self.file
        self.chup_moc('tu_dong')
        if self.dong_du_an() is False:
            return False
        try:
            co_may_thoi_gian.khoi_phuc(f, moc)
        except (OSError, sqlite3.Error) as e:
            QMessageBox.critical(self, TEN_UD, chu_loi('Không khôi phục được', e))
            self.mo(f)
            return False
        self.mo(f, chi_doc=False)
        from .giao_dien import thong_bao_noi
        thong_bao_noi(self, f'Đã khôi phục dự án về {moc.luc:%d/%m/%Y %H:%M}', 'dat')
        return True

    def _sao_luu_tu_dong(self, con=None, file=None):
        """Sao lưu tự động dự án vừa mở để sửa (csdl.sao_luu_tu_dong). Lỗi (đầy đĩa, thư mục máy không ghi được): chỉ báo ở thanh
        trạng thái - không chặn làm việc."""
        con, file = con or self.con, file or self.file
        if con is None or file is None:
            return None
        try:
            return csdl.sao_luu_tu_dong(con, file)
        except (OSError, sqlite3.Error) as e:
            self.statusBar().showMessage(chu_loi('Không tạo được bản sao lưu tự động', e), 8000)
            return None

    # ---- kéo - thả file từ Windows Explorer (1.0.08)
    def _file_keo(self, ev) -> list:
        md = ev.mimeData()
        if md is None or not md.hasUrls():
            return []
        return [u.toLocalFile() for u in md.urls() if u.isLocalFile() and u.toLocalFile().lower().endswith(DUOI_KEO_THA)]

    def dragEnterEvent(self, e):
        if self._file_keo(e):
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if self._file_keo(e):
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        ds = self._file_keo(e)
        if not ds:
            return super().dropEvent(e)
        e.acceptProposedAction()
        QTimer.singleShot(0, lambda p=ds[0]: self.mo_file_keo(p))      # chạy sau khi Explorer đã nhả chuột

    def mo_file_keo(self, p: str):
        """File kéo thả vào cửa sổ: dự án (.larc / .pabt) -> mở; gói cập nhật (.larcud / .pabtcn) -> cài; gói mẫu in & cấu hình
        (.pabtcfg) -> cài; Excel (.xlsx / .xlsm) -> nhập (file phương án chi tiết tự nhận ra). Trả loại đã xử lý ('' nếu không nhận)."""
        d = p.lower()
        if d.endswith(csdl.DUOI_MO):
            self._chay_lenh(lambda: self.mo(p))
            return 'du_an'
        if d.endswith(('.larcud', '.pabtcn')):
            self._chay_lenh(lambda: self.cap_nhat_phan_mem(p))
            return 'cap_nhat'
        if d.endswith('.pabtcfg'):
            self._chay_lenh(lambda: self.nhap_goi_mau(p))
            return 'goi_mau'
        if d.endswith(('.xlsx', '.xlsm')):
            self._chay_lenh(lambda: self.nhap_excel(p))
            return 'excel'
        return ''

    def _ap_vai_tro_lenh(self):
        """1.0.57: tắt lệnh vai trò tài khoản máy chủ không có quyền (phan_quyen.LENH_QUYEN); chú thích lý do."""
        vt = getattr(self, 'vai_tro', None)
        if vt is None or self.con is None:
            return
        from . import phan_quyen
        for ten in phan_quyen.lenh_bi_tat(vt, self.lenh):
            self.lenh[ten].setEnabled(False)
            self.lenh[ten].setStatusTip(f'Vai trò "{phan_quyen.ten_vai_tro(vt)}" không dùng lệnh này')

    def _cap_nhat_lenh_theo_du_an(self):
        """Chưa mở dự án: tắt các lệnh của nhóm 3, 4, 5 + Đơn giá đặc biệt (LENH_CAN_DU_AN); có dự án: bật (riêng Lập phương án hộ vẫn tắt khi chỉ xem)."""
        co = self.con is not None
        for ten in LENH_CAN_DU_AN:
            a = self.lenh.get(ten)
            if a is not None:
                a.setEnabled(co and not (self.chi_doc and ten == 'Lập phương án hộ…'))
                # có dự án thì xóa nhắc (trước đây giữ mãi: thanh trạng thái vẫn báo "Mở hoặc tạo dự án…" khi đã mở)
                a.setStatusTip('' if co else 'Mở hoặc tạo dự án để dùng chức năng này')
        self._ap_vai_tro_lenh()

    def lam_moi_khoa(self, hoi: bool = True):
        """Làm mới khóa mỗi phút. Máy khác đã lấy khóa (chọn "Vẫn mở để sửa"): rà soát kiến trúc 31/10/2026 - chuyển dự án sang CHỈ XEM
        (trước đây chỉ cảnh báo rồi vẫn cho sửa: hai máy ghi đè số liệu của nhau). Số liệu đã ghi ngay khi thao tác, không mất."""
        if self.khoa is not None and not self.khoa.lam_moi():
            self.dong_ho.stop()
            k = self.khoa.doc() or {}
            p = self.file
            self.khoa = None                            # khóa đã thuộc máy kia: không nhả (xóa) khóa của họ khi đóng
            if hoi:
                QMessageBox.warning(self, TEN_UD, f'Một máy khác ({khoa.mo_ta(k)}) đã mở file dự án để sửa.\n\n'
                                                  'Để hai máy không ghi đè số liệu của nhau, phần mềm chuyển dự án sang CHẾ ĐỘ CHỈ XEM '
                                                  '(số liệu bạn đã thao tác đều đã được lưu). Mở lại dự án khi máy kia sửa xong.')
            if p is not None:
                self.mo(p, chi_doc=True)

    def dong_du_an(self):
        if hasattr(self, 'khung_tab') and not self._dong_tab_phu(hoi=True):
            return False
        if self.con is not None and self.file is not None and self.kq is not None:
            try:                                        # nhớ tổng chuẩn cho bảng dự án gần đây (màn hình chào)
                self.con.commit()
            except sqlite3.Error:
                pass
            ghi_tong_nho(self.file, len(self.kq.ho), sum((h['tong'] for h in self.kq.ho), D('0')))
            if not self.chi_doc:                        # mốc cuối phiên (chỉ khi có thay đổi từ mốc trước)
                self.chup_moc('tu_dong')
        self.dong_ho.stop()
        self.dong_ho_moc.stop()
        if self.khoa is not None:
            self.khoa.nha()
            self.khoa = None
        self.chi_doc = False
        for a in self.lenh.values():
            a.setEnabled(True)
        if self.ht is not None:
            self.ht.dong()
            self.ht = None
        self.dv = None
        if self.con is not None:
            self.con.close()
            self.con = None
        self.nhan_viec = None
        self.vai_tro = None
        self._cap_nhat_nhan_viec()
        self._cap_nhat_lenh_theo_du_an()                # đóng dự án: làm mờ lại nhóm 3, 4, 5 (+ Đơn giá đặc biệt) của menu trái
        if hasattr(self, 'nut_ht'):
            self._cap_nhat_nut_ht()
        self.kq = None
        self.dm = None
        self.mo_hinh.dat_du_lieu([])
        if hasattr(self, 'khung_trang'):
            for k in self.khung_trang.values():
                k.dat_du_an(None)
        if getattr(self, 'khung_du_toan', None) is not None:
            self.khung_du_toan.dat_du_an(None)
        self._xoa_ket_qua()
        self._dem_loc()                                 # danh sách trống: ẩn huy hiệu lọc + dải cộng
        self._cap_nhat_the_so()
        if hasattr(self, 'trang'):
            self._hien_trang_chao()
        return True

    TAI_LAI_HO_TOI_DA = 200        # đổi nhiều hộ hơn (cập nhật trạng thái hàng loạt...): nạp lại toàn bộ

    def tai_lai(self, giu_trang: bool = False):
        """Nạp lại danh sách hộ (và các trang tổng hợp, tiến độ). giu_trang: gọi từ trang tổng hợp / tiến độ sau khi ghi.
        Chỉ một số hộ đổi (csdl.DauVetHo - lưu phương án, sửa hồ sơ, trạng thái một hộ, hoàn tác...): tính và vẽ lại các hộ đó;
        thêm / xóa hộ, đổi danh mục, dự án, quyết định, đợt, hoặc máy khác ghi vào file: nạp lại toàn bộ như trước."""
        doi = self.dv.lay() if self.dv is not None else None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            xong = False
            if self.kq is not None and doi is not None:
                try:
                    xong = self._tai_lai_ho(doi)
                except Exception:                      # tính riêng từng hộ lỗi: nạp lại toàn bộ (không để danh sách sai)
                    xong = False
                    try:
                        import traceback
                        from .giao_dien import ghi_loi_log
                        ghi_loi_log('Tải lại từng hộ lỗi — nạp lại toàn bộ.\n' + traceback.format_exc())
                    except Exception:                   # noqa: BLE001 - không ghi được log thì vẫn nạp lại
                        pass
            if not xong:
                self._tai_lai_toan_bo()
            self._sau_tai_lai(giu_trang)
            self._tc_nap = self.con.total_changes if self.con is not None else None
        finally:
            QApplication.restoreOverrideCursor()

    def _tai_lai_neu_doi(self) -> bool:
        """1.0.09 (người dùng 20/10/2026: "nhập thêm hộ nhưng dự án không cập nhật hộ đó"): cửa sổ lập phương án là TRANG NHÚNG - thêm hộ /
        lưu phương án rồi chuyển trang bằng menu (không bấm Đóng) thì danh sách hộ, thẻ số, màn hình chính còn số cũ (trước chỉ tải lại khi
        đóng cửa sổ hộ). Về trang chính mà file đã ghi kể từ lần tải trước (total_changes của kết nối) thì tải lại - DauVetHo: chỉ tính lại
        hộ đổi, thêm / xóa hộ thì toàn bộ. Trả True nếu đã tải lại."""
        if self.con is None or getattr(self, '_tc_nap', None) is None:
            return False
        try:
            tc = self.con.total_changes
        except sqlite3.ProgrammingError:                # kết nối đã đóng
            return False
        if tc == self._tc_nap:
            return False
        self.tai_lai()
        return True

    def _so_lieu_dong(self, ds_ma_ho=None) -> tuple:
        """(số thửa + DT, trường trạng thái trên bảng ho, TongHopHo, tên đợt) để dựng dòng danh sách; ds_ma_ho: chỉ các hộ này."""
        from . import theo_doi
        from .quan_ly import TRUONG_TT, ds_dot
        loc, ts = '', ()
        if ds_ma_ho is not None:
            loc, ts = f' WHERE ma_ho IN ({",".join("?" * len(ds_ma_ho))})', tuple(ds_ma_ho)
        # tờ/thửa "12/45" của mọi thửa: ô tìm danh sách hộ tìm được theo tờ / thửa (17/10/2026)
        # diện tích cộng bằng Decimal (dải cộng dưới danh sách - trước đây SUM(CAST AS REAL) của SQLite: số thực)
        so_thua = {}
        for ma, dt, to, thua in self.con.execute(f'SELECT ma_ho, dt_thu_hoi, so_to, so_thua FROM thua{loc}', ts):
            n, tong_dt, chu = so_thua.get(ma, (0, D(0), ''))
            try:
                dt = D(dt or 0)
            except (ArithmeticError, ValueError):       # ô diện tích hỏng (file cũ): không cộng, như CAST cũ ra 0
                dt = D(0)
            so_thua[ma] = (n + 1, tong_dt + dt, f'{chu} {to}/{thua}')
        tt = {r['ma_ho']: dict(r) for r in self.con.execute(
            f'SELECT ma_ho, trang_thai, dot_id, dia_chi, so_cccd, {", ".join(TRUONG_TT)} FROM ho{loc}', ts)}
        th = {x.ma_ho: x for x in theo_doi.tong_hop(self.con, ds_ma_ho, tinh_pa=False)}
        ten_dot = {d.id: d.ten for d in ds_dot(self.con)}
        r = self.con.execute('SELECT ten_dia_ban FROM du_an WHERE id = 1').fetchone()
        return so_thua, tt, th, ten_dot, (r[0] or '') if r else ''

    @staticmethod
    def _dong_ho(i: int, h: dict, so_lieu: tuple) -> dict:
        """Một dòng danh sách hộ (BangHo) từ kết quả đối chiếu h của hộ và số liệu _so_lieu_dong."""
        from .man_hinh_theo_doi import VANG as MAU_VANG, XANH as MAU_XANH
        from .quan_ly import TRUONG_TT
        from .ho_so import rut_gon_dia_chi
        so_thua, tt, th, ten_dot, dia_ban = so_lieu
        st, dt, to_thua = so_thua.get(h['ma_ho'], (0, D(0), ''))
        x = tt.get(h['ma_ho'], {})
        t = th.get(h['ma_ho'])
        td = None
        if t is not None:
            t.tong_pa = h['tong']
            td = t.tien_do                              # tiến độ phân tích tự động, tuần tự (theo_doi.phan_tich_tien_do)
            trang_thai = t.trang_thai
            goi_y = '\n'.join([f'QĐ {q["so_qd"]} ({q["ngay_qd"]}): {vn(q["so_tien"]) if q["so_tien"] else "?"} đ - '
                               + (f'đã nhận {q["chi_tra_ngay"]}' if q['da_chi_tra'] else 'chưa nhận') for q in t.qd]
                              + [f'Bàn giao: {t.ban_giao_ngay or "đã"}' if t.da_ban_giao else '',
                                 f'Đợt trình: {ten_dot[x["dot_id"]]}' if x.get('dot_id') in ten_dot else '']).strip()
            mau = MAU_XANH if td.da_bg else (MAU_VANG if t.qd else None)
            if t.qd and t.qd_chua_nhan and len(t.qd_chua_nhan) == len(t.qd):
                mau = None
            if td.canh_bao:                             # dữ liệu nhập tay chưa khớp thứ tự / thiếu biên bản: nền vàng + giải thích
                mau = MAU_VANG
                goi_y = (goi_y + '\n' if goi_y else '') + (
                    f'Cần xem lại: {td.canh_bao}. Nấc tiến độ chỉ tăng khi đủ bước trước (phê duyệt -> nhận đủ tiền) và bàn giao '
                    'có ngày biên bản (Tiến độ chi trả & Bàn giao, bấm đúp hộ).')
        else:
            trang_thai, goi_y, mau = x.get('trang_thai', ''), '', None
        gc = h.get('ghi_chu_dc') or ''
        da_lap = bool(getattr(t, 'da_lap', False) or (t is not None and t.tong_pa > 0))
        # nấc tiến độ (cột Trạng thái, thanh 4 ô) = phân tích TỰ ĐỘNG, tuần tự (17/10/2026): phê duyệt theo quyết định, chi trả khi
        # mọi quyết định đã nhận tiền, bàn giao khi có ngày biên bản. Các cờ phê duyệt / chi trả / bàn giao của dòng (bộ lọc trạng
        # thái quan_ly.hop_trang_thai, thẻ số liệu) lấy CÙNG kết quả này - tích tay "đã bàn giao" không làm thẻ / nấc tăng
        if td is not None:
            nac = td.nac
            x = dict(x, da_phe_duyet=td.da_pd, da_chi_tra=td.da_ct, da_ban_giao=td.da_bg)
        else:
            nac = (4 if x.get('da_ban_giao') else 3 if x.get('da_chi_tra') else 2 if x.get('da_phe_duyet') else
                   1 if da_lap or h['tong'] > 0 else 0)
        return dict(ma_ho=h['ma_ho'], tong=h['tong'], lech=h['lech'], da_lap=da_lap, nac=nac, muc=h.get('muc') or {}, dt=dt,
                    so_thua=st,
                    **{k: x.get(k) for k in TRUONG_TT},
                    dot_id=x.get('dot_id'), goi_y_tt=goi_y, mau_tt=mau, mau_gc=MAU_LECH if gc else None,
                    tim=f'{h["ma_ho"]} {x.get("theo_doi") or ""} {ten_dot.get(x.get("dot_id"), "")} '
                        f'{x.get("qd_so") or ""} {x.get("dia_chi") or ""} {x.get("so_cccd") or ""} {to_thua}',
                    dia_chi=x.get('dia_chi') or '',          # đầy đủ (chú thích); cột hiện bản gọn theo địa bàn dự án
                    o=[i, h['ho_ten'], rut_gon_dia_chi(x.get('dia_chi'), dia_ban), st, dt, trang_thai, gc])

    def _tai_lai_toan_bo(self):
        from . import doi_chieu
        self.kq = doi_chieu.doi_chieu(self.con)
        so_lieu = self._so_lieu_dong()
        self.mo_hinh.dat_du_lieu([self._dong_ho(i, h, so_lieu) for i, h in enumerate(self.kq.ho, start=1)])
        self._nap_ds_dot(so_lieu[3])
        dau = self.bang.horizontalHeader()
        dau.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.bang.resizeColumnsToContents()
        # 1.0.03 (Ảnh 3): 7 cột vừa khít khung nhìn - họ tên / địa chỉ co nhẹ (đủ chữ ở chú thích), Ghi chú (cột cuối) giãn lấp chỗ
        # còn lại, không còn thanh cuộn ngang thừa
        for c, (thap, cao) in RONG_COT_DS.items():
            self.bang.setColumnWidth(c, min(max(int(self.bang.columnWidth(c)), thap), cao))
        self._vua_tieu_de()
        # Họ và tên + Địa chỉ co / giãn theo khung nhìn (chia đều phần còn lại): tổng bề rộng luôn bằng khung - kể cả cỡ chữ 110-125%
        # (kéo giãn cột theo tỷ lệ chữ) - không thanh cuộn ngang; Ghi chú (cột cuối) bề rộng gọn, kéo được
        for c in COT_GIAN_DS:
            dau.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        dau.setStretchLastSection(False)
        self.bang.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    def _tai_lai_ho(self, doi: set) -> bool:
        """Tính lại và vẽ lại các hộ trong doi (csdl.DauVetHo.lay), giữ nguyên các hộ khác, cách sắp xếp, độ rộng cột.
        False: không làm riêng được (nhiều hộ quá, hộ lạ...) - gọi nạp lại toàn bộ."""
        if len(doi) > self.TAI_LAI_HO_TOI_DA:
            return False
        vi_tri = {h['ma_ho']: i for i, h in enumerate(self.kq.ho)}
        if len(self.mo_hinh.dong) != len(self.kq.ho) or any(m not in vi_tri for m in doi):
            return False
        if not doi:
            return True
        from . import doi_chieu
        ds = sorted(doi, key=vi_tri.get)
        moi = doi_chieu.doi_chieu(self.con, ds_ma_ho=ds)
        if sorted(h['ma_ho'] for h in moi.ho) != sorted(ds):
            return False
        for h in moi.ho:
            self.kq.ho[vi_tri[h['ma_ho']]] = h
        theo_vi_tri = lambda x: vi_tri[x[0]]            # noqa: E731 - giữ thứ tự hộ như khi tính cả dự án (sắp xếp ổn định)
        self.kq.dong_lech = sorted([x for x in self.kq.dong_lech if x[0] not in doi] + moi.dong_lech, key=theo_vi_tri)
        self.kq.canh_bao = sorted([x for x in self.kq.canh_bao if x[0] not in doi] + moi.canh_bao, key=theo_vi_tri)
        so_lieu = self._so_lieu_dong(ds)
        for h in moi.ho:
            i = vi_tri[h['ma_ho']]
            self.mo_hinh.thay_dong(i, self._dong_ho(i + 1, h, so_lieu))
        return True

    def _sau_tai_lai(self, giu_trang: bool):
        """Phần chung sau khi nạp lại (toàn bộ hay từng hộ): trang tổng hợp / tiến độ, thẻ số liệu, tiêu đề dự án, đối chiếu."""
        hien = self.trang.currentIndex()
        for i, k in self.khung_trang.items():                    # trang đang xem vừa tự nạp (_da_ghi): không nạp lại, trừ Danh sách hộ
            if giu_trang and i == hien:
                if i == STACK_TONG_HOP:                          # thẻ khác của bảng tổng hợp nạp khi chuyển sang
                    k._can_nap = {0, 1, 2} - {k.tab.currentIndex()}
                continue
            k.nap()
        self._cap_nhat_the_so()
        self._dem_loc()
        da = self.con.execute('SELECT * FROM du_an WHERE id = 1').fetchone()
        # băng tiêu đề: đơn vị lập phương án của DỰ ÁN đang mở (0.9.23 - trước: luôn một đơn vị cố định trong to_chuc.py)
        from .giao_dien import dat_to_chuc
        k = da.keys()
        dv = str(da['don_vi_lap'] or '').strip() if 'don_vi_lap' in k else ''
        cap = str(da['don_vi_cap_tren'] or '').strip() if 'don_vi_cap_tren' in k else ''
        dat_to_chuc(self.bang_tieu_de, dv.upper(), (f'Trực thuộc {cap}   •   ' if cap else '') +
                    f'{da["cap_dia_ban"] or ""} {da["ten_dia_ban"] or ""}'.strip() if dv else '')
        if hasattr(self, 'lb_don_vi'):
            from . import to_chuc
            self.lb_don_vi.setText((dv or to_chuc.TEN).upper())
        self._cap_nhat_chon()
        sua = f' (trừ {self.kq.so_ho_sua} hộ đã sửa trong phần mềm)' if self.kq.so_ho_sua else ''
        from .giao_dien import dat_trang_thai
        if self.kq.khop_het:
            dat_trang_thai(self.lb_ket_qua, 'dat',
                           f'✓ Đối chiếu file Excel: KHỚP 100%{sua}  ·  {len(self.kq.canh_bao)} điểm cần xem lại')
        else:
            # lệch so với file Excel lúc nhập = cần rà lại (thường do đã sửa / áp giá mới), không phải lỗi: màu cảnh báo,
            # kèm bước tiếp theo thay vì chỉ báo con số
            dat_trang_thai(self.lb_ket_qua, 'canh_bao',
                           f'⚠ Đối chiếu file Excel: LỆCH {self.kq.so_ho_lech} hộ, {len(self.kq.dong_lech)} dòng{sua}  ·  '
                           'xem từng dòng lệch: menu trái Lập phương án → Đối chiếu file Excel')
        self.dat_tieu_de()
        self._cap_nhat_hien_hang_the()

    # ------------------------------------------------ lọc danh sách
    def _nap_ds_dot(self, ten_dot: dict):
        cu = self.cb_dot.currentData()
        self.cb_dot.blockSignals(True)
        self.cb_dot.clear()
        self.cb_dot.addItem(TAT_CA_DOT, '')
        self.cb_dot.addItem('Chưa xếp đợt', 'chua')
        for i, t in ten_dot.items():
            self.cb_dot.addItem(t, i)
        k = self.cb_dot.findData(cu) if cu not in (None, '') else 0
        self.cb_dot.setCurrentIndex(max(k, 0))
        self.cb_dot.blockSignals(False)
        self.loc.dat(dot=self.cb_dot.currentData() or '')

    def _loc(self, **kw):
        self.loc.dat(**{k: ('' if v is None else v) for k, v in kw.items()})
        self._dem_loc()

    def _cap_nhat_nhan_viec(self):
        """Nhãn "Chế độ Nhận việc theo hộ (Đang nhận N hộ)" + ô lọc - chỉ hiện khi đang mở bản offline theo hộ."""
        nv = self.nhan_viec
        if not hasattr(self, 'w_nhan_viec'):
            return
        self.w_nhan_viec.setVisible(nv is not None)
        self.lb_nhan_viec.setText(f'Chế độ Nhận việc theo hộ (Đang nhận {len(nv)} hộ)' if nv is not None else '')
        if nv is None and self.o_chi_ho_toi.isChecked():
            self.o_chi_ho_toi.blockSignals(True)
            self.o_chi_ho_toi.setChecked(False)
            self.o_chi_ho_toi.blockSignals(False)
        self._loc_nhan_viec()

    def _loc_nhan_viec(self):
        chi = self.nhan_viec if self.nhan_viec is not None and self.o_chi_ho_toi.isChecked() else None
        if chi is not self.loc.chi_ma:
            self.loc.dat(chi_ma=chi)
            if self.con is not None:
                self._dem_loc()

    def _dem_loc(self):
        """Huy hiệu "Đang lọc: k / N hộ" + dải cộng dưới bảng (cộng các hộ ĐANG HIỆN, Decimal) + thẻ KPI đang lọc."""
        n = self.loc.rowCount()
        ds = self.mo_hinh.dong
        hien = [ds[self.loc.mapToSource(self.loc.index(r, 0)).row()] for r in range(n)]
        tong_muc = cong_dai_cong(hien)
        self.lb_loc.setText(f'Lọc: <b style="color:#1E3A5F">{n}</b>/{len(ds)} hộ · '
                            f'<b style="color:#1E3A5F">{tong_muc["so_thua"]}</b> thửa ↗' if ds else '')
        self.lb_loc.setVisible(bool(ds))
        self._ve_dai_cong(n, tong_muc, co_du_lieu=bool(ds))
        self._cap_nhat_loc_the()

    def _dai_cong(self) -> QWidget:
        """Dải cộng cố định ngay dưới danh sách hộ (Hybrid Enterprise Navy, 17/10/2026): cộng các hộ đang hiện theo bộ lọc."""
        self.dai_cong_ds = DaiCong()
        self.o_cong = self.dai_cong_ds.o
        self._ve_dai_cong(0, None, co_du_lieu=False)
        return self.dai_cong_ds

    def _ve_dai_cong(self, n: int, tong_muc: dict | None, co_du_lieu: bool) -> None:
        if not hasattr(self, 'dai_cong_ds'):
            return
        self.dai_cong_ds.dat(chu_dai_cong(n, tong_muc if co_du_lieu else None))
        self.dai_cong_ds.setVisible(co_du_lieu)

    def ho_dang_loc(self) -> list:
        """Mã hộ đang hiện trong danh sách (sau lọc), theo thứ tự đang sắp."""
        return [self.mo_hinh.dong[self.loc.mapToSource(self.loc.index(r, 0)).row()]['ma_ho'] for r in range(self.loc.rowCount())]

    def _khung_dang_xem(self):
        """Trang bên phải đang xem có bảng hộ riêng (thẻ Bảng tổng hợp, Quyết định, Tiến độ chi trả & Bàn giao); None = danh sách hộ."""
        i = self.trang.currentIndex() if hasattr(self, 'trang') else 0
        if i == STACK_TONG_HOP and STACK_TONG_HOP in getattr(self, 'khung_trang', {}):
            return self.khung_trang[STACK_TONG_HOP].tab.currentWidget()
        return getattr(self, 'khung_trang', {}).get(i)

    def ho_da_chon(self) -> list:
        """Hộ đang chọn TRÊN TRANG ĐANG XEM (trước 0.9.18 luôn lấy ở danh sách hộ - đang ở trang Tiến độ chọn hộ rồi bấm
        "Trạng thái hộ…" ở menu trái thì phần mềm lấy hộ của danh sách đang ẩn)."""
        k = self._khung_dang_xem()
        if k is not None and hasattr(k, 'ma_da_chon'):
            return sorted(k.ma_da_chon())
        return self._ho_chon_ds()

    def _dong_chon_ds(self) -> list:
        """Các dòng (BangHo.dong) có ô đang chọn trên danh sách hộ - chọn 1 ô của 3 hộ = 3 hộ (giao_dien.cac_dong_da_chon)."""
        from .giao_dien import cac_dong_da_chon
        if self.con is None:
            return []
        ds = self.mo_hinh.dong
        return [ds[self.loc.mapToSource(self.loc.index(r, 0)).row()] for r in cac_dong_da_chon(self.bang)]

    def _ho_chon_ds(self) -> list:
        return sorted({d['ma_ho'] for d in self._dong_chon_ds()})

    def mo_ta_loc(self) -> str:
        t = [x for x in (self.cb_dot.currentText() if self.cb_dot.currentData() else '',
                         self.cb_tt.currentText() if self.cb_tt.currentData() else '',
                         f'tìm "{self.o_tim.text()}"' if self.o_tim.text().strip() else '') if x]
        return ', '.join(t)

    # ------------------------------------------------ Tìm nhanh Ctrl+K (man_hinh_tim_nhanh)
    def tim_nhanh(self, cho: bool = True):
        """Hộp Tìm nhanh: chọn hộ (mở hồ sơ như bấm đúp danh sách) hoặc chức năng (chạy QAction). cho=False: chỉ tạo hộp (test)."""
        from .man_hinh_tim_nhanh import HopTimKiemNhanh
        hop = HopTimKiemNhanh(self, im_lang=not cho)
        if cho and hop.exec() == QDialog.DialogCode.Accepted:
            self.thuc_hien_tim_nhanh(hop.ket_qua())
        return hop

    def thuc_hien_tim_nhanh(self, kq):
        """kq = ('ho', mã hộ) | ('lenh', tên lệnh). Lệnh: QAction.trigger() - lệnh đang tắt (chưa mở dự án / chỉ xem) không chạy."""
        if not kq:
            return None
        loai, khoa = kq
        if loai == 'lenh':
            a = self.lenh.get(khoa)
            if a is not None and a.isEnabled():
                a.trigger()
            return None
        idx = self.chon_ho_tren_danh_sach(khoa)
        if idx is not None:
            self.mo_chi_tiet(idx)                       # như bấm đúp: lập phương án (chỉ xem: xem chi tiết)
        return idx

    def chon_ho_tren_danh_sach(self, ma_ho):
        """Về trang Danh sách hộ, chọn và cuộn tới hộ ma_ho (bỏ lọc nếu hộ đang bị lọc ẩn). Trả chỉ số của dòng (bảng) / None."""
        if self.con is None:
            return None
        r = next((i for i, d in enumerate(self.mo_hinh.dong) if d['ma_ho'] == ma_ho), None)
        if r is None:
            return None
        self.mo_trang(TRANG_DS)
        idx = self.loc.mapFromSource(self.mo_hinh.index(r, 0))
        if not idx.isValid():                           # đang lọc ẩn hộ này: bỏ lọc
            self.o_tim.setText('')
            if hasattr(self.o_tim, 'phat_ngay'):
                self.o_tim.phat_ngay()
            self.cb_dot.setCurrentIndex(0)
            self.cb_tt.setCurrentIndex(0)
            idx = self.loc.mapFromSource(self.mo_hinh.index(r, 0))
        if not idx.isValid():
            return None
        self.bang.setCurrentIndex(idx)
        self.bang.scrollTo(idx)
        return idx

    def mo_chi_tiet(self, idx):
        if self.con is None:
            return
        r = self.loc.mapToSource(idx).row()
        if self.chi_doc:
            ChiTietHo(self.con, self.mo_hinh.dong[r]['ma_ho'], self).exec()
            return
        self.mo_lap_pa(self.mo_hinh.dong[r]['ma_ho'])

    # ------------------------------------------------ màn hình chính: thẻ số liệu, thao tác nhanh, menu chuột phải
    # màu từng thẻ: giao_dien.MAU_THE_SO (kiểu nằm trong QSS chung, thẻ chỉ gắn thuộc tính vai / the)
    # 17/10/2026 (Hybrid Enterprise Navy): tiến độ trái -> phải, tổng kinh phí cuối hàng; mỗi thẻ: tên (trên), số + chữ phụ (dưới)
    THE_SO = [('so_ho', 'Số hộ'), ('da_pa', 'Đã lập phương án'), ('da_pd', 'Đã phê duyệt'),
              ('da_ct', 'Đã chi trả'), ('da_bg', 'Đã bàn giao mặt bằng'), ('tong', 'Tổng kinh phí')]
    # bấm thẻ: lọc danh sách hộ theo trạng thái (quan_ly.TRANG_THAI); '' = bỏ lọc trạng thái
    LOC_THE = {'so_ho': '', 'da_pa': 'co_pa', 'tong': '', 'da_pd': 'da_pd', 'da_ct': 'da_ct', 'da_bg': 'da_bg'}
    # 22/10/2026 (nâng cấp giao diện): tên hiện trên thẻ gọn để 6 thẻ không cắt chữ ở 1366 - 1536 px; tên đủ ở chú thích
    TEN_THE_GON = {'da_pa': 'Lập PA', 'da_pd': 'Phê duyệt', 'da_ct': 'Chi trả', 'da_bg': 'Bàn giao', 'tong': 'Kinh phí'}   # tên đủ ở chú thích

    def _hien_ty_le(self, t: float):
        self.nut_ty_le['ty_le'].setText(f'{round(t * 100)}%')
        self.nut_ty_le['ty_le'].setToolTip('Bấm để về 100%. Ctrl + con lăn chuột, Ctrl + "+" / "-" để phóng to / thu nhỏ')

    def _vua_tieu_de(self):
        """Cột không hẹp hơn chữ tiêu đề (tiêu đề in đậm, có mũi tên sắp xếp): không bị mất chữ như "DT thu hồi (m²)"."""
        from PySide6.QtGui import QFontMetrics
        f = QFont(self.bang.font())
        f.setBold(True)
        fm = QFontMetrics(f)
        for v in (self.bang,):
            for c, ten in enumerate(COT):
                can = fm.horizontalAdvance(ten) + 34
                if v.columnWidth(c) < can:
                    v.setColumnWidth(c, can)

    CAO_THE_SO = 62                                      # giữ 62 px (màn 21"): chỗ cho bảng hộ; dòng 2 không cắt nhờ xếp trên, không nới thẻ

    def _hang_the_so(self) -> QHBoxLayout:
        from .giao_dien import MAU_NHOM_KPI, MAU_THE_SO, NHOM_KPI_THE, NhanRutGon, do_bong, tao_thanh_tien_do
        h = QHBoxLayout()
        h.setSpacing(8)                                  # 17/10/2026: thẻ cách 8 px (0.9.95: 4 px, thẻ một dòng 32 px)
        h.setProperty('giu_khoang_cach', True)          # giao_dien.gian_cach không nâng lên 10 px
        # 21/10/2026 (ảnh mẫu người dùng): hàng trên = tên + huy hiệu tỷ lệ % (Tổng kinh phí: tổng ha); hàng dưới = số hộ lớn + đơn
        # vị | vạch dọc | sổ địa chính 2 dòng: số thửa / diện tích (1.0.44: không ghép bằng "/", không RichText — dòng DT
        # từng bị cắt trong thẻ 62 px). the_so[k].text() vẫn CHỈ là số.
        self.the_so, self.the_phu, self.the_khung, self.the_don_vi, self.the_dia_chinh, self.the_dt = {}, {}, {}, {}, {}, {}
        self.the_tien_do = {}                            # 1.0.34: thanh tiến độ (tỷ lệ số hộ) - ẩn ở thẻ Số hộ / Tổng kinh phí
        for k, ten in self.THE_SO:
            khung = TheSo()
            khung.cao_toi_thieu = self.CAO_THE_SO
            khung.setObjectName('the_so')
            khung.setCursor(Qt.CursorShape.PointingHandCursor)
            khung.setToolTip(f'{ten} - ' + ('bấm để xem tất cả hộ' if not self.LOC_THE[k] else f'bấm để lọc danh sách hộ: {ten.lower()}'))
            khung.bam.connect(lambda k=k: self.bam_the_so(k))
            khung.setProperty('vai', 'the_so')
            khung.setProperty('the', k)
            if k in NHOM_KPI_THE:                            # 1.0.33: màu vạch theo nhóm ngữ nghĩa (tiền / đã xong)
                khung.setProperty('nhom_kpi', NHOM_KPI_THE[k])
            khung.setProperty('dang_loc', '0')
            khung.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)    # QWidget thường: cần để QSS vẽ nền / viền
            o = QVBoxLayout(khung)
            o.setContentsMargins(10, 3, 10, 4)
            o.setSpacing(0)
            o.setAlignment(Qt.AlignmentFlag.AlignTop)
            o.setProperty('giu_khoang_cach', True)
            khung.setFixedHeight(self.CAO_THE_SO)
            nhan = NhanRutGon(self.TEN_THE_GON.get(k, ten))     # hẹp (màn hình 1366): rút "…", không ép cửa sổ rộng ra
            nhan.setProperty('vai', 'nhan_the')
            nhan.setToolTip(ten)                         # tên đủ ('Đã phê duyệt', 'Tổng kinh phí'…) khi tên hiện trên thẻ đã rút gọn
            phu = QLabel('')                             # huy hiệu: tỷ lệ % số hộ (Tổng kinh phí: tổng ha)
            phu.setProperty('vai', 'huy_hieu_the')
            phu.setProperty('co', '')
            phu.setVisible(False)
            so = QLabel('–')
            so.setProperty('vai', 'so_the')
            don_vi = QLabel('')
            don_vi.setProperty('vai', 'phu_the')
            vach = QLabel('')
            vach.setProperty('vai', 'vach_the')
            vach.setFixedSize(1, 26)
            dc = QLabel('')
            dc.setProperty('vai', 'dia_chinh_the')
            dc.setWordWrap(False)
            dc.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
            dt = NhanRutGon('')
            dt.setProperty('vai', 'dt_the')
            dt.setMinimumWidth(48)
            dt.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            so_dc = QWidget()
            so_dc.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            so_dc.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Maximum)
            cot_dc = QVBoxLayout(so_dc)
            cot_dc.setContentsMargins(0, 0, 0, 0)
            cot_dc.setSpacing(0)
            cot_dc.setProperty('giu_khoang_cach', True)
            cot_dc.addWidget(dc)
            cot_dc.addWidget(dt)
            for x in (nhan, so, phu, don_vi, vach, dc, dt):  # bấm vào chữ = bấm thẻ
                x.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            tren = QHBoxLayout()
            tren.setContentsMargins(0, 0, 0, 0)
            tren.setSpacing(4)
            tren.setProperty('giu_khoang_cach', True)
            tren.addWidget(nhan, 1)
            tren.addWidget(phu)
            hang = QHBoxLayout()
            hang.setContentsMargins(0, 0, 0, 0)
            hang.setSpacing(5)
            hang.setProperty('giu_khoang_cach', True)
            hang.addWidget(so, 0, Qt.AlignmentFlag.AlignBaseline)
            hang.addWidget(don_vi, 0, Qt.AlignmentFlag.AlignBaseline)
            hang.addSpacing(4)
            hang.addWidget(vach, 0, Qt.AlignmentFlag.AlignVCenter)
            hang.addWidget(so_dc, 1, Qt.AlignmentFlag.AlignTop)   # không căn giữa: thanh ẩn làm dòng m² rơi vào bo góc
            o.addLayout(tren)
            o.addLayout(hang)
            o.setAlignment(hang, Qt.AlignmentFlag.AlignTop)
            o.addStretch(1)                                      # chỗ thừa ở đáy thẻ, không đẩy chữ xuống
            thanh = tao_thanh_tien_do(MAU_NHOM_KPI.get(NHOM_KPI_THE.get(k, ''), MAU_THE_SO.get(k, '#2563EB')))
            # 1.0.52 (ảnh người dùng 02/11/2026: thanh đè dòng "42.914,0 m²" ở cỡ chữ 125%): thanh NỔI sát mép dưới, ngoài bố cục -
            # chữ dùng trọn chiều cao thẻ 62 px. Đặt cha TRƯỚC khi ẩn / hiện (widget không cha hiện thành cửa sổ riêng)
            thanh.setParent(khung)
            thanh.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            thanh.setFixedHeight(4)
            thanh.setVisible(False)
            khung.thanh = thanh
            khung._dat_thanh()
            self.the_tien_do[k] = thanh
            do_bong(khung, 14, 2, 26)
            self.the_so[k], self.the_phu[k], self.the_khung[k] = so, phu, khung
            self.the_don_vi[k], self.the_dia_chinh[k], self.the_dt[k] = don_vi, dc, dt
            h.addWidget(khung, 7 if k == 'tong' else 6)     # thẻ Tổng kinh phí (số tiền + huy hiệu ha) rộng hơn: không cắt tên
        return h

    def _cap_nhat_loc_the(self):
        """Thẻ KPI ứng với bộ lọc trạng thái đang dùng: property dang_loc="1" (nền xanh băng, viền navy) - nhìn là biết đang lọc gì."""
        tt = self.cb_tt.currentData() or '' if hasattr(self, 'cb_tt') else ''
        for k, khung in getattr(self, 'the_khung', {}).items():
            v = '1' if tt and self.LOC_THE.get(k) == tt and self.con is not None else '0'
            if khung.property('dang_loc') != v:
                khung.setProperty('dang_loc', v)
                khung.style().unpolish(khung)
                khung.style().polish(khung)

    def _cap_nhat_the_so(self):
        ds = self.mo_hinh.dong
        tong = sum((d['tong'] for d in ds), D(0))
        # "đã lập" không tính phương án phần mềm tự lập lúc tạo Dự án mới mà chưa mở soát (in_an.phan_loai_lap)
        lap = {}
        if ds and self.con is not None:
            try:
                lap = lap_pa.phan_loai_lap(self.con)
            except Exception:                           # file chỉ xem phiên bản cũ...: đếm như trước
                lap = {}
        da_pa = sum(1 for v in lap.values() if v == 'da_lap') if lap else sum(1 for d in ds if d['tong'] > 0)
        tu_lap = sum(1 for v in lap.values() if v == 'tu_lap')
        gt = dict(so_ho=len(ds), da_pa=da_pa, tong=vn_gon(tong) if ds else '–',
                  da_pd=sum(1 for d in ds if d.get('da_phe_duyet')), da_ct=sum(1 for d in ds if d.get('da_chi_tra')),
                  da_bg=sum(1 for d in ds if d.get('da_ban_giao')))
        from .tien import phan_tram
        n = len(ds)
        nhom = nhom_dia_chinh(ds, lap)
        for k, o in self.the_so.items():
            v = gt[k]
            o.setText(str(v) if ds else '–')
            if k in getattr(self, 'the_don_vi', {}):
                self.the_don_vi[k].setText(('VNĐ' if k == 'tong' else 'hộ') if ds else '')
            if k in getattr(self, 'the_dia_chinh', {}):
                _h, t, dt = nhom[k]
                dc = self.the_dia_chinh[k]
                o_dt = getattr(self, 'the_dt', {}).get(k)
                chu_thua, chu_dt = (f'{t} thửa', f'{so_luong_vn(dt)} m²') if ds else ('', '')
                chu_tip = f'{_h} hộ · {t} thửa · {so_luong_vn(dt)} m² ({so_ha(dt)})' if ds else ''
                dc.setText(chu_thua)
                dc.setToolTip(chu_tip)
                if o_dt is not None:
                    o_dt.setText(chu_dt)
                    o_dt.setToolTip(chu_tip)
            phu = self.the_phu.get(k) if hasattr(self, 'the_phu') else None
            if phu is None:
                continue
            if k == 'tong':                              # huy hiệu thẻ Tổng kinh phí: tổng DT thu hồi quy đổi ha
                chu, co = (so_ha(nhom['tong'][2]), 'ha') if ds else ('', '')
            else:                                        # tỷ lệ so với tổng số hộ (Decimal) - số hộ đủ ở chú thích của số
                chu = phan_tram(v, n) if ds else ''
                co = '1' if ds and v and k != 'so_ho' else ''
                if k != 'so_ho':
                    o.setToolTip(f'{v} / {n} hộ' if ds else '')
            phu.setText(chu)
            phu.setVisible(bool(chu))
            thanh = getattr(self, 'the_tien_do', {}).get(k)
            if thanh is not None:                        # tỷ lệ hoàn thành theo số hộ (không có ở Số hộ / Tổng kinh phí)
                co = bool(ds) and k not in ('so_ho', 'tong')
                thanh.setVisible(co)
                if co:
                    thanh.setValue(int(round(v * 100 / n)) if n else 0)
            if phu.property('co') != co:
                phu.setProperty('co', co)
                phu.style().unpolish(phu)
                phu.style().polish(phu)
        if 'tong' in self.the_so:
            self.the_so['tong'].setToolTip(f'{vn(tong)} đồng' if ds else '')
        if tu_lap and 'da_pa' in self.the_so:
            self.the_so['da_pa'].setToolTip(self.the_so['da_pa'].toolTip() +
                                            f'\n{tu_lap} hộ có phương án phần mềm tự lập, chưa mở soát và lưu')
        self._cap_nhat_loc_the()

    def bam_the_so(self, k: str):
        """Thẻ số liệu: Số hộ / Tổng kinh phí = bỏ mọi bộ lọc; thẻ khác = lọc trạng thái tương ứng; về danh sách hộ."""
        if self.con is None:
            return
        if not self.LOC_THE.get(k):
            self.cb_dot.setCurrentIndex(0)
            self.o_tim.clear()
            self.o_tim.phat_ngay()                      # bỏ lọc ngay, không chờ ô tìm
        self.cb_tt.setCurrentIndex(max(0, self.cb_tt.findData(self.LOC_THE.get(k, ''))))
        self.mo_trang(0)

    # ------------------------------------------------ thanh công cụ danh sách hộ, màn hình chào
    def _thanh_cong_cu_ds(self):
        """Thanh công cụ theo ngữ cảnh của danh sách hộ (0.9.23 - lộ trình người dùng): Thêm hộ, Lập phương án, Xóa hộ (chỉ
        sáng khi đang chọn hộ) - trước nằm ở menu trái (điều hướng) như một màn hình; đặt cùng hàng với bộ lọc. Chọn nhiều hộ:
        hàng "Đã chọn N hộ" với thao tác hàng loạt. Nút dùng chính QAction của lệnh (tắt khi chỉ xem như mọi nơi khác)."""
        from .giao_dien import KieuNut, XepDong, ap_kieu_nut, nut_lenh
        # hai khối (nút | bộ lọc) trong XepDong: hẹp thì bộ lọc xuống dòng - một hàng cứng cần 1136 điểm + menu trái 248 = cửa
        # sổ tối thiểu 1414 điểm, rộng hơn màn hình 1366 (và làm hỏng phóng to lúc mở: xem hien_cua_so)
        h = XepDong(cach=12)
        nhom_nut = QWidget()
        hn = QHBoxLayout(nhom_nut)
        hn.setContentsMargins(0, 0, 0, 0)
        hn.setSpacing(6)
        self.nut_ds = {}
        # 0.9.66 (bỏ lệnh trùng): chỉ lệnh KHÔNG có ở menu trái / thanh menu - Thêm hộ, Xóa hộ. Lập phương án (menu trái), Xuất
        # danh sách hộ (menu Dữ liệu) không lặp ở đây
        # 0.9.69: Chọn hộ niêm yết (đánh dấu hộ đủ điều kiện niêm yết, lấy ý kiến sau khi lập phương án) - chỉ có ở đây
        # 17/10/2026 (Hybrid Enterprise Navy): dải cao CAO_DAI_CONG_CU 32 px - Thêm hộ nền navy đặc (thao tác chính), Xóa hộ viền mảnh
        # đỏ (tắt: mờ), Chọn hộ niêm yết kiểu phụ nền trắng viền xám
        # 31/10/2026: Xem hộ trên bản đồ - thửa thu hồi của hộ đang chọn trên nền vệ tinh (chỉ có ở đây + chuột phải)
        for ten, kieu in (('Thêm hộ…', KieuNut.CHINH), ('Xóa hộ…', KieuNut.NGUY_HIEM), ('Chọn hộ niêm yết…', KieuNut.PHU),
                          ('Xem hộ trên bản đồ…', KieuNut.PHU)):
            b = nut_lenh(self.lenh[ten], 16)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            b.setFixedHeight(CAO_DAI_CONG_CU)
            b.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            ap_kieu_nut(b, kieu)
            hn.addWidget(b)
            self.nut_ds[ten] = b
        self.lenh['Chọn hộ niêm yết…'].setToolTip(
            'Đánh dấu hộ đủ điều kiện niêm yết công khai, lấy ý kiến (đã lập phương án, đủ họ tên, nguồn gốc thửa, không tranh '
            'chấp, không vướng): các hộ đang chọn (từ 2 hộ), không thì cả dự án')
        self.lenh['Xuất danh sách hộ…'].setToolTip(
            'Xuất Excel danh sách hộ để theo dõi, trình, lưu trữ: các hộ đang chọn (từ 2 hộ), không thì các hộ đang hiện theo '
            'Đợt / Trạng thái / Tìm')
        hn.addStretch(1)
        nhom_loc = QWidget()
        hl = QHBoxLayout(nhom_loc)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        # bộ lọc không còn nhãn "Đợt:", "Trạng thái:", "Tìm:" riêng: mục đầu của ô chọn ghi "Đợt: Tất cả" / "Trạng thái: Tất cả", ô
        # tìm có kính lúp + chữ gợi ý; huy hiệu "Đang lọc: k / N hộ" cuối hàng
        for w in (self.cb_dot, self.cb_tt, self.o_tim):
            w.setFixedHeight(CAO_DAI_CONG_CU)
            w.setProperty('loc_ds', '1')
            hl.addWidget(w, 1 if w is self.o_tim else 0)
        self.cb_dot.setToolTip('Lọc danh sách hộ theo đợt trình')
        self.cb_tt.setToolTip('Lọc danh sách hộ theo trạng thái xử lý (cũng lọc khi bấm thẻ số liệu)')
        self.lb_loc.setFixedHeight(CAO_DAI_CONG_CU)
        self.lb_loc.setProperty('vai', 'huy_hieu_loc')
        self.lb_loc.setTextFormat(Qt.TextFormat.RichText)
        # 1.0.29: đang mở bản offline THEO HỘ (máy chủ LAN, chia việc): nhãn chế độ + lọc nhanh hộ mình nhận - ẩn với file thường
        self.w_nhan_viec = QWidget()
        hv = QHBoxLayout(self.w_nhan_viec)
        hv.setContentsMargins(0, 0, 0, 0)
        hv.setSpacing(6)
        self.lb_nhan_viec = QLabel('')
        self.lb_nhan_viec.setProperty('vai', 'huy_hieu_loc')
        self.lb_nhan_viec.setToolTip('Bản offline nhận theo hộ: chỉ các hộ đã nhận được lưu và gộp lên máy chủ')
        self.o_chi_ho_toi = QCheckBox('Chỉ hiện hộ tôi nhận')
        self.o_chi_ho_toi.toggled.connect(lambda b: self._loc_nhan_viec())
        hv.addWidget(self.lb_nhan_viec)
        hv.addWidget(self.o_chi_ho_toi)
        hl.addWidget(self.w_nhan_viec)
        self.w_nhan_viec.setVisible(False)
        hl.addWidget(self.lb_loc)
        h.addWidget(nhom_nut)
        h.addWidget(nhom_loc)
        # 0.9.66: bỏ hàng "Đã chọn N hộ" (In / Xuất, Đợt trình, Trạng thái hộ - menu trái; Xóa hộ - nút ngay trên). Số hộ đang
        # chọn hiện ở thanh trạng thái (lb_tom_tat), thao tác hàng loạt qua menu trái / chuột phải trên các hộ đã chọn
        return h

    def _cap_nhat_chon(self):
        """Xóa hộ chỉ sáng khi đang chọn hộ trên danh sách; số hộ đang chọn ở thanh trạng thái."""
        chon = self._dong_chon_ds()
        a_xoa = self.lenh['Xóa hộ…']
        a_xoa.setEnabled(bool(chon) and not self.chi_doc)
        if self.chi_doc:
            a_xoa.setToolTip('Dự án đang chỉ xem — không xóa được.')
        elif not chon:
            a_xoa.setToolTip('Chọn hộ trên danh sách rồi bấm Xóa hộ.')
        else:
            a_xoa.setToolTip(GOI_Y_MENU.get('Xóa hộ…', 'Xóa hộ'))
        self._ap_vai_tro_lenh()
        if self.con is None:
            self.lb_tom_tat.setText('Sẵn sàng · Chưa mở dự án')
            return
        n, t, dt = dia_chinh(self.mo_hinh.dong)
        k, tk, dtk = dia_chinh(chon)
        self.lb_tom_tat.setText(f'Sẵn sàng · Dự án: {n} hộ · {t} thửa · {so_luong_vn(dt)} m² | '
                                f'Đang chọn: {k} hộ ({tk} thửa · {so_luong_vn(dtk)} m²)')

    def _trang_chao(self) -> QWidget:
        """Màn hình chính (ô TRANG_CHAO của self.trang) = ngan_chao: ô 0 màn hình chào khi chưa mở dự án (0.9.23: thẻ bắt đầu + dự
        án gần đây), ô 1 tổng quan dự án khi đã mở dự án (1.0.07, man_hinh_tong_quan - tạo khi cần lần đầu: _nap_tong_quan)."""
        self.ngan_chao = QStackedWidget()
        self.ngan_chao.addWidget(self._trang_chao_bat_dau())
        self.tong_quan = None
        return self.ngan_chao

    def _nap_tong_quan(self):
        """Đã mở dự án: Màn hình chính hiện tổng quan dự án (KPI, hộ đang làm dở, đồng hồ pháp lý); chưa mở: màn hình chào."""
        if not hasattr(self, 'ngan_chao'):
            return
        if self.con is None or self.file is None or not hasattr(self, 'mo_hinh'):
            self.ngan_chao.setCurrentIndex(0)
            return
        if self.tong_quan is None:
            from .man_hinh_tong_quan import KhungTongQuanDuAn
            self.tong_quan = KhungTongQuanDuAn(self.lenh)
            self.tong_quan.mo_ho.connect(lambda m: self._chay_lenh(lambda: self.mo_lap_pa(m)))
            self.tong_quan.mo_buoc.connect(lambda b: self._chay_lenh(lambda: self.mo_buoc_quy_trinh(b)))
            self.tong_quan.chay_lenh.connect(self._kich_lenh)
            self.ngan_chao.addWidget(self.tong_quan)
            if self.isVisible():
                from .giao_dien import ap_kieu_cay
                ap_kieu_cay(self.tong_quan)
        da = {}
        try:
            r = self.con.execute('SELECT * FROM du_an WHERE id = 1').fetchone()
            da = dict(r) if r is not None else {}
        except Exception:
            da = {}
        dia_ban = f'{da.get("cap_dia_ban") or ""} {da.get("ten_dia_ban") or ""}'.strip()
        try:
            lap = lap_pa.phan_loai_lap(self.con)
            self.tong_quan.nap(self.con, self.mo_hinh.dong, da.get('ten') or self.file.stem, dia_ban, str(self.file),
                               da.get('chu_dau_tu') or '', lap=lap)
        except Exception as e:                          # số liệu phụ (niêm yết, vận động) lỗi: vẫn hiện màn hình chính
            self.statusBar().showMessage(chu_loi('Không tính được số liệu tổng quan', e), 8000)
        self.ngan_chao.setCurrentWidget(self.tong_quan)

    def _kich_lenh(self, khoa: str) -> None:
        """Chạy QAction của self.lenh (nút "Làm ngay" của buồng lái). Lệnh tắt (chưa đủ điều kiện / chỉ xem): trigger không làm gì."""
        a = self.lenh.get(khoa)
        if a is not None and a.isEnabled():
            a.trigger()

    def mo_buoc_quy_trinh(self, buoc: int, ngay=None, cho: bool = True):
        """Bấm một bước của quy trình QĐ 18 (buồng lái): bước đánh dấu bằng ngày (họp dân, thông báo thu hồi, công khai quyết định,
        gửi phương án, quyết định thu hồi) -> ghi ngày; bước khác -> mở chỗ làm (QAction quy_trinh.LENH_BUOC)."""
        from . import quy_trinh
        if self.con is None:
            return None
        if buoc in quy_trinh.MOC_BUOC:
            return self.ghi_ngay_buoc(buoc, ngay, cho)
        khoa = quy_trinh.LENH_BUOC.get(buoc)
        if khoa:
            self._kich_lenh(khoa)
        return khoa

    def ghi_ngay_buoc(self, buoc: int, ngay=None, cho: bool = True) -> bool:
        """Ghi / xóa ngày đánh dấu xong của bước (quy_trinh.MOC_BUOC). ngay None + cho: hỏi bằng hộp nhập. True nếu đã ghi."""
        from PySide6.QtWidgets import QInputDialog
        from . import quy_trinh
        if self.chi_doc:
            QMessageBox.information(self, TEN_UD, 'Dự án đang mở chỉ xem: không ghi được ngày của bước.')
            return False
        if ngay is None:
            if not cho:
                return False
            cu = quy_trinh.doc_moc(self.con, buoc)
            chu, ok = QInputDialog.getText(
                self, TEN_UD, f'Bước {buoc} - {quy_trinh.TEN_BUOC[buoc]}\nNgày thực hiện (ngày/tháng/năm, để trống = bỏ ngày):',
                text=cu.strftime('%d/%m/%Y') if cu else '')
            if not ok:
                return False
            ngay = chu.strip()
        try:
            quy_trinh.ghi_moc(self.con, buoc, ngay)
        except lap_pa.LoiNhap as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return False
        self._nap_tong_quan()
        return True

    def _trang_chao_bat_dau(self) -> QWidget:
        """Màn hình chào khi chưa mở dự án (0.9.23 - thay dòng chữ vàng): 3 nút bắt đầu + dự án làm việc gần đây."""
        from .giao_dien import TOKEN, nut_lenh
        from .giao_dien import OTimKiemThongMinh
        w = QWidget()
        lo = QVBoxLayout(w)
        # 26/10/2026 (người dùng): nội dung sát lên trên (bỏ khoảng trống đầu trang), bảng dự án gần đây giãn hết phần còn lại
        lo.setContentsMargins(32, 12, 32, 12)
        tieu = QLabel('Hệ thống quản lý bồi thường, hỗ trợ và GPMB')
        tieu.setStyleSheet(f'QLabel {{ font-size: 18px; font-weight: 700; color: {TOKEN["chinh"]}; letter-spacing: 0; }}')
        tieu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lo.addWidget(tieu)
        self.lb_chao = QLabel('Khởi tạo dự án mới hoặc tiếp tục làm việc với các hồ sơ gần đây')
        self.lb_chao.setWordWrap(True)
        self.lb_chao.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb_chao.setStyleSheet(f'QLabel {{ color: {TOKEN["chu_phu"]}; font-size: 13px; }}')
        lo.addWidget(self.lb_chao)
        h = QHBoxLayout()
        h.setSpacing(20)
        h.addStretch(1)
        self.nut_chao = {}
        mo_ta_nut = (
            ('Dự án mới…', 'moi', 'Khởi tạo CSDL .larc', 'Tạo dự án mới (3 bước) - Ctrl+N'),
            ('Mở dự án…', 'mo', 'Chọn tệp từ máy / LAN', 'Mở file dự án có sẵn (.larc, .pabt) - Ctrl+O'),
            ('Nhập file Excel…', 'excel', 'Bảng kiểm đếm số liệu', 'Nhập nhanh từ bảng kiểm đếm Excel'),
            # 1.0.04: tiếp nhận hồ sơ pháp lý đầu vào (máy trắng, chưa có dự án) - cùng QAction với menu trái (trigger)
            ('Tiếp nhận & Kiểm tra pháp lý dự án…', 'phap_ly', 'Kiểm tra hồ sơ đầu vào',
             'Tiếp nhận & kiểm tra pháp lý hồ sơ dự án trước khi triển khai - Ctrl+Shift+L'),
        )
        from .giao_dien import CO_ICON_THE_CHAO, TheChao
        self.the_chao = {}
        for ten, loai, phu, goi_y in mo_ta_nut:
            the = TheChao(loai=loai)
            b = nut_lenh(self.lenh[ten], CO_ICON_THE_CHAO, duoi=True)
            b.setToolTip(goi_y)
            the.setToolTip(goi_y)
            the.dat_noi_dung(b, phu)               # biểu tượng 38px, tên lệnh, mô tả: tất cả trong thẻ
            h.addWidget(the)
            self.nut_chao[ten] = b
            self.the_chao[ten] = the
        h.addStretch(1)
        lo.addLayout(h)
        # Đóng / Xóa dự án chỉ ở menu Tệp tin (0.9.66: bỏ hàng nút luôn ẩn từ 0.9.38)
        # 0.9.80: thanh công cụ NGAY TRÊN ĐẦU bảng: tiêu đề | Mở đã chọn, Xóa khỏi danh sách, Xóa file | ô tìm (bo 6px); bảng trống thì ẩn cụm nút
        from PySide6.QtWidgets import QPushButton
        hang_gd = QHBoxLayout()
        hang_gd.setSpacing(8)
        nhan = QLabel('Hồ sơ dự án làm việc gần đây')
        nhan.setProperty('vai', 'nhan')
        hang_gd.addWidget(nhan)
        self.khung_nut_gan = QWidget()
        h3 = QHBoxLayout(self.khung_nut_gan)
        h3.setContentsMargins(8, 0, 0, 0)
        h3.setSpacing(6)
        self.b_mo_gan = QPushButton('Mở đã chọn')
        self.b_mo_gan.setToolTip('Đóng dự án hiện tại (nếu có) và mở file đang chọn — không cần thoát phần mềm')
        self.b_mo_gan.clicked.connect(lambda: self._chay_lenh(self._mo_gan_day_chon))
        self.b_bo_gan = QPushButton('Xóa khỏi danh sách')
        self.b_bo_gan.setToolTip('Bỏ khỏi danh sách gần đây; file dự án vẫn còn trên đĩa')
        self.b_bo_gan.clicked.connect(lambda: self._chay_lenh(lambda: self.xoa_du_an(xoa_file=False, tu_danh_sach=True)))
        self.b_xoa_gan = QPushButton('Xóa file dự án…')
        self.b_xoa_gan.setToolTip('Xóa hẳn file dự án đang chọn (không đưa vào Thùng rác). Thư mục bản in giữ nguyên.')
        self.b_xoa_gan.clicked.connect(lambda: self._chay_lenh(lambda: self.xoa_du_an(xoa_file=True, tu_danh_sach=True)))
        for b in (self.b_mo_gan, self.b_bo_gan, self.b_xoa_gan):
            h3.addWidget(b)
        hang_gd.addWidget(self.khung_nut_gan)
        hang_gd.addStretch(1)
        self.o_tim_gan = OTimKiemThongMinh()
        self.o_tim_gan.setPlaceholderText('Tìm theo tên dự án, địa bàn...')
        self.o_tim_gan.setMinimumWidth(240)
        self.o_tim_gan.setMaximumWidth(300)
        dat_kieu_theo_tong(self.o_tim_gan,
            'QLineEdit { border: 1px solid #8696AB; border-radius: 6px; padding: 4px 8px; background: #FFFFFF; }'
            'QLineEdit:focus { border: 2px solid #2563EB; padding: 3px 7px; }')
        self.o_tim_gan.chuoi_da_doi.connect(self._loc_gan_day)
        hang_gd.addWidget(self.o_tim_gan)
        lo.addSpacing(8)
        lo.addLayout(hang_gd)
        self.ds_gan_day = QTableWidget(0, 6)
        self.ds_gan_day.setHorizontalHeaderLabels(
            ['Tên dự án và địa bàn', 'Số hộ', 'Tổng kinh phí', 'Cập nhật', 'Ghim', 'Thao tác'])
        self.ds_gan_day.horizontalHeader().setStretchLastSection(True)
        self.ds_gan_day.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3, 4):                           # tiêu đề đậm (nền navy): cột vừa cả chữ tiêu đề lẫn số liệu, không cắt "Tổng kinh phí"
            self.ds_gan_day.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.ds_gan_day.verticalHeader().setVisible(False)
        self.ds_gan_day.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ds_gan_day.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ds_gan_day.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ds_gan_day.cellDoubleClicked.connect(lambda r, _c: self._mo_gan_day_dong(r))
        self.ds_gan_day.itemSelectionChanged.connect(self._cap_nhat_nut_gan_day)
        # trạng thái trống (0.9.80): không hiện lưới trắng trơ trọi - biểu tượng thư mục + hướng dẫn bắt đầu, ở giữa vùng bảng
        self.ngan_gan_day = QStackedWidget()
        self.ngan_gan_day.addWidget(self.ds_gan_day)
        self.ngan_gan_day.addWidget(self._trang_trong_gan_day())
        lo.addWidget(self.ngan_gan_day, 1)                # giãn hết chiều cao còn lại (trước: tối đa 220 px, dưới trống)
        # chân trang 4 liên kết (0.9.80): Hướng dẫn · Bảng giá đất NQ 28 · Quy trình 16 bước · Lịch sử cập nhật
        chan = QHBoxLayout()
        chan.setContentsMargins(0, 10, 0, 0)
        chan.setSpacing(14)
        chan.addStretch(1)
        self.lk_huong_dan = None
        self.lien_ket_chan = {}
        for i, (ma, ten, chu, goi_y, ham) in enumerate((
                (0xE897, 'huong_dan', 'Hướng dẫn sử dụng (F1)', 'Hướng dẫn sử dụng phần mềm',
                 lambda: self._chay_lenh(self.lenh['Hướng dẫn sử dụng'].trigger)),
                (0xE707, 'bang_gia_dat', 'Tra cứu Bảng giá đất NQ 28', 'Tra cứu bảng giá đất Nghị quyết 28/2025',
                 lambda: self._chay_lenh(self.lenh['Bảng giá đất NQ 28…'].trigger)),
                (0xE8FD, 'quy_trinh', 'Quy trình 16 bước QĐ 18', 'Quy trình 16 bước thu hồi đất, bồi thường theo QĐ 18/2026 và chỗ làm trong phần mềm',
                 lambda: self._chay_lenh(self.quy_trinh_16_buoc)),
                (0xE81C, 'lich_su', 'Lịch sử cập nhật phần mềm', 'Các bản cập nhật từ phiên bản 0.9.53',
                 lambda: self._chay_lenh(self.lich_su_cap_nhat)))):
            if i:
                cham = QLabel('·')
                dat_kieu_theo_tong(cham, 'QLabel { color: #94A3B8; font-size: 14px; font-weight: 700; background: transparent; }')
                chan.addWidget(cham)
            khung, lk = self._lien_ket_icon(ma, chu, ham)
            lk.setToolTip(goi_y)
            chan.addWidget(khung)
            self.lien_ket_chan[ten] = lk
        self.lk_huong_dan = self.lien_ket_chan['lich_su']      # tên cũ (test): liên kết "Lịch sử cập nhật phần mềm"
        chan.addStretch(1)
        lo.addLayout(chan)
        return w

    def _lien_ket_icon(self, ma: int, chu: str, ham):
        """Liên kết chân trang: biểu tượng nhỏ (phông Segoe MDL2; máy không có phông chỉ hiện chữ) + chữ bấm được."""
        from .giao_dien import icon_ky_hieu
        khung = QWidget()
        h = QHBoxLayout(khung)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(5)
        ic = icon_ky_hieu(ma, '#475569', 16)
        if ic is not None:
            lb_ic = QLabel()
            lb_ic.setPixmap(ic.pixmap(16, 16))
            lb_ic.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            h.addWidget(lb_ic)
        lk = self._lien_ket_chan(chu, ham)
        h.addWidget(lk)
        return khung, lk

    def _trang_trong_gan_day(self) -> QWidget:
        """Trạng thái trống của bảng dự án gần đây."""
        from .giao_dien import icon_ky_hieu
        w = QWidget()
        w.setObjectName('trong_gan_day')
        dat_kieu_theo_tong(w, 'QWidget#trong_gan_day { background: transparent; border: 1px dashed #CBD5E1; border-radius: 8px; }')
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(8)
        v.addStretch(1)
        self.lb_trong_icon = QLabel()
        self.lb_trong_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb_trong_icon.setStyleSheet('QLabel { background: transparent; border: 0; }')
        ic = icon_ky_hieu(0xE8B7, '#94A3B8', 42)                 # thư mục (không dùng emoji: Windows 7 không có phông emoji)
        if ic is not None:
            self.lb_trong_icon.setPixmap(ic.pixmap(42, 42))
        else:
            self.lb_trong_icon.setVisible(False)
        v.addWidget(self.lb_trong_icon)
        self.lb_trong = QLabel('Chưa có hồ sơ dự án nào được mở gần đây.\n'
                               "Hãy bấm 'Dự án mới' hoặc 'Mở dự án' phía trên để bắt đầu.")
        self.lb_trong.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dat_kieu_theo_tong(self.lb_trong, 'QLabel { color: #64748B; font-size: 13px; background: transparent; border: 0; }')
        v.addWidget(self.lb_trong)
        v.addStretch(1)
        return w

    def _hien_trong_gan_day(self):
        """Bảng trống: hiện trạng thái trống, ẩn cụm nút thao tác, tắt ô tìm; có dòng: ngược lại."""
        co = self.ds_gan_day.rowCount() > 0
        self.ngan_gan_day.setCurrentIndex(0 if co else 1)
        self.khung_nut_gan.setVisible(co)
        self.o_tim_gan.setEnabled(co)

    def quy_trinh_16_buoc(self, cho: bool = True):
        """Liên kết chân trang "Quy trình 16 bước QĐ 18": bảng 16 bước và chỗ làm từng bước trong phần mềm."""
        from .man_hinh_quy_trinh import HopQuyTrinh
        hop = HopQuyTrinh(self)
        if cho:
            hop.exec()
        return hop

    def _lien_ket_chan(self, chu, ham):
        from .giao_dien import NhanBam
        lk = NhanBam(chu)
        lk.setProperty('vai', 'lien_ket')
        lk.setCursor(Qt.CursorShape.PointingHandCursor)
        lk.bam = ham
        return lk

    def _nap_gan_day(self):
        from datetime import datetime
        import time
        viec = ('Khởi tạo dự án mới hoặc tiếp tục làm việc với các hồ sơ gần đây.')
        self.lb_chao.setText(f'Đang mở dự án {self.file.name} — bấm một mục ở menu trái để quay lại làm việc. {viec}'
                             if self.con is not None and self.file else viec)
        self.ds_gan_day.setRowCount(0)
        n = 0
        ghim = {x.lower() for x in doc_ghim()}
        ds = doc_gan_day()
        dau = [x for x in doc_ghim() if any(x.lower() == y.lower() for y in ds)]
        con = [x for x in ds if x.lower() not in ghim]
        from .giao_dien import icon_ky_hieu, TOKEN
        ic_file = icon_ky_hieu(0xE8E5, TOKEN['chinh'], 16)
        for f in map(Path, dau + con):
            try:
                st = f.stat()
            except OSError:
                continue
            if self.con is not None and self.file is not None and self.kq is not None and f.resolve() == self.file.resolve():
                ghi_tong_nho(f, len(self.kq.ho), sum((h['tong'] for h in self.kq.ho), D('0')))    # dự án đang mở: tổng vừa tính, khỏi tính lại
            so_ho, tong, chu_tim, ten_hien = _tom_tat_pabt(f)
            r = self.ds_gan_day.rowCount()
            self.ds_gan_day.insertRow(r)
            ten = QTableWidgetItem(ten_hien)
            ten.setData(Qt.ItemDataRole.UserRole, str(f))
            ten.setData(Qt.ItemDataRole.UserRole + 1, f'{f.name} {chu_tim}')      # ô tìm: tên file + tên dự án + địa bàn
            ten.setToolTip(str(f))
            if ic_file is not None:
                ten.setIcon(ic_file)
            self.ds_gan_day.setItem(r, 0, ten)
            self.ds_gan_day.setItem(r, 1, QTableWidgetItem('—' if so_ho is None else f'{so_ho} hộ'))
            o_tong = QTableWidgetItem('—' if tong is None else tong)
            o_tong.setFont(phong_so())                  # 1.0.51: số tiền phông số
            self.ds_gan_day.setItem(r, 2, o_tong)
            cach = time.time() - st.st_mtime
            if cach < 3600:
                luc = f'{max(1, int(cach // 60))} phút trước'
            elif cach < 86400:
                luc = 'Hôm nay'
            else:
                luc = datetime.fromtimestamp(st.st_mtime).strftime('%d/%m/%Y')
            self.ds_gan_day.setItem(r, 3, QTableWidgetItem(luc))
            from PySide6.QtWidgets import QPushButton, QToolButton
            da_ghim = str(f.resolve()).lower() in ghim or str(f).lower() in ghim
            b_ghim = QToolButton()
            # 17/10/2026: biểu tượng ghim của phông Segoe MDL2 (đã ghim: ghim đặc navy) thay emoji ghim - Windows 7 không có
            # phông emoji (hiện ô vuông); máy không có phông biểu tượng thì hiện chữ
            ic_ghim = icon_ky_hieu(0xE841 if da_ghim else 0xE718, TOKEN['chinh'] if da_ghim else '#94A3B8', 16)
            if ic_ghim is not None:
                b_ghim.setIcon(ic_ghim)
            else:
                b_ghim.setText('Bỏ ghim' if da_ghim else 'Ghim')
            b_ghim.setToolTip('Bỏ ghim — xuống theo thứ tự gần đây' if da_ghim else 'Ghim dự án quan trọng lên đầu')
            b_ghim.setAutoRaise(True)
            b_ghim.clicked.connect(lambda _=False, p=str(f), g=not da_ghim: self._chay_lenh(
                lambda: (ghim_du_an(p, g), self._nap_gan_day())))
            self.ds_gan_day.setCellWidget(r, 4, b_ghim)
            mo = QPushButton('Mở')
            mo.setCursor(Qt.CursorShape.PointingHandCursor)
            mo.setObjectName('nut_mo_gan')
            dat_kieu_theo_tong(mo, QSS_NUT_MO_GAN)
            mo.clicked.connect(lambda _=False, p=str(f): self._chay_lenh(lambda: self.mo(p)))
            hop_mo = QWidget()
            hm = QHBoxLayout(hop_mo)
            hm.setContentsMargins(4, 2, 4, 2)
            hm.addStretch(1)
            hm.addWidget(mo)
            hm.addStretch(1)
            self.ds_gan_day.setCellWidget(r, 5, hop_mo)
            n += 1
            if n >= GAN_DAY_TOI_DA:                       # trước 26/10/2026: tối đa 8 dòng
                break
        dang_mo = self.con is not None and self.file is not None
        self.lenh['Đóng dự án'].setEnabled(dang_mo)
        if hasattr(self, 'nut_chao'):
            goi_y = ('Mở file dự án khác (đóng dự án hiện tại, không thoát phần mềm) - Ctrl+O' if dang_mo
                     else 'Mở file dự án có sẵn (.larc, .pabt) - Ctrl+O')
            self.nut_chao['Mở dự án…'].setToolTip(goi_y)
            self.the_chao['Mở dự án…'].setToolTip(goi_y)
        self._hien_trong_gan_day()
        self._cap_nhat_nut_gan_day()
        if hasattr(self, 'o_tim_gan') and self.o_tim_gan.text().strip():
            self._loc_gan_day(self.o_tim_gan.text())
        if self.trang.currentIndex() == TRANG_CHAO:
            self._nap_tong_quan()

    def _loc_gan_day(self, chu: str = ''):
        from .lap_pa import bo_dau
        k = bo_dau((chu or '').strip())
        for r in range(self.ds_gan_day.rowCount()):
            it = self.ds_gan_day.item(r, 0)
            tim = (it.data(Qt.ItemDataRole.UserRole + 1) or it.text()) if it else ''
            self.ds_gan_day.setRowHidden(r, bool(k) and k not in bo_dau(tim))

    def _mo_gan_day_dong(self, r: int):
        it = self.ds_gan_day.item(r, 0) if r >= 0 else None
        p = it.data(Qt.ItemDataRole.UserRole) if it is not None else None
        if p:
            self._chay_lenh(lambda: self.mo(p))

    def _file_gan_day_chon(self):
        if not hasattr(self, 'ds_gan_day'):
            return None
        r = self.ds_gan_day.currentRow()
        it = self.ds_gan_day.item(r, 0) if r >= 0 else None
        return it.data(Qt.ItemDataRole.UserRole) if it is not None else None

    def _cap_nhat_nut_gan_day(self):
        p = self._file_gan_day_chon()
        dang_mo = self.con is not None and self.file is not None
        if hasattr(self, 'b_mo_gan'):
            self.b_mo_gan.setEnabled(bool(p))
            self.b_bo_gan.setEnabled(bool(p))
            self.b_xoa_gan.setEnabled(bool(p))
        self.lenh['Xóa dự án…'].setEnabled(dang_mo or bool(p))

    def _mo_gan_day_chon(self):
        p = self._file_gan_day_chon()
        if p:
            self.mo(p)

    def xoa_du_an(self, p=None, xoa_file: bool = True, xac_nhan=None, tu_danh_sach: bool = False):
        """Xóa dự án khỏi danh sách gần đây; xoa_file=True thì xóa cả file .pabt (đóng nếu đang mở). Không xóa thư mục bản in."""
        if p is None:
            p = self._file_gan_day_chon() if tu_danh_sach else (str(self.file) if self.file else self._file_gan_day_chon())
        if not p:
            QMessageBox.information(self, TEN_UD, 'Hãy chọn một dự án trong danh sách gần đây, hoặc mở dự án rồi bấm Xóa dự án.')
            return None
        p = Path(p)
        dang_mo = self.file is not None and p.resolve() == self.file.resolve()
        if xoa_file:
            chu = (f'XÓA HẲN file dự án?\n\n{p}\n\nKhông đưa vào Thùng rác. Thư mục bản in / hồ sơ đợt (nếu có) giữ nguyên. '
                   + ('Dự án đang mở sẽ được đóng trước.' if dang_mo else ''))
        else:
            chu = f'Bỏ "{p.name}" khỏi danh sách gần đây? File dự án vẫn còn trên đĩa.'
        if xac_nhan is None:
            xac_nhan = QMessageBox.question(self, TEN_UD, chu) == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        if dang_mo:
            self.dong_du_an_lenh()
        bo_gan_day(p)
        if xoa_file:
            khoa_p = p.with_name(p.name + '.khoa')
            try:
                if khoa_p.exists():
                    khoa_p.unlink()
                if p.exists():
                    p.unlink()
            except OSError as e:
                QMessageBox.warning(self, TEN_UD, chu_loi('Không xóa được file dự án', e))
                self._nap_gan_day()
                return None
        self._nap_gan_day()
        self.statusBar().showMessage(('Đã xóa file dự án: ' if xoa_file else 'Đã bỏ khỏi danh sách: ') + p.name, 8000)
        return str(p)

    def _hien_trang_chao(self):
        """Chưa mở / vừa đóng dự án: màn hình chào thay danh sách trống (trang Dự toán dùng được khi chưa mở dự án: giữ)."""
        self._cap_nhat_chon()
        from .giao_dien import dat_to_chuc
        dat_to_chuc(self.bang_tieu_de)
        if hasattr(self, 'lb_don_vi'):
            from . import to_chuc
            self.lb_don_vi.setText(to_chuc.TEN)
        if self.trang.currentIndex() != 3:
            self.trang.setCurrentIndex(TRANG_CHAO)
            self.lb_trang.setVisible(False)
            self._danh_dau_trang_chu()
            self._dam_bao_tab(-1)
        self._nap_gan_day()
        self._cap_nhat_hien_hang_the()

    def ve_trang_chu(self):
        """Nút "Màn hình chính" (menu trái): về màn hình bắt đầu như lúc mở phần mềm - Dự án mới, Mở dự án,
        Nhập Excel, dự án gần đây. Dự án đang mở vẫn mở: bấm một trang ở menu trái để quay lại."""
        self._danh_dau_trang_chu()                       # 1.0.44: dấu chọn menu ngay, trước khi nạp / đổi trang
        self._tai_lai_neu_doi()                         # 1.0.09: tổng quan dự án tính cả hộ vừa thêm ở cửa sổ hộ
        with dung_ve(self):
            self.trang.setCurrentIndex(TRANG_CHAO)
            if hasattr(self, 'ngan_lv'):
                self.ngan_lv.setCurrentWidget(self.trang)
            self.lb_trang.setVisible(False)
            self._nap_gan_day()
            self._dam_bao_tab(-1)
            self._cap_nhat_hien_hang_the()

    def _danh_dau_trang_chu(self):
        self._dong_bo_menu_trai('Màn hình chính')

    def _lenh_dang_xem(self) -> str | None:
        """Khóa self.lenh của mục menu trái ứng với màn hình đang hiện (trang chính / trang nhúng / thẻ So sánh)."""
        if not hasattr(self, 'ngan_lv'):
            return None
        if hasattr(self, 'khung_tab') and self.ngan_lv.currentWidget() is self.khung_tab.stack_phu:
            w = self.khung_tab.stack_phu.currentWidget()
            khoa = next((k for k, x in self.khung_tab.widget.items() if x is w), None)
            if isinstance(khoa, tuple) and khoa and khoa[0] == 'ho':
                return 'Lập phương án hộ…'
            return {'du_thao': 'Dự thảo PABT…', 'don_gia': 'Bộ đơn giá…'}.get(khoa)
        i = self.trang.currentIndex()
        if i == TRANG_CHAO:
            return 'Màn hình chính'
        if i == STACK_DU_TOAN:
            k = self.khung_du_toan
            return 'So sánh với thực tế' if k is not None and k.tab.currentIndex() == 1 else TRANG[TRANG_DU_TOAN]
        return TRANG[self._i_trang] if 0 <= self._i_trang < len(TRANG) else None

    def _dong_bo_menu_trai(self, khoa_active: str | None = None) -> None:
        """1.0.03: CHỈ mục menu trái của màn hình đang hiện được đánh dấu (trang chính, Màn hình chính, Lập phương án chi tiết, Niêm
        yết, Đơn giá bồi thường, So sánh với thực tế). khoa_active None: suy từ màn hình đang hiện. Lệnh bấm mà không mở được gì
        (QAction checkable tự đảo dấu) cũng được đặt lại vì _chay_lenh gọi hàm này sau mỗi lệnh."""
        if khoa_active is None:
            khoa_active = self._lenh_dang_xem()
        for t in (*TRANG, 'Màn hình chính', *LENH_DANH_DAU_PHU):
            a = self.lenh.get(t)
            if a is not None and a.isCheckable() and a.isChecked() != (t == khoa_active):
                a.setChecked(t == khoa_active)

    def luu_du_an_lenh(self):
        """Tệp tin → Lưu dự án (Ctrl+S). Mọi thao tác đã ghi ngay vào file dự án (SQLite, từng giao dịch); lệnh này ép ghi hẳn xuống
        đĩa (đồng bộ Google Drive / ổ mạng) và báo giờ lưu - người dùng quen Ctrl+S không phải đoán đã lưu chưa.
        Đang xem trang Khái toán & dự toán (0.9.71): Ctrl+S lưu file khái toán .pabtdt (nút "LƯU DỰ TOÁN (Ctrl+S)").
        Không gắn phím tắt riêng trên trang: hai phím tắt cùng Ctrl+S thì Qt không chạy cái nào."""
        if self.khung_du_toan is not None and self.trang.currentIndex() == 3 and self.khung_du_toan.isVisible():
            return self.khung_du_toan.luu() is not None
        if self.con is None or self.file is None:
            self.statusBar().showMessage('Chưa mở dự án.', 4000)
            return False
        if self.chi_doc:
            self.statusBar().showMessage('Dự án đang mở chỉ xem: không ghi.', 4000)
            return False
        hop = self._hop_tab_dang_soan()
        if hop is not None and not hop.luu():
            return False
        import os
        from datetime import datetime
        try:
            if self.con.in_transaction:
                self.con.commit()
            with open(self.file, 'rb+') as f:
                os.fsync(f.fileno())
        except OSError as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không ghi được file dự án xuống đĩa', e))
            return False
        self.statusBar().showMessage(f'Đã lưu {self.file.name} lúc {datetime.now():%H:%M:%S} '
                                     '(mọi thay đổi được ghi ngay sau mỗi thao tác).', 6000)
        from .giao_dien import thong_bao_noi
        thong_bao_noi(self, f'Đã lưu dữ liệu an toàn lúc {datetime.now():%H:%M:%S}', 'dat')     # 1.0.07: thông báo nổi
        self._tu_dong_bo_sau_luu()
        return True

    def _tu_dong_bo_sau_luu(self) -> dict | None:
        """30/10/2026 (phương án đột phá 5): bản offline theo hộ + cài đặt "Tự đồng bộ khi bấm Lưu" (Dự án trên máy chủ, mặc định tắt)
        -> đồng bộ các hộ lên máy chủ, vẫn giữ hộ (may_chu.dong_bo_ho ở luồng nền). Xung đột / mất mạng: chỉ báo, KHÔNG ghi đè."""
        if self.nhan_viec is None:
            return None
        from . import may_chu
        if may_chu.PHIEN is None or not may_chu.tu_dong_bo_khi_luu():
            return None
        from .giao_dien import chay_nen, thong_bao_noi
        f = self.file
        try:
            kq = chay_nen(self, lambda: may_chu.dong_bo_ho(f), 'Đang đồng bộ các hộ lên máy chủ…')
        except may_chu.LoiXungDot as e:
            thong_bao_noi(self, f'Chưa đồng bộ: {len(e.ds)} hộ đã bị sửa trên máy chủ - mở Tệp tin > Dự án trên máy chủ để xử lý',
                          'canh_bao', 8000)
            return None
        except (may_chu.LoiMayChu, OSError) as e:
            thong_bao_noi(self, f'Chưa đồng bộ lên máy chủ: {e}', 'canh_bao', 8000)
            return None
        thong_bao_noi(self, f'Đã đồng bộ {kq["so_ho"]} hộ lên máy chủ (vẫn giữ hộ)', 'dat')
        return kq

    def _phong_to(self, buoc: int):
        from .giao_dien import phong_to
        phong_to(buoc)

    def _thanh_menu(self):
        """Thanh menu chuẩn (0.9.23 - lộ trình người dùng): thao tác file / dữ liệu / công cụ / trợ giúp, phím tắt."""
        L = self.lenh
        self.menu_tren = {}
        from .thanh_tieu_de import dung_thanh_hop_nhat
        from PySide6.QtWidgets import QMenuBar
        # thanh hợp nhất: QMenuBar riêng nằm trong thanh tiêu đề (setMenuWidget) - menuBar() trả thanh này; dùng menuBar() của
        # QMainWindow thì setMenuWidget sẽ xóa nó (deleteLater)
        self._mb_rieng = QMenuBar(self) if dung_thanh_hop_nhat() else None
        for ten, ds in (('&Tệp tin', ['Dự án mới…', 'Mở dự án…', 'Dự án trên máy chủ…', None, 'Lưu dự án', 'Lưu dự án thành…',
                                      'Cỗ máy thời gian (mốc khôi phục)…', 'Đóng dự án', 'Xóa dự án…', None, 'Thoát']),
                        ('Chỉnh &sửa', [self.nut_ht['lui'], self.nut_ht['toi'], None, 'Tìm nhanh…']),
                        # 0.9.66 (người dùng 12/10/2026 - mỗi lệnh một chỗ): lệnh đã có ở menu trái không lặp ở đây - Báo cáo
                        # tổng hợp, Xuất báo cáo đối chiếu, Bộ đơn giá, Thông tin dự án (KIEM_TRA test_khong_trung_menu_trai)
                        ('&Dữ liệu', ['Nhập file Excel…', 'Nhập phương án chi tiết…', 'Quét file thông minh…', 'Nhập bản vẽ CAD (.dxf)…', 'Bản đồ thửa đất',
                                      None, 'Trạng thái hộ…',
                                      'Xuất danh sách hộ…', LENH_THONG_KE, None, 'Nhật ký kiểm toán…']),
                        ('&Công cụ', ['Quản lý Mẫu in & Bản in…', 'Rà soát giá…', 'Cập nhật bảng giá đất…', None,
                                      'Phiếu kiểm đếm thực địa…', 'Trợ lý (giải thích, soạn nháp)…', None,
                                      'Xuất gói mẫu in & cấu hình…', 'Nhập gói mẫu in & cấu hình…',
                                      'Tạo gói cấu hình cho nhiều đơn vị…']),
                        ('C&ài đặt', ['Cấu hình nghiệp vụ…', 'Giao diện…', None, 'Kết nối máy chủ LAN…', None, 'Phóng to chữ', 'Thu nhỏ chữ',
                                      'Cỡ chữ 100%']),
                        ('Trợ &giúp', ['Hướng dẫn sử dụng', 'Cập nhật phần mềm…', None, 'Chẩn đoán & sửa lỗi hệ thống…',
                                       None, 'Giới thiệu'])):
            # QMenu có cha + giữ tham chiếu: PySide2 (bản Win7) xóa menu do menuBar().addMenu("chữ") trả về khi biến Python
            # hết phạm vi (thanh menu còn tiêu đề nhưng mất danh sách lệnh)
            m = QMenu(ten, self)
            self.menuBar().addMenu(m)
            self.menu_tren[ten.replace('&', '')] = m
            m.setToolTipsVisible(True)
            for t in ds:
                if t is None:
                    m.addSeparator()
                else:
                    m.addAction(t if isinstance(t, QAction) else L[t])
        from .giao_dien import kieu_menu_bar, tao_banner_ten, tao_dai_nhan_dien, _BamMenu
        if self._mb_rieng is not None:
            # thanh tiêu đề hợp nhất kiểu VS Code (12/10/2026): biểu tượng + menu + Hoàn tác / Làm lại | tiêu đề | nút cửa sổ
            from .thanh_tieu_de import ThanhTieuDe
            self.thanh_td = ThanhTieuDe(self, self._mb_rieng)
            self._mb_rieng._bam_menu = _BamMenu(self._mb_rieng)
            self.setMenuWidget(self.thanh_td)
            self.dai_nhan_dien = self.thanh_td.logo
            self.thanh_td.gan_khung()                   # trước khi hiện cửa sổ; lỗi -> khung Windows như 0.9.64
        else:
            self.thanh_td = None
            kieu_menu_bar(self.menuBar())
            self.dai_nhan_dien = tao_dai_nhan_dien()
            self.menuBar().setCornerWidget(self.dai_nhan_dien, Qt.Corner.TopLeftCorner)
        self.banner_ten = tao_banner_ten()
        self.lb_don_vi = self.banner_ten.lb_don_vi
        self.lb_ban_quyen_nho = self.banner_ten.lb_ban_quyen

    def menuBar(self):
        """Thanh menu: QMenuBar nằm trong thanh tiêu đề hợp nhất, hoặc thanh menu của QMainWindow (khung Windows / bản Qt 5)."""
        mb = getattr(self, '_mb_rieng', None)
        return mb if mb is not None else super().menuBar()

    def _xoa_ket_qua(self):
        """Băng kết quả trống (chưa mở / đã đóng dự án): bỏ cả nền màu, không để lại ô màu rỗng cạnh nút."""
        self.lb_ket_qua.setText('')
        self.lb_ket_qua.setStyleSheet('QLabel { font-weight: bold; padding: 5px 8px; }')

    def _chay_lenh(self, ham):
        """Chạy một lệnh (menu trái, thanh nút, chuột phải) rồi giải phóng các hộp thoại đã đóng."""
        try:
            ham()
        finally:
            self.don_hop_da_dong()
            try:
                self._dong_bo_menu_trai()
            except RuntimeError:                         # cửa sổ đang đóng
                pass

    def don_hop_da_dong(self) -> int:
        """Hộp thoại tạo với cha là cửa sổ chính / trang bên phải không tự xóa khi đóng: mở cửa sổ lập phương án 20 lần để lại
        20 cửa sổ ẩn (~5.800 thành phần, giữ kết nối dự án cũ) - dùng cả ngày phần mềm nặng dần. Gọi khi lệnh đã chạy xong
        (không còn mã nào dùng các hộp đó); còn hộp đang mở (lệnh gọi từ bên trong hộp khác) thì để lần sau."""
        if QApplication.activeModalWidget() is not None:
            return 0
        an = [h for h in self.findChildren(QDialog) if not h.isVisible() and not h.property('nhung_tab')]
        for h in an:
            h.deleteLater()
        return len(an)

    def _menu_ho(self, view, pos):
        idx = view.indexAt(pos)
        if self.con is None or not idx.isValid():
            return
        sm = view.selectionModel()
        if view.currentIndex().row() != idx.row() and not (sm is not None and sm.isSelected(idx)):
            view.setCurrentIndex(idx)                   # chuột phải ngoài vùng đang chọn: thao tác trên dòng đó (trong vùng: giữ vùng)
        m = QMenu(self)
        # lệnh của menu trái dùng lại đúng QAction (cùng tên, cùng trạng thái bật / tắt khi chỉ xem); chỉ "Xem chi tiết tính
        # tiền…" là riêng của chuột phải
        m.addAction(self.lenh['Lập phương án hộ…'])
        m.addAction('Xem chi tiết tính tiền…', lambda: self._chay_lenh(self.xem_chi_tiet_tinh))
        m.addSeparator()
        for ten in ('Trạng thái hộ…', 'Chọn hộ niêm yết…', 'Xem hộ trên bản đồ…', 'Đợt trình…', 'In / Xuất…', 'Nhật ký kiểm toán…',
                    None, 'Xóa hộ…'):
            if ten is None:
                m.addSeparator()
            else:
                m.addAction(self.lenh[ten])
        from .giao_dien import them_muc_sao_chep
        them_muc_sao_chep(m, view, pos)                # 1.0.04: sao chép ô / dòng đứng đầu menu
        m.exec(view.viewport().mapToGlobal(pos))
        m.deleteLater()

    def nhap_ban_ve_cad(self, file=None, cho: bool = True):
        """Nhập ranh thửa từ bản vẽ địa chính .dxf vào bản đồ dự án (tùy chọn cập nhật DT thu hồi). True nếu đã lưu."""
        if self.con is None or self.chi_doc:
            QMessageBox.information(self, TEN_UD, 'Mở dự án (không ở chế độ chỉ xem) trước khi nhập bản vẽ.')
            return False
        from .man_hinh_ban_do import HopNhapCad
        d = HopNhapCad(self.con, self, file)
        if not cho:
            return d
        ok = d.exec() == QDialog.DialogCode.Accepted
        if ok:
            self.tai_lai()
        return ok

    def ban_do_thua(self, cho: bool = True):
        """Bản đồ thửa đất (cửa sổ riêng, không chặn): màu theo đồng thuận, bấm thửa mở hồ sơ / phương án của hộ. Chưa mở dự án
        (31/10/2026): vẫn mở để xem KML / KMZ trên nền vệ tinh như LARC Mobile."""
        from .man_hinh_ban_do import HopBanDo
        co = self.con is not None
        d = HopBanDo(self.con, self, mo_ho=(lambda ma: self.mo_lap_pa(ma)) if co else None,
                     nhap=None if (self.chi_doc or not co) else (lambda: self.nhap_ban_ve_cad()), chi_doc=self.chi_doc)
        d.setWindowModality(Qt.WindowModality.NonModal)
        if cho:
            d.show()
        return d

    def xem_ho_tren_ban_do(self, ma_ho=None, cho: bool = True):
        """Mở bản đồ, viền nổi + phóng tới các thửa thu hồi của hộ đang chọn (tìm theo số tờ / thửa - máy không có GPS)."""
        if self.con is None:
            return None
        ma = ma_ho if ma_ho is not None else self.ho_dang_chon()
        if ma is None:
            QMessageBox.information(self, TEN_UD, 'Chọn một hộ trong danh sách trước.')
            return None
        d = self.ban_do_thua(cho)
        if cho:
            # khung bản đồ có cỡ thật rồi mới phóng tới thửa. Bộ hẹn giờ là CON của cửa sổ bản đồ: cửa sổ bị đóng / hủy trước 150 ms
            # thì hẹn giờ hủy theo (QTimer.singleShot không gắn cửa sổ từng chạm vào hình thửa đã xóa -> sập, kiểm tra giao diện 31/10)
            t = QTimer(d)
            t.setSingleShot(True)
            t.timeout.connect(lambda: d.xem_ho(ma))
            t.start(150)
        else:
            d.xem_ho(ma)
        return d

    def giao_dien_tuy_chinh(self, cho: bool = True):
        """Cài đặt > Giao diện: mật độ bảng (áp ngay), tương phản cao (áp khi mở lại)."""
        from .man_hinh_giao_dien import HopGiaoDien
        d = HopGiaoDien(self)
        if cho:
            d.exec()
        return d

    def cau_hinh_nghiep_vu(self, cho: bool = True):
        """Cấu hình nghiệp vụ (hồ sơ địa phương): mốc thời hạn 16 bước, kinh phí, ngưỡng kiểm tra, bản in, cơ quan (0.9.87)."""
        from .man_hinh_cau_hinh import HopCauHinhNghiepVu
        d = HopCauHinhNghiepVu(self)
        if cho and d.exec() == QDialog.DialogCode.Accepted:
            self._lam_moi_don_vi()                      # băng tiêu đề, kinh phí, mốc thời hạn theo cấu hình mới
        return d

    def _lam_moi_don_vi(self) -> None:
        """Sau khi đổi hồ sơ địa phương / cấu hình: băng tiêu đề lấy tên đơn vị mới (dự án đang mở: tải lại; chưa mở: màn hình chào)."""
        from . import to_chuc
        if hasattr(self, 'banner_ten'):
            self.banner_ten.lb_ten.setText(to_chuc.TEN_PHAN_MEM)
        if self.con is not None:
            self.tai_lai()
        else:
            self._hien_trang_chao()

    def chan_doan_he_thong(self, cho: bool = True):
        """Chẩn đoán máy, kiểm tra / sửa file dự án (đóng rồi mở lại dự án đang mở), xuất gói chẩn đoán ẩn danh (0.9.87)."""
        from .man_hinh_chan_doan import HopChanDoanHeThong

        def dong():
            if self.dong_du_an() is False:
                return False
            self.file = None
            self.dat_tieu_de()
            return True
        d = HopChanDoanHeThong(self, self.file, dong_du_an=dong, mo_lai=lambda f: self.mo(Path(f)), im_lang=not cho)
        if cho:
            d.exec()
        return d

    def phieu_kiem_dem(self, cho: bool = True):
        """Phiếu kiểm đếm thực địa: xuất dữ liệu .json cho LARC Mobile, nhập kết quả vào phương án hộ,
        gắn ảnh hiện trạng theo mã hộ / CCCD / họ tên (0.9.87)."""
        if not self._can_du_an():
            return None
        from .man_hinh_kiem_dem import HopKiemDem
        d = HopKiemDem(self, self.con, self.file, self.dm, chi_doc=self.chi_doc, im_lang=not cho)
        if cho:
            d.exec()
            if d.da_ghi:
                self.tai_lai()
        return d

    def thong_ke_dia_chinh(self, cho: bool = True):
        """Hộp Thống kê Hộ · Thửa · Diện tích (21/10/2026): theo 7 trạng thái thực hiện và theo đợt trình - số liệu của danh sách hộ
        đang nạp (cùng cờ với thẻ KPI / bộ lọc). cho=False: chỉ tạo hộp (kiểm thử)."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Mở dự án trước để xem thống kê.')
            return None
        from .man_hinh_thong_ke import HopThongKeDiaChinh
        from .quan_ly import ds_dot
        da = self.con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
        try:
            lap = lap_pa.phan_loai_lap(self.con)        # "đã lập" như thẻ KPI (tự lập chưa soát = chưa lập)
        except Exception:                               # noqa: BLE001 - file chỉ xem phiên bản cũ: đã lập = tổng > 0
            lap = None
        d = HopThongKeDiaChinh(self.mo_hinh.dong, {x.id: x.ten for x in ds_dot(self.con)}, (da['ten'] or '') if da else '', self,
                               im_lang=not cho, lap=lap)
        if cho:
            d.exec()
        return d

    def nhat_ky_kiem_toan(self, ma_ho=None, cho: bool = True):
        """Nhật ký kiểm toán của dự án (lọc sẵn hộ đang chọn nếu có). Xem được cả khi dự án mở chỉ xem."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Mở dự án trước để xem nhật ký kiểm toán.')
            return None
        from .man_hinh_kiem_toan import HopKiemToan
        da = self.con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
        d = HopKiemToan(self.con, self, self.ho_dang_chon() if ma_ho is None else ma_ho, da['ten'] if da else '',
                        self.file.parent if self.file else None)
        if cho:
            d.exec()
        return d

    def xem_chi_tiet_tinh(self, ma_ho=None, cho: bool = True):
        ma_ho = self.ho_dang_chon() if ma_ho is None else ma_ho
        if self.con is None or ma_ho is None:
            return None
        d = ChiTietHo(self.con, ma_ho, self)
        if cho:
            d.exec()
        return d

    # ------------------------------------------------ hoàn tác / làm lại
    def hoan_tac(self, lam_lai: bool = False) -> str:
        """Hoàn tác (lam_lai=False) / làm lại thao tác gần nhất đã ghi vào file dự án. Trả tên thao tác ('' nếu không có)."""
        if self.ht is None:
            return ''
        try:
            viec = self.ht.lam_lai() if lam_lai else self.ht.hoan_tac()
        except Exception as e:                          # file bị khóa / lỗi SQLite: không làm hỏng dữ liệu (đã rollback)
            QMessageBox.warning(self, TEN_UD, chu_loi(f'Không {"làm lại" if lam_lai else "hoàn tác"} được', e))
            return ''
        from .giao_dien import thong_bao_noi
        if not viec:
            self.statusBar().showMessage('Không còn thao tác để ' + ('làm lại.' if lam_lai else 'hoàn tác.'), 4000)
            thong_bao_noi(self, 'Không còn thao tác để ' + ('làm lại' if lam_lai else 'hoàn tác'), 'canh_bao')
            return ''
        self.dm = lap_pa.DanhMuc(self.con) if 'đơn giá' in viec.lower() or 'danh mục' in viec.lower() else self.dm
        self.tai_lai()
        self.statusBar().showMessage(f'{"Đã làm lại" if lam_lai else "Đã hoàn tác"}: {viec}', 8000)
        thong_bao_noi(self, f'{"Đã làm lại" if lam_lai else "Đã hoàn tác"}: {viec}')          # 1.0.07: thông báo nổi
        return viec

    def hoan_tac_phim(self, lam_lai: bool) -> bool:
        if self.ht is None:
            return False
        self.hoan_tac(lam_lai)
        return True

    def _cap_nhat_nut_ht(self):
        ht = self.ht
        for k, co, ten, phim in (('lui', ht is not None and ht.co_hoan_tac, ht.ten_hoan_tac() if ht else '', 'Ctrl+Z'),
                                 ('toi', ht is not None and ht.co_lam_lai, ht.ten_lam_lai() if ht else '', 'Ctrl+Y')):
            a = self.nut_ht[k]
            viec = 'Làm lại' if k == 'toi' else 'Hoàn tác'
            gon = ten if len(ten) <= 40 else ten[:39] + '…'
            a.setEnabled(bool(co))
            a.setText(f'{viec}: {gon}\t{phim}'.replace('&', '&&') if co else f'{viec}\t{phim}')    # như "Undo Typing" của Office
            a.setToolTip(f'{viec}: {ten}  ({phim})' if co else 'Chưa có thao tác để ' + viec.lower())

    def mo_trang(self, i: int):
        """Trang bên phải (chỉ số TRANG): 0 danh sách hộ, 1 bảng tổng hợp kinh phí (3 thẻ), 2 quyết định phê duyệt, 3 theo dõi chi
        trả & bàn giao (gộp báo cáo tiến độ GPMB từ 1.0.00), 4 dự toán & khái toán. Chưa mở dự án: trang 0-3 hiện màn hình chào (trang Dự toán dùng
        được cả khi chưa mở dự án)."""
        self._danh_dau_trang(i)                         # 1.0.44: dấu chọn menu trái ngay — phản hồi < 1 khung hình
        if i != TRANG_DU_TOAN:
            self._tai_lai_neu_doi()                     # 1.0.09: hộ vừa thêm / lưu ở cửa sổ hộ (chưa đóng) hiện ngay
        with dung_ve(self):                             # một khung hình: không nhấp nháy giữa ẩn hàng thẻ / đổi stack / nạp
            if i == TRANG_DU_TOAN:
                self._dam_bao_du_toan()
                self.khung_du_toan.tab.setCurrentIndex(0)   # menu trái "Lập khái toán & Dự toán" (So sánh: so_sanh_du_toan chọn thẻ 1)
                chuyen_trang_muot(self.trang, STACK_DU_TOAN)
            elif self.con is None:
                chuyen_trang_muot(self.trang, TRANG_CHAO)
            else:
                k = self._dam_bao_trang(STACK_CUA_TRANG[i])         # trang nặng: tạo khi mở lần đầu
                chuyen_trang_muot(self.trang, STACK_CUA_TRANG[i])
                if STACK_CUA_TRANG[i] == STACK_TONG_HOP:
                    k.mo_the(k.tab.currentIndex())          # nạp thẻ đang xem (giữ thẻ người dùng chọn lần trước)
                elif k is not None and getattr(k, '_can_nap', False):
                    k.nap()
            self._dam_bao_tab(-1 if self.trang.currentIndex() == TRANG_CHAO else i)
            self._cap_nhat_hien_hang_the()

    def _danh_dau_trang(self, i: int):
        """Tiêu đề trang bên phải và dấu chọn ở menu trái theo trang i (gọi cả khi bấm thẳng thẻ của Bảng tổng hợp)."""
        self._i_trang = i
        self.lb_trang.setText(chu_hien(NHAN_MENU.get(TRANG[i], TRANG[i])))
        # không hiện tiêu đề trang ở trang nào: trùng mục menu trái đang chọn và tiêu đề khung của trang (người dùng 15-16/10/2026:
        # Dự toán, Quyết định phê duyệt "bị trùng tiêu đề mục"). lb_trang vẫn giữ chữ (test, tên trang hiện tại)
        self.lb_trang.setVisible(False)
        self._dong_bo_menu_trai(TRANG[i] if 0 <= i < len(TRANG) else None)

    def _ten_tab(self, khoa) -> str:
        if isinstance(khoa, int):
            # QTabBar cũng coi "&" là phím tắt: "&&" để hiện "&" (trước: "Dự toán  khái toán" - mất "&", thừa dấu cách)
            return 'Màn hình chính' if khoa < 0 else NHAN_MENU.get(TRANG[khoa], TRANG[khoa]).replace('&', '&&')
        if khoa in TEN_TAB:
            return TEN_TAB[khoa]
        if isinstance(khoa, tuple) and khoa and khoa[0] == 'ho':
            return f'Hộ: {khoa[1]}'
        return str(khoa)

    def _dam_bao_tab(self, khoa, ten: str | None = None, widget=None, dong_duoc: bool | None = None):
        """Mở hoặc chuyển tab (khoa số = trang chính; ('ho', ma) / 'don_gia' = widget phụ giữ RAM)."""
        if not hasattr(self, 'khung_tab'):
            return
        with dung_ve(self):
            self.khung_tab.dam_bao(khoa, ten or self._ten_tab(khoa), widget, dong_duoc)
            if widget is not None or not isinstance(khoa, int):
                self.ngan_lv.setCurrentWidget(self.khung_tab.stack_phu)
                self.lb_trang.setVisible(False)
            elif isinstance(khoa, int):
                self.ngan_lv.setCurrentWidget(self.trang)
            self._cap_nhat_hien_hang_the()
            self._dong_bo_menu_trai()

    def _cap_nhat_hien_hang_the(self):
        """0.9.95 (đặc tả "Ultra-Compact"): hàng thẻ số liệu CHỈ ở trang Danh sách hộ khi đã mở dự án - ẩn ở mọi trang khác (hộ đang
        soạn, Niêm yết, Đơn giá, Dự toán, Bảng tổng hợp, Quyết định, Tiến độ, Báo cáo). Banner xanh (tên phần mềm, đơn vị, phiên bản)
        CHỈ ở màn hình chào - màn hình làm việc nhường chiều cao cho bảng (tên dự án đã ở tiêu đề giữa thanh menu). Nối với tín hiệu
        đổi trang của `trang` / `ngan_lv` nên đúng dù trang đổi theo đường nào."""
        if not hasattr(self, 'ngan_lv') or not hasattr(self, 'hang_the'):
            return
        self._xoa_bo_dem_neu_an()
        self._tu_thu_gon_menu()
        o_trang = self.ngan_lv.currentWidget() is self.trang
        chao = o_trang and self.trang.currentIndex() == TRANG_CHAO
        self.hang_the.setVisible(self.con is not None and o_trang and self.trang.currentIndex() == STACK_CUA_TRANG[TRANG_DS])
        if hasattr(self, 'banner_ten'):
            self.banner_ten.setVisible(self.con is None or chao)

    RONG_CUA_SO_HEP = 1280                              # điểm logic: cửa sổ hẹp hơn thì menu trái tự thu gọn khi soạn phương án hộ

    def _tu_thu_gon_menu(self) -> None:
        """1.0.16 (màn hình 1366 @125% = 1093 điểm: menu mở chiếm ~255, cửa sổ lập phương án cần ~840): mở cửa sổ lập phương án mà
        cửa sổ hẹp -> thu gọn menu trái (chỉ biểu tượng); rời trang đó thì mở lại. Người dùng tự bấm Thu gọn / Mở rộng thì app không can
        thiệp nữa (tới lần mở lập phương án kế tiếp)."""
        khung = getattr(self, 'khung_menu', None)
        if khung is None or not hasattr(khung, 'dat_thu_gon') or not hasattr(self, 'khung_tab'):
            return
        w = self.khung_tab.stack_phu.currentWidget() if self.ngan_lv.currentWidget() is self.khung_tab.stack_phu else None
        la_lap_pa = w is not None and type(w).__name__ == 'CuaSoLapPA'
        if la_lap_pa and self.width() < self.RONG_CUA_SO_HEP and not khung.thu_gon:
            self._menu_tu_thu_gon = True
            khung.dat_thu_gon(True)
        elif not la_lap_pa and getattr(self, '_menu_tu_thu_gon', False):
            self._menu_tu_thu_gon = False
            if khung.thu_gon:
                khung.dat_thu_gon(False)

    def cap_nhat_bo_dem(self, bang, tk: dict) -> None:
        """Vùng chọn của một bảng trong cửa sổ chính đổi (giao_dien._BoChonVung): bộ đếm thanh trạng thái theo bảng đó. Bảng đang ẩn
        (trang khác nạp lại / chọn sẵn dòng) không ghi đè bộ đếm của bảng người dùng đang xem."""
        if not hasattr(self, 'lb_bo_dem_excel'):
            return
        try:
            hien = bang.isVisibleTo(self)
        except RuntimeError:
            return
        if not hien and bang is not self._bang_bo_dem:
            return
        self._bang_bo_dem = bang
        self.lb_bo_dem_excel.dat(tk if hien else None)

    def _xoa_bo_dem_neu_an(self) -> None:
        """Đổi trang / tab: bảng của bộ đếm không còn hiện thì xóa bộ đếm."""
        b = getattr(self, '_bang_bo_dem', None)
        if b is None or not hasattr(self, 'lb_bo_dem_excel'):
            return
        try:
            an = not b.isVisibleTo(self)
        except RuntimeError:
            an = True
        if an:
            self._bang_bo_dem = None
            self.lb_bo_dem_excel.dat(None)

    def _tab_doi(self, i: int):
        if i < 0 or i >= len(self._tab_khoa):
            return
        self._tab_doi_khoa(self._tab_khoa[i])

    def _tab_doi_khoa(self, k):
        if isinstance(k, int):
            if k < 0:
                self._danh_dau_trang_chu()
                with dung_ve(self):
                    self.ngan_lv.setCurrentWidget(self.trang)
                    self.trang.setCurrentIndex(TRANG_CHAO)
                    self.lb_trang.setVisible(False)
                    self._cap_nhat_hien_hang_the()
                return
            self.mo_trang(k)
            return
        with dung_ve(self):
            self.ngan_lv.setCurrentWidget(self.khung_tab.stack_phu)
            w = self.khung_tab.widget.get(k)
            if w is not None:
                self.khung_tab.stack_phu.setCurrentWidget(w)
            self.lb_trang.setVisible(False)
            self._cap_nhat_hien_hang_the()
            self._dong_bo_menu_trai()

    def _tab_dong(self, i: int):
        if i < 0 or i >= len(self._tab_khoa):
            return
        k = self._tab_khoa[i]
        if isinstance(k, int) and k < 0:
            return
        w = self.khung_tab.widget.get(k)
        if w is not None and hasattr(w, 'hoi_luu') and not w.hoi_luu():
            return
        da_ap = bool(getattr(w, 'da_ap', False))
        da_ghi = bool(getattr(w, 'da_luu', False) or getattr(w, 'thay_doi_csdl', False))
        self.khung_tab.bo(i)
        if da_ap and self.con is not None:
            self.dm = lap_pa.DanhMuc(self.con)
            self.tai_lai()
        elif da_ghi and self.con is not None:
            self.tai_lai()
        if self.thanh_tab.count() == 0:
            self._dam_bao_tab(-1)
        elif self.thanh_tab.currentIndex() >= 0:
            self._tab_doi(self.thanh_tab.currentIndex())

    def _tab_ke(self, buoc: int):
        if hasattr(self, 'khung_tab'):
            self.khung_tab.ke(buoc)
            n, i = self.thanh_tab.count(), self.thanh_tab.currentIndex()
            ten = self.thanh_tab.tabText(i).replace('&&', '&').strip() if 0 <= i < n else ''
            if n > 1 and ten:                       # thanh tab ẩn (15/10/2026): báo nổi màn hình vừa chuyển tới
                from .giao_dien import thong_bao_noi
                thong_bao_noi(self, f'{ten}  ·  màn hình {i + 1}/{n} (Ctrl+Tab / Ctrl+Shift+Tab để chuyển)')

    def _nhung_hop(self, hop):
        """Đưa hộp thoại thành trang tab: giữ nguyên widget / dữ liệu đang nhập, không exec().
        Tắt phím Ctrl+S riêng của hộp (trùng QAction cửa sổ chính -> Qt hỏi phím nào). Ctrl+S đi qua luu_du_an_lenh."""
        if hop.isWindow():                              # hộp tạo sẵn kiểu nhúng (CuaSoLapPA(nhung=True)): khỏi đặt lại cờ
            hop.setWindowFlags(Qt.WindowType.Widget)
        hop.setProperty('nhung_tab', True)
        from PySide6.QtGui import QKeySequence
        for sc in getattr(hop, '_phim', []):
            if sc.key() == QKeySequence(QKeySequence.StandardKey.Save):
                sc.setEnabled(False)

    def _hop_tab_dang_soan(self):
        """Tab hộ đang mở (có hàm luu). Ctrl+S ghi phương án hộ trước khi ép file xuống đĩa."""
        if not hasattr(self, 'khung_tab'):
            return None
        i = self.thanh_tab.currentIndex()
        if i < 0 or i >= len(self.khung_tab.khoa):
            return None
        w = self.khung_tab.widget.get(self.khung_tab.khoa[i])
        if w is not None and w.property('nhung_tab') and hasattr(w, 'luu') and hasattr(w, 'bo'):
            return w
        return None

    def _dong_tab_phu(self, hoi: bool = True) -> bool:
        """Đóng tab hộ / bộ đơn giá. False nếu người dùng hủy lưu."""
        if not hasattr(self, 'khung_tab'):
            return True
        phu = [k for k in list(self.khung_tab.khoa) if not isinstance(k, int)]
        if hoi:
            for khoa in phu:
                w = self.khung_tab.widget.get(khoa)
                if w is not None and hasattr(w, 'hoi_luu') and not w.hoi_luu():
                    return False
        for khoa in list(phu):
            if khoa in self.khung_tab.khoa:
                self.khung_tab.bo(self.khung_tab.khoa.index(khoa))
        if hasattr(self, 'ngan_lv'):
            self.ngan_lv.setCurrentWidget(self.trang)
        return True

    def _bo_trang_an(self) -> int:
        """1.0.08 (A+ / A−): Qt áp lại bảng kiểu cho MỌI widget còn sống kể cả trang đang ẩn (~1,2 ms / widget: 1.300 widget ~1,7 s).
        Trước khi đổi cỡ chữ bỏ các trang đang ẩn có thể dựng lại: Bảng tổng hợp / Tiến độ / Quyết định (khung_trang - tạo lại ở
        _dam_bao_trang khi mở tới) và tab phụ đang ẩn KHÔNG có thay đổi chưa lưu (hộ, Niêm yết, Đơn giá - lệnh mở tạo lại). Giữ: trang
        đang xem, Danh sách hộ, Khái toán (số liệu đang soạn), tab hộ còn sửa dở. Trả số trang đã bỏ."""
        n = 0
        dang = self.trang.currentIndex()
        for i in [i for i in list(self.khung_trang) if i != dang or self.ngan_lv.currentWidget() is not self.trang]:
            k = self.khung_trang.pop(i)
            k.setParent(None)
            k.deleteLater()
            n += 1
        if hasattr(self, 'khung_tab'):
            hien = self.khung_tab.stack_phu.currentWidget() if self.ngan_lv.currentWidget() is self.khung_tab.stack_phu else None
            for khoa in [k for k in list(self.khung_tab.khoa) if not isinstance(k, int)]:
                w = self.khung_tab.widget.get(khoa)
                if w is None or w is hien:
                    continue
                if isinstance(khoa, tuple) and khoa[0] == 'ho' and (w.bo.co_thay_doi or w.ho_so.co_thay_doi()):
                    continue
                self.khung_tab.bo(self.khung_tab.khoa.index(khoa))
                n += 1
        return n

    # ---- trang bên phải tạo khi mở lần đầu
    def _dam_bao_trang(self, i: int):
        """Khung của trang ở ô i trong self.trang (STACK_TONG_HOP / THEO_DOI / QUYET_DINH / BAO_CAO): tạo, nối tín hiệu, gắn dự án
        đang mở ở lần hỏi đầu. Ô khác (danh sách hộ, dự toán, màn hình chào): None."""
        k = self.khung_trang.get(i)
        if k is not None or i not in self._cho_trang:
            return k
        from .man_hinh_theo_doi import KhungBangTongHop, KhungQuyetDinh, KhungTienDo
        if i == STACK_TONG_HOP:
            k = KhungBangTongHop(None, self)
            k.di_den_phe_duyet.connect(lambda: self.mo_trang(TRANG_QUYET_DINH))
            k.doi_soat.nguon_dang_mo = self._khai_toan_dang_mo
        elif i == STACK_THEO_DOI:
            k = KhungTienDo(None, self)
        else:
            k = KhungQuyetDinh(None, self)                  # Nhóm 6: màn hình DUY NHẤT quản lý quyết định phê duyệt
        k.da_doi.connect(lambda: self.tai_lai(giu_trang=True))
        k.mo_ho.connect(lambda m: self.trang_thai_ho([m]))
        self._cho_trang[i].layout().addWidget(k)
        self.khung_trang[i] = k
        if self.isVisible():                            # cửa sổ đã hiện (kiểu đã áp lúc hiện): áp cho khung mới tạo
            from .giao_dien import ap_kieu_cay
            ap_kieu_cay(k)
        if self.con is not None:
            k.dat_du_an(self.con, self.chi_doc)
        return k

    @property
    def bang_tong_hop(self):
        return self._dam_bao_trang(STACK_TONG_HOP)

    @property
    def tien_do(self):
        return self._dam_bao_trang(STACK_THEO_DOI)

    @property
    def quyet_dinh(self):
        return self._dam_bao_trang(STACK_QUYET_DINH)

    def _dam_bao_du_toan(self):
        if self.khung_du_toan is None:
            from .man_hinh_du_toan import KhungDuToan
            self.khung_du_toan = KhungDuToan(self.trang_dt, self.con, self.file if self.con is not None else None)
            self.trang_dt.layout().addWidget(self.khung_du_toan)
            self.khung_du_toan.tab.currentChanged.connect(lambda _i: self._dong_bo_menu_trai())   # nút chế độ Khái toán / So sánh
            if self.isVisible():                        # tạo sau khi cửa sổ đã hiện: áp kiểu như lúc hiện
                from .giao_dien import ap_kieu_cay
                ap_kieu_cay(self.khung_du_toan)

    def ho_dang_chon(self):
        k = self._khung_dang_xem()
        if k is not None and hasattr(k, 'ma_da_chon'):              # trang Tổng quát / Quyết định / Tiến độ: hộ chọn ở đó
            ds = k.ma_da_chon()
            return ds[0] if ds else None
        idx = self.bang.currentIndex()
        if not idx.isValid():
            return None
        return self.mo_hinh.dong[self.loc.mapToSource(idx).row()]['ma_ho']

    def mo_lap_pa(self, ma_ho=None, cho: bool = True, the: int | None = None, truoc: int | None = None):
        """Mở cửa sổ hồ sơ và phương án hộ (cho=False: chỉ tạo cửa sổ, dùng khi kiểm thử; the: thẻ mở đầu, 0 = thông tin hộ)."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        if ma_ho is None:
            ma_ho = self.ho_dang_chon()
        if self.chi_doc:                                # chỉ xem (máy khác đang sửa): xem chi tiết, không mở cửa sổ sửa
            return self.xem_chi_tiet_tinh(ma_ho, cho) if ma_ho is not None else None
        if ma_ho is None:
            r = self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho LIMIT 1').fetchone()
            if r is None:
                QMessageBox.information(self, TEN_UD, 'Dự án chưa có hộ nào.')
                return None
            ma_ho = r[0]
        if cho and self.nhan_viec is not None and int(ma_ho) not in self.nhan_viec:
            # bản offline theo hộ: vẫn mở để xem, Lưu bị chặn (lap_pa.kiem_ho_nhan_viec) - báo trước để khỏi sửa mất công
            QMessageBox.warning(self, TEN_UD, lap_pa.TB_HO_KHONG_NHAN)
        from .man_hinh import CuaSoLapPA
        khoa = ('ho', int(ma_ho))
        if cho and hasattr(self, 'khung_tab'):
            # không còn thanh tab (15/10/2026): hộ khác đang mở mà không có thay đổi chưa lưu thì đóng, khỏi chất cửa sổ ẩn trong
            # RAM; hộ còn thay đổi chưa lưu giữ lại (mở lại hộ đó là thấy; đóng dự án / thoát vẫn hỏi lưu)
            for k in [k for k in self.khung_tab.khoa if isinstance(k, tuple) and k[0] == 'ho' and k != khoa]:
                ww = self.khung_tab.widget.get(k)
                if ww is not None and not (ww.bo.co_thay_doi or ww.ho_so.co_thay_doi()):
                    self.khung_tab.bo(self.khung_tab.khoa.index(k))
        if cho and hasattr(self, 'khung_tab') and khoa in self.khung_tab.khoa:
            w = self.khung_tab.widget.get(khoa)
            if the is not None and w is not None:
                w.tab.setCurrentIndex(the)
            self._dam_bao_tab(khoa)
            if w is not None:
                w.dat_tieu_diem_dau()
            return w
        w = CuaSoLapPA(self.con, ma_ho, self, self.dm, nhung=cho)
        if the is not None:
            w.tab.setCurrentIndex(the)
        if not cho:
            return w
        self._nhung_hop(w)
        ten_ho = (getattr(getattr(w.bo, 'pa', None), 'ho', None) and w.bo.pa.ho.ho_ten) or f'Hộ {ma_ho}'
        self._dam_bao_tab(khoa, f'Hộ: {ten_ho}', widget=w, dong_duoc=True)
        w.dat_tieu_diem_dau()
        cu_chuyen = w.chuyen_ho

        def _chuyen(ma):
            kq = cu_chuyen(ma)
            if kq and hasattr(self, 'khung_tab'):
                ten = (getattr(getattr(w.bo, 'pa', None), 'ho', None) and w.bo.pa.ho.ho_ten) or f'Hộ {ma}'
                moi = ('ho', int(w.bo.ma_ho))
                cu = next((k for k, ww in self.khung_tab.widget.items() if ww is w), None)
                if moi in self.khung_tab.khoa and self.khung_tab.widget.get(moi) is not w:
                    self.khung_tab.chon(moi)
                elif cu is not None:
                    self.khung_tab.doi_khoa(cu, moi, f'Hộ: {ten}')
            return kq
        w.chuyen_ho = _chuyen
        w.finished.connect(lambda *_: self._khi_hop_nhung_xong(w))
        return w

    def _khi_hop_nhung_xong(self, w):
        """Đóng tab khi hộp nhúng tự đóng (nút Đóng / accept) — không hỏi lưu lần hai nếu đã sạch."""
        if not hasattr(self, 'khung_tab'):
            return
        for i, k in enumerate(list(self.khung_tab.khoa)):
            if self.khung_tab.widget.get(k) is w:
                self._tab_dong(i)
                return

    XOA_HIEN_TOI_DA = 12           # hộp hỏi xóa: liệt kê tối đa bấy nhiêu hộ (danh sách dài không đẩy nút ra ngoài màn hình)

    def xoa_ho(self, ds_ma_ho=None, xac_nhan=None):
        """Xóa các hộ đang chọn trong danh sách (giữ Ctrl / Shift để chọn nhiều hộ; phím Delete) cùng thửa, phương án, quyết
        định / chi trả của hộ. Hoàn tác được (nút Hoàn tác / Ctrl+Z). xac_nhan: bỏ qua câu hỏi (kiểm thử)."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        if self.chi_doc:
            return None
        from . import ho_so
        ds = ho_so.thong_tin_xoa(self.con, self.ho_da_chon() if ds_ma_ho is None else ds_ma_ho)
        if not ds:
            if xac_nhan is None:
                QMessageBox.information(self, TEN_UD, 'Chọn hộ cần xóa trong danh sách (giữ Ctrl hoặc Shift để chọn nhiều hộ) rồi '
                                                      'bấm "Xóa hộ…" hoặc phím Delete.')
            return None
        if xac_nhan is None:
            n = self.XOA_HIEN_TOI_DA
            dong = [f'  {x["thu_tu"]}. {x["ho_ten"]} - {x["so_thua"]} thửa, {x["so_dong_pa"]} dòng phương án'
                    + (f', {x["so_qd"]} quyết định' if x['so_qd'] else '') + (', ĐÃ NHẬN TIỀN' if x['da_nhan_tien'] else '')
                    for x in ds[:n]]
            if len(ds) > n:
                dong.append(f'  … và {len(ds) - n} hộ khác')
            qd = sum(1 for x in ds if x['so_qd'])
            chu = (f'XÓA {len(ds)} hộ khỏi dự án?\n\n' + '\n'.join(dong) +
                   '\n\nXóa cả thửa đất, phương án' + (', quyết định phê duyệt / chi trả của hộ' if qd else '') + ' của các hộ này.'
                   + (f'\nCHÚ Ý: {qd} hộ đã có quyết định phê duyệt.' if qd else '') +
                   '\n\nXóa nhầm: Chỉnh sửa > Hoàn tác (Ctrl+Z) (Ctrl+Z) để lấy lại.')
            hop = QMessageBox(QMessageBox.Icon.Warning, TEN_UD, chu,
                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
            hop.button(QMessageBox.StandardButton.Yes).setText(f'Xóa {len(ds)} hộ')
            hop.button(QMessageBox.StandardButton.No).setText('Không xóa')
            hop.setDefaultButton(QMessageBox.StandardButton.No)
            xac_nhan = hop.exec() == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        try:
            tb = ho_so.xoa_nhieu_ho(self.con, [x['ma_ho'] for x in ds])
        except (lap_pa.LoiNhap, sqlite3.Error) as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không xóa được', e))
            return None
        self.tai_lai()
        self.statusBar().showMessage(tb + '  Xóa nhầm: bấm Hoàn tác (Ctrl+Z).', 20000)
        return tb

    def mo_ho_so(self, ma_ho=None, moi: bool = False, cho: bool = True, ho_ten: str | None = None):
        """Hồ sơ hộ nằm chung cửa sổ với phương án (thẻ "Thông tin hộ, thửa đất"). moi: thêm hộ mới (hỏi họ tên) rồi mở."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        if moi and self.chi_doc:
            QMessageBox.information(self, TEN_UD, 'Dự án đang mở ở chế độ CHỈ XEM (máy khác đang sửa file): không thêm hộ được.\n\n'
                                                  'Đóng dự án ở máy kia rồi mở lại để sửa.')
            return None
        if moi:
            if ho_ten is None:
                from PySide6.QtWidgets import QInputDialog
                ho_ten, ok = QInputDialog.getText(self, 'Thêm hộ', 'Họ và tên chủ hộ (CCCD, địa chỉ, thửa đất nhập tiếp ở cửa sổ hồ sơ):')
                if not ok or not ho_ten.strip():
                    return None
            from . import ho_so
            truoc = self.con.total_changes                  # tải lại MỘT lần khi đóng cửa sổ hộ (tính cả hộ vừa thêm)
            try:
                ma_ho = ho_so.luu_ho(self.con, None, dict(ho_ten=ho_ten), [])
            except lap_pa.LoiNhap as e:
                QMessageBox.warning(self, TEN_UD, str(e))
                return None
            if not cho:
                self.tai_lai()
            return self.mo_lap_pa(ma_ho, cho=cho, the=0, truoc=truoc)
        elif ma_ho is None:
            ma_ho = self.ho_dang_chon()
            if ma_ho is None:
                QMessageBox.information(self, TEN_UD, 'Chọn một hộ trong danh sách (hoặc bấm "Thêm hộ…").')
                return None
        return self.mo_lap_pa(ma_ho, cho=cho, the=0)

    def sua_du_an(self, cho: bool = True):
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        from .man_hinh import HopDuAn
        dlg = HopDuAn(self.con, self)
        if cho and dlg.exec():
            self.tai_lai()
        return dlg

    def in_xuat(self, cho: bool = True, ma_ho: list | None = None, che_do: str | None = None, dot_id: int | None = None):
        """Trung tâm Xuất bản (Xuất hồ sơ & Bản in) - nơi DUY NHẤT in / xuất file. ma_ho: hộ truyền sẵn (mặc định hộ đang chọn trên danh
        sách); che_do: 'du_thao' (niêm yết, họp dân) / 'chinh_thuc' (trình thẩm định, gửi hộ) - None: như trước, không đặt sẵn; dot_id:
        đợt trình chọn sẵn."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        from .man_hinh import HopIn
        chon = sorted(ma_ho) if ma_ho is not None else self._ho_chon_ds()
        dlg = HopIn(self.con, self, ma_ho_chon=chon, file_du_an=self.file, che_do=che_do, dot_id=dot_id)
        if cho:
            dlg.exec()
        return dlg

    def quan_ly_mau_in(self, cho: bool = True):
        """1.0.07: hộp Quản lý Mẫu in & Bản in - 3 mẫu (chi tiết chính thức / dự thảo / tổng hợp): trạng thái nhúng / tùy chỉnh,
        thay bằng file Excel khác (áp chuẩn khổ giấy), xuất mẫu ra Excel, khôi phục mẫu chuẩn."""
        from .man_hinh_quan_ly_mau import HopQuanLyMauIn
        hop = HopQuanLyMauIn(self)
        if cho:
            hop.exec()
        return hop

    def tiep_nhan_phap_ly(self, cho: bool = True):
        """1.0.04: hộp Tiếp nhận & Kiểm tra pháp lý hồ sơ đầu vào. Không cần dự án (máy trắng: hồ sơ trống, lưu file .pabtpl);
        có dự án mở thì nạp / lưu thêm vào dự án. Nút "Khởi tạo Dự án Mới" mở hộp Dự án mới điền sẵn từ hồ sơ."""
        from . import tiep_nhan_phap_ly as tn
        from .man_hinh_tiep_nhan import HopTiepNhanPhapLy
        dlg = HopTiepNhanPhapLy(self.con if not self.chi_doc else None, self.file, self,
                                khoi_tao=lambda d: self.du_an_moi(dien_san=tn.du_lieu_du_an_moi(d)))
        if not cho:
            return dlg
        dlg.exec()
        return dlg

    def du_an_moi(self, cho: bool = True, dien_san: dict | None = None):
        """Dự án mới từ dữ liệu thô: 4 bước, tự lập phương án, xuất 2 bảng in; xong thì mở dự án. dien_san: thông tin bước 1
        điền sẵn (từ hồ sơ Tiếp nhận pháp lý - 1.0.04)."""
        from .man_hinh_du_an_moi import HopDuAnMoi
        dlg = HopDuAnMoi(self)
        if dien_san:
            dlg.dien_san(dien_san)
        if not cho:
            return dlg
        if dlg.exec() and dlg.ket_qua:
            self.mo_ket_qua_du_an_moi(dlg.ket_qua)
        return dlg

    def mo_ket_qua_du_an_moi(self, kq: dict):
        self.mo(kq['file'])
        tb = (f'Đã tạo dự án: {kq["so_ho"]} hộ, {kq["so_thua"]} thửa; {kq["so_ho_co_pa"]} hộ đã có phương án, '
              f'tổng {vn(kq["tong"])} đồng.')
        if kq.get('in'):
            x = kq['in']
            tb += f'\n\nĐã xuất {len(x.get("word", []))} file Word, {len(x["excel"])} file Excel' + \
                (f', {len(x["pdf"])} file PDF' if x['pdf'] else '') + f' vào:\n{kq["thu_muc_in"]}'
        from .giao_dien import hop_ket_qua                  # ô cuộn: đủ mọi điểm cần xem lại, nút Đóng luôn trong màn hình
        hop_ket_qua(self, tb, kq['canh_bao'], tieu_de=TEN_UD)

    def bo_don_gia(self, cho: bool = True):
        from .man_hinh_don_gia import HopBoDonGia
        if cho and hasattr(self, 'khung_tab') and 'don_gia' in self.khung_tab.khoa:
            self._dam_bao_tab('don_gia')
            return self.khung_tab.widget.get('don_gia')
        dlg = HopBoDonGia(self, self.con, self.chi_doc)
        if not cho:
            return dlg
        self._nhung_hop(dlg)
        self._dam_bao_tab('don_gia', TEN_TAB['don_gia'], widget=dlg, dong_duoc=True)
        dlg.finished.connect(lambda *_: self._khi_hop_nhung_xong(dlg))
        return dlg

    def don_gia_rieng(self, cho: bool = True, the: int = 0):
        """Quy ước giá tương đương nhập tay và đơn giá thẩm định giá (tài sản đặc biệt) của dự án đang mở."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        from .man_hinh_don_gia_rieng import HopDonGiaRieng
        dlg = HopDonGiaRieng(self.con, self, self.dm, self.chi_doc, the)
        if not cho:
            return dlg
        dlg.exec()
        if dlg.da_luu:
            self.dm = lap_pa.DanhMuc(self.con)      # danh sách chọn nhanh dựng lại theo quy ước mới
        return dlg

    def nap_danh_muc(self, file_excel=None, xac_nhan=None):
        """Thay danh mục đơn giá, tham số, biểu thưởng của dự án đang mở bằng danh mục trong một file PABT Excel."""
        if self.con is None or self.chi_doc:
            QMessageBox.information(self, TEN_UD, 'Hãy mở một dự án (để sửa) trước.')
            return None
        if file_excel is None:
            file_excel, _ = QFileDialog.getOpenFileName(self, 'Chọn file PABT Excel có danh mục đơn giá', '',
                                                        'File PABT Excel (*.xlsm *.xlsx)')
            if not file_excel:
                return None
        if xac_nhan is None:
            xac_nhan = QMessageBox.question(self, TEN_UD, 'Thay toàn bộ danh mục đơn giá, hỗ trợ, tham số, biểu thưởng, giá đất '
                                                          'của dự án bằng danh mục trong file đã chọn?\n\n'
                                                          'Hồ sơ hộ, thửa và phương án đã lập giữ nguyên.') \
                == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        from . import nhap_tho
        try:
            with con_tro_cho():
                dem = nhap_tho.nap_danh_muc(self.file, file_excel)
        except Exception as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không nạp được danh mục', e))
            return None
        self.dm = lap_pa.DanhMuc(self.con)
        self.tai_lai()
        self.statusBar().showMessage(f'Đã nạp danh mục: {dem["dm_taisan"]} tài sản, cây trồng; {dem["dm_hotro"]} khoản hỗ trợ; '
                                     f'{dem["tham_so"]} tham số; {dem["gia_dat"]} dòng giá đất.', 15000)
        return dem

    def ra_soat_gia(self, cho: bool = True):
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        from .man_hinh import HopRaSoat
        dlg = HopRaSoat(lap_pa.ra_soat_gia(self.con, self.dm), self)
        if cho and dlg.exec() and dlg.ma_ho_chon is not None:
            self.mo_lap_pa(dlg.ma_ho_chon)
        return dlg

    def xuat_bao_cao(self):
        if self.kq is None or self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return
        mac_dinh = str(self.file.with_name(self.file.stem + '_DoiChieu.xlsx'))
        p, _ = QFileDialog.getSaveFileName(self, 'Lưu báo cáo đối chiếu', mac_dinh, 'File Excel (*.xlsx)')
        if not p:
            return
        da = self.con.execute('SELECT ten, nguon_nhap FROM du_an WHERE id = 1').fetchone()
        from . import doi_chieu
        try:
            with con_tro_cho():
                rs = lap_pa.ra_soat_gia(self.con, self.dm)
                from .giao_dien import chay_nen             # chỉ ghi Excel (số liệu đã có): chạy nền
                chay_nen(self, lambda: doi_chieu.xuat_bao_cao(self.kq, p, da['ten'], da['nguon_nhap'], rs),
                         'Đang ghi báo cáo đối chiếu…')
        except OSError as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không ghi được file', e))
            return
        QMessageBox.information(self, TEN_UD, f'Đã lưu báo cáo:\n{p}')

    # ------------------------------------------------ quản lý hồ sơ trình, tiến độ
    def _can_du_an(self, sua: bool = False) -> bool:
        if self.con is None or (sua and self.chi_doc):
            QMessageBox.information(self, TEN_UD, 'Hãy mở một dự án (để sửa) trước.' if sua else 'Hãy nhập hoặc mở một dự án trước.')
            return False
        return True

    def _tong_pa(self) -> dict:
        return {h['ma_ho']: h['tong'] for h in (self.kq.ho if self.kq else [])}

    def luu_du_an_thanh(self, dich=None, mo_ban_moi: bool | None = None):
        """Lưu (chép) file dự án đang mở sang đường dẫn khác, ví dụ vào thư mục hồ sơ dự án; rồi làm việc trên bản mới."""
        if not self._can_du_an():
            return None
        from . import quan_ly
        if dich is None:
            goc = quan_ly.thu_muc_ho_so(self.con, self.file)
            mac_dinh = str((goc if goc.exists() else self.file.parent) / self.file.name)
            dich, _ = QFileDialog.getSaveFileName(self, 'Lưu dự án thành', mac_dinh, csdl.LOC_LUU)
            if not dich:
                return None
        dich = Path(dich)
        if dich.resolve() == self.file.resolve():
            QMessageBox.information(self, TEN_UD, 'Đây là file đang mở: không cần lưu thành.')
            return None
        k = khoa.KhoaFile(dich).nguoi_khac()
        if k:
            QMessageBox.warning(self, TEN_UD, f'File đích đang được sửa trên {khoa.mo_ta(k)}.')
            return None
        try:
            p = quan_ly.luu_thanh(self.con, dich)
        except Exception as e:                         # thư mục không ghi được, file đích đang mở, SQLite...
            QMessageBox.warning(self, TEN_UD, chu_loi('Không lưu được', e))
            return None
        if mo_ban_moi is None:
            mo_ban_moi = QMessageBox.question(self, TEN_UD, f'Đã lưu dự án thành:\n{p}\n\nLàm việc tiếp trên file mới này?') \
                == QMessageBox.StandardButton.Yes
        if mo_ban_moi:
            self.mo(p, chi_doc=False)
        return p

    def dot_trinh(self, cho: bool = True):
        if not self._can_du_an():
            return None
        from .man_hinh_quan_ly import HopDotTrinh
        dlg = HopDotTrinh(self.con, self, self.ho_da_chon(), self.file, self.chi_doc)
        if not cho:
            return dlg
        dlg.exec()
        if dlg.thay_doi:
            self.tai_lai()
        if getattr(dlg, 'mo_xuat_dot', None) is not None:      # nút "Xuất bản hồ sơ đợt này": trình hướng dẫn xuất bản 4 bước
            self.xuat_ban_dot(dot_id=dlg.mo_xuat_dot, che_do='chinh_thuc')
        return dlg

    def xuat_ban_dot(self, dot_id: int | None = None, che_do: str = 'chinh_thuc', cho: bool = True):
        """Xuất bản hồ sơ MỘT CHẠM theo đợt trình (man_hinh_xuat_ban.HopXuatBanDot: chọn đợt -> kiểm tra -> xem trước -> xuất bản);
        khâu xuất dùng chung HopIn.thuc_hien. Không phải lệnh menu riêng (mỗi lệnh một chỗ): mở từ Đợt trình thẩm định."""
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        from .man_hinh_xuat_ban import HopXuatBanDot
        dlg = HopXuatBanDot(self.con, self, self.file, dot_id, che_do)
        if cho:
            dlg.exec()
        return dlg

    def trang_thai_ho(self, ds_ma_ho: list | None = None, cho: bool = True):
        if not self._can_du_an(sua=True):
            return None
        ds = ds_ma_ho if ds_ma_ho is not None else self.ho_da_chon()
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Chọn một hoặc nhiều hộ trong danh sách (giữ Ctrl / Shift để chọn nhiều).')
            return None
        if len(ds) == 1:                        # một hộ: các quyết định (phê duyệt bổ sung), chi trả từng quyết định, bàn giao
            from .man_hinh_theo_doi import HopHoTheoDoi
            dlg = HopHoTheoDoi(self.con, ds[0], self, self._tong_pa().get(ds[0]))
        else:
            from .man_hinh_quan_ly import HopTrangThai
            dlg = HopTrangThai(self.con, ds, self, self._tong_pa())
        if not cho:
            return dlg
        if dlg.exec():
            self.tai_lai(giu_trang=True)
        return dlg

    def bao_cao_tong_hop(self, file=None, ds=None, dieu_kien: str | None = None, ten_file: str = '', tieu_de: str = '',
                         hoi: bool = True):
        """Báo cáo tổng hợp (Excel) các hộ đang hiện theo bộ lọc (đợt, trạng thái, từ khóa) - hoặc các hộ ds (Xuất danh sách hộ)."""
        if not self._can_du_an():
            return None
        from . import quan_ly
        ds = self.ho_dang_loc() if ds is None else ds
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Không có hộ nào theo bộ lọc hiện tại.')
            return None
        if file is None:
            goc = quan_ly.thu_muc_ho_so(self.con, self.file)
            mac_dinh = str((goc if goc.exists() else self.file.parent) / (ten_file or f'BaoCaoTongHop_{self.file.stem}.xlsx'))
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu danh sách hộ' if ten_file else 'Lưu báo cáo tổng hợp', mac_dinh,
                                                  'File Excel (*.xlsx)')
            if not file:
                return None
        try:
            with con_tro_cho():
                # số liệu đọc ở đây (kết quả tính dùng chung), ghi Excel ở luồng nền: hàng nghìn hộ không "Không phản hồi"
                so_lieu = quan_ly.du_lieu_bao_cao(self.con, ds)
                dk = self.mo_ta_loc() if dieu_kien is None else dieu_kien
                from .giao_dien import chay_nen
                p = chay_nen(self, lambda: quan_ly.ghi_bao_cao_tong_hop(so_lieu, file, tieu_de, dk),
                             f'Đang ghi {len(ds)} hộ ra Excel…')
        except OSError as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không ghi được file', e))
            return None
        if hoi and QMessageBox.question(self, TEN_UD, f'Đã lưu {len(ds)} hộ:\n{p}\n\nMở file?') == QMessageBox.StandardButton.Yes:
            from .in_an import mo_file
            mo_file(p)
        return p

    def xuat_danh_sach(self, file=None, hoi: bool = True):
        """Nút "Xuất" (thanh công cụ danh sách hộ, người dùng 11/10/2026): Excel danh sách hộ để theo dõi, trình, lưu trữ - các hộ
        đang chọn (từ 2 hộ), không thì các hộ đang hiện theo Đợt / Trạng thái / Tìm. Cùng bảng với Báo cáo tổng hợp (đợt, tiền
        từng mục, phê duyệt / chi trả / bàn giao, ghi chú theo dõi); tên file theo đợt, trạng thái, giờ xuất."""
        if not self._can_du_an():
            return None
        import re
        from datetime import datetime
        loc = self.mo_ta_loc()
        chon = set(self.ho_da_chon()) if self._khung_dang_xem() is None else set()
        if len(chon) >= 2:
            ds = [m for m in self.ho_dang_loc() if m in chon]
            ds += sorted(chon - set(ds))
            dk = f'{len(ds)} hộ đang chọn' + (f' (trong danh sách lọc: {loc})' if loc else '')
        else:
            ds, dk = self.ho_dang_loc(), loc
        phan = [cb.currentText() for cb in (self.cb_dot, self.cb_tt) if cb.currentData()] + (['Chon'] if len(chon) >= 2 else [])
        ten = re.sub(r'[\\/:*?"<>|\s]+', '_', '_'.join(phan or ['TatCa'])).strip('_')[:80]
        return self.bao_cao_tong_hop(file, ds=ds, dieu_kien=dk, tieu_de='DANH SÁCH HỘ BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ',
                                     ten_file=f'DanhSachHo_{ten}_{datetime.now():%Y%m%d_%H%M}.xlsx', hoi=hoi)

    def kiem_tra_loi(self, cho: bool = True):
        if not self._can_du_an():
            return None
        from .man_hinh_quan_ly import HopKiemLoi
        da = self.con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
        dlg = HopKiemLoi(self.con, self, self.dm, self.chi_doc, da['ten'] if da else '')
        if not cho:
            return dlg
        dlg.exec()
        if dlg.da_sua:
            self.tai_lai()
        if dlg.ma_ho_chon is not None:
            if self.chi_doc:
                ChiTietHo(self.con, dlg.ma_ho_chon, self).exec()
            else:
                self.mo_lap_pa(dlg.ma_ho_chon)
        return dlg

    def du_toan(self, cho: bool = True):
        """Trang Dự toán & khái toán (0.9.23: trang trong cửa sổ chính, trước là hộp thoại riêng). Trả KhungDuToan."""
        self.mo_trang(TRANG_DU_TOAN)
        return self.khung_du_toan

    def chon_ho_niem_yet(self, cho: bool = True):
        """Chọn hộ đủ điều kiện niêm yết công khai, lấy ý kiến (0.9.69): các hộ đang chọn trên danh sách (từ 2 hộ), không thì
        cả dự án. Lưu -> ho.du_dieu_kien (+ đưa vào đợt niêm yết nếu chọn) -> nạp lại tab Niêm yết & Lấy ý kiến nếu đang mở."""
        if self.con is None:
            return None
        from .man_hinh_du_thao import HopChonNiemYet
        ds = self.ho_da_chon()
        d = HopChonNiemYet(self, self.con, ds if len(ds) >= 2 else None, self.chi_doc)
        if not cho:
            return d
        if d.exec() == QDialog.DialogCode.Accepted:
            w = self.khung_tab.widget.get('du_thao')
            if w is not None and getattr(w, 'con', None) is self.con:
                w.nap()
        return d

    def _khai_toan_dang_mo(self):
        """Bảng khái toán đang mở ở Nhóm 1 (thẻ Đối soát dự toán Pre-F/S dùng làm khái toán ban đầu); chưa mở / chưa có dòng: None."""
        k = self.khung_du_toan
        return k.dt if k is not None and k.dt.dong else None

    def so_sanh_du_toan(self):
        """Menu trái "So sánh với thực tế" (0.9.70): trang Khái toán, thẻ So sánh với thực tế áp giá."""
        k = self.du_toan(cho=False)
        if k is not None:
            with dung_ve(self):
                k.tab.setCurrentIndex(1)
        self._dong_bo_menu_trai()
        return k

    def mo_du_thao(self, cho: bool = True):
        """Mở tab Dự thảo PABT của dự án đang mở (niêm yết, ý kiến, đối thoại, hộ vướng)."""
        if self.con is None:
            if cho:
                QMessageBox.information(self, TEN_UD, 'Mở một dự án trước khi lập dự thảo.')
            return None
        if 'du_thao' in self.khung_tab.widget:
            w = self.khung_tab.widget['du_thao']
            if getattr(w, 'con', None) is not self.con:
                self._tab_dong(self.khung_tab.khoa.index('du_thao'))
            else:
                w.nap()
                self._dam_bao_tab('du_thao', TEN_TAB['du_thao'], w, True)
                return w
        from .man_hinh_du_thao import KhungDuThao
        w = KhungDuThao(self.con, self, chi_doc=self.chi_doc)
        self._dam_bao_tab('du_thao', TEN_TAB['du_thao'], w, True)
        return w

    def bang_gia_dat(self, cho: bool = True, the: int = 0):
        """Bảng giá đất: thẻ "Bảng giá đất 2026" (NQ 28/2025, tra theo địa bàn của dự án đang mở) và thẻ "Hệ số K" (QĐ 03/2026/QĐ-UBND,
        nhập từ file / chữ dán - he_so_k.py), thẻ "Cập nhật, bổ sung giá đất" (web / file, quy tắc vị trí 2-4). the: 0 / 1 / 2 = thẻ mở sẵn."""
        from .man_hinh_du_toan import HopTraNQ28
        xa = ''
        if self.con is not None:
            r = self.con.execute('SELECT ten_dia_ban FROM du_an WHERE id = 1').fetchone()
            xa = (r[0] or '') if r else ''
        d = HopTraNQ28(self, xa, xem=True, the=the)
        if cho:
            d.exec()
        return d

    def tinh_don_gia_dat(self, cho: bool = True, ds_ma_ho=None):
        """Bảng tính đơn giá đất bồi thường (NQ 28/2025 x QĐ 03/2026 - man_hinh_tinh_gia_dat.HopTinhGiaDat): tính + áp vào dòng đất của các hộ
        đang chọn trên danh sách (ds_ma_ho: kiểm thử). Chưa mở dự án: chỉ tính. cho=False: trả hộp (kiểm thử)."""
        from .man_hinh_tinh_gia_dat import HopTinhGiaDat
        xa, ds = '', []
        if self.con is not None:
            r = self.con.execute('SELECT ten_dia_ban FROM du_an WHERE id = 1').fetchone()
            xa = (r[0] or '') if r else ''
            ds = list(ds_ma_ho) if ds_ma_ho is not None else self.ho_da_chon()
        d = HopTinhGiaDat(self, self.con, ds, xa, bool(getattr(self, 'chi_doc', False)))
        if not cho:
            return d
        if d.exec() == QDialog.DialogCode.Accepted and d.ket_qua_ap:
            self.tai_lai()
        return d

    def quet_thong_minh(self, files=None, cho: bool = True, ngu_canh: str = 'AUTO_DETECT', doc=None):
        """Quét file thông minh (bộ quét DÙNG CHUNG quet_chung.py, chạy trên máy): xem kết quả rồi ghi văn bản căn cứ vào dự án hoặc mở
        Bảng tính đơn giá đất với thông số vừa đọc. files / doc: kiểm thử. cho=False: trả hộp kết quả."""
        from .man_hinh_quet_chung import HopKetQuaQuet, chon_va_quet
        kq = chon_va_quet(self, ngu_canh, files, doc)
        if kq is None:
            return None
        ds_ho = []
        ma_goi_y = None
        if self.con is not None:
            from . import quet_chung
            ds_ho = [(r[0], r[1]) for r in self.con.execute('SELECT ma_ho, ho_ten FROM ho ORDER BY thu_tu, ma_ho')]
            chon = self.ho_da_chon()
            ma_goi_y = quet_chung.tim_ho(self.con, kq) or (chon[0] if chon else None)
        while True:
            h = HopKetQuaQuet(self, kq, self.con is not None, bool(getattr(self, 'chi_doc', False)), ds_ho, ma_goi_y)
            if not cho:
                return h
            h.exec()
            if not h.hanh_dong:
                return h
            ma_goi_y = h.ho_chon() or ma_goi_y
            self.xu_ly_ket_qua_quet(h)
            from . import quet_chung as qc
            if h.hanh_dong == 'mo_file' and h.loai_chon == qc.D_DU_AN:   # có thể đã đổi dự án đang mở: danh sách hộ của hộp không còn đúng
                return h
            for f in kq.tung_file:                                       # file vừa mở màn hình xử lý: không nhắc lại
                if f['file'] == h.file_chon or (h.hanh_dong == 'dua_vao_ho' and f['loai'] == qc.D_HO_SO):
                    f['da_xu_ly'] = True
            if not any(not f.get('da_xu_ly') and f['loai'] in h.LOAI_CON_VIEC for f in kq.tung_file):
                return h

    def xu_ly_ket_qua_quet(self, h):
        """Việc người dùng chọn ở hộp kết quả quét: mở đúng màn hình chuyên trách của file đó / đưa vào hộ / ghi căn cứ / tính giá đất."""
        from . import van_ban_can_cu as vbcc
        kq = h.kq
        try:
            if h.hanh_dong == 'ghi_can_cu' and self.con is not None:
                vbcc.ghi_can_cu_du_an(self.con, vbcc.doc_can_cu_du_an(self.con) + '\n' + '\n'.join(kq.can_cu))
                self.thong_bao(f'Đã ghi {len(kq.can_cu)} văn bản căn cứ vào dự án (sắp theo 13 bậc hiệu lực).')
            elif h.hanh_dong == 'tinh_gia':
                t = self.tinh_don_gia_dat(cho=False)
                t.sau_khi_quet(kq)
                if t.exec() == QDialog.DialogCode.Accepted and t.ket_qua_ap:
                    self.tai_lai()
            elif h.hanh_dong == 'dua_vao_ho':
                self.dua_ket_qua_quet_vao_ho(kq, h.ho_chon())
            elif h.hanh_dong == 'mo_file':
                return self.mo_file_quet(h.file_chon, h.loai_chon, kq, h.ho_chon())
        except Exception as e:                                           # noqa: BLE001 - LoiNhap (quyền) / lỗi đọc: báo rõ, không sập
            QMessageBox.warning(self, TEN_UD, chu_loi('Chưa xử lý được', e))
        return None

    def mo_file_quet(self, file, loai: str, kq=None, ma_ho=None, cho: bool = True):
        """Bộ định tuyến: đưa file vào màn hình chuyên trách theo loại (quet_chung.DICH). Trả màn hình / kết quả của màn hình đó."""
        from . import quet_chung as qc
        file = str(file)
        if loai == qc.D_DU_AN:
            return self.nhap_excel(file)
        if loai == qc.D_CHI_TIET:
            return self.nhap_chi_tiet(file)
        if loai in (qc.D_HE_SO_K, qc.D_BANG_GIA):
            from .man_hinh_du_toan import HopTraNQ28
            d = self.bang_gia_dat(cho=False, the=1 if loai == qc.D_HE_SO_K else HopTraNQ28.THE_CAP_NHAT)
            if cho:
                (d.khung_k if loai == qc.D_HE_SO_K else d.khung_cn).chon_file(file)
                d.exec()
            return d
        if loai == qc.D_DON_GIA:
            d = self.bo_don_gia(cho=cho)
            if cho and d is not None:
                d.cap_nhat_file(file)
            return d
        if loai == qc.D_HO_SO:
            return self.dua_ket_qua_quet_vao_ho(kq, ma_ho, cho=cho)
        return None

    def dua_ket_qua_quet_vao_ho(self, kq, ma_ho, cho: bool = True):
        """Thửa, tài sản quét được -> cửa sổ phương án của hộ (CHƯA lưu: người dùng soát rồi bấm Lưu như mọi khi). Thửa khớp theo tờ + thửa; tài
        sản qua hộp "Dán danh sách tài sản" (tự xếp mục, khớp danh mục đơn giá). Trả (cửa sổ, hộp dán, (thêm, thiếu, trùng))."""
        from . import quet_chung as qc
        if self.con is None or kq is None or ma_ho is None:
            QMessageBox.information(self, TEN_UD, 'Chọn hộ cần đưa dữ liệu vào.')
            return None
        w = self.mo_lap_pa(ma_ho, cho=cho)
        if w is None or not hasattr(w, 'bo'):
            return None
        them, thieu, trung = qc.ghi_thua_vao_ho(w.bo, kq.dong_dat)
        if them:
            w.bang[1].ve()
            w.bang[1].nap_danh_sach()
            w.cap_nhat()
        bao = [f'Thêm {them} dòng đất (chưa lưu).'] if them else []
        if thieu:
            bao.append('Không có trong hồ sơ hộ: ' + ', '.join(thieu) + ' (thêm thửa ở thẻ Thông tin hộ, thửa đất).')
        if trung:
            bao.append('Đã có dòng: ' + ', '.join(trung) + '.')
        if bao:
            w.thong_bao(' '.join(bao))
        chu = kq.dong_dan or [f'{t.ten} {t.dvt} {t.so_luong}' for t in kq.dong_tai_san]
        hop = w.dan_tai_san('\n'.join(chu), cho=cho) if chu else None
        return w, hop, (them, thieu, trung)

    def cap_nhat_bang_gia_dat(self, cho: bool = True):
        """Cập nhật / bổ sung bảng giá đất (web, file Excel / Word / PDF): 30/10/2026 là thẻ "Cập nhật, bổ sung giá đất" của cửa sổ Bảng
        giá đất (không còn cửa sổ riêng). Trả cửa sổ Bảng giá đất (khung: d.khung_cn)."""
        from .man_hinh_du_toan import HopTraNQ28
        return self.bang_gia_dat(cho, the=HopTraNQ28.THE_CAP_NHAT)

    def lich_su_cap_nhat(self, cho: bool = True):
        """Chân trang: lịch sử cập nhật từ 0.9.53. Không mang các bản đã phát hành trước đó."""
        from PySide6.QtWidgets import QDialogButtonBox, QTextBrowser
        from .lich_su_cap_nhat import MUC
        d = QDialog(self)
        d.setWindowTitle(f'Lịch sử cập nhật phần mềm - {TEN_UD}')
        d.resize(640, 420)
        tb = QTextBrowser()
        tb.setOpenExternalLinks(False)
        if MUC:
            khoi = []
            for pb, ngay, dong in MUC:
                khoi.append(f'## Phiên bản {pb}  ·  {ngay}')
                khoi.extend(f'- {x}' for x in dong)
                khoi.append('')
            tb.setMarkdown('\n'.join(khoi))
        else:
            tb.setPlainText('Chưa có mục lịch sử.')
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        nut.rejected.connect(d.reject)
        lo = QVBoxLayout(d)
        lo.addWidget(tb)
        lo.addWidget(nut)
        from .giao_dien import vua_man_hinh
        vua_man_hinh(d)
        if cho:
            d.exec()
        return d

    def huong_dan(self, cho: bool = True):
        """Hướng dẫn sử dụng (HUONG_DAN.md đóng gói kèm) - F1."""
        from PySide6.QtWidgets import QDialogButtonBox, QTextBrowser
        d = QDialog(self)
        d.setWindowTitle(f'Hướng dẫn sử dụng - {TEN_UD}')
        d.resize(1000, 720)
        tb = QTextBrowser()
        tb.setOpenExternalLinks(True)
        f = file_huong_dan()
        if f is not None:
            tb.setMarkdown(f.read_text(encoding='utf-8'))
        else:
            tb.setPlainText('Không tìm thấy file hướng dẫn (HUONG_DAN.md) trong thư mục cài phần mềm.')
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        nut.rejected.connect(d.reject)
        lo = QVBoxLayout(d)
        lo.addWidget(tb)
        lo.addWidget(nut)
        from .giao_dien import vua_man_hinh
        vua_man_hinh(d)
        if cho:
            d.exec()
        return d

    def dong_du_an_lenh(self):
        """Lệnh Tệp tin → Đóng dự án: đóng file đang mở, về màn hình chào."""
        if self.dong_du_an() is False:
            return
        self.file = None
        self.dat_tieu_de()

    def quy_chuan(self, cho: bool = True):
        if not self._can_du_an():
            return None
        from .man_hinh_cay import HopQuyChuan
        dlg = HopQuyChuan(self.con, self, self.chi_doc)
        if cho:
            dlg.exec()
        return dlg

    def cap_nhat_phan_mem(self, file=None):
        from .man_hinh_cap_nhat import HopCapNhat
        h = HopCapNhat(self)
        if file:
            h.show()
            h.cai_file(file)
        h.exec()

    def gioi_thieu(self):
        # 26/10/2026 (người dùng): Giới thiệu KHÔNG ghi tên cơ quan / hồ sơ địa phương nào - chỉ tên phần mềm, phiên bản, gói, tác giả
        from . import to_chuc
        from .cap_nhat import ban_goc
        goc = ban_goc()
        pb = f'Phiên bản {__version__}' + (f' (bản cập nhật, bản cài gốc {goc})' if goc != __version__ else '') + \
            (f' - {NHAN_THU_NGHIEM}' if BAN_THU_NGHIEM else '') + '.'
        from .ban_quyen import mo_ta
        QMessageBox.about(self, TEN_UD, f'{TEN_UD}\n{pb}\n{mo_ta()}.\n{to_chuc.TAC_GIA}.')

    # ------------------------------------------------ gói mẫu in & cấu hình (.pabtcfg, 0.9.85)
    def xuat_goi_mau(self, file=None, cho: bool = True):
        """Đóng gói hồ sơ địa phương + mẫu in / mẫu văn bản trình đang dùng thành file .pabtcfg để gửi máy khác. Trả danh sách gói."""
        import re
        from datetime import datetime
        from . import dia_phuong, goi_mau
        from .lap_pa import bo_dau
        if file is None:
            ten = re.sub(r'[^\w\-]+', '_', bo_dau(dia_phuong.ten_ho_so()))[:40].strip('_') or 'LARC'
            mac = Path.home() / 'Documents' / f'PABT_MauIn_{ten}_{datetime.now():%Y%m%d}{goi_mau.DUOI}'
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu gói mẫu in & cấu hình', str(mac),
                                                  f'Gói mẫu in & cấu hình PABT (*{goi_mau.DUOI})')
            if not file:
                return None
        try:
            with con_tro_cho():
                ds = goi_mau.tao_goi(file, mo_ta=f'Xuất từ {__version__}')
        except goi_mau.LoiGoiMau as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        if cho:
            mau = [t['ten'][len('mau_in/'):] for t in ds['tep'] if t['ten'].startswith('mau_in/')]
            QMessageBox.information(self, TEN_UD, f'Đã đóng gói hồ sơ địa phương "{ds["ho_so"]}" và {len(mau)} mẫu:\n'
                                    f'{ds["file"]}\n\nGửi file này qua Zalo / email; máy nhận bấm đúp file (hoặc Công cụ → Nhập '
                                    'gói mẫu in & cấu hình…) là cập nhật, không cần cài lại phần mềm.')
        return ds

    def tao_goi_don_vi(self, cho: bool = True):
        """Tạo gói .pabtcfg hàng loạt: mỗi đơn vị (dòng của file Excel / .json) một gói, không đổi cấu hình máy này. Trả hộp."""
        from .man_hinh_goi_don_vi import HopGoiDonVi
        d = HopGoiDonVi(self)
        if cho:
            d.exec()
        return d

    def nhap_goi_mau(self, file=None, xac_nhan: bool = True):
        """Cài gói .pabtcfg: kiểm tra, hỏi, sao lưu mẫu cũ, thay mẫu + hồ sơ địa phương. Trả kết quả goi_mau.cai hoặc None."""
        from . import goi_mau
        if file is None:
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn gói mẫu in & cấu hình', str(Path.home() / 'Downloads'),
                                                  f'Gói mẫu in & cấu hình PABT (*{goi_mau.DUOI})')
            if not file:
                return None
        try:
            with con_tro_cho():
                ds = goi_mau.doc_goi(file)
        except goi_mau.LoiGoiMau as e:
            QMessageBox.warning(self, TEN_UD, chu_loi(f'Không nhập được gói {Path(file).name}', e))
            return None
        if xac_nhan and QMessageBox.question(
                self, TEN_UD, 'Cài gói mẫu in & cấu hình?\n\n' + '\n'.join(goi_mau.mo_ta_goi(ds)) +
                '\n\nMẫu / hồ sơ cũ được sao lưu trước khi thay.') != QMessageBox.StandardButton.Yes:
            return None
        try:
            kq = goi_mau.cai(file)
        except goi_mau.LoiGoiMau as e:
            QMessageBox.warning(self, TEN_UD, str(e))
            return None
        self._lam_moi_don_vi()                          # băng tiêu đề lấy tên phần mềm / đơn vị mặc định mới khi dự án để trống
        if xac_nhan:
            QMessageBox.information(self, TEN_UD, f'Đã cài {len(kq["mau"])} mẫu' + (' và hồ sơ địa phương' if kq['ho_so'] else '') +
                                    f'.\nHồ sơ địa phương đang dùng: {kq["ten_ho_so"]}' +
                                    (f'\nBản cũ sao lưu ở: {kq["sao_luu"]}' if kq['sao_luu'] else ''))
        return kq

    # ------------------------------------------------ máy chủ LAN, tài khoản
    def dat_tieu_de(self):
        """Tiêu đề cửa sổ = chỗ DUY NHẤT hiện tên dự án (15/10/2026, người dùng: trước đây lặp ở banner và dòng dưới banner):
        "PABT - <tên dự án> · <địa bàn> (<file>)"; chưa mở dự án: "PABT - Lập phương án bồi thường, hỗ trợ". Thanh tiêu đề hợp
        nhất hiện ở giữa thanh menu trắng (dài thì rút "…" ở giữa, đủ chữ ở chú thích)."""
        t = TIEU_DE_CUA_SO
        if self.file is None:
            t += ' - ' + MO_TA_UD
        else:
            ten = dia_ban = ''
            if self.con is not None:
                try:
                    da = self.con.execute('SELECT ten, ten_dia_ban FROM du_an WHERE id = 1').fetchone()
                except sqlite3.Error:
                    da = None
                if da is not None:
                    ten, dia_ban = (str(da[0] or '').strip(), str(da[1] or '').strip())
            if ten:
                t += f' - {ten}' + (f' · {dia_ban}' if dia_ban else '') + f' ({self.file.name})'
            else:
                t += f' - {self.file.name}'
            if self.chi_doc:
                t += '  [CHỈ XEM]'
            try:
                if may_chu.thu_muc_offline() in self.file.resolve().parents:
                    t += '  [BẢN LÀM OFFLINE]'
            except OSError:
                pass
        if may_chu.PHIEN is not None:
            t += f'  ·  {may_chu.PHIEN.ten_hien}'
        self.setWindowTitle(t)

    def cap_nhat_tai_khoan(self):
        # đèn báo mạng LAN (đặc tả: Online / Offline trên thanh trạng thái) gộp vào nút tài khoản - một chỗ
        p = may_chu.PHIEN
        if p is not None:
            self.nut_tk.setText(f'● LAN: Trực tuyến · Tài khoản: {p.ten_hien}')
            self.nut_tk.setToolTip(f'Đăng nhập máy chủ {p.goc}')
            mau = '#107C41'
        elif may_chu.doc_cau_hinh().get('may_chu'):
            self.nut_tk.setText('● LAN: Ngoại tuyến (Offline) · Đăng nhập máy chủ')
            self.nut_tk.setToolTip('Đang làm việc offline với file trên máy này')
            mau = '#9A5A12'
        else:
            self.nut_tk.setText('● Máy đơn · Máy chủ LAN')
            self.nut_tk.setToolTip('Không dùng máy chủ trong mạng nội bộ. Bấm để thiết lập (không bắt buộc).')
            mau = '#5F6368'
        self.nut_tk.setStyleSheet(f'QToolButton {{ color: {mau}; font-weight: 600; }}')
        self.dat_tieu_de()

    def _menu_tai_khoan(self):
        m = self.nut_tk.menu()
        m.clear()
        p = may_chu.PHIEN
        # chỉ việc của tài khoản; mở / mang về / đưa lên dự án trên máy chủ: "Dự án" → "Dự án trên máy chủ…" (trước 0.9.18 lặp
        # thêm ở đây dưới 2 tên khác: "Dự án trên máy chủ, làm offline…", "Dự án đã mang về làm offline…")
        if p is not None:
            m.addAction(f'Máy chủ: {p.goc}').setEnabled(False)
            m.addAction('Đổi mật khẩu…', lambda: self.doi_mat_khau())
            if p.la_quan_tri:
                m.addAction('Quản lý tài khoản người dùng…', lambda: self.quan_ly_tai_khoan())
            m.addSeparator()
            m.addAction('Đăng xuất', lambda: self.dang_xuat())
        else:
            m.addAction('Đăng nhập máy chủ…', lambda: self.dang_nhap())
        m.addSeparator()
        m.addAction('Thiết lập máy chủ…', lambda: self.thiet_lap_may_chu())

    def dang_nhap(self, cho: bool = True, tu_mo_lai: bool = True):
        """Hộp đăng nhập; đăng nhập được thì mở lại dự án làm gần nhất của tài khoản (ở máy bất kỳ)."""
        from .man_hinh_may_chu import HopDangNhap
        dlg = HopDangNhap(self)
        if not cho:
            return dlg
        dlg.exec()
        self.sau_dang_nhap(tu_mo_lai and self.con is None)
        return dlg

    def sau_dang_nhap(self, tu_mo_lai: bool = True):
        self.cap_nhat_tai_khoan()
        if may_chu.PHIEN is None:
            return None
        self.dong_bo_bo_don_gia()
        if self.con is not None and not self.chi_doc:       # nhật ký kiểm toán ghi đúng tài khoản vừa đăng nhập
            from . import kiem_toan
            try:
                kiem_toan.dat_phien(self.con)
            except sqlite3.Error:
                pass
        cuoi = None
        if tu_mo_lai:
            try:
                cuoi = may_chu.du_an_cuoi()
            except (may_chu.LoiMayChu, OSError):
                cuoi = None
        if cuoi is not None:
            self.mo(cuoi)
            self.statusBar().showMessage(f'Xin chào {may_chu.PHIEN.ten_hien}: đã mở lại dự án đang làm - {cuoi.name}', 15000)
        else:
            self.statusBar().showMessage(f'Xin chào {may_chu.PHIEN.ten_hien}. Dự án dùng chung: nút "Dự án trên máy chủ…".', 15000)
        return cuoi

    def dong_bo_bo_don_gia(self) -> str:
        """1.0.56: đăng nhập máy chủ -> nhận bộ đơn giá (tài sản, cây trồng, vật nuôi, chính sách, bảng giá đất, hệ số K) do quản trị phát
        hành; quản trị đăng nhập mà máy chủ chưa có bộ nào -> phát hành bộ của máy này (lần đầu). Lỗi chỉ báo, không chặn đăng nhập."""
        from . import dong_bo_don_gia as db, quan_tri_bo
        from .giao_dien import con_tro_cho, thong_bao_noi
        chu, loai = '', 'tin'
        try:
            with con_tro_cho():
                if quan_tri_bo.la_quan_tri_may_chu() and db.doc_phien_ban() is None:
                    db.phat_hanh()
                    chu = 'Đã phát hành bộ đơn giá của máy này lên máy chủ (các máy khác nhận khi đăng nhập).'
                else:
                    kq = db.nhan()
                    if kq:
                        chu = f'Đã nhận {db.mo_ta(kq)} từ máy chủ.'
        except Exception as e:                          # noqa: BLE001 - mất mạng / file đang ghi dở: lần đăng nhập sau nhận lại
            chu, loai = f'Chưa đồng bộ được bộ đơn giá với máy chủ: {e}', 'canh_bao'
            from .giao_dien import ghi_loi_log
            ghi_loi_log(chu)
        if chu:
            self.statusBar().showMessage(chu, 15000)
            try:
                thong_bao_noi(self, chu, loai)
            except Exception:                           # noqa: BLE001 - thông báo nổi không được làm hỏng đăng nhập
                pass
        return chu

    def dang_xuat(self, xac_nhan: bool | None = None):
        if may_chu.PHIEN is None:
            return
        if xac_nhan is None:
            xac_nhan = QMessageBox.question(self, TEN_UD, 'Đăng xuất tài khoản? Dự án đang mở sẽ được đóng.') \
                == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return
        self.dong_du_an()
        self.file = None
        self._xoa_ket_qua()
        may_chu.dang_xuat()
        self.cap_nhat_tai_khoan()

    def thiet_lap_may_chu(self):
        from .man_hinh_may_chu import HopThietLap
        dlg = HopThietLap(self)
        if dlg.exec():
            if dlg.goc and may_chu.PHIEN is None:
                self.dang_nhap()
            elif not dlg.goc:
                self.cap_nhat_tai_khoan()
        return dlg

    def doi_mat_khau(self):
        from .man_hinh_may_chu import HopDoiMatKhau
        HopDoiMatKhau(self).exec()

    def quan_ly_tai_khoan(self):
        from .man_hinh_may_chu import HopTaiKhoan
        HopTaiKhoan(self).exec()

    def du_an_may_chu(self, cho: bool = True):
        if may_chu.PHIEN is None and not may_chu.ds_lay_ve_cuc_bo():
            if QMessageBox.question(self, TEN_UD, 'Chưa đăng nhập máy chủ. Đăng nhập (hoặc thiết lập máy chủ) ngay?') \
                    == QMessageBox.StandardButton.Yes:
                self.dang_nhap(tu_mo_lai=False)
            if may_chu.PHIEN is None:
                return None
        from .man_hinh_may_chu import HopDuAnMayChu
        if self.file is not None and may_chu.thu_muc_offline() in self.file.resolve().parents:
            self.dong_du_an()                       # để đưa lên / hủy được bản offline đang mở
        dlg = HopDuAnMayChu(self)
        if not cho:
            return dlg
        if dlg.exec() and dlg.mo_file is not None:
            self.mo(dlg.mo_file)
        return dlg

    def khoi_dong_may_chu(self, mo_lai: bool = True):
        """Khi mở phần mềm: có thiết lập máy chủ và kết nối được thì hiện đăng nhập; không thì làm việc offline bình thường."""
        goc = may_chu.doc_cau_hinh().get('may_chu')
        if not goc:
            return 'khong_dung'
        from .man_hinh_may_chu import ket_noi_duoc      # luồng nền: máy chủ không tới được thì cửa sổ không đứng hình 4 giây
        if ket_noi_duoc(self, goc):
            self.dang_nhap(tu_mo_lai=mo_lai)
            return 'dang_nhap' if may_chu.PHIEN is not None else 'offline'
        self.cap_nhat_tai_khoan()
        off = may_chu.ds_lay_ve_cuc_bo()
        self.statusBar().showMessage(f'Không kết nối được máy chủ {goc}: đang làm việc offline'
                                     + (f' ({len(off)} dự án đã mang về máy này).' if off else '.'), 20000)
        if off and mo_lai and self.con is None and QMessageBox.question(
                self, TEN_UD, f'Không kết nối được máy chủ:\n{goc}\n\nMáy này có {len(off)} dự án đã mang về làm offline. '
                              'Mở danh sách để làm tiếp?') == QMessageBox.StandardButton.Yes:
            self.du_an_may_chu()
        return 'mat_ket_noi'

    def closeEvent(self, e):
        # 1.0.58: khái toán chưa lưu (kể cả chưa đặt tên file) không mất im lặng khi thoát
        kt = sys.modules.get('pabt.man_hinh_du_toan')
        if kt is not None and any(not k.hoi_luu() for k in self.findChildren(kt.KhungDuToan)):
            e.ignore()
            return
        if self.dong_du_an() is False:                  # 1.0.58: người dùng Hủy / lưu lỗi: ở lại, không đóng, không mất thay đổi
            e.ignore()
            return
        from .giao_dien import KHI_DOI_TY_LE, TRUOC_DOI_TY_LE, XU_LY_HOAN_TAC
        if self._hien_ty_le in KHI_DOI_TY_LE:
            KHI_DOI_TY_LE.remove(self._hien_ty_le)
        if self._bo_trang_an in TRUOC_DOI_TY_LE:       # 1.0.51: không giữ tham chiếu cửa sổ đã đóng (rò rỉ khi mở lại nhiều lần)
            TRUOC_DOI_TY_LE.remove(self._bo_trang_an)
        if self.hoan_tac_phim in XU_LY_HOAN_TAC:
            XU_LY_HOAN_TAC.remove(self.hoan_tac_phim)
        if may_chu.PHIEN is not None:                   # ghi "Đăng xuất" lên máy chủ: chờ tối đa 3 giây (mất mạng không treo lúc đóng)
            import threading
            t = threading.Thread(target=may_chu.dang_xuat, daemon=True)
            t.start()
            t.join(3)
        super().closeEvent(e)


def hien_cua_so(w) -> None:
    """Hiện cửa sổ chính phóng to. Kích thước thường đặt trước bằng vùng làm việc của màn hình: kiểu chữ / màu áp lúc Show
    (_BoToMau) làm bề rộng tối thiểu tăng; lớn hơn kích thước thường (từng 1414 > 1360 điểm) thì Qt ép lại kích thước SAU khi phóng
    to -> Windows vẫn ghi "phóng to" nhưng cửa sổ chỉ 1414 x 760, phần màn hình còn lại hiện cửa sổ phía sau (người dùng 11/10/2026:
    lỗi hình góc trên bên phải). Không hiện thường rồi mới phóng to: khung đầu tiên đen."""
    from .giao_dien import kich_thuoc_thuong
    # kích thước THƯỜNG = 1200 x 740 canh giữa (đặc tả V10): nút Thu về / Restore Down của Windows trả cửa sổ về đây, không còn "thu
    # về" mà vẫn kín màn hình (trước 0.9.77 kích thước thường = cả vùng làm việc)
    w.setGeometry(kich_thuoc_thuong(w))
    w.showMaximized()


# 1.0.52 (người dùng 02/11/2026): định danh thương mại, không dùng tiền tố "gov" của cơ quan nhà nước. Lối tắt của bộ cài mang cùng
# định danh (cai_dat.ps1 $APP_ID) và bộ cài đổi luôn định danh các lối tắt đã ghim. Máy còn bản cài GỐC trước 1.0.52 (chỉ nhận gói
# .larcud) giữ định danh cũ: lối tắt của máy đó còn định danh cũ - đổi thì taskbar tách thành hai nút
APP_USER_MODEL_ID = 'vn.larc.desktop.enterprise'
APP_USER_MODEL_ID_CU = 'gov.pabt.boithuong.enterprise.2026'
ID_MOI_TU_BAN_CAI = '1.0.52'


def dinh_danh_ung_dung() -> str:
    """Định danh taskbar theo bản cài gốc: bản cài gốc < 1.0.52 (đang chạy gói cập nhật) -> định danh cũ."""
    if not getattr(sys, 'frozen', False):
        return APP_USER_MODEL_ID
    try:
        import nap_cap_nhat
        goc = nap_cap_nhat.BAN_GOC or __version__
    except ImportError:
        goc = __version__
    so = lambda v: tuple(int(x) for x in str(v).split('.') if x.isdigit())     # noqa: E731
    return APP_USER_MODEL_ID if so(goc) >= so(ID_MOI_TU_BAN_CAI) else APP_USER_MODEL_ID_CU


def dat_app_user_model_id() -> bool:
    """Windows: định danh ứng dụng riêng cho taskbar (0.9.74 - người dùng 13/10/2026) - gọi TRƯỚC khi tạo QApplication. Không có
    thì khi chạy bằng python.exe (mã nguồn) taskbar gộp vào biểu tượng Python; bản exe cũng gộp cửa sổ đúng nhóm PABT."""
    if sys.platform != 'win32':
        return False
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(dinh_danh_ung_dung())
        return True
    except Exception:                                   # noqa: BLE001 - Windows quá cũ / thiếu API: bỏ qua, không chặn khởi động
        return False


def main() -> int:
    dat_app_user_model_id()
    app = QApplication(sys.argv)
    app.setApplicationName('PABT')
    from .giao_dien import ap_dung, cai_bat_loi
    ap_dung(app)
    cai_bat_loi()                                      # lỗi trong nút bấm: báo + ghi loi.log (trước đây mất im lặng)
    from .ban_quyen import kiem_tra_ban_quyen          # cổng chờ bản quyền (giai đoạn này luôn hợp lệ - ban_quyen.py)
    if not kiem_tra_ban_quyen():
        QMessageBox.critical(None, TEN_UD, 'Bản quyền phần mềm không hợp lệ hoặc đã hết hạn.')
        return 1
    menu_trai = '--menu-tren' not in sys.argv              # từ 0.9.3: menu dọc bên trái thay thanh nút phía trên
    w = CuaSoChinh(menu_trai=menu_trai)
    from .giao_dien import bieu_tuong
    w.setWindowIcon(bieu_tuong())                       # (app.setWindowIcon ở ap_dung đã gán cho mọi cửa sổ; gắn thẳng cho chắc)
    w.dat_tieu_de()
    tep = [a for a in sys.argv[1:] if not a.startswith('--')]
    co_file = bool(tep and csdl.la_file_du_an(tep[0]))
    hien_cua_so(w)                         # dùng hết màn hình: thanh nút gọn 2 dòng, danh sách hộ rộng
    w.khoi_dong_may_chu(mo_lai=not co_file)   # máy chủ LAN (nếu có thiết lập): đăng nhập, mở lại dự án đang làm
    if co_file:
        w.mo(tep[0])
    try:
        import nap_cap_nhat
        # 1.0.51: vòng sự kiện đã chạy, cửa sổ đã lên hình: xóa cờ "đang khởi động" sau 1 giây (trước 5 giây - tắt máy / đóng ngay
        # trong 5 giây đầu bị tính là khởi động hỏng, hai lần là bỏ bản cập nhật .larcud)
        QTimer.singleShot(1000, nap_cap_nhat.khoi_dong_tot)
    except ImportError:
        pass
    if tep and tep[0].lower().endswith(('.larcud', '.pabtcn')):                          # nhấp đúp gói cập nhật
        QTimer.singleShot(0, lambda: w.cap_nhat_phan_mem(tep[0]))
    if tep and tep[0].lower().endswith('.pabtcfg'):                         # nhấp đúp gói mẫu in & cấu hình (0.9.85)
        QTimer.singleShot(0, lambda: w.nhap_goi_mau(tep[0]))
    from . import dia_phuong
    if dia_phuong.loi():                                                    # hồ sơ địa phương trên máy sai: đang dùng mặc định
        QTimer.singleShot(800, lambda: QMessageBox.warning(
            w, TEN_UD, 'Hồ sơ địa phương trên máy chưa hợp lệ, phần mềm đang dùng hồ sơ mặc định:\n\n' + '\n'.join(dia_phuong.loi()) +
            f'\n\nSửa file {dia_phuong.file_may()} hoặc nhập lại gói .pabtcfg.'))
    return app.exec()

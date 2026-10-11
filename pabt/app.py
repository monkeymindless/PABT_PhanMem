"""Cửa sổ chính phần mềm PABT: nhập file Excel, danh sách hộ, lập phương án từng hộ, thông tin dự án, rà soát giá, đối chiếu."""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, QTimer
from PySide6.QtGui import QAction, QBrush, QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit,
                               QMainWindow, QMessageBox, QPlainTextEdit, QStackedWidget, QTableView, QToolButton,
                               QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from . import BAN_THU_NGHIEM, NHAN_THU_NGHIEM, __version__, csdl, khoa, lap_pa, may_chu, nghiep_vu
from .tien import D, so_vn, vn
from .giao_dien import con_tro_cho
from .thong_bao import TEN_UD, THE_TONG_HOP, chu_loi

# doi_chieu, nhap_excel, nhap_tho (kéo theo openpyxl ~0,2 giây - 60% thời gian nạp mã lúc mở phần mềm) nạp khi dùng tới

TIEU_DE_CUA_SO = TEN_UD + (f' ({NHAN_THU_NGHIEM})' if BAN_THU_NGHIEM else '')     # tiêu đề cửa sổ chính
# danh sách hộ ở màn hình chính: gọn (0.9.12). Tiền từng mục, quyết định, chi trả, bàn giao, ghi chú: menu "Bảng tổng hợp",
# "Theo dõi tiến độ" (man_hinh_theo_doi)
COT = ['STT', 'Họ và tên', 'Địa chỉ', 'Số thửa', 'DT thu hồi (m²)', 'Trạng thái']
COT_SO = {4}
# các trang bên phải cửa sổ chính (chọn ở menu trái)
TRANG = ['Danh sách hộ', *THE_TONG_HOP, 'Theo dõi tiến độ']     # trang bên phải: 1-3 = các thẻ của Bảng tổng hợp
XANH, DO, VANG = QColor('#E2EFDA'), QColor('#F8CBAD'), QColor('#FFF2CC')
CHUA_MO = ('Chưa mở dự án. Bấm <b>"Dự án"</b> → <b>"Dự án mới…"</b> để nhập thông tin dự án, danh sách hộ, '
           'thửa (thô) và bảng giá đất: phần mềm tự lập phương án và xuất 2 bảng in. Hoặc "Mở dự án…" / "Nhập file Excel…".')
# menu trái: nhóm đóng sẵn lần đầu mở phần mềm (sau đó nhớ theo người dùng) - vừa màn hình 1366x768 không phải cuộn
NHOM_DONG_MAC_DINH = ('Đơn giá, dự toán', 'Trình duyệt, tiến độ', 'In, báo cáo')
# chữ ngắn trên menu (khóa = tên lệnh đầy đủ trong self.lenh, hiện ở gợi ý khi rê chuột)
NHAN_MENU = {'Lập phương án hộ…': 'Lập phương án', 'Thêm hộ…': 'Thêm hộ', 'Xóa hộ…': 'Xóa hộ', 'Kiểm tra lỗi…': 'Kiểm tra lỗi',
             'Bộ đơn giá…': 'Bộ đơn giá', 'Đơn giá riêng dự án…': 'Đơn giá riêng', 'Rà soát giá…': 'Rà soát giá',
             'Dự toán, áp giá dự thảo…': 'Dự toán', 'Quy chuẩn cây, tài sản…': 'Quy chuẩn cây',
             'Thông tin tổng quát hộ': 'Tổng quát hộ', 'Tổng hợp tiền theo phương án': 'Tổng hợp tiền',
             'Quyết định phê duyệt': 'Quyết định', 'Đợt trình…': 'Đợt trình', 'Trạng thái hộ…': 'Trạng thái hộ',
             'In / Xuất…': 'In / Xuất', 'Báo cáo tổng hợp…': 'Báo cáo tổng hợp', 'Cập nhật mẫu in…': 'Mẫu in',
             'Xuất báo cáo đối chiếu…': 'Đối chiếu với file Excel…'}


class LocHo(QSortFilterProxyModel):
    """Lọc danh sách hộ theo đợt trình, trạng thái xử lý và từ khóa."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dot = ''                  # '' tất cả / 'chua' chưa xếp đợt / id đợt
        self.trang_thai = ''           # khóa trong quan_ly.TRANG_THAI
        self.tu_khoa = []
        self._hop_tt = None            # quan_ly.hop_trang_thai - nạp khi lần đầu lọc theo trạng thái (không nạp lúc mở phần mềm)

    def dat(self, dot=None, trang_thai=None, tu_khoa=None):
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
        if moi:
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)
        else:
            self.invalidateFilter()

    def filterAcceptsRow(self, r, parent):
        # gọi cho TỪNG dòng mỗi lần lọc (5.000 hộ x mỗi phím gõ): không import / tra thuộc tính thừa ở đây
        d = self.sourceModel().dong[r]
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
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return COT[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        d, c = self.dong[index.row()], index.column()
        v = d['o'][c]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if c == 4:
                return so_vn(v)
            return str(v)
        if role == Qt.ItemDataRole.ToolTipRole:
            if c == 5:
                return d.get('goi_y_tt') or str(v)
            if c in (1, 2):
                return f'{v}\nMã hộ {d["ma_ho"]}' + (f'\nGhi chú: {d["theo_doi"]}' if d.get('theo_doi') else '')
            return None
        if role == Qt.ItemDataRole.UserRole:                       # giá trị để sắp xếp
            return float(v) if c in COT_SO or c in (0, 3) else str(v)
        if role == Qt.ItemDataRole.TextAlignmentRole and (c in COT_SO or c in (0, 3)):
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        if role == Qt.ItemDataRole.BackgroundRole and c == 5 and d.get('mau_tt') is not None:
            return QBrush(d['mau_tt'])
        return None


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
        for muc in nghiep_vu.THU_TU_MUC:                # 1 đất, 2 nhà, 3 cây, 4 vật nuôi, 5 hỗ trợ, 6 thưởng
            goc = QTreeWidgetItem([str(nghiep_vu.so_muc(muc)), nghiep_vu.TEN_MUC[muc], '', '', '', '', vn(k.muc[muc])])
            for i in (0, 1, 6):
                goc.setFont(i, dam)
            goc.setTextAlignment(6, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            for d in (x for x in k.dong if x.muc == muc):
                it = QTreeWidgetItem([d.stt, d.ten, d.dvt, so_vn(d.so_luong), vn(d.don_gia),
                                      f'{so_vn(d.ty_le * 100)}%', vn(d.thanh_tien)])
                for i in (3, 4, 5, 6):
                    it.setTextAlignment(i, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if d.thanh_tien_excel is not None and d.thanh_tien_excel != d.thanh_tien:
                    it.setBackground(6, QBrush(DO))
                    it.setToolTip(6, f'Excel: {vn(d.thanh_tien_excel)}')
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
        self.dong_ho = QTimer(self)                      # làm mới khóa file mỗi phút
        self.dong_ho.setInterval(khoa.LAM_MOI * 1000)
        self.dong_ho.timeout.connect(self.lam_moi_khoa)
        self.setWindowTitle(TIEU_DE_CUA_SO)
        man = QApplication.primaryScreen()
        vung = man.availableGeometry() if man else None
        self.resize(min(1360, vung.width() - 40) if vung else 1360, min(760, vung.height() - 40) if vung else 760)
        self.setMinimumHeight(560)          # đủ chỗ cho băng tiêu đề + thanh nút 2 dòng khi cửa sổ hẹp
        self.lenh = {}
        for ten, ham in (('Dự án mới…', lambda: self.du_an_moi()),
                         ('Nhập file Excel…', lambda: self.nhap_excel()), ('Mở dự án…', self.mo_du_an),
                         ('Nhập phương án chi tiết…', lambda: self.nhap_chi_tiet()),
                         ('Thêm hộ…', lambda: self.mo_ho_so(moi=True)),
                         ('Xóa hộ…', lambda: self.xoa_ho()),
                         ('Lập phương án hộ…', lambda: self.mo_lap_pa()), ('Thông tin dự án…', lambda: self.sua_du_an()),
                         ('Rà soát giá…', lambda: self.ra_soat_gia()), ('In / Xuất…', lambda: self.in_xuat()),
                         ('Cập nhật mẫu in…', lambda: self.cap_nhat_mau_in()),
                         ('Bộ đơn giá…', lambda: self.bo_don_gia()),
                         ('Đơn giá riêng dự án…', lambda: self.don_gia_rieng()),
                         ('Xuất báo cáo đối chiếu…', self.xuat_bao_cao), ('Cập nhật phần mềm…', lambda: self.cap_nhat_phan_mem()),
                         ('Giới thiệu', self.gioi_thieu),
                         ('Lưu dự án thành…', lambda: self.luu_du_an_thanh()), ('Đợt trình…', lambda: self.dot_trinh()),
                         ('Trạng thái hộ…', lambda: self.trang_thai_ho()),
                         ('Báo cáo tổng hợp…', lambda: self.bao_cao_tong_hop()), ('Kiểm tra lỗi…', lambda: self.kiem_tra_loi()),
                         ('Dự toán, áp giá dự thảo…', lambda: self.du_toan()),
                         ('Quy chuẩn cây, tài sản…', lambda: self.quy_chuan()),
                         ('Dự án trên máy chủ…', lambda: self.du_an_may_chu()),
                         *((t, lambda _=False, i=i: self.mo_trang(i)) for i, t in enumerate(TRANG))):
            a = QAction(ten, self)
            a.triggered.connect(lambda _=False, ham=ham: self._chay_lenh(ham))
            self.lenh[ten] = a
        for k, t in enumerate(TRANG):                   # mục trang ở menu trái: đánh dấu trang đang xem
            self.lenh[t].setCheckable(True)
            self.lenh[t].setChecked(k == 0)
        self.dm = None
        self.lb_du_an = QLabel(CHUA_MO)
        self.lb_du_an.setWordWrap(True)
        self.lb_du_an.setProperty('vai', 'bang_ten')
        self.lb_ket_qua = QLabel('')
        self.lb_ket_qua.setStyleSheet('QLabel { font-weight: bold; padding: 5px 8px; }')
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm theo mã hộ, họ tên, trạng thái, ghi chú (không cần dấu)…')
        self.o_tim.setClearButtonEnabled(True)
        self.mo_hinh = BangHo()
        self.loc = LocHo(self)
        self.loc.setSourceModel(self.mo_hinh)
        self.loc.setSortRole(Qt.ItemDataRole.UserRole)
        self.o_tim.textChanged.connect(lambda t: self._loc(tu_khoa=t))
        self.cb_dot = QComboBox()
        self.cb_dot.setMinimumWidth(150)
        self.cb_dot.addItem('Tất cả đợt', '')
        self.cb_dot.currentIndexChanged.connect(lambda *_: self._loc(dot=self.cb_dot.currentData()))
        self.cb_tt = QComboBox()
        self.cb_tt.addItem('Tất cả trạng thái', '')
        from .quan_ly import TRANG_THAI
        for k, t in TRANG_THAI:
            self.cb_tt.addItem(t, k)
        self.cb_tt.currentIndexChanged.connect(lambda *_: self._loc(trang_thai=self.cb_tt.currentData()))
        self.lb_loc = QLabel('')
        self.bang = QTableView()
        self.bang.setModel(self.loc)
        self.bang.setSortingEnabled(True)
        self.bang.setAlternatingRowColors(True)
        self.bang.setWordWrap(True)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.bang.verticalHeader().setVisible(False)
        self.bang.horizontalHeader().setResizeContentsPrecision(300)    # tự canh cột: đo 300 dòng mẫu, không đo hết (3.000 hộ)
        self.bang.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.bang.doubleClicked.connect(lambda idx: self._chay_lenh(lambda: self.mo_chi_tiet(idx)))
        self.bang.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bang.customContextMenuRequested.connect(lambda p: self._menu_ho(self.bang, p))
        from PySide6.QtGui import QKeySequence, QShortcut
        phim_xoa = QShortcut(QKeySequence(QKeySequence.StandardKey.Delete), self.bang)    # phím Delete trên danh sách hộ
        phim_xoa.setContext(Qt.ShortcutContext.WidgetShortcut)                            # (không áp khi đang sửa ô ghi chú)
        phim_xoa.activated.connect(lambda: self.lenh['Xóa hộ…'].isEnabled() and self._chay_lenh(self.xoa_ho))
        self._vua_tieu_de()
        # trang bên phải: danh sách hộ / bảng tổng hợp (3 mục) / theo dõi tiến độ - chọn ở menu trái
        from .man_hinh_theo_doi import KhungBangTongHop, KhungTienDo
        self.bang_tong_hop = KhungBangTongHop(None, self)
        self.tien_do = KhungTienDo(None, self)
        for k in (self.bang_tong_hop, self.tien_do):
            k.da_doi.connect(lambda: self.tai_lai(giu_trang=True))
            k.mo_ho.connect(lambda m: self.trang_thai_ho([m]))
        # bấm thẳng thẻ của Bảng tổng hợp: tiêu đề trang + dấu chọn ở menu trái đi theo (trước: giữ trang cũ)
        self.bang_tong_hop.the_da_doi.connect(lambda i: self.trang.currentIndex() == 1 and self._danh_dau_trang(1 + i))
        hang = QHBoxLayout()
        for ten, w in (('Đợt:', self.cb_dot), ('Trạng thái:', self.cb_tt), ('Tìm:', self.o_tim)):
            nhan_tim = QLabel(ten)
            nhan_tim.setProperty('vai', 'nhan')
            hang.addWidget(nhan_tim)
            hang.addWidget(w, 1 if w is self.o_tim else 0)
        hang.addWidget(self.lb_loc)
        nen = QWidget()
        lo = QVBoxLayout(nen)
        lo.setContentsMargins(10, 8, 10, 6)
        lo.setSpacing(7)
        from .giao_dien import bang_to_chuc, do_bong, thanh_lenh
        from .giao_dien import menu_trai as tao_menu_trai
        L = self.lenh
        # 0.9.20 (người dùng yêu cầu "gọn chữ"): chữ trên menu ngắn (NHAN_MENU, tên đầy đủ ở gợi ý); khóa self.lenh giữ tên cũ
        for k, ngan in NHAN_MENU.items():
            L[k].setText(ngan)
            L[k].setToolTip(k.rstrip('…'))
        nhom = [
            ('Dự án', [L['Dự án mới…'], L['Mở dự án…'], L['Lưu dự án thành…'], L['Nhập file Excel…'],
                       L['Nhập phương án chi tiết…'], L['Xuất báo cáo đối chiếu…'], L['Thông tin dự án…'],
                       L['Dự án trên máy chủ…']]),
            ('Hồ sơ, phương án', [L['Lập phương án hộ…'], L['Thêm hộ…'], L['Xóa hộ…'], L['Kiểm tra lỗi…']]),
            ('Đơn giá, dự toán', [L['Bộ đơn giá…'], L['Đơn giá riêng dự án…'], L['Rà soát giá…'],
                                  L['Dự toán, áp giá dự thảo…'], L['Quy chuẩn cây, tài sản…']]),
            ('Tổng hợp', [L['Danh sách hộ'], L['Thông tin tổng quát hộ'], L['Tổng hợp tiền theo phương án']]),
            # mọi việc về quyết định ở MỘT chỗ: trang "Quyết định phê duyệt" (Thêm / Nhập từ file / Sửa / Xóa); trước 0.9.18 trang
            # nằm ở nhóm Bảng tổng hợp và nhóm này có thêm "Nhập quyết định…" - cùng hộp thoại với nút "Nhập từ file…" của trang
            ('Trình duyệt, tiến độ', [L['Theo dõi tiến độ'], L['Đợt trình…'], L['Quyết định phê duyệt'], L['Trạng thái hộ…']]),
            ('In, báo cáo', [L['In / Xuất…'], L['Báo cáo tổng hợp…'], L['Cập nhật mẫu in…']]),
        ]
        # hoàn tác / làm lại thao tác đã ghi vào file dự án (Ctrl+Z / Ctrl+Y ở mọi cửa sổ): trên băng tiêu đề, cạnh tên phần mềm
        from .giao_dien import XU_LY_HOAN_TAC
        self.nut_ht = {}
        for k, chu, lai in (('lui', '↶ Hoàn tác', False), ('toi', '↷ Làm lại', True)):
            b = QToolButton()
            b.setText(chu)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, x=lai: self.hoan_tac(x))
            self.nut_ht[k] = b
        lo.addWidget(do_bong(bang_to_chuc(f'Phiên bản {__version__}', (self.nut_ht['lui'], self.nut_ht['toi'])), 18, 3, 45))
        if self.menu_trai:
            ngang = QHBoxLayout()
            ngang.setSpacing(8)
            # "Dự án" (lệnh ít dùng) = một nút xổ; nhóm khác bấm tiêu đề để đóng / mở - menu không tràn màn hình 1366x768
            self.khung_menu = tao_menu_trai(nhom, xo=('Dự án',), dong_mac_dinh=NHOM_DONG_MAC_DINH)
            ngang.addWidget(self.khung_menu)
            phai = QVBoxLayout()
            phai.setSpacing(7)
            ngang.addLayout(phai, 1)
            lo.addLayout(ngang, 1)
        else:
            lo.addWidget(thanh_lenh(nhom))
            phai = lo
        phai.addWidget(self.lb_du_an)
        phai.addLayout(self._hang_the_so())
        trang_ds = QWidget()
        lo_ds = QVBoxLayout(trang_ds)
        lo_ds.setContentsMargins(0, 0, 0, 0)
        lo_ds.setSpacing(7)
        # băng kết quả đối chiếu; Lập phương án / Thêm hộ chỉ ở menu trái (+ bấm đúp, chuột phải) - không lặp nút ở đây
        lo_ds.addWidget(self.lb_ket_qua)
        lo_ds.addLayout(hang)
        lo_ds.addWidget(self.bang, 1)
        self.lb_trang = QLabel('')
        self.lb_trang.setProperty('vai', 'tieu_de')
        self.lb_trang.setVisible(False)
        self.trang = QStackedWidget()
        for w in (trang_ds, self.bang_tong_hop, self.tien_do):
            self.trang.addWidget(w)
        phai.addWidget(self.lb_trang)
        phai.addWidget(self.trang, 1)
        self.setCentralWidget(nen)
        self.statusBar().showMessage('Nhấp đúp một hộ để lập / sửa phương án.')
        from PySide6.QtWidgets import QMenu
        # cỡ giao diện: nút − / + , bấm vào % để về 100%; phím Ctrl + con lăn chuột, Ctrl + "+" / "-" / "0"
        from .giao_dien import KHI_DOI_TY_LE, TY_LE, phong_to
        goi_y = 'Cỡ giao diện: Ctrl + con lăn chuột, hoặc Ctrl + "+" / Ctrl + "-"; Ctrl + 0 về 100%'
        self.nut_ty_le = {}
        for k, chu, buoc in (('nho', 'A−', -1), ('ty_le', '', 0), ('to', 'A+', 1)):
            b = QToolButton()
            b.setText(chu)
            b.setToolTip(goi_y)
            b.setAutoRaise(True)
            b.clicked.connect(lambda _=False, x=buoc: phong_to(x))
            self.statusBar().addPermanentWidget(b)
            self.nut_ty_le[k] = b
        self._hien_ty_le(TY_LE[0])
        KHI_DOI_TY_LE.append(self._hien_ty_le)
        XU_LY_HOAN_TAC.append(self.hoan_tac_phim)
        self._cap_nhat_nut_ht()
        self.nut_tk = QToolButton()                            # tài khoản / máy chủ LAN
        self.nut_tk.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.nut_tk.setMenu(QMenu(self.nut_tk))
        self.nut_tk.menu().aboutToShow.connect(self._menu_tai_khoan)
        self.statusBar().addPermanentWidget(self.nut_tk)
        self.cap_nhat_tai_khoan()
        for ten in ('Cập nhật phần mềm…', 'Giới thiệu'):                            # góc dưới bên phải cửa sổ
            a = L[ten]
            a.setIconText(a.text().rstrip('…'))
            from .giao_dien import MAU, icon_ky_hieu, ky_hieu_nut, nhom_nut
            k, n = ky_hieu_nut(ten), nhom_nut(ten)
            ic = icon_ky_hieu(k, MAU[n][1] if n else '#1F4E79', 16) if k else None
            if ic is not None:
                a.setIcon(ic)
            b = QToolButton()
            b.setDefaultAction(a)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon if ic is not None
                                 else Qt.ToolButtonStyle.ToolButtonTextOnly)
            self.statusBar().addPermanentWidget(b)

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
            mac_dinh = str(self.file if tho and self.file else Path(xl).with_suffix('.pabt'))
            hoi = {'options': QFileDialog.Option.DontConfirmOverwrite} if tho else {}   # tự hỏi "xóa trắng" bên dưới
            dich, _ = QFileDialog.getSaveFileName(self, 'Lưu vào file dự án', mac_dinh, 'Dự án PABT (*.pabt)', **hoi)
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
            dich, _ = QFileDialog.getSaveFileName(self, 'Lưu vào file dự án', str(Path(xl).with_suffix('.pabt')),
                                                  'Dự án PABT (*.pabt)')
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
        try:
            with con_tro_cho():
                if vao_mo:
                    bc = nhap_chi_tiet.ghi(self.con, kq.ho, cach, Path(xl).name, kq.du_an)
                else:
                    if self.file is not None and Path(dich).resolve() == self.file.resolve():
                        self.dong_du_an()
                    from .giao_dien import chay_nen         # file khác (kết nối riêng): ghi ở luồng nền, cửa sổ không treo
                    bc = chay_nen(self, lambda: nhap_chi_tiet.ghi_file(kq, dich, cach), f'Đang ghi vào {Path(dich).name}…')
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
        p, _ = QFileDialog.getOpenFileName(self, 'Mở dự án', str(tm), 'Dự án PABT (*.pabt)')
        if p:
            self.mo(p)

    def mo(self, p, chi_doc: bool | None = None):
        """Mở dự án. File đang được máy khác sửa thì hỏi: mở chỉ xem / vẫn mở để sửa (chi_doc: bỏ qua câu hỏi)."""
        try:
            self.dong_du_an()
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
            if not chi_doc:
                kf.lay(ep=True)
                self.khoa = kf
                self.dong_ho.start()
            self.chi_doc = chi_doc
            self.con = csdl.mo(p, chi_doc=chi_doc)
            if not chi_doc:
                from .hoan_tac import HoanTac
                self.ht = HoanTac(self.con, hen=lambda ham: QTimer.singleShot(0, ham))
                self.ht.khi_doi.append(self._cap_nhat_nut_ht)
                try:
                    self.dv = csdl.DauVetHo(self.con)
                except Exception:                      # không tạo được: vẫn mở dự án, tai_lai nạp toàn bộ như trước
                    self.dv = None
            self._cap_nhat_nut_ht()
            self.file = Path(p)
            self.dm = lap_pa.DanhMuc(self.con)
            # chỉ xem: tắt mọi lệnh ghi. Mỗi lệnh một QAction dùng chung cho menu trái / chuột phải - không còn nút gọi thẳng
            # hàm (trước 0.9.18 hai nút nhanh "Thêm hộ…", "Lập phương án hộ đang chọn" vẫn bật khi chỉ xem -> lỗi ghi CSDL)
            for ten in ('Thêm hộ…', 'Xóa hộ…', 'Lập phương án hộ…', 'Thông tin dự án…', 'Trạng thái hộ…'):
                self.lenh[ten].setEnabled(not chi_doc)
            self.bang_tong_hop.dat_du_an(self.con, chi_doc)
            self.tien_do.dat_du_an(self.con, chi_doc)
            self.tai_lai()
            from .man_hinh import lam_san                 # lúc rảnh: dựng sẵn danh sách chọn của cửa sổ lập phương án
            dm = self.dm
            QTimer.singleShot(400, lambda: dm is self.dm and lam_san(dm))
            if may_chu.PHIEN is not None:                   # đăng nhập máy chủ: máy khác đăng nhập cùng tài khoản sẽ mở tiếp dự án
                import threading                            # luồng riêng: máy chủ chậm / mất mạng không làm chậm việc mở dự án
                threading.Thread(target=may_chu.ghi_mo_du_an, args=(self.file,), daemon=True).start()
        except Exception as e:
            self.dong_du_an()
            QMessageBox.critical(self, TEN_UD, chu_loi('Không mở được dự án', e))

    def lam_moi_khoa(self):
        if self.khoa is not None and not self.khoa.lam_moi():
            self.dong_ho.stop()
            k = self.khoa.doc() or {}
            QMessageBox.warning(self, TEN_UD, f'Một máy khác ({khoa.mo_ta(k)}) đã mở file dự án để sửa.\n'
                                              'Hai máy cùng sửa có thể ghi đè số liệu của nhau: hãy thống nhất chỉ một máy sửa.')

    def dong_du_an(self):
        self.dong_ho.stop()
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
        if hasattr(self, 'nut_ht'):
            self._cap_nhat_nut_ht()
        self.kq = None
        self.dm = None
        self.mo_hinh.dat_du_lieu([])
        if hasattr(self, 'tien_do'):
            self.bang_tong_hop.dat_du_an(None)
            self.tien_do.dat_du_an(None)
        self._xoa_ket_qua()
        self.lb_loc.setText('')
        self._cap_nhat_the_so()

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
            if not xong:
                self._tai_lai_toan_bo()
            self._sau_tai_lai(giu_trang)
        finally:
            QApplication.restoreOverrideCursor()

    def _so_lieu_dong(self, ds_ma_ho=None) -> tuple:
        """(số thửa + DT, trường trạng thái trên bảng ho, TongHopHo, tên đợt) để dựng dòng danh sách; ds_ma_ho: chỉ các hộ này."""
        from . import theo_doi
        from .quan_ly import TRUONG_TT, ds_dot
        loc, ts = '', ()
        if ds_ma_ho is not None:
            loc, ts = f' WHERE ma_ho IN ({",".join("?" * len(ds_ma_ho))})', tuple(ds_ma_ho)
        so_thua = {r[0]: (r[1], D(r[2] or 0)) for r in self.con.execute(
            f"SELECT ma_ho, COUNT(*), SUM(CAST(dt_thu_hoi AS REAL)) FROM thua{loc} GROUP BY ma_ho", ts)}
        tt = {r['ma_ho']: dict(r) for r in self.con.execute(
            f'SELECT ma_ho, trang_thai, dot_id, dia_chi, {", ".join(TRUONG_TT)} FROM ho{loc}', ts)}
        th = {x.ma_ho: x for x in theo_doi.tong_hop(self.con, ds_ma_ho, tinh_pa=False)}
        ten_dot = {d.id: d.ten for d in ds_dot(self.con)}
        return so_thua, tt, th, ten_dot

    @staticmethod
    def _dong_ho(i: int, h: dict, so_lieu: tuple) -> dict:
        """Một dòng danh sách hộ (BangHo) từ kết quả đối chiếu h của hộ và số liệu _so_lieu_dong."""
        from .man_hinh_theo_doi import VANG as MAU_VANG, XANH as MAU_XANH
        from .quan_ly import TRUONG_TT
        so_thua, tt, th, ten_dot = so_lieu
        st, dt = so_thua.get(h['ma_ho'], (0, D(0)))
        x = tt.get(h['ma_ho'], {})
        t = th.get(h['ma_ho'])
        if t is not None:
            t.tong_pa = h['tong']
            trang_thai = t.trang_thai
            goi_y = '\n'.join([f'QĐ {q["so_qd"]} ({q["ngay_qd"]}): {vn(q["so_tien"]) if q["so_tien"] else "?"} đ - '
                               + (f'đã nhận {q["chi_tra_ngay"]}' if q['da_chi_tra'] else 'chưa nhận') for q in t.qd]
                              + [f'Bàn giao: {t.ban_giao_ngay or "đã"}' if t.da_ban_giao else '',
                                 f'Đợt trình: {ten_dot[x["dot_id"]]}' if x.get('dot_id') in ten_dot else '']).strip()
            mau = MAU_XANH if t.da_ban_giao else (MAU_VANG if t.qd else None)
            if t.qd and t.qd_chua_nhan and len(t.qd_chua_nhan) == len(t.qd):
                mau = None
        else:
            trang_thai, goi_y, mau = x.get('trang_thai', ''), '', None
        return dict(ma_ho=h['ma_ho'], tong=h['tong'], lech=h['lech'], **{k: x.get(k) for k in TRUONG_TT},
                    dot_id=x.get('dot_id'), goi_y_tt=goi_y, mau_tt=mau,
                    tim=f'{h["ma_ho"]} {x.get("theo_doi") or ""} {ten_dot.get(x.get("dot_id"), "")} '
                        f'{x.get("qd_so") or ""}',
                    o=[i, h['ho_ten'], x.get('dia_chi') or '', st, dt.quantize(D('0.1')), trang_thai])

    def _tai_lai_toan_bo(self):
        from . import doi_chieu
        self.kq = doi_chieu.doi_chieu(self.con)
        so_lieu = self._so_lieu_dong()
        self.mo_hinh.dat_du_lieu([self._dong_ho(i, h, so_lieu) for i, h in enumerate(self.kq.ho, start=1)])
        self._nap_ds_dot(so_lieu[3])
        dau = self.bang.horizontalHeader()
        dau.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.bang.resizeColumnsToContents()
        self.bang.setColumnWidth(1, min(max(int(self.bang.columnWidth(1)), 240), 340))   # họ tên dài: xem đủ khi rê chuột
        self.bang.setColumnWidth(2, min(max(int(self.bang.columnWidth(2)), 240), 420))   # địa chỉ
        self.bang.setColumnWidth(5, max(int(self.bang.columnWidth(5)), 220))              # trạng thái
        dau.setStretchLastSection(True)
        self._vua_tieu_de()
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
        if not giu_trang or self.trang.currentIndex() == 0:
            self.bang_tong_hop.nap()
            self.tien_do.nap()
        elif self.trang.currentIndex() == 1:
            self.tien_do.nap()
            self.bang_tong_hop._can_nap = {0, 1, 2} - {self.bang_tong_hop.tab.currentIndex()}
        else:
            self.bang_tong_hop.nap()
        self._cap_nhat_the_so()
        self._dem_loc()
        da = self.con.execute('SELECT * FROM du_an WHERE id = 1').fetchone()
        # một dòng (trước 0.9.18: 2 dòng, nhắc lại số hộ / đã lập / tổng tiền đã có ở hàng thẻ số liệu ngay bên dưới)
        self.lb_du_an.setText(f'<b>{da["ten"]}</b>  ·  {da["cap_dia_ban"]} {da["ten_dia_ban"]}  ·  file {self.file.name}')
        self.lb_du_an.setToolTip(str(self.file))
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
                           'xem từng dòng lệch: Dự án → Đối chiếu với file Excel…')
        self.dat_tieu_de()

    # ------------------------------------------------ lọc danh sách
    def _nap_ds_dot(self, ten_dot: dict):
        cu = self.cb_dot.currentData()
        self.cb_dot.blockSignals(True)
        self.cb_dot.clear()
        self.cb_dot.addItem('Tất cả đợt', '')
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

    def _dem_loc(self):
        n = self.loc.rowCount()
        tong = sum((self.mo_hinh.dong[self.loc.mapToSource(self.loc.index(r, 0)).row()]['tong'] for r in range(n)), D(0))
        self.lb_loc.setText(f'{n}/{len(self.mo_hinh.dong)} hộ · {vn(tong)} đ' if self.mo_hinh.dong else '')

    def ho_dang_loc(self) -> list:
        """Mã hộ đang hiện trong danh sách (sau lọc), theo thứ tự đang sắp."""
        return [self.mo_hinh.dong[self.loc.mapToSource(self.loc.index(r, 0)).row()]['ma_ho'] for r in range(self.loc.rowCount())]

    def _khung_dang_xem(self):
        """Trang bên phải đang xem có bảng hộ riêng (Tổng quát, Quyết định, Tổng hợp tiền, Tiến độ); None = danh sách hộ."""
        i = self.trang.currentIndex() if hasattr(self, 'trang') else 0
        if i == 1:
            return self.bang_tong_hop.tab.currentWidget()
        if i == 2:
            return self.tien_do
        return None

    def ho_da_chon(self) -> list:
        """Hộ đang chọn TRÊN TRANG ĐANG XEM (trước 0.9.18 luôn lấy ở danh sách hộ - đang ở trang Tiến độ chọn hộ rồi bấm
        "Trạng thái hộ…" ở menu trái thì phần mềm lấy hộ của danh sách đang ẩn)."""
        k = self._khung_dang_xem()
        if k is not None and hasattr(k, 'ma_da_chon'):
            return sorted(k.ma_da_chon())
        if self.bang.selectionModel() is None:
            return []
        return sorted({self.mo_hinh.dong[self.loc.mapToSource(i).row()]['ma_ho'] for i in self.bang.selectionModel().selectedRows()})

    def mo_ta_loc(self) -> str:
        t = [x for x in (self.cb_dot.currentText() if self.cb_dot.currentData() else '',
                         self.cb_tt.currentText() if self.cb_tt.currentData() else '',
                         f'tìm "{self.o_tim.text()}"' if self.o_tim.text().strip() else '') if x]
        return ', '.join(t)

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
    THE_SO = [('so_ho', 'Số hộ'), ('da_pa', 'Đã lập phương án'), ('tong', 'Tổng kinh phí (đồng)'), ('da_pd', 'Đã phê duyệt'),
              ('da_ct', 'Đã chi trả'), ('da_bg', 'Đã bàn giao mặt bằng')]

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

    def _hang_the_so(self) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setSpacing(10)
        self.the_so = {}
        for k, ten in self.THE_SO:
            khung = QWidget()
            khung.setObjectName('the_so')
            khung.setProperty('vai', 'the_so')
            khung.setProperty('the', k)
            khung.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)    # QWidget thường: cần để QSS vẽ nền / viền
            o = QVBoxLayout(khung)
            o.setContentsMargins(12, 7, 12, 7)
            o.setSpacing(1)
            so = QLabel('–')
            so.setProperty('vai', 'so_the')
            nhan = QLabel(ten)
            nhan.setProperty('vai', 'nhan_the')
            o.addWidget(so)
            o.addWidget(nhan)
            self.the_so[k] = so
            h.addWidget(khung, 1)
        return h

    def _cap_nhat_the_so(self):
        ds = self.mo_hinh.dong
        tong = sum((d['tong'] for d in ds), D(0))
        # "đã lập" không tính phương án phần mềm tự lập lúc tạo Dự án mới mà chưa mở soát (in_an.phan_loai_lap)
        lap = {}
        if ds and self.con is not None:
            try:
                lap = lap_pa.phan_loai_lap(self.con, {d['ma_ho']: d['tong'] > 0 for d in ds})
            except Exception:                           # file chỉ xem phiên bản cũ...: đếm như trước
                lap = {}
        da_pa = sum(1 for v in lap.values() if v == 'da_lap') if lap else sum(1 for d in ds if d['tong'] > 0)
        tu_lap = sum(1 for v in lap.values() if v == 'tu_lap')
        if 'da_pa' in self.the_so:
            self.the_so['da_pa'].setToolTip(f'{tu_lap} hộ có phương án phần mềm tự lập, chưa mở soát và lưu' if tu_lap else '')
        gt = dict(so_ho=len(ds), da_pa=da_pa, tong=vn(tong) if ds else '–',
                  da_pd=sum(1 for d in ds if d.get('da_phe_duyet')), da_ct=sum(1 for d in ds if d.get('da_chi_tra')),
                  da_bg=sum(1 for d in ds if d.get('da_ban_giao')))
        for k, o in self.the_so.items():
            v = gt[k]
            o.setText(str(v) if ds else '–')
            if k in ('da_pa', 'da_pd', 'da_ct', 'da_bg') and ds:
                o.setText(f'{v} / {len(ds)}')

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

    def don_hop_da_dong(self) -> int:
        """Hộp thoại tạo với cha là cửa sổ chính / trang bên phải không tự xóa khi đóng: mở cửa sổ lập phương án 20 lần để lại
        20 cửa sổ ẩn (~5.800 thành phần, giữ kết nối dự án cũ) - dùng cả ngày phần mềm nặng dần. Gọi khi lệnh đã chạy xong
        (không còn mã nào dùng các hộp đó); còn hộp đang mở (lệnh gọi từ bên trong hộp khác) thì để lần sau."""
        if QApplication.activeModalWidget() is not None:
            return 0
        an = [h for h in self.findChildren(QDialog) if not h.isVisible()]
        for h in an:
            h.deleteLater()
        return len(an)

    def _menu_ho(self, view, pos):
        idx = view.indexAt(pos)
        if self.con is None or not idx.isValid():
            return
        if view.currentIndex().row() != idx.row():     # chuột phải lên dòng khác dòng đang chọn: thao tác trên dòng đó
            view.setCurrentIndex(idx)
        from PySide6.QtWidgets import QMenu
        m = QMenu(self)
        # lệnh của menu trái dùng lại đúng QAction (cùng tên, cùng trạng thái bật / tắt khi chỉ xem); chỉ "Xem chi tiết tính
        # tiền…" là riêng của chuột phải
        m.addAction(self.lenh['Lập phương án hộ…'])
        m.addAction('Xem chi tiết tính tiền…', lambda: self._chay_lenh(self.xem_chi_tiet_tinh))
        m.addSeparator()
        for ten in ('Trạng thái hộ…', 'Đợt trình…', 'In / Xuất…', None, 'Xóa hộ…'):
            if ten is None:
                m.addSeparator()
            else:
                m.addAction(self.lenh[ten])
        m.exec(view.viewport().mapToGlobal(pos))
        m.deleteLater()

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
        if not viec:
            self.statusBar().showMessage('Không còn thao tác để ' + ('làm lại.' if lam_lai else 'hoàn tác.'), 4000)
            return ''
        self.dm = lap_pa.DanhMuc(self.con) if 'đơn giá' in viec.lower() or 'danh mục' in viec.lower() else self.dm
        self.tai_lai()
        self.statusBar().showMessage(f'{"Đã làm lại" if lam_lai else "Đã hoàn tác"}: {viec}', 8000)
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
            b = self.nut_ht[k]
            b.setEnabled(bool(co))
            b.setToolTip((f'{"Làm lại" if k == "toi" else "Hoàn tác"}: {ten}  ({phim})') if co else
                         ('Chưa có thao tác để ' + ('làm lại' if k == 'toi' else 'hoàn tác')))

    def mo_trang(self, i: int):
        """Trang bên phải: 0 danh sách hộ, 1-3 các thẻ của Bảng tổng hợp, 4 theo dõi tiến độ."""
        self.trang.setCurrentIndex(0 if i == 0 else 1 if i <= 3 else 2)
        if 1 <= i <= 3:
            self.bang_tong_hop.mo_the(i - 1)            # -> the_da_doi -> _danh_dau_trang
        self._danh_dau_trang(i)

    def _danh_dau_trang(self, i: int):
        """Tiêu đề trang bên phải và dấu chọn ở menu trái theo trang i (gọi cả khi bấm thẳng thẻ của Bảng tổng hợp)."""
        self.lb_trang.setText(TRANG[i].upper() + ('  ·  ◀ bấm "Danh sách hộ" ở menu trái để quay lại' if i else ''))
        self.lb_trang.setVisible(i != 0)
        for k, t in enumerate(TRANG):
            self.lenh[t].setChecked(k == i)

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
        from .man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, ma_ho, self, self.dm)
        if the is not None:
            w.tab.setCurrentIndex(the)
        if not cho:
            return w
        truoc = self.con.total_changes if truoc is None else truoc
        w.exec()
        if self.con.total_changes != truoc:             # chỉ xem, không ghi gì: khỏi tải lại cả dự án (3.000 hộ ~1 giây)
            self.tai_lai()
        if w.ho_so.canh_bao:
            self.statusBar().showMessage('Lưu ý: ' + '; '.join(w.ho_so.canh_bao), 15000)
        return w

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
                   '\n\nXóa nhầm: bấm "Hoàn tác" trên băng tiêu đề (Ctrl+Z) để lấy lại.')
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

    def in_xuat(self, cho: bool = True):
        if self.con is None:
            QMessageBox.information(self, TEN_UD, 'Hãy nhập hoặc mở một dự án trước.')
            return None
        from .man_hinh import HopIn
        chon = sorted({self.mo_hinh.dong[self.loc.mapToSource(i).row()]['ma_ho']
                       for i in self.bang.selectionModel().selectedRows()}) if self.bang.selectionModel() else []
        dlg = HopIn(self.con, self, ma_ho_chon=chon, file_du_an=self.file)
        if cho:
            dlg.exec()
        return dlg

    def cap_nhat_mau_in(self, file_excel=None, ten_mau: str | None = None, loai: str | None = None, cho: bool = True):
        """Thêm / thay mẫu in từ file Excel: file PABT Excel (sheet IN_CHITIET và / hoặc IN_BANGTONGHOP) hoặc file mẫu đã sửa
        sẵn (một sheet, có chỗ trống {…}). ten_mau '' = thay mẫu chính, có tên = thêm mẫu riêng (chọn ở In / Xuất), None = hỏi."""
        from . import in_an
        if file_excel is None:
            file_excel, _ = QFileDialog.getOpenFileName(self, 'Chọn file mẫu in (file PABT Excel hoặc mẫu đã sửa)', '',
                                                        'File Excel (*.xlsx *.xlsm)')
            if not file_excel:
                return None
        if ten_mau is None:
            hop = QMessageBox(QMessageBox.Icon.Question, TEN_UD,
                              f'Dùng file {Path(file_excel).name} làm:\n\n'
                              '- Mẫu chính: thay mẫu đang in (mẫu cũ được giữ trong thư mục mau_in\\cu).\n'
                              '- Mẫu riêng: thêm một mẫu có tên (ví dụ "Dự thảo"), chọn được khi In / Xuất; mẫu chính giữ nguyên.',
                              parent=self)
            b_chinh = hop.addButton('Thay mẫu chính', QMessageBox.ButtonRole.AcceptRole)
            b_rieng = hop.addButton('Thêm mẫu riêng…', QMessageBox.ButtonRole.AcceptRole)
            hop.addButton('Hủy', QMessageBox.ButtonRole.RejectRole)
            hop.exec()
            if hop.clickedButton() is b_chinh:
                ten_mau = ''
            elif hop.clickedButton() is b_rieng:
                import re
                from PySide6.QtWidgets import QInputDialog
                goi_y = re.sub(r'^(IN_CHITIET|IN_BANGTONGHOP)[_ -]*', '', Path(file_excel).stem, flags=re.I) or 'Mẫu 2'
                ten_mau, ok = QInputDialog.getText(self, TEN_UD, 'Tên mẫu riêng (hiện ở ô chọn mẫu khi In / Xuất):', text=goi_y)
                if not ok or not in_an.ten_mau_hop_le(ten_mau):
                    return None
            else:
                return None
        try:
            in_an.mau_de_sua()                          # bản cài: chép mẫu đang dùng sang thư mục ghi (đổi một mẫu, giữ mẫu kia)
            try:
                ds = in_an.tao_mau_tu_excel(file_excel, in_an.thu_muc_mau_ghi(), loai=loai, ten_mau=ten_mau)
            except in_an.LoiChuaRoMau:
                if not cho:
                    raise
                hop = QMessageBox(QMessageBox.Icon.Question, TEN_UD, f'File {Path(file_excel).name} là mẫu in nào?', parent=self)
                b_ct = hop.addButton('Phương án chi tiết từng hộ', QMessageBox.ButtonRole.AcceptRole)
                b_bth = hop.addButton('Bảng tổng hợp', QMessageBox.ButtonRole.AcceptRole)
                hop.addButton('Hủy', QMessageBox.ButtonRole.RejectRole)
                hop.exec()
                if hop.clickedButton() not in (b_ct, b_bth):
                    return None
                ds = in_an.tao_mau_tu_excel(file_excel, in_an.thu_muc_mau_ghi(),
                                            loai=in_an.TEN_CT if hop.clickedButton() is b_ct else in_an.TEN_BTH, ten_mau=ten_mau)
        except (in_an.LoiIn, OSError, KeyError) as e:
            if cho:
                QMessageBox.warning(self, TEN_UD, chu_loi('Không lấy được mẫu in', e))
                return None
            raise
        if cho:
            QMessageBox.information(self, TEN_UD, ('Đã thêm mẫu riêng "' + in_an.ten_mau_hop_le(ten_mau) + '"' if ten_mau else
                                                   'Đã cập nhật mẫu in chính') + ':\n' + '\n'.join(str(p) for p in ds))
        return ds

    def du_an_moi(self, cho: bool = True):
        """Dự án mới từ dữ liệu thô: 4 bước, tự lập phương án, xuất 2 bảng in; xong thì mở dự án."""
        from .man_hinh_du_an_moi import HopDuAnMoi
        dlg = HopDuAnMoi(self)
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
            tb += f'\n\nĐã xuất {len(kq["in"]["excel"])} file Excel' + (f', {len(kq["in"]["pdf"])} file PDF' if kq['in']['pdf'] else '') \
                  + f' vào:\n{kq["thu_muc_in"]}'
        from .giao_dien import hop_ket_qua                  # ô cuộn: đủ mọi điểm cần xem lại, nút Đóng luôn trong màn hình
        hop_ket_qua(self, tb, kq['canh_bao'], tieu_de=TEN_UD)

    def bo_don_gia(self, cho: bool = True):
        from .man_hinh_don_gia import HopBoDonGia
        dlg = HopBoDonGia(self, self.con, self.chi_doc)
        if not cho:
            return dlg
        dlg.exec()
        if dlg.da_ap and self.con is not None:
            self.dm = lap_pa.DanhMuc(self.con)
            self.tai_lai()
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
            dich, _ = QFileDialog.getSaveFileName(self, 'Lưu dự án thành', mac_dinh, 'Dự án PABT (*.pabt)')
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

    def bao_cao_tong_hop(self, file=None):
        """Báo cáo tổng hợp (Excel) các hộ đang hiện theo bộ lọc (đợt, trạng thái, từ khóa)."""
        if not self._can_du_an():
            return None
        from . import quan_ly
        ds = self.ho_dang_loc()
        if not ds:
            QMessageBox.information(self, TEN_UD, 'Không có hộ nào theo bộ lọc hiện tại.')
            return None
        if file is None:
            goc = quan_ly.thu_muc_ho_so(self.con, self.file)
            mac_dinh = str((goc if goc.exists() else self.file.parent) / f'BaoCaoTongHop_{self.file.stem}.xlsx')
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu báo cáo tổng hợp', mac_dinh, 'File Excel (*.xlsx)')
            if not file:
                return None
        try:
            with con_tro_cho():
                # số liệu đọc ở đây (kết quả tính dùng chung), ghi Excel ở luồng nền: hàng nghìn hộ không "Không phản hồi"
                so_lieu = quan_ly.du_lieu_bao_cao(self.con, ds)
                dk = self.mo_ta_loc()
                from .giao_dien import chay_nen
                p = chay_nen(self, lambda: quan_ly.ghi_bao_cao_tong_hop(so_lieu, file, dieu_kien=dk),
                             f'Đang ghi báo cáo tổng hợp {len(ds)} hộ…')
        except OSError as e:
            QMessageBox.warning(self, TEN_UD, chu_loi('Không ghi được file', e))
            return None
        if QMessageBox.question(self, TEN_UD, f'Đã lưu báo cáo {len(ds)} hộ:\n{p}\n\nMở file?') == QMessageBox.StandardButton.Yes:
            from .in_an import mo_file
            mo_file(p)
        return p

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
        from .man_hinh_du_toan import HopDuToan
        dlg = HopDuToan(self, self.con, self.file)
        if cho:
            dlg.exec()
        return dlg

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
        from . import to_chuc
        from .cap_nhat import ban_goc
        goc = ban_goc()
        pb = f'Phiên bản {__version__}' + (f' (bản cập nhật, bản cài gốc {goc})' if goc != __version__ else '') + \
            (f' - {NHAN_THU_NGHIEM}' if BAN_THU_NGHIEM else '') + '.'
        QMessageBox.about(self, TEN_UD, f'{TEN_UD}\n{pb}\n{to_chuc.TAC_GIA}.')

    # ------------------------------------------------ máy chủ LAN, tài khoản
    def dat_tieu_de(self):
        t = TIEU_DE_CUA_SO
        if self.file is not None:
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
        p = may_chu.PHIEN
        if p is not None:
            self.nut_tk.setText(f'Tài khoản: {p.ten_hien}')
            self.nut_tk.setToolTip(f'Đăng nhập máy chủ {p.goc}')
        elif may_chu.doc_cau_hinh().get('may_chu'):
            self.nut_tk.setText('Offline · Đăng nhập máy chủ')
            self.nut_tk.setToolTip('Đang làm việc offline với file trên máy này')
        else:
            self.nut_tk.setText('Máy chủ LAN')
            self.nut_tk.setToolTip('Thiết lập máy chủ trong mạng nội bộ, tài khoản đăng nhập (không bắt buộc)')
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
        self.lb_du_an.setText(CHUA_MO)
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
        from .giao_dien import KHI_DOI_TY_LE, XU_LY_HOAN_TAC
        if self._hien_ty_le in KHI_DOI_TY_LE:
            KHI_DOI_TY_LE.remove(self._hien_ty_le)
        if self.hoan_tac_phim in XU_LY_HOAN_TAC:
            XU_LY_HOAN_TAC.remove(self.hoan_tac_phim)
        self.dong_du_an()
        if may_chu.PHIEN is not None:                   # ghi "Đăng xuất" lên máy chủ: chờ tối đa 3 giây (mất mạng không treo lúc đóng)
            import threading
            t = threading.Thread(target=may_chu.dang_xuat, daemon=True)
            t.start()
            t.join(3)
        super().closeEvent(e)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName('PABT')
    from .giao_dien import ap_dung, cai_bat_loi
    ap_dung(app)
    cai_bat_loi()                                      # lỗi trong nút bấm: báo + ghi loi.log (trước đây mất im lặng)
    menu_trai = '--menu-tren' not in sys.argv              # từ 0.9.3: menu dọc bên trái thay thanh nút phía trên
    w = CuaSoChinh(menu_trai=menu_trai)
    w.dat_tieu_de()
    tep = [a for a in sys.argv[1:] if not a.startswith('--')]
    co_file = bool(tep and tep[0].lower().endswith('.pabt'))
    w.showMaximized()                      # dùng hết màn hình: thanh nút gọn 2 dòng, danh sách hộ rộng
    w.khoi_dong_may_chu(mo_lai=not co_file)   # máy chủ LAN (nếu có thiết lập): đăng nhập, mở lại dự án đang làm
    if co_file:
        w.mo(tep[0])
    try:
        import nap_cap_nhat
        QTimer.singleShot(5000, nap_cap_nhat.khoi_dong_tot)
    except ImportError:
        pass
    if tep and tep[0].lower().endswith('.pabtcn'):                          # nhấp đúp gói cập nhật
        QTimer.singleShot(0, lambda: w.cap_nhat_phan_mem(tep[0]))
    return app.exec()

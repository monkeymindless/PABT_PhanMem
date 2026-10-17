"""Bảng chỉ đọc cho danh sách lớn (hàng nghìn hộ / thửa): QTableView trên mô hình ảo.

QTableWidget giữ MỘT đối tượng QTableWidgetItem cho mỗi ô và phải dựng hết trước khi hiện: trang "Thông tin tổng quát hộ" của dự
án 10.000 thửa = 110.000 ô, mỗi lần nạp / gõ tìm ~0,9 giây (dựng ô ~0,5 s + resizeRowsToContents đo chữ mọi dòng ~0,3 s).
BangAo chỉ giữ danh sách chuỗi; Qt hỏi dữ liệu (data()) cho CÁC Ô ĐANG HIỆN (~40 dòng) - vẽ lại gần như không phụ thuộc cỡ dự án.

API giống phần QTableWidget mà các trang đang dùng (rowCount, columnCount, item(r, c).text() / .data(UserRole), tín hiệu
cellDoubleClicked(r, c)) để mã gọi và kiểm thử cũ không phải đổi.

Sắp xếp (sap_xep=True, bấm tiêu đề cột): theo GIÁ TRỊ từng ô truyền ở `khoa` (Decimal, int, chuỗi), không theo chuỗi hiển thị
- QTableWidget sắp cột tiền theo chữ ("9.000" đứng sau "10.000.000"). Ô trống (None) luôn ở cuối. Bảng có gộp ô không sắp xếp.
"""
from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView

DO_MAU = 300                    # số dòng Qt đo khi tự canh bề rộng cột
SO_DONG_CHU_TOI_DA = 6          # ô chữ dài: dòng bảng cao tối đa bấy nhiêu dòng chữ (đủ chữ xem ở chú thích khi rê chuột)
DU_RONG = 1.15                  # chữ xuống dòng theo từ: ước dài hơn số ký tự trung bình chút ít cho khỏi thiếu dòng
GOI_Y_TU = 15                   # ô có chữ dài hơn bấy nhiêu ký tự: chú thích (tooltip) = nội dung ô
_PHAI = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
_TRAI = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
_HIEN, _CAN, _DU_LIEU = Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.TextAlignmentRole, Qt.ItemDataRole.UserRole
_NEN, _MAU_CHU, _CHU, _GOI_Y = (Qt.ItemDataRole.BackgroundRole, Qt.ItemDataRole.ForegroundRole, Qt.ItemDataRole.FontRole,
                                Qt.ItemDataRole.ToolTipRole)
# 1.0.03 "làm mờ số 0 - tôn vinh số thực": ô có giá trị bằng 0 / gạch chữ xám nhạt (mắt lướt qua khoản trống); ô số của cột tổng /
# thành tiền chữ navy đậm. Chỉ ô chưa có màu chữ riêng (kieu['mau_chu'])
SO_KHONG = frozenset(('0', '0,0', '0,00', '0,0%', '0.0%', '0%', '-', '—'))
MAU_SO_KHONG = '#94A3B8'
MAU_SO_TIEN = '#0F3866'
_BUT_SO_KHONG = QBrush(QColor(MAU_SO_KHONG))
_BUT_SO_TIEN = QBrush(QColor(MAU_SO_TIEN))


def la_cot_tien(tieu_de: str) -> bool:
    """Cột tổng / thành tiền (chữ navy cho số khác 0)."""
    t = (tieu_de or '').casefold()
    return 'tổng' in t or 'thành tiền' in t


class _MoHinhAo(QAbstractTableModel):
    def __init__(self, cot: list, can_phai: set, parent=None):
        super().__init__(parent)
        self.cot, self.can_phai = list(cot), set(can_phai)
        self.cot_tien = {c for c, t in enumerate(self.cot) if la_cot_tien(t)}
        self.dong: list = []            # [[chuỗi hiển thị của từng cột]]
        self.du_lieu: list = []         # giá trị UserRole của từng dòng (mã hộ...)
        self.kieu: dict = {}            # {(dòng, cột): dict(nen=QColor, mau_chu=QColor, dam=True, goi_y=str)} - chỉ ô có kiểu riêng
        self.khoa: list = []            # [[giá trị sắp xếp của từng cột]] - rỗng: bảng không sắp xếp
        self._sap = None                # (cột, thứ tự) người dùng đã chọn: giữ khi nạp lại dữ liệu
        self._dam = QFont()
        self._dam.setBold(True)

    def dat(self, dong: list, du_lieu: list, kieu: dict, khoa: list | None = None) -> None:
        self.beginResetModel()           # một lần báo "đổi toàn bộ" thay cho hàng trăm nghìn setItem
        self.dong, self.du_lieu, self.kieu, self.khoa = dong, du_lieu, kieu, khoa or []
        if self._sap is not None and self.khoa:
            self._sap_xep(*self._sap)
        self.endResetModel()

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        if not self.khoa or not 0 <= column < len(self.cot):
            return
        self.beginResetModel()
        self._sap = (column, order)
        self._sap_xep(column, order)
        self.endResetModel()

    def _sap_xep(self, c: int, order) -> None:
        k = self.khoa
        co = [r for r in range(len(k)) if k[r][c] is not None]
        co.sort(key=lambda r: k[r][c].casefold() if isinstance(k[r][c], str) else k[r][c],
                reverse=order == Qt.SortOrder.DescendingOrder)
        thu_tu = co + [r for r in range(len(k)) if k[r][c] is None]
        moi = {cu: i for i, cu in enumerate(thu_tu)}
        self.dong = [self.dong[r] for r in thu_tu]
        self.khoa = [k[r] for r in thu_tu]
        if self.du_lieu:
            self.du_lieu = [self.du_lieu[r] for r in thu_tu]
        self.kieu = {(moi[r], cot): v for (r, cot), v in self.kieu.items()}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.dong)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.cot)

    def data(self, idx, role=_HIEN):
        r, c = idx.row(), idx.column()
        if role == _HIEN:
            return self.dong[r][c]
        if role == _CAN:
            return _PHAI if c in self.can_phai else _TRAI
        if role == _DU_LIEU:
            return self.du_lieu[r] if r < len(self.du_lieu) else None
        k = self.kieu.get((r, c))
        if role == _GOI_Y:
            if k and k.get('goi_y'):
                return k['goi_y']
            v = self.dong[r][c]
            return v if len(v) > GOI_Y_TU else None
        if role == _MAU_CHU:
            if k is not None and k.get('mau_chu') is not None:
                return QBrush(k['mau_chu'])
            v = self.dong[r][c].strip()
            if v in SO_KHONG:
                return _BUT_SO_KHONG
            if c in self.cot_tien and v and (v[0].isdigit() or v[0] == '-'):
                return _BUT_SO_TIEN
            return None
        if k is None:
            return None
        if role == _NEN and k.get('nen') is not None:
            return QBrush(k['nen'])
        if role == _CHU and k.get('dam'):
            return self._dam
        return None

    def headerData(self, section, orientation, role=_HIEN):
        if role == _HIEN and orientation == Qt.Orientation.Horizontal and 0 <= section < len(self.cot):
            return self.cot[section]
        return None


class _OAo:
    """Ô của BangAo trả về bởi item(r, c) - như QTableWidgetItem ở phần đọc (text, data)."""
    __slots__ = ('_mh', '_r', '_c')

    def __init__(self, mh: _MoHinhAo, r: int, c: int):
        self._mh, self._r, self._c = mh, r, c

    def text(self) -> str:
        return self._mh.dong[self._r][self._c]

    def data(self, role):
        return self._mh.data(self._mh.index(self._r, self._c), role)

    def row(self) -> int:
        return self._r

    def column(self) -> int:
        return self._c


class BangAo(QTableView):
    """Bảng chỉ đọc chọn theo dòng, chạy trên mô hình ảo. dat_du_lieu(dòng, dữ liệu dòng, kiểu ô, gộp ô) thay cho setRowCount +
    setItem từng ô."""
    cellDoubleClicked = Signal(int, int)

    def __init__(self, cot: list, can_phai=(), parent=None, sap_xep: bool = False, tu_cao: bool = True):
        super().__init__(parent)
        self.tu_cao = tu_cao             # False: bảng không có chữ xuống dòng - không đo chiều cao dòng
        self.mo_hinh = _MoHinhAo(cot, set(can_phai), self)
        self.setModel(self.mo_hinh)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setWordWrap(True)
        self.verticalHeader().setVisible(False)
        dau = self.horizontalHeader()
        dau.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        dau.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        dau.setStretchLastSection(True)
        dau.setMinimumHeight(46)                         # tiêu đề 2 dòng
        dau.setResizeContentsPrecision(DO_MAU)           # resizeColumnsToContents: đo mẫu, không đo hết hàng nghìn dòng
        if sap_xep:
            dau.setSortIndicator(0, Qt.SortOrder.AscendingOrder)    # mặc định Qt: cột 0 GIẢM dần (STT ngược)
            self.setSortingEnabled(True)
        self.doubleClicked.connect(lambda i: self.cellDoubleClicked.emit(i.row(), i.column()))

    def dat_du_lieu(self, dong: list, du_lieu: list | None = None, kieu: dict | None = None, gop=(),
                    khoa: list | None = None) -> None:
        """dong: [[chuỗi]] mỗi dòng đủ số cột; du_lieu: giá trị UserRole của từng dòng; kieu: {(r, c): dict(nen, mau_chu, dam,
        goi_y)}; gop: [(dòng, số dòng, [cột...])] - gộp ô thông tin hộ trên các dòng thửa; khoa: giá trị sắp xếp từng ô
        (bảng sap_xep=True)."""
        self.clearSpans()
        self.mo_hinh.dat(dong, du_lieu or [], kieu or {}, khoa)
        for r, n, cot in gop:
            if n > 1:
                for c in cot:
                    self.setSpan(r, c, n, 1)
        if self.tu_cao:
            self._vua_dong(dong)

    def _vua_dong(self, dong: list) -> None:
        """Dòng cao theo chữ: ƯỚC số dòng chữ của ô (dòng "\\n" + chữ dài / số ký tự vừa cột) rồi đặt chiều cao - chỉ các dòng
        cần cao hơn mặc định (đặt lại mô hình = mọi dòng về mặc định). Trước 0.9.22 Qt đo từng ô (resizeRowsToContents, ~105 lần
        hỏi dữ liệu mỗi dòng): trang Tiến độ lọc còn 1.500 hộ mất 0,33 s mỗi lần đổi bộ lọc, bảng > 2.000 dòng phải bỏ không đo."""
        fm = self.fontMetrics()
        tb = max(1, fm.averageCharWidth())
        vua = [max(1, int((self.columnWidth(c) - 10) / (tb * DU_RONG))) for c in range(len(self.mo_hinh.cot))]  # ký tự / dòng
        cao_chu, mac_dinh = fm.lineSpacing(), self.verticalHeader().defaultSectionSize()
        dat = self.verticalHeader().resizeSection
        for r, o in enumerate(dong):
            n = 1
            for t, v in zip(o, vua):
                if len(t) > v or '\n' in t:
                    n = max(n, sum(-(-len(d) // v) or 1 for d in t.split('\n')))
            if n > 1:
                dat(r, max(mac_dinh, min(n, SO_DONG_CHU_TOI_DA) * cao_chu + 8))

    def ma_dong(self, r: int):
        """Giá trị UserRole (mã hộ) của dòng r."""
        dl = self.mo_hinh.du_lieu
        return dl[r] if 0 <= r < len(dl) else None

    def ma_da_chon(self) -> list:
        """Mã của các dòng đang chọn (không trùng, theo thứ tự dòng)."""
        sm = self.selectionModel()
        ds = []
        for r in sorted(i.row() for i in sm.selectedRows()) if sm is not None else []:
            m = self.ma_dong(r)
            if m is not None and m not in ds:
                ds.append(m)
        return ds

    # ---- tương thích QTableWidget (phần đọc)
    def currentRow(self) -> int:
        return self.currentIndex().row()

    def rowCount(self) -> int:
        return self.mo_hinh.rowCount()

    def columnCount(self) -> int:
        return self.mo_hinh.columnCount()

    def item(self, r: int, c: int):
        return _OAo(self.mo_hinh, r, c) if 0 <= r < self.rowCount() and 0 <= c < self.columnCount() else None

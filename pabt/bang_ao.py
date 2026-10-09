"""Bảng chỉ đọc cho danh sách lớn (hàng nghìn hộ / thửa): QTableView trên mô hình ảo.

QTableWidget giữ MỘT đối tượng QTableWidgetItem cho mỗi ô và phải dựng hết trước khi hiện: trang "Thông tin tổng quát hộ" của dự
án 10.000 thửa = 110.000 ô, mỗi lần nạp / gõ tìm ~0,9 giây (dựng ô ~0,5 s + resizeRowsToContents đo chữ mọi dòng ~0,3 s).
BangAo chỉ giữ danh sách chuỗi; Qt hỏi dữ liệu (data()) cho CÁC Ô ĐANG HIỆN (~40 dòng) - vẽ lại gần như không phụ thuộc cỡ dự án.

API giống phần QTableWidget mà các trang đang dùng (rowCount, columnCount, item(r, c).text() / .data(UserRole), tín hiệu
cellDoubleClicked(r, c)) để mã gọi và kiểm thử cũ không phải đổi.
"""
from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QBrush, QFont
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView

DONG_TU_CAO_TOI_DA = 2000       # bảng nhiều dòng hơn: không đo chiều cao từng dòng (chữ dài xem ở chú thích khi rê chuột)
GOI_Y_TU = 15                   # ô có chữ dài hơn bấy nhiêu ký tự: chú thích (tooltip) = nội dung ô
_PHAI = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
_TRAI = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
_HIEN, _CAN, _DU_LIEU = Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.TextAlignmentRole, Qt.ItemDataRole.UserRole
_NEN, _MAU_CHU, _CHU, _GOI_Y = (Qt.ItemDataRole.BackgroundRole, Qt.ItemDataRole.ForegroundRole, Qt.ItemDataRole.FontRole,
                                Qt.ItemDataRole.ToolTipRole)


class _MoHinhAo(QAbstractTableModel):
    def __init__(self, cot: list, can_phai: set, parent=None):
        super().__init__(parent)
        self.cot, self.can_phai = list(cot), set(can_phai)
        self.dong: list = []            # [[chuỗi hiển thị của từng cột]]
        self.du_lieu: list = []         # giá trị UserRole của từng dòng (mã hộ...)
        self.kieu: dict = {}            # {(dòng, cột): dict(nen=QColor, mau_chu=QColor, dam=True, goi_y=str)} - chỉ ô có kiểu riêng
        self._dam = QFont()
        self._dam.setBold(True)

    def dat(self, dong: list, du_lieu: list, kieu: dict) -> None:
        self.beginResetModel()           # một lần báo "đổi toàn bộ" thay cho hàng trăm nghìn setItem
        self.dong, self.du_lieu, self.kieu = dong, du_lieu, kieu
        self.endResetModel()

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
        if k is None:
            return None
        if role == _NEN and k.get('nen') is not None:
            return QBrush(k['nen'])
        if role == _MAU_CHU and k.get('mau_chu') is not None:
            return QBrush(k['mau_chu'])
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

    def __init__(self, cot: list, can_phai=(), parent=None):
        super().__init__(parent)
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
        self.doubleClicked.connect(lambda i: self.cellDoubleClicked.emit(i.row(), i.column()))

    def dat_du_lieu(self, dong: list, du_lieu: list | None = None, kieu: dict | None = None, gop=()) -> None:
        """dong: [[chuỗi]] mỗi dòng đủ số cột; du_lieu: giá trị UserRole của từng dòng; kieu: {(r, c): dict(nen, mau_chu, dam,
        goi_y)}; gop: [(dòng, số dòng, [cột...])] - gộp ô thông tin hộ trên các dòng thửa."""
        self.clearSpans()
        self.mo_hinh.dat(dong, du_lieu or [], kieu or {})
        for r, n, cot in gop:
            if n > 1:
                for c in cot:
                    self.setSpan(r, c, n, 1)
        if len(dong) <= DONG_TU_CAO_TOI_DA:
            self.resizeRowsToContents()              # bảng vừa: dòng cao theo chữ; bảng lớn: đo mọi dòng là O(n) - bỏ

    # ---- tương thích QTableWidget (phần đọc)
    def rowCount(self) -> int:
        return self.mo_hinh.rowCount()

    def columnCount(self) -> int:
        return self.mo_hinh.columnCount()

    def item(self, r: int, c: int):
        return _OAo(self.mo_hinh, r, c) if 0 <= r < self.rowCount() and 0 <= c < self.columnCount() else None

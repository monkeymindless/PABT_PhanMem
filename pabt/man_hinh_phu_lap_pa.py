"""Khung phụ của cửa sổ lập phương án (1.0.58, Gói 3 đề án V2.0, làm theo cách không trái quyết định cũ - nạp khi dùng lần đầu):
- KhungDsHo: ghim danh sách hộ bên trái (Ctrl+B / nút "DS hộ");
- KhungChiTietDong: chi tiết dòng đang chọn dưới bảng mục (phím Space): công thức, quy cách, căn cứ giá, ghi chú;
- HopSoSanhHo: đối chiếu phương án hai hộ, chỉ đọc."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMenu, QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from . import nghiep_vu, so_sanh_ho
from .giao_dien import TOKEN, loc_khi_ngung_go, qmau_theo_tong, vua_dong
from .lap_pa import bo_dau
from .tien import so_vn, vn

RONG_DS_HO = 230
COT_CHI_TIET = (('quy_cach', 'Quy cách'), ('can_cu_gia', 'Căn cứ giá'), ('ghi_chu', 'Ghi chú'))
CAO_GIAI_TRINH = 96


class KhungDsHo(QWidget):
    """Danh sách hộ ghim bên trái: bấm một hộ để chuyển (hỏi lưu như nút ◀ ▶); gõ để lọc không dấu."""

    def __init__(self, man):
        super().__init__(man)
        self.man = man
        self._ds = None
        self.setObjectName('khung_ds_ho')
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(4)
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Lọc hộ (không cần dấu)…')
        loc_khi_ngung_go(self.o_tim, self.loc)
        self.ds = QListWidget()
        self.ds.setUniformItemSizes(True)                # 3.000 hộ: không đo từng dòng
        self.ds.setToolTip('Bấm một hộ để chuyển sang hộ đó. Chuột phải: đối chiếu với hộ đang mở.')
        self.ds.itemClicked.connect(self._bam)
        self.ds.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ds.customContextMenuRequested.connect(self._menu)
        self.b_doi_chieu = QPushButton('Đối chiếu hai hộ…')
        self.b_doi_chieu.setToolTip('So phương án đã lưu của hộ đang mở với hộ khác: cùng tài sản khác đơn giá, khác số lượng (chỉ đọc)')
        self.b_doi_chieu.clicked.connect(lambda: self.man.doi_chieu_ho())
        lo.addWidget(self.o_tim)
        lo.addWidget(self.ds, 1)
        lo.addWidget(self.b_doi_chieu)
        self.nap()

    def nap(self) -> None:
        """Dựng danh sách khi danh sách hộ đổi (BoSoan.danh_sach_ho nhớ trên kết nối: cùng đối tượng = chưa đổi); đánh dấu hộ đang mở."""
        ds = self.man.bo.danh_sach_ho()
        if ds is not self._ds:
            self._ds = ds
            self.ds.setUpdatesEnabled(False)
            self.ds.clear()
            for ma, tt, ten in ds:
                it = QListWidgetItem(f'{tt}. {ten}')
                it.setData(Qt.ItemDataRole.UserRole, ma)
                it.setToolTip(f'{tt}. {ten}')
                self.ds.addItem(it)
            self.ds.setUpdatesEnabled(True)
            self.loc(self.o_tim.text())
        self.chon_ho_dang_mo()

    def chon_ho_dang_mo(self) -> None:
        ma = self.man.bo.ma_ho
        for i, x in enumerate(self._ds or ()):
            if x[0] == ma:
                self.ds.setCurrentRow(i)
                self.ds.scrollToItem(self.ds.item(i))
                return

    def loc(self, chu: str) -> None:
        tu = bo_dau(chu or '').split()
        self.ds.setUpdatesEnabled(False)
        for i in range(self.ds.count()):
            it = self.ds.item(i)
            k = bo_dau(it.text())
            it.setHidden(bool(tu) and not all(t in k for t in tu))
        self.ds.setUpdatesEnabled(True)

    def _bam(self, it) -> None:
        if not self.man.chuyen_ho(it.data(Qt.ItemDataRole.UserRole)):      # còn thay đổi, người dùng chọn ở lại
            self.chon_ho_dang_mo()

    def _menu(self, pos) -> None:
        it = self.ds.itemAt(pos)
        if it is None:
            return
        ma = it.data(Qt.ItemDataRole.UserRole)
        m = QMenu(self)
        a = m.addAction('Đối chiếu với hộ đang mở…', lambda: self.man.doi_chieu_ho(ma))
        a.setEnabled(ma != self.man.bo.ma_ho)
        m.exec(self.ds.viewport().mapToGlobal(pos))
        m.deleteLater()


class KhungChiTietDong(QFrame):
    """Chi tiết dòng đang chọn của một bảng mục (dưới bảng): đọc được cột phụ khi bảng ở chế độ Gọn cột, sửa ngay; ghi qua đúng ô của bảng
    (setText -> cellChanged -> CuaSoLapPA.sua_o) nên cùng kiểm tra, cùng phân quyền như sửa trực tiếp trên ô."""

    def __init__(self, bm):
        super().__init__(bm)
        self.bm = bm
        self.r = -1
        self.setObjectName('khung_chi_tiet_dong')
        self.setFrameShape(QFrame.Shape.StyledPanel)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(8, 4, 8, 4)
        lo.setSpacing(4)
        h = QHBoxLayout()
        self.lb_ten = QLabel()
        self.lb_ten.setWordWrap(True)
        self.lb_ten.setTextFormat(Qt.TextFormat.PlainText)
        h.addWidget(self.lb_ten, 1)
        self.lb_nguon = QLabel()
        self.lb_nguon.setProperty('vai', 'nhan')
        h.addWidget(self.lb_nguon)
        self.b_dong = QPushButton('Đóng')
        self.b_dong.setToolTip('Đóng khung chi tiết (phím Space trên bảng)')
        self.b_dong.clicked.connect(lambda: self.bm.bat_tat_chi_tiet(False))
        h.addWidget(self.b_dong)
        lo.addLayout(h)
        khoa = [c[0] for c in bm.cot]
        self.o = {}
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(4)
        for k, nhan in COT_CHI_TIET:
            if k in khoa:
                e = QLineEdit()
                e.editingFinished.connect(lambda k=k: self._ghi(k))
                self.o[k] = e
                form.addRow(nhan + ':', e)
        lo.addLayout(form)
        self.o_gt = QPlainTextEdit()
        self.o_gt.setReadOnly(True)
        self.o_gt.setMaximumHeight(CAO_GIAI_TRINH)
        self.o_gt.setToolTip('Công thức, thay số và căn cứ của dòng (Ctrl+I: mở hộp giải trình đầy đủ, có nút Chép)')
        lo.addWidget(self.o_gt)

    def _cot(self, k: str) -> int:
        return [c[0] for c in self.bm.cot].index(k)

    def nap(self, r: int | None = None) -> None:
        bm = self.bm
        b = bm.bang                                     # property: vẽ phần còn chờ (bảng vẽ lười)
        self.r = b.currentRow() if r is None else r
        ds = bm.man.bo.ds(bm.muc)
        co = 0 <= self.r < len(ds)
        for e in self.o.values():
            e.setEnabled(co)
        if not co:
            self.lb_ten.setText('Chọn một dòng trong bảng để xem chi tiết.')
            self.lb_nguon.setText('')
            self.o_gt.setPlainText('')
            for e in self.o.values():
                e.setText('')
            return
        gt = nghiep_vu.giai_trinh_dong_pa(bm.man.bo.pa, bm.man.bo.bc, bm.muc, self.r)
        self.lb_ten.setText(f'Dòng {nghiep_vu.so_muc(bm.muc)}.{self.r + 1}: {gt["ten_hang_muc"]} - {vn(gt["thanh_tien"])} đồng')
        self.lb_nguon.setText(f'Nguồn giá: {ds[self.r].nguon_gia}' if bm.muc != 1 else '')
        self.o_gt.setPlainText('\n'.join(gt['dong']))
        cam_sua = b.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
        for k, e in self.o.items():
            it = b.item(self.r, self._cot(k))
            if not e.hasFocus():
                e.setText(it.text() if it is not None else '')
                e.setCursorPosition(0)
            e.setReadOnly(cam_sua or it is None or not (it.flags() & Qt.ItemFlag.ItemIsEditable))

    def _ghi(self, k: str) -> None:
        e = self.o[k]
        if e.isReadOnly() or not e.isEnabled():
            return
        it = self.bm._bang.item(self.r, self._cot(k)) if self.r >= 0 else None
        chu = ' '.join(e.text().split())
        if it is not None and chu != ' '.join(it.text().split()):
            it.setText(chu)                             # cellChanged -> BangMuc._doi_o -> CuaSoLapPA.sua_o


COT_SO_SANH = ('Mục', 'Tên hạng mục', 'ĐVT', 'SL (A)', 'Đơn giá (A)', 'Thành tiền (A)', 'SL (B)', 'Đơn giá (B)', 'Thành tiền (B)', 'Khác nhau')
RONG_SO_SANH = (70, 320, 50, 70, 100, 110, 70, 100, 110, 150)


class HopSoSanhHo(QDialog):
    """Đối chiếu phương án ĐÃ LƯU của hai hộ - chỉ đọc, không chặn cửa sổ lập phương án (mở song song để vừa xem vừa sửa, bấm Đọc lại)."""

    def __init__(self, parent, con, ds_ho: list, ma_a: int, ma_b: int | None = None):
        super().__init__(parent)
        self.con = con
        self.kq = None
        self.setWindowTitle('Đối chiếu phương án hai hộ')
        self.setModal(False)
        self.resize(1180, 640)
        lo = QVBoxLayout(self)
        h = QHBoxLayout()
        self.cb_a, self.cb_b = QComboBox(), QComboBox()
        for nhan, cb in (('Hộ A:', self.cb_a), ('Hộ B:', self.cb_b)):
            for ma, tt, ten in ds_ho:
                cb.addItem(f'{tt}. {ten}', ma)
            cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            cb.setMinimumContentsLength(24)
            n = QLabel(nhan)
            n.setProperty('vai', 'nhan')
            h.addWidget(n)
            h.addWidget(cb, 1)
        self.cb_a.setCurrentIndex(max(0, self.cb_a.findData(ma_a)))
        self.cb_b.setCurrentIndex(max(0, self.cb_b.findData(ma_b if ma_b is not None else ma_a)))
        self.o_chi_khac = QCheckBox('Chỉ dòng khác nhau')
        self.b_doc = QPushButton('Đọc lại')
        self.b_doc.setToolTip('Đọc lại số liệu đã lưu (phương án đang sửa dở chưa lưu không tính)')
        h.addWidget(self.o_chi_khac)
        h.addWidget(self.b_doc)
        lo.addLayout(h)
        self.lb = QLabel()
        self.lb.setWordWrap(True)
        lo.addWidget(self.lb)
        self.bang = QTableWidget(0, len(COT_SO_SANH))
        self.bang.setHorizontalHeaderLabels(list(COT_SO_SANH))
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setWordWrap(True)
        self.bang.verticalHeader().setVisible(False)
        for c, w in enumerate(RONG_SO_SANH):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        lo.addWidget(self.bang, 1)
        for cb in (self.cb_a, self.cb_b):
            cb.activated.connect(lambda _: self.nap())
        self.o_chi_khac.toggled.connect(lambda _: self._loc())
        self.b_doc.clicked.connect(lambda: self.nap())
        self.nap()

    def nap(self) -> None:
        ma_a, ma_b = self.cb_a.currentData(), self.cb_b.currentData()
        if ma_a is None or ma_b is None:
            return
        self.kq = kq = so_sanh_ho.so_sanh(self.con, ma_a, ma_b)
        canh = qmau_theo_tong(TOKEN['canh_bao_nhat'])
        self.bang.setRowCount(len(kq['dong']))

        def so(x, k, ham):
            return ham(x[k]) if x is not None else ''
        for r, d in enumerate(kq['dong']):
            a, b = d['a'], d['b']
            khac = ('khác đơn giá' if d['khac_gia'] else ('khác số lượng' if d['khac_sl'] else
                    ('khác thành tiền' if d['khac_tien'] and not d['chi_mot'] else
                     (f'chỉ hộ {d["chi_mot"].upper()} có' if d['chi_mot'] else ''))))
            for c, v in enumerate((f'{d["so_muc"]}. {d["ten_muc"]}', d['ten'], d['dvt'], so(a, 'so_luong', so_vn), so(a, 'don_gia', vn),
                                   so(a, 'thanh_tien', vn), so(b, 'so_luong', so_vn), so(b, 'don_gia', vn), so(b, 'thanh_tien', vn), khac)):
                it = QTableWidgetItem(str(v))
                if 3 <= c <= 8:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if d['khac_gia'] and c in (4, 7, 9):
                    it.setBackground(canh)
                self.bang.setItem(r, c, it)
        vua_dong(self.bang)
        lech = kq['tong_a'] - kq['tong_b']
        self.lb.setText(f'<b>A: {kq["ten_a"]}</b> - {vn(kq["tong_a"])} đồng &nbsp;|&nbsp; <b>B: {kq["ten_b"]}</b> - {vn(kq["tong_b"])} đồng '
                        f'&nbsp;|&nbsp; Chênh lệch A - B: {vn(lech)} đồng &nbsp;|&nbsp; {kq["so_khac_gia"]} tài sản cùng tên khác đơn giá '
                        '(số liệu đã lưu, kể cả thưởng trong tổng)')
        self._loc()

    def _loc(self) -> None:
        chi = self.o_chi_khac.isChecked()
        for r, d in enumerate((self.kq or {}).get('dong', ())):
            self.bang.setRowHidden(r, chi and not (d['khac_gia'] or d['khac_sl'] or d['khac_tien']))

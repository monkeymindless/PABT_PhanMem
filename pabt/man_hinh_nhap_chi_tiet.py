"""Hộp thoại "Nhập phương án chi tiết từ Excel": xem các sheet hộ đọc được, chọn sheet cần nhập, cách xử lý hộ đã có trong
dự án. Việc đọc / ghi nằm ở nhap_chi_tiet; hộp thoại chỉ cho chọn."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                               QRadioButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import nhap_chi_tiet
from .tien import vn

TIEU_DE = 'Nhập phương án chi tiết từ Excel'
COT = ['Nhập', 'Sheet', 'Họ và tên', 'Thửa, dòng phương án', 'Tổng theo file (đ)', 'Ghi chú']
TRUNG = [('bo_qua', 'Bỏ qua hộ đã có (giữ nguyên số liệu trong phần mềm)'),
         ('thay', 'Thay hồ sơ, thửa, phương án của hộ đã có bằng số liệu trong file (giữ mã hộ, đợt trình, quyết định)'),
         ('them', 'Vẫn thêm thành hộ mới')]


class HopNhapChiTiet(QDialog):
    """kq: nhap_chi_tiet.KetQuaDoc; con: dự án sẽ nhập vào (để báo hộ trùng), None = dự án mới."""

    def __init__(self, kq, con=None, parent=None, ten_du_an: str = ''):
        super().__init__(parent)
        self.kq = kq
        self.setWindowTitle(TIEU_DE)
        self.resize(1080, 600)
        lo = QVBoxLayout(self)
        dich = f'vào dự án đang mở <b>{ten_du_an}</b>' if con is not None else 'vào <b>dự án mới</b> (bộ đơn giá tích hợp)'
        gt = QLabel(f'Mỗi sheet là phương án chi tiết của một hộ. Đánh dấu các sheet cần nhập {dich}. Dòng nhà, công trình, '
                    'cây trồng trùng tên và đơn giá với bộ đơn giá được gắn mã danh mục; dòng khác giá / ngoài danh mục ghi '
                    '"nhập tay". Thành tiền của file được giữ để đối chiếu (Dự án → Đối chiếu với file Excel).')
        gt.setWordWrap(True)
        lo.addWidget(gt)
        self.bang = QTableWidget(len(kq.ho), len(COT))
        self.bang.setHorizontalHeaderLabels(COT)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setWordWrap(True)
        self.trung = {}
        chi_muc = nhap_chi_tiet.ChiMucTrung(con) if con is not None else None
        for i, h in enumerate(kq.ho):
            ma = chi_muc.tim(h) if chi_muc is not None and h.ho_ten else None
            self.trung[i] = ma
            o = QTableWidgetItem()
            o.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            o.setCheckState(Qt.CheckState.Checked if h.chon else Qt.CheckState.Unchecked)
            if h.loi or not h.ho_ten:
                o.setFlags(Qt.ItemFlag.NoItemFlags)
            self.bang.setItem(i, 0, o)
            tong = h.tong.get('tong')
            gc = [h.ly_do] if h.ly_do else []
            if ma is not None:
                gc.append(f'trùng hộ {ma} đã có trong dự án')
            gc += h.loi + h.canh_bao
            for c, v in enumerate([h.sheet, h.ten_ngan, nhap_chi_tiet.mo_ta(h), vn(tong) if tong is not None else '',
                                   '; '.join(gc)], start=1):
                it = QTableWidgetItem(v)
                if c == 4:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.bang.setItem(i, c, it)
        hd = self.bang.horizontalHeader()
        for c, w in enumerate((58, 70, 230, 400, 140)):
            self.bang.setColumnWidth(c, w)
        hd.setSectionResizeMode(len(COT) - 1, QHeaderView.ResizeMode.Stretch)
        self.bang.resizeRowsToContents()
        self.bang.itemChanged.connect(lambda *_: self._dem())
        lo.addWidget(self.bang, 1)
        h = QHBoxLayout()
        for chu, gt_chon in (('Chọn tất cả', True), ('Bỏ chọn tất cả', False)):
            b = QPushButton(chu)
            b.clicked.connect(lambda _=False, x=gt_chon: self.chon_tat_ca(x))
            h.addWidget(b)
        self.lb = QLabel()
        self.lb.setProperty('vai', 'nhan')
        h.addWidget(self.lb, 1)
        lo.addLayout(h)
        co_trung = any(m is not None for m in self.trung.values())
        nhan = QLabel('Hộ đã có trong dự án (cùng số CCCD; không có CCCD thì cùng họ tên):')
        nhan.setVisible(co_trung)
        lo.addWidget(nhan)
        self.nhom = QButtonGroup(self)
        self.nut_trung = {}
        for k, chu in TRUNG:
            r = QRadioButton(chu)
            r.setChecked(k == 'bo_qua')
            r.setVisible(co_trung)
            self.nhom.addButton(r)
            self.nut_trung[k] = r
            lo.addWidget(r)
        h = QHBoxLayout()
        h.addStretch()
        self.b_nhap = QPushButton('Thực hiện nhập')
        self.b_nhap.setDefault(True)
        self.b_nhap.clicked.connect(self.accept)
        b_huy = QPushButton('Hủy')
        b_huy.clicked.connect(self.reject)
        h.addWidget(self.b_nhap)
        h.addWidget(b_huy)
        lo.addLayout(h)
        self._dem()

    def chon_tat_ca(self, co: bool) -> None:
        # chặn itemChanged trong lúc đánh dấu (mỗi ô một lần đếm lại cả bảng: 3.000 sheet = 9 triệu lần đọc ô); đếm một lần sau cùng
        self.bang.blockSignals(True)
        try:
            for i in range(self.bang.rowCount()):
                o = self.bang.item(i, 0)
                if o.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    o.setCheckState(Qt.CheckState.Checked if co else Qt.CheckState.Unchecked)
        finally:
            self.bang.blockSignals(False)
        self.bang.viewport().update()
        self._dem()

    def ds_chon(self) -> list:
        """Tên các sheet đang đánh dấu."""
        return [self.kq.ho[i].sheet for i in range(self.bang.rowCount())
                if self.bang.item(i, 0).checkState() == Qt.CheckState.Checked]

    def cach_trung(self) -> str:
        return next((k for k, r in self.nut_trung.items() if r.isChecked()), 'bo_qua')

    def _dem(self) -> None:
        chon = set(self.ds_chon())
        so_dong = sum(h.so_dong + len(h.dat) for h in self.kq.ho if h.sheet in chon)
        trung = sum(1 for i, h in enumerate(self.kq.ho) if h.sheet in chon and self.trung.get(i) is not None)
        self.lb.setText(f'Đã chọn {len(chon)}/{len(self.kq.ho)} sheet, {so_dong} dòng'
                        + (f' - {trung} hộ đã có trong dự án' if trung else ''))
        self.b_nhap.setEnabled(bool(chon))

    def ap_dung(self) -> str:
        """Ghi lựa chọn vào kq (HoChiTiet.chon); trả cách xử lý hộ trùng."""
        chon = set(self.ds_chon())
        for h in self.kq.ho:
            h.chon = h.sheet in chon
        return self.cach_trung()

"""Hộp "Dán danh sách tài sản": dán / gõ nhiều dòng tài sản thô (Tên, ĐVT, Số lượng, Tỷ lệ, Ghi chú) -> phần mềm tự xếp mỗi dòng
vào Nhà, công trình / Cây trồng / Vật nuôi / Chính sách hỗ trợ (phan_loai_tai_san) và tìm mục đơn giá khớp; người dùng sửa
loại nếu cần rồi thêm vào phương án của hộ đang mở (CuaSoLapPA)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
                               QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import lap_pa
from .lap_pa import LoiNhap
from .phan_loai_tai_san import LOAI, BoPhanLoai, doc_danh_sach
from .thong_bao import TEN_UD

VANG = QColor('#FFF2CC')
COT = ['Thêm', 'Tên tài sản', 'ĐVT', 'Số lượng', 'Tỷ lệ', 'Xếp vào', 'Mục đơn giá khớp', 'Độ tin', 'Căn cứ xếp loại']
VI_DU = ('Nhà cấp 4 mái tôn\tm2\t45\nHàng rào lưới B40\tm2\t30\nMít 6 năm\tcây\t3\t80%\nAo nuôi cá ghép\tha/vụ\t0,03\t70%\n'
         'Gà ta\tcon\t40\nDi dời đồng hồ điện\tbộ\t1')


def _bo_phan_loai(dm) -> BoPhanLoai:
    """Dựng một lần cho mỗi danh mục (DanhMuc dùng chung giữa các lần mở cửa sổ)."""
    bo = dm.__dict__.get('_bo_phan_loai')
    if bo is None:
        bo = dm.__dict__['_bo_phan_loai'] = BoPhanLoai(dm)
    return bo


class HopDanTaiSan(QDialog):
    im_lang = False

    def __init__(self, cua_so, chu: str = ''):
        """cua_so: CuaSoLapPA (cần .bo = BoSoan, .bang, .cap_nhat, .thong_bao)."""
        super().__init__(cua_so)
        self.cua_so = cua_so
        self.ds = []                                    # [(dict dòng thô, KetQua)]
        self.setWindowTitle('Dán danh sách tài sản - tự xếp vào Nhà, công trình / Cây trồng / Vật nuôi / Hỗ trợ')
        self.resize(1250, 680)
        hd = QLabel('Dán từ Excel (chép các cột <b>Tên, ĐVT, Số lượng, Tỷ lệ, Ghi chú</b>) hoặc gõ mỗi dòng một tài sản, cột cách nhau '
                    'bằng Tab, dấu <b>;</b> hoặc <b>|</b> (chỉ cần tên; gõ "Mít 6 năm 3 cây" cũng được). Bấm <b>Phân loại</b>: phần '
                    'mềm so với bộ đơn giá, rồi theo từ khóa và đơn vị tính; dòng nền vàng nên xem lại loại.')
        hd.setWordWrap(True)
        self.o_chu = QPlainTextEdit(chu)
        self.o_chu.setPlaceholderText(VI_DU)
        b_pl = QPushButton('Phân loại')
        b_pl.clicked.connect(lambda: self.phan_loai())
        tren = QWidget()
        lt = QVBoxLayout(tren)
        lt.setContentsMargins(0, 0, 0, 0)
        lt.addWidget(hd)
        lt.addWidget(self.o_chu, 1)
        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(b_pl)
        lt.addLayout(h)
        self.bang = QTableWidget(0, len(COT))
        self.bang.setHorizontalHeaderLabels(COT)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        for c, w in enumerate((45, 300, 70, 80, 60, 170, 300, 60, 400)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.lb = QLabel('')
        b_them = QPushButton('Thêm vào phương án')
        b_them.clicked.connect(lambda: self.them())
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        hn = QHBoxLayout()
        hn.addWidget(self.lb, 1)
        hn.addWidget(b_them)
        hn.addWidget(b_dong)
        tach = QSplitter(Qt.Orientation.Vertical)
        tach.addWidget(tren)
        tach.addWidget(self.bang)
        tach.setSizes([220, 420])
        lo = QVBoxLayout(self)
        lo.addWidget(tach, 1)
        lo.addLayout(hn)
        if chu:
            self.phan_loai()

    def bao(self, chu: str, loi: bool = True) -> None:
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TEN_UD, chu)

    # ---------------------------------------------- phân loại
    def phan_loai(self, chu: str | None = None) -> list:
        if chu is not None:
            self.o_chu.setPlainText(chu)
        dong = doc_danh_sach(self.o_chu.toPlainText())
        if not dong:
            self.bao('Chưa có dòng tài sản nào: dán hoặc gõ danh sách vào ô phía trên.', loi=False)
            return []
        bo = _bo_phan_loai(self.cua_so.bo.dm)
        self.ds = [(d, bo.phan_loai(d['ten'], d['dvt'])) for d in dong]
        b = self.bang
        b.setUpdatesEnabled(False)
        b.setRowCount(len(self.ds))
        for r, (d, k) in enumerate(self.ds):
            o = QTableWidgetItem()
            o.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            o.setCheckState(Qt.CheckState.Checked)
            b.setItem(r, 0, o)
            for c, v in ((1, d['ten']), (2, k.dvt or d['dvt']), (3, d['so_luong']), (4, d['ty_le'])):
                b.setItem(r, c, QTableWidgetItem(v))
            cb = QComboBox()
            for ma, (_, ten) in LOAI.items():
                cb.addItem(ten, ma)
            cb.setCurrentIndex(cb.findData(k.loai))
            cb.currentIndexChanged.connect(lambda _=0, rr=r: self._doi_loai(rr))
            b.setCellWidget(r, 5, cb)
            for c, v in ((6, k.khop.ten if k.khop is not None else '(ngoài danh mục: nhập đơn giá sau)'),
                         (7, f'{k.do_tin:.0%}'), (8, k.ly_do)):
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                it.setToolTip(v)
                b.setItem(r, c, it)
            if k.can_xem:
                for c in range(len(COT)):
                    if b.item(r, c) is not None:
                        b.item(r, c).setBackground(QBrush(VANG))
        b.setUpdatesEnabled(True)
        dem = {}
        for _, k in self.ds:
            dem[k.ten_loai] = dem.get(k.ten_loai, 0) + 1
        self.lb.setText(f'{len(self.ds)} dòng: ' + ', '.join(f'{t} {n}' for t, n in dem.items()) +
                        f'; khớp đơn giá {sum(1 for _, k in self.ds if k.khop is not None)} dòng; '
                        f'cần xem lại {sum(1 for _, k in self.ds if k.can_xem)} dòng (nền vàng).')
        return self.ds

    def _doi_loai(self, r: int):
        """Người dùng đổi loại: mục danh mục đã khớp khác loại thì bỏ (dòng thành ngoài danh mục)."""
        d, k = self.ds[r]
        loai = self.bang.cellWidget(r, 5).currentData()
        if k.khop is not None and loai != k.loai:
            k.khop = None
            self.bang.item(r, 6).setText('(ngoài danh mục: nhập đơn giá sau)')
        k.loai = loai


    # ---------------------------------------------- thêm vào phương án
    def them(self) -> int:
        bo = self.cua_so.bo
        n, loi, muc_cuoi = 0, [], None
        for r, (d, k) in enumerate(self.ds):
            if self.bang.item(r, 0).checkState() != Qt.CheckState.Checked:
                continue
            ten, dvt = self.bang.item(r, 1).text().strip(), self.bang.item(r, 2).text().strip()
            sl, tl = self.bang.item(r, 3).text().strip(), self.bang.item(r, 4).text().strip()
            muc = LOAI[k.loai][0]
            try:
                if k.khop is not None:
                    i, _ = bo.them_tu_danh_muc(muc, k.khop)
                else:
                    i = bo.them_hang_muc_khac(muc, ten)
                    if dvt:
                        bo.sua_khoan(muc, i, 'dvt', dvt)
                if sl:
                    bo.sua_khoan(muc, i, 'so_luong', sl)
                if tl:
                    so = lap_pa.doc_so(tl.rstrip('%'), 'Tỷ lệ')
                    bo.pa.khoan[muc][i].ty_le = so if so <= 5 and not tl.endswith('%') else lap_pa.doc_ty_le(tl)
                if d.get('ghi_chu'):
                    bo.pa.khoan[muc][i].ghi_chu = d['ghi_chu']
                n += 1
                muc_cuoi = muc
                self.bang.item(r, 0).setCheckState(Qt.CheckState.Unchecked)       # đã thêm: bấm lại không thêm trùng
            except LoiNhap as e:
                loi.append(f'Dòng {r + 1} "{ten[:40]}": {e}')
        if muc_cuoi is not None:
            from .man_hinh import the_cua
            from .nghiep_vu import MUC_KHOAN
            for m in MUC_KHOAN:
                self.cua_so.bang[m].ve()
            self.cua_so.tab.setCurrentIndex(the_cua(muc_cuoi))
            self.cua_so.cap_nhat()
            self.cua_so.thong_bao(f'Đã thêm {n} dòng từ danh sách tài sản (chưa lưu: bấm Lưu).')
        if loi:
            self.bao(f'Đã thêm {n} dòng; {len(loi)} dòng chưa thêm được:\n' + '\n'.join(loi[:15]))
        elif n and not self.im_lang:
            self.accept()
        return n

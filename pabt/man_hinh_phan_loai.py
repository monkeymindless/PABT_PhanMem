"""Hộp "Dán danh sách tài sản": dán / gõ nhiều dòng tài sản thô (Tên, ĐVT, Số lượng, Tỷ lệ, Ghi chú) -> phần mềm tự xếp mỗi dòng
vào Nhà, công trình / Cây trồng / Vật nuôi / Chính sách hỗ trợ (phan_loai_tai_san) và tìm mục đơn giá khớp; người dùng sửa
loại nếu cần rồi thêm vào phương án của hộ đang mở (CuaSoLapPA) hoặc bảng Dự toán & khái toán (KhungDuToan) - 0.9.67: cùng
một hộp, ghi qua "đích" của nhap_tai_san (DichPhuongAn / DichDuToan); màn hình chủ vẽ lại ở `sau_khi_dan_tai_san(n, muc)`."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
                               QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .lap_pa import LoiNhap
from .phan_loai_tai_san import LOAI, BoPhanLoai, doc_danh_sach
from .thong_bao import TEN_UD

VANG = QColor('#FFF2CC')
COT = ['Thêm', 'Tên tài sản', 'ĐVT', 'Số lượng', 'Tỷ lệ', 'Xếp vào', 'Mục đơn giá khớp', 'Độ tin', 'Căn cứ xếp loại']
VI_DU = ('Nhà tạm m2 4*5\nNhà cấp 4 mái tôn m2 45\nHàng rào lưới B40 m2 30\nMít 6 năm cây 3 80%\nAo nuôi cá ghép ha/vụ 0,03 70%\n'
         'Gà ta con 40\nDi dời đồng hồ điện bộ 1')


def _bo_phan_loai(dm) -> BoPhanLoai:
    """Dựng một lần cho mỗi danh mục (DanhMuc dùng chung giữa các lần mở cửa sổ)."""
    bo = dm.__dict__.get('_bo_phan_loai')
    if bo is None:
        bo = dm.__dict__['_bo_phan_loai'] = BoPhanLoai(dm)
    return bo


class HopDanTaiSan(QDialog):
    im_lang = False

    def __init__(self, cua_so, chu: str = '', dich=None):
        """cua_so: màn hình chủ có `sau_khi_dan_tai_san(n, muc_cuoi)` (CuaSoLapPA, KhungDuToan); dich: đích ghi của
        nhap_tai_san (mặc định DichPhuongAn(cua_so.bo))."""
        super().__init__(cua_so)
        self.cua_so = cua_so
        if dich is None:
            from .nhap_tai_san import DichPhuongAn
            dich = DichPhuongAn(cua_so.bo)
        self.dich = dich
        self.ds = []                                    # [(dict dòng thô, KetQua)]
        self.setWindowTitle('Dán danh sách tài sản - tự xếp vào Nhà, công trình / Cây trồng / Vật nuôi / Hỗ trợ')
        self.resize(1250, 680)
        hd = QLabel('Mỗi dòng một tài sản: <b>Tên tài sản, công trình</b> ␣ <b>Đơn vị tính</b> ␣ <b>Số lượng</b> (cách nhau dấu cách; '
                    'thêm ␣ <b>Tỷ lệ %</b> nếu có). Số lượng gõ số hoặc phép tính: <b>Nhà tạm m2 4*5</b> = 20 m² (nhân bằng * hoặc x). '
                    'Dán thẳng từ Excel (cột Tên, ĐVT, Số lượng, Tỷ lệ, Ghi chú) cũng được. Bấm <b>Phân loại</b>: phần mềm tự xếp '
                    'vào Nhà / Cây / Vật nuôi / Hỗ trợ theo bộ đơn giá; dòng nền vàng nên xem lại loại.')
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
        bo = _bo_phan_loai(self.dich.dm)
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
            if d.get('cong_thuc'):                       # "4*5" đã tính thành 20: giữ phép tính gốc ở chú thích
                b.item(r, 3).setToolTip(f'= {d["cong_thuc"]}')
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
        from .nhap_tai_san import them_dong_tho
        n, loi, muc_cuoi = 0, [], None
        for r, (d, k) in enumerate(self.ds):
            if self.bang.item(r, 0).checkState() != Qt.CheckState.Checked:
                continue
            ten, dvt = self.bang.item(r, 1).text().strip(), self.bang.item(r, 2).text().strip()
            sl, tl = self.bang.item(r, 3).text().strip(), self.bang.item(r, 4).text().strip()
            muc = LOAI[k.loai][0]
            try:
                them_dong_tho(self.dich, muc, k.khop, ten, dvt, sl, tl, d.get('ghi_chu') or '')
                n += 1
                muc_cuoi = muc
                self.bang.item(r, 0).setCheckState(Qt.CheckState.Unchecked)       # đã thêm: bấm lại không thêm trùng
            except LoiNhap as e:
                loi.append(f'Dòng {r + 1} "{ten[:40]}": {e}')
        if muc_cuoi is not None:
            self.cua_so.sau_khi_dan_tai_san(n, muc_cuoi)
        if loi:
            self.bao(f'Đã thêm {n} dòng; {len(loi)} dòng chưa thêm được:\n' + '\n'.join(loi[:15]))
        elif n and not self.im_lang:
            self.accept()
        return n

"""Cửa sổ "Đơn giá riêng của dự án": quy ước giá tương đương nhập tay (tài sản đặc biệt của từng dự án) và nhập đơn giá
thẩm định giá được phê duyệt (file Excel / Word / PDF / CSV). Lưu vào bảng quy_uoc của file dự án (don_gia_rieng)."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QInputDialog, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout,
                               QWidget)

from . import don_gia_rieng as dgr
from .lap_pa import LoiNhap
from .tien import so_vn as vn
from .thong_bao import TEN_UD

COT_QU = [('ten_thuc_te', 'Tên tài sản thực tế (in ra phương án)', 300), ('ten_tuong_duong', 'Áp giá theo / nguồn giá', 260),
          ('dvt', 'ĐVT', 60), ('don_gia', 'Đơn giá (đ)', 100), ('can_cu', 'Căn cứ', 300), ('nguon', 'Thuộc', 100)]
MAU_RIENG, MAU_TD = QColor('#E8F5E9'), QColor('#E3F2FD')


class HopDonGiaRieng(QDialog):
    im_lang = False

    def __init__(self, con, parent=None, dm=None, chi_doc: bool = False, the: int = 0):
        super().__init__(parent)
        self.con, self.dm, self.chi_doc = con, dm, chi_doc
        self.da_luu = False
        self.thong_bao_cuoi = ''
        self.ds_td = []
        self._dang_ve = False
        self.setWindowTitle('Đơn giá đặc biệt của dự án (quy ước tương đương, đơn giá thẩm định)')
        self.resize(1250, 680)
        self.tab = QTabWidget()
        self.tab.addTab(self._the_quy_uoc(), 'Quy ước giá tương đương')
        self.tab.addTab(self._the_tham_dinh(), 'Nhập đơn giá thẩm định (tài sản đặc biệt)')
        self.tab.setCurrentIndex(the)
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(b_dong)
        v = QVBoxLayout(self)
        v.addWidget(self.tab, 1)
        v.addLayout(h)
        self.nap()

    def _bao(self, ham, chu):
        self.thong_bao_cuoi = chu
        if not self.im_lang:
            ham(self, TEN_UD, chu)

    # ------------------------------------------------------------ thẻ 1: quy ước tương đương
    def _the_quy_uoc(self) -> QWidget:
        w = QWidget()
        # mô tả một dòng (người dùng 13/10/2026: thu gọn) - đầy đủ ở chú thích
        lb = QLabel('Tài sản không có trong bộ đơn giá: tên thực tế + giá theo mục tương đương. Dòng nền xanh = riêng của dự án.')
        lb.setToolTip('Tài sản đặc biệt / không có trong bộ đơn giá của dự án này: gõ tên thực tế, giá áp theo mục tương đương '
                      '(hoặc đơn giá thẩm định), ĐVT, căn cứ. Khi lập phương án, các dòng này nằm đầu ô chọn nhanh mục Nhà, công '
                      'trình và Cây trồng, vật nuôi (nhãn [Quy ước] / [Thẩm định]). Dòng nền xanh là dòng riêng của dự án - '
                      'được giữ khi "Áp bộ đơn giá vào dự án"; dòng của bộ đơn giá mà sửa thì thành dòng riêng.')
        self.bang = QTableWidget(0, len(COT_QU))
        self.bang.setHorizontalHeaderLabels([c[1] for c in COT_QU])
        for i, c in enumerate(COT_QU):
            self.bang.setColumnWidth(i, c[2])
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setWordWrap(True)
        if self.chi_doc:
            self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.itemChanged.connect(self._da_sua)
        h = QHBoxLayout()
        self.b_them = QPushButton('Thêm dòng trống')
        self.b_them.clicked.connect(lambda: self.them_dong())
        self.b_chon = QPushButton('Thêm theo mục trong bộ đơn giá…')
        self.b_chon.setToolTip('Chọn mục tương đương trong danh mục (lấy ĐVT, đơn giá, căn cứ), rồi gõ tên tài sản thực tế')
        self.b_chon.clicked.connect(lambda: self.them_theo_danh_muc())
        self.b_xoa = QPushButton('Xóa dòng chọn')
        self.b_xoa.clicked.connect(self.xoa_dong)
        self.b_luu = QPushButton('Lưu thay đổi')
        self.b_luu.setDefault(True)
        from .giao_dien import KieuNut, ap_kieu_nut
        ap_kieu_nut(self.b_luu, KieuNut.LUU)            # xanh lá đậm; chỉ bật khi có thay đổi chưa lưu
        self.b_luu.clicked.connect(lambda: self.luu())
        for b in (self.b_them, self.b_chon, self.b_xoa):
            h.addWidget(b)
            b.setEnabled(not self.chi_doc)
        h.addStretch(1)
        h.addWidget(self.b_luu)
        self.b_luu.setEnabled(False)
        v = QVBoxLayout(w)
        v.addWidget(lb)
        v.addWidget(self.bang, 1)
        v.addLayout(h)
        return w

    def nap(self):
        self._dang_ve = True
        self.bang.setRowCount(0)
        for r in dgr.doc(self.con):
            self._them_hang(r)
        self._dang_ve = False
        self.b_luu.setEnabled(False)

    def _them_hang(self, r: dict):
        i = self.bang.rowCount()
        self.bang.insertRow(i)
        for c, (k, _, _) in enumerate(COT_QU):
            if k == 'nguon':
                v = 'Thẩm định giá' if r.get('tham_dinh') else ('Dự án' if r.get('rieng') else 'Bộ đơn giá')
            elif k == 'don_gia':
                v = vn(r[k]) if str(r.get(k) or '').strip() else ''
            else:
                v = str(r.get(k) or '')
            it = QTableWidgetItem(v)
            it.setToolTip(v)
            if k == 'nguon':
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if k == 'don_gia':
                it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if r.get('rieng'):
                it.setBackground(QBrush(MAU_TD if r.get('tham_dinh') else MAU_RIENG))
            self.bang.setItem(i, c, it)
        self.bang.item(i, 0).setData(Qt.ItemDataRole.UserRole, r.get('id'))
        return i

    def _da_sua(self, *_):
        if not self._dang_ve:
            self.b_luu.setEnabled(not self.chi_doc)

    def them_dong(self, ten: str = '', ten_td: str = '', dvt: str = '', don_gia='', can_cu: str = '') -> int:
        self._dang_ve = True
        i = self._them_hang(dict(id=None, ten_thuc_te=ten, ten_tuong_duong=ten_td, dvt=dvt, don_gia=don_gia, can_cu=can_cu,
                                 rieng=True))
        self._dang_ve = False
        self.b_luu.setEnabled(True)
        self.bang.setCurrentCell(i, 0)
        if not ten:
            self.bang.editItem(self.bang.item(i, 0))
        return i

    def them_theo_danh_muc(self, m=None, ten: str | None = None):
        """Chọn mục tương đương trong bộ đơn giá của dự án (nhà, công trình / cây trồng / hỗ trợ), gõ tên thực tế -> dòng mới."""
        if m is None:
            from .man_hinh import ChonDanhMuc
            from .lap_pa import DanhMuc
            dlg = ChonDanhMuc(self.dm or DanhMuc(self.con), 2, self, tuong_duong=True)
            if dlg.exec() != QDialog.DialogCode.Accepted or dlg.chon is None:
                return None
            m = dlg.chon
        if m.don_gia is None:
            self._bao(QMessageBox.warning, f'{m.ma} - {m.ten} chưa có đơn giá trong danh mục, không làm giá tương đương được.')
            return None
        if ten is None:
            ten, ok = QInputDialog.getText(self, 'Quy ước giá tương đương', f'Tài sản thực tế áp giá theo "{m.ten}":')
            if not ok or not ten.strip():
                return None
        ten_td = m.phan_loai if m.nguon == 'quyuoc' else m.ten
        cc = f'Áp giá tương đương theo {m.ten}' + (f' ({m.ma})' if m.nguon != 'quyuoc' else '')
        return self.them_dong(ten.strip(), ten_td, m.dvt, str(m.don_gia), cc)

    def xoa_dong(self):
        hang = sorted({i.row() for i in self.bang.selectedIndexes()}, reverse=True)
        for i in hang:
            self.bang.removeRow(i)
        if hang:
            self.b_luu.setEnabled(True)

    def doc_bang_qu(self) -> list:
        ds = []
        for i in range(self.bang.rowCount()):
            d = {k: (self.bang.item(i, c).text() if self.bang.item(i, c) else '') for c, (k, _, _) in enumerate(COT_QU)}
            d['id'] = self.bang.item(i, 0).data(Qt.ItemDataRole.UserRole) if self.bang.item(i, 0) else None
            ds.append(d)
        return ds

    def luu(self) -> dict | None:
        if self.chi_doc:
            return None
        try:
            kq = dgr.luu(self.con, self.doc_bang_qu())
        except LoiNhap as e:
            self._bao(QMessageBox.warning, str(e))
            return None
        self.da_luu = True
        self.nap()
        return kq

    def reject(self):
        if self.b_luu.isEnabled() and not self.im_lang:
            tl = QMessageBox.question(self, TEN_UD, 'Quy ước tương đương đã sửa nhưng chưa lưu. Lưu trước khi đóng?',
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                                      | QMessageBox.StandardButton.Cancel)
            if tl == QMessageBox.StandardButton.Cancel:
                return
            if tl == QMessageBox.StandardButton.Save and self.luu() is None:
                return
        super().reject()

    # ------------------------------------------------------------ thẻ 2: đơn giá thẩm định
    def _the_tham_dinh(self) -> QWidget:
        w = QWidget()
        lb = QLabel(f'Đơn giá của đơn vị thẩm định giá đã được phê duyệt (theo {dgr.QD_TAI_SAN_DAC_BIET}): chọn file, xem lại '
                    'từng dòng rồi đưa vào đơn giá của dự án.')
        lb.setToolTip(f'Tài sản đặc biệt chưa có đơn giá trong bộ đơn giá: lấy đơn giá của đơn vị thẩm định giá đã được phê '
                      f'duyệt (theo {dgr.QD_TAI_SAN_DAC_BIET} - sửa số hiệu ở ô "Áp dụng theo" nếu khác). Chọn file kết quả / '
                      'chứng thư thẩm định giá (Excel, Word, PDF, CSV) có bảng Tên tài sản - ĐVT - Đơn giá; xem lại từng dòng '
                      '(sửa được tên, ĐVT, đơn giá; bỏ chọn dòng không lấy) rồi bấm "Đưa vào đơn giá của dự án".')
        lb.setWordWrap(True)
        from .giao_dien import KieuNut, ap_kieu_nut
        self.b_file = QPushButton('Chọn file thẩm định giá…')
        self.b_file.clicked.connect(lambda: self.chon_file())
        self.b_file.setEnabled(not self.chi_doc)
        self.lb_file = QLabel('')
        self.b_dua = QPushButton('Đưa vào đơn giá của dự án')
        self.b_dua.setEnabled(False)
        self.b_dua.clicked.connect(lambda: self.dua_vao())
        ap_kieu_nut(self.b_dua, KieuNut.CHINH)
        self.o_so = QLineEdit()
        self.o_ngay = QLineEdit()
        self.o_ngay.setPlaceholderText('dd/mm/yyyy')
        self.o_don_vi = QLineEdit()
        self.o_qd = QLineEdit()
        self.o_qd.setPlaceholderText('Ví dụ: Quyết định số …/QĐ-UBND ngày … phê duyệt giá …')
        self.o_ap_dung = QLineEdit(dgr.QD_TAI_SAN_DAC_BIET)
        self.o_can_cu = QLineEdit()
        for o in (self.o_so, self.o_ngay, self.o_don_vi, self.o_qd, self.o_ap_dung):
            o.textEdited.connect(self._ghep_can_cu)
        # 6 trường chứng thư: lưới 2 cột (người dùng 13/10/2026: trước 1 cột dài ~220 px) - bảng tài sản thẩm định cao hơn
        luoi = QGridLayout()
        luoi.setHorizontalSpacing(10)
        luoi.setVerticalSpacing(4)
        for hang, ((n1, o1), (n2, o2)) in enumerate((
                (('Chứng thư số:', self.o_so), ('Quyết định phê duyệt giá:', self.o_qd)),
                (('Ngày chứng thư:', self.o_ngay), ('Căn cứ ghi vào phương án:', self.o_can_cu)),
                (('Đơn vị thẩm định giá:', self.o_don_vi), ('Áp dụng theo:', self.o_ap_dung)))):
            for cot, (nhan, o) in enumerate(((n1, o1), (n2, o2))):
                lbn = QLabel(nhan)
                lbn.setProperty('vai', 'nhan')
                luoi.addWidget(lbn, hang, cot * 2)
                luoi.addWidget(o, hang, cot * 2 + 1)
        luoi.setColumnStretch(1, 2)
        luoi.setColumnStretch(3, 3)
        self.bang_td = QTableWidget(0, 5)
        self.bang_td.setHorizontalHeaderLabels(['Lấy', 'Tên tài sản', 'ĐVT', 'Đơn giá thẩm định (đ)', 'Dòng gốc trong file'])
        for i, x in enumerate((45, 380, 80, 150, 450)):
            self.bang_td.setColumnWidth(i, x)
        self.bang_td.horizontalHeader().setStretchLastSection(True)
        self.bang_td.itemChanged.connect(self._sua_td)
        self.lb_xem = QLabel('')
        self.lb_xem.setWordWrap(True)
        self.lb_xem.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        h1 = QHBoxLayout()                              # thanh công cụ trên cùng: chọn file | tên file | đưa vào
        h1.addWidget(self.b_file)
        h1.addWidget(self.lb_file, 1)
        h1.addWidget(self.b_dua)
        v = QVBoxLayout(w)
        v.addLayout(h1)
        v.addWidget(lb)
        v.addLayout(luoi)
        v.addWidget(self.bang_td, 1)
        v.addWidget(self.lb_xem)
        return w

    def _ghep_can_cu(self, *_):
        self.o_can_cu.setText(dgr.can_cu_tham_dinh(self.o_so.text().strip(), self.o_ngay.text().strip(),
                                                   self.o_don_vi.text().strip(), self.o_qd.text().strip(),
                                                   self.o_ap_dung.text().strip()))

    def chon_file(self, p=None, dong: list | None = None):
        if p is None:
            p, _ = QFileDialog.getOpenFileName(self, 'Chọn file kết quả thẩm định giá', '',
                                               'Excel, Word, PDF, CSV (*.xlsx *.xlsm *.xls *.docx *.doc *.pdf *.csv *.txt)')
            if not p:
                return None
        from . import nhap_don_gia as ndg, ocr
        try:
            if dong is None:
                from .man_hinh_quan_ly import doc_co_tien_do
                dong = doc_co_tien_do(self, ndg.doc_bang_ocr, p)      # PDF scan: nhận dạng chữ, có nút Hủy
            ds, tt, xem = dgr.doc_file_tham_dinh(p, dong)
        except ocr.DaHuy:
            return None
        except (LoiNhap, ocr.LoiOCR, OSError, ValueError) as e:
            self._bao(QMessageBox.warning, str(e))
            return None
        self.ds_td = ds
        self.lb_file.setText(Path(p).name)
        self.o_so.setText(tt['so_chung_thu'])
        self.o_ngay.setText(tt['ngay'])
        self.o_don_vi.setText(tt['don_vi'])
        self._ghep_can_cu()
        self._ve_td()
        self.lb_xem.setText(('Cần xem lại (phần mềm không tự lấy):\n- ' + '\n- '.join(xem[:15])) if xem else '')
        return ds

    def _ve_td(self):
        self._dang_ve = True
        self.bang_td.setRowCount(len(self.ds_td))
        for i, m in enumerate(self.ds_td):
            c = QTableWidgetItem()
            c.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            c.setCheckState(Qt.CheckState.Checked if m.chon else Qt.CheckState.Unchecked)
            self.bang_td.setItem(i, 0, c)
            for j, v in ((1, m.ten), (2, m.dvt), (3, vn(m.don_gia))):
                it = QTableWidgetItem(str(v))
                if j == 3:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.bang_td.setItem(i, j, it)
            g = QTableWidgetItem(m.nguon_dong)
            g.setFlags(g.flags() & ~Qt.ItemFlag.ItemIsEditable)
            g.setToolTip(m.nguon_dong)
            self.bang_td.setItem(i, 4, g)
        self._dang_ve = False
        self.b_dua.setEnabled(bool(self.ds_td) and not self.chi_doc)

    def _sua_td(self, it):
        if self._dang_ve or it.row() >= len(self.ds_td):
            return
        m = self.ds_td[it.row()]
        c, t = it.column(), it.text().strip()
        if c == 0:
            m.chon = it.checkState() == Qt.CheckState.Checked
        elif c == 1:
            m.ten = ' '.join(t.split())
        elif c == 2:
            m.dvt = t
        elif c == 3:
            try:
                g = dgr.chuan_gia(t)
                m.don_gia = int(g) if g and '.' not in g else (float(g) if g else 0)
            except LoiNhap as e:
                self._bao(QMessageBox.warning, str(e))
                self._dang_ve = True
                it.setText(vn(m.don_gia))
                self._dang_ve = False

    def dua_vao(self) -> dict | None:
        if self.b_luu.isEnabled():
            if self.luu() is None:                      # quy ước đang sửa dở: lưu trước để không mất
                return None
        cc = self.o_can_cu.text().strip()
        if not cc:
            self._bao(QMessageBox.warning, 'Ghi căn cứ (chứng thư thẩm định giá, quyết định phê duyệt giá) trước khi đưa vào.')
            return None
        try:
            kq = dgr.them_tham_dinh(self.con, self.ds_td, cc)
        except LoiNhap as e:
            self._bao(QMessageBox.warning, str(e))
            return None
        self.da_luu = True
        self.nap()
        self.tab.setCurrentIndex(0)
        self._bao(QMessageBox.information, f'Đã đưa {kq["moi"]} mục mới, cập nhật giá {kq["cap_nhat"]} mục vào đơn giá riêng của '
                                              'dự án. Khi lập phương án: chọn nhanh mục có nhãn [Thẩm định].')
        return kq

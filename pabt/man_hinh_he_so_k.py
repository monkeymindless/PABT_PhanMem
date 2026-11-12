"""Thẻ "Hệ số K" của cửa sổ Bảng giá đất (logic: he_so_k.py): xem / sửa bảng hệ số K theo QĐ 03/2026/QĐ-UBND, nhập từ file
(Excel, Word, PDF có chữ, PDF ảnh / ảnh - nhận dạng chữ từng trang, nút Dừng) hoặc chữ dán, chọn dòng rồi lưu (file JSON của máy)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import he_so_k as hk
from .giao_dien import kieu_o_he_so_k
from .loi import LoiNhap

COT = [('chon', 'Lấy', 40), ('dia_ban', 'Địa bàn', 130), ('tt', 'TT', 45), ('loai_dat', 'Loại đất', 190), ('vi_tri', 'Vị trí', 55),
       ('he_so', 'Hệ số K', 70), ('tuyen_duong', 'Tuyến đường / khu vực', 220), ('diem_dau', 'Từ', 170), ('diem_cuoi', 'Đến', 170),
       ('ghi_chu', 'Ghi chú', 150)]
C_K = [k for k, _, _ in COT].index('he_so')


class KhungHeSoK(QWidget):
    """Bảng hệ số K: dòng đang lưu trên máy, hoặc dòng vừa đọc từ file / chữ dán (chưa lưu - cột Lấy chọn dòng sẽ lưu)."""
    da_luu = Signal()
    im_lang = False

    def __init__(self, parent=None, dia_ban: str = ''):
        super().__init__(parent)
        from .giao_dien import KieuNut, ap_kieu_nut
        self.nguon = ''
        self.chua_luu = False
        self.lb = QLabel()
        self.lb.setWordWrap(True)
        self.o_vb = QLineEdit(hk.van_ban())
        self.o_vb.setToolTip('Tên văn bản ghi ở căn cứ (cột Ghi chú mục Đất): "Hệ số K theo QĐ …"')
        self.o_db = QLineEdit()
        self.o_db.setPlaceholderText('Trống = địa bàn của bảng giá đất; nhiều xã cách nhau dấu phẩy')
        self.o_db.setMinimumWidth(260)
        self.o_loc = QLineEdit()
        self.o_loc.setPlaceholderText('Lọc: xã, tên đường, TT, vị trí…')
        h1 = QHBoxLayout()
        for nhan, w in (('Văn bản:', self.o_vb), ('Địa bàn:', self.o_db)):
            l = QLabel(nhan)
            l.setProperty('vai', 'nhan')
            h1.addWidget(l)
            h1.addWidget(w, 1 if w is self.o_vb else 0)
        h1.addWidget(self.o_loc, 1)
        self.b_file = QPushButton('Đọc từ file…')
        self.b_file.setToolTip('PDF Phụ lục I.1 / I.2 của QĐ 03/2026 (chọn nhiều file một lần: đất phi NN + đất NN), Excel, Word, PDF '
                               'ảnh / ảnh chụp (nhận dạng chữ). Chỉ lấy các địa bàn ở ô "Địa bàn" (trống = địa bàn của bảng giá đất '
                               'đang dùng). Dòng đọc được thay dòng cùng địa bàn / TT / loại đất trên bảng; kiểm tra rồi bấm Lưu.')
        self.b_dan = QPushButton('Dán chữ')
        self.b_dan.setToolTip('Lấy chữ đã chép (Ctrl+C) từ văn bản / bảng tính, tự nhận các dòng hệ số K')
        self.b_them = QPushButton('Thêm dòng')
        self.b_xoa = QPushButton('Xóa dòng')
        self.b_luu = QPushButton('Lưu hệ số K')
        ap_kieu_nut(self.b_luu, KieuNut.LUU)
        self.b_bo = QPushButton('Dùng bảng gắn sẵn')
        self.b_bo.setToolTip('Bỏ bảng hệ số K đã nhập trên máy này, dùng lại bảng gắn sẵn của QĐ 03/2026 (4 địa bàn của bảng giá gắn '
                             'sẵn). Phương án đã lập không đổi.')
        ap_kieu_nut(self.b_bo, KieuNut.NGUY_HIEM)
        self.b_file.clicked.connect(lambda: self.chon_file())
        self.b_dan.clicked.connect(lambda: self.dan_chu())
        self.b_them.clicked.connect(self.them_dong)
        self.b_xoa.clicked.connect(self.xoa_dong)
        self.b_luu.clicked.connect(lambda: self.luu())
        self.b_bo.clicked.connect(lambda: self.bo_het())
        h2 = QHBoxLayout()
        for b in (self.b_file, self.b_dan, self.b_them, self.b_xoa):
            h2.addWidget(b)
        h2.addStretch(1)
        h2.addWidget(self.b_bo)
        h2.addWidget(self.b_luu)
        self.bang = QTableWidget(0, len(COT))
        self.bang.setHorizontalHeaderLabels([t for _, t, _ in COT])
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.verticalHeader().setVisible(False)
        for c, (_, _, w) in enumerate(COT):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.itemChanged.connect(lambda *_: self._da_sua())
        lo = QVBoxLayout(self)
        lo.addWidget(self.lb)
        lo.addLayout(h1)
        lo.addLayout(h2)
        lo.addWidget(self.bang, 1)
        from .giao_dien import loc_khi_ngung_go
        loc_khi_ngung_go(self.o_loc, self.loc)
        self._da_nap = False                            # ~4.500 dòng gắn sẵn: dựng bảng khi thẻ hiện lần đầu (mở cửa sổ nhanh)
        self._chu_trang_thai()

    def showEvent(self, e):
        super().showEvent(e)
        self.nap()

    def nap(self):
        if not self._da_nap:
            self.hien(hk.tat_ca())

    def loc(self):
        from .lap_pa import bo_dau
        tu = bo_dau(self.o_loc.text()).split()
        for i in range(self.bang.rowCount()):
            chu = bo_dau(' '.join(self.bang.item(i, c).text() for c in range(1, len(COT)) if self.bang.item(i, c)))
            self.bang.setRowHidden(i, not all(t in chu for t in tu))

    # ------------------------------------------------ bảng
    def _chu_trang_thai(self, them: str = ''):
        chu = hk.tom_tat()
        if self.chua_luu:
            chu = 'CHƯA LƯU - kiểm tra từng hệ số, bỏ chọn dòng sai rồi bấm "Lưu hệ số K". ' + chu
        self.lb.setText((them + ' ' if them else '') + chu + '. Mục Đất của phương án tự lấy hệ số theo TT / tuyến đường của vị trí '
                        'đã chọn trong bảng giá (Phụ lục I; hệ số Phụ lục II, III nhân thêm ở ô Hệ số K khi có).')
        self.b_bo.setEnabled(hk.dang_thay() or self.chua_luu)

    def _da_sua(self):
        if not getattr(self, '_dang_hien', False):
            self.chua_luu = True

    def hien(self, dong: list, chon: bool = True):
        self._da_nap = True
        self._dang_hien = True
        self.bang.setUpdatesEnabled(False)
        try:
            self.bang.setRowCount(0)
            for r in dong:
                self._them(r, chon)
        finally:
            self.bang.setUpdatesEnabled(True)
            self._dang_hien = False
        if self.o_loc.text().strip():
            self.loc()

    def _them(self, r: dict, chon: bool = True):
        i = self.bang.rowCount()
        self.bang.insertRow(i)
        it = QTableWidgetItem()
        it.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        it.setCheckState(Qt.CheckState.Checked if chon else Qt.CheckState.Unchecked)
        self.bang.setItem(i, 0, it)
        for c, (k, _, _) in enumerate(COT[1:], start=1):
            v = r.get(k, '')
            if k == 'loai_dat':
                v = hk.ten_loai_dat(v)
            elif k == 'he_so' and v:
                v = str(v).replace('.', ',')
            o = QTableWidgetItem(str(v or ''))
            if k == 'he_so':
                kieu_o_he_so_k(o)                           # 1.0.02: căn giữa, đậm, xanh trời
            elif k == 'tt':
                o.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.bang.setItem(i, c, o)

    def them_dong(self):
        self._them({'dia_ban': self.o_db.text().strip()})
        self.chua_luu = True
        self.bang.setCurrentCell(self.bang.rowCount() - 1, C_K)

    def xoa_dong(self):
        hang = sorted({i.row() for i in self.bang.selectedIndexes()}, reverse=True)
        for i in hang:
            self.bang.removeRow(i)
        if hang:
            self.chua_luu = True

    def lay_dong(self) -> list:
        self.nap()
        """Các dòng đang chọn (cột Lấy) đã chuẩn hóa; dòng hệ số không hợp lệ -> hk.LoiHeSoK nêu số dòng."""
        kq = []
        for i in range(self.bang.rowCount()):
            if self.bang.item(i, 0).checkState() != Qt.CheckState.Checked:
                continue
            r = {k: (self.bang.item(i, c).text() if self.bang.item(i, c) else '') for c, (k, _, _) in enumerate(COT) if c}
            d = hk.chuan_dong(r)
            if not d['he_so']:
                raise hk.LoiHeSoK(f'Dòng {i + 1}: hệ số K "{r["he_so"]}" không hợp lệ (số lớn hơn 0, vd 1,2).')
            kq.append(d)
        return kq

    # ------------------------------------------------ nhập
    def _bao(self, chu: str, loi: bool = True):
        if self.im_lang:
            self.lb.setText(chu)
            return
        from .thong_bao import TEN_UD
        (QMessageBox.warning if loi else QMessageBox.information)(self, TEN_UD, chu)

    def _nhan(self, dong: list, vb: str, nguon: str, cach: str, gop: bool = False):
        self.nap()
        if gop:                                         # thêm vào bảng đang có: dòng cùng khóa thay dòng cũ
            khoa = (lambda r: (hk._ten_xa(r['dia_ban']), r['tt'], r['loai_dat'], r['vi_tri'],
                               '' if r['tt'] != '' else r['tuyen_duong']))
            cu = {}
            for i in range(self.bang.rowCount()):
                r = hk.chuan_dong({k: (self.bang.item(i, c).text() if self.bang.item(i, c) else '')
                                   for c, (k, _, _) in enumerate(COT) if c})
                cu[khoa(r)] = r
            for r in dong:
                cu[khoa(r)] = r
            dong = list(cu.values())
        self.hien(dong)
        if vb:
            self.o_vb.setText(vb)
        self.nguon = nguon
        self.chua_luu = True
        self._chu_trang_thai(f'Đọc được {len(dong)} dòng hệ số K. {cach}')

    def chon_file(self, file=None):
        if not file:
            file, _ = QFileDialog.getOpenFileNames(
                self, 'Chọn văn bản hệ số K (chọn được nhiều file)', '',
                'Văn bản (*.xlsx *.xlsm *.docx *.pdf *.jpg *.jpeg *.png *.tif *.tiff *.csv *.txt);;PDF và ảnh (*.pdf *.jpg *.jpeg *.png)')
            if not file:
                return None
        ds = file if isinstance(file, (list, tuple)) else [file]
        kq = None
        for i, f in enumerate(ds):
            d = self.nap_file(f, gop=i > 0 or self.chua_luu or hk.co_du_lieu())
            kq = (kq or []) + (d or [])
        return kq

    def an_lenh_trung(self) -> None:
        """1.1.06 - "Đọc từ file…" và "Dùng bảng gắn sẵn" đặt ở cột trái thẻ "Bộ quy tắc & cập nhật giá đất" (mỗi lệnh một chỗ): ẩn ở
        đây; thẻ này còn Dán chữ, Thêm / Xóa dòng, Lưu. Hàm giữ nguyên (cột trái gọi chon_file / bo_het)."""
        for b in (self.b_file, self.b_bo):
            b.hide()
        self.lb_cot_trai = True

    def _chon_xa(self, dong: list, chon=None):
        """1.1.06: file có nhiều xã -> hộp tích chọn xã. Tích sẵn: xã ở ô Địa bàn; ô trống thì các xã của bảng giá đất đang dùng
        (đúng phạm vi đọc cũ). Trả các dòng của xã được chọn, None = Hủy."""
        from . import gia_dat_nq28 as nq
        from .man_hinh_chon_dia_ban import chon_dia_ban
        go = [x.strip() for x in self.o_db.text().split(',') if x.strip()] or nq.ds_xa()
        may = {}
        for r in hk.tat_ca():
            may[r.get('dia_ban') or ''] = may.get(r.get('dia_ban') or '', 0) + 1
        # so tên giữ dấu (khop_dia_ban, 1.0.90: "Lộc Thành" khác "Lộc Thạnh")
        return chon_dia_ban(self, dong, 'dia_ban', lambda x: any(hk.khop_dia_ban(x, g) for g in go),
                            lambda x: sum(n for k, n in may.items() if x and hk.khop_dia_ban(k, x)), 'hệ số K', chon)

    def nap_file(self, file, gop: bool = False, chon_xa=None):
        from PySide6.QtWidgets import QProgressDialog
        hop = [None]

        def bao(i, n):
            if self.im_lang:
                return
            if hop[0] is None:
                hop[0] = QProgressDialog('Đang đọc…', 'Dừng', 0, max(n, 1), self)
                hop[0].setWindowTitle('Đọc hệ số K')
                hop[0].setMinimumDuration(0)
            hop[0].setMaximum(max(n, 1))
            hop[0].setValue(min(i, n))
            hop[0].setLabelText(f'Đang nhận dạng trang {i} / {n}. Bấm Dừng để dùng các trang đã đọc.')
            QApplication.processEvents()

        def cho():
            return hop[0] is not None and hop[0].wasCanceled()

        # 1.1.06: ô Địa bàn trống -> đọc MỌI xã của file rồi người dùng tích chọn (trước: chỉ lấy xã của bảng giá đang dùng, xã
        # khác bị bỏ không báo). Chế độ im lặng không chọn xã (kiểm thử cũ): đọc như trước.
        hoi = chon_xa is not None or not self.im_lang
        db = self.o_db.text().strip() or ('*' if hoi else '')
        try:
            dong, vb, cach = hk.doc_file(file, db, bao, cho)
        except hk.LoiHeSoK as e:
            self._bao(str(e))
            return None
        finally:
            if hop[0] is not None:
                hop[0].close()
        if hoi:
            dong = self._chon_xa(dong, chon_xa)
            if dong is None:
                self._chu_trang_thai('Đã hủy: chưa đưa xã nào lên bảng.')
                return None
        self._nhan(dong, vb, str(file), cach, gop)
        return dong

    def dan_chu(self, chu: str | None = None):
        if chu is None:
            chu = QApplication.clipboard().text()
        dong, vb = hk.doc_chu(chu or '', self.o_db.text().strip())
        if not dong:
            self._bao('Chữ đã chép không có dòng hệ số K nào (cần loại đất / vị trí và hệ số dạng 1,2).')
            return None
        self._nhan(dong, vb, 'chữ dán', 'Chữ dán.', gop=self.chua_luu or hk.co_du_lieu())
        return dong

    # ------------------------------------------------ lưu
    def luu(self) -> bool:
        try:
            dong = self.lay_dong()
            if not dong:
                raise hk.LoiHeSoK('Chưa chọn dòng hệ số K nào để lưu.')
            from .man_hinh_don_gia import xin_quyen_sua
            if not xin_quyen_sua(self, self.im_lang):           # 1.0.56: chỉ quản trị sửa hệ số K
                raise hk.LoiHeSoK('Chưa lưu: cần quyền quản trị bộ đơn giá.')
            hk.ghi(dong, self.o_vb.text().strip(), self.nguon)
        except (hk.LoiHeSoK, LoiNhap, OSError) as e:
            self._bao(str(e))
            return False
        self.chua_luu = False
        self.hien(hk.tat_ca())
        self._chu_trang_thai('Đã lưu.')
        self.da_luu.emit()
        return True

    def bo_het(self, xac_nhan=None) -> bool:
        if xac_nhan is None:
            if self.im_lang:
                return False
            from .thong_bao import TEN_UD
            xac_nhan = QMessageBox.question(self, TEN_UD, 'Bỏ bảng hệ số K đã nhập, dùng lại bảng gắn sẵn? Phương án đã lập không '
                                            'đổi.') \
                == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return False
        from .man_hinh_don_gia import xin_quyen_sua
        if not xin_quyen_sua(self, self.im_lang):
            self._bao('Chưa đổi: cần quyền quản trị bộ đơn giá.')
            return False
        hk.xoa()
        self.chua_luu = False
        self.hien(hk.tat_ca())
        self._chu_trang_thai('Đã dùng lại bảng gắn sẵn.')
        self.da_luu.emit()
        return True

"""Hộp "Văn bản, biên bản" và "Đọc kết quả từ file" của màn hình Niêm yết (1.0.58) - logic ở van_ban_dot."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import du_thao, van_ban_dot as vbd
from .loi import LoiNhap
from .thong_bao import TEN_UD, chu_loi

LOC_FILE = 'Văn bản, biên bản (*.pdf *.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp *.doc *.docx *.xls *.xlsx *.xlsm);;Tất cả (*.*)'
LOI_DOC = (LoiNhap, OSError, ValueError)


class HopVanBanDot(QDialog):
    """Danh sách văn bản của một mục trong đợt + khung thêm / sửa; "Đọc từ file…" điền sẵn số hiệu, ngày, trích yếu."""
    im_lang = False

    def __init__(self, parent, con, dot_id: int, ten_dot: str, muc: str, chi_doc: bool = False):
        super().__init__(parent)
        self.con, self.dot_id, self.muc, self.chi_doc = con, dot_id, muc, chi_doc
        self.id_sua = None
        self.setWindowTitle(f'Văn bản, biên bản - {vbd.TEN_MUC[muc]} - {ten_dot}')
        self.resize(900, 600)
        lo = QVBoxLayout(self)
        self.bang = QTableWidget(0, 5)
        self.bang.setHorizontalHeaderLabels(['Loại văn bản', 'Số hiệu', 'Ngày', 'Nội dung', 'File'])
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.verticalHeader().setVisible(False)
        for c, w in enumerate((230, 110, 90, 260)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.currentCellChanged.connect(lambda r, *_: self._chon(r))
        self.bang.cellDoubleClicked.connect(lambda *_: self.mo_file())
        lo.addWidget(self.bang, 1)
        f = QFormLayout()
        self.o_loai = QComboBox()
        self.o_loai.setEditable(True)
        self.o_loai.addItems(vbd.LOAI_THEO_MUC[muc])
        self.o_so, self.o_ngay, self.o_file = QLineEdit(), QLineEdit(), QLineEdit()
        self.o_ngay.setPlaceholderText('dd/mm/yyyy')
        self.o_nd = QPlainTextEdit()
        self.o_nd.setMaximumHeight(90)
        self.o_nd.setPlaceholderText('Nội dung, thành phần, địa điểm, kết quả… gõ trực tiếp hoặc bấm "Đọc từ file…"')
        self.b_chon = QPushButton('Chọn file…')
        self.b_chon.clicked.connect(lambda: self.chon_file())
        self.b_doc = QPushButton('Đọc từ file…')
        self.b_doc.setToolTip('Chọn file PDF, ảnh scan, Word, Excel: phần mềm đọc số hiệu, ngày, trích yếu để điền sẵn (nhận dạng chữ ngay trên máy)')
        self.b_doc.clicked.connect(lambda: self.doc_tu_file())
        h = QHBoxLayout()
        h.addWidget(self.o_file, 1)
        h.addWidget(self.b_chon)
        h.addWidget(self.b_doc)
        for nhan, w in (('Loại văn bản:', self.o_loai), ('Số hiệu:', self.o_so), ('Ngày:', self.o_ngay), ('Nội dung:', self.o_nd), ('File:', h)):
            f.addRow(nhan, w)
        lo.addLayout(f)
        h = QHBoxLayout()
        self.b_moi, self.b_luu, self.b_xoa, self.b_mo = QPushButton('Soạn mới'), QPushButton('Lưu văn bản'), QPushButton('Xóa'), QPushButton('Mở file')
        self.b_moi.clicked.connect(lambda: self._xoa_o())
        self.b_luu.clicked.connect(lambda: self.luu())
        self.b_xoa.clicked.connect(lambda: self.xoa())
        self.b_mo.clicked.connect(lambda: self.mo_file())
        dong = QPushButton('Đóng')
        dong.clicked.connect(self.accept)
        for b in (self.b_moi, self.b_luu, self.b_xoa, self.b_mo):
            h.addWidget(b)
        h.addStretch(1)
        h.addWidget(dong)
        lo.addLayout(h)
        for b in (self.b_moi, self.b_luu, self.b_xoa, self.b_chon, self.b_doc):
            b.setEnabled(not chi_doc)
        self.nap()

    def _bao(self, chu):
        self.thong_bao_cuoi = chu
        if not self.im_lang:
            QMessageBox.warning(self, TEN_UD, chu)

    def nap(self):
        self.ds = vbd.ds(self.con, self.dot_id, self.muc)
        self.bang.setRowCount(len(self.ds))
        for r, x in enumerate(self.ds):
            for c, v in enumerate((x['loai'], x['so_hieu'], du_thao.hien_ngay(x['ngay']) if x['ngay'] else '', x['noi_dung'], Path(x['duong_dan']).name if x['duong_dan'] else '')):
                it = QTableWidgetItem(v)
                it.setToolTip(x['duong_dan'] if c == 4 else v)
                self.bang.setItem(r, c, it)

    def _xoa_o(self):
        self.id_sua = None
        self.bang.clearSelection()
        self.o_loai.setCurrentIndex(0)
        for o in (self.o_so, self.o_ngay, self.o_file):
            o.clear()
        self.o_nd.clear()

    def _chon(self, r: int):
        if not 0 <= r < len(self.ds):
            return
        x = self.ds[r]
        self.id_sua = x['id']
        self.o_loai.setCurrentText(x['loai'])
        self.o_so.setText(x['so_hieu'])
        self.o_ngay.setText(du_thao.hien_ngay(x['ngay']) if x['ngay'] else '')
        self.o_nd.setPlainText(x['noi_dung'])
        self.o_file.setText(x['duong_dan'])

    def chon_file(self, p=None):
        if p is None:
            p, _ = QFileDialog.getOpenFileName(self, 'Chọn file văn bản', '', LOC_FILE)
        if p:
            self.o_file.setText(str(p))
        return p

    def doc_tu_file(self, p=None) -> dict | None:
        p = self.chon_file(p)
        if not p:
            return None
        from . import ocr
        from .man_hinh_quan_ly import doc_co_tien_do
        try:
            kq = doc_co_tien_do(self, vbd.doc_thong_tin, p)
        except ocr.DaHuy:
            return None
        except (*LOI_DOC, ocr.LoiOCR) as e:
            self._bao(chu_loi('Không đọc được file (vẫn lưu đính kèm được)', e))
            return None
        if kq['so_hieu']:
            self.o_so.setText(kq['so_hieu'])
        if kq['ngay']:
            self.o_ngay.setText(kq['ngay'])
        if kq['noi_dung'] and not self.o_nd.toPlainText().strip():
            self.o_nd.setPlainText(kq['noi_dung'])
        return kq

    def luu(self) -> int | None:
        try:
            i = vbd.luu(self.con, self.dot_id, self.muc, self.o_loai.currentText(), self.o_so.text(), self.o_ngay.text(),
                        self.o_nd.toPlainText(), self.o_file.text(), self.id_sua)
        except LoiNhap as e:
            self._bao(str(e))
            return None
        self.nap()
        self._xoa_o()
        return i

    def xoa(self, xac_nhan=None):
        if self.id_sua is None:
            return
        if xac_nhan is None:
            xac_nhan = self.im_lang or QMessageBox.question(self, TEN_UD, 'Xóa văn bản này khỏi đợt? File gốc trên máy không bị xóa.') == QMessageBox.StandardButton.Yes
        if xac_nhan:
            try:
                vbd.xoa(self.con, self.id_sua)
            except LoiNhap as e:
                self._bao(str(e))
                return
            self._xoa_o()
            self.nap()

    def mo_file(self) -> bool:
        p = self.o_file.text().strip()
        if not p:
            return False
        from .man_hinh_ho_so_scan import mo_file
        ok = mo_file(p)
        if not ok:
            self._bao(f'Không mở được file: {p} (file đã chuyển, xóa, hoặc không phải loại văn bản).')
        return ok


class HopKetQuaFile(QDialog):
    """Xem trước kết quả đọc từ file theo từng hộ trong đợt; dòng không rõ kết quả không chọn sẵn. Áp dụng thì ghi, kèm lưu file vào văn bản của mục."""
    im_lang = False
    COT = ('Dùng', 'Hộ', 'Khớp theo', 'Kết quả', 'Nội dung đọc được (sửa được)', 'Dòng gốc')

    def __init__(self, parent, con, dot_id: int, muc: str, files: list, kq: dict):
        super().__init__(parent)
        self.con, self.dot_id, self.muc, self.files, self.kq = con, dot_id, muc, files, kq
        self.so_ghi = None
        self.setWindowTitle(f'Đọc kết quả từ file - {vbd.TEN_MUC[muc]}')
        self.resize(1050, 620)
        lo = QVBoxLayout(self)
        d = kq['dong']
        n = QLabel(f'Đọc {kq["tong_dong"]} dòng, nhận ra {len(d)} hộ trong đợt.' + (' File scan: đối chiếu kỹ chữ nhận dạng.' if kq['scan'] else '') +
                   ' Dòng không rõ kết quả không chọn sẵn.')
        n.setWordWrap(True)
        lo.addWidget(n)
        self.bang = QTableWidget(len(d), len(self.COT))
        self.bang.setHorizontalHeaderLabels(list(self.COT))
        self.bang.verticalHeader().setVisible(False)
        for c, w in enumerate((46, 190, 70, 130, 330)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.cb = []
        for r, x in enumerate(d):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked if x.chon else Qt.CheckState.Unchecked)
            self.bang.setItem(r, 0, chk)
            cb = QComboBox()
            cb.addItem('(giữ nguyên)', '')
            for k, t in du_thao.LOAI_Y_KIEN:
                if k != 'chua':
                    cb.addItem(t, k)
            cb.setCurrentIndex(max(0, cb.findData(x.loai)))
            cb.setEnabled(muc != 'doi_thoai')
            self.bang.setCellWidget(r, 3, cb)
            self.cb.append(cb)
            for c, v in ((1, x.ho_ten), (2, x.khop_theo), (5, x.nguon)):
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                it.setToolTip(v)
                self.bang.setItem(r, c, it)
            self.bang.setItem(r, 4, QTableWidgetItem(x.noi_dung))
        lo.addWidget(self.bang, 1)
        h = QFormLayout()
        self.o_ngay, self.o_dd = QLineEdit(), QLineEdit()
        self.o_ngay.setPlaceholderText('dd/mm/yyyy (trống = hôm nay)')
        if muc == 'doi_thoai':
            h.addRow('Ngày đối thoại:', self.o_ngay)
            h.addRow('Địa điểm:', self.o_dd)
        else:
            self.o_ngay.setVisible(False)
            self.o_dd.setVisible(False)
        lo.addLayout(h)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText('Ghi kết quả các dòng đã chọn')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo.addWidget(nut)

    def accept(self):
        for r, x in enumerate(self.kq['dong']):
            x.chon = self.bang.item(r, 0).checkState() == Qt.CheckState.Checked
            x.loai = self.cb[r].currentData()
            x.noi_dung = self.bang.item(r, 4).text().strip()
        try:
            self.so_ghi = vbd.ap_dung(self.con, self.dot_id, self.muc, self.kq['dong'], self.o_ngay.text().strip(), self.o_dd.text().strip())
            loai = next((t for t in vbd.LOAI_THEO_MUC[self.muc] if t.startswith(('Biên bản', 'Báo cáo'))), 'Văn bản khác')
            for f in self.files:
                vbd.luu(self.con, self.dot_id, self.muc, loai, noi_dung=f'Kết quả {self.so_ghi} hộ, nhập từ file', duong_dan=str(f))
        except LoiNhap as e:
            self.thong_bao_cuoi = str(e)
            if not self.im_lang:
                QMessageBox.warning(self, TEN_UD, str(e))
            return
        super().accept()

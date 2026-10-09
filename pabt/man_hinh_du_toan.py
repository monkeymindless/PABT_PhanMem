"""Màn hình dự toán / áp giá dự thảo kinh phí bồi thường, hỗ trợ (logic: du_toan.py). Dùng được khi chưa mở dự án nào
(đơn giá lấy theo bộ đơn giá đang dùng của máy)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout)

from . import du_toan
from .du_toan import DongDT, DuToan
from .lap_pa import DanhMuc, LoiNhap, doc_so
from .tien import D, KHONG, so_vn, tien_bang_chu, vn
from .giao_dien import con_tro_cho
from .thong_bao import chu_loi

TIEU_DE = 'Dự toán, áp giá dự thảo'
XAM, XANH = QColor('#F2F2F2'), QColor('#DDEBF7')
COT = [('muc', 'Mục', 45), ('ten', 'Hạng mục', 380), ('dvt', 'ĐVT', 60), ('khoi_luong', 'Khối lượng (%)', 100),
       ('don_gia', 'Đơn giá (đ)', 110), ('he_so', 'Hệ số / tỷ lệ', 80), ('thanh_tien', 'Thành tiền (đ)', 130), ('ma', 'Mã', 70),
       ('can_cu', 'Căn cứ, ghi chú', 300)]
SO = {'khoi_luong', 'don_gia', 'he_so', 'thanh_tien', 'muc'}


class HopTraNQ28(QDialog):
    """Chọn giá đất theo bảng giá NQ 28/2025 (đồng/m²)."""

    def __init__(self, parent=None, xa: str = '', loai_dat: str = ''):
        super().__init__(parent)
        from . import gia_dat_nq28 as nq
        self.nq = nq
        self.chon = None
        self.setWindowTitle('Tra giá đất - ' + nq.VAN_BAN)
        self.resize(1100, 560)
        self.cb_xa = QComboBox()
        self.cb_xa.addItem('Tất cả địa bàn', '')
        for x in nq.ds_xa():
            self.cb_xa.addItem(x, x)
        i = next((k for k in range(self.cb_xa.count()) if xa and nq.khop_xa(xa, self.cb_xa.itemData(k) or '')), 0)
        self.cb_xa.setCurrentIndex(i)
        self.cb_cot = QComboBox()
        for k, t in nq.COT:
            self.cb_cot.addItem(t, k)
        cot = nq.cot_cua_loai(loai_dat)
        if cot:
            self.cb_cot.setCurrentIndex([k for k, _ in nq.COT].index(cot))
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tên đường, điểm đầu / cuối, vị trí (MT, T1…K3)…')
        self.bang = QTableWidget(0, 6)
        self.bang.setHorizontalHeaderLabels(['Địa bàn', 'Tên đường', 'Từ', 'Đến', 'Vị trí', 'Giá (đồng/m²)'])
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.verticalHeader().setVisible(False)
        for c, w in enumerate((120, 260, 220, 220, 60, 120)):
            self.bang.setColumnWidth(c, w)
        self.bang.doubleClicked.connect(lambda *_: self.accept())
        h = QHBoxLayout()
        for w in (QLabel('Địa bàn:'), self.cb_xa, QLabel('Loại đất:'), self.cb_cot, self.o_tim):
            h.addWidget(w)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText('Lấy giá này')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        lo.addLayout(h)
        lo.addWidget(self.bang)
        lo.addWidget(nut)
        for s in (self.cb_xa.currentIndexChanged, self.cb_cot.currentIndexChanged, self.o_tim.textChanged):
            s.connect(lambda *_: self.loc())
        self.loc()

    def loc(self):
        nq = self.nq
        self.ds = nq.tim(self.cb_xa.currentData() or '', self.o_tim.text())[:500]
        cot = self.cb_cot.currentData()
        self.bang.setRowCount(len(self.ds))
        for r, x in enumerate(self.ds):
            for c, v in enumerate((x['xa'], x['ten_duong'], x['diem_dau'], x['diem_cuoi'], x['vi_tri'], vn(nq.gia_dong(x, cot)))):
                it = QTableWidgetItem(str(v))
                it.setToolTip(nq.mo_ta_vi_tri(x) if c == 4 else str(v))
                self.bang.setItem(r, c, it)

    def accept(self):
        r = self.bang.currentRow()
        if not 0 <= r < len(self.ds):
            return
        x, cot = self.ds[r], self.cb_cot.currentData()
        self.chon = (D(self.nq.gia_dong(x, cot)), self.nq.can_cu(x, cot))
        super().accept()


class HopDuToan(QDialog):
    im_lang = False

    def __init__(self, parent=None, con=None, file_du_an=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.con, self.file_du_an = con, file_du_an
        self.file = None
        self.dt = DuToan()
        self._dm = None
        self.setWindowTitle('Dự toán / áp giá dự thảo kinh phí bồi thường, hỗ trợ')
        self.resize(1360, 760)
        self.o_ten = QLineEdit()
        self.o_ten.setPlaceholderText('Tên dự án / công trình dự toán')
        self.o_dia_ban = QLineEdit()
        self.o_dia_ban.setPlaceholderText('Địa bàn (xã, phường) - dùng khi tra giá đất')
        self.o_dia_chi = QLineEdit()
        self.o_dia_chi.setPlaceholderText('Địa chỉ dự án trên Bảng khái toán, ví dụ: Khu phố Bà Hào, phường Trị An')
        h0 = QHBoxLayout()
        h0.setSpacing(8)
        for w, k in ((QLabel('Dự án:'), 0), (self.o_ten, 3), (QLabel('Địa bàn:'), 0), (self.o_dia_ban, 1),
                     (QLabel('Địa chỉ:'), 0), (self.o_dia_chi, 2)):
            if isinstance(w, QLabel):
                w.setProperty('vai', 'nhan')
            h0.addWidget(w, k)
        h1 = QHBoxLayout()
        nhan = QLabel('Lấy khối lượng:')
        nhan.setProperty('vai', 'nhan')
        h1.addWidget(nhan)
        for ten, ham, bat in (('Từ dự án đang mở', lambda: self.lay('du_an'), con is not None),
                              ('Từ file dự án .pabt…', lambda: self.lay('pabt'), True),
                              ('Từ file PABT Excel…', lambda: self.lay('excel'), True),
                              ('Từ danh sách thô…', lambda: self.lay('tho'), True)):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            b.setEnabled(bat)
            h1.addWidget(b)
        h1.addStretch(1)
        for ten, ham in (('Áp đơn giá hiện hành', lambda: self.ap_gia_hien_hanh()),
                         ('Thêm chi phí 2,5% và dự phòng 10%', lambda: self.them_chi_phi())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            h1.addWidget(b)
        self.bang = QTableWidget(0, len(COT))
        self.bang.setHorizontalHeaderLabels([c[1] for c in COT])
        for i, c in enumerate(COT):
            self.bang.setColumnWidth(i, c[2])
        self.bang.horizontalHeader().setSectionResizeMode(len(COT) - 1, QHeaderView.ResizeMode.Stretch)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setWordWrap(True)
        self.bang.setAlternatingRowColors(True)
        self.bang.cellChanged.connect(self._doi_o)
        # ---- thêm đất (mục 1): loại đất xổ xuống (dùng chung danh sách loại đất của phương án hộ), diện tích, đơn giá
        from .giao_dien import mo_danh_sach
        from .loai_dat import ds_chon
        self.cb_loai_dat = QComboBox()
        self.cb_loai_dat.setEditable(True)
        self.cb_loai_dat.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cb_loai_dat.setMaxVisibleItems(20)
        self.cb_loai_dat.setMinimumWidth(320)
        for ma, nhan in ds_chon(con):
            self.cb_loai_dat.addItem(nhan, ma)
        self.cb_loai_dat.setCurrentIndex(-1)
        self.cb_loai_dat.lineEdit().setPlaceholderText('Loại đất (▼ chọn, hoặc gõ mã: CLN, ONT…)')
        mo_danh_sach(self.cb_loai_dat)
        self.o_dt_dat = QLineEdit()
        self.o_dt_dat.setPlaceholderText('Diện tích (m²), =12*30')
        self.o_dt_dat.setMaximumWidth(170)
        self.o_gia_dat = QLineEdit()
        self.o_gia_dat.setPlaceholderText('Đơn giá (đ/m²)')
        self.o_gia_dat.setMaximumWidth(170)
        self.o_gia_dat.returnPressed.connect(lambda: self.them_dat())
        self.o_dt_dat.returnPressed.connect(lambda: self.them_dat())
        h_dat = QHBoxLayout()
        nhan = QLabel('Thêm đất:')
        nhan.setProperty('vai', 'nhan')
        h_dat.addWidget(nhan)
        h_dat.addWidget(self.cb_loai_dat, 2)
        h_dat.addWidget(self.o_dt_dat, 1)
        h_dat.addWidget(self.o_gia_dat, 1)
        for ten, ham in (('Tra giá NQ 28…', lambda: self._tra_gia_o_dat()), ('Thêm đất vào mục 1', lambda: self.them_dat())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            h_dat.addWidget(b)
        h_dat.addStretch(1)
        h2 = QHBoxLayout()
        for ten, ham in (('Thêm từ danh mục…', lambda: self.them_danh_muc()), ('Thêm dòng', lambda: self.them_dong()),
                         ('Tra giá đất NQ 28…', lambda: self.tra_gia_dat()), ('Xóa dòng', lambda: self.xoa_dong())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            h2.addWidget(b)
        h2.addStretch(1)
        self.lb_tong = QLabel('')
        self.lb_tong.setWordWrap(True)
        self.lb_tong.setStyleSheet('QLabel { font-size: 14px; padding: 8px 10px; background: #EAF2FB; border: 1px solid #D3E2F1; '
                                   'border-radius: 6px; }')
        h3 = QHBoxLayout()
        for ten, ham in (('Mở dự toán…', lambda: self.mo()), ('Lưu dự toán…', lambda: self.luu()),
                         ('Xuất Bảng khái toán (Excel)…', lambda: self.xuat_khai_toan()),
                         ('Xuất Bảng khái toán (PDF)…', lambda: self.xuat_khai_toan(pdf=True)),
                         ('Xuất bảng chi tiết (Excel)…', lambda: self.xuat())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            h3.addWidget(b)
        h3.addStretch(1)
        b = QPushButton('Đóng')
        b.clicked.connect(self.reject)
        h3.addWidget(b)
        ghi = QLabel('Mục 1 đất, 2 nhà - công trình, 3 cây trồng, 4 hỗ trợ, 5 thưởng, 6 chi phí khác (cột Khối lượng là %, tính trên '
                     'tổng mục 1-5). Thành tiền = khối lượng × đơn giá × hệ số, làm tròn như dự án. "Áp đơn giá hiện hành" thay '
                     'đơn giá các dòng có mã theo bộ đơn giá đang dùng (áp giá dự thảo cho dự án tương tự).')
        ghi.setWordWrap(True)
        lo = QVBoxLayout(self)
        lo.addLayout(h0)
        lo.addLayout(h1)
        lo.addLayout(h_dat)
        lo.addWidget(self.bang, 1)
        lo.addLayout(h2)
        lo.addWidget(self.lb_tong)
        lo.addWidget(ghi)
        lo.addLayout(h3)
        self._dang_ve = False
        self.o_ten.textChanged.connect(lambda t: setattr(self.dt, 'ten', t.strip()))
        self.o_dia_ban.textChanged.connect(lambda t: setattr(self.dt, 'dia_ban', t.strip()))
        self.o_dia_chi.textChanged.connect(lambda t: setattr(self.dt, 'dia_chi', t.strip()))
        self.ve()

    # ---------------------------------------------- danh mục đơn giá
    @property
    def dm(self) -> DanhMuc:
        if self._dm is None:
            if self.con is not None:
                self._dm = DanhMuc(self.con)
            else:
                from . import csdl, don_gia
                c = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
                try:
                    self._dm = DanhMuc(c)
                finally:
                    c.close()
        return self._dm

    def bao(self, chu: str, loi: bool = True):
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TIEU_DE, chu)

    # ---------------------------------------------- hiển thị
    def ve(self, chon: int | None = None):
        self._dang_ve = True
        try:
            self.dt.sap_xep()
            self.bang.setRowCount(len(self.dt.dong))
            for r, d in enumerate(self.dt.dong):
                pt = d.muc == 6 and d.phan_tram is not None
                gt = dict(muc=str(d.muc), ten=d.ten, dvt='%' if pt else d.dvt,
                          khoi_luong=so_vn(d.phan_tram) if pt else so_vn(d.khoi_luong),
                          don_gia=vn(self.dt.co_so_phan_tram()) if pt else vn(d.don_gia),
                          he_so='' if pt else so_vn(d.he_so), thanh_tien=vn(self.dt.thanh_tien(d)), ma=d.ma,
                          can_cu=d.can_cu + ('; ' if d.can_cu and d.ghi_chu else '') + d.ghi_chu)
                for c, (k, _, _) in enumerate(COT):
                    it = QTableWidgetItem(gt[k])
                    it.setToolTip(gt[k])
                    if k in SO:
                        it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    if k == 'thanh_tien' or (pt and k in ('don_gia', 'he_so', 'dvt')):
                        it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        it.setBackground(QBrush(XAM))
                    if k == 'thanh_tien':
                        f = QFont()
                        f.setBold(True)
                        it.setFont(f)
                    self.bang.setItem(r, c, it)
        finally:
            self._dang_ve = False
        self.bang.resizeRowsToContents()                 # chữ dài xuống dòng, hiện đủ nội dung
        if chon is not None and 0 <= chon < len(self.dt.dong):
            self.bang.setCurrentCell(chon, 1)
        if self.o_ten.text().strip() != self.dt.ten:
            self.o_ten.setText(self.dt.ten)
        if self.o_dia_ban.text().strip() != self.dt.dia_ban:
            self.o_dia_ban.setText(self.dt.dia_ban)
        if self.o_dia_chi.text().strip() != self.dt.dia_chi:
            self.o_dia_chi.setText(self.dt.dia_chi)
        self.lb_tong.setText(du_toan.mo_ta_tong(self.dt) + f'<br><i>Bằng chữ: {tien_bang_chu(self.dt.tong)}.</i>'
                             + (f'<br>Nguồn: {self.dt.nguon}' if self.dt.nguon else ''))

    def _doi_o(self, r: int, c: int):
        if self._dang_ve or not 0 <= r < len(self.dt.dong):
            return
        d = self.dt.dong[r]
        k = COT[c][0]
        text = self.bang.item(r, c).text()
        try:
            if k == 'muc':
                m = int(doc_so(text, 'Mục', cho_phep_trong=False))
                if m not in du_toan.TEN_MUC:
                    raise LoiNhap('Mục: 1 đến 6.')
                d.muc = m
                if m == 6 and d.phan_tram is None:
                    d.phan_tram = KHONG
            elif k == 'khoi_luong':
                v = doc_so(text, 'Khối lượng')
                if d.muc == 6 and d.phan_tram is not None:
                    d.phan_tram = v
                else:
                    d.khoi_luong = v
            elif k == 'don_gia':
                d.don_gia = doc_so(text, 'Đơn giá')
            elif k == 'he_so':
                d.he_so = doc_so(text, 'Hệ số') or D(1)
            elif k == 'can_cu':
                d.can_cu, d.ghi_chu = text.strip(), ''
            elif k in ('ten', 'dvt', 'ma'):
                setattr(d, k, ' '.join(text.split()))
        except LoiNhap as e:
            self.bao(str(e))
        self.ve(r)

    def _doc_dau(self):
        self.dt.ten = self.o_ten.text().strip()
        self.dt.dia_ban = self.o_dia_ban.text().strip()
        self.dt.dia_chi = self.o_dia_chi.text().strip()

    # ---------------------------------------------- lấy khối lượng
    def lay(self, nguon: str, file=None):
        if self.dt.dong and not self.im_lang and QMessageBox.question(
                self, TIEU_DE, 'Thay toàn bộ các dòng dự toán hiện có bằng khối lượng mới?') != QMessageBox.StandardButton.Yes:
            return None
        if nguon != 'du_an' and file is None:
            loc = {'pabt': 'Dự án PABT (*.pabt)', 'excel': 'File PABT Excel (*.xlsm *.xlsx)',
                   'tho': 'Danh sách Excel (*.xlsx *.xlsm)'}[nguon]
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn file', '', loc)
            if not file:
                return None
        try:
            with con_tro_cho():
                if nguon == 'du_an':
                    dt = du_toan.tu_du_an(self.con)
                elif nguon == 'pabt':
                    dt = du_toan.tu_file_pabt(file)
                elif nguon == 'excel':
                    dt = du_toan.tu_excel_pabt(file)
                else:
                    dt = du_toan.tu_ds_tho(file)
        except Exception as e:                      # file hỏng / không đúng mẫu
            self.bao(chu_loi('Không lấy được khối lượng', e))
            return None
        self.dt = dt
        self.file = None
        self.ve()
        return dt

    def ap_gia_hien_hanh(self):
        doi = du_toan.ap_don_gia_hien_hanh(self.dt, self.dm)
        self.ve()
        if doi:
            self.bao(f'Đã thay đơn giá {len(doi)} dòng theo bộ đơn giá hiện hành, ví dụ:\n' +
                     '\n'.join(f'- {t[:60]}: {vn(a)} -> {vn(b)}' for t, a, b in doi[:12]), loi=False)
        else:
            self.bao('Các dòng có mã đã đúng đơn giá hiện hành.', loi=False)
        return doi

    def them_chi_phi(self):
        self.dt.them_chi_phi_mac_dinh()
        self.ve()

    # ---------------------------------------------- dòng
    def them_danh_muc(self, m=None):
        if m is None:
            from .man_hinh import ChonDanhMuc
            dlg = ChonDanhMuc(self.dm, 3, self)
            dlg.cb_nhom.clear()
            for n, t in ((2, 'Nhà, công trình'), (3, 'Cây trồng'), (4, 'Hỗ trợ')):
                dlg.cb_nhom.addItem(t, n)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return None
            m = dlg.chon
        muc = m.nhom if m.nhom in (2, 3, 4) else 2
        don_gia = m.don_gia if (m.don_gia is not None and not (muc == 4 and m.don_gia < 100)) else KHONG
        self.dt.dong.append(DongDT(muc, m.ten, m.dvt, D(1) if muc == 4 else KHONG, don_gia, D(1), m.ma, m.can_cu))
        self.ve()
        r = max(i for i, d in enumerate(self.dt.dong) if d.ma == m.ma)
        self.bang.setCurrentCell(r, 3)
        return r

    def them_dong(self, muc: int = 1):
        r = self.bang.currentRow()
        if 0 <= r < len(self.dt.dong):
            muc = self.dt.dong[r].muc
        self.dt.dong.append(DongDT(muc, 'Hạng mục mới', 'm²' if muc == 1 else ''))
        self.ve()
        r = max(i for i, d in enumerate(self.dt.dong) if d.ten == 'Hạng mục mới')
        self.bang.setCurrentCell(r, 1)
        return r

    def them_dat(self, ma: str | None = None, dien_tich=None, don_gia=None, can_cu: str = ''):
        """Thêm một dòng đất (mục 1, nằm trên cùng bảng khái toán): loại đất, diện tích, đơn giá nhập tay."""
        from .loai_dat import ds_chon
        if ma is None:
            i = self.cb_loai_dat.currentIndex()
            chu = self.cb_loai_dat.currentText().strip()
            ma = self.cb_loai_dat.itemData(i) if i >= 0 and self.cb_loai_dat.itemText(i) == chu else chu.split('–')[0].strip()
        ma = (ma or '').upper()
        if not ma:
            self.bao('Chọn loại đất.', loi=False)
            return None
        try:
            dt = doc_so(self.o_dt_dat.text() if dien_tich is None else dien_tich, 'Diện tích', cho_phep_trong=False)
            gia = doc_so(self.o_gia_dat.text() if don_gia is None else don_gia, 'Đơn giá') or KHONG
        except LoiNhap as e:
            self.bao(str(e))
            return None
        ten = next((n.split('–', 1)[1].strip() for m, n in ds_chon(self.con) if m == ma), '')
        nhan = ten if ten.lower().startswith('đất') else (f'Đất {ten.lower()}' if ten else f'Đất {ma}')
        self.dt.dong.append(DongDT(1, f'{nhan} ({ma})', 'm²', dt, gia, D(1), ma,
                                   can_cu or getattr(self, '_can_cu_gia_dat', '')))
        self._can_cu_gia_dat = ''
        self.o_dt_dat.clear()
        self.o_gia_dat.clear()
        self.ve()
        r = max(i for i, d in enumerate(self.dt.dong) if d.muc == 1 and d.ma == ma)
        self.bang.setCurrentCell(r, 3)
        return r

    def _tra_gia_o_dat(self):
        """Tra giá NQ 28 cho ô đơn giá của hàng "Thêm đất"."""
        dlg = HopTraNQ28(self, self.o_dia_ban.text(), self.cb_loai_dat.currentData() or self.cb_loai_dat.currentText())
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.chon is not None:
            self.o_gia_dat.setText(vn(dlg.chon[0]))
            self._can_cu_gia_dat = dlg.chon[1]

    def tra_gia_dat(self, chon=None):
        r = self.bang.currentRow()
        if not 0 <= r < len(self.dt.dong):
            self.bao('Chọn dòng đất (mục 1) cần tra giá.', loi=False)
            return None
        d = self.dt.dong[r]
        if chon is None:
            dlg = HopTraNQ28(self, self.o_dia_ban.text(), d.ma or d.ten)
            if dlg.exec() != QDialog.DialogCode.Accepted or dlg.chon is None:
                return None
            chon = dlg.chon
        d.don_gia, d.can_cu = chon
        self.ve(r)
        return chon

    def xoa_dong(self):
        r = self.bang.currentRow()
        if 0 <= r < len(self.dt.dong):
            del self.dt.dong[r]
            self.ve(min(r, len(self.dt.dong) - 1))

    # ---------------------------------------------- lưu / mở / xuất
    def _thu_muc(self) -> str:
        return str(Path(self.file_du_an).parent) if self.file_du_an else ''

    def luu(self, file=None):
        self._doc_dau()
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu dự toán', str(self.file or Path(self._thu_muc()) /
                                                                         f'{self.dt.ten or "DuToan"}{du_toan.DUOI}'),
                                                  f'Dự toán PABT (*{du_toan.DUOI})')
            if not file:
                return None
        self.file = self.dt.luu(file)
        return self.file

    def mo(self, file=None):
        if file is None:
            file, _ = QFileDialog.getOpenFileName(self, 'Mở dự toán', self._thu_muc(), f'Dự toán PABT (*{du_toan.DUOI})')
            if not file:
                return None
        try:
            self.dt = DuToan.mo(file)
        except (OSError, ValueError, TypeError) as e:
            self.bao(chu_loi('Không mở được file dự toán', e))
            return None
        self.file = Path(file)
        self.ve()
        return self.dt

    def xuat_khai_toan(self, file=None, pdf: bool = False):
        """Bảng khái toán theo mẫu của đơn vị (Excel, kèm PDF nếu chọn - cần Microsoft Excel)."""
        self._doc_dau()
        if not self.dt.dong:
            self.bao('Chưa có dòng dự toán: lấy khối lượng hoặc thêm dòng trước.', loi=False)
            return None
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Xuất Bảng khái toán', str(Path(self._thu_muc()) /
                                                                                f'KhaiToan_{self.dt.ten or "PABT"}.xlsx'),
                                                  'File Excel (*.xlsx)')
            if not file:
                return None
        try:
            with con_tro_cho():
                kq = du_toan.xuat_khai_toan(self.dt, file, pdf=pdf)
        except Exception as e:                      # file đang mở trong Excel, không có Excel để xuất PDF...
            self.bao(chu_loi('Không xuất được Bảng khái toán', e))
            return None
        mo = kq['pdf'] or kq['excel']
        if kq['loi']:
            self.bao('Đã lưu Excel nhưng không xuất được PDF:\n' + '\n'.join(kq['loi'][:5]))
        elif not self.im_lang and QMessageBox.question(self, TIEU_DE, f'Đã xuất:\n{mo}\n\nMở file?') == \
                QMessageBox.StandardButton.Yes:
            from .in_an import mo_file
            mo_file(mo)
        return kq

    def xuat(self, file=None):
        self._doc_dau()
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Xuất dự toán ra Excel', str(Path(self._thu_muc()) /
                                                                                   f'DuToan_{self.dt.ten or "PABT"}.xlsx'),
                                                  'File Excel (*.xlsx)')
            if not file:
                return None
        try:
            p = du_toan.xuat_excel(self.dt, file)
        except OSError as e:
            self.bao(chu_loi('Không ghi được file', e))
            return None
        if not self.im_lang and QMessageBox.question(self, TIEU_DE, f'Đã xuất:\n{p}\n\nMở file?') == QMessageBox.StandardButton.Yes:
            from .in_an import mo_file
            mo_file(p)
        return p

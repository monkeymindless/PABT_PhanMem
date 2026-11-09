"""Quản lý bộ quy tắc giá đất (1.0.64): xem các gói, tạo gói mới khi có văn bản mới, sửa hệ số / yếu tố / công thức / câu giải trình trên bảng, xem khác gì gói gốc rồi mới lưu. Logic ở goi_gia_dat.py."""
from __future__ import annotations

import copy
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
                               QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from . import goi_gia_dat as gg

TIEU_DE = 'LARC - Bộ quy tắc giá đất'
COT_YT = ('Mã', 'Yếu tố ảnh hưởng', 'Hệ số', 'Áp cho', 'Mặt đường', 'Khóa', 'Căn cứ')
CHU_COT_YT = ('Mã không dấu, không trùng', 'Tên hiện ở bảng tính', '', 'nn: đất nông nghiệp; pnn: đất phi nông nghiệp; ca: cả hai', 'Tự áp khi chọn mặt đường có mã này', 'Ghi "có": tuyến đã có quy định riêng thì không nhân (chống nhân trùng)', '')
COT_THEM = ('Mã (K4…)', 'Tên hệ số', 'Mặc định', 'Căn cứ')
SUA_BANG = QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed | QAbstractItemView.EditTrigger.AnyKeyPressed


def _o(x) -> QTableWidgetItem:
    return QTableWidgetItem('' if x is None else str(x))


class HopChonXaGoiCai(QDialog):
    """Chọn xã / phường để đóng gói cài: đơn giá đất và hệ số K luôn đi cùng; bộ quy tắc kèm theo."""
    im_lang = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Chọn xã / phường đóng gói cài giá đất')
        self.resize(720, 520)
        self.chon = []
        lo = QVBoxLayout(self)
        lo.addWidget(QLabel('Mỗi địa bàn trong gói cài gồm đủ đơn giá đất và hệ số K. Bộ quy tắc giá đất đi kèm gói.'))
        hang = QHBoxLayout()
        self.b_het = QPushButton('Chọn tất cả đủ cặp')
        self.b_bo = QPushButton('Bỏ chọn')
        hang.addWidget(self.b_het)
        hang.addWidget(self.b_bo)
        hang.addStretch(1)
        lo.addLayout(hang)
        self.bang = QTableWidget(0, 4)
        self.bang.setHorizontalHeaderLabels(['Chọn', 'Địa bàn', 'Dòng đơn giá', 'Dòng hệ số K'])
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.verticalHeader().setVisible(False)
        self.bang.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        lo.addWidget(self.bang, 1)
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        lo.addWidget(self.lb)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText('Xuất gói cài…')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo.addWidget(nut)
        self.b_het.clicked.connect(self._chon_het)
        self.b_bo.clicked.connect(self._bo_het)
        self._nap()

    def _nap(self) -> None:
        self._ds = gg.ds_xa_cho_goi_cai()
        self.bang.setRowCount(len(self._ds))
        du = thieu = 0
        for i, x in enumerate(self._ds):
            ck = QTableWidgetItem()
            ck.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled if x['du']
                        else Qt.ItemFlag.ItemIsUserCheckable)
            ck.setCheckState(Qt.CheckState.Unchecked)
            if not x['du']:
                ck.setFlags(Qt.ItemFlag.NoItemFlags)
            self.bang.setItem(i, 0, ck)
            self.bang.setItem(i, 1, _o(x['ten'] + ('' if x['du'] else ' (thiếu một bên)')))
            self.bang.setItem(i, 2, _o(x['so_gia']))
            self.bang.setItem(i, 3, _o(x['so_k']))
            du += 1 if x['du'] else 0
            thieu += 0 if x['du'] else 1
        self.lb.setText(f'{du} địa bàn đủ cặp đơn giá + hệ số K; {thieu} địa bàn thiếu một bên (không chọn được).')

    def _chon_het(self) -> None:
        for i, x in enumerate(self._ds):
            if x['du']:
                self.bang.item(i, 0).setCheckState(Qt.CheckState.Checked)

    def _bo_het(self) -> None:
        for i in range(self.bang.rowCount()):
            it = self.bang.item(i, 0)
            if it is not None and it.flags() & Qt.ItemFlag.ItemIsEnabled:
                it.setCheckState(Qt.CheckState.Unchecked)

    def accept(self) -> None:
        self.chon = [self._ds[i]['ten'] for i in range(self.bang.rowCount())
                     if self.bang.item(i, 0) and self.bang.item(i, 0).checkState() == Qt.CheckState.Checked]
        if not self.chon:
            if not self.im_lang:
                QMessageBox.warning(self, TIEU_DE, 'Chọn ít nhất một xã / phường đủ cặp đơn giá đất và hệ số K.')
            return
        super().accept()


class HopGoiGiaDat(QDialog):
    """Trái: danh sách gói. Phải: nội dung gói đang chọn (gói gắn sẵn chỉ xem). self.da_doi: có lưu / xóa gói. im_lang: kiểm thử."""
    im_lang = False

    def __init__(self, parent=None, ma_chon: str = '', nhung: bool = False):
        super().__init__(parent)
        self._nhung = nhung
        if nhung:
            from PySide6.QtCore import Qt
            self.setWindowFlags(Qt.WindowType.Widget)
        self.setWindowTitle(TIEU_DE)
        self.resize(1240, 680)
        self.g = None
        self._luc_nap = None
        self.goc = None
        self.moi = False
        self.da_doi = False
        self._ds = []
        lo = QVBoxLayout(self)
        than = QHBoxLayout()
        lo.addLayout(than, 1)

        # ---- trái: danh sách gói + lệnh tạo, nhập
        trai = QVBoxLayout()
        self.ds = QTableWidget(0, 2)
        self.ds.setHorizontalHeaderLabels(['Gói (văn bản)', 'Hiệu lực từ'])
        self.ds.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ds.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ds.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ds.verticalHeader().setVisible(False)
        self.ds.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ds.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.ds.setFixedWidth(330)
        self.ds.currentCellChanged.connect(lambda r, *_: self._chon_dong(r))
        trai.addWidget(self.ds, 1)
        for ten, chu, tip, ham in (
                ('b_chep', 'Tạo gói mới từ gói này…', 'Văn bản mới chỉ đổi một phần: chép gói đang chọn rồi sửa', lambda: self.tao_tu_goi()),
                ('b_tu_k', 'Tạo gói từ bảng hệ số K đã nhập…', 'Đoạn đường và K1 lấy từ thẻ Hệ số K (đã đọc từ văn bản), kể cả xã mới; K3, công thức chép từ gói đang chọn', lambda: self.tao_tu_he_so_k()),
                ('b_nhap', 'Nhập gói quy tắc từ file…', 'File .json gói quy tắc do đơn vị khác hoặc đơn vị phát hành gửi; kiểm từng trường, không chạy mã', lambda: self.nhap_file()),
                ('b_xuat', 'Xuất gói quy tắc ra file…', 'Gửi gói quy tắc (không kèm bảng giá / hệ số K) cho đơn vị khác', lambda: self.xuat_file()),
                ('b_xuat_cai', 'Xuất gói cài (giá + hệ số K)…', 'Chọn xã / phường: đóng kèm đơn giá đất + hệ số K (luôn đi cùng) và bộ quy tắc thành file .larcgia để cài máy khác hoặc đóng vào bản mới', lambda: self.xuat_goi_cai()),
                ('b_nhap_cai', 'Nhập gói cài giá đất…', 'Nhận file .larcgia: cài bộ quy tắc + đơn giá đất + hệ số K của các xã trong gói', lambda: self.nhap_goi_cai()),
                ('b_xoa', 'Xóa gói', 'Xóa gói của máy; số đã áp vào hộ không đổi', lambda: self.xoa())):
            b = QPushButton(chu)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, h=ham: h())
            setattr(self, ten, b)
            trai.addWidget(b)
        than.addLayout(trai)

        # ---- phải: nội dung gói
        phai = QVBoxLayout()
        self.lb_trang_thai = QLabel('')
        self.lb_trang_thai.setWordWrap(True)
        phai.addWidget(self.lb_trang_thai)
        hang = QHBoxLayout()
        f1, f2 = QFormLayout(), QFormLayout()
        self.o_ma, self.o_ten, self.o_so_hieu, self.o_bang_gia, self.o_tu, self.o_den = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        self.o_so_hieu.setToolTip('Số hiệu ngắn, ghi vào giải trình và ô Ghi chú của dòng đất, ví dụ QĐ 03/2026/QĐ-UBND')
        self.o_tu.setPlaceholderText('dd/mm/yyyy')
        self.o_den.setPlaceholderText('Trống: còn hiệu lực')
        f1.addRow('Tên gói:', self.o_ten)
        f1.addRow('Số hiệu văn bản:', self.o_so_hieu)
        f1.addRow('Bảng giá đất:', self.o_bang_gia)
        f2.addRow('Mã gói:', self.o_ma)
        f2.addRow('Hiệu lực từ:', self.o_tu)
        f2.addRow('Hiệu lực đến:', self.o_den)
        hang.addLayout(f1, 2)
        hang.addLayout(f2, 1)
        phai.addLayout(hang)

        self.the = QTabWidget()
        # thẻ Quy tắc
        t1 = QWidget()
        v1 = QVBoxLayout(t1)
        g_ct = QGroupBox('Công thức: đơn giá = giá bảng giá nhân lần lượt các hệ số')
        h_ct = QHBoxLayout(g_ct)
        self.o_cong_thuc = QLineEdit()
        self.o_cong_thuc.setToolTip('Các hệ số nhân, cách nhau bằng dấu phẩy, ví dụ K1, K2, K3, K_KHAC, K4. Chỉ nhận dạng tích; công thức dạng khác cần cập nhật phần mềm.')
        self.sp_tron = QSpinBox()
        self.sp_tron.setRange(-6, 4)
        self.sp_tron.setToolTip('0: đến đồng; -3: đến nghìn đồng')
        self.ck_chuyen_tiep = QCheckBox('Có quy định chuyển tiếp (giữ giá đất cụ thể nếu cao hơn)')
        for w, co in ((QLabel('Hệ số:'), 0), (self.o_cong_thuc, 1), (QLabel('Làm tròn đơn giá:'), 0), (self.sp_tron, 0), (self.ck_chuyen_tiep, 0)):
            h_ct.addWidget(w, co)
        v1.addWidget(g_ct)
        v1.addWidget(QLabel('Yếu tố ảnh hưởng (K3): sửa trực tiếp trên bảng'))
        self.bang_yt = QTableWidget(0, len(COT_YT))
        self.bang_yt.setHorizontalHeaderLabels(COT_YT)
        self.bang_yt.verticalHeader().setVisible(False)
        hh = self.bang_yt.horizontalHeader()
        for c, cho in enumerate(CHU_COT_YT):
            self.bang_yt.horizontalHeaderItem(c).setToolTip(cho)
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch if c == 1 else (QHeaderView.ResizeMode.Interactive if c in (0, 4, 6) else QHeaderView.ResizeMode.ResizeToContents))
        for c, rong in ((0, 130), (4, 120), (6, 130)):
            self.bang_yt.setColumnWidth(c, rong)
        v1.addWidget(self.bang_yt, 2)
        h_yt = QHBoxLayout()
        self.b_them_yt = QPushButton('+ Yếu tố')
        self.b_them_yt.clicked.connect(lambda: self.them_dong(self.bang_yt, ('K3_MOI', '', '1', 'pnn', '', '', '')))
        self.b_bo_yt = QPushButton('Bỏ yếu tố')
        self.b_bo_yt.clicked.connect(lambda: self.bang_yt.removeRow(self.bang_yt.currentRow()))
        self.b_them_hs = QPushButton('+ Hệ số mới')
        self.b_them_hs.setToolTip('Văn bản đặt thêm hệ số (K4…): khai ở bảng dưới rồi thêm mã vào ô công thức')
        self.b_them_hs.clicked.connect(lambda: self.them_dong(self.bang_them, ('K4', '', '1', '')))
        self.b_bo_hs = QPushButton('Bỏ hệ số')
        self.b_bo_hs.clicked.connect(lambda: self.bang_them.removeRow(self.bang_them.currentRow()))
        for b in (self.b_them_yt, self.b_bo_yt, self.b_them_hs, self.b_bo_hs):
            h_yt.addWidget(b)
        h_yt.addStretch(1)
        v1.addLayout(h_yt)
        self.bang_them = QTableWidget(0, len(COT_THEM))
        self.bang_them.setHorizontalHeaderLabels(COT_THEM)
        self.bang_them.verticalHeader().setVisible(False)
        self.bang_them.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.bang_them.setColumnWidth(3, 200)
        self.bang_them.setMaximumHeight(96)
        v1.addWidget(self.bang_them)
        self.lb_doan = QLabel('')
        self.lb_doan.setWordWrap(True)
        v1.addWidget(self.lb_doan)
        self.the.addTab(t1, 'Quy tắc')
        # thẻ Câu giải trình
        t2 = QWidget()
        v2 = QVBoxLayout(t2)
        v2.addWidget(QLabel('Câu ghi vào nhật ký giải trình. Văn bản mới đổi điều khoản thì sửa ở đây. {so_hieu}, {bang_gia} và các ô trong ngoặc tự điền khi tính.'))
        self.bang_cau = QTableWidget(len(gg.CAU_CHU), 2)
        self.bang_cau.setHorizontalHeaderLabels(['Dùng ở đâu', 'Mẫu câu'])
        self.bang_cau.verticalHeader().setVisible(False)
        self.bang_cau.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.bang_cau.setColumnWidth(0, 290)
        self.bang_cau.setWordWrap(True)
        self.bang_cau.verticalHeader().setDefaultSectionSize(3 * self.fontMetrics().height() + 10)     # câu dài nhất 3 dòng
        v2.addWidget(self.bang_cau, 2)
        v2.addWidget(QLabel('Văn bản căn cứ của gói (mỗi dòng một văn bản; tự gộp vào danh sách căn cứ khi chọn gói):'))
        self.o_can_cu = QPlainTextEdit()
        v2.addWidget(self.o_can_cu, 1)
        self.the.addTab(t2, 'Câu giải trình, căn cứ')
        # thẻ So sánh
        t3 = QWidget()
        v3 = QVBoxLayout(t3)
        self.o_khac = QPlainTextEdit()
        self.o_khac.setReadOnly(True)
        v3.addWidget(self.o_khac)
        self.the.addTab(t3, 'Khác gói gốc')
        phai.addWidget(self.the, 1)
        than.addLayout(phai, 1)

        hn = QHBoxLayout()
        self.lb_luu_y = QLabel('Số đã áp vào hộ không tự đổi khi có gói mới: đơn giá và tên văn bản đã lưu ở dòng đất, V1 giữ nguyên.')
        self.lb_luu_y.setWordWrap(True)
        hn.addWidget(self.lb_luu_y, 1)
        self.b_kiem = QPushButton('Kiểm tra, so sánh')
        self.b_kiem.setToolTip('Kiểm các trường và liệt kê những điểm khác gói gốc, chưa lưu gì')
        self.b_kiem.clicked.connect(lambda: self.kiem(True))
        self.b_luu = QPushButton('Lưu gói')
        self.b_luu.clicked.connect(lambda: self.luu())
        d = QPushButton('Đóng')
        d.clicked.connect(self.reject)
        if nhung:
            d.hide()
        for b in (self.b_kiem, d, self.b_luu):
            hn.addWidget(b)
        lo.addLayout(hn)
        self.nap(ma_chon)

    # ------------------------------------------------ danh sách
    def nap(self, ma_chon: str = '') -> None:
        self._ds = gg.ds_goi()
        self.ds.blockSignals(True)
        self.ds.setRowCount(len(self._ds))
        for r, g in enumerate(self._ds):
            self.ds.setItem(r, 0, _o(g.get('ten', '') + (' (gắn sẵn)' if g.get('gan_san') else '')))
            self.ds.setItem(r, 1, _o(gg.ngay_vn(g.get('hieu_luc_tu'))))
        i = next((k for k, g in enumerate(self._ds) if g.get('ma') == ma_chon), 0)
        self.ds.setCurrentCell(i, 0)
        self.ds.blockSignals(False)
        self._chon_dong(i)

    def _chon_dong(self, r: int) -> None:
        if not 0 <= r < len(self._ds):
            return
        g = self._ds[r]
        if self.g is not None and g.get('ma') == self.g.get('ma') and not self.moi:
            return
        if self.chua_luu() and not self._hoi_bo():
            i = next((k for k, x in enumerate(self._ds) if x.get('ma') == self.g.get('ma')), 0)
            self.ds.blockSignals(True)
            self.ds.setCurrentCell(i, 0)
            self.ds.blockSignals(False)
            return
        self.dat_goi(g, gg.lay_goi(g.get('goc', '')) or gg._gan_san(), False)

    def chua_luu(self) -> bool:
        """Gói trên màn hình có gì chưa lưu (gói gắn sẵn chỉ xem: không)."""
        if self.g is None or self.g.get('gan_san'):
            return False
        return self.moi or self.gia_tri() != self._luc_nap

    def _hoi_bo(self) -> bool:
        if self.im_lang:
            return True
        return QMessageBox.question(self, TIEU_DE, 'Gói đang sửa chưa lưu. Bỏ các thay đổi?') == QMessageBox.StandardButton.Yes

    def reject(self) -> None:
        if not self.chua_luu() or self._hoi_bo():
            super().reject()

    def dat_goi(self, g: dict, goc: dict, moi: bool) -> None:
        """Hiện một gói. moi: gói chưa lưu (vừa tạo / vừa nhập)."""
        self.g, self.goc, self.moi = copy.deepcopy(g), goc, moi
        ro = bool(g.get('gan_san'))
        self.o_ma.setText(g.get('ma', ''))
        self.o_ten.setText(g.get('ten', ''))
        self.o_so_hieu.setText(g.get('so_hieu', ''))
        self.o_bang_gia.setText(g.get('bang_gia', ''))
        self.o_tu.setText(gg.ngay_vn(g.get('hieu_luc_tu')))
        self.o_den.setText(gg.ngay_vn(g.get('hieu_luc_den')))
        ct = g.get('cong_thuc', {})
        self.o_cong_thuc.setText(', '.join(ct.get('he_so', [])))
        self.sp_tron.setValue(int(ct.get('lam_tron', 0)))
        self.ck_chuyen_tiep.setChecked(bool((g.get('chuyen_tiep') or {}).get('bat')))
        self.bang_yt.setRowCount(0)
        for y in g.get('yeu_to', []):
            self.them_dong(self.bang_yt, (y['ma'], y['ten'], y['he_so'], y['ap_cho'], y.get('kich_hoat_ket_cau', ''), 'có' if y.get('khoa_neu_quy_dinh_rieng') else '', y.get('can_cu', '')))
        self.bang_them.setRowCount(0)
        for x in g.get('he_so_them') or []:
            self.them_dong(self.bang_them, (x['ma'], x.get('ten', ''), x.get('mac_dinh', 1), x.get('can_cu', '')))
        cau = g.get('cau_chu') or {}
        for r, (k, nhan) in enumerate(gg.CAU_CHU):
            o = _o(nhan)
            o.setToolTip(nhan)
            self.bang_cau.setItem(r, 0, o)
            self.bang_cau.setItem(r, 1, _o(cau.get(k, '')))
        self.o_can_cu.setPlainText('\n'.join(g.get('van_ban_can_cu') or []))
        n = sum(len(v) for v in g.get('dia_ban', {}).values())
        self.lb_doan.setText(f'Địa bàn: {", ".join(g.get("dia_ban", {}))} ({n} đoạn đường). Đoạn đường và K1 đổi bằng "Tạo gói từ bảng hệ số K" hoặc nhập file.')
        self.lb_trang_thai.setText('Gói gắn sẵn trong phần mềm: chỉ xem. Muốn đổi, bấm "Tạo gói mới từ gói này".' if ro else ('Gói mới, CHƯA LƯU.' if moi else 'Gói của máy, sửa được.'))
        for w in (self.o_ma, self.o_ten, self.o_so_hieu, self.o_bang_gia, self.o_tu, self.o_den, self.o_cong_thuc, self.o_can_cu):
            w.setReadOnly(ro)
        self.sp_tron.setEnabled(not ro)
        self.ck_chuyen_tiep.setEnabled(not ro)
        sua = QAbstractItemView.EditTrigger.NoEditTriggers if ro else SUA_BANG
        for b in (self.bang_yt, self.bang_them, self.bang_cau):
            b.setEditTriggers(sua)
        for b in (self.b_them_yt, self.b_bo_yt, self.b_them_hs, self.b_bo_hs, self.b_luu):
            b.setEnabled(not ro)
        self.b_xoa.setEnabled(not ro and not moi)
        self._luc_nap = self.gia_tri()
        self.kiem()

    @staticmethod
    def them_dong(bang, gt) -> None:
        r = bang.rowCount()
        bang.setRowCount(r + 1)
        for c, v in enumerate(gt):
            bang.setItem(r, c, _o(v))

    # ------------------------------------------------ đọc form
    @staticmethod
    def _chu(bang, r: int, c: int) -> str:
        it = bang.item(r, c)
        return it.text().strip() if it is not None else ''

    def gia_tri(self) -> dict:
        """Gói theo nội dung đang hiện trên màn hình."""
        g = copy.deepcopy(self.g)
        g.pop('gan_san', None)
        g.update(ma=self.o_ma.text().strip(), ten=self.o_ten.text().strip(), so_hieu=self.o_so_hieu.text().strip(), bang_gia=self.o_bang_gia.text().strip(),
                 hieu_luc_tu=gg._ngay(self.o_tu.text()), hieu_luc_den=gg._ngay(self.o_den.text()))
        g['cong_thuc'] = dict(g.get('cong_thuc', {}), he_so=[x.strip() for x in self.o_cong_thuc.text().replace('×', ',').split(',') if x.strip()], lam_tron=self.sp_tron.value())
        g['chuyen_tiep'] = dict(g.get('chuyen_tiep') or {}, bat=self.ck_chuyen_tiep.isChecked())
        g['van_ban_can_cu'] = [x.strip() for x in self.o_can_cu.toPlainText().splitlines() if x.strip()]
        cu = {y['ma']: y for y in g.get('yeu_to', [])}
        o = self._chu
        b = self.bang_yt
        g['yeu_to'] = [dict(cu.get(o(b, r, 0), {}), ma=o(b, r, 0), ten=o(b, r, 1), he_so=o(b, r, 2).replace(',', '.'), ap_cho=o(b, r, 3), kich_hoat_ket_cau=o(b, r, 4),
                            khoa_neu_quy_dinh_rieng=bool(o(b, r, 5)), can_cu=o(b, r, 6)) for r in range(b.rowCount())]
        b = self.bang_them
        g['he_so_them'] = [dict(ma=o(b, r, 0), ten=o(b, r, 1), mac_dinh=o(b, r, 2).replace(',', '.'), can_cu=o(b, r, 3)) for r in range(b.rowCount())]
        g['cau_chu'] = {k: self.bang_cau.item(r, 1).text() for r, (k, _) in enumerate(gg.CAU_CHU) if self.bang_cau.item(r, 1) is not None and self.bang_cau.item(r, 1).text().strip()}
        return g

    def kiem(self, mo_the: bool = False) -> list:
        """Hiện lỗi hoặc các điểm khác so với gói gốc. Trả danh sách lỗi."""
        g = self.gia_tri()
        loi = gg.kiem_goi(g)
        if loi:
            self.o_khac.setPlainText('CHƯA HỢP LỆ:\n' + '\n'.join(loi))
        else:
            self.o_khac.setPlainText('\n'.join(gg.so_sanh(self.goc or gg._gan_san(), g)) or '(Không khác gói gốc.)')
        if mo_the:
            self.the.setCurrentIndex(self.the.count() - 1)
        return loi

    def _bao(self, chu: str, loi: bool = True) -> None:
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TIEU_DE, chu)

    def _ma_moi(self) -> str:
        n = 1
        while gg.lay_goi(f'GOI_{date.today():%Y%m%d}_{n}') is not None:
            n += 1
        return f'GOI_{date.today():%Y%m%d}_{n}'

    def _hoi_ten(self):
        """(mã, tên, hiệu lực từ) cho gói mới; im_lang dùng giá trị mặc định. None: bỏ."""
        hom_nay = date.today().strftime('%d/%m/%Y')
        if self.im_lang:
            return self._ma_moi(), 'Gói mới', hom_nay
        ten, ok = QInputDialog.getText(self, TIEU_DE, 'Số hiệu văn bản mới (ví dụ QĐ 15/2027/QĐ-UBND):')
        if not ok or not ten.strip():
            return None
        tu, ok = QInputDialog.getText(self, TIEU_DE, 'Hiệu lực từ ngày (dd/mm/yyyy):', text=hom_nay)
        if not ok:
            return None
        return self._ma_moi(), ten.strip(), tu.strip()

    def _goi_dang_chon(self) -> dict:
        return self._ds[max(0, self.ds.currentRow())]

    # ------------------------------------------------ tạo, nhập
    def tao_tu_goi(self) -> bool:
        goc = self._goi_dang_chon()
        t = self._hoi_ten()
        if not t:
            return False
        self.dat_goi(gg.tao_goi_tu(goc, *t), goc, True)
        return True

    def tao_tu_he_so_k(self) -> bool:
        goc = self._goi_dang_chon()
        t = self._hoi_ten()
        if not t:
            return False
        try:
            self.dat_goi(gg.tao_goi_tu_he_so_k(goc, *t), goc, True)
        except gg.LoiGoi as e:
            self._bao(str(e))
            return False
        return True

    def nhap_file(self, file=None) -> bool:
        if file is None:
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn file gói quy tắc', '', 'Gói quy tắc (*.json)')
            if not file:
                return False
        try:
            g = gg.doc_file_goi(file)
        except gg.LoiGoi as e:
            self._bao(str(e))
            return False
        if g.get('ma') == gg.MA_GAN_SAN:
            g['ma'] = self._ma_moi()
        self.dat_goi(g, gg.lay_goi(g.get('goc', '')) or gg._gan_san(), True)
        return True

    def xuat_file(self, file=None) -> bool:
        if self.g is None:
            return False
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu gói quy tắc', f'{self.g.get("ma", "goi")}.json', 'Gói quy tắc (*.json)')
            if not file:
                return False
        try:
            gg.xuat_file_goi(self.g if self.g.get('gan_san') else self.gia_tri(), file)
        except OSError as e:
            self._bao(f'Không ghi được file: {e}')
            return False
        return True

    def xuat_goi_cai(self, file=None, ds_xa=None) -> bool:
        """Chọn xã (đơn giá + hệ số K đi cùng) rồi xuất file .larcgia kèm bộ quy tắc."""
        if ds_xa is None:
            h = HopChonXaGoiCai(self)
            h.im_lang = self.im_lang
            if self.im_lang:
                h._chon_het()
                h.accept()
                ds_xa = h.chon
            else:
                if h.exec() != QDialog.DialogCode.Accepted:
                    return False
                ds_xa = h.chon
        if not ds_xa:
            self._bao('Chưa chọn xã / phường nào.')
            return False
        if file is None:
            mau = 'GoiCai_GiaDat_' + ('_'.join(x.replace(' ', '')[:12] for x in ds_xa[:2]) or 'DongNai')
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu gói cài giá đất', mau + gg.DUOI_GOI_CAI,
                                                  f'Gói cài giá đất (*{gg.DUOI_GOI_CAI})')
            if not file:
                return False
        try:
            goc = self.g if self.g and not self.moi else gg._gan_san()
            if goc and not goc.get('gan_san') and self.g is goc:
                goc = self.gia_tri()
            ra = gg.xuat_goi_cai(file, ds_xa, goc)
        except (gg.LoiGoi, OSError) as e:
            self._bao(str(e))
            return False
        self._bao(f'Đã xuất gói cài {len(ds_xa)} địa bàn (đơn giá + hệ số K + bộ quy tắc):\n{ra}', loi=False)
        return True

    def nhap_goi_cai(self, file=None, bo_sung: bool = True) -> bool:
        if file is None:
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn gói cài giá đất', '', f'Gói cài giá đất (*{gg.DUOI_GOI_CAI})')
            if not file:
                return False
        try:
            xem = gg.doc_goi_cai(file)
        except gg.LoiGoi as e:
            self._bao(str(e))
            return False
        xa = ', '.join(xem['mo_ta'].get('xa') or [])
        if not self.im_lang:
            hoi = (f'Cài gói giá đất gồm {xem["mo_ta"].get("so_gia", 0)} dòng đơn giá và '
                   f'{xem["mo_ta"].get("so_k", 0)} dòng hệ số K của: {xa}?\n'
                   'Địa bàn trùng tên được thay; địa bàn khác trên máy giữ nguyên. Bộ quy tắc trong gói được lưu vào máy.')
            if QMessageBox.question(self, TIEU_DE, hoi) != QMessageBox.StandardButton.Yes:
                return False
        if not self._xin_quyen():
            return False
        try:
            kq = gg.nhap_goi_cai(file, bo_sung=bo_sung)
        except Exception as e:                                           # noqa: BLE001
            self._bao(str(e))
            return False
        self.da_doi = True
        self.nap(kq.get('goi_ma') or '')
        self._bao(f'Đã cài {len(kq.get("xa") or [])} địa bàn ({kq.get("so_gia", 0)} dòng giá, {kq.get("so_k", 0)} dòng hệ số K). '
                  'Cửa sổ Tính đơn giá đất bồi thường sẽ hiện đủ xã vừa cài.', loi=False)
        return True

    # ------------------------------------------------ lưu, xóa
    def _xin_quyen(self) -> bool:
        from .man_hinh_don_gia import xin_quyen_sua
        return xin_quyen_sua(self, im_lang=self.im_lang)

    def luu(self) -> bool:
        if self.g is None or self.g.get('gan_san'):
            return False
        loi = self.kiem(True)
        if loi:
            self._bao('Gói chưa hợp lệ:\n' + '\n'.join(loi[:12]))
            return False
        if not self._xin_quyen():
            return False
        g = self.gia_tri()
        if self.moi and gg.lay_goi(g['ma']) is not None and not self.im_lang and QMessageBox.question(
                self, TIEU_DE, f'Đã có gói mã {g["ma"]}. Thay gói đó bằng gói này?') != QMessageBox.StandardButton.Yes:
            return False
        try:
            gg.ghi_goi(g)
        except Exception as e:                                           # noqa: BLE001 - LoiGoi, thiếu quyền, lỗi ghi: báo rõ, không sập
            self._bao(str(e))
            return False
        self.da_doi = True
        self.g, self.moi = None, False
        self.nap(g['ma'])
        self._bao(f'Đã lưu gói {g["ten"]}. Áp dụng cho việc tính mới từ {gg.ngay_vn(g["hieu_luc_tu"])}; số đã áp vào hộ không đổi.', loi=False)
        return True

    def xoa(self, hoi: bool = True) -> bool:
        if self.g is None or self.g.get('gan_san') or self.moi:
            return False
        if hoi and not self.im_lang and QMessageBox.question(self, TIEU_DE, f'Xóa gói {self.g.get("ten")}? Số đã áp vào hộ không đổi.') != QMessageBox.StandardButton.Yes:
            return False
        if not self._xin_quyen():
            return False
        try:
            gg.xoa_goi(self.g['ma'])
        except Exception as e:                                           # noqa: BLE001
            self._bao(str(e))
            return False
        self.da_doi = True
        self.g, self.moi = None, False
        self.nap()
        return True

"""Hộp tra bảng giá đất NQ 28/2025/NQ-HĐND: chọn địa bàn, loại giá, tìm theo tên đường; chọn một dòng -> lấy giá."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import gia_dat_nq28 as nq
from .giao_dien import loc_khi_ngung_go
from .tien import vn

XANH = QColor('#DDEBF7')


class HopTraGiaDat(QDialog):
    def __init__(self, parent=None, xa: str = '', loai_dat: str = '', chi_xem: bool = False):
        super().__init__(parent)
        self.chon = None                 # (dòng, cột) đã chọn
        self.setWindowTitle('Tra bảng giá đất — ' + nq.tom_tat())
        self.resize(1300, 700)
        self.o_xa = QComboBox()
        self.o_xa.addItems(['(Tất cả địa bàn)'] + nq.ds_xa())
        for i, x in enumerate(nq.ds_xa(), start=1):
            if nq.khop_xa(xa, x):
                self.o_xa.setCurrentIndex(i)
        self.o_cot = QComboBox()
        for k, t in nq.COT:
            self.o_cot.addItem(t, k)
        c = nq.cot_cua_loai(loai_dat)
        if c:
            self.o_cot.setCurrentIndex(self.o_cot.findData(c))
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm tên đường, điểm đầu / cuối (không cần dấu): vd "768", "huong lo 15", "MT"')
        hang = QHBoxLayout()
        for nhan, w in (('Địa bàn:', self.o_xa), ('Loại giá:', self.o_cot), ('Tìm:', self.o_tim)):
            l = QLabel(nhan)
            l.setProperty('vai', 'nhan')
            hang.addWidget(l)
            hang.addWidget(w, 1 if w is self.o_tim else 0)
        self.bang = QTableWidget(0, 7)
        self.bang.setHorizontalHeaderLabels(['Địa bàn', 'TT', 'Tên đường', 'Điểm đầu → điểm cuối', 'Vị trí', 'Điều kiện', 'Giá (đ/m²)'])
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.bang.verticalHeader().setVisible(False)
        for c, w in enumerate((110, 45, 190, 300, 50, 380, 110)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.doubleClicked.connect(lambda *_: None if chi_xem else self.accept())
        self.lb = QLabel(nq.van_ban_dang_dung() + '. Cột Giá là đồng/m². '
                         + ('Nhấp đúp một dòng để lấy giá.' if not chi_xem else ''))
        self.lb.setWordWrap(True)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Close if chi_xem else
                               QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        if not chi_xem:
            nut.button(QDialogButtonBox.StandardButton.Ok).setText('Lấy giá dòng đang chọn')
            nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        else:
            nut.button(QDialogButtonBox.StandardButton.Close).setText('Đóng')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        lo.addLayout(hang)
        lo.addWidget(self.bang, 1)
        lo.addWidget(self.lb)
        lo.addWidget(nut)
        self.o_xa.currentIndexChanged.connect(self.ve)
        self.o_cot.currentIndexChanged.connect(self.ve)
        loc_khi_ngung_go(self.o_tim, self.ve)
        self.ve()

    def ve(self):
        xa = self.o_xa.currentText() if self.o_xa.currentIndex() > 0 else ''
        cot = self.o_cot.currentData()
        self.ds = nq.tim(xa, self.o_tim.text()) if xa or self.o_tim.text() else nq.tat_ca()
        if xa:
            self.ds = [r for r in self.ds if r['xa'] == xa]
        self.bang.setRowCount(len(self.ds))
        dam = QFont()
        dam.setBold(True)
        # 1.0.32: tỉnh dùng mô hình vị trí khác Đồng Nai (VT1-VT4, KV1-VT1…): cột Vị trí ghi tên vị trí, tô đậm vị trí đầu của mô hình
        mac_dinh = nq.la_mo_hinh_mac_dinh()
        dau = nq.ds_ma_vi_tri()[0]
        if not mac_dinh and self.bang.columnWidth(4) < 150:
            self.bang.setColumnWidth(4, 150)
        for i, r in enumerate(self.ds):
            vt = r['vi_tri']
            o = [r['xa'], str(r['tt']), r['ten_duong'], f'{r["diem_dau"]} → {r["diem_cuoi"]}', vt if mac_dinh else nq.ten_vi_tri(vt),
                 nq.mo_ta_vi_tri(r), vn(nq.gia_dong(r, cot))]
            for c, v in enumerate(o):
                it = QTableWidgetItem(v)
                it.setToolTip(nq.ten_vi_tri(vt) if c == 4 else v)
                if c in (1, 6):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if str(vt).strip().upper() == dau:
                    it.setBackground(QBrush(XANH))
                    it.setFont(dam)
                self.bang.setItem(i, c, it)

    def accept(self):
        i = self.bang.currentRow()
        if 0 <= i < len(self.ds):
            self.chon = (self.ds[i], self.o_cot.currentData())
        super().accept()


def khoi_phuc_bang(cha, xac_nhan=None, hien: bool = True):
    """Xóa bảng người dùng đã thay, dùng lại bảng gắn sẵn."""
    from PySide6.QtWidgets import QMessageBox
    from .thong_bao import TEN_UD
    if not nq.dang_thay():
        if hien:
            QMessageBox.information(cha, TEN_UD, 'Đang dùng bảng gắn sẵn: ' + ', '.join(nq.ds_xa()) + '.')
        return False
    if xac_nhan is None:
        if not hien or QMessageBox.question(
                cha, TEN_UD, 'Bỏ bảng giá đang dùng và trở lại bảng gắn sẵn?') != QMessageBox.StandardButton.Yes:
            return False
    elif not xac_nhan:
        return False
    nq.xoa_thay()
    if hien:
        QMessageBox.information(cha, TEN_UD, 'Đã dùng lại bảng gắn sẵn: ' + ', '.join(nq.ds_xa()) + '.')
    return True


class HopCapNhatGiaDat(QDialog):
    """Hai đường cập nhật bảng giá đất: web, rồi file Excel / Word / PDF khi web không ra giá.
    Ghi xong thì bốn địa bàn gắn sẵn không còn hiện."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.im_lang = False
        self.dong = []
        self.van_ban = ''
        self.nguon = ''
        self.setWindowTitle('Cập nhật bảng giá đất')
        self.resize(980, 640)
        self.o_xa = QLineEdit()
        self.o_xa.setPlaceholderText('Trị An, Trảng Bom, Nhơn Trạch, Vũng Tàu')
        self.o_tinh = QLineEdit()
        self.o_tinh.setPlaceholderText('Đồng Nai, Hồ Chí Minh, Lâm Đồng (gõ tên tỉnh cũ cũng được)')
        self.o_url = QLineEdit()
        self.o_url.setPlaceholderText('https://… trang nghị quyết bảng giá đất hoặc file phụ lục - không bắt buộc, phần mềm nhớ cho lần sau')
        self.o_url.setToolTip('Dán đường dẫn văn bản chính thức (Công báo, cổng thông tin tỉnh) khi tìm tự động không ra.\n'
                              'Đọc được giá thì đường dẫn được nhớ theo tỉnh (danh_ba_gia_dat.json), lần sau tự tải.')
        hang_url = QHBoxLayout()
        l_url = QLabel('Đường dẫn văn bản:')
        l_url.setProperty('vai', 'nhan')
        hang_url.addWidget(l_url)
        hang_url.addWidget(self.o_url, 1)
        hang = QHBoxLayout()
        for nhan, w in (('Xã / phường:', self.o_xa), ('Tỉnh / thành phố:', self.o_tinh)):
            l = QLabel(nhan)
            l.setProperty('vai', 'nhan')
            hang.addWidget(l)
            hang.addWidget(w, 1)
        self.b_web = QPushButton('Tải từ web')
        self.b_web.setToolTip('Tìm văn bản bảng giá đất theo xã và tỉnh. Không thấy bảng giá thì chuyển sang chọn file.')
        self.b_file = QPushButton('Chọn file Excel, Word, PDF…')
        self.b_file.setToolTip('Đọc bảng có cột Tên đường và Đất ở hoặc Đơn giá. Thay cả bảng gắn sẵn.')
        self.b_web.clicked.connect(self.tai_web)
        self.b_file.clicked.connect(self.chon_file)
        hang.addWidget(self.b_web)
        hang.addWidget(self.b_file)
        self.lb = QLabel(nq.tom_tat() + '. Bảng mới thay bốn địa bàn gắn sẵn trên máy này (mọi dự án), không sửa số tiền đã lập.')
        self.lb.setWordWrap(True)
        self.bang = QTableWidget(0, 5)
        self.bang.setHorizontalHeaderLabels(['Địa bàn', 'Tên đường', 'Điểm đầu → điểm cuối', 'Vị trí', 'Giá (đ/m²)'])
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.verticalHeader().setVisible(False)
        for c, w in enumerate((130, 200, 240, 70, 120)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Reset |
                               QDialogButtonBox.StandardButton.Close)
        self.b_ghi = nut.button(QDialogButtonBox.StandardButton.Ok)
        self.b_ghi.setText('Dùng bảng này')
        self.b_ghi.setEnabled(False)
        nut.button(QDialogButtonBox.StandardButton.Reset).setText('Dùng lại bảng gắn sẵn')
        nut.button(QDialogButtonBox.StandardButton.Close).setText('Đóng')
        nut.accepted.connect(self.ghi)
        nut.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self.khoi_phuc)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        lo.addWidget(self.lb)
        lo.addLayout(hang)
        lo.addLayout(hang_url)
        lo.addWidget(self.bang, 1)
        lo.addWidget(nut)

    def _bao(self, loai, chu: str):
        if self.im_lang:
            self.lb.setText(chu)
            return
        from .thong_bao import TEN_UD
        { 'canh_bao': QMessageBox.warning, 'tin': QMessageBox.information }[loai](self, TEN_UD, chu)

    def _hien(self, dong, vb, chu, nguon: str):
        self.dong, self.van_ban, self.nguon = dong, vb, nguon
        self.b_ghi.setEnabled(bool(dong))
        self.bang.setUpdatesEnabled(False)
        try:
            self.bang.setRowCount(len(dong))
            for i, r in enumerate(dong):
                gia_o = nq.gia_dong(r, 'dat_o')
                if gia_o:
                    cot_gia = vn(gia_o)
                else:
                    cot_gia = ''
                    for khoa, ten in (('nn_cay', 'nông nghiệp'), ('nn_rung_nts', 'rừng / nuôi trồng'),
                                      ('tmdv', 'thương mại'), ('sxkd', 'sản xuất')):
                        g = nq.gia_dong(r, khoa)
                        if g:
                            cot_gia = f'{vn(g)} · {ten}'
                            break
                o = [r['xa'], r['ten_duong'], f'{r["diem_dau"]} → {r["diem_cuoi"]}'.strip(' →'), r['vi_tri'], cot_gia]
                for c, v in enumerate(o):
                    it = QTableWidgetItem(v)
                    if c == 4:
                        it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.bang.setItem(i, c, it)
        finally:
            self.bang.setUpdatesEnabled(True)
        xs = ', '.join(dict.fromkeys(r['xa'] for r in dong))
        tk = any(r.get('tham_khao') for r in dong)
        self.lb.setText(
            ('GIÁ THAM KHẢO - chưa phải căn cứ pháp lý. ' if tk else '') +
            f'{len(dong)} dòng của {xs}. {chu} Nguồn: {nguon}. '
            'Kiểm tra vài dòng rồi bấm "Dùng bảng này". Bảng này chỉ lưu trên máy này.')

    def tai_web(self):
        from .cap_nhat_gia_dat import LoiWeb, tim_tren_web
        xa, tinh, url = self.o_xa.text().strip(), self.o_tinh.text().strip(), self.o_url.text().strip()
        if not xa:
            self._bao('canh_bao', 'Nhập tên xã hoặc phường.')
            return None
        self.lb.setText('Đang tìm bảng giá đất trên web…')
        try:
            if self.im_lang:
                dong, vb, chu, nguon = tim_tren_web(tinh, xa, url=url)
            else:
                from .giao_dien import chay_nen
                dong, vb, chu, nguon = chay_nen(self, lambda: tim_tren_web(tinh, xa, url=url), 'Đang tìm bảng giá đất')
        except LoiWeb as e:
            self.lb.setText(str(e))
            if self.im_lang:
                return None
            from PySide6.QtWidgets import QMessageBox
            from .thong_bao import TEN_UD
            hop = QMessageBox(QMessageBox.Icon.Question, TEN_UD,
                              'Chưa tải được bảng giá của địa bàn này.\n\n'
                              + str(e) + '\n\n'
                              'Bạn có file Excel, Word, PDF hoặc ảnh bảng giá trên máy thì bấm Có để đọc file đó.',
                              parent=self)
            co = hop.addButton('Có', QMessageBox.ButtonRole.YesRole)
            hop.addButton('Không', QMessageBox.ButtonRole.NoRole)
            hop.exec()
            if hop.clickedButton() is co:
                return self.chon_file()
            return None
        except Exception as e:
            self._bao('canh_bao', str(e))
            return None
        self._hien(dong, vb, chu, nguon)
        return dong

    def chon_file(self, file=None):
        if not file:
            file, _ = QFileDialog.getOpenFileName(
                self, 'Chọn bảng giá đất', '',
                'Bảng giá (*.xlsx *.xlsm *.docx *.pdf *.jpg *.jpeg *.png *.tif *.csv *.txt);;Excel (*.xlsx *.xlsm);;PDF và ảnh (*.pdf *.jpg *.jpeg *.png)')
            if not file:
                return None
        return self.nap_file(file)

    def nap_file(self, file):
        from PySide6.QtWidgets import QApplication, QProgressDialog
        from .cap_nhat_gia_dat import doc_file
        hop = [None]

        def bao(i, n):
            if self.im_lang:
                return
            if hop[0] is None:
                hop[0] = QProgressDialog('Đang đọc…', 'Dừng', 0, max(n, 1), self)
                hop[0].setWindowTitle('Đọc bảng giá')
                hop[0].setMinimumDuration(0)
            hop[0].setMaximum(max(n, 1))
            hop[0].setValue(min(i, n))
            hop[0].setLabelText(f'Đang đọc trang {i} / {n}. File lớn đọc từng trang, bấm Dừng để ngừng.')
            QApplication.processEvents()

        def cho():
            return hop[0] is not None and hop[0].wasCanceled()

        try:
            dong, vb, chu = doc_file(file, self.o_tinh.text().strip(), self.o_xa.text().strip(), bao, cho)
        except nq.LoiBangGia as e:
            self._bao('canh_bao', str(e))
            return None
        finally:
            if hop[0] is not None:
                hop[0].close()
        self._hien(dong, vb, chu, str(file))
        return dong

    def ghi(self) -> list | None:
        from .cap_nhat_gia_dat import ap_dung
        if not self.dong:
            return None
        if not self.im_lang:
            from PySide6.QtWidgets import QMessageBox
            from .thong_bao import TEN_UD
            xs = ', '.join(dict.fromkeys(r['xa'] for r in self.dong))
            if QMessageBox.question(
                    self, TEN_UD,
                    ('BẢNG NÀY LÀ GIÁ THAM KHẢO từ trang doanh nghiệp, chưa phải căn cứ pháp lý: căn cứ in trên phương án ghi '
                     'rõ "tham khảo". Đối chiếu nghị quyết bảng giá đất của tỉnh trước khi trình.\n\n'
                     if any(r.get('tham_khao') for r in self.dong) else '') +
                    f'Thay bảng giá đang dùng bằng {len(self.dong)} dòng của {xs}?\n'
                    'Bốn địa bàn gắn sẵn (Trị An, Tân An, Phú Lý, Tân Triều) sẽ không còn hiện.') \
                    != QMessageBox.StandardButton.Yes:
                return None
        try:
            xs = ap_dung(self.dong, self.van_ban, self.nguon)
        except (nq.LoiBangGia, OSError) as e:
            self._bao('canh_bao', str(e))
            return None
        self._bao('tin', 'Đã dùng bảng: ' + ', '.join(xs) + f' ({len(nq.tat_ca())} dòng).')
        return xs

    def khoi_phuc(self):
        if khoi_phuc_bang(self, True if self.im_lang else None, hien=not self.im_lang):
            self.dong = []
            self.bang.setRowCount(0)
            self.b_ghi.setEnabled(False)
            self.lb.setText(nq.tom_tat())

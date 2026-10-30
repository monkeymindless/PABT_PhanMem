"""Hộp tra bảng giá đất NQ 28/2025/NQ-HĐND: chọn địa bàn, loại giá, tìm theo tên đường; chọn một dòng -> lấy giá.
KhungCapNhatGiaDat: thẻ "Cập nhật, bổ sung giá đất" của cửa sổ Bảng giá đất (man_hinh_du_toan.HopTraNQ28)."""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

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


class KhungCapNhatGiaDat(QWidget):
    """Cập nhật / bổ sung bảng giá đất - thẻ thứ ba của cửa sổ Bảng giá đất (30/10/2026 người dùng: "đưa bộ công cụ cập nhật giá đất vào
    mục Bảng giá đất, không cần cửa sổ riêng"). Đọc web hoặc file Excel / Word / PDF (kể cả bản scan) -> bảng xem trước; lời văn của
    nghị quyết có hướng dẫn tính vị trí 2-4 ngoài bảng thì bảng "Quy tắc vị trí" liệt kê (sửa / thêm / xóa được) và các vị trí đó được
    dựng thêm từ vị trí 1 (quy_tac_vi_tri). Ghi: BỔ SUNG vào bảng đang dùng (giữ địa bàn khác, kể cả bốn địa bàn gắn sẵn) hoặc THAY toàn
    bộ. Tín hiệu da_ghi: bảng giá đang dùng đã đổi (cửa sổ nạp lại thẻ Bảng giá)."""
    da_ghi = Signal()
    COT_QT = ['Vị trí', 'So với vị trí', 'Tỷ lệ (%)', 'Loại đất', 'Không thấp hơn (đ/m²)', 'Câu trong văn bản']
    CACH_GHI = [('bo_sung', 'Bổ sung vào bảng đang dùng (giữ các địa bàn khác, thay địa bàn trùng tên)'),
                ('thay', 'Thay toàn bộ bảng đang dùng bằng bảng này')]

    def __init__(self, parent=None, xa: str = ''):
        super().__init__(parent)
        from .quy_tac_vi_tri import LOAI
        self.LOAI = LOAI
        self.im_lang = False
        self.dong = []
        self.kq = None                                  # kết quả đọc file (doc_file_day_du) - tính lại khi sửa quy tắc
        self.van_ban = ''
        self.nguon = ''
        self.o_xa = QLineEdit(xa)
        self.o_xa.setPlaceholderText('Trị An, Trảng Bom, Nhơn Trạch, Vũng Tàu')
        self.o_tinh = QLineEdit()
        self.o_tinh.setPlaceholderText('Đồng Nai, Hồ Chí Minh, Lâm Đồng (gõ tên tỉnh cũ cũng được)')
        self.o_url = QLineEdit()
        self.o_url.setPlaceholderText('https://… trang nghị quyết bảng giá đất hoặc file phụ lục - không bắt buộc, phần mềm nhớ cho lần sau')
        self.o_url.setToolTip('Dán đường dẫn văn bản chính thức (Công báo, cổng thông tin tỉnh) khi tìm tự động không ra.\n'
                              'Đọc được giá thì đường dẫn được nhớ theo tỉnh (danh_ba_gia_dat.json), lần sau tự tải.')
        hang = QHBoxLayout()
        for nhan, w in (('Xã / phường:', self.o_xa), ('Tỉnh / thành phố:', self.o_tinh)):
            l = QLabel(nhan)
            l.setProperty('vai', 'nhan')
            hang.addWidget(l)
            hang.addWidget(w, 1)
        self.b_file = QPushButton('Đọc file Excel, Word, PDF, ảnh…')
        self.b_file.setToolTip('Đọc bảng có cột Tên đường và Đất ở hoặc Đơn giá (PDF scan: nhận dạng chữ). Lời văn có hướng dẫn tính '
                               'vị trí 2, 3, 4 thì các vị trí đó được dựng thêm theo hướng dẫn.')
        self.b_web = QPushButton('Tải từ web')
        self.b_web.setToolTip('Tìm văn bản bảng giá đất theo xã và tỉnh. Không thấy bảng giá thì chuyển sang chọn file.')
        self.b_file.clicked.connect(lambda: self.chon_file())
        self.b_web.clicked.connect(lambda: self.tai_web())
        hang.addWidget(self.b_file)
        hang.addWidget(self.b_web)
        hang_url = QHBoxLayout()
        l_url = QLabel('Đường dẫn văn bản:')
        l_url.setProperty('vai', 'nhan')
        hang_url.addWidget(l_url)
        hang_url.addWidget(self.o_url, 1)
        self.lb = QLabel(nq.tom_tat() + '.')
        self.lb.setWordWrap(True)
        self.bang = QTableWidget(0, 6)
        self.bang.setHorizontalHeaderLabels(['Địa bàn', 'Tên đường', 'Điểm đầu → điểm cuối', 'Vị trí', 'Giá (đ/m²)', 'Cách tính'])
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.verticalHeader().setVisible(False)
        for c, w in enumerate((130, 200, 240, 70, 150, 260)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        # ---- quy tắc vị trí 2-4 trong lời văn
        self.khung_qt = QGroupBox('Quy tắc vị trí ngoài bảng (đọc trong lời văn nghị quyết - sửa, thêm, xóa được)')
        lo_qt = QVBoxLayout(self.khung_qt)
        self.bang_qt = QTableWidget(0, len(self.COT_QT))
        self.bang_qt.setHorizontalHeaderLabels(self.COT_QT)
        self.bang_qt.verticalHeader().setVisible(False)
        for c, w in enumerate((60, 105, 80, 230, 175)):
            self.bang_qt.setColumnWidth(c, w)
        self.bang_qt.horizontalHeader().setStretchLastSection(True)
        self.bang_qt.verticalHeader().setDefaultSectionSize(32)       # ô chọn Loại đất trong ô bảng không bị cắt
        self.bang_qt.setMinimumHeight(150)
        self.bang_qt.setToolTip('Ví dụ văn bản: "vị trí 2 bằng 70% giá đất vị trí 1". Sửa ô Tỷ lệ / Vị trí rồi bấm "Tính lại vị trí".')
        h_qt = QHBoxLayout()
        self.lb_qt = QLabel('Chưa có quy tắc. Văn bản ghi giá vị trí 2-4 bằng tỷ lệ của vị trí 1 mà phần mềm không đọc được (bản '
                            'scan mờ): bấm "+ Thêm quy tắc" và nhập theo văn bản.')
        self.lb_qt.setWordWrap(True)
        self.b_them_qt = QPushButton('+ Thêm quy tắc')
        self.b_xoa_qt = QPushButton('Xóa quy tắc')
        self.b_tinh = QPushButton('Tính lại vị trí')
        self.b_them_qt.clicked.connect(lambda: self.them_quy_tac())
        self.b_xoa_qt.clicked.connect(lambda: self.xoa_quy_tac())
        self.b_tinh.clicked.connect(lambda: self.tinh_lai())
        h_qt.addWidget(self.lb_qt, 1)
        h_qt.addStretch()
        for b in (self.b_them_qt, self.b_xoa_qt, self.b_tinh):
            h_qt.addWidget(b)
        lo_qt.addLayout(h_qt)
        lo_qt.addWidget(self.bang_qt)
        tach = QSplitter(Qt.Orientation.Vertical)
        tach.setChildrenCollapsible(False)
        tach.addWidget(self.bang)
        tach.addWidget(self.khung_qt)
        tach.setStretchFactor(0, 3)
        tach.setStretchFactor(1, 2)
        tach.setSizes([420, 260])
        # ---- ghi
        h_ghi = QHBoxLayout()
        l = QLabel('Cách ghi:')
        l.setProperty('vai', 'nhan')
        self.cb_cach = QComboBox()
        for k, t in self.CACH_GHI:
            self.cb_cach.addItem(t, k)
        self.b_ghi = QPushButton('Ghi vào bảng giá đất')
        self.b_ghi.setEnabled(False)
        self.b_ghi.clicked.connect(lambda: self.ghi())
        self.b_khoi_phuc = QPushButton('Dùng lại bảng gắn sẵn')
        self.b_khoi_phuc.setToolTip('Bỏ mọi bảng đã thay / bổ sung trên máy này, trở lại bốn địa bàn gắn sẵn.')
        self.b_khoi_phuc.clicked.connect(lambda: self.khoi_phuc())
        h_ghi.addWidget(l)
        h_ghi.addWidget(self.cb_cach, 1)
        h_ghi.addWidget(self.b_ghi)
        h_ghi.addSpacing(16)
        h_ghi.addWidget(self.b_khoi_phuc)
        lo = QVBoxLayout(self)
        lo.addWidget(self.lb)
        lo.addLayout(hang)
        lo.addLayout(hang_url)
        lo.addWidget(tach, 1)
        lo.addLayout(h_ghi)
        from .giao_dien import KieuNut, ap_kieu_nut
        ap_kieu_nut(self.b_ghi, KieuNut.CHINH)

    # ---------------------------------------------------------------- hiển thị
    def _bao(self, loai, chu: str):
        if self.im_lang:
            self.lb.setText(chu)
            return
        from .thong_bao import TEN_UD
        {'canh_bao': QMessageBox.warning, 'tin': QMessageBox.information}[loai](self, TEN_UD, chu)

    def _hien(self, dong, vb, chu, nguon: str):
        self.dong, self.van_ban, self.nguon = dong, vb, nguon
        self.b_ghi.setEnabled(bool(dong))
        self.bang.setUpdatesEnabled(False)
        vang = QBrush(QColor('#FFF4D6'))
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
                o = [r['xa'], r['ten_duong'], f'{r["diem_dau"]} → {r["diem_cuoi"]}'.strip(' →'), r['vi_tri'], cot_gia,
                     r.get('tinh_tu') or ('Theo bảng giá' if r.get('vi_tri') else '')]
                for c, v in enumerate(o):
                    it = QTableWidgetItem(str(v))
                    it.setToolTip(str(v))
                    if c == 4:
                        it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    if r.get('sinh_tu_quy_tac'):
                        it.setBackground(vang)
                    self.bang.setItem(i, c, it)
        finally:
            self.bang.setUpdatesEnabled(True)
        xs = ', '.join(dict.fromkeys(r['xa'] for r in dong))
        tk = any(r.get('tham_khao') for r in dong)
        sinh = sum(1 for r in dong if r.get('sinh_tu_quy_tac'))
        self.lb.setText(
            ('GIÁ THAM KHẢO - chưa phải căn cứ pháp lý. ' if tk else '') +
            f'{len(dong)} dòng của {xs}' + (f' (trong đó {sinh} dòng vị trí dựng theo hướng dẫn trong văn bản, nền vàng)' if sinh else '')
            + f'. {chu} Nguồn: {nguon}. Kiểm tra vài dòng rồi bấm "Ghi vào bảng giá đất".')

    def _ve_quy_tac(self, ds: list):
        b = self.bang_qt
        b.blockSignals(True)
        try:
            b.setRowCount(0)
            for q in ds:
                self._them_dong_qt(q)
        finally:
            b.blockSignals(False)
        self.lb_qt.setVisible(not ds)

    def _them_dong_qt(self, q):
        from decimal import Decimal
        b = self.bang_qt
        r = b.rowCount()
        b.insertRow(r)
        pt = format((q.ty_le * Decimal(100)).normalize(), 'f').replace('.', ',')
        for c, v in enumerate((str(q.vi_tri), str(q.so_voi), pt, None, vn(q.toi_thieu * 1000) if q.toi_thieu else '', q.cau)):
            if c == 3:
                cb = QComboBox()
                for k, t in self.LOAI.items():
                    cb.addItem(t, k)
                cb.setCurrentIndex(max(0, cb.findData(q.loai)))
                b.setCellWidget(r, c, cb)
                continue
            it = QTableWidgetItem(v)
            if c == 5:
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                it.setToolTip(v)
            else:
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            b.setItem(r, c, it)

    def quy_tac(self) -> list:
        """Quy tắc theo bảng (sau khi người dùng sửa). Dòng sai (vị trí / tỷ lệ không đọc được) bỏ qua."""
        from decimal import Decimal, InvalidOperation
        from .quy_tac_vi_tri import QuyTac, gon
        from .tien import doc_so_vn
        ra = []
        b = self.bang_qt
        for r in range(b.rowCount()):
            def o(c):
                it = b.item(r, c)
                return (it.text() if it is not None else '').strip()
            try:
                vt, sv = int(o(0)), int(o(1) or '1')
                tl = Decimal(o(2).replace('%', '').replace(',', '.')) / 100
                tt = int(doc_so_vn(o(4)) / 1000) if o(4) else 0
            except (ValueError, InvalidOperation, ArithmeticError):
                continue
            if not (1 <= sv < vt <= 5) or not (0 < tl <= 1):
                continue
            cb = b.cellWidget(r, 3)
            ra.append(QuyTac(vt, tl.normalize(), sv, cb.currentData() if cb is not None else '', tt, o(5)))
        return gon(ra)

    def them_quy_tac(self, vi_tri: int = 2, ty_le: str = '70', so_voi: int = 1, loai: str = ''):
        from decimal import Decimal
        from .quy_tac_vi_tri import QuyTac
        self._them_dong_qt(QuyTac(vi_tri, Decimal(ty_le.replace(',', '.')) / 100, so_voi, loai, 0, 'Nhập tay'))
        self.lb_qt.setVisible(False)
        self.bang_qt.setCurrentCell(self.bang_qt.rowCount() - 1, 2)

    def xoa_quy_tac(self):
        hang = sorted({i.row() for i in self.bang_qt.selectedIndexes()} or
                      ({self.bang_qt.currentRow()} if self.bang_qt.currentRow() >= 0 else set()), reverse=True)
        for r in hang:
            self.bang_qt.removeRow(r)
        self.lb_qt.setVisible(self.bang_qt.rowCount() == 0)

    def tinh_lai(self):
        """Dựng lại các vị trí theo quy tắc đang có trên bảng (bỏ các dòng đã dựng lần trước)."""
        from .quy_tac_vi_tri import ap_quy_tac
        goc = self.kq['dong_goc'] if self.kq else self.dong
        if not goc:
            self._bao('canh_bao', 'Chưa có bảng giá: đọc file hoặc tải từ web trước.')
            return None
        dong, them = ap_quy_tac(goc, self.quy_tac())
        chu = (self.kq or {}).get('chu', '')
        self._hien(dong, self.van_ban, chu + (f' Đã dựng {them} dòng vị trí theo quy tắc.' if them else ''), self.nguon)
        return dong

    # ---------------------------------------------------------------- đọc
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
        self.kq = {'dong_goc': dong, 'quy_tac': [], 'van_ban': vb, 'chu': chu}
        self._ve_quy_tac([])
        self._hien(dong, vb, chu, nguon)
        return dong

    def chon_file(self, file=None):
        if not file:
            file, _ = QFileDialog.getOpenFileName(
                self, 'Chọn bảng giá đất / nghị quyết', '',
                'Bảng giá (*.xlsx *.xlsm *.docx *.pdf *.jpg *.jpeg *.png *.tif *.csv *.txt);;Excel (*.xlsx *.xlsm);;'
                'PDF và ảnh (*.pdf *.jpg *.jpeg *.png)')
            if not file:
                return None
        return self.nap_file(file)

    def nap_file(self, file):
        from PySide6.QtWidgets import QApplication, QProgressDialog
        from .cap_nhat_gia_dat import ap_quy_tac_file, doc_file_day_du
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
            kq = doc_file_day_du(file, self.o_tinh.text().strip(), self.o_xa.text().strip(), bao, cho)
        except nq.LoiBangGia as e:
            self._bao('canh_bao', str(e))
            return None
        finally:
            if hop[0] is not None:
                hop[0].close()
        self.kq = kq
        self._ve_quy_tac(kq['quy_tac'])
        dong, them = ap_quy_tac_file(kq)
        chu = kq['chu'] + (f' Văn bản có hướng dẫn tính vị trí ngoài bảng ({len(kq["quy_tac"])} quy tắc, xem bảng "Quy tắc vị trí" '
                           'phía dưới).' if kq['quy_tac'] else '')
        self._hien(dong, kq['van_ban'], chu, str(file))
        return dong

    # ---------------------------------------------------------------- ghi
    def ghi(self) -> list | None:
        from .cap_nhat_gia_dat import ap_dung
        if not self.dong:
            return None
        bo_sung = self.cb_cach.currentData() == 'bo_sung'
        xs = ', '.join(dict.fromkeys(r['xa'] for r in self.dong))
        if not self.im_lang:
            from .thong_bao import TEN_UD
            hoi = (f'Bổ sung {len(self.dong)} dòng của {xs} vào bảng giá đang dùng?\nĐịa bàn trùng tên được thay, các địa bàn khác giữ '
                   'nguyên.' if bo_sung else
                   f'Thay bảng giá đang dùng bằng {len(self.dong)} dòng của {xs}?\nCác địa bàn khác (cả bốn địa bàn gắn sẵn) sẽ không '
                   'còn hiện.')
            if QMessageBox.question(
                    self, TEN_UD,
                    ('BẢNG NÀY LÀ GIÁ THAM KHẢO từ trang doanh nghiệp, chưa phải căn cứ pháp lý: căn cứ in trên phương án ghi '
                     'rõ "tham khảo". Đối chiếu nghị quyết bảng giá đất của tỉnh trước khi trình.\n\n'
                     if any(r.get('tham_khao') for r in self.dong) else '') + hoi) != QMessageBox.StandardButton.Yes:
                return None
        try:
            ra = ap_dung(self.dong, self.van_ban, self.nguon, bo_sung=bo_sung)
        except (nq.LoiBangGia, OSError) as e:
            self._bao('canh_bao', str(e))
            return None
        self._bao('tin', 'Đã ghi. Bảng giá đang dùng: ' + ', '.join(ra) + f' ({len(nq.tat_ca())} dòng).')
        self.da_ghi.emit()
        return ra

    def khoi_phuc(self):
        if khoi_phuc_bang(self, True if self.im_lang else None, hien=not self.im_lang):
            self.lb.setText(nq.tom_tat())
            self.da_ghi.emit()
            return True
        return False

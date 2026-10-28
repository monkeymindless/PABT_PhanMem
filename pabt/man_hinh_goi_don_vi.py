"""Hộp "Tạo gói cấu hình cho nhiều đơn vị" (Công cụ, người dùng 28/10/2026): chọn file danh sách đơn vị (Excel mẫu / .json), hồ sơ
nền, thư mục lưu -> xem trước từng đơn vị -> Tạo gói (mỗi đơn vị một .pabtcfg). Logic ở goi_don_vi (không Qt)."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import goi_don_vi as gd
from .giao_dien import KieuNut, ap_kieu_nut, con_tro_cho, hop_ket_qua
from .thong_bao import TEN_UD

NEN = [('Cấu hình nghiệp vụ của máy này (cùng tỉnh)', gd.NEN_MAY), ('Hồ sơ mặc định (trung tính)', gd.NEN_MAC_DINH),
       ('File hồ sơ của tỉnh (.json)…', 'file')]
COT_XEM = ('Dòng', 'Tên tổ chức', 'Tiêu đề bản in', 'Người ký', 'Tên file gói', 'Kiểm tra')
MAU_LOI = '#B83A3A'
MAU_LUU_Y = '#9A5A12'


class HopGoiDonVi(QDialog):
    im_lang = False                      # kiểm thử: không bật hộp chọn file / thông báo

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Tạo gói cấu hình cho nhiều đơn vị')
        self.resize(1020, 600)
        self.ket_qua = []
        v = QVBoxLayout(self)
        gt = QLabel('Mỗi dòng của file danh sách là một đơn vị (chi nhánh, đơn vị ở tỉnh khác) -> một gói .pabtcfg. Gửi gói cho '
                    'đơn vị đó: bấm đúp gói là phần mềm có đủ tên cơ quan, đơn vị lập, người ký. Cấu hình của máy này không đổi.')
        gt.setWordWrap(True)
        v.addWidget(gt)
        f = QFormLayout()
        self.o_file = QLineEdit()
        self.o_file.setPlaceholderText('File Excel danh sách đơn vị (.xlsx) hoặc .json')
        self.o_file.editingFinished.connect(self.nap)
        b_chon = QPushButton('Chọn…')
        b_chon.clicked.connect(lambda: self.chon_file())
        self.b_mau = QPushButton('Tạo file Excel mẫu…')
        self.b_mau.setToolTip('Ghi file Excel có sẵn các cột (sheet Don_vi) và sheet Huong_dan giải thích từng cột')
        self.b_mau.clicked.connect(lambda: self.tao_file_mau())
        f.addRow('Danh sách đơn vị:', self._hang(self.o_file, b_chon, self.b_mau))
        self.cb_nen = QComboBox()
        for ten, k in NEN:
            self.cb_nen.addItem(ten, k)
        self.cb_nen.setToolTip('Căn cứ pháp lý, mốc thời hạn, tỷ lệ kinh phí, thông số bản in của các gói lấy theo hồ sơ này; '
                               'thông tin cơ quan luôn lấy theo từng dòng của danh sách')
        self.cb_nen.activated.connect(self._doi_nen)
        self.o_nen = QLineEdit()
        self.o_nen.setReadOnly(True)
        self.o_nen.setPlaceholderText('(chọn "File hồ sơ của tỉnh" để dùng file .json)')
        f.addRow('Hồ sơ nền:', self._hang(self.cb_nen, self.o_nen))
        self.o_ra = QLineEdit()
        b_ra = QPushButton('Chọn…')
        b_ra.clicked.connect(lambda: self.chon_thu_muc())
        f.addRow('Lưu các gói vào:', self._hang(self.o_ra, b_ra))
        self.o_mau = QCheckBox('Kèm mẫu tờ trình đang dùng trên máy này')
        self.o_mau.setToolTip('Chỉ chọn khi mẫu tờ trình của máy này không ghi cố định tên đơn vị của bạn')
        f.addRow('', self.o_mau)
        v.addLayout(f)
        self.bang = QTableWidget(0, len(COT_XEM))
        self.bang.setHorizontalHeaderLabels(COT_XEM)
        self.bang.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.bang.verticalHeader().setVisible(False)
        h = self.bang.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c, r in ((0, 56), (2, 140), (3, 150), (4, 250), (5, 220)):
            self.bang.setColumnWidth(c, r)
        v.addWidget(self.bang, 1)
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        v.addWidget(self.lb)
        hn = QHBoxLayout()
        self.b_mo = QPushButton('Mở thư mục gói')
        self.b_mo.setEnabled(False)
        self.b_mo.clicked.connect(lambda: self.mo_thu_muc())
        self.b_tao = QPushButton('Tạo gói')
        ap_kieu_nut(self.b_tao, KieuNut.CHINH)
        self.b_tao.setEnabled(False)
        self.b_tao.clicked.connect(lambda: self.tao())
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        hn.addWidget(self.b_mo)
        hn.addStretch(1)
        hn.addWidget(self.b_tao)
        hn.addWidget(b_dong)
        v.addLayout(hn)

    @staticmethod
    def _hang(*w) -> QWidget:
        k = QWidget()
        h = QHBoxLayout(k)
        h.setContentsMargins(0, 0, 0, 0)
        for x in w:
            h.addWidget(x, 1 if isinstance(x, QLineEdit) else 0)
        return k

    def _bao(self, chu: str, loi: bool = False) -> None:
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TEN_UD, chu)

    # ---- chọn file / nền / thư mục
    def tao_file_mau(self, file=None):
        if file is None:
            if self.im_lang:
                return None
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu file Excel mẫu danh sách đơn vị',
                                                  str(Path.home() / 'Documents' / 'Danh_sach_don_vi_LARC.xlsx'), 'Excel (*.xlsx)')
            if not file:
                return None
        try:
            p = gd.tao_file_mau(file)
        except OSError as e:
            self._bao(f'Không ghi được file mẫu: {e}\n(file đang mở bằng Excel? đóng file rồi thử lại)', True)
            return None
        self.o_file.setText(str(p))
        self.nap()
        if not self.im_lang:
            from .in_excel import mo_file
            if QMessageBox.question(self, TEN_UD, f'Đã tạo file mẫu:\n{p}\n\nĐiền mỗi đơn vị một dòng ở sheet Don_vi, lưu lại rồi '
                                    'quay về hộp này bấm Tạo gói.\n\nMở file bằng Excel ngay?') == QMessageBox.StandardButton.Yes:
                mo_file(p)
        return p

    def chon_file(self, file=None):
        if file is None:
            if self.im_lang:
                return None
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn danh sách đơn vị', self.o_file.text() or str(Path.home() / 'Documents'),
                                                  'Danh sách đơn vị (*.xlsx *.xlsm *.json)')
            if not file:
                return None
        self.o_file.setText(str(file))
        self.nap()
        return file

    def _doi_nen(self, *_a) -> None:
        if self.cb_nen.currentData() == 'file' and not self.o_nen.text():
            if self.chon_nen() is None:
                self.cb_nen.setCurrentIndex(0)
        elif self.cb_nen.currentData() != 'file':
            self.o_nen.clear()
        self.nap()

    def chon_nen(self, file=None):
        if file is None:
            if self.im_lang:
                return None
            file, _ = QFileDialog.getOpenFileName(self, 'Chọn file hồ sơ địa phương của tỉnh', str(Path.home() / 'Documents'),
                                                  'Hồ sơ địa phương (*.json)')
            if not file:
                return None
        self.cb_nen.setCurrentIndex(self.cb_nen.findData('file'))
        self.o_nen.setText(str(file))
        self.nap()
        return file

    def nen(self):
        k = self.cb_nen.currentData()
        return self.o_nen.text() if k == 'file' else k

    def chon_thu_muc(self, thu_muc=None):
        if thu_muc is None:
            if self.im_lang:
                return None
            thu_muc = QFileDialog.getExistingDirectory(self, 'Lưu các gói cấu hình vào', self.o_ra.text() or str(Path.home()))
            if not thu_muc:
                return None
        self.o_ra.setText(str(thu_muc))
        return thu_muc

    # ---- xem trước, tạo
    def _o(self, r: int, c: int, chu: str, mau: str = '', goi_y: str = '') -> None:
        it = QTableWidgetItem(chu)
        it.setToolTip(goi_y or chu)
        if mau:
            from PySide6.QtGui import QColor
            it.setForeground(QColor(mau))
        self.bang.setItem(r, c, it)

    def nap(self) -> list:
        """Đọc danh sách + kiểm tra từng đơn vị trên hồ sơ nền (không ghi gì). Trả [(đơn vị, hồ sơ | None, lỗi, cảnh báo)]."""
        self.bang.setRowCount(0)
        self.ket_qua = []
        self.b_tao.setEnabled(False)
        f = self.o_file.text().strip()
        if not f:
            self.lb.setText('Chọn file danh sách đơn vị, hoặc bấm "Tạo file Excel mẫu…" rồi điền.')
            return []
        if not self.o_ra.text().strip():
            self.o_ra.setText(str(Path(f).parent / 'Goi_cau_hinh'))
        try:
            with con_tro_cho():
                ds = gd.doc_danh_sach(f)
                nen = gd.ho_so_nen(self.nen())
        except gd.LoiDonVi as e:
            self.lb.setText(str(e))
            return []
        xem = []
        for dv in ds:
            try:
                hs, cb = gd.ho_so_don_vi(dv['du_lieu'], nen)
                xem.append((dv, hs, '', cb))
            except gd.LoiDonVi as e:
                xem.append((dv, None, str(e), []))
        self.bang.setRowCount(len(xem))
        for r, (dv, hs, loi, cb) in enumerate(xem):
            bm = (hs or {}).get('co_quan', {}).get('ban_in_mac_dinh', {})
            self._o(r, 0, str(dv['dong']), goi_y=f'{Path(dv["nguon"]).name}, dòng {dv["dong"]}')
            self._o(r, 1, hs['co_quan']['ten'] if hs else str(dv['du_lieu'].get('ten', '')))
            self._o(r, 2, bm.get('don_vi_tieu_de', ''))
            self._o(r, 3, ' '.join(x for x in (bm.get('chuc_vu_ky', ''), bm.get('nguoi_ky', '')) if x))
            self._o(r, 4, gd.ten_file_goi(hs, hs.get('_ten_file', '')) if hs else '')
            self._o(r, 5, loi or ('Lưu ý: ' + ', '.join(cb) if cb else 'Đạt'), MAU_LOI if loi else (MAU_LUU_Y if cb else ''))
        dat = sum(1 for x in xem if x[1] is not None)
        if not xem:
            self.lb.setText('File danh sách chưa có đơn vị nào (dòng trống bị bỏ qua).')
        else:
            self.lb.setText(f'{len(xem)} đơn vị, {dat} đạt' +
                            (f', {len(xem) - dat} lỗi (sửa file danh sách, lưu lại rồi chọn lại file)' if dat < len(xem) else '') + '.')
        self.b_tao.setEnabled(dat > 0)
        self.ket_qua = xem
        return xem

    def tao(self, hien: bool = True) -> list:
        """Tạo gói cho các đơn vị (đọc lại file - người dùng có thể vừa sửa Excel). Trả kết quả goi_don_vi.tao_hang_loat."""
        f, ra = self.o_file.text().strip(), self.o_ra.text().strip()
        if not f or not ra:
            self._bao('Chọn file danh sách và thư mục lưu gói.', True)
            return []
        try:
            with con_tro_cho():
                kq = gd.tao_hang_loat(f, ra, nen=self.nen(), kem_mau=self.o_mau.isChecked())
        except (gd.LoiDonVi, OSError) as e:
            self._bao(f'Không tạo được gói: {e}', True)
            return []
        self.nap()
        self.b_mo.setEnabled(any(x['file'] for x in kq))
        tom, dong = gd.tom_tat(kq)
        hop_ket_qua(self, tom + f'\nThư mục: {ra}\nGửi mỗi gói cho đúng đơn vị: máy nhận bấm đúp gói (hoặc Công cụ → Nhập gói mẫu in '
                    '& cấu hình…) là xong, không cần cài lại phần mềm.', dong, 'Từng đơn vị',
                    canh_bao=any(x['loi'] for x in kq), hien=hien and not self.im_lang)
        return kq

    def mo_thu_muc(self) -> None:
        from .in_excel import mo_file
        if self.o_ra.text().strip() and Path(self.o_ra.text()).is_dir():
            mo_file(self.o_ra.text())


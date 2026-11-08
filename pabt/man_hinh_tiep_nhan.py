"""Hộp "Tiếp nhận & Kiểm tra pháp lý dự án" (1.0.04): 4 thẻ - (1) quy định thu hồi đất, chủ đầu tư, thời hạn chủ trương;
(2) 32 đầu mục hồ sơ pháp lý (5 nhóm) bấm tích; (3) kỹ thuật địa chính + quét bảng kê thửa Excel; (4) tổng hợp có / thiếu / cần
bổ sung, xác nhận đủ điều kiện / đúng tiến độ, xuất phiếu (.xlsx) và công văn (.docx). Chạy được khi chưa mở dự án nào (con None):
lưu / mở file .pabtpl; có dự án mở thì lưu thêm vào dự án. Logic ở tiep_nhan_phap_ly (không Qt).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QGridLayout, QGroupBox,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QScrollArea,
                               QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from . import tiep_nhan_phap_ly as tn
from .giao_dien import chu_hien, mau_theo_tong
from .thong_bao import TEN_UD, chu_loi

TEN_THE = ('1. Quy định thu hồi, chủ đầu tư, thời hạn', '2. Hồ sơ pháp lý (32 mục)', '3. Kỹ thuật địa chính',
           '4. Tổng hợp & xuất văn bản')
C_CO, C_ND, C_AD, C_GC = 0, 1, 2, 3


class HopTiepNhanPhapLy(QDialog):
    def __init__(self, con=None, file_du_an=None, parent=None, im_lang: bool = False, khoi_tao=None, du_lieu: dict | None = None):
        super().__init__(parent)
        self.con = con
        self.file_du_an = file_du_an
        self.im_lang = im_lang
        self.khoi_tao = khoi_tao                 # hàm(dict) -> mở "Dự án mới" từ hồ sơ này (cửa sổ chính gắn)
        self.file = ''                            # file .pabtpl đang mở / đã lưu
        self._dang_nap = False
        self.setWindowTitle('Tiếp nhận & Kiểm tra pháp lý hồ sơ đầu vào dự án')
        self.resize(1100, 680)
        d = du_lieu or (tn.doc_du_an(con) if con is not None else None) or tn.moi()
        if con is not None:
            d = tn.tu_du_an(d, con)
        self.d = tn.chuan(d)
        self.nut = {}
        self.tab = QTabWidget()
        self.tab.addTab(self._the_1(), TEN_THE[0])
        self.tab.addTab(self._the_2(), TEN_THE[1])
        self.tab.addTab(self._the_3(), TEN_THE[2])
        self.tab.addTab(self._the_4(), chu_hien(TEN_THE[3]))       # 1.0.51: hiện đúng dấu &
        self.tab.currentChanged.connect(lambda _: self.cap_nhat())
        self.lb_trang_thai = QLabel('')
        self.lb_trang_thai.setWordWrap(True)
        h = QHBoxLayout()
        for chu, ham in (('Mở tệp…', lambda: self.mo_tep()), ('Lưu tệp…', lambda: self.luu_tep()),
                         ('Nạp từ khái toán…', lambda: self.nap_khai_toan())):
            b = QPushButton(chu)
            b.clicked.connect(ham)
            self.nut[chu] = b
            h.addWidget(b)
        if con is not None:
            b = QPushButton('Lưu vào dự án')
            b.setToolTip('Lưu hồ sơ tiếp nhận vào file dự án đang mở (Thông tin dự án hiện trạng thái)')
            b.clicked.connect(lambda: self.luu_du_an())
            self.nut['Lưu vào dự án'] = b
            h.addWidget(b)
        h.addStretch(1)
        b = QPushButton('Khởi tạo Dự án Mới (.pabt) từ Hồ sơ này →')
        b.setToolTip('Mở hộp Dự án mới, điền sẵn tên dự án, chủ đầu tư, địa bàn từ hồ sơ tiếp nhận')
        b.clicked.connect(lambda: self.khoi_tao_du_an())
        b.setEnabled(khoi_tao is not None)
        from .giao_dien import KieuNut, ap_kieu_nut
        ap_kieu_nut(b, KieuNut.CHINH)
        self.nut['Khởi tạo'] = b
        h.addWidget(b)
        b = QPushButton('Đóng')
        b.clicked.connect(self.reject)
        h.addWidget(b)
        lo = QVBoxLayout(self)
        lo.addWidget(self.tab, 1)
        lo.addWidget(self.lb_trang_thai)
        lo.addLayout(h)
        self.nap(self.d)

    # ---------------------------------------------------------------- dựng thẻ
    def _the_1(self) -> QWidget:
        w = QWidget()
        lo = QHBoxLayout(w)
        trai = QWidget()
        f = QFormLayout(trai)
        self.o_da = {}
        for k, ten in tn.TRUONG_DU_AN:
            o = QLineEdit()
            o.textChanged.connect(lambda _=None: self._doi())
            self.o_da[k] = o
            f.addRow(f'{ten}:', o)
        self.cb_cdt = QComboBox()
        for k, ten in tn.LOAI_CDT:
            self.cb_cdt.addItem(ten, k)
        self.cb_cdt.currentIndexChanged.connect(lambda _=None: self._doi())
        f.addRow('Loại chủ đầu tư:', self.cb_cdt)
        g = QGroupBox('Căn cứ thu hồi đất')
        gl = QVBoxLayout(g)
        self.o_cc = {}
        for k, ten in tn.CAN_CU:
            o = QCheckBox(ten)
            o.toggled.connect(lambda _=None: self._doi())
            self.o_cc[k] = o
            gl.addWidget(o)
        f.addRow(g)
        cuon = QScrollArea()
        cuon.setWidgetResizable(True)
        cuon.setWidget(trai)
        phai = QGroupBox('Phân tích tự động: trách nhiệm của Tổ chức làm nhiệm vụ bồi thường, thời hạn')
        pl = QVBoxLayout(phai)
        self.lb_phan_tich = QLabel('')
        self.lb_phan_tich.setWordWrap(True)
        self.lb_phan_tich.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lb_phan_tich.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        pl.addWidget(self.lb_phan_tich, 1)
        lo.addWidget(cuon, 3)
        lo.addWidget(phai, 2)
        return w

    def _the_2(self) -> QWidget:
        w = QWidget()
        lo = QVBoxLayout(w)
        lo.addWidget(__import__('pabt.giao_dien').giao_dien.nhan_xuong_dong('Bấm ô "Đã có" để tích hồ sơ đã tiếp nhận; mục không áp dụng (theo loại chủ đầu tư / căn cứ) hiện mờ. '
                            '(*) = bắt buộc để đủ điều kiện triển khai. Cột Ghi chú sửa trực tiếp (số, ngày văn bản…).'))
        self.bang_hs = QTableWidget(0, 4)
        self.bang_hs.setHorizontalHeaderLabels(['Đã có', 'Nội dung hồ sơ', 'Áp dụng', 'Ghi chú (số, ngày văn bản)'])
        self.bang_hs.verticalHeader().setVisible(False)
        dau = self.bang_hs.horizontalHeader()
        dau.setSectionResizeMode(C_ND, QHeaderView.ResizeMode.Stretch)
        self.bang_hs.setColumnWidth(C_CO, 70)
        self.bang_hs.setColumnWidth(C_AD, 80)
        self.bang_hs.setColumnWidth(C_GC, 260)
        self.bang_hs.itemChanged.connect(self._sua_o_hs)
        from .giao_dien import cho_phep_sao_chep_bang
        cho_phep_sao_chep_bang(self.bang_hs)
        lo.addWidget(self.bang_hs, 1)
        self.dong_hs = []                         # dòng bảng -> mã mục (None: dòng nhóm)
        for nhom, ds in tn.NHOM_HO_SO:
            self.dong_hs.append(None)
            for m in ds:
                self.dong_hs.append(m)
        self.bang_hs.setRowCount(len(self.dong_hs))
        return w

    def _the_3(self) -> QWidget:
        w = QWidget()
        lo = QHBoxLayout(w)
        g = QGroupBox('10 tiêu chí kỹ thuật địa chính')
        gl = QVBoxLayout(g)
        self.o_kt = {}
        for k, ten in tn.KY_THUAT:
            o = QCheckBox(ten)
            o.toggled.connect(lambda _=None: self._doi())
            self.o_kt[k] = o
            gl.addWidget(o)
        gl.addStretch(1)
        lo.addWidget(g, 2)
        p = QGroupBox('Quét thử bảng kê thửa đất (Excel của đơn vị đo đạc) - không ghi vào dự án')
        pl = QVBoxLayout(p)
        b = QPushButton('Quét bảng kê thửa Excel…')
        b.clicked.connect(lambda: self.quet_excel())
        self.nut['Quét'] = b
        h = QHBoxLayout()
        h.addWidget(b)
        h.addStretch(1)
        pl.addLayout(h)
        self.lb_excel = QLabel('Chưa quét bảng kê.')
        self.lb_excel.setWordWrap(True)
        pl.addWidget(self.lb_excel)
        self.ds_excel = QListWidget()
        pl.addWidget(self.ds_excel, 1)
        lo.addWidget(p, 3)
        return w

    def _the_4(self) -> QWidget:
        w = QWidget()
        lo = QVBoxLayout(w)
        luoi = QGridLayout()
        self.ds_co, self.ds_thieu, self.ds_bo_sung = QListWidget(), QListWidget(), QListWidget()
        for i, (ten, ds) in enumerate((('(1) Dự án ĐÃ CÓ', self.ds_co), ('(2) Dự án CÒN THIẾU', self.ds_thieu),
                                       ('(3) CẦN BỔ SUNG', self.ds_bo_sung))):
            g = QGroupBox(ten)
            gl = QVBoxLayout(g)
            ds.setWordWrap(True)
            ds.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            gl.addWidget(ds)
            luoi.addWidget(g, 0, i)
            luoi.setColumnStretch(i, 1)
        lo.addLayout(luoi, 1)
        g = QGroupBox('Xác nhận')
        gl = QVBoxLayout(g)
        self.o_du = QCheckBox('Dự án ĐỦ ĐIỀU KIỆN triển khai công tác bồi thường, hỗ trợ, tái định cư')
        self.o_tien_do = QCheckBox('Dự án ĐẢM BẢO ĐÚNG TIẾN ĐỘ (thời hạn chủ trương, hiệu lực Nghị quyết HĐND)')
        for o in (self.o_du, self.o_tien_do):
            o.toggled.connect(lambda _=None: self._doi())
            gl.addWidget(o)
        self.lb_danh_gia = QLabel('')
        self.lb_danh_gia.setWordWrap(True)
        gl.addWidget(self.lb_danh_gia)
        lo.addWidget(g)
        h = QHBoxLayout()
        for chu, ham in (('Xuất Phiếu tiếp nhận (.xlsx)…', lambda: self.xuat_phieu()),
                         ('Xuất Công văn đề nghị bổ sung (.docx)…', lambda: self.xuat_cong_van())):
            b = QPushButton(chu)
            b.clicked.connect(ham)
            self.nut[chu] = b
            h.addWidget(b)
        h.addStretch(1)
        lo.addLayout(h)
        return w

    # ---------------------------------------------------------------- nạp / đọc
    def nap(self, d: dict) -> None:
        self._dang_nap = True
        try:
            self.d = tn.chuan(d)
            for k, o in self.o_da.items():
                o.setText(self.d['du_an'].get(k, ''))
                o.setCursorPosition(0)
            self.cb_cdt.setCurrentIndex(max(0, self.cb_cdt.findData(self.d['loai_cdt'])))
            for k, o in self.o_cc.items():
                o.setChecked(k in self.d['can_cu'])
            for k, o in self.o_kt.items():
                o.setChecked(bool(self.d['ky_thuat'].get(k)))
            self.o_du.setChecked(self.d['xac_nhan']['du_dieu_kien'])
            self.o_tien_do.setChecked(self.d['xac_nhan']['dung_tien_do'])
            self._ve_ho_so()
            self._ve_excel()
        finally:
            self._dang_nap = False
        self.cap_nhat()

    def lay(self) -> dict:
        d = tn.chuan(self.d)
        d['du_an'] = {k: o.text().strip() for k, o in self.o_da.items()}
        d['loai_cdt'] = self.cb_cdt.currentData()
        d['can_cu'] = [k for k, o in self.o_cc.items() if o.isChecked()]
        d['ky_thuat'] = {k: o.isChecked() for k, o in self.o_kt.items()}
        d['xac_nhan'] = dict(du_dieu_kien=self.o_du.isChecked(), dung_tien_do=self.o_tien_do.isChecked())
        ho_so, ghi = {}, {}
        for r, m in enumerate(self.dong_hs):
            if m is None:
                continue
            it, gc = self.bang_hs.item(r, C_CO), self.bang_hs.item(r, C_GC)
            if it is not None and it.checkState() == Qt.CheckState.Checked:
                ho_so[m[0]] = True
            if gc is not None and gc.text().strip():
                ghi[m[0]] = gc.text().strip()
        d['ho_so'], d['ghi_chu'] = ho_so, ghi
        return d

    def _ve_ho_so(self) -> None:
        from PySide6.QtGui import QBrush, QColor, QFont
        b = self.bang_hs
        b.blockSignals(True)
        try:
            for r, m in enumerate(self.dong_hs):
                if m is None:
                    nhom = tn.NHOM_HO_SO[sum(1 for x in self.dong_hs[:r + 1] if x is None) - 1][0]
                    it = QTableWidgetItem(nhom)
                    f = QFont(it.font())
                    f.setBold(True)
                    it.setFont(f)
                    it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    it.setBackground(QBrush(QColor(mau_theo_tong('#EFF6FF', 'nen'))))
                    b.setItem(r, 0, QTableWidgetItem(''))
                    b.item(r, 0).setFlags(Qt.ItemFlag.ItemIsEnabled)
                    b.item(r, 0).setBackground(QBrush(QColor(mau_theo_tong('#EFF6FF', 'nen'))))
                    b.setItem(r, C_ND, it)
                    for c in (C_AD, C_GC):
                        x = QTableWidgetItem('')
                        x.setFlags(Qt.ItemFlag.ItemIsEnabled)
                        x.setBackground(QBrush(QColor(mau_theo_tong('#EFF6FF', 'nen'))))
                        b.setItem(r, c, x)
                    continue
                co = QTableWidgetItem('')
                co.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
                co.setCheckState(Qt.CheckState.Checked if self.d['ho_so'].get(m[0]) else Qt.CheckState.Unchecked)
                b.setItem(r, C_CO, co)
                nd = QTableWidgetItem(m[1] + (' (*)' if m[0] in tn.BAT_BUOC else ''))
                nd.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                nd.setToolTip(m[1])
                b.setItem(r, C_ND, nd)
                ad = QTableWidgetItem('')
                ad.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                ad.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                b.setItem(r, C_AD, ad)
                gc = QTableWidgetItem(str(self.d['ghi_chu'].get(m[0]) or ''))
                gc.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                b.setItem(r, C_GC, gc)
        finally:
            b.blockSignals(False)
        self._to_ap_dung()

    def _to_ap_dung(self) -> None:
        from PySide6.QtGui import QBrush, QColor
        d = self.lay() if not self._dang_nap else self.d
        b = self.bang_hs
        b.blockSignals(True)
        try:
            for r, m in enumerate(self.dong_hs):
                if m is None or b.item(r, C_ND) is None:
                    continue
                ad = tn.ap_dung(m, d)
                b.item(r, C_AD).setText('Có' if ad else 'Không')
                mau = QColor(mau_theo_tong('#0F172A', 'chu')) if ad else QColor('#94A3B8')
                for c in (C_ND, C_AD):
                    b.item(r, c).setForeground(QBrush(mau))
        finally:
            b.blockSignals(False)

    def _sua_o_hs(self, it) -> None:
        if not self._dang_nap:
            self._doi()

    def _ve_excel(self) -> None:
        ex = self.d.get('ket_qua_excel') or None
        self.ds_excel.clear()
        if not ex:
            self.lb_excel.setText('Chưa quét bảng kê.')
            return
        from .tien import D, so_vn
        self.lb_excel.setText(f'{Path(ex["file"]).name}: {ex["so_dong"]} thửa, {ex["so_ho"]} chủ sử dụng, tổng '
                              f'{so_vn(D(ex["tong_dt"]))} m² · thiếu tờ/thửa {ex["thieu_to_thua"]} · trùng {ex["trung"]} · sai loại '
                              f'đất {ex["sai_loai_dat"]} · DT 0: {ex["dt_0"]} · thiếu tên {ex["thieu_ten"]}')
        self.ds_excel.addItems(ex.get('van_de') or ['Không phát hiện vấn đề.'])

    def _doi(self) -> None:
        if self._dang_nap:
            return
        self._to_ap_dung()
        self.cap_nhat()

    def cap_nhat(self) -> dict:
        """Vẽ lại phân tích (thẻ 1) và tổng hợp (thẻ 4) theo dữ liệu đang nhập. Trả kết quả tổng hợp."""
        d = self.lay() if not self._dang_nap else self.d
        th = tn.tong_hop(d)
        dong = ['<b>Trách nhiệm của Tổ chức làm nhiệm vụ bồi thường:</b>'] + [f'• {x}' for x in th['trach_nhiem']]
        if th['thoi_han']:
            mau = dict(loi='#B83A3A', canh_bao='#9A5A12', tin='#1F6F66')
            dong += ['', '<b>Thời hạn chủ trương / Nghị quyết HĐND:</b>'] + \
                [f'<span style="color:{mau_theo_tong(mau[m], "chu")}">• {x}</span>' for m, x in th['thoi_han']]
        self.lb_phan_tich.setText('<br>'.join(dong))
        for ds, muc in ((self.ds_co, th['da_co']), (self.ds_thieu, th['con_thieu'])):
            ds.clear()
            ds.addItems([x for _, x in muc] or ['(không)'])
        self.ds_bo_sung.clear()
        self.ds_bo_sung.addItems(th['can_bo_sung'] or ['(không)'])
        self.lb_danh_gia.setText(f'Đánh giá tự động: hồ sơ {"ĐỦ" if th["du_dieu_kien_tu_dong"] else "CHƯA ĐỦ"} điều kiện triển khai'
                                 + (f' (thiếu {len(th["thieu_bat_buoc"])} hồ sơ bắt buộc)' if th['thieu_bat_buoc'] else '') +
                                 f'; tiến độ {"đúng hạn" if th["dung_tien_do_tu_dong"] else "CÓ VẤN ĐỀ (xem thẻ 1)"}.')
        self.lb_trang_thai.setText(tn.trang_thai(d)['nhan'] + (f' · {Path(self.file).name}' if self.file else ''))
        return th

    # ---------------------------------------------------------------- thao tác
    def _bao(self, chu: str, loi: bool = False) -> None:
        if self.im_lang:
            return
        (QMessageBox.warning if loi else QMessageBox.information)(self, TEN_UD, chu)

    def _chon(self, luu: bool, tieu_de: str, loc: str, ten: str = '') -> str:
        if self.im_lang:
            return ''
        goc = str(Path(self.file_du_an).parent / ten) if self.file_du_an else ten
        f = (QFileDialog.getSaveFileName if luu else QFileDialog.getOpenFileName)(self, tieu_de, goc, loc)[0]
        return f or ''

    def mo_tep(self, file: str = '') -> bool:
        file = file or self._chon(False, 'Mở hồ sơ tiếp nhận', f'Hồ sơ tiếp nhận (*{tn.DUOI})')
        if not file:
            return False
        from .lap_pa import LoiNhap
        try:
            self.nap(tn.mo_file(file))
        except LoiNhap as e:
            self._bao(str(e), True)
            return False
        self.file = str(file)
        self.cap_nhat()
        return True

    def luu_tep(self, file: str = '') -> str:
        file = file or self.file or self._chon(True, 'Lưu hồ sơ tiếp nhận', f'Hồ sơ tiếp nhận (*{tn.DUOI})', 'HoSoTiepNhan' + tn.DUOI)
        if not file:
            return ''
        try:
            p = tn.luu_file(self.lay(), file)
        except OSError as e:
            self._bao(chu_loi('Không lưu được hồ sơ tiếp nhận', e), True)
            return ''
        self.file = str(p)
        self.cap_nhat()
        return self.file

    def luu_du_an(self) -> bool:
        if self.con is None:
            return False
        import sqlite3
        try:
            tn.ghi_du_an(self.con, self.lay())
        except sqlite3.Error as e:
            self._bao(chu_loi('Không lưu được vào dự án (dự án đang mở chỉ xem?)', e), True)
            return False
        self._bao('Đã lưu hồ sơ tiếp nhận vào dự án.')
        return True

    def nap_khai_toan(self, file: str = '') -> bool:
        file = file or self._chon(False, 'Chọn file khái toán', 'Khái toán (*.pabtdt)')
        if not file:
            return False
        from .lap_pa import LoiNhap
        try:
            self.nap(tn.tu_khai_toan(self.lay(), file))
        except LoiNhap as e:
            self._bao(str(e), True)
            return False
        return True

    def quet_excel(self, file: str = '') -> dict | None:
        file = file or self._chon(False, 'Chọn bảng kê thửa đất', 'Excel (*.xlsx *.xlsm)')
        if not file:
            return None
        from .lap_pa import LoiNhap
        from .giao_dien import con_tro_cho
        try:
            with con_tro_cho():
                kq = tn.quet_excel(file)
        except (LoiNhap, OSError, ValueError, KeyError) as e:
            self._bao(chu_loi('Không đọc được bảng kê thửa', e), True)
            return None
        d = self.lay()
        d['ket_qua_excel'] = kq
        self.nap(d)
        return kq

    def xuat_phieu(self, file: str = '') -> str:
        file = file or self._chon(True, 'Xuất phiếu tiếp nhận', 'Excel (*.xlsx)', 'PhieuTiepNhanPhapLy.xlsx')
        if not file:
            return ''
        try:
            return str(tn.xuat_phieu_xlsx(self.lay(), file))
        except OSError as e:
            self._bao(chu_loi('Không ghi được phiếu (file đang mở trong Excel?)', e), True)
            return ''

    def xuat_cong_van(self, file: str = '') -> str:
        file = file or self._chon(True, 'Xuất công văn đề nghị bổ sung hồ sơ', 'Word (*.docx)', 'CongVan_BoSungHoSo.docx')
        if not file:
            return ''
        try:
            return str(tn.xuat_cong_van_docx(self.lay(), file))
        except OSError as e:
            self._bao(chu_loi('Không ghi được công văn (file đang mở trong Word?)', e), True)
            return ''

    def khoi_tao_du_an(self):
        if self.khoi_tao is None:
            return None
        d = self.lay()
        self.accept()
        return self.khoi_tao(d)

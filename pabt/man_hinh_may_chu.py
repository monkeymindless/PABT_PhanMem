"""Màn hình máy chủ LAN: đăng nhập, thiết lập máy chủ, tài khoản người dùng, đổi mật khẩu, dự án trên máy chủ (mở / mang về làm
offline / đưa lên lại). Logic ở may_chu.py; hàm thao tác nhận tham số để kiểm thử (im_lang = True: không hiện hộp thông báo)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from . import may_chu
from .may_chu import LoiMayChu

TIEU_DE = 'Máy chủ, tài khoản'


class _Hop(QDialog):
    im_lang = False

    def bao(self, chu: str, loi: bool = True) -> None:
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TIEU_DE, chu)

    def hoi(self, chu: str) -> bool:
        return self.im_lang or QMessageBox.question(self, TIEU_DE, chu) == QMessageBox.StandardButton.Yes


def _o_mk(cho: str = '') -> QLineEdit:
    o = QLineEdit()
    o.setEchoMode(QLineEdit.EchoMode.Password)
    o.setPlaceholderText(cho)
    return o


def _bang(cot: list, rong: list) -> QTableWidget:
    b = QTableWidget(0, len(cot))
    b.setHorizontalHeaderLabels(cot)
    b.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    b.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    b.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    b.verticalHeader().setVisible(False)
    b.setAlternatingRowColors(True)
    for c, w in enumerate(rong):
        b.setColumnWidth(c, w)
    b.horizontalHeader().setStretchLastSection(True)
    b.setTextElideMode(Qt.TextElideMode.ElideMiddle)        # đường dẫn dài: giữ đầu và tên file
    b.setWordWrap(False)
    return b


def _dien(b: QTableWidget, r: int, gia: list):
    for c, v in enumerate(gia):
        it = QTableWidgetItem('' if v is None else str(v))
        it.setToolTip('' if v is None else str(v))
        b.setItem(r, c, it)


# ---------------------------------------------------------------- đăng nhập
class HopDangNhap(_Hop):
    """Đăng nhập máy chủ, hoặc làm việc offline. Kết quả: self.phien (None nếu chọn offline)."""

    def __init__(self, parent=None, goc=None):
        super().__init__(parent)
        ch = may_chu.doc_cau_hinh()
        self.goc = str(goc or ch.get('may_chu', ''))
        self.phien = None
        self.offline = False
        self.setWindowTitle('Đăng nhập PABT')
        self.setFixedWidth(430)
        tieu = QLabel('<b>Đăng nhập máy chủ PABT</b>')
        tieu.setProperty('vai', 'tieu_de')
        self.lb_may_chu = QLabel(f'Máy chủ: {self.goc or "(chưa thiết lập)"}')
        self.lb_may_chu.setWordWrap(True)
        self.o_tk = QLineEdit(ch.get('tai_khoan', ''))
        self.o_tk.setPlaceholderText('tài khoản, ví dụ vinh.pt')
        self.o_mk = _o_mk('mật khẩu')
        f = QFormLayout()
        f.addRow('Tài khoản:', self.o_tk)
        f.addRow('Mật khẩu:', self.o_mk)
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        self.lb.setStyleSheet('color: #C62828;')
        b_dn = QPushButton('Đăng nhập')
        b_dn.setDefault(True)
        b_dn.setProperty('nhom', 'luu')
        b_dn.clicked.connect(lambda: self.dang_nhap())
        b_off = QPushButton('Làm việc offline')
        b_off.clicked.connect(lambda: self.lam_offline())
        b_tl = QPushButton('Thiết lập máy chủ…')
        b_tl.clicked.connect(lambda: self.thiet_lap())
        h = QHBoxLayout()
        h.addWidget(b_tl)
        h.addStretch(1)
        h.addWidget(b_off)
        h.addWidget(b_dn)
        ghi = QLabel('Đăng nhập ở máy bất kỳ trong mạng nội bộ: phần mềm mở lại dự án đang làm dở. Không có máy chủ (mất mạng, '
                     'đi hiện trường) thì chọn "Làm việc offline" - mọi chức năng nhập liệu vẫn dùng bình thường.')
        ghi.setWordWrap(True)
        ghi.setStyleSheet('color: #5B6B7A;')
        lo = QVBoxLayout(self)
        lo.addWidget(tieu)
        lo.addWidget(self.lb_may_chu)
        lo.addLayout(f)
        lo.addWidget(self.lb)
        lo.addLayout(h)
        lo.addWidget(ghi)
        (self.o_mk if self.o_tk.text() else self.o_tk).setFocus()

    def dang_nhap(self, tai_khoan=None, mat_khau=None):
        tk = self.o_tk.text() if tai_khoan is None else tai_khoan
        mk = self.o_mk.text() if mat_khau is None else mat_khau
        if not self.goc:
            self.lb.setText('Chưa thiết lập máy chủ: bấm "Thiết lập máy chủ…" hoặc làm việc offline.')
            return None
        if not may_chu.ket_noi_duoc(self.goc):
            self.lb.setText('Không kết nối được máy chủ (mạng / thư mục dùng chung). Có thể chọn "Làm việc offline".')
            return None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.phien = may_chu.dang_nhap(self.goc, tk, mk)
        except LoiMayChu as e:
            QApplication.restoreOverrideCursor()
            self.lb.setText(str(e))
            self.o_mk.selectAll()
            return None
        QApplication.restoreOverrideCursor()
        self.accept()
        return self.phien

    def lam_offline(self):
        self.offline = True
        self.reject()

    def thiet_lap(self):
        dlg = HopThietLap(self, self.goc)
        dlg.im_lang = self.im_lang
        if dlg.exec() and dlg.goc:
            self.goc = dlg.goc
            self.lb_may_chu.setText(f'Máy chủ: {self.goc}')
            if dlg.tai_khoan:
                self.o_tk.setText(dlg.tai_khoan)


# ---------------------------------------------------------------- thiết lập máy chủ
class HopThietLap(_Hop):
    """Chọn thư mục máy chủ (thư mục dùng chung trong mạng): kết nối máy chủ có sẵn, hoặc khởi tạo mới với tài khoản quản trị."""

    def __init__(self, parent=None, goc: str = ''):
        super().__init__(parent)
        self.goc = None
        self.tai_khoan = ''
        self.setWindowTitle('Thiết lập máy chủ trong mạng nội bộ')
        self.setMinimumWidth(820)
        self.o_goc = QLineEdit(goc or may_chu.doc_cau_hinh().get('may_chu', ''))
        self.o_goc.setPlaceholderText(r'\\TEN-MAY-CHU\PABT  hoặc  Z:\PABT (ổ mạng)')
        b_chon = QPushButton('Chọn thư mục…')
        b_chon.clicked.connect(lambda: self._chon())
        h = QHBoxLayout()
        h.addWidget(self.o_goc, 1)
        h.addWidget(b_chon)
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        self.o_qt_tk = QLineEdit('quantri')
        self.o_qt_ten = QLineEdit('Quản trị hệ thống')
        self.o_qt_mk = _o_mk('ít nhất 6 ký tự')
        self.o_qt_mk2 = _o_mk('nhập lại')
        from .giao_dien import the_form
        self.the_moi = the_form('Khởi tạo máy chủ mới (lần đầu)', [
            ('Tài khoản quản trị:', self.o_qt_tk), ('Họ tên:', self.o_qt_ten), ('Mật khẩu:', self.o_qt_mk),
            ('Nhập lại mật khẩu:', self.o_qt_mk2)], 130)
        b_kt = QPushButton('Kiểm tra')
        b_kt.clicked.connect(lambda: self.kiem_tra())
        b_kn = QPushButton('Kết nối máy chủ có sẵn')
        b_kn.setProperty('nhom', 'nhap')
        b_kn.clicked.connect(lambda: self.ket_noi())
        b_tao = QPushButton('Khởi tạo máy chủ mới')
        b_tao.setProperty('nhom', 'them')
        b_tao.clicked.connect(lambda: self.khoi_tao())
        b_bo = QPushButton('Không dùng máy chủ')
        b_bo.clicked.connect(lambda: self.bo_may_chu())
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        hn = QHBoxLayout()
        for b in (b_kt, b_kn, b_tao):
            hn.addWidget(b)
        hn.addStretch(1)
        hn.addWidget(b_bo)
        hn.addWidget(b_dong)
        ghi = QLabel('Máy chủ là một thư mục dùng chung trên máy chủ của đơn vị (chia sẻ trong mạng, cấp quyền đọc / ghi cho người '
                     'dùng PABT). Máy đầu tiên khởi tạo máy chủ và tài khoản quản trị; các máy khác chỉ cần chọn cùng thư mục rồi '
                     '"Kết nối". Dự án dùng chung đặt trong thư mục DuAn của máy chủ.')
        ghi.setWordWrap(True)
        lo = QVBoxLayout(self)
        nhan = QLabel('Thư mục máy chủ:')
        nhan.setProperty('vai', 'nhan')
        lo.addWidget(nhan)
        lo.addLayout(h)
        lo.addWidget(self.lb)
        lo.addWidget(self.the_moi)
        lo.addWidget(ghi)
        lo.addLayout(hn)
        if self.o_goc.text():
            self.kiem_tra()

    def _chon(self):
        p = QFileDialog.getExistingDirectory(self, 'Chọn thư mục máy chủ (thư mục dùng chung)', self.o_goc.text())
        if p:
            self.o_goc.setText(str(Path(p)))
            self.kiem_tra()

    def kiem_tra(self) -> str:
        goc = self.o_goc.text().strip()
        if not goc:
            self.lb.setText('Nhập hoặc chọn thư mục máy chủ.')
            return 'trong'
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if may_chu.ket_noi_duoc(goc):
                n = len(may_chu.ds_nguoi_dung(goc))
                kq, chu = 'co', f'✔ Đây là máy chủ PABT ({n} tài khoản): bấm "Kết nối máy chủ có sẵn".'
            elif may_chu.thu_muc_ton_tai(goc):
                kq, chu = 'moi', 'Thư mục chưa phải máy chủ PABT: nhập tài khoản quản trị rồi bấm "Khởi tạo máy chủ mới".'
            else:
                kq, chu = 'khong', ('Thư mục chưa có hoặc không truy cập được (kiểm tra mạng, tên máy chủ, quyền chia sẻ). '
                                    'Khởi tạo máy chủ mới sẽ tạo thư mục nếu có quyền ghi.')
        finally:
            QApplication.restoreOverrideCursor()
        self.lb.setText(chu)
        self.the_moi.setVisible(kq != 'co')
        return kq

    def ket_noi(self):
        goc = self.o_goc.text().strip()
        if not may_chu.ket_noi_duoc(goc):
            self.bao('Thư mục này chưa phải máy chủ PABT hoặc không truy cập được.')
            return False
        may_chu.ghi_cau_hinh(may_chu=goc)
        self.goc = goc
        self.accept()
        return True

    def khoi_tao(self):
        goc = self.o_goc.text().strip()
        if self.o_qt_mk.text() != self.o_qt_mk2.text():
            self.bao('Hai lần nhập mật khẩu không giống nhau.')
            return False
        try:
            may_chu.khoi_tao(goc, self.o_qt_tk.text(), self.o_qt_mk.text(), self.o_qt_ten.text())
        except LoiMayChu as e:
            self.bao(str(e))
            return False
        may_chu.ghi_cau_hinh(may_chu=goc, tai_khoan=self.o_qt_tk.text().strip().lower())
        self.goc, self.tai_khoan = goc, self.o_qt_tk.text().strip().lower()
        self.bao(f'Đã khởi tạo máy chủ tại {goc}.\nĐăng nhập bằng tài khoản quản trị rồi thêm tài khoản cho người dùng '
                 '(nút Tài khoản → Quản lý tài khoản).', loi=False)
        self.accept()
        return True

    def bo_may_chu(self):
        if not self.hoi('Không dùng máy chủ trên máy này (làm việc offline với file trên máy)? Dữ liệu trên máy chủ giữ nguyên.'):
            return False
        may_chu.dang_xuat()
        may_chu.ghi_cau_hinh(may_chu='')
        self.goc = ''
        self.accept()
        return True


# ---------------------------------------------------------------- đổi mật khẩu
class HopDoiMatKhau(_Hop):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Đổi mật khẩu')
        self.setFixedWidth(400)
        self.o_cu, self.o_moi, self.o_moi2 = _o_mk(), _o_mk('ít nhất 6 ký tự'), _o_mk()
        f = QFormLayout(self)
        f.addRow('Mật khẩu hiện tại:', self.o_cu)
        f.addRow('Mật khẩu mới:', self.o_moi)
        f.addRow('Nhập lại:', self.o_moi2)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Save).setText('Lưu')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        f.addRow(nut)

    def accept(self):
        if self.o_moi.text() != self.o_moi2.text():
            self.bao('Hai lần nhập mật khẩu mới không giống nhau.')
            return
        try:
            may_chu.doi_mat_khau(may_chu.PHIEN, self.o_cu.text(), self.o_moi.text())
        except LoiMayChu as e:
            self.bao(str(e))
            return
        self.bao('Đã đổi mật khẩu.', loi=False)
        super().accept()


# ---------------------------------------------------------------- quản lý tài khoản (quản trị)
class HopTaiKhoan(_Hop):
    COT = ['Tài khoản', 'Họ tên', 'Chức vụ', 'Vai trò', 'Trạng thái', 'Đăng nhập cuối', 'Máy']

    def __init__(self, parent=None):
        super().__init__(parent)
        self.phien = may_chu.PHIEN
        self.setWindowTitle('Quản lý tài khoản người dùng')
        self.resize(940, 520)
        self.bang = _bang(self.COT, [110, 190, 130, 90, 90, 140, 110])
        self.o_tk, self.o_ten, self.o_cv = QLineEdit(), QLineEdit(), QLineEdit()
        self.o_tk.setPlaceholderText('vd: vinh.pt')
        self.o_mk = _o_mk('ít nhất 6 ký tự')
        self.cb_vt = QComboBox()
        for k, t in may_chu.TEN_VAI_TRO.items():
            self.cb_vt.addItem(t, k)
        self.cb_vt.setCurrentIndex(1)
        from .giao_dien import the_form
        the = the_form('Thêm tài khoản', [('Tài khoản:', self.o_tk), ('Họ tên:', self.o_ten), ('Chức vụ:', self.o_cv),
                                          ('Mật khẩu ban đầu:', self.o_mk), ('Vai trò:', self.cb_vt)], 120)
        b_them = QPushButton('Thêm tài khoản')
        b_them.clicked.connect(lambda: self.them())
        the.layout().addRow(b_them)
        hn = QHBoxLayout()
        for ten, ham in (('Đặt lại mật khẩu…', lambda: self.dat_lai()), ('Khóa / mở khóa', lambda: self.khoa_mo()),
                         ('Đổi vai trò', lambda: self.doi_vai_tro())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            hn.addWidget(b)
        hn.addStretch(1)
        b = QPushButton('Đóng')
        b.clicked.connect(self.reject)
        hn.addWidget(b)
        lo = QVBoxLayout(self)
        lo.addWidget(self.bang, 1)
        lo.addWidget(the)
        lo.addLayout(hn)
        self.ve()

    def ve(self):
        self.ds = may_chu.ds_nguoi_dung(self.phien.goc)
        self.bang.setRowCount(len(self.ds))
        for r, u in enumerate(self.ds):
            _dien(self.bang, r, [u['tai_khoan'], u['ho_ten'], u['chuc_vu'], may_chu.TEN_VAI_TRO.get(u['vai_tro'], u['vai_tro']),
                                 'Đang khóa' if u['khoa'] else 'Hoạt động', (u['dang_nhap_cuoi'] or '').replace('T', ' '),
                                 u['may_cuoi']])

    def _chon(self):
        r = self.bang.currentRow()
        if not 0 <= r < len(self.ds):
            self.bao('Chọn một tài khoản trong bảng.', loi=False)
            return None
        return self.ds[r]

    def them(self, tk=None, ten=None, mk=None, vai_tro=None, chuc_vu=None):
        try:
            may_chu.them_nguoi_dung(self.phien, tk if tk is not None else self.o_tk.text(),
                                    ten if ten is not None else self.o_ten.text(), mk if mk is not None else self.o_mk.text(),
                                    vai_tro or self.cb_vt.currentData(), chuc_vu if chuc_vu is not None else self.o_cv.text())
        except LoiMayChu as e:
            self.bao(str(e))
            return False
        for o in (self.o_tk, self.o_ten, self.o_cv, self.o_mk):
            o.clear()
        self.ve()
        return True

    def dat_lai(self, mk=None):
        u = self._chon()
        if u is None:
            return False
        if mk is None:
            from PySide6.QtWidgets import QInputDialog
            mk, ok = QInputDialog.getText(self, 'Đặt lại mật khẩu', f'Mật khẩu mới cho "{u["tai_khoan"]}":', QLineEdit.EchoMode.Password)
            if not ok:
                return False
        try:
            may_chu.dat_lai_mat_khau(self.phien, u['tai_khoan'], mk)
        except LoiMayChu as e:
            self.bao(str(e))
            return False
        self.ve()
        self.bao('Đã đặt lại mật khẩu (tài khoản được mở khóa).', loi=False)
        return True

    def khoa_mo(self):
        u = self._chon()
        if u is None:
            return False
        try:
            may_chu.sua_nguoi_dung(self.phien, u['tai_khoan'], khoa=not u['khoa'])
        except LoiMayChu as e:
            self.bao(str(e))
            return False
        self.ve()
        return True

    def doi_vai_tro(self):
        u = self._chon()
        if u is None:
            return False
        moi = may_chu.NGUOI_DUNG if u['vai_tro'] == may_chu.QUAN_TRI else may_chu.QUAN_TRI
        try:
            may_chu.sua_nguoi_dung(self.phien, u['tai_khoan'], vai_tro=moi)
        except LoiMayChu as e:
            self.bao(str(e))
            return False
        self.ve()
        return True


# ---------------------------------------------------------------- dự án trên máy chủ, làm offline
class HopDuAnMayChu(_Hop):
    """Dự án trên máy chủ (mở, mang về làm offline) và dự án đã mang về máy này (mở, đưa lên lại, hủy)."""
    COT = ['Dự án', 'File', 'Sửa lúc', 'Đang mở bởi', 'Đã mang về (offline)']
    COT_OFF = ['Bản làm offline', 'Từ máy chủ', 'Mang về lúc', 'Tài khoản']

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mo_file = None                      # file người dùng chọn mở
        self.setWindowTitle('Dự án trên máy chủ và làm offline')
        self.resize(1100, 620)
        self.lb = QLabel('')
        self.lb.setProperty('vai', 'tieu_de')
        self.bang = _bang(self.COT, [300, 190, 125, 280, 240])
        self.bang.doubleClicked.connect(lambda *_: self.mo())
        h1 = QHBoxLayout()
        for ten, ham in (('Mở dự án', lambda: self.mo()), ('Mang về làm offline', lambda: self.mang_ve()),
                         ('Mở thư mục máy chủ', lambda: self._mo_thu_muc()), ('Làm mới', lambda: self.ve())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            h1.addWidget(b)
        h1.addStretch(1)
        nhan = QLabel('Dự án đã mang về máy này (làm offline)')
        nhan.setProperty('vai', 'tieu_de')
        self.bang_off = _bang(self.COT_OFF, [300, 480, 150, 120])
        self.bang_off.doubleClicked.connect(lambda *_: self.mo_offline())
        h2 = QHBoxLayout()
        for ten, ham in (('Mở bản offline', lambda: self.mo_offline()), ('Đưa lên máy chủ', lambda: self.dua_len()),
                         ('Hủy bản offline', lambda: self.huy())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            h2.addWidget(b)
        h2.addStretch(1)
        b = QPushButton('Đóng')
        b.clicked.connect(self.reject)
        h2.addWidget(b)
        lo = QVBoxLayout(self)
        lo.addWidget(self.lb)
        lo.addWidget(self.bang, 3)
        lo.addLayout(h1)
        lo.addWidget(nhan)
        lo.addWidget(self.bang_off, 2)
        lo.addLayout(h2)
        self.ve()

    def ve(self):
        p = may_chu.PHIEN
        self.ds = []
        if p is not None and may_chu.ket_noi_duoc(p.goc):
            self.ds = may_chu.ds_du_an()
            self.lb.setText(f'Dự án trên máy chủ {p.goc}  ·  {p.ten_hien}')
        else:
            self.lb.setText('Chưa đăng nhập / không kết nối được máy chủ: chỉ làm việc với các bản offline trên máy này.')
        self.bang.setRowCount(len(self.ds))
        for r, x in enumerate(self.ds):
            lv = x['lay_ve']
            _dien(self.bang, r, [x['ten'], x['file'].name, x['sua_luc'], x['dang_mo'],
                                 f'{lv["tai_khoan"]} (máy {lv["may"]}, {lv["luc"].replace("T", " ")})' if lv else ''])
        self.ds_off = may_chu.ds_lay_ve_cuc_bo()
        self.bang_off.setRowCount(len(self.ds_off))
        for r, x in enumerate(self.ds_off):
            _dien(self.bang_off, r, [Path(x['ban_sao']).name, x['file_goc'], x['luc'].replace('T', ' '), x['tai_khoan']])

    def _chon(self, bang, ds):
        r = bang.currentRow()
        if not 0 <= r < len(ds):
            self.bao('Chọn một dòng trong bảng.', loi=False)
            return None
        return ds[r]

    def mo(self):
        x = self._chon(self.bang, self.ds)
        if x is None:
            return None
        if x['lay_ve'] and not self.hoi(f'Dự án đang được "{x["lay_ve"]["tai_khoan"]}" mang về làm offline: sửa trên máy chủ lúc '
                                        'này sẽ xung đột khi người đó đưa lên. Vẫn mở?'):
            return None
        self.mo_file = x['file']
        self.accept()
        return self.mo_file

    def mang_ve(self, x=None):
        x = x or self._chon(self.bang, self.ds)
        if x is None:
            return None
        try:
            dich = may_chu.lay_ve(x['file'])
        except (LoiMayChu, OSError) as e:
            self.bao(str(e))
            return None
        self.ve()
        if self.hoi(f'Đã mang về máy này:\n{dich}\n\nMở bản offline để làm việc ngay?'):
            self.mo_file = dich
            self.accept()
        return dich

    def mo_offline(self):
        x = self._chon(self.bang_off, self.ds_off)
        if x is None:
            return None
        self.mo_file = Path(x['ban_sao'])
        self.accept()
        return self.mo_file

    def dua_len(self, x=None, ep: bool | None = None):
        x = x or self._chon(self.bang_off, self.ds_off)
        if x is None:
            return None
        try:
            f = may_chu.dua_len(x['ban_sao'], ep=bool(ep))
        except LoiMayChu as e:
            if 'XUNG ĐỘT' in str(e) and ep is None and self.hoi(str(e) + '\n\nVẫn đưa lên (ghi đè)?'):
                return self.dua_len(x, ep=True)
            self.bao(str(e))
            return None
        except OSError as e:
            self.bao(f'Không đưa lên được (file đang mở?): {e}')
            return None
        self.ve()
        self.bao(f'Đã đưa lên máy chủ:\n{f}', loi=False)
        return f

    def huy(self, x=None):
        x = x or self._chon(self.bang_off, self.ds_off)
        if x is None:
            return False
        if not self.hoi('Bỏ bản làm offline này (các sửa đổi chưa đưa lên sẽ mất)?'):
            return False
        try:
            may_chu.huy_lay_ve(x['ban_sao'])
        except (LoiMayChu, OSError) as e:
            self.bao(str(e))
            return False
        self.ve()
        return True

    def _mo_thu_muc(self):
        from .in_an import mo_file
        if may_chu.PHIEN is not None:
            mo_file(may_chu.thu_muc_du_an())


"""Màn hình máy chủ LAN: đăng nhập, thiết lập máy chủ, tài khoản người dùng, đổi mật khẩu, dự án trên máy chủ (mở / mang về làm
offline / đưa lên lại). Logic ở may_chu.py; hàm thao tác nhận tham số để kiểm thử (im_lang = True: không hiện hộp thông báo)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from . import may_chu
from .may_chu import LoiMayChu
from .giao_dien import con_tro_cho
from .thong_bao import chu_loi


def ket_noi_duoc(cha, goc) -> bool:
    """may_chu.ket_noi_duoc chạy ở luồng nền (giao_dien.chay_nen): mạng / thư mục dùng chung không tới được thì cửa sổ vẫn vẽ lại,
    hiện "Đang kết nối máy chủ…" thay vì đứng hình tới 4 giây (mỗi lần kiểm tra)."""
    from .giao_dien import chay_nen
    return chay_nen(cha, lambda: may_chu.ket_noi_duoc(goc), f'Đang kết nối máy chủ {goc}…')

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
        self.setWindowTitle('Đăng nhập LARC')
        self.setFixedWidth(430)
        tieu = QLabel('<b>Đăng nhập máy chủ LARC</b>')
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
        self.lb.setStyleSheet('color: #B83A3A;')
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
        if not ket_noi_duoc(self, self.goc):
            self.lb.setText('Không kết nối được máy chủ (mạng / thư mục dùng chung). Có thể chọn "Làm việc offline".')
            return None
        try:
            with con_tro_cho():
                self.phien = may_chu.dang_nhap(self.goc, tk, mk)
        except LoiMayChu as e:
            self.lb.setText(str(e))
            self.o_mk.selectAll()
            return None
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
                     'dùng LARC). Máy đầu tiên khởi tạo máy chủ và tài khoản quản trị; các máy khác chỉ cần chọn cùng thư mục rồi '
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
            from .giao_dien import chay_nen
            if ket_noi_duoc(self, goc):
                n = len(may_chu.ds_nguoi_dung(goc))
                kq, chu = 'co', f'✔ Đây là máy chủ PABT ({n} tài khoản): bấm "Kết nối máy chủ có sẵn".'
            elif chay_nen(self, lambda: may_chu.thu_muc_ton_tai(goc), f'Đang kiểm tra thư mục {goc}…'):
                kq, chu = 'moi', 'Thư mục chưa phải máy chủ LARC: nhập tài khoản quản trị rồi bấm "Khởi tạo máy chủ mới".'
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
        if not ket_noi_duoc(self, goc):
            self.bao('Thư mục này chưa phải máy chủ LARC hoặc không truy cập được.')
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
    COT_OFF = ['Bản làm offline', 'Từ máy chủ', 'Mang về lúc', 'Tài khoản', 'Phạm vi']

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
                         ('Nhận theo hộ (Chia việc)', lambda: self.nhan_theo_ho()),
                         ('Mở thư mục máy chủ', lambda: self._mo_thu_muc()), ('Làm mới', lambda: self.ve())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            h1.addWidget(b)
        h1.addStretch(1)
        nhan = QLabel('Dự án đã mang về máy này (làm offline)')
        nhan.setProperty('vai', 'tieu_de')
        self.bang_off = _bang(self.COT_OFF, [300, 420, 150, 120, 110])
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
        if p is not None and ket_noi_duoc(self, p.goc):
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
            _dien(self.bang_off, r, [Path(x['ban_sao']).name, x['file_goc'], x['luc'].replace('T', ' '), x['tai_khoan'],
                                     f'{len(x["ds_ma_ho"])} hộ' if x.get('ds_ma_ho') else 'Cả dự án'])

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

    def nhan_theo_ho(self, x=None, ds_ma_ho=None):
        """Chia việc: chọn một nhóm hộ của dự án (HopChonHoLayVe) rồi nhận về làm offline - chỉ khóa các hộ đó trên máy chủ.
        ds_ma_ho (kiểm thử): bỏ qua hộp chọn."""
        x = x or self._chon(self.bang, self.ds)
        if x is None:
            return None
        if ds_ma_ho is None:
            hop = HopChonHoLayVe(x['file'], self)
            if hop.exec() != QDialog.DialogCode.Accepted:
                return None
            ds_ma_ho = hop.ds_chon()
        try:
            with con_tro_cho():
                dich = may_chu.lay_ve_theo_ho(x['file'], ds_ma_ho)
        except (LoiMayChu, OSError) as e:
            self.bao(str(e))
            return None
        self.ve()
        if self.hoi(f'Đã nhận {len(ds_ma_ho)} hộ về máy này:\n{dich}\n\nChỉ các hộ này được lưu và gộp lên máy chủ khi bấm "Đưa lên '
                    'máy chủ". Mở bản offline để làm việc ngay?'):
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
        except may_chu.LoiXungDot as e:
            # bản theo hộ: liệt kê các hộ đã bị sửa trên máy chủ trong lúc làm offline, hỏi ghi đè hay hủy để kiểm tra
            ds = '\n'.join(f'  - Mã {m}: {ten}' for m, ten in e.ds[:SO_HO_XUNG_DOT_HIEN])
            them = f'\n  … và {len(e.ds) - SO_HO_XUNG_DOT_HIEN} hộ khác' if len(e.ds) > SO_HO_XUNG_DOT_HIEN else ''
            if ep is None and self.hoi(f'XUNG ĐỘT: {len(e.ds)} hộ đã được sửa trực tiếp trên máy chủ sau lúc bạn nhận về:\n{ds}{them}'
                                       '\n\nGhi đè các hộ này bằng bản của bạn (file trên máy chủ được sao lưu vào thư mục SaoLuu)?\n'
                                       'Chọn "No" để hủy và kiểm tra lại với người đã sửa.'):
                return self.dua_len(x, ep=True)
            self.bao(str(e))
            return None
        except LoiMayChu as e:
            if 'XUNG ĐỘT' in str(e) and ep is None and self.hoi(str(e) + '\n\nVẫn đưa lên (ghi đè)?'):
                return self.dua_len(x, ep=True)
            self.bao(str(e))
            return None
        except OSError as e:
            self.bao(chu_loi('Không đưa lên được', e))
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


SO_HO_XUNG_DOT_HIEN = 30          # số hộ xung đột liệt kê trong câu hỏi ghi đè (còn lại: "… và N hộ khác")


class HopChonHoLayVe(_Hop):
    """Chia việc trên máy chủ LAN (1.0.29): chọn các hộ của MỘT dự án để nhận về làm offline (may_chu.lay_ve_theo_ho). Tìm theo tên /
    CCCD / tờ-thửa, lọc theo đợt / ấp, chọn nhanh theo khoảng STT. Hộ người khác đang nhận: hiện người / máy đang giữ, không chọn được."""
    COT = ['', 'STT', 'Họ tên', 'CCCD', 'Địa chỉ', 'Tờ / thửa', 'Đợt', 'Đang nhận']

    def __init__(self, file, parent=None, ds=None):
        super().__init__(parent)
        from .giao_dien import loc_khi_ngung_go
        from .lap_pa import bo_dau
        self.file = Path(file)
        self._bo_dau = bo_dau
        self.setWindowTitle(f'Nhận theo hộ (Chia việc) - {self.file.name}')
        self.resize(1100, 640)
        self.ds = ds if ds is not None else may_chu.ds_ho_de_chon(self.file)
        for x in self.ds:
            x['_tim'] = bo_dau(' '.join((x['ho_ten'], x['cccd'], x['to_thua'], x['dia_chi'])))
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm theo họ tên, số CCCD, tờ/thửa (vd 12/45)')
        self.cb_dot = QComboBox()
        self.cb_dot.addItem('Đợt: Tất cả', '')
        for d in dict.fromkeys(x['dot'] for x in self.ds if x['dot']):
            self.cb_dot.addItem(d, d)
        self.cb_ap = QComboBox()
        self.cb_ap.addItem('Ấp / khu phố: Tất cả', '')
        for a in sorted({x['ap'] for x in self.ds if x['ap']}, key=bo_dau):
            self.cb_ap.addItem(a, a)
        h_loc = QHBoxLayout()
        h_loc.addWidget(self.o_tim, 1)
        h_loc.addWidget(self.cb_dot)
        h_loc.addWidget(self.cb_ap)
        stt = [x['stt'] for x in self.ds] or [1]
        self.o_tu, self.o_den = QSpinBox(), QSpinBox()
        for o, v in ((self.o_tu, min(stt)), (self.o_den, max(stt))):
            o.setRange(min(stt), max(stt))
            o.setValue(v)
        b_khoang = QPushButton('Chọn khoảng STT')
        b_khoang.setToolTip('Đánh dấu các hộ (đang hiện, chưa ai nhận) có STT trong khoảng')
        b_khoang.clicked.connect(lambda: self.chon_khoang())
        b_hien = QPushButton('Chọn các hộ đang hiện')
        b_hien.clicked.connect(lambda: self.chon_dang_hien(True))
        b_bo = QPushButton('Bỏ chọn tất cả')
        b_bo.clicked.connect(lambda: self.chon_dang_hien(False, tat_ca=True))
        h_chon = QHBoxLayout()
        for w in (QLabel('Từ STT'), self.o_tu, QLabel('đến'), self.o_den, b_khoang):
            h_chon.addWidget(w)
        h_chon.addStretch(1)
        h_chon.addWidget(b_hien)
        h_chon.addWidget(b_bo)
        self.bang = _bang(self.COT, [36, 56, 230, 120, 240, 150, 110, 160])
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.bang.itemChanged.connect(lambda *_: self._dem())
        self.lb = QLabel('')
        self.b_ok = QPushButton('Nhận về làm offline')
        self.b_ok.clicked.connect(self.accept)
        b_huy = QPushButton('Hủy')
        b_huy.clicked.connect(self.reject)
        h_nut = QHBoxLayout()
        h_nut.addWidget(self.lb, 1)
        h_nut.addWidget(self.b_ok)
        h_nut.addWidget(b_huy)
        nhac = QLabel('Chỉ các hộ được chọn bị khóa trên máy chủ: người khác vẫn nhận được các hộ còn lại. Khi làm xong bấm "Đưa lên '
                      'máy chủ" để gộp đúng các hộ này lên.')
        nhac.setWordWrap(True)
        lo = QVBoxLayout(self)
        lo.addWidget(nhac)
        lo.addLayout(h_loc)
        lo.addLayout(h_chon)
        lo.addWidget(self.bang, 1)
        lo.addLayout(h_nut)
        self._ve()
        loc_khi_ngung_go(self.o_tim, self.loc)
        self.cb_dot.currentIndexChanged.connect(lambda *_: self.loc())
        self.cb_ap.currentIndexChanged.connect(lambda *_: self.loc())
        self.loc()

    def _ve(self):
        b = self.bang
        b.blockSignals(True)
        b.setRowCount(len(self.ds))
        xam = QColor('#94A3B8')
        for r, x in enumerate(self.ds):
            g = x['giu']
            khoa = bool(g) and not g.get('cua_toi')
            it = QTableWidgetItem('')
            if khoa:
                it.setFlags(Qt.ItemFlag.ItemIsSelectable)               # người khác đang nhận: không đánh dấu được
            else:
                it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
                it.setCheckState(Qt.CheckState.Unchecked)
            dang = (f'{g["tai_khoan"]} (máy {g["may"]})' + (' - bạn' if g.get('cua_toi') else '')) if g else ''
            _dien(b, r, [None, x['stt'], x['ho_ten'], x['cccd'], x['dia_chi'], x['to_thua'], x['dot'], dang])
            b.setItem(r, 0, it)
            if khoa:
                for c in range(1, len(self.COT)):
                    b.item(r, c).setForeground(xam)
                b.item(r, 7).setToolTip(f'Đang được "{g["tai_khoan"]}" nhận làm trên máy {g["may"]} từ {g["luc"].replace("T", " ")}')
        b.blockSignals(False)
        self._dem()

    def la_khoa(self, r: int) -> bool:
        g = self.ds[r]['giu']
        return bool(g) and not g.get('cua_toi')

    def loc(self):
        k = self._bo_dau(self.o_tim.text()).split()
        dot, ap = self.cb_dot.currentData() or '', self.cb_ap.currentData() or ''
        for r, x in enumerate(self.ds):
            an = (dot and x['dot'] != dot) or (ap and x['ap'] != ap) or not all(t in x['_tim'] for t in k)
            self.bang.setRowHidden(r, bool(an))
        self._dem()

    def _dat(self, r: int, chon: bool) -> None:
        if not self.la_khoa(r):
            self.bang.item(r, 0).setCheckState(Qt.CheckState.Checked if chon else Qt.CheckState.Unchecked)

    def chon_khoang(self, tu: int | None = None, den: int | None = None) -> int:
        tu = self.o_tu.value() if tu is None else tu
        den = self.o_den.value() if den is None else den
        if tu > den:
            tu, den = den, tu
        n = 0
        self.bang.blockSignals(True)
        for r, x in enumerate(self.ds):
            if tu <= x['stt'] <= den and not self.bang.isRowHidden(r) and not self.la_khoa(r):
                self._dat(r, True)
                n += 1
        self.bang.blockSignals(False)
        self._dem()
        return n

    def chon_dang_hien(self, chon: bool, tat_ca: bool = False) -> None:
        self.bang.blockSignals(True)
        for r in range(len(self.ds)):
            if tat_ca or not self.bang.isRowHidden(r):
                self._dat(r, chon)
        self.bang.blockSignals(False)
        self._dem()

    def ds_chon(self) -> list:
        return [x['ma_ho'] for r, x in enumerate(self.ds)
                if not self.la_khoa(r) and self.bang.item(r, 0).checkState() == Qt.CheckState.Checked]

    def _dem(self):
        n = len(self.ds_chon())
        khoa = sum(1 for r in range(len(self.ds)) if self.la_khoa(r))
        self.lb.setText(f'Đã chọn {n} hộ · {khoa} hộ đang được người khác nhận (khóa)')
        self.b_ok.setEnabled(n > 0)
        self.b_ok.setText(f'Nhận {n} hộ về làm offline' if n else 'Nhận về làm offline')

    def accept(self):
        if not self.ds_chon():
            self.bao('Chọn ít nhất một hộ (đánh dấu ô đầu dòng, hoặc Chọn khoảng STT).', loi=False)
            return
        super().accept()


"""Màn hình quản lý hồ sơ trình: đợt trình + thư mục hồ sơ, trạng thái xử lý hộ, nhập quyết định từ file, kiểm tra lỗi.
Logic ở quan_ly.py, kiem_loi.py; hàm thao tác nhận tham số để kiểm thử (im_lang = True: không hiện hộp thông báo).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
                               QPlainTextEdit, QProgressDialog, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from . import kiem_loi, quan_ly
from .lap_pa import LoiNhap
from .tien import D, vn

TIEU_DE = 'Quản lý hồ sơ trình phương án'
DO, VANG, XANH = QColor('#F8CBAD'), QColor('#FFF2CC'), QColor('#E2EFDA')


def _html(s: str) -> str:
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _bang(cot: list, rong: list) -> QTableWidget:
    b = QTableWidget(0, len(cot))
    b.setHorizontalHeaderLabels(cot)
    b.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    b.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    b.verticalHeader().setVisible(False)
    b.setAlternatingRowColors(True)
    for c, w in enumerate(rong):
        b.setColumnWidth(c, w)
    b.horizontalHeader().setStretchLastSection(True)
    return b


def _o(b: QTableWidget, r: int, c: int, v, so: bool = False, nen=None):
    it = QTableWidgetItem('' if v is None else str(v))
    it.setToolTip('' if v is None else str(v))
    if so:
        it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    if nen is not None:
        it.setBackground(QBrush(nen))
    b.setItem(r, c, it)
    return it


class _Hop(QDialog):
    im_lang = False

    def bao(self, chu: str, loi: bool = True) -> None:
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TIEU_DE, chu)

    def hoi(self, chu: str) -> bool:
        return self.im_lang or QMessageBox.question(self, TIEU_DE, chu) == QMessageBox.StandardButton.Yes

    def doc_co_tien_do(self, ham, *a, **k):
        return doc_co_tien_do(self, ham, *a, **k)


def doc_co_tien_do(cha, ham, *a, **k):
    """Gọi ham(..., bao_tien_do=, cho=) với hộp tiến trình (bản scan phải nhận dạng chữ từng trang, mất vài giây/trang)."""
    im_lang = getattr(cha, 'im_lang', False)
    tien = QProgressDialog('Đang đọc file…', 'Hủy', 0, 0, cha)
    tien.setWindowTitle(TIEU_DE)
    tien.setWindowModality(Qt.WindowModality.WindowModal)
    tien.setMinimumDuration(300)

    def bao(i, n):
        tien.setMaximum(n)
        tien.setValue(i - 1)
        tien.setLabelText(f'Bản scan: đang nhận dạng chữ trang {i}/{n}…')
        QApplication.processEvents()

    def cho() -> bool:
        QApplication.processEvents()
        return tien.wasCanceled()
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        return ham(*a, bao_tien_do=bao, cho=None if im_lang else cho, **k)
    finally:
        QApplication.restoreOverrideCursor()
        tien.close()


# ---------------------------------------------------------------- sửa thông tin một đợt
class HopSuaDot(_Hop):
    def __init__(self, parent=None, dot: quan_ly.Dot | None = None):
        super().__init__(parent)
        self.setWindowTitle('Sửa đợt trình' if dot else 'Thêm đợt trình')
        self.o_ten = QLineEdit(dot.ten if dot else '')
        self.o_ten.setPlaceholderText('Để trống: tự đặt "Đợt N"')
        self.o_ngay = QLineEdit(dot.ngay_trinh if dot else '')
        self.o_ngay.setPlaceholderText('ngày/tháng/năm')
        self.o_so = QLineEdit(dot.so_to_trinh if dot else '')
        self.o_gc = QLineEdit(dot.ghi_chu if dot else '')
        form = QFormLayout(self)
        form.addRow('Tên đợt:', self.o_ten)
        form.addRow('Ngày trình:', self.o_ngay)
        form.addRow('Số tờ trình:', self.o_so)
        form.addRow('Ghi chú:', self.o_gc)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Save).setText('Lưu')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        form.addRow(nut)

    def gia_tri(self) -> dict:
        return dict(ten=self.o_ten.text(), ngay_trinh=self.o_ngay.text(), so_to_trinh=self.o_so.text(), ghi_chu=self.o_gc.text())


# ---------------------------------------------------------------- đợt trình
class HopDotTrinh(_Hop):
    """Lập các đợt trình (Đợt 1 - 25 hộ…), xếp hộ vào đợt, chọn thư mục hồ sơ dự án, xuất PA chi tiết theo thư mục đợt."""

    def __init__(self, con, parent=None, ma_ho_chon: list | None = None, file_du_an=None, chi_doc: bool = False):
        super().__init__(parent)
        self.con, self.file_du_an, self.chi_doc = con, file_du_an, chi_doc
        self.ma_ho_chon = [m for m in (ma_ho_chon or []) if m is not None]
        self.thay_doi = False
        self.setWindowTitle('Đợt trình phương án và thư mục hồ sơ')
        self.resize(1250, 700)
        self.o_goc = QLineEdit(str(quan_ly.thu_muc_ho_so(con, file_du_an)))
        b_goc = QPushButton('Chọn thư mục…')
        b_goc.clicked.connect(lambda: self.chon_thu_muc())
        b_mo = QPushButton('Mở thư mục')
        b_mo.clicked.connect(lambda: self._mo(self.o_goc.text()))
        h_goc = QHBoxLayout()
        nhan = QLabel('Thư mục hồ sơ dự án:')
        nhan.setProperty('vai', 'nhan')
        h_goc.addWidget(nhan)
        h_goc.addWidget(self.o_goc, 1)
        h_goc.addWidget(b_goc)
        h_goc.addWidget(b_mo)
        # ---- đợt
        self.bang_dot = _bang(['Đợt', 'Ngày trình', 'Số tờ trình', 'Số hộ', 'Tổng tiền (đ)', 'Thư mục đã xuất'],
                              [110, 90, 110, 60, 130, 300])
        self.bang_dot.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.bang_dot.itemSelectionChanged.connect(lambda: self.ve_ho())
        hd = QHBoxLayout()
        for ten, ham in (('Thêm đợt…', lambda: self.them_dot()), ('Sửa đợt…', lambda: self.sua_dot()),
                         ('Xóa đợt', lambda: self.xoa_dot())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            b.setEnabled(not chi_doc)
            hd.addWidget(b)
        hd.addStretch(1)
        trai = QWidget()
        lt = QVBoxLayout(trai)
        lt.setContentsMargins(0, 0, 0, 0)
        nhan = QLabel('Các đợt trình')
        nhan.setProperty('vai', 'tieu_de')
        lt.addWidget(nhan)
        lt.addWidget(self.bang_dot)
        lt.addLayout(hd)
        # ---- hộ của đợt
        self.lb_ho = QLabel('Hộ trong đợt')
        self.lb_ho.setProperty('vai', 'tieu_de')
        self.bang_ho = _bang(['STT', 'Mã hộ', 'Họ và tên', 'Tổng tiền (đ)', 'Phê duyệt'], [50, 60, 230, 120, 160])
        hh = QHBoxLayout()
        self.b_dua = QPushButton(f'Đưa {len(self.ma_ho_chon)} hộ đang chọn vào đợt')
        self.b_dua.setEnabled(bool(self.ma_ho_chon) and not chi_doc)
        self.b_dua.clicked.connect(lambda: self.dua_vao())
        self.b_con = QPushButton('Đưa các hộ chưa xếp đợt vào đợt')
        self.b_con.clicked.connect(lambda: self.dua_vao(quan_ly.ho_cua_dot(con, None)))
        self.b_bo = QPushButton('Bỏ hộ đã chọn khỏi đợt')
        self.b_bo.clicked.connect(lambda: self.bo_ra())
        for b in (self.b_dua, self.b_con, self.b_bo):
            b.setEnabled(b.isEnabled() and not chi_doc)
            hh.addWidget(b)
        hh.addStretch(1)
        phai = QWidget()
        lp = QVBoxLayout(phai)
        lp.setContentsMargins(0, 0, 0, 0)
        lp.addWidget(self.lb_ho)
        lp.addWidget(self.bang_ho)
        lp.addLayout(hh)
        tach = QSplitter()
        tach.addWidget(trai)
        tach.addWidget(phai)
        tach.setSizes([620, 620])
        # ---- xuất
        self.o_pdf = QCheckBox('Kèm file PDF (qua Microsoft Excel)')
        b_xuat = QPushButton('Xuất hồ sơ đợt đang chọn')
        b_xuat.clicked.connect(lambda: self.xuat())
        b_tat_ca = QPushButton('Xuất tất cả các đợt')
        b_tat_ca.clicked.connect(lambda: self.xuat(tat_ca=True))
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.accept)
        hx = QHBoxLayout()
        hx.addWidget(self.o_pdf)
        hx.addStretch(1)
        hx.addWidget(b_xuat)
        hx.addWidget(b_tat_ca)
        hx.addWidget(b_dong)
        ghi = QLabel('Mỗi đợt xuất vào thư mục con "<Tên đợt> - <số hộ> hộ" của thư mục hồ sơ: phương án chi tiết từng hộ '
                     '(PA_<STT>_<họ tên>.xlsx/.pdf) và BANG_TONG_HOP của đợt. Xuất lại khi số hộ đổi: thư mục cũ được đổi tên '
                     'theo số hộ mới. File dự án .pabt có thể lưu vào cùng thư mục bằng "Lưu dự án thành…".')
        ghi.setWordWrap(True)
        lo = QVBoxLayout(self)
        lo.addLayout(h_goc)
        lo.addWidget(tach, 1)
        lo.addWidget(ghi)
        lo.addLayout(hx)
        self.ve_dot()

    # ---------------------------------------------- hiển thị
    def _tong(self) -> dict:
        from .nghiep_vu import tinh_tat_ca
        return {k.ma_ho: k.tong for k in tinh_tat_ca(self.con)}

    def ve_dot(self, chon_id=None):
        self.tong = self._tong()
        self.ds = quan_ly.ds_dot(self.con)
        cu = chon_id if chon_id is not None else self.dot_chon()
        self.bang_dot.setRowCount(len(self.ds) + 1)
        for r, d in enumerate(self.ds):
            tien = sum((self.tong.get(m, 0) for m in quan_ly.ho_cua_dot(self.con, d.id)), D(0))
            for c, v in enumerate((d.ten, d.ngay_trinh, d.so_to_trinh, d.so_ho, vn(tien), d.thu_muc)):
                _o(self.bang_dot, r, c, v, so=c in (3, 4))
        chua = quan_ly.ho_cua_dot(self.con, None)
        r = len(self.ds)
        for c, v in enumerate(('(Chưa xếp đợt)', '', '', len(chua), vn(sum((self.tong.get(m, 0) for m in chua), D(0))), '')):
            _o(self.bang_dot, r, c, v, so=c in (3, 4), nen=VANG)
        ids = [d.id for d in self.ds]
        self.bang_dot.selectRow(ids.index(cu) if cu in ids else (0 if self.ds else r))
        self.ve_ho()

    def dot_chon(self):
        r = self.bang_dot.currentRow()
        return self.ds[r].id if 0 <= r < len(getattr(self, 'ds', [])) else None

    def ve_ho(self):
        dot = self.dot_chon()
        self.ho_hien = quan_ly.ho_cua_dot(self.con, dot)
        ten = {r['ma_ho']: (r['thu_tu'], r['ho_ten'], r['da_phe_duyet'], r['qd_so'])
               for r in self.con.execute('SELECT ma_ho, thu_tu, ho_ten, da_phe_duyet, qd_so FROM ho')}
        self.lb_ho.setText(f'Hộ trong {next((d.ten for d in self.ds if d.id == dot), "(chưa xếp đợt)")}: {len(self.ho_hien)} hộ')
        self.bang_ho.setRowCount(len(self.ho_hien))
        for r, m in enumerate(self.ho_hien):
            tt, ht, pd, qd = ten[m]
            for c, v in enumerate((tt, m, ht, vn(self.tong.get(m, 0)), ('Đã PD ' + qd) if pd else '')):
                _o(self.bang_ho, r, c, v, so=c in (0, 1, 3), nen=XANH if pd and c == 4 else None)
        self.b_dua.setText(f'Đưa {len(self.ma_ho_chon)} hộ đang chọn vào đợt')
        self.b_con.setEnabled(dot is not None and not self.chi_doc)
        self.b_dua.setEnabled(dot is not None and bool(self.ma_ho_chon) and not self.chi_doc)
        self.b_bo.setEnabled(dot is not None and not self.chi_doc)

    # ---------------------------------------------- thao tác
    def chon_thu_muc(self, thu_muc=None):
        if thu_muc is None:
            thu_muc = QFileDialog.getExistingDirectory(self, 'Chọn thư mục hồ sơ dự án', self.o_goc.text())
            if not thu_muc:
                return None
        if not self.chi_doc:
            quan_ly.dat_thu_muc_ho_so(self.con, thu_muc)
        self.o_goc.setText(str(Path(thu_muc)))
        return thu_muc

    def them_dot(self, gia_tri: dict | None = None):
        if gia_tri is None:
            dlg = HopSuaDot(self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return None
            gia_tri = dlg.gia_tri()
        try:
            i = quan_ly.tao_dot(self.con, **gia_tri)
        except LoiNhap as e:
            self.bao(str(e))
            return None
        self.thay_doi = True
        self.ve_dot(i)
        return i

    def sua_dot(self, gia_tri: dict | None = None):
        dot = self.dot_chon()
        if dot is None:
            return None
        if gia_tri is None:
            dlg = HopSuaDot(self, quan_ly.lay_dot(self.con, dot))
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return None
            gia_tri = dlg.gia_tri()
        try:
            quan_ly.sua_dot(self.con, dot, **gia_tri)
        except LoiNhap as e:
            self.bao(str(e))
            return None
        self.thay_doi = True
        self.ve_dot(dot)
        return dot

    def xoa_dot(self):
        dot = self.dot_chon()
        if dot is None:
            return None
        d = quan_ly.lay_dot(self.con, dot)
        if not self.hoi(f'Xóa {d.ten}? {d.so_ho} hộ của đợt trở về "chưa xếp đợt" (hồ sơ, thư mục đã xuất giữ nguyên).'):
            return None
        quan_ly.xoa_dot(self.con, dot)
        self.thay_doi = True
        self.ve_dot()
        return dot

    def dua_vao(self, ds: list | None = None):
        dot = self.dot_chon()
        ds = self.ma_ho_chon if ds is None else ds
        if dot is None or not ds:
            return 0
        chon = set(ds)                                  # không dùng IN (?,?...): hàng nghìn hộ vượt giới hạn tham số của SQLite cũ
        khac = sum(1 for m, d in self.con.execute('SELECT ma_ho, dot_id FROM ho WHERE dot_id IS NOT NULL')
                   if m in chon and d != dot)
        if khac and not self.hoi(f'{khac} hộ đang thuộc đợt khác: chuyển sang đợt này?'):
            return 0
        n = quan_ly.gan_dot(self.con, ds, dot)
        self.thay_doi = True
        self.ve_dot(dot)
        return n

    def bo_ra(self, ds: list | None = None):
        if ds is None:
            ds = sorted({self.ho_hien[i.row()] for i in self.bang_ho.selectionModel().selectedRows()})
        if not ds:
            self.bao('Chọn hộ trong bảng bên phải.', loi=False)
            return 0
        dot = self.dot_chon()
        n = quan_ly.gan_dot(self.con, ds, None)
        self.thay_doi = True
        self.ve_dot(dot)
        return n

    def xuat(self, tat_ca: bool = False, pdf: bool | None = None):
        pdf = self.o_pdf.isChecked() if pdf is None else pdf
        goc = self.o_goc.text().strip()
        if not goc:
            self.bao('Chọn thư mục hồ sơ dự án.')
            return None
        if not self.chi_doc:
            quan_ly.dat_thu_muc_ho_so(self.con, goc)
        ds = [d.id for d in self.ds if d.so_ho] if tat_ca else [self.dot_chon()]
        ds = [d for d in ds if d is not None]
        if not ds:
            self.bao('Chưa có đợt nào có hộ để xuất.' if tat_ca else 'Chọn một đợt (đã có hộ).')
            return None
        tong_ho = sum(quan_ly.lay_dot(self.con, d).so_ho for d in ds)
        tien_do = None
        if not self.im_lang:
            tien_do = QProgressDialog('Đang xuất hồ sơ…', 'Hủy', 0, tong_ho + len(ds), self)
            tien_do.setWindowModality(Qt.WindowModality.WindowModal)
            tien_do.setMinimumDuration(0)
        kq_tong, da = [], 0
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for d in ds:
                def bao(i, n, _da=da):
                    if tien_do is not None:
                        tien_do.setValue(_da + i)
                        tien_do.setLabelText(f'Đang tạo file Excel: {i}/{n}…')
                        QApplication.processEvents()
                        return tien_do.wasCanceled()
                    return False

                def bao_excel(i, n):            # Excel xuất PDF từng file: giữ giao diện chạy, cho phép Hủy
                    if tien_do is not None:
                        tien_do.setLabelText(f'Microsoft Excel đang xuất PDF: xong {i}/{n} file…')
                        QApplication.processEvents()
                        return tien_do.wasCanceled()
                    return False
                kq = quan_ly.xuat_dot(self.con, d, goc, pdf=pdf, bao_tien_do=bao, bao_excel=bao_excel)
                da += quan_ly.lay_dot(self.con, d).so_ho + 1
                kq_tong.append(kq)
                if tien_do is not None and tien_do.wasCanceled():
                    break
        except Exception as e:                       # file đang mở trong Excel, không ghi được thư mục...
            QApplication.restoreOverrideCursor()
            if tien_do is not None:
                tien_do.close()
            self.bao(f'Không xuất được:\n{e}')
            return kq_tong
        QApplication.restoreOverrideCursor()
        if tien_do is not None:
            tien_do.close()
        self.ve_dot()
        loi = [x for k in kq_tong for x in k['loi']]
        tb = '\n'.join(f'- {Path(k["thu_muc"]).name}: {len(k["excel"])} file Excel' +
                       (f', {len(k["pdf"])} PDF' if k['pdf'] else '') for k in kq_tong)
        if loi:
            tb += '\n\nLỗi PDF:\n' + '\n'.join(loi[:8])
        if not self.im_lang and QMessageBox.question(self, TIEU_DE, f'Đã xuất vào {goc}:\n{tb}\n\nMở thư mục?') == \
                QMessageBox.StandardButton.Yes:
            self._mo(kq_tong[0]['thu_muc'] if len(kq_tong) == 1 else goc)
        return kq_tong

    def _mo(self, p):
        from .in_an import mo_file
        p = Path(p)
        if not p.exists():
            self.bao('Thư mục chưa có (chưa xuất hồ sơ đợt nào).', loi=False)
            return
        mo_file(p)


# ---------------------------------------------------------------- trạng thái xử lý hộ
class HopTrangThai(_Hop):
    """Phê duyệt / chi trả / bàn giao mặt bằng / ghi chú theo dõi cho một hoặc nhiều hộ (nhiều hộ: ô trống = giữ nguyên)."""

    def __init__(self, con, ds_ma_ho: list, parent=None, tong_pa: dict | None = None):
        super().__init__(parent)
        self.con, self.ds_ma_ho = con, list(ds_ma_ho)
        self.tong_pa = tong_pa or {}
        mot = len(self.ds_ma_ho) == 1
        self.mot = mot
        self.kq_qd = None
        tt = quan_ly.doc_trang_thai(con, self.ds_ma_ho[0]) if mot else {}
        ten = con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (self.ds_ma_ho[0],)).fetchone()[0]
        self.setWindowTitle(f'Trạng thái xử lý - {ten} (mã {self.ds_ma_ho[0]})' if mot else
                            f'Trạng thái xử lý - {len(self.ds_ma_ho)} hộ')
        self.resize(720, 560)

        def hop(nhan, khoa):
            o = QCheckBox(nhan)
            o.setTristate(not mot)
            o.setCheckState(Qt.CheckState.Checked if tt.get(khoa) else (Qt.CheckState.Unchecked if mot else
                                                                          Qt.CheckState.PartiallyChecked))
            return o

        def chu(khoa, cho=''):
            o = QLineEdit(str(tt.get(khoa) or '') if not khoa.endswith('so_tien') else (vn(tt[khoa]) if tt.get(khoa) else ''))
            o.setPlaceholderText(cho if mot else 'để trống: giữ nguyên')
            return o
        self.o = dict(da_phe_duyet=hop('Đã phê duyệt phương án', 'da_phe_duyet'), qd_so=chu('qd_so', 'ví dụ 1234/QĐ-UBND'),
                      qd_ngay=chu('qd_ngay', 'ngày/tháng/năm'), qd_so_tien=chu('qd_so_tien', 'đồng'), qd_file=chu('qd_file'),
                      da_chi_tra=hop('Đã chi trả tiền bồi thường, hỗ trợ', 'da_chi_tra'),
                      chi_tra_ngay=chu('chi_tra_ngay', 'ngày/tháng/năm'), chi_tra_so_tien=chu('chi_tra_so_tien', 'đồng'),
                      da_ban_giao=hop('Đã hoàn tất bàn giao mặt bằng', 'da_ban_giao'),
                      ban_giao_ngay=chu('ban_giao_ngay', 'ngày/tháng/năm'))
        self.o_theo_doi = QPlainTextEdit(tt.get('theo_doi', '') if mot else '')
        self.o_theo_doi.setPlaceholderText('Ghi chú theo dõi tiến độ (vướng mắc, hẹn làm việc…)' if mot else
                                           'để trống: giữ nguyên ghi chú từng hộ')
        self.o_theo_doi.setMaximumHeight(90)
        self.o_theo_pa = QCheckBox('Số tiền phê duyệt / chi trả = tổng phương án của từng hộ')
        self.o_theo_pa.setChecked(False)
        b_file = QPushButton('Chọn file…')
        b_file.clicked.connect(lambda: self._chon_file())
        g1 = QGroupBox('Phê duyệt phương án')
        f1 = QFormLayout(g1)
        f1.addRow(self.o['da_phe_duyet'])
        f1.addRow('Số quyết định:', self.o['qd_so'])
        f1.addRow('Ngày quyết định:', self.o['qd_ngay'])
        f1.addRow('Số tiền phê duyệt (đ):', self.o['qd_so_tien'])
        hf = QHBoxLayout()
        hf.addWidget(self.o['qd_file'], 1)
        hf.addWidget(b_file)
        f1.addRow('File quyết định:', hf)
        # kết quả tự đọc số QĐ, ngày, số tiền phê duyệt từ file quyết định (một hộ)
        self.lb_qd = QLabel('')
        self.lb_qd.setWordWrap(True)
        self.lb_qd.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lb_qd.setVisible(False)
        f1.addRow(self.lb_qd)
        if mot:
            b_file.setToolTip('Chọn file quyết định (PDF, Word, Excel, ảnh scan): phần mềm tự đọc số quyết định, ngày và '
                              'số tiền phê duyệt của hộ để điền sẵn')
        g2 = QGroupBox('Chi trả')
        f2 = QFormLayout(g2)
        f2.addRow(self.o['da_chi_tra'])
        f2.addRow('Ngày chi trả:', self.o['chi_tra_ngay'])
        f2.addRow('Số tiền đã chi (đ):', self.o['chi_tra_so_tien'])
        g3 = QGroupBox('Bàn giao mặt bằng')
        f3 = QFormLayout(g3)
        f3.addRow(self.o['da_ban_giao'])
        f3.addRow('Ngày bàn giao:', self.o['ban_giao_ngay'])
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Save).setText('Lưu')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        for g in (g1, g2, g3):
            lo.addWidget(g)
        lo.addWidget(self.o_theo_pa)
        lo.addWidget(QLabel('Ghi chú theo dõi:'))
        lo.addWidget(self.o_theo_doi)
        lo.addWidget(nut)
        self._goc = self._doc_o()

    def _chon_file(self):
        p, _ = QFileDialog.getOpenFileName(self, 'Chọn file quyết định', '', 'Văn bản (*.pdf *.docx *.doc *.xlsx *.xls *.jpg *.png);;'
                                                                             'Tất cả (*.*)')
        if p:
            self.o['qd_file'].setText(p)
            if self.mot:
                self.doc_quyet_dinh(p)

    def doc_quyet_dinh(self, file, dien: bool | None = None):
        """Đọc file quyết định cho hộ đang mở; hỏi người dùng rồi điền số QĐ, ngày, số tiền phê duyệt (chưa lưu - bấm Lưu).
        dien: True/False bỏ qua câu hỏi (kiểm thử). Trả quan_ly.KetQuaQDHo hoặc None."""
        from . import ocr
        if Path(file).suffix.lower() not in ('.pdf', '.docx', '.xlsx', '.xlsm', '.csv', '.txt') + ocr.DUOI_ANH:
            return None
        ma = self.ds_ma_ho[0]
        try:
            kq = self.doc_co_tien_do(quan_ly.doc_qd_mot_ho, self.con, file, ma, self.tong_pa.get(ma))
        except ocr.DaHuy:
            return None
        except (LoiNhap, ocr.LoiOCR, OSError, ValueError) as e:
            self._hien_qd(f'Không tự đọc được số tiền từ file: {e}', VANG)
            return None
        self.kq_qd = kq
        dong = [f'Số quyết định: <b>{kq.so_qd or "—"}</b>', f'Ngày: <b>{kq.ngay or "—"}</b>',
                f'Số tiền phê duyệt của hộ: <b>{vn(kq.so_tien) + " đ" if kq.so_tien is not None else "không tìm thấy"}</b>']
        if kq.cach:
            dong.append(f'Lấy từ: {kq.cach}' + (' (đã cộng kiểm tra các khoản: khớp)' if kq.chac_chan else ''))
        if kq.nguon:
            dong.append(f'<i>{_html(kq.nguon[:220])}</i>')
        dong += [f'⚠ {_html(x)}' for x in kq.ghi_chu]
        if kq.ocr:
            dong.append('(Bản scan: đã nhận dạng chữ tự động - nên đối chiếu với văn bản.)')
        self._hien_qd('<br>'.join(dong), XANH if kq.so_tien is not None and kq.chac_chan and not kq.ghi_chu else VANG)
        if not (kq.so_qd or kq.ngay or kq.so_tien is not None):
            return kq
        if dien is None:
            dien = self.im_lang or QMessageBox.question(
                self, TIEU_DE, 'Đọc được từ file quyết định:\n\n' + '\n'.join(
                    x for x in (f'Số quyết định: {kq.so_qd}' if kq.so_qd else '', f'Ngày: {kq.ngay}' if kq.ngay else '',
                                f'Số tiền phê duyệt: {vn(kq.so_tien)} đồng ({kq.cach})' if kq.so_tien is not None else '',
                                *kq.ghi_chu) if x) + '\n\nĐiền vào các ô? (kiểm tra lại rồi bấm Lưu)') == QMessageBox.StandardButton.Yes
        if dien:
            if kq.so_qd:
                self.o['qd_so'].setText(kq.so_qd)
            if kq.ngay:
                self.o['qd_ngay'].setText(kq.ngay)
            if kq.so_tien is not None:
                self.o['qd_so_tien'].setText(vn(kq.so_tien))
            self.o['da_phe_duyet'].setCheckState(Qt.CheckState.Checked)
        return kq

    def _hien_qd(self, chu: str, nen: QColor):
        self.lb_qd.setText(chu)
        self.lb_qd.setStyleSheet(f'QLabel {{ background: {nen.name()}; border-radius: 5px; padding: 6px 8px; }}')
        self.lb_qd.setVisible(True)
        self.lb_qd.setMinimumHeight(self.lb_qd.heightForWidth(max(300, self.lb_qd.width())))
        self.resize(self.width(), max(self.height(), self.sizeHint().height()))

    def _doc_o(self) -> dict:
        kq = {}
        for k, w in self.o.items():
            kq[k] = w.checkState() if isinstance(w, QCheckBox) else w.text().strip()
        kq['theo_doi'] = self.o_theo_doi.toPlainText().strip()
        return kq

    def gia_tri(self) -> dict:
        """Các trường người dùng đã đổi (so với lúc mở)."""
        moi = self._doc_o()
        gt = {}
        for k, v in moi.items():
            if v == self._goc[k]:
                continue
            if isinstance(v, Qt.CheckState):
                if v == Qt.CheckState.PartiallyChecked:
                    continue
                gt[k] = v == Qt.CheckState.Checked
            else:
                gt[k] = v
        return gt

    def luu(self, gia_tri: dict | None = None) -> int:
        gt = self.gia_tri() if gia_tri is None else gia_tri
        n = 0
        if self.o_theo_pa.isChecked():
            for m in self.ds_ma_ho:
                rieng = dict(gt)
                tong = self.tong_pa.get(m)
                if tong is not None:
                    if rieng.get('da_phe_duyet', None) is not False:
                        rieng['qd_so_tien'] = tong
                    if rieng.get('da_chi_tra'):
                        rieng['chi_tra_so_tien'] = tong
                n += quan_ly.cap_nhat_trang_thai(self.con, [m], rieng) if rieng else 0
            return n
        return quan_ly.cap_nhat_trang_thai(self.con, self.ds_ma_ho, gt)

    def accept(self):
        try:
            self.so_ho = self.luu()
        except LoiNhap as e:
            self.bao(str(e))
            return
        super().accept()


# ---------------------------------------------------------------- nhập quyết định / danh sách từ file
class HopNhapQD(_Hop):
    """Đọc quyết định phê duyệt / danh sách chi trả / biên bản bàn giao (Excel, Word, PDF có chữ, CSV), khớp hộ, ghi trạng thái."""
    COT = ['Ghi', 'Mã hộ', 'Họ và tên', 'Khớp theo', 'Số tiền trong file', 'Tổng phương án', 'Số QĐ', 'Ngày', 'Dòng trong file']

    def __init__(self, con, parent=None, tong_pa: dict | None = None, thu_muc_ho_so=None, file=None, loai: str = 'pd'):
        super().__init__(parent)
        self.con, self.tong_pa, self.thu_muc_ho_so = con, tong_pa or {}, thu_muc_ho_so
        self.kq = None
        self.file = None
        self.setWindowTitle('Nhập quyết định phê duyệt, danh sách chi trả, bàn giao từ file')
        self.resize(1250, 680)
        self.cb_loai = QComboBox()
        for k, t in quan_ly.LOAI_NHAP.items():
            self.cb_loai.addItem(t, k)
        self.cb_loai.setCurrentIndex(list(quan_ly.LOAI_NHAP).index(loai))
        self.o_file = QLineEdit()
        self.o_file.setReadOnly(True)
        b_file = QPushButton('Chọn file…')
        b_file.clicked.connect(lambda: self.doc())
        self.o_so = QLineEdit()
        self.o_ngay = QLineEdit()
        self.o_ngay.setPlaceholderText('ngày/tháng/năm')
        self.o_chep = QCheckBox('Chép file vào thư mục hồ sơ dự án')
        self.o_chep.setChecked(bool(thu_muc_ho_so))
        self.bang = _bang(self.COT, [40, 60, 210, 80, 120, 120, 120, 90, 400])
        self.lb = QLabel('Chọn file Excel / Word / PDF có danh sách hộ (họ tên, CCCD hoặc mã hộ; số tiền nếu có).')
        self.lb.setWordWrap(True)
        h1 = QHBoxLayout()
        h1.addWidget(QLabel('Loại:'))
        h1.addWidget(self.cb_loai)
        h1.addWidget(QLabel('File:'))
        h1.addWidget(self.o_file, 1)
        h1.addWidget(b_file)
        h2 = QHBoxLayout()
        h2.addWidget(QLabel('Số quyết định:'))
        h2.addWidget(self.o_so)
        h2.addWidget(QLabel('Ngày:'))
        h2.addWidget(self.o_ngay)
        h2.addWidget(self.o_chep)
        h2.addStretch(1)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText('Cập nhật trạng thái các hộ đã đánh dấu')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Đóng')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        lo.addLayout(h1)
        lo.addLayout(h2)
        lo.addWidget(self.bang, 1)
        lo.addWidget(self.lb)
        lo.addWidget(nut)
        if file:
            self.doc(file)

    def doc(self, file=None):
        """file: một file hoặc danh sách (quyết định + bảng tổng hợp kèm theo, chọn cùng lúc)."""
        if file is None:
            file, _ = QFileDialog.getOpenFileNames(self, 'Chọn file quyết định và bảng danh sách kèm theo (chọn được nhiều file)', '',
                                                   'Văn bản có danh sách (*.xlsx *.xlsm *.docx *.pdf *.csv *.txt *.jpg *.jpeg *.png)')
            if not file:
                return None
        ds = [file] if isinstance(file, (str, Path)) else list(file)
        from . import ocr
        try:
            self.kq = self.doc_co_tien_do(quan_ly.doc_quyet_dinh_nhieu, self.con, ds, self.tong_pa)   # bản scan: nhận dạng chữ
        except ocr.DaHuy:
            return None
        except Exception as e:                      # file hỏng, PDF scan khi máy chưa có bộ nhận dạng chữ...
            self.bao(f'Không đọc được file:\n{e}')
            return None
        self.file = [Path(f) for f in ds] if len(ds) > 1 else Path(ds[0])
        self.o_file.setText('; '.join(str(f) for f in ds))
        if self.kq.so_qd and not self.o_so.text():
            self.o_so.setText(self.kq.so_qd)
        if self.kq.ngay and not self.o_ngay.text():
            self.o_ngay.setText(self.kq.ngay)
        self.ve()
        return self.kq

    def ve(self):
        ds = self.kq.dong if self.kq else []
        self.bang.setRowCount(len(ds))
        for r, d in enumerate(ds):
            it = QTableWidgetItem('')
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if d.chon else Qt.CheckState.Unchecked)
            self.bang.setItem(r, 0, it)
            nen = DO if d.lech_tien else None
            for c, v in enumerate((d.ma_ho, d.ho_ten, d.cach_khop, vn(d.so_tien) if d.so_tien is not None else '',
                                   vn(d.tong_pa) if d.tong_pa is not None else '', d.so_qd, d.ngay, d.nguon), start=1):
                _o(self.bang, r, c, v, so=c in (1, 4, 5), nen=nen if c in (4, 5) else None)
        n_lech = sum(1 for d in ds if d.lech_tien)
        tb = f'Khớp {len(ds)} hộ' + (f', {n_lech} hộ số tiền trong file khác tổng phương án (tô đỏ)' if n_lech else '') + '.'
        if self.kq and self.kq.khong_khop:
            tb += f' {len(self.kq.khong_khop)} dòng không xác định được hộ: ' + '; '.join(self.kq.khong_khop[:3])
        if self.kq and not ds:
            tb = 'Không tìm thấy hộ nào của dự án trong file (cần họ tên đầy đủ, số CCCD hoặc mã hộ).'
        self.lb.setText(tb)

    def ap_dung(self) -> dict:
        if not self.kq:
            raise LoiNhap('Chưa chọn file.')
        for r, d in enumerate(self.kq.dong):
            d.chon = self.bang.item(r, 0).checkState() == Qt.CheckState.Checked
        loai = self.cb_loai.currentData()
        return quan_ly.ap_quyet_dinh(self.con, loai, self.kq.dong, self.o_so.text().strip(), self.o_ngay.text().strip(),
                                     file_goc=self.file, thu_muc_luu=self.thu_muc_ho_so if self.o_chep.isChecked() else None)

    def accept(self):
        try:
            self.ket_qua = self.ap_dung()
        except (LoiNhap, OSError) as e:
            self.bao(str(e))
            return
        self.bao(f'Đã cập nhật {self.ket_qua["so_ho"]} hộ.' +
                 (f'\nĐã chép file vào {self.ket_qua["file_luu"]}' if self.ket_qua['file_luu'] else ''), loi=False)
        super().accept()


# ---------------------------------------------------------------- kiểm tra lỗi
class HopKiemLoi(_Hop):
    COT = ['Mức độ', 'Nhóm', 'Mã hộ', 'Họ và tên', 'Nội dung']

    def __init__(self, con, parent=None, dm=None, chi_doc: bool = False, ten_du_an: str = ''):
        super().__init__(parent)
        self.con, self.dm, self.chi_doc, self.ten_du_an = con, dm, chi_doc, ten_du_an
        self.ma_ho_chon = None
        self.da_sua = False
        self.setWindowTitle('Kiểm tra lỗi trước khi trình')
        self.resize(1300, 720)
        self.lb = QLabel('')
        self.lb.setProperty('vai', 'bang_ten')
        self.lb.setWordWrap(True)
        self.cb_nhom = QComboBox()
        self.cb_nhom.addItem('Tất cả nhóm', '')
        for n in kiem_loi.NHOM:
            self.cb_nhom.addItem(n, n)
        self.o_chi_loi = QCheckBox('Chỉ hiện lỗi')
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Lọc theo họ tên, nội dung…')
        self.bang = _bang(self.COT, [80, 130, 60, 220, 700])
        self.bang.doubleClicked.connect(lambda *_: self.mo_ho())
        h = QHBoxLayout()
        h.addWidget(QLabel('Nhóm:'))
        h.addWidget(self.cb_nhom)
        h.addWidget(self.o_chi_loi)
        h.addWidget(self.o_tim, 1)
        hn = QHBoxLayout()
        for ten, ham, bat in (('Kiểm tra lại', lambda: self.kiem_tra(), True),
                              ('Sửa tự động lỗi trình bày', lambda: self.sua_tu_dong(), not chi_doc),
                              ('Xuất Excel…', lambda: self.xuat(), True)):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            b.setEnabled(bat)
            hn.addWidget(b)
        hn.addStretch(1)
        b = QPushButton('Đóng')
        b.clicked.connect(self.reject)
        hn.addWidget(b)
        ghi = QLabel('Nhấp đúp một dòng có mã hộ để mở phương án của hộ. "Sửa tự động" chỉ sửa lỗi trình bày (khoảng trắng thừa, '
                     'viết hoa họ tên, chữ tổ hợp, ký tự lạ trong số CCCD); các lỗi khác cần người lập xem lại.')
        ghi.setWordWrap(True)
        lo = QVBoxLayout(self)
        lo.addWidget(self.lb)
        lo.addLayout(h)
        lo.addWidget(self.bang, 1)
        lo.addWidget(ghi)
        lo.addLayout(hn)
        self.cb_nhom.currentIndexChanged.connect(lambda *_: self.ve())
        self.o_chi_loi.toggled.connect(lambda *_: self.ve())
        self.o_tim.textChanged.connect(lambda *_: self.ve())
        self.kiem_tra()

    def kiem_tra(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.ds = kiem_loi.kiem_tra(self.con, self.dm)
        finally:
            QApplication.restoreOverrideCursor()
        loi = sum(1 for x in self.ds if x.muc_do == kiem_loi.LOI)
        cb = len(self.ds) - loi
        sua = sum(1 for x in self.ds if x.sua_duoc)
        self.lb.setText(f'<b>{loi} lỗi</b>, {cb} cảnh báo' + (f' ({sua} mục sửa tự động được)' if sua else '') +
                        ('  -  Không phát hiện vấn đề nào.' if not self.ds else ''))
        self.ve()
        return self.ds

    def ve(self):
        from .lap_pa import bo_dau
        nhom = self.cb_nhom.currentData()
        tu = bo_dau(self.o_tim.text()).split()
        self.hien = [x for x in self.ds if (not nhom or x.nhom == nhom) and (not self.o_chi_loi.isChecked() or x.muc_do == kiem_loi.LOI)
                     and all(t in bo_dau(f'{x.ho_ten} {x.noi_dung} {x.ma_ho}') for t in tu)]
        self.bang.setRowCount(len(self.hien))
        for r, x in enumerate(self.hien):
            nen = DO if x.muc_do == kiem_loi.LOI else VANG
            for c, v in enumerate((x.muc_do, x.nhom, x.ma_ho if x.ma_ho is not None else '', x.ho_ten, x.noi_dung)):
                _o(self.bang, r, c, v, so=c == 2, nen=nen if c == 0 else None)

    def sua_tu_dong(self):
        if not self.hoi('Sửa tự động các lỗi trình bày (khoảng trắng, viết hoa họ tên, chữ tổ hợp, số CCCD) cho toàn dự án?'):
            return 0
        n = kiem_loi.sua_tu_dong(self.con)
        self.da_sua = self.da_sua or n > 0
        self.kiem_tra()
        self.bao(f'Đã sửa {n} ô.', loi=False)
        return n

    def xuat(self, file=None):
        if file is None:
            file, _ = QFileDialog.getSaveFileName(self, 'Lưu kết quả kiểm tra', 'KiemTraLoi.xlsx', 'File Excel (*.xlsx)')
            if not file:
                return None
        try:
            kiem_loi.xuat_excel(self.hien, file, self.ten_du_an)
        except OSError as e:
            self.bao(f'Không ghi được file (đang mở trong Excel?):\n{e}')
            return None
        return file

    def mo_ho(self):
        r = self.bang.currentRow()
        if 0 <= r < len(self.hien) and self.hien[r].ma_ho is not None:
            self.ma_ho_chon = self.hien[r].ma_ho
            self.accept()


__all__ = ['HopDotTrinh', 'HopTrangThai', 'HopNhapQD', 'HopKiemLoi', 'HopSuaDot', 'QHeaderView']

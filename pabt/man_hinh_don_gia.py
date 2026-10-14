"""Màn hình "Bộ đơn giá": xem danh mục đơn giá, chính sách hỗ trợ, tham số - hạn mức, biểu thưởng, văn bản căn cứ;
thêm / sửa / xóa / thay thế một mục (quyền quản trị); cập nhật từ file hoặc Internet; áp vào dự án đang mở."""
from __future__ import annotations
import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout)

from . import csdl, don_gia, quan_tri_bo
from .lap_pa import LoiNhap, bo_dau
from .tien import vn
from .giao_dien import con_tro_cho, loc_khi_ngung_go
from .thong_bao import TEN_UD, chu_loi

_TS = 'SELECT ma, phan_loai, ten, dvt, don_gia, ghi_chu FROM dm_taisan WHERE '
_COT_TS = (['Mã', 'Phân loại', 'Tên', 'ĐVT', 'Đơn giá (đ)', 'Ghi chú'], [70, 240, 420, 80, 110, 300])
# vật nuôi (mục 3 của phương án như cây trồng): mã VN.. của bộ tích hợp (QĐ 31/2025/QĐ-UBND) hoặc mục cập nhật từ văn bản vật
# nuôi (nhap_don_gia.ap_dung ghi phân loại PHAN_LOAI_VAT_NUOI) - thẻ riêng để thấy ngay, không lẫn trong 5.500 dòng cây trồng
_VAT_NUOI = f"(ma LIKE 'VN%' OR phan_loai LIKE '{don_gia.PHAN_LOAI_VAT_NUOI}%')"
THE = [
    # chỉ nhóm 2: các dòng HT / TH (nhóm 4, 5) trong dm_taisan trùng thẻ Chính sách hỗ trợ / Thưởng (người dùng 12/10/2026)
    ('Nhà, công trình', _TS + 'nhom = 2 ORDER BY rowid', *_COT_TS),
    ('Cây trồng', _TS + f'nhom = 3 AND NOT {_VAT_NUOI} ORDER BY rowid', *_COT_TS),
    ('Vật nuôi', _TS + f'nhom = 3 AND {_VAT_NUOI} ORDER BY LENGTH(ma), ma', *_COT_TS),
    ('Chính sách hỗ trợ (QĐ 42/2025)', 'SELECT ma, ten, dvt, don_gia, can_cu, cach_tinh FROM dm_hotro ORDER BY LENGTH(ma), ma',
     ['Mã', 'Khoản hỗ trợ', 'ĐVT', 'Đơn giá / hệ số', 'Căn cứ', 'Cách tính'], [55, 420, 90, 110, 330, 330]),
    ('Tham số, hạn mức đất NN', 'SELECT ma, ten, gia_tri, dvt, can_cu, trang_thai FROM tham_so',
     ['Mã', 'Tham số', 'Giá trị', 'ĐVT', 'Căn cứ', 'Trạng thái'], [120, 430, 90, 90, 330, 160]),
    ('Thưởng bàn giao mặt bằng', 'SELECT tu, muc FROM bieu_thuong ORDER BY CAST(tu AS REAL)',
     ['Mã', 'Tổng bồi thường, hỗ trợ từ (đ)', 'Mức thưởng (đ/hộ)'], [60, 220, 180]),     # Mã TH1… chỉ hiển thị (0.9.69)
    ('Văn bản căn cứ', 'SELECT id, so_hieu, co_quan, noi_dung, trang_thai FROM van_ban ORDER BY id',
     ['Văn bản', 'Cơ quan', 'Nội dung áp dụng', 'Trạng thái'], [380, 200, 440, 230]),
]
# bảng + cột khóa từng thẻ (cột 0 của SQL là khóa khi bang in quy_uoc/van_ban — không hiện)
THE_BANG = (
    ('dm_taisan', 'ma'), ('dm_taisan', 'ma'), ('dm_taisan', 'ma'),
    ('dm_hotro', 'ma'), ('tham_so', 'ma'), ('bieu_thuong', 'tu'),
    ('van_ban', 'id'),
)
# 0.9.69: bỏ thẻ "Quy ước giá tương đương" (người dùng: quy ước tùy biến từng máy / dự án - nhập ở Đơn giá đặc biệt)
I_QUY_UOC = -1
_AN_KHOA = {'quy_uoc', 'van_ban'}           # cột đầu SQL là id, không đưa lên bảng
NHOM_THE = {0: 2, 1: 3, 2: 3}              # nhà = nhóm 2; cây / vật nuôi = nhóm 3


class HopBoDonGia(QDialog):

    im_lang = False             # True: không hiện hộp thông báo (kiểm thử); nội dung lưu ở thong_bao_cuoi

    def _bao(self, ham, chu):
        self.thong_bao_cuoi = chu
        if not self.im_lang:
            ham(self, TEN_UD, chu)
    def __init__(self, parent=None, con_du_an=None, chi_doc: bool = False):
        super().__init__(parent)
        self.con_du_an = con_du_an
        self.chi_doc = chi_doc
        self.da_ap = False
        self._da_mo_khoa = False            # đã xác thực quản trị trong phiên hộp thoại này
        self.setWindowTitle('Đơn giá bồi thường, hỗ trợ, tái định cư')
        self.resize(1300, 720)
        # dải thông tin một dòng (người dùng 13/10/2026: thay khối mô tả 4 dòng) - mô tả đầy đủ ở chú thích
        self.lb = QLabel()
        self.lb.setObjectName('dai_bo_don_gia')
        self.lb.setFixedHeight(28)
        self.lb.setStyleSheet('QLabel#dai_bo_don_gia { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; '
                              'padding: 0 10px; color: #334155; }')
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm trong thẻ đang xem (không cần dấu): xoai, nha cap 4, CS9…')
        loc_khi_ngung_go(self.o_tim, self.loc)
        self.the = QTabWidget()
        # hàng nút gọn (trước 0.9.17: 7 nút một hàng, chật ở màn hình 1366): lệnh cùng việc gom vào nút xổ, việc chính ở bên phải
        nut = QHBoxLayout()
        # 0.9.73: bỏ Giá đất / Đơn giá riêng (đã có ở menu trái: Bảng giá đất, Đơn giá đặc biệt) và cập nhật từ web, tra cứu
        # trên trình duyệt (người dùng: không dùng được); thêm / sửa / thay thế / xóa một mục: chuột phải trên bảng
        self.b_cap = QPushButton('Cập nhật đơn giá')
        self.b_cap.setToolTip('Nạp bộ đơn giá từ file định mức, hoặc sao lưu bộ đang dùng ra file')
        m = QMenu(self.b_cap)
        m.addAction('Nạp từ file định mức (Excel, gói .sqlite, CSV)…', lambda: self.cap_nhat_file())
        m.addAction('Sao lưu bộ đơn giá ra file (.sqlite / Excel)…', lambda: self.sao_luu())
        self.b_cap.setMenu(m)
        self.b_qt = self.b_sua = QPushButton('Quản trị bảo mật')
        self.b_qt.setToolTip('Quyền sửa bộ đơn giá: tài khoản quản trị máy chủ hoặc mật khẩu quản trị trên máy này. Thêm / sửa / '
                             'thay thế / xóa một mục: bấm chuột phải trên bảng')
        m = QMenu(self.b_qt)
        m.addAction('Mở khóa quản trị (cho phép sửa / xóa)…', lambda: self.mo_khoa_quan_tri())
        m.addAction('Đổi mật khẩu quản trị…', lambda: self.doi_mat_khau_quan_tri())
        m.addSeparator()
        m.addAction('Khôi phục bộ đơn giá chuẩn gốc của Tỉnh…', lambda: self.khoi_phuc_goc())
        self.b_qt.setMenu(m)
        self.b_ap = QPushButton('Áp bộ đơn giá vào dự án đang mở')
        self.b_ap.clicked.connect(lambda: self.ap_du_an())
        dong = QPushButton('Đóng')
        dong.clicked.connect(self.accept)
        for b in (self.b_cap, self.b_qt):
            nut.addWidget(b)
        nut.addStretch(1)
        nut.addWidget(self.b_ap)
        nut.addWidget(dong)
        self.b_ap.setEnabled(con_du_an is not None and not chi_doc)
        lo = QVBoxLayout(self)
        lo.addWidget(self.lb)
        lo.addWidget(self.o_tim)
        lo.addWidget(self.the, 1)
        lo.addLayout(nut)
        self.nap()

    def trang_thai_khoa(self) -> str:
        """Trạng thái quyền sửa bộ đơn giá hiện trên dải thông tin."""
        if self._da_mo_khoa:
            return 'Đã mở khóa (sửa được)'
        if quan_tri_bo.la_quan_tri_may_chu():
            return 'Tài khoản quản trị máy chủ'
        return 'Đã kích hoạt' if quan_tri_bo.da_dat() else 'Chưa đặt mật khẩu'

    def _dat_tieu(self):
        tt = don_gia.thong_tin()
        so_vb = []                       # quyết định của UBND tỉnh làm căn cứ bộ đơn giá: "…42/2025/QĐ-UBND…" -> "QĐ 42/2025"
        for v in tt.get('van_ban') or ():
            sh = str(v.get('so_hieu') or '')
            m = re.search(r'(\d+/\d{4})/QĐ-UBND', sh)
            if m and not sh.lower().startswith('dự thảo') and f'QĐ {m.group(1)}' not in so_vb:
                so_vb.append(f'QĐ {m.group(1)}')
        vb = (' (' + ', '.join(so_vb[:6]) + (', …' if len(so_vb) > 6 else '') + ')') if so_vb else ''
        self.lb.setText(f'<b>{tt["ten"]}</b> {tt["phien_ban"]}{vb}  ·  Khóa quản trị: <b>{self.trang_thai_khoa()}</b>')
        them = ('\nThẻ "Quy ước giá tương đương" đang hiện quy ước của dự án mở - đồng bộ với Đơn giá đặc biệt.'
                if self.con_du_an is not None else '')
        self.lb.setToolTip(f'{tt["ten"]} - phiên bản {tt["phien_ban"]} (nguồn {tt["nguon"]}, đóng gói {tt["ngay"][:10]})\n'
                           f'{tt["ghi_chu"]}\n\nThêm / sửa / thay thế / xóa một mục (chuột phải trên bảng) hoặc nạp cả bộ: '
                           f'cần quyền quản trị. {quan_tri_bo.mo_ta_quyen()}{them}')

    def _bang_the(self, i, ds) -> tuple:
        """(bảng, nhãn thẻ) từ các dòng SQL của thẻ i."""
        ten, _sql, cot, rong = THE[i]
        bang, _ck = THE_BANG[i]
        b = QTableWidget(len(ds), len(cot))
        b.setHorizontalHeaderLabels(cot)
        b.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        b.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        b.setAlternatingRowColors(True)
        b.verticalHeader().setVisible(False)
        for c, w in enumerate(rong):
            b.setColumnWidth(c, w)
        b.horizontalHeader().setStretchLastSection(True)
        b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        b.customContextMenuRequested.connect(lambda pos, b=b: self._menu_bang(b, pos))
        b.setToolTip('Chuột phải: thêm / sửa / thay thế / xóa mục (cần mở khóa quản trị)')
        an_khoa = bang in _AN_KHOA
        for r, dong in enumerate(ds):
            khoa = dong[0]
            vals = dong[1:] if an_khoa else dong
            if bang == 'bieu_thuong':                   # biểu thưởng không lưu mã: TH1, TH2… theo thứ tự mức (ma_tai_san)
                from .ma_tai_san import ma_thuong
                vals = (ma_thuong(r + 1), *vals)
            for c, v in enumerate(vals):
                s = '' if v is None else str(v)
                if cot[c].startswith(('Đơn giá', 'Mức thưởng', 'Tổng bồi')) and s.replace('.', '').isdigit() and float(s) >= 100:
                    s = vn(s)
                it = QTableWidgetItem(s)
                it.setToolTip(s)
                b.setItem(r, c, it)
            if b.item(r, 0) is not None:
                b.item(r, 0).setData(Qt.ItemDataRole.UserRole, khoa)
        nhan = f'{ten} ({len(ds)})'
        if i == I_QUY_UOC and self.con_du_an is not None:
            nhan = f'{ten} · dự án ({len(ds)})'
        return b, nhan

    def _menu_bang(self, b, pos):
        """Chuột phải trên bảng: thêm / sửa / thay thế / xóa mục của thẻ đang xem (tự hỏi mở khóa quản trị khi cần)."""
        r = b.rowAt(pos.y())
        if r >= 0:
            b.selectRow(r)
        co = r >= 0 and b.item(r, 0) is not None
        m = QMenu(self)
        m.addAction('Thêm mục…', lambda: self.them_muc()).setEnabled(not self.chi_doc)
        for chu, ham in (('Sửa dòng đang chọn…', self.sua_muc), ('Thay thế dòng đang chọn…', self.thay_muc),
                         ('Xóa dòng đang chọn…', self.xoa_muc)):
            m.addAction(chu, lambda ham=ham: ham()).setEnabled(co and not self.chi_doc)
        if not self._da_mo_khoa:
            m.addSeparator()
            m.addAction('Mở khóa quản trị…', lambda: self.mo_khoa_quan_tri())
        m.exec(b.viewport().mapToGlobal(pos))
        m.deleteLater()

    def sao_luu(self, p=None):
        """Sao lưu bộ đơn giá đang dùng ra .sqlite (nạp lại được) hoặc Excel (mỗi danh mục một sheet)."""
        if p is None:
            p, _ = QFileDialog.getSaveFileName(self, 'Sao lưu bộ đơn giá',
                                               f'BoDonGia_{don_gia.thong_tin()["phien_ban"]}.sqlite',
                                               'Gói bộ đơn giá (*.sqlite);;Excel (*.xlsx)')
            if not p:
                return None
        try:
            with con_tro_cho():
                f = don_gia.sao_luu_bo(p)
        except Exception as e:
            self._bao(QMessageBox.warning, chu_loi('Không sao lưu được bộ đơn giá', e))
            return None
        self._bao(QMessageBox.information, f'Đã sao lưu bộ đơn giá: {f}')
        return f

    def khoi_phuc_goc(self, xac_nhan=None, mat_khau=None):
        """Dùng lại bộ đơn giá chuẩn đóng gói (bản đã cập nhật / sửa trên máy được cất lại, không xóa). Cần quyền quản trị."""
        if not self._can_sua(mat_khau):
            return None
        if xac_nhan is None:
            xac_nhan = self.im_lang or QMessageBox.question(
                self, TEN_UD, 'Dùng lại bộ đơn giá chuẩn gốc kèm phần mềm? Bộ đang dùng trên máy (đã cập nhật / sửa) được cất '
                              'thành file sao lưu cạnh đó, không bị xóa.') == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        try:
            tt = don_gia.khoi_phuc_bo_goc()
        except Exception as e:
            self._bao(QMessageBox.warning, chu_loi('Không khôi phục được bộ đơn giá gốc', e))
            return None
        self.nap()
        self._bao(QMessageBox.information, f'Đang dùng bộ đơn giá chuẩn gốc phiên bản {tt["phien_ban"]}.' +
                  (f' Bộ cũ cất tại: {tt["cat"]}' if tt['cat'] else ''))
        return tt

    def nap(self):
        self._dat_tieu()
        i_giu = self.the.currentIndex()
        self.the.clear()
        self._khoa_the = {}                             # loc: chữ tìm từng dòng của mỗi thẻ (dựng lại khi nạp lại bộ đơn giá)
        con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
        try:
            for i, (_ten, sql, _cot, _rong) in enumerate(THE):
                src = self.con_du_an if i == I_QUY_UOC and self.con_du_an is not None else con
                b, nhan = self._bang_the(i, src.execute(sql).fetchall())
                self.the.addTab(b, nhan)
        finally:
            con.close()
        if 0 <= i_giu < self.the.count():
            self.the.setCurrentIndex(i_giu)

    def nap_quy_uoc(self):
        """Chỉ dựng lại thẻ quy ước (sau Đơn giá riêng) — không đọc lại 5.500 dòng nhà / cây. Không còn thẻ quy ước: bỏ qua."""
        if I_QUY_UOC < 0:
            return
        if self.the.count() <= I_QUY_UOC:
            self.nap()
            return
        ten, sql, _cot, _rong = THE[I_QUY_UOC]
        if self.con_du_an is not None:
            ds = self.con_du_an.execute(sql).fetchall()
        else:
            con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
            try:
                ds = con.execute(sql).fetchall()
            finally:
                con.close()
        b, nhan = self._bang_the(I_QUY_UOC, ds)
        cu = self.the.widget(I_QUY_UOC)
        self.the.removeTab(I_QUY_UOC)
        if cu is not None:
            cu.deleteLater()
        self.the.insertTab(I_QUY_UOC, b, nhan)
        self.the.setCurrentIndex(I_QUY_UOC)
        self._khoa_the.pop(I_QUY_UOC, None)
        self._dat_tieu()

    def mo_khoa_quan_tri(self, mat_khau=None, mat_khau2=None) -> bool:
        """Xác thực quyền sửa bộ đơn giá. Kiểm thử: truyền mat_khau (lần đầu = đặt mật khẩu)."""
        if self._da_mo_khoa:
            return True
        if quan_tri_bo.la_quan_tri_may_chu():
            self._da_mo_khoa = True
            self._dat_tieu()
            return True
        if quan_tri_bo.bi_chan_may_chu():
            self._bao(QMessageBox.warning, quan_tri_bo.mo_ta_quyen())
            return False
        if self.im_lang:
            if mat_khau is None:
                return False
            try:
                if not quan_tri_bo.da_dat():
                    quan_tri_bo.dat(mat_khau)
                elif not quan_tri_bo.dung(mat_khau):
                    return False
            except LoiNhap:
                return False
            self._da_mo_khoa = True
            return True
        d = HopXacThucBo(self)
        if mat_khau is not None:
            d.o_mk.setText(mat_khau)
            if hasattr(d, 'o_lai'):
                d.o_lai.setText(mat_khau2 if mat_khau2 is not None else mat_khau)
            if d.thu():
                d.accept()
        elif d.exec() != QDialog.DialogCode.Accepted:
            return False
        self._da_mo_khoa = True
        self._dat_tieu()
        return True

    def _can_sua(self, mat_khau=None) -> bool:
        if self.chi_doc:
            self._bao(QMessageBox.information, 'Dự án đang mở chỉ xem: không sửa bộ đơn giá từ đây.')
            return False
        return self.mo_khoa_quan_tri(mat_khau)

    def _the_bang(self):
        i = self.the.currentIndex()
        if i < 0:
            return None
        return i, THE_BANG[i][0], THE_BANG[i][1]

    def _khoa_chon(self):
        b = self.the.currentWidget()
        if b is None or b.currentRow() < 0 or b.item(b.currentRow(), 0) is None:
            return None
        return b.item(b.currentRow(), 0).data(Qt.ItemDataRole.UserRole)

    def _nhom_the(self):
        return NHOM_THE.get(self.the.currentIndex())

    def them_muc(self, gt=None, mat_khau=None, cho: bool = True):
        t = self._the_bang()
        if t is None:
            return None
        i, bang, _ck = t
        if i == I_QUY_UOC and self.con_du_an is not None:
            return self.don_gia_rieng(cho=cho)          # quy ước của dự án: sửa ở Đơn giá riêng (đồng bộ thẻ này)
        if not self._can_sua(mat_khau):
            return None
        if gt is None and i == 2:
            gt = dict(nhom=3, phan_loai=don_gia.PHAN_LOAI_VAT_NUOI)
        d = HopSuaMuc(bang, None, self._nhom_the(), self, False)
        if gt:
            d.dat(gt)
        if not cho:
            return d
        if not self.im_lang and d.exec() != QDialog.DialogCode.Accepted:
            return None
        try:
            kq = don_gia.them_dong(bang, d.gia_tri(), self._nhom_the())
        except LoiNhap as e:
            self._bao(QMessageBox.warning, str(e))
            return None
        self.nap()
        self._bao(QMessageBox.information, 'Đã thêm mục vào bộ đơn giá trên máy này. Dự án đang mở muốn dùng mục mới thì bấm '
                                              '"Áp bộ đơn giá vào dự án đang mở".')
        return kq

    def sua_muc(self, gt=None, mat_khau=None, cho: bool = True):
        return self._ghi_muc('sua', gt, mat_khau, cho)

    def thay_muc(self, gt=None, mat_khau=None, cho: bool = True):
        return self._ghi_muc('thay', gt, mat_khau, cho)

    def _ghi_muc(self, viec: str, gt=None, mat_khau=None, cho: bool = True):
        t = self._the_bang()
        if t is None:
            return None
        i, bang, _ck = t
        if i == I_QUY_UOC and self.con_du_an is not None:
            return self.don_gia_rieng(cho=cho)
        khoa = self._khoa_chon()
        if khoa is None:
            self._bao(QMessageBox.information, 'Hãy chọn một dòng trên thẻ đang xem.')
            return None
        if not self._can_sua(mat_khau):
            return None
        cu = don_gia.doc_dong(bang, khoa)
        if cu is None:
            self._bao(QMessageBox.warning, 'Không đọc được dòng đang chọn (bộ đơn giá vừa đổi?).')
            return None
        d = HopSuaMuc(bang, cu, self._nhom_the(), self, viec == 'thay')
        if gt:
            d.dat(gt)
        if not cho:
            return d
        if not self.im_lang and d.exec() != QDialog.DialogCode.Accepted:
            return None
        try:
            ham = don_gia.thay_the_dong if viec == 'thay' else don_gia.sua_dong
            kq = ham(bang, khoa, d.gia_tri(), self._nhom_the())
        except LoiNhap as e:
            self._bao(QMessageBox.warning, str(e))
            return None
        self.nap()
        return kq

    def xoa_muc(self, xac_nhan=None, mat_khau=None):
        t = self._the_bang()
        if t is None:
            return None
        i, bang, _ck = t
        if i == I_QUY_UOC and self.con_du_an is not None:
            return self.don_gia_rieng()
        khoa = self._khoa_chon()
        if khoa is None:
            self._bao(QMessageBox.information, 'Hãy chọn một dòng trên thẻ đang xem.')
            return None
        if not self._can_sua(mat_khau):
            return None
        cu = don_gia.doc_dong(bang, khoa) or {}
        ten = cu.get('ten') or cu.get('ten_thuc_te') or cu.get('so_hieu') or str(khoa)
        if xac_nhan is None:
            xac_nhan = self.im_lang or QMessageBox.question(
                self, TEN_UD, f'Xóa mục "{ten}" khỏi bộ đơn giá trên máy này?\nDự án đã lập không tự mất mục này '
                              '(chỉ dự án mới / lần "Áp bộ đơn giá" sau).') == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        try:
            kq = don_gia.xoa_dong(bang, khoa)
        except LoiNhap as e:
            self._bao(QMessageBox.warning, str(e))
            return None
        self.nap()
        return kq

    def doi_mat_khau_quan_tri(self, cu=None, moi=None):
        if quan_tri_bo.la_quan_tri_may_chu():
            self._bao(QMessageBox.information, 'Bạn đang đăng nhập tài khoản quản trị máy chủ — không cần mật khẩu riêng.')
            return False
        if quan_tri_bo.bi_chan_may_chu():
            self._bao(QMessageBox.warning, quan_tri_bo.mo_ta_quyen())
            return False
        if self.im_lang:
            if cu is None or moi is None:
                return False
            try:
                quan_tri_bo.dat(moi, cu)
            except LoiNhap as e:
                self.thong_bao_cuoi = str(e)
                return False
            return True
        d = HopXacThucBo(self, doi=True)
        return d.exec() == QDialog.DialogCode.Accepted

    def loc(self, chu: str):
        b = self.the.currentWidget()
        i = self.the.currentIndex()
        if i not in self._khoa_the:     # chữ không dấu từng dòng: tính một lần mỗi thẻ (trước: ghép lại 5.510 dòng × 6 ô mỗi phím)
            self._khoa_the[i] = ([bo_dau(' '.join(b.item(r, c).text() for c in range(b.columnCount()) if b.item(r, c)))
                                  for r in range(b.rowCount())], [False] * b.rowCount())
        khoa, an = self._khoa_the[i]
        tu = bo_dau(chu).split()
        b.setUpdatesEnabled(False)
        try:
            for r, k in enumerate(khoa):
                h = bool(tu) and not all(x in k for x in tu)
                if h != an[r]:                  # chỉ đổi dòng đổi trạng thái (setRowHidden từng dòng là phần tốn nhất)
                    b.setRowHidden(r, h)
                    an[r] = h
        finally:
            b.setUpdatesEnabled(True)

    def cap_nhat_file(self, p=None, mat_khau=None):
        if not self._can_sua(mat_khau):
            return None
        if p is None:
            p, _ = QFileDialog.getOpenFileName(self, 'Chọn file đơn giá', '',
                                               'File đơn giá (*.xlsx *.xlsm *.docx *.pdf *.csv *.sqlite);;Tất cả (*.*)')
            if not p:
                return None
        from .nhap_tho import la_file_pabt
        if Path(p).suffix.lower() != '.sqlite' and not (Path(p).suffix.lower() in ('.xlsx', '.xlsm') and la_file_pabt(p)):
            return self.cap_nhat_file_bat_ky(p)
        try:
            with con_tro_cho():
                tt = don_gia.cap_nhat_tu_file(p)
        except Exception as e:
            self._bao(QMessageBox.warning, chu_loi('Không cập nhật được', e))
            return None
        self.nap()
        self._bao(QMessageBox.information, f'Đã cập nhật bộ đơn giá phiên bản {tt["phien_ban"]}. Dự án mới dùng bộ này; '
                                              'dự án đang lập muốn đổi thì bấm "Áp bộ đơn giá vào dự án đang mở".')
        return tt

    def cap_nhat_file_bat_ky(self, p, nguon: str = '', cho: bool = True, mat_khau=None):
        """File Excel / Word / PDF / CSV bất kỳ: xem trước các dòng đơn giá rồi áp dụng."""
        if not self._can_sua(mat_khau):
            return None
        from . import nhap_don_gia as ndg, ocr
        from .man_hinh_nhap_don_gia import HopNhapDonGia
        from .man_hinh_quan_ly import doc_co_tien_do
        try:
            dong = doc_co_tien_do(self, ndg.doc_bang_ocr, p)        # PDF scan: nhận dạng chữ từng trang, có nút Hủy
            d = HopNhapDonGia(p, self, nguon, dong=dong)
        except ocr.DaHuy:
            return None
        except (LoiNhap, ocr.LoiOCR, OSError, ValueError) as e:
            self._bao(QMessageBox.warning, str(e))
            return None
        d.im_lang = self.im_lang
        if not cho:
            return d
        if d.exec() and d.ket_qua:
            self.nap()
        return d.ket_qua

    def ap_du_an(self, xac_nhan=None):
        if self.con_du_an is None or self.chi_doc:
            return None
        if xac_nhan is None:
            xac_nhan = QMessageBox.question(self, TEN_UD, 'Thay danh mục đơn giá, chính sách, tham số của dự án đang mở bằng bộ đơn giá '
                                                          'này? Hồ sơ hộ, thửa, giá đất và phương án đã lập giữ nguyên (dòng đã lập '
                                                          'giữ đơn giá cũ; dùng Rà soát giá để kiểm tra).') == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        tt = don_gia.ap_vao_du_an(self.con_du_an)
        self.da_ap = True
        self._bao(QMessageBox.information, f'Đã áp bộ đơn giá phiên bản {tt["phien_ban"]} vào dự án.')
        return tt


# ---------------------------------------------------------------- hộp mật khẩu / form sửa một mục
_NHAN_O = {
    'ma': 'Mã', 'nhom': 'Nhóm (2 nhà, 3 cây / vật nuôi)', 'phan_loai': 'Phân loại', 'ten': 'Tên',
    'dvt': 'Đơn vị tính', 'don_gia': 'Đơn giá (đồng)', 'ghi_chu': 'Ghi chú', 'can_cu': 'Căn cứ',
    'cach_tinh': 'Cách tính', 'gia_tri': 'Giá trị', 'trang_thai': 'Trạng thái',
    'tu': 'Tổng bồi thường, hỗ trợ từ (đồng)', 'muc': 'Mức thưởng (đồng/hộ)',
    'ten_thuc_te': 'Tên thực tế', 'ten_tuong_duong': 'Áp giá tương đương',
    'so_hieu': 'Số hiệu văn bản', 'co_quan': 'Cơ quan', 'noi_dung': 'Nội dung áp dụng',
}


class HopXacThucBo(QDialog):
    """Đặt mật khẩu lần đầu, nhập mật khẩu, hoặc đổi mật khẩu quản trị bộ đơn giá."""

    def __init__(self, parent=None, doi: bool = False):
        super().__init__(parent)
        self.doi = doi
        self.setWindowTitle('Đổi mật khẩu quản trị bộ đơn giá' if doi else 'Quyền quản trị bộ đơn giá')
        self.resize(460, 200)
        lo = QVBoxLayout(self)
        if doi:
            chu = 'Nhập mật khẩu hiện tại và mật khẩu mới (ít nhất 6 ký tự).'
        elif quan_tri_bo.da_dat():
            chu = 'Nhập mật khẩu quản trị bộ đơn giá trên máy này để thêm, sửa, xóa hoặc thay thế một mục / cập nhật cả bộ.'
        else:
            chu = ('Máy này chưa có mật khẩu quản trị bộ đơn giá. Đặt mật khẩu (ít nhất 6 ký tự) — người không có mật khẩu '
                   'không tự ý đổi đơn giá được.')
        lb = QLabel(chu)
        lb.setWordWrap(True)
        lo.addWidget(lb)
        f = QFormLayout()
        self.o_cu = QLineEdit()
        self.o_cu.setEchoMode(QLineEdit.EchoMode.Password)
        self.o_mk = QLineEdit()
        self.o_mk.setEchoMode(QLineEdit.EchoMode.Password)
        self.o_lai = QLineEdit()
        self.o_lai.setEchoMode(QLineEdit.EchoMode.Password)
        if doi or not quan_tri_bo.da_dat():
            if doi:
                f.addRow('Mật khẩu hiện tại:', self.o_cu)
            f.addRow('Mật khẩu mới:', self.o_mk)
            f.addRow('Nhập lại:', self.o_lai)
        else:
            f.addRow('Mật khẩu:', self.o_mk)
        lo.addLayout(f)
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        self.lb.setStyleSheet('color: #C62828;')
        lo.addWidget(self.lb)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.accepted.connect(self.thu)
        nut.rejected.connect(self.reject)
        lo.addWidget(nut)
        self.o_mk.setFocus()

    def thu(self) -> bool:
        mk = self.o_mk.text()
        try:
            if self.doi:
                if mk != self.o_lai.text():
                    raise LoiNhap('Mật khẩu mới nhập lại không khớp.')
                quan_tri_bo.dat(mk, self.o_cu.text())
            elif not quan_tri_bo.da_dat():
                if mk != self.o_lai.text():
                    raise LoiNhap('Mật khẩu nhập lại không khớp.')
                quan_tri_bo.dat(mk)
            elif not quan_tri_bo.dung(mk):
                raise LoiNhap('Mật khẩu không đúng.')
        except LoiNhap as e:
            self.lb.setText(str(e))
            return False
        self.accept()
        return True


class HopSuaMuc(QDialog):
    """Form thêm / sửa / thay thế một dòng danh mục của bộ đơn giá."""

    def __init__(self, bang: str, gt=None, nhom=None, parent=None, thay: bool = False):
        super().__init__(parent)
        self.bang, self.thay = bang, thay
        gt = dict(gt or {})
        if nhom is not None and 'nhom' not in gt:
            gt['nhom'] = nhom
        if bang == 'dm_taisan' and int(gt.get('nhom') or 0) == 3 and not gt.get('phan_loai'):
            if (gt.get('ma') or '').upper().startswith('VN'):
                gt['phan_loai'] = don_gia.PHAN_LOAI_VAT_NUOI
        viec = 'Thay thế' if thay else ('Sửa' if gt.get(don_gia.KHOA_SUA.get(bang, 'ma')) else 'Thêm')
        self.setWindowTitle(f'{viec} mục bộ đơn giá')
        self.resize(560, 320)
        self.o = {}
        f = QFormLayout()
        ck = don_gia.KHOA_SUA[bang]
        for k in don_gia.COT_SUA[bang]:
            if k == 'nhom':
                cb = QComboBox()
                cb.addItem('2 — Nhà, công trình', 2)
                cb.addItem('3 — Cây trồng, vật nuôi', 3)
                n = int(gt.get('nhom') or nhom or 2)
                cb.setCurrentIndex(0 if n == 2 else 1)
                self.o[k] = cb
                f.addRow(_NHAN_O[k] + ':', cb)
                continue
            e = QLineEdit(str(gt.get(k) or ''))
            if k == ck and gt.get(k) and not thay:
                e.setReadOnly(True)
            self.o[k] = e
            f.addRow(_NHAN_O.get(k, k) + ':', e)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        lo.addLayout(f)
        lo.addWidget(nut)

    def dat(self, gt: dict) -> None:
        for k, w in self.o.items():
            if k not in gt:
                continue
            if isinstance(w, QComboBox):
                i = w.findData(int(gt[k]))
                if i >= 0:
                    w.setCurrentIndex(i)
            else:
                w.setText(str(gt[k] or ''))

    def gia_tri(self) -> dict:
        ra = {}
        for k, w in self.o.items():
            ra[k] = w.currentData() if isinstance(w, QComboBox) else w.text()
        return ra

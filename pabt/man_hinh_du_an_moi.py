"""Màn hình "Dự án mới": 4 bước nhập thô -> tự lập phương án -> 2 bảng in.

Bước 1 thông tin dự án; bước 2 danh sách hộ, thửa (lấy từ Excel bất kỳ rồi sửa ngay trên bảng); bước 3 bảng giá đất của
dự án; bước 4 nơi lưu, tự lập phương án, xuất bảng in. Đây là nơi duy nhất nhập / sửa dữ liệu thô khi lập dự án;
danh mục đơn giá, chính sách, tham số lấy từ bộ đơn giá tích hợp và được cố định.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import csdl, don_gia, du_an_moi, in_an, lap_pa, may_chu, to_chuc
from .giao_dien import ChonXoXuong, bang_to_chuc, chay_nen, con_tro_cho
from .lap_pa import LoiNhap
from .thong_bao import TEN_UD, chu_loi

BUOC = ['1. Thông tin dự án', '2. Danh sách hộ, thửa (nhập thô)', '3. Bảng giá đất của dự án', '4. Hoàn thiện, in']
CAM, XAM = QColor('#FCE4D6'), QColor('#EEF1F4')
COT_GIA = [('loai_dat', 'Loại đất', 80), ('nhom', 'Nhóm', 110), ('vi_tri', 'Vị trí (theo dữ liệu)', 130),
           ('vi_tri_ap', 'Vị trí áp dụng', 110), ('so_thua', 'Số thửa', 70), ('gia', 'Giá bảng giá (đ/m²)', 150),
           ('he_so_k', 'Hệ số K', 80), ('ghi_chu', 'Lưu ý', 360)]


def _nhan(chu):
    w = QLabel(chu)
    w.setProperty('vai', 'nhan')
    return w


class HopDuAnMoi(QDialog):

    im_lang = False             # True: không hiện hộp thông báo (kiểm thử); nội dung lưu ở thong_bao_cuoi

    def _bao(self, ham, chu):
        self.thong_bao_cuoi = chu
        if not self.im_lang:
            ham(self, TEN_UD, chu)
    def __init__(self, parent=None, luu_cai_dat: bool = True):
        super().__init__(parent)
        self.luu_cai_dat = luu_cai_dat
        self.ket_qua = None
        self.setWindowTitle('Dự án mới – nhập dữ liệu thô, tự lập phương án')
        self.resize(1320, 800)
        self.nguon = ''
        self.tieu_de = QLabel()
        self.tieu_de.setProperty('vai', 'bang_ten')
        self.trang = QStackedWidget()
        for ham in (self._trang_1, self._trang_2, self._trang_3, self._trang_4):
            self.trang.addWidget(ham())
        self.b_lui = QPushButton('◀ Quay lại')
        self.b_tiep = QPushButton('Tiếp ▶')
        self.b_tao = QPushButton('Lưu: tạo dự án và lập phương án')
        self.b_huy = QPushButton('Hủy')
        self.b_lui.clicked.connect(lambda: self.sang(self.trang.currentIndex() - 1))
        self.b_tiep.clicked.connect(lambda: self.sang(self.trang.currentIndex() + 1))
        self.b_tao.clicked.connect(lambda: self.tao())
        self.b_huy.clicked.connect(self.reject)
        nut = QHBoxLayout()
        nut.addWidget(self.b_huy)
        nut.addStretch(1)
        for b in (self.b_lui, self.b_tiep, self.b_tao):
            nut.addWidget(b)
        lo = QVBoxLayout(self)
        lo.addWidget(bang_to_chuc())
        lo.addWidget(self.tieu_de)
        lo.addWidget(self.trang, 1)
        lo.addLayout(nut)
        self.sang(0, kiem=False)

    # ---------------------------------------------- bước 1
    def _trang_1(self):
        from .giao_dien import can_giua, the_form
        w = QWidget()
        lo = QVBoxLayout(w)
        self.o = {}
        cai = QSettings('PABT', 'PABT') if self.luu_cai_dat else None
        du_an, don_vi = [], []
        for k, ten in lap_pa.TRUONG_DU_AN:
            if k == 'cap_dia_ban':
                o = QComboBox()
                o.addItems(['Xã', 'Phường', 'Thị trấn', 'Đặc khu'])
            else:
                o = QLineEdit()
                if k == 'nam':
                    o.setText(str(datetime.now().year))
                if k in csdl.TRUONG_DON_VI:
                    o.setText(str((cai.value(f'don_vi/{k}', '') if cai is not None else '') or to_chuc.MAC_DINH.get(k, '')))
            self.o[k] = o
            (don_vi if k in csdl.TRUONG_DON_VI else du_an).append(
                (ten + (' *' if k in ('ten', 'ten_dia_ban') else '') + ':', o))
        lo.addWidget(can_giua(the_form('Thông tin dự án', du_an, 120), the_form('Đơn vị lập, người ký', don_vi, 170)))
        tt = don_gia.thong_tin()
        ghi = QLabel(f'Danh mục đơn giá, chính sách hỗ trợ, tham số: bộ đơn giá tích hợp phiên bản <b>{tt["phien_ban"]}</b> '
                     f'({tt["dem"]["dm_taisan"]} tài sản, cây trồng; {tt["dem"]["dm_hotro"]} khoản hỗ trợ) - cố định, '
                     'không sửa trong dự án. Thông tin đơn vị, người ký được nhớ cho lần sau.')
        ghi.setWordWrap(True)
        ghi.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lo.addWidget(ghi)
        lo.addStretch(1)
        return w

    # ---------------------------------------------- bước 2
    def _trang_2(self):
        w = QWidget()
        lo = QVBoxLayout(w)
        hang = QHBoxLayout()
        for ten, ham in (('Nhập file Excel thô…', lambda: self.nap_excel()), ('Thêm dòng', lambda: self.them_dong()),
                         ('Xóa dòng', lambda: self.xoa_dong())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            hang.addWidget(b)
        hang.addStretch(1)
        lo.addLayout(hang)
        self.bang_tho = QTableWidget(0, len(du_an_moi.COT_THO))
        self.bang_tho.setHorizontalHeaderLabels([t + (' ▾' if k in ('loai_dat', 'vi_tri') else '') for k, t in du_an_moi.COT_THO])
        self.bang_tho.setAlternatingRowColors(True)
        self.bang_tho.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.bang_tho.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.SelectedClicked
                                      | QAbstractItemView.EditTrigger.EditKeyPressed | QAbstractItemView.EditTrigger.AnyKeyPressed)
        for c, rong in enumerate((180, 250, 110, 85, 120, 100, 70, 85, 105, 135, 95, 75, 110, 180)):
            self.bang_tho.setColumnWidth(c, rong)
        cot = {k: c for c, (k, _) in enumerate(du_an_moi.COT_THO)}
        self.xo_loai_dat = ChonXoXuong([(ma, f'{ma} – {ten}') for ma, ten, _ in du_an_moi.ds_loai_dat()], self.bang_tho)
        self.xo_vi_tri = ChonXoXuong([(v, f'Vị trí {v}') for v in du_an_moi.VI_TRI], self.bang_tho)
        self.bang_tho.setItemDelegateForColumn(cot['loai_dat'], self.xo_loai_dat)
        self.bang_tho.setItemDelegateForColumn(cot['vi_tri'], self.xo_vi_tri)
        lo.addWidget(self.bang_tho, 1)
        self.lb_tho = QLabel('Vùng dữ liệu thô (riêng, không thuộc vùng đơn giá): họ tên, địa chỉ, CCCD, diện tích… lấy từ file Excel '
                             'và sửa được ngay trên bảng. Loại đất, vị trí: nhấp đúp để chọn trong danh sách xổ xuống (hoặc gõ tay). '
                             'Mỗi dòng một thửa; họ tên để trống = thửa tiếp của hộ phía trên. Thửa nhiều loại đất (ONT+CLN): tách '
                             'thành nhiều dòng, mỗi loại một diện tích.')
        self.lb_tho.setWordWrap(True)
        lo.addWidget(self.lb_tho)
        return w

    def nap_excel(self, file_excel=None):
        if file_excel is None:
            file_excel, _ = QFileDialog.getOpenFileName(self, 'Chọn file Excel danh sách hộ, thửa', '', 'File Excel (*.xlsx *.xlsm)')
            if not file_excel:
                return None
        try:
            dong, kq = du_an_moi.dong_tu_excel(file_excel)
        except Exception as e:
            self._bao(QMessageBox.warning, chu_loi('Không đọc được file', e))
            return None
        if kq.loi:
            self._bao(QMessageBox.warning, '\n'.join(kq.loi))
            return None
        self.dat_dong(dong)
        self.nguon = Path(file_excel).name
        if not self.o['ten'].text() and kq.tieu_de_bang:
            self.o['ten'].setText(kq.tieu_de_bang)
        from .nhap_tho import mo_ta_cot
        self.lb_tho.setText(f'Đã lấy {len(dong)} dòng từ {Path(file_excel).name} - nhận cột: {mo_ta_cot(kq.bo_cot)}. '
                            f'{len(kq.canh_bao)} điểm cần xem lại (sửa ngay trên bảng).')
        return dong

    def dat_dong(self, dong):
        self.bang_tho.setRowCount(0)
        for r in dong:
            self.them_dong(r)

    def them_dong(self, r=None):
        i = self.bang_tho.rowCount() if r is not None or self.bang_tho.currentRow() < 0 else self.bang_tho.currentRow() + 1
        self.bang_tho.insertRow(i)
        for c, (k, _) in enumerate(du_an_moi.COT_THO):
            self.bang_tho.setItem(i, c, QTableWidgetItem(str((r or {}).get(k, '') or '')))
        return i

    def xoa_dong(self):
        for i in sorted({x.row() for x in self.bang_tho.selectedIndexes()}, reverse=True):
            self.bang_tho.removeRow(i)

    def dong_tho(self) -> list:
        return [{k: (self.bang_tho.item(i, c).text() if self.bang_tho.item(i, c) else '')
                 for c, (k, _) in enumerate(du_an_moi.COT_THO)} for i in range(self.bang_tho.rowCount())]

    # ---------------------------------------------- bước 3
    def _trang_3(self):
        w = QWidget()
        lo = QVBoxLayout(w)
        lo.addWidget(QLabel('Giá đất theo bảng giá đất của địa bàn (NQ 28/2025/NQ-HĐND hoặc văn bản thay thế) và hệ số K '
                            '(QĐ hệ số điều chỉnh giá đất hiện hành). Dòng thiếu vị trí: nhập "Vị trí áp dụng" cho các thửa đó.'))
        self.bang_gia = QTableWidget(0, len(COT_GIA))
        self.bang_gia.setHorizontalHeaderLabels([c[1] for c in COT_GIA])
        self.bang_gia.setAlternatingRowColors(True)
        for c, (_, _, rong) in enumerate(COT_GIA):
            self.bang_gia.setColumnWidth(c, rong)
        self.bang_gia.horizontalHeader().setStretchLastSection(True)
        lo.addWidget(self.bang_gia, 1)
        h = QHBoxLayout()
        b = QPushButton('Tra bảng giá đất NQ 28/2025… (dòng đang chọn)')
        b.clicked.connect(lambda: self.tra_gia_nq28())
        h.addWidget(b)
        h.addWidget(QLabel('Có sẵn: Xã Trị An, Xã Tân An, Xã Phú Lý, Phường Tân Triều. Giá lấy về vẫn sửa được.'))
        h.addStretch(1)
        lo.addLayout(h)
        return w

    def tra_gia_nq28(self, r=None, chon=None):
        """Mở hộp tra giá (lọc theo xã của dự án, loại đất của dòng) và điền giá dòng được chọn vào bảng giá đất."""
        from .man_hinh_gia_dat import HopTraGiaDat
        from . import gia_dat_nq28 as nq
        r = self.bang_gia.currentRow() if r is None else r
        if not 0 <= r < self.bang_gia.rowCount():
            self._bao(QMessageBox.information, 'Chọn một dòng (loại đất, vị trí) trong bảng giá đất trước.')
            return None
        g = self.gia_dat()[r]
        if chon is None:
            d = HopTraGiaDat(self, self.o['ten_dia_ban'].text(), g['loai_dat'])
            if not d.exec() or d.chon is None:
                return None
            chon = d.chon
        dong, cot = chon
        cot_ten = {k: c for c, (k, _, _) in enumerate(COT_GIA)}
        self.bang_gia.item(r, cot_ten['gia']).setText(str(nq.gia_dong(dong, cot)))
        self.bang_gia.item(r, cot_ten['ghi_chu']).setText(nq.can_cu(dong, cot))
        self.bang_gia.item(r, cot_ten['ghi_chu']).setToolTip(nq.can_cu(dong, cot))
        return nq.gia_dong(dong, cot)

    def lap_bang_gia(self):
        cu = {(g['loai_dat'], g['vi_tri']): g for g in self.gia_dat()} if self.bang_gia.rowCount() else {}
        ds = du_an_moi.bang_gia_can_nhap(self.dong_tho())
        self.bang_gia.setRowCount(0)
        for g in ds:
            g = dict(g, **{k: cu.get((g['loai_dat'], g['vi_tri']), {}).get(k, '') for k in ('vi_tri_ap', 'gia', 'he_so_k')})
            g['he_so_k'] = g['he_so_k'] or '1'
            cc = cu.get((g['loai_dat'], g['vi_tri']), {}).get('ghi_chu', '')
            if cc.startswith('NQ 28/2025'):                   # giữ căn cứ giá đã tra từ bảng giá đất
                g['ghi_chu'] = cc
            r = self.bang_gia.rowCount()
            self.bang_gia.insertRow(r)
            for c, (k, _, _) in enumerate(COT_GIA):
                it = QTableWidgetItem(str(g.get(k, '')))
                sua = k in ('gia', 'he_so_k') or (k == 'vi_tri_ap' and not g['vi_tri'])
                if not sua:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    it.setBackground(QBrush(XAM))
                elif not g['loai_dat']:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    it.setBackground(QBrush(XAM))
                if k == 'ghi_chu' and g['ghi_chu']:
                    it.setBackground(QBrush(CAM))
                self.bang_gia.setItem(r, c, it)

    def gia_dat(self) -> list:
        return [{k: (self.bang_gia.item(i, c).text() if self.bang_gia.item(i, c) else '') for c, (k, _, _) in enumerate(COT_GIA)}
                for i in range(self.bang_gia.rowCount())]

    def dat_gia(self, loai_dat, vi_tri, gia, he_so_k='1', vi_tri_ap=''):
        """Điền giá cho một dòng bảng giá (dùng khi kiểm thử)."""
        for i, g in enumerate(self.gia_dat()):
            if g['loai_dat'] == loai_dat and g['vi_tri'] == vi_tri:
                cot = {k: c for c, (k, _, _) in enumerate(COT_GIA)}
                self.bang_gia.item(i, cot['gia']).setText(str(gia))
                self.bang_gia.item(i, cot['he_so_k']).setText(str(he_so_k))
                self.bang_gia.item(i, cot['vi_tri_ap']).setText(str(vi_tri_ap))
                return True
        return False

    # ---------------------------------------------- bước 4
    def _trang_4(self):
        w = QWidget()
        lo = QVBoxLayout(w)
        f = QFormLayout()
        self.o_file = QLineEdit()
        b = QPushButton('Chọn…')
        b.clicked.connect(self.chon_file)
        h = QHBoxLayout()
        h.addWidget(self.o_file, 1)
        h.addWidget(b)
        f.addRow(_nhan('Lưu file dự án (.pabt):'), h)
        self.c_tu_lap = QCheckBox('Tự lập phương án: mục 1 từ các thửa (giá theo bảng giá đất), mục 4 theo gợi ý hỗ trợ QĐ 42/2025')
        self.c_tu_lap.setChecked(True)
        self.c_in = QCheckBox('Xuất 2 bảng in chuẩn (phương án chi tiết từng hộ, bảng tổng hợp) vào thư mục cạnh file dự án')
        self.c_in.setChecked(True)
        self.c_pdf = QCheckBox('Kèm PDF (cần Microsoft Excel)')
        self.c_pdf.setChecked(in_an.co_excel())
        self.c_pdf.setEnabled(in_an.co_excel())
        for c in (self.c_tu_lap, self.c_in, self.c_pdf):
            f.addRow(c)
        lo.addLayout(f)
        self.tom_tat = QPlainTextEdit()
        self.tom_tat.setReadOnly(True)
        lo.addWidget(self.tom_tat, 1)
        return w

    def chon_file(self):
        mac_dinh = self.o_file.text() or str(may_chu.thu_muc_mac_dinh() / f'{self.o["ten"].text()[:60] or "DuAn"}.pabt')
        p, _ = QFileDialog.getSaveFileName(self, 'Lưu file dự án', mac_dinh, 'Dự án PABT (*.pabt)')
        if p:
            self.o_file.setText(p)

    def thong_tin(self) -> dict:
        return {k: (o.currentText() if isinstance(o, QComboBox) else o.text()) for k, o in self.o.items()}

    def cap_nhat_tom_tat(self):
        ho, thua, loi, cb = du_an_moi.gom(self.dong_tho())
        thieu = [g for g in self.gia_dat() if g['loai_dat'] and not g['gia'].strip()]
        dong = [f'Dự án: {self.o["ten"].text()} - {self.o["cap_dia_ban"].currentText()} {self.o["ten_dia_ban"].text()}',
                f'{len(ho)} hộ, {len(thua)} thửa; {len(self.gia_dat()) - len(thieu)} giá đất đã nhập, {len(thieu)} còn thiếu.']
        dong += ['LỖI: ' + x for x in loi] + ['Lưu ý: ' + x for x in cb[:40]]
        if thieu:
            dong.append('Thửa thuộc loại đất / vị trí chưa có giá: dòng mục 1 có giá 0, cần bổ sung sau.')
        self.tom_tat.setPlainText('\n'.join(dong))

    # ---------------------------------------------- điều hướng
    def sang(self, i: int, kiem: bool = True) -> bool:
        cu = self.trang.currentIndex()
        if not 0 <= i < len(BUOC):
            return False
        if kiem and i > cu:
            if cu == 0 and (not self.o['ten'].text().strip() or not self.o['ten_dia_ban'].text().strip()):
                self._bao(QMessageBox.information, 'Nhập tên dự án và tên xã, phường.')
                return False
            if cu == 1:
                _, _, loi, _ = du_an_moi.gom(self.dong_tho())
                if loi:
                    self._bao(QMessageBox.warning, 'Sửa các lỗi trước khi tiếp tục:\n' + '\n'.join(loi[:20]))
                    return False
        if i == 2:
            self.lap_bang_gia()
        if i == 3:
            self.cap_nhat_tom_tat()
        self.trang.setCurrentIndex(i)
        self.tieu_de.setText(f'<b>DỰ ÁN MỚI</b> – bước {BUOC[i]}<br>' +
                             '  ›  '.join(('<u>' + b + '</u>') if j == i else b for j, b in enumerate(BUOC)))
        self.b_lui.setEnabled(i > 0)
        self.b_tiep.setVisible(i < len(BUOC) - 1)
        self.b_tao.setVisible(i == len(BUOC) - 1)
        return True

    def tao(self, file_pabt=None, xuat=None):
        p = file_pabt or self.o_file.text().strip()
        if not p:
            self.chon_file()
            p = self.o_file.text().strip()
            if not p:
                return None
        p = Path(p).with_suffix('.pabt')
        if file_pabt is None and p.exists() and QMessageBox.question(
                self, TEN_UD, f'File {p.name} đã có. Ghi đè (mất toàn bộ dữ liệu trong file đó)?') != QMessageBox.StandardButton.Yes:
            return None
        try:
            with con_tro_cho():
                tt, dong, gia, tu_lap = self.thong_tin(), self.dong_tho(), self.gia_dat(), self.c_tu_lap.isChecked()
                # luồng nền (tự mở kết nối file mới): hàng nghìn hộ không làm cửa sổ "Không phản hồi"
                kq = chay_nen(self, lambda: du_an_moi.tao_du_an(p, tt, dong, gia, tu_lap, self.nguon),
                              f'Đang tạo dự án và tự lập phương án ({len(dong)} dòng thửa)…')
                xuat = self.c_in.isChecked() if xuat is None else xuat
                if xuat and kq['so_ho_co_pa']:
                    con = csdl.mo(p)
                    try:
                        thu_muc = p.with_name(f'BanIn_{p.stem}_{datetime.now():%Y%m%d_%H%M}')
                        kq['in'] = du_an_moi.xuat_2_bang(con, thu_muc, pdf=self.c_pdf.isChecked())
                        kq['thu_muc_in'] = str(thu_muc)
                    finally:
                        con.close()
        except LoiNhap as e:
            self._bao(QMessageBox.warning, str(e))
            return None
        except Exception as e:
            self._bao(QMessageBox.critical, chu_loi('Không tạo được dự án', e))
            return None
        if self.luu_cai_dat:
            cai = QSettings('PABT', 'PABT')
            for k in csdl.TRUONG_DON_VI:
                cai.setValue(f'don_vi/{k}', self.thong_tin().get(k, ''))
        self.ket_qua = kq
        self.accept()
        return kq

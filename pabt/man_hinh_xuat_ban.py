"""Xuất bản hồ sơ MỘT CHẠM theo đợt trình (phương án đột phá 6, người dùng 30/10/2026). Bốn bước dẫn đường:
  1 Chọn đợt + chế độ phát hành (dự thảo / chính thức);
  2 Kiểm tra điều kiện: quan_ly.kiem_tra_xuat_dot (số PA chi tiết, văn bản trình, PA tổng, ý kiến) + cờ của phễu tiến độ
    (pheu_tien_do) cho các hộ của đợt - CHỈ NHẮC, không chặn; nút "Xem hộ" mở danh sách hộ của từng cờ;
  3 Xem trước cả bộ: phương án chi tiết (tối đa man_hinh.XEM_NHIEU_TOI_DA hộ đầu) + bảng tổng hợp, gộp một bản PDF có ô nhảy tới hộ;
  4 Xuất bản: Word + PDF + gộp một file (mặc định) / chỉ file Word, Excel / gửi máy in; thư mục mặc định của đợt.
Khâu xuất dùng ĐÚNG man_hinh.HopIn.thuc_hien (hộp ẩn đặt sẵn đợt, chế độ, tài liệu, đầu ra) - một logic xuất duy nhất (tiến trình,
nút Dừng, PDF dự phòng khi thiếu Word, thư mục theo đợt). Mở từ nút "Xuất bản hồ sơ đợt này →" của Đợt trình thẩm định (app.dot_trinh)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QMessageBox, QPushButton, QRadioButton, QSpinBox, QStackedWidget, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from . import pheu_tien_do as ph
from . import quan_ly
from .giao_dien import KieuNut, ap_kieu_nut, dat_trang_thai
from .thong_bao import TEN_UD

BUOC = ('Chọn đợt', 'Kiểm tra', 'Xem trước', 'Xuất bản')
KICH_THUOC = (980, 640)
QSS = '''
QLabel#xb_buoc { color: #475569; background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 12px; padding: 3px 12px;
    font-size: 12px; font-weight: 600; }
QLabel#xb_buoc[dang="1"] { color: #FFFFFF; background: #1E3A5F; border-color: #1E3A5F; }
QLabel#xb_buoc[xong="1"] { color: #1E3A5F; background: #EFF6FF; border-color: #BFDBFE; }
QLabel#xb_tieu_de { font-size: 16px; font-weight: 700; color: #0F172A; }
QLabel#xb_mo_ta { font-size: 12px; color: #475569; }
'''
MUC_KIEM = {True: ('dat', 'Đạt'), None: ('canh_bao', 'Xem lại'), False: ('loi', 'Thiếu')}


class HopXuatBanDot(QDialog):
    im_lang = False

    def __init__(self, con, parent=None, file_du_an=None, dot_id=None, che_do: str = 'chinh_thuc'):
        super().__init__(parent)
        from .giao_dien import dat_kieu_theo_tong
        self.con, self.file_du_an = con, file_du_an
        self.setWindowTitle('Xuất bản hồ sơ theo đợt trình')
        self.resize(*KICH_THUOC)
        dat_kieu_theo_tong(self, QSS)
        self.ds_dot = quan_ly.ds_dot(con)
        self.ket_qua = None
        self._pheu = None
        lo = QVBoxLayout(self)
        lo.setSpacing(8)
        # thanh 4 bước
        h = QHBoxLayout()
        h.setSpacing(6)
        self.nhan_buoc = []
        for i, ten in enumerate(BUOC, 1):
            lb = QLabel(f'{i}  {ten}')
            lb.setObjectName('xb_buoc')
            self.nhan_buoc.append(lb)
            h.addWidget(lb)
            if i < len(BUOC):
                mui = QLabel('›')
                mui.setObjectName('xb_mo_ta')
                h.addWidget(mui)
        h.addStretch(1)
        lo.addLayout(h)
        self.ngan = QStackedWidget()
        lo.addWidget(self.ngan, 1)
        self.ngan.addWidget(self._trang_chon(dot_id, che_do))
        self.ngan.addWidget(self._trang_kiem())
        self.ngan.addWidget(self._trang_xem())
        self.ngan.addWidget(self._trang_xuat())
        # chân: quay lại / tiếp / xuất bản / đóng
        h = QHBoxLayout()
        self.b_lui = QPushButton('← Quay lại')
        self.b_lui.clicked.connect(lambda: self.sang(self.ngan.currentIndex() - 1))
        self.b_tiep = QPushButton('Tiếp →')
        self.b_tiep.clicked.connect(lambda: self.sang(self.ngan.currentIndex() + 1))
        self.b_xuat = QPushButton('Xuất bản')
        self.b_xuat.clicked.connect(lambda: self.xuat_ban())
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        h.addWidget(self.b_lui)
        h.addStretch(1)
        h.addWidget(self.b_tiep)
        h.addWidget(self.b_xuat)
        h.addWidget(b_dong)
        lo.addLayout(h)
        ap_kieu_nut(self.b_tiep, KieuNut.CHINH)
        ap_kieu_nut(self.b_xuat, KieuNut.CHINH)
        self.sang(0)

    # ------------------------------------------------ trang 1: chọn đợt
    def _trang_chon(self, dot_id, che_do) -> QWidget:
        from .man_hinh import MO_TA_CHE_DO
        w = QWidget()
        v = QVBoxLayout(w)
        t = QLabel('Chọn đợt trình cần xuất bản hồ sơ')
        t.setObjectName('xb_tieu_de')
        v.addWidget(t)
        self.bang_dot = QTableWidget(len(self.ds_dot), 4)
        self.bang_dot.setHorizontalHeaderLabels(['Đợt trình', 'Số hộ', 'Văn bản trình', 'Thư mục đã xuất'])
        self.bang_dot.verticalHeader().setVisible(False)
        self.bang_dot.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang_dot.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang_dot.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        hh = self.bang_dot.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        chon = 0
        for r, d in enumerate(self.ds_dot):
            it = QTableWidgetItem(d.ten or f'Đợt {d.so}')
            it.setData(Qt.ItemDataRole.UserRole, d.id)
            self.bang_dot.setItem(r, 0, it)
            it = QTableWidgetItem(str(d.so_ho))
            it.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            self.bang_dot.setItem(r, 1, it)
            self.bang_dot.setItem(r, 2, QTableWidgetItem(d.van_ban_trinh or ''))
            self.bang_dot.setItem(r, 3, QTableWidgetItem(d.thu_muc or 'chưa xuất'))
            if d.id == dot_id:
                chon = r
        if self.ds_dot:
            self.bang_dot.selectRow(chon)
        self.bang_dot.cellDoubleClicked.connect(lambda *_: self.sang(1))
        v.addWidget(self.bang_dot, 1)
        self.lb_khong_dot = QLabel('Dự án chưa có đợt trình. Lập đợt và đưa hộ vào đợt ở "Đợt trình thẩm định" (menu trái nhóm 4).')
        self.lb_khong_dot.setWordWrap(True)
        v.addWidget(self.lb_khong_dot)
        self.lb_khong_dot.setVisible(not self.ds_dot)
        t = QLabel('Chế độ phát hành')
        t.setObjectName('xb_tieu_de')
        v.addWidget(t)
        self.r_du_thao = QRadioButton('Dự thảo niêm yết (có chữ DỰ THẢO, chưa ghi số phương án)')
        self.r_du_thao.setToolTip(MO_TA_CHE_DO['du_thao'])
        self.r_chinh_thuc = QRadioButton('Hồ sơ chính thức trình thẩm định (trọn bộ, số phương án theo đợt)')
        self.r_chinh_thuc.setToolTip(MO_TA_CHE_DO['chinh_thuc'])
        g = QButtonGroup(w)
        for r in (self.r_du_thao, self.r_chinh_thuc):
            g.addButton(r)
            v.addWidget(r)
        (self.r_du_thao if che_do == 'du_thao' else self.r_chinh_thuc).setChecked(True)
        return w

    def dot_chon(self):
        r = self.bang_dot.currentRow()
        it = self.bang_dot.item(r, 0) if r >= 0 else None
        i = it.data(Qt.ItemDataRole.UserRole) if it is not None else None
        return next((d for d in self.ds_dot if d.id == i), None)

    def che_do(self) -> str:
        return 'du_thao' if self.r_du_thao.isChecked() else 'chinh_thuc'

    def ds_ho(self) -> list:
        d = self.dot_chon()
        return quan_ly.ho_cua_dot(self.con, d.id) if d is not None else []

    # ------------------------------------------------ trang 2: kiểm tra điều kiện
    def _trang_kiem(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        self.lb_kiem = QLabel('')
        self.lb_kiem.setObjectName('xb_tieu_de')
        v.addWidget(self.lb_kiem)
        self.lb_tom_kiem = QLabel('')
        self.lb_tom_kiem.setWordWrap(True)
        v.addWidget(self.lb_tom_kiem)
        self.bang_kiem = QTableWidget(0, 3)
        self.bang_kiem.setHorizontalHeaderLabels(['Kết quả', 'Nội dung', ''])
        self.bang_kiem.verticalHeader().setVisible(False)
        self.bang_kiem.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        hh = self.bang_kiem.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        v.addWidget(self.bang_kiem, 1)
        ghi = QLabel('Các điểm "Xem lại" chỉ để nhắc - vẫn xuất bản được. Số phương án, văn bản trình, phương án tổng sửa ở "Đợt trình '
                     'thẩm định"; hộ có cờ mở bằng nút "Xem hộ".')
        ghi.setObjectName('xb_mo_ta')
        ghi.setWordWrap(True)
        v.addWidget(ghi)
        return w

    def kiem_tra(self) -> list:
        """[(muc True / None / False, chữ, ds hộ hoặc None)] của đợt đang chọn: điều kiện đợt + cờ phễu của các hộ trong đợt."""
        d = self.dot_chon()
        if d is None:
            return [(False, 'Chưa chọn đợt trình.', None)]
        kq = [(m, chu, None) for m, chu in quan_ly.kiem_tra_xuat_dot(self.con, d.id)]
        ds = set(self.ds_ho())
        if self._pheu is None:
            self._pheu = ph.tinh(self.con)
        ho = [x for x in self._pheu.ho if x.ma_ho in ds]
        for k, ten in ph.CO:
            co = [x for x in ho if k in x.co]
            if co:
                kq.append((None, f'{len(co)} hộ: {ten.lower()}', co))
        bs = [x for x in ho if 'pa_bo_sung' in x.co]
        if bs:
            kq.append((True, f'{len(bs)} hộ xuất theo phương án bổ sung / điều chỉnh (lần đang mở)', bs))
        return kq

    def _ve_kiem(self) -> None:
        from .man_hinh_tong_quan import HopHoPheu
        d = self.dot_chon()
        ds = self.kiem_tra()
        self.lb_kiem.setText(f'Kiểm tra hồ sơ {d.ten if d else ""}' + (f' · {len(self.ds_ho())} hộ' if d else ''))
        dat = sum(1 for m, _, _ in ds if m is True)
        xem = sum(1 for m, _, _ in ds if m is None)
        thieu = sum(1 for m, _, _ in ds if m is False)
        dat_trang_thai(self.lb_tom_kiem, 'loi' if thieu else 'canh_bao' if xem else 'dat',
                       f'Đạt {dat} · cần xem lại {xem}' + (f' · thiếu {thieu}' if thieu else '') +
                       (' - đủ điều kiện xuất bản.' if not xem and not thieu else ' - vẫn xuất bản được (bản nháp / bổ sung sau).'))
        b = self.bang_kiem
        b.setRowCount(len(ds))
        for r, (m, chu, ho) in enumerate(ds):
            ma, ten = MUC_KIEM[m]
            it = QTableWidgetItem(ten)
            it.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            b.setItem(r, 0, it)
            b.setItem(r, 1, QTableWidgetItem(chu))
            if ho:
                nut = QPushButton('Xem hộ')
                nut.clicked.connect(lambda _=False, ho=ho, chu=chu: self._mo_ds(chu, ho, HopHoPheu))
                b.setCellWidget(r, 2, nut)
            else:
                b.removeCellWidget(r, 2)
        b.resizeColumnToContents(0)
        b.resizeColumnToContents(2)
        self.kiem = ds

    def _mo_ds(self, tieu_de: str, ho: list, lop):
        h = lop(tieu_de, ho, self)
        h.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        h.show()
        return h

    # ------------------------------------------------ trang 3: xem trước
    def _trang_xem(self) -> QWidget:
        from .xem_truoc_tai_lieu import KhungXemTruocTaiLieu
        w = QWidget()
        v = QVBoxLayout(w)
        self.lb_xem = QLabel('')
        self.lb_xem.setObjectName('xb_mo_ta')
        self.lb_xem.setWordWrap(True)
        v.addWidget(self.lb_xem)
        self.w_preview = KhungXemTruocTaiLieu(w)
        v.addWidget(self.w_preview, 1)
        return w

    def tao_xem_truoc(self, thu_muc) -> list:
        """Các file của bản xem trước gộp: [(file, nhãn)] - phương án chi tiết (tối đa XEM_NHIEU_TOI_DA hộ đầu) rồi bảng tổng hợp."""
        from . import du_lieu_in, in_an, in_word
        from .man_hinh import XEM_NHIEU_TOI_DA
        d = self.dot_chon()
        ds = self.ds_ho()
        du_thao = self.che_do() == 'du_thao'
        ten = {r[0]: f'{r[1]}. {r[2]}' for r in self.con.execute('SELECT ma_ho, thu_tu, ho_ten FROM ho')}
        thu_muc = Path(thu_muc)
        kq = [(in_word.xuat_chi_tiet_docx(self.con, m, thu_muc / f'{k:03d}_{du_lieu_in.ten_file_ho(self.con, m)}.docx',
                                          du_thao=du_thao, lan='moi_nhat'), ten.get(m, str(m)))
              for k, m in enumerate(ds[:XEM_NHIEU_TOI_DA], 1)]
        if ds and d is not None:
            f = in_an.lap_bang_tong_hop(self.con, thu_muc / 'BANG_TONG_HOP.xlsx', ds,
                                        so_pa_tong='' if du_thao else d.so_pa_tong, ngay_pa_tong='' if du_thao else d.ngay_pa_tong,
                                        ky_hieu_so=d.ky_hieu_so, du_thao=du_thao)
            kq.append((f, 'Bảng tổng hợp'))
        return kq

    def _xem(self) -> None:
        from .man_hinh import XEM_NHIEU_TOI_DA
        d = self.dot_chon()
        ds = self.ds_ho()
        if d is None or not ds:
            self.lb_xem.setText('Đợt chưa có hộ - không có gì để xem trước.')
            return
        gioi = f' (xem {XEM_NHIEU_TOI_DA} hộ đầu / {len(ds)} hộ; khi xuất bản đủ mọi hộ)' if len(ds) > XEM_NHIEU_TOI_DA else ''
        self.lb_xem.setText(f'Xem trước bộ hồ sơ {d.ten} ({"dự thảo" if self.che_do() == "du_thao" else "chính thức"}): phương án '
                            f'chi tiết từng hộ + bảng tổng hợp{gioi}. Ô "Nhảy tới hộ" trên thanh xem trước để chuyển nhanh.')
        self.w_preview.yeu_cau(('xb', d.id, tuple(ds), self.che_do()), self.tao_xem_truoc, f'{d.ten} - {len(ds)} hộ')

    # ------------------------------------------------ trang 4: xuất bản
    def _trang_xuat(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        t = QLabel('Tài liệu')
        t.setObjectName('xb_tieu_de')
        v.addWidget(t)
        self.o_ct = QCheckBox('Phương án chi tiết từng hộ (Word)')
        self.o_bth = QCheckBox('Bảng tổng hợp kinh phí (Excel)')
        self.o_tt = QCheckBox('Tờ trình đề nghị thẩm định && phê duyệt (chỉ hồ sơ chính thức)')
        self.o_bc = QCheckBox('Báo cáo tiếp thu && giải trình ý kiến (chỉ hồ sơ chính thức)')
        for o in (self.o_ct, self.o_bth, self.o_tt, self.o_bc):
            o.setChecked(True)
            v.addWidget(o)
        t = QLabel('Đầu ra')
        t.setObjectName('xb_tieu_de')
        v.addWidget(t)
        self.r_gop = QRadioButton('Word / Excel + PDF, gộp phương án chi tiết thành một file PDF (khuyên dùng)')
        self.r_file = QRadioButton('Chỉ file Word / Excel (không cần Microsoft Office)')
        self.r_in = QRadioButton('Gửi cả bộ ra máy in mặc định')
        g = QButtonGroup(w)
        for r in (self.r_gop, self.r_file, self.r_in):
            g.addButton(r)
            v.addWidget(r)
        self.r_gop.setChecked(True)
        h = QHBoxLayout()
        h.addWidget(QLabel('Số bản in mỗi hộ:'))
        self.o_so_ban = QSpinBox()
        self.o_so_ban.setRange(1, 20)
        h.addWidget(self.o_so_ban)
        h.addStretch(1)
        v.addLayout(h)
        h = QHBoxLayout()
        h.addWidget(QLabel('Thư mục lưu:'))
        self.o_thu_muc = QLineEdit()
        h.addWidget(self.o_thu_muc, 1)
        b = QPushButton('Chọn…')
        b.clicked.connect(self._chon_thu_muc)
        h.addWidget(b)
        v.addLayout(h)
        self.o_mo = QCheckBox('Mở thư mục kết quả khi xong')
        self.o_mo.setChecked(True)
        v.addWidget(self.o_mo)
        self.lb_ket_qua = QLabel('')
        self.lb_ket_qua.setWordWrap(True)
        v.addWidget(self.lb_ket_qua)
        self.lb_ket_qua.setVisible(False)
        v.addStretch(1)
        return w

    def _bao(self, chu: str) -> None:
        """Thông báo; im_lang (kiểm thử): hiện ở nhãn kết quả thay hộp thoại (QMessageBox treo bộ test)."""
        if self.im_lang:
            self.lb_ket_qua.setVisible(True)
            dat_trang_thai(self.lb_ket_qua, 'tin', chu)
        else:
            QMessageBox.information(self, TEN_UD, chu)

    def _chon_thu_muc(self):
        p = QFileDialog.getExistingDirectory(self, 'Chọn thư mục lưu hồ sơ', self.o_thu_muc.text())
        if p:
            self.o_thu_muc.setText(p)

    def _ve_xuat(self) -> None:
        chinh = self.che_do() == 'chinh_thuc'
        for o in (self.o_tt, self.o_bc):
            o.setEnabled(chinh)
            o.setChecked(chinh)
        d = self.dot_chon()
        if d is not None:
            self._thu_muc_mac_dinh = str(quan_ly.thu_muc_ho_so(self.con, self.file_du_an) / d.ten_thu_muc)
            self.o_thu_muc.setText(self._thu_muc_mac_dinh)

    def xuat_ban(self, xac_nhan: bool = True):
        """Xuất bản bằng man_hinh.HopIn.thuc_hien (hộp ẩn đặt sẵn đợt / chế độ / tài liệu / đầu ra). Trả kết quả xuat_bo_ho_so."""
        from .man_hinh import HopIn
        d = self.dot_chon()
        ds = self.ds_ho()
        if d is None or not ds:
            self._bao('Chọn một đợt trình đã có hộ.')
            return None
        if self.r_in.isChecked() and xac_nhan and QMessageBox.question(
                self, TEN_UD, f'Gửi bộ hồ sơ {d.ten} ({len(ds)} hộ) tới máy in mặc định của Windows?') != QMessageBox.StandardButton.Yes:
            return None
        hop = HopIn(self.con, self, ma_ho_chon=ds, file_du_an=self.file_du_an, che_do=self.che_do(), dot_id=d.id)
        try:
            hop.o_ct.setChecked(self.o_ct.isChecked())
            hop.o_ct_excel.setChecked(False)
            hop.o_bth.setChecked(self.o_bth.isChecked())
            hop.o_tt.setChecked(self.o_tt.isChecked() and self.o_tt.isEnabled())
            hop.o_bc.setChecked(self.o_bc.isChecked() and self.o_bc.isEnabled())
            (hop.r_in if self.r_in.isChecked() else hop.r_excel if self.r_file.isChecked() else hop.r_pdf).setChecked(True)
            hop.o_gop.setChecked(self.r_gop.isChecked())
            hop.o_so_ban.setValue(self.o_so_ban.value())
            hop.o_chia.setChecked(True)
            hop.o_mo.setChecked(False)
            hop.o_thu_muc.setText(self.o_thu_muc.text().strip() or getattr(self, '_thu_muc_mac_dinh', ''))
            kq = hop.thuc_hien(xac_nhan=False)
        finally:
            hop.done(0)
            hop.deleteLater()
        if kq is None:
            return None
        self.ket_qua = kq
        tep = ([f'{len(kq["word"])} file Word'] if kq.get('word') else []) + ([f'{len(kq["excel"])} file Excel'] if kq.get('excel') else [])
        chu = f'Đã xuất bản {d.ten}: {", ".join(tep) or "0 file"}' + (f', {len(kq["pdf"])} file PDF' if kq.get('pdf') else '') + \
            (f' (gộp: {kq["gop"].name})' if kq.get('gop') else '') + '.'
        if kq.get('loi'):
            chu += ' Lỗi: ' + '; '.join(x.replace('\t\t', ' – ').replace('\t', ' – ') for x in kq['loi'][:5])
        self.lb_ket_qua.setVisible(True)
        dat_trang_thai(self.lb_ket_qua, 'canh_bao' if kq.get('loi') else 'dat', chu)
        if self.o_mo.isChecked() and not self.im_lang:
            from .in_an import mo_file
            mo_file(Path(self.o_thu_muc.text()))
        return kq

    # ------------------------------------------------ chuyển bước
    def sang(self, i: int) -> None:
        i = max(0, min(i, len(BUOC) - 1))
        if i > 0 and self.dot_chon() is None:
            i = 0
        self.ngan.setCurrentIndex(i)
        for k, lb in enumerate(self.nhan_buoc):
            for ten, gt in (('dang', '1' if k == i else ''), ('xong', '1' if k < i else '')):
                if lb.property(ten) != gt:
                    lb.setProperty(ten, gt)
                    lb.style().unpolish(lb)
                    lb.style().polish(lb)
        self.b_lui.setEnabled(i > 0)
        self.b_tiep.setVisible(i < len(BUOC) - 1)
        self.b_tiep.setEnabled(bool(self.ds_dot))
        self.b_xuat.setVisible(i == len(BUOC) - 1)
        if i == 1:
            self._ve_kiem()
        elif i == 2:
            self._xem()
        elif i == 3:
            self._ve_xuat()

    def done(self, r):
        self.w_preview.don_dep()
        super().done(r)


__all__ = ['HopXuatBanDot']

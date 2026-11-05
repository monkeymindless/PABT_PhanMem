"""Cửa sổ "Tính đơn giá đất bồi thường" (NQ 28/2025/NQ-HĐND x QĐ 03/2026/QĐ-UBND) - thay cửa sổ tính giá nội bộ cũ.

Logic ở gia_dat_qd03.py (port calculateStandardLandPrice), van_ban_can_cu.py (13 bậc pháp lý), quet_chung.py (bộ quét dùng chung); file này
chỉ hiển thị. Ba khối: Văn bản căn cứ (tự khử trùng + sắp xếp mỗi khi quét thêm / sửa xong) | Thông số đầu vào (địa bàn, nhóm đất, tuyến đường
& đoạn đường điểm đầu -> điểm cuối từ 106 đoạn, vị trí kết nối cụm 7 dòng NQ 27 / NQ 28, mặt đường, G_NQ28, K2, Phụ lục III, K khác, giá đất
cụ thể chuyển tiếp) và kết quả tức thì | Các dòng đất của hộ đang chọn để áp giá. Áp giá = BoSoan.ap_don_gia_qd03 + luu (khóa hộ nhận việc,
phân quyền, nhật ký, hoàn tác như mọi thao tác lưu phương án)."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import gia_dat_qd03 as g
from . import quet_chung as qc
from . import van_ban_can_cu as vb
from .lap_pa import LoiNhap, doc_so
from .man_hinh_quet_chung import NutQuetChung
from .tien import D, vn

TIEU_DE = 'LARC - Tính đơn giá đất bồi thường'
TOI_DA_HO = 60                                   # số hộ tối đa đưa vào bảng chọn dòng đất một lần (mỗi hộ một lần mở phương án)


class HopTinhGiaDat(QDialog):
    """con: kết nối dự án (None: chỉ tính, không áp). ds_ma_ho: các hộ có dòng đất để áp giá. xa_mac_dinh: tên địa bàn dự án."""
    im_lang = False

    def __init__(self, parent=None, con=None, ds_ma_ho=(), xa_mac_dinh: str = '', chi_doc: bool = False):
        super().__init__(parent)
        self.con, self.chi_doc = con, bool(chi_doc)
        self.setWindowTitle(TIEU_DE)
        self.resize(1040, 760)
        self.kq = None
        self.doan = None
        self._bo = {}                            # ma_ho -> BoSoan đang mở
        self._dong = []                          # (ma_ho, chỉ số dòng đất) theo hàng của bảng
        self.ket_qua_ap = None                   # (số dòng, số hộ) sau khi áp
        lo = QVBoxLayout(self)
        td = QLabel('Bảng tính đơn giá đất bồi thường - chuẩn hóa NQ 28/2025/NQ-HĐND và QĐ 03/2026/QĐ-UBND')
        td.setProperty('vai', 'tieu_de')
        lo.addWidget(td)
        gt = QLabel('Đơn giá = ROUND(G_NQ28 × K1 × K2 × K3 × K_khác). K1 theo ĐOẠN đường (Phụ lục I.1 / I.2), K2 theo quy hoạch (Phụ lục II), '
                    'K3 theo yếu tố ảnh hưởng (Phụ lục III); VB 1201/SNNMT-ĐĐ và VB 29/5/2026 của Sở NN&MT.')
        gt.setWordWrap(True)
        lo.addWidget(gt)

        # ---- 1. văn bản căn cứ
        kc = QGroupBox('Văn bản căn cứ (tự sắp xếp từ Luật, Nghị quyết Quốc hội, Nghị định, Thông tư xuống NQ HĐND, QĐ UBND, văn bản Sở)')
        vk = QVBoxLayout(kc)
        hk = QHBoxLayout()
        self.nut_quet_cc = NutQuetChung('Quét file văn bản căn cứ…', qc.CAN_CU, self)
        self.nut_quet_cc.da_quet.connect(self.sau_khi_quet)
        self.nut_sap = QPushButton('Sắp xếp lại (13 bậc)')
        self.nut_sap.clicked.connect(self.sap_xep_can_cu)
        hk.addWidget(self.nut_quet_cc)
        hk.addWidget(self.nut_sap)
        hk.addStretch(1)
        vk.addLayout(hk)
        self.o_can_cu = QPlainTextEdit()
        self.o_can_cu.setMinimumHeight(70)
        self.o_can_cu.setPlainText(vb.doc_can_cu_du_an(con))
        vk.addWidget(self.o_can_cu)
        lo.addWidget(kc)

        # ---- 2. thông số đầu vào
        self.cb_dia_ban = QComboBox()
        for k in g.ds_dia_ban():
            self.cb_dia_ban.addItem(k, k)
        self.cb_nhom = QComboBox()
        for ma, ten in g.NHOM_DAT:
            self.cb_nhom.addItem(ten, f'{ma}|{g.COT_BANG_GIA[ma]}')
        self.cb_nhom.addItem('Đất rừng sản xuất, nuôi trồng thủy sản - PL I.2', f'DAT_NONG_NGHIEP|{g.COT_NN_RUNG_NTS}')
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm tuyến đường / điểm đầu / điểm cuối (không cần dấu)…')
        self.o_tim.setClearButtonEnabled(True)
        self.cb_doan = QComboBox()
        self.cb_doan.setMaxVisibleItems(18)
        self.cb_vi_tri = QComboBox()
        for ma, _, mo_ta in g.VI_TRI_KET_NOI:
            self.cb_vi_tri.addItem(mo_ta, ma)
        self.cb_ket_cau = QComboBox()
        for ma, ten in g.KET_CAU:
            self.cb_ket_cau.addItem(ten, ma)
        self.o_g = QLineEdit('0')
        self.o_g.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lb_g = QLabel('')
        self.nut_tra = QPushButton('Tra bảng giá NQ 28')
        self.nut_tra.setToolTip('Điền G_NQ28 từ bảng giá đất đang dùng: dòng thứ tự vị trí kết nối trong cụm 7 dòng của đoạn đường đã chọn')
        self.nut_tra.clicked.connect(lambda: self.tra_gia(True))
        self.ck_k2 = QCheckBox('Dự án đầu tư có hệ số sử dụng đất (FAR) - áp dụng Phụ lục II')
        self.o_k2 = QLineEdit('1')
        self.o_k2.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.o_k2.setEnabled(False)
        self.ck_pl3 = {}
        for ma, he, _, mo_ta in g.YEU_TO_PL3:
            c = QCheckBox(mo_ta)
            self.ck_pl3[ma] = c
        self.ck_rieng = QCheckBox('Tuyến đã có hệ số riêng cho đường đất / sỏi / "các tuyến còn lại" ở Phụ lục I.2 (khóa K3 = 1,00)')
        self.o_khac = QLineEdit('1')
        self.o_khac.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.o_cu_the = QLineEdit('')
        self.o_cu_the.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.o_cu_the.setPlaceholderText('Để trống nếu không có (khoản 3 Điều 4 QĐ 03: giữ giá cụ thể nếu ≥ giá tính)')
        self.nut_quet_gd = NutQuetChung('Quét văn bản / bảng giá để lấy dữ liệu…', qc.GIA_DAT, self)
        self.nut_quet_gd.da_quet.connect(self.sau_khi_quet)

        def hang(*w):
            h = QHBoxLayout()
            for x in w:
                h.addWidget(x, 1 if isinstance(x, (QComboBox, QLineEdit)) else 0)
            return h
        tp = QGroupBox('1. Thông số đầu vào và hệ số điều chỉnh')
        f = QFormLayout(tp)
        f.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        f.addRow(self.nut_quet_gd)
        f.addRow('Khu vực / Xã, Phường:', self.cb_dia_ban)
        f.addRow('Nhóm đất (Phụ lục I):', self.cb_nhom)
        f.addRow('Tìm đoạn đường:', self.o_tim)
        f.addRow('Tuyến đường & Đoạn đường (Điểm đầu → Điểm cuối):', self.cb_doan)
        f.addRow('Vị trí kết nối (cụm 7 dòng NQ 27 / NQ 28):', self.cb_vi_tri)
        f.addRow('Kết cấu mặt đường (Phụ lục III):', self.cb_ket_cau)
        f.addRow('Đơn giá bảng giá NQ 28 (đ/m²):', hang(self.o_g, self.nut_tra, self.lb_g))
        f.addRow(self.ck_k2)
        f.addRow('Hệ số K2 (Phụ lục II):', self.o_k2)
        for c in self.ck_pl3.values():
            f.addRow(c)
        f.addRow(self.ck_rieng)
        f.addRow('Hệ số khác (nếu có văn bản cá biệt):', self.o_khac)
        f.addRow('Giá đất cụ thể đã phê duyệt (đ/m²):', self.o_cu_the)
        lo.addWidget(tp)

        # ---- kết quả
        kqg = QGroupBox('Kết quả')
        vq = QVBoxLayout(kqg)
        self.lb_gia = QLabel('')
        self.lb_gia.setProperty('vai', 'tieu_de')
        self.lb_ct = QLabel('')
        self.lb_ct.setWordWrap(True)
        self.lb_canh_bao = QLabel('')
        self.lb_canh_bao.setWordWrap(True)
        self.o_giai_trinh = QPlainTextEdit()
        self.o_giai_trinh.setReadOnly(True)
        self.o_giai_trinh.setMaximumHeight(110)
        self.o_giai_trinh.setPlaceholderText('Nhật ký giải trình từng bước (in vào thuyết minh phương án)')
        for w in (self.lb_gia, self.lb_ct, self.lb_canh_bao, self.o_giai_trinh):
            vq.addWidget(w)
        lo.addWidget(kqg)

        # ---- 3. dòng đất của hộ
        self.lb_ho = QLabel('')
        self.bang = QTableWidget(0, 8)
        self.bang.setHorizontalHeaderLabels(['Chọn', 'Hộ', 'Tờ / Thửa', 'Loại đất', 'Diện tích (m²)', 'Đơn giá hiện tại (đ/m²)',
                                             'Đơn giá mới (đ/m²)', 'Thành tiền mới (đ)'])
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.verticalHeader().setVisible(False)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.setMinimumHeight(130)
        gh = QGroupBox('2. Chọn các dòng đất của hộ để áp giá')
        vh = QVBoxLayout(gh)
        vh.addWidget(self.lb_ho)
        vh.addWidget(self.bang)
        lo.addWidget(gh, 1)

        # ---- hàng nút
        nut = QDialogButtonBox()
        self.nut_ap = QPushButton('Áp đơn giá vào các dòng đã chọn')
        self.nut_ap.clicked.connect(lambda: self.ap_gia())
        nut.addButton(self.nut_ap, QDialogButtonBox.ButtonRole.AcceptRole)
        nut_dong = nut.addButton('Đóng', QDialogButtonBox.ButtonRole.RejectRole)
        nut_dong.clicked.connect(self.reject)
        lo.addWidget(nut)

        # ---- nối tín hiệu
        self.cb_dia_ban.currentIndexChanged.connect(lambda *_: self._nap_doan())
        self.o_tim.textChanged.connect(lambda *_: self._nap_doan(giu=True))
        for cb in (self.cb_doan, self.cb_vi_tri, self.cb_nhom):
            cb.currentIndexChanged.connect(lambda *_: self.tra_gia(False))
        for cb in (self.cb_dia_ban, self.cb_doan, self.cb_nhom, self.cb_vi_tri, self.cb_ket_cau):
            cb.currentIndexChanged.connect(lambda *_: self.tinh())
        for e in (self.o_g, self.o_k2, self.o_khac, self.o_cu_the):
            e.textChanged.connect(lambda *_: self.tinh())
        for c in (self.ck_k2, self.ck_rieng, *self.ck_pl3.values()):
            c.toggled.connect(lambda *_: self.tinh())
        self.ck_k2.toggled.connect(self.o_k2.setEnabled)
        self.cb_nhom.currentIndexChanged.connect(lambda *_: self._dong_bo_yeu_to())
        self.o_can_cu.installEventFilter(self)
        self.bang.itemChanged.connect(lambda *_: self._dat_nut_ap())

        i = g.ds_dia_ban().index(g.dia_ban_theo_ten(xa_mac_dinh)) if g.dia_ban_theo_ten(xa_mac_dinh) else 0
        self.cb_dia_ban.setCurrentIndex(i)
        self._nap_doan()
        self._dong_bo_yeu_to()
        self.nap_dong_dat(list(ds_ma_ho))
        self.tra_gia(False)
        self.tinh()

    # ---------------------------------------------------------------- văn bản căn cứ
    def eventFilter(self, obj, e):
        from PySide6.QtCore import QEvent
        if obj is self.o_can_cu and e.type() == QEvent.Type.FocusOut:
            self.sap_xep_can_cu()
        return False

    def sap_xep_can_cu(self) -> None:
        self.o_can_cu.setPlainText(vb.gop_va_sap_xep([self.o_can_cu.toPlainText()])[0])

    # ---------------------------------------------------------------- chọn đoạn đường / nhóm đất
    def _nap_doan(self, giu: bool = False) -> None:
        ma_cu = self.cb_doan.currentData() if giu else None
        from .lap_pa import bo_dau
        khoa = bo_dau(self.o_tim.text()).split()
        ds = [r for r in g.ds_doan(self.cb_dia_ban.currentData() or '')
              if all(k in bo_dau(f'{r["ten_duong"]} {r["diem_dau"]} {r["diem_cuoi"]}') for k in khoa)]
        self.cb_doan.blockSignals(True)
        self.cb_doan.clear()
        for r in ds:
            self.cb_doan.addItem(g.nhan_doan(r), r['ma_doan_duong'])
        k = self.cb_doan.findData(ma_cu) if ma_cu else 0
        self.cb_doan.setCurrentIndex(max(0, k))
        self.cb_doan.blockSignals(False)
        self.tra_gia(False)
        self.tinh()

    def _dong_bo_yeu_to(self) -> None:
        """Yếu tố Phụ lục III chỉ chọn được đúng nhóm đất (Mục I: phi nông nghiệp; Mục II.1: nông nghiệp)."""
        la_nn = self.nhom_cot()[0] == 'DAT_NONG_NGHIEP'
        for ma, _, nhom, _ in g.YEU_TO_PL3:
            c = self.ck_pl3[ma]
            dung = (nhom == 'nn') == la_nn
            c.setEnabled(dung)
            if not dung:
                c.setChecked(False)

    def nhom_cot(self) -> tuple:
        """(nhóm đất QĐ 03, cột bảng giá NQ 28) của mục đang chọn - dữ liệu mục là chuỗi 'nhóm|cột' (tuple không qua được QVariant của Qt5)."""
        return tuple((self.cb_nhom.currentData() or 'DAT_NONG_NGHIEP|nn_cay').split('|'))

    def doan_hien_tai(self):
        return g.tim_doan(self.cb_dia_ban.currentData() or '', self.cb_doan.currentData() or '')

    def tra_gia(self, thong_bao: bool = False) -> None:
        """Điền G_NQ28 từ bảng giá đất đang dùng; không có dòng khớp thì giữ số người dùng nhập."""
        nhom, cot = self.nhom_cot()
        gia = g.gia_bang_gia(self.cb_dia_ban.currentData() or '', self.doan_hien_tai(), nhom, self.cb_vi_tri.currentData() or '', cot)
        if gia is not None:
            self.o_g.setText(vn(gia).replace('.', ''))
            self.lb_g.setText('(tự tra bảng giá NQ 28)')
        else:
            self.lb_g.setText('(nhập tay - bảng giá không có dòng khớp)')
            if thong_bao and not self.im_lang:
                QMessageBox.information(self, TIEU_DE, 'Bảng giá đất đang dùng không có dòng khớp đoạn đường / vị trí này: nhập đơn giá bằng tay.')

    # ---------------------------------------------------------------- tính
    def dau_vao(self) -> g.DauVao:
        nhom, _ = self.nhom_cot()
        cu_the = self.o_cu_the.text().strip()
        return g.DauVao(
            dia_ban=self.cb_dia_ban.currentData() or '', nhom_dat=nhom, ma_doan_duong=self.cb_doan.currentData() or '',
            loai_ket_noi_vi_tri=self.cb_vi_tri.currentData() or 'MAT_TIEN_VT1', ket_cau_mat_duong=self.cb_ket_cau.currentData() or 'NHUA_BETONG',
            don_gia_bang_gia=doc_so(self.o_g.text(), 'Đơn giá bảng giá NQ 28'),
            ap_dung_quy_hoach_pl2=self.ck_k2.isChecked(), he_so_quy_hoach_k2=doc_so(self.o_k2.text(), 'Hệ số K2') or D(1),
            yeu_to_pl3=[m for m, c in self.ck_pl3.items() if c.isChecked() and c.isEnabled()],
            he_so_khac=doc_so(self.o_khac.text(), 'Hệ số khác') or D(1),
            gia_dat_cu_the=doc_so(cu_the, 'Giá đất cụ thể') if cu_the else D(0),
            co_quy_dinh_rieng_duong_dat_pl1=self.ck_rieng.isChecked())

    def tinh(self):
        try:
            v = self.dau_vao()
        except LoiNhap as e:
            self.kq = None
            self.lb_gia.setText('Chưa tính được')
            self.lb_ct.setText(str(e))
            self.nut_ap.setEnabled(False)
            return None
        self.doan = self.doan_hien_tai()
        self.kq = g.tinh_don_gia(v, self.doan)
        k = self.kq
        self.lb_gia.setText(f'ĐƠN GIÁ ĐẤT BỒI THƯỜNG (đã làm tròn): {vn(k.don_gia_ap_dung)} đ/m²')
        self.lb_gia.setToolTip('\n'.join(k.buoc_lap_luan))
        self.lb_ct.setText('Công thức: ' + k.cong_thuc)
        self.lb_canh_bao.setText('\n'.join('! ' + c for c in k.canh_bao))
        self.o_giai_trinh.setPlainText('\n'.join(k.buoc_lap_luan))
        self._ve_gia_moi()
        self._dat_nut_ap()
        return k

    # ---------------------------------------------------------------- quét
    def sau_khi_quet(self, kq: qc.KetQuaQuet) -> None:
        """Kết quả quét: văn bản căn cứ gộp + sắp 13 bậc; thông số (địa bàn, mặt đường, yếu tố Phụ lục III) điền vào ô."""
        if kq.can_cu:
            self.o_can_cu.setPlainText(vb.gop_va_sap_xep([self.o_can_cu.toPlainText()], kq.can_cu)[0])
        ts = kq.tham_so or {}
        if ts.get('dia_ban') in g.ds_dia_ban():
            self.cb_dia_ban.setCurrentIndex(self.cb_dia_ban.findData(ts['dia_ban']))
        if ts.get('ket_cau_mat_duong'):
            self.cb_ket_cau.setCurrentIndex(max(0, self.cb_ket_cau.findData(ts['ket_cau_mat_duong'])))
        for m in ts.get('yeu_to_pl3', ()):
            if m in self.ck_pl3 and self.ck_pl3[m].isEnabled():
                self.ck_pl3[m].setChecked(True)
        self.tinh()

    # ---------------------------------------------------------------- dòng đất của hộ
    def nap_dong_dat(self, ds_ma_ho: list) -> None:
        from .lap_pa import BoSoan
        self.bang.setRowCount(0)
        self._dong, self._bo = [], {}
        if self.con is None or not ds_ma_ho:
            self.lb_ho.setText('Chưa chọn hộ: bảng chỉ để tính. Chọn hộ ở danh sách hộ rồi mở lại để áp đơn giá vào dòng đất.')
            return
        bo_qua = max(0, len(ds_ma_ho) - TOI_DA_HO)
        for ma in ds_ma_ho[:TOI_DA_HO]:
            try:
                bs = BoSoan(self.con, ma)
            except Exception:                                           # noqa: BLE001 - hộ lỗi dữ liệu: bỏ qua, không dừng cả cửa sổ
                continue
            self._bo[ma] = bs
            for i, d in enumerate(bs.pa.dat):
                self._dong.append((ma, i))
        self.bang.setRowCount(len(self._dong))
        for r, (ma, i) in enumerate(self._dong):
            bs = self._bo[ma]
            d = bs.pa.dat[i]
            o = QTableWidgetItem()
            o.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            o.setCheckState(Qt.CheckState.Checked)
            self.bang.setItem(r, 0, o)
            ten = bs.pa.ho.ho_ten or ''
            for c, v in ((1, f'{ma} - {ten}'.strip(' -')), (2, bs.ten_thua(d.ma_thua)), (3, d.loai_dat), (4, vn(d.dien_tich, 1)),
                         (5, vn(d.gia_bang_gia * d.he_so_k))):
                self.bang.setItem(r, c, QTableWidgetItem(v))
        self.bang.resizeColumnsToContents()
        self.lb_ho.setText(f'{len(self._bo)} hộ, {len(self._dong)} dòng đất.' + (f' (Chỉ hiện {TOI_DA_HO} hộ đầu; còn {bo_qua} hộ chưa đưa vào.)'
                                                                                 if bo_qua else ''))
        self._ve_gia_moi()
        self._dat_nut_ap()

    def _ve_gia_moi(self) -> None:
        if self.kq is None:
            return
        gia = self.kq.don_gia_ap_dung
        self.bang.blockSignals(True)
        for r, (ma, i) in enumerate(self._dong):
            d = self._bo[ma].pa.dat[i]
            self.bang.setItem(r, 6, QTableWidgetItem(vn(gia)))
            self.bang.setItem(r, 7, QTableWidgetItem(vn(D(d.dien_tich) * gia)))
        self.bang.blockSignals(False)

    def dong_da_chon(self) -> list:
        return [self._dong[r] for r in range(self.bang.rowCount())
                if self.bang.item(r, 0) is not None and self.bang.item(r, 0).checkState() == Qt.CheckState.Checked]

    def _dat_nut_ap(self) -> None:
        ok = self.kq is not None and self.con is not None and not self.chi_doc and bool(self.dong_da_chon()) and self.kq.don_gia_ap_dung > 0
        self.nut_ap.setEnabled(ok)
        self.nut_ap.setToolTip('' if ok else 'Cần: mở dự án (không ở chế độ chỉ xem), chọn hộ có dòng đất, tích dòng cần áp và đơn giá lớn hơn 0.')

    def ap_gia(self, xac_nhan: bool | None = None) -> tuple:
        """Áp đơn giá vào các dòng đã tích: mỗi hộ một lần lưu phương án. Trả (số dòng, số hộ, danh sách lỗi). xac_nhan=True: không hỏi."""
        if self.kq is None or self.con is None:
            return 0, 0, []
        chon = self.dong_da_chon()
        if not chon:
            return 0, 0, []
        if xac_nhan is None and not self.im_lang:
            if QMessageBox.question(self, TIEU_DE, f'Áp đơn giá {vn(self.kq.don_gia_ap_dung)} đ/m² vào {len(chon)} dòng đất?') != \
                    QMessageBox.StandardButton.Yes:
                return 0, 0, []
        gc = g.ghi_chu_ap_gia(self.kq, self.doan, g.ten_ngan(self.cb_dia_ban.currentData() or ''))
        theo_ho = {}
        for ma, i in chon:
            theo_ho.setdefault(ma, []).append(i)
        so_dong, so_ho, loi = 0, 0, []
        for ma, chi_so in theo_ho.items():
            bs = self._bo[ma]
            try:
                n = bs.ap_don_gia_qd03(chi_so, self.kq.don_gia_ap_dung, gc)
                bs.luu()
            except LoiNhap as e:
                loi.append(f'Hộ {ma}: {e}')
                continue
            so_dong += n
            so_ho += 1
        try:
            vb.ghi_can_cu_du_an(self.con, self.o_can_cu.toPlainText())
        except Exception:                                                # noqa: BLE001 - lưu căn cứ không được thì không làm hỏng việc áp giá
            pass
        self.ket_qua_ap = (so_dong, so_ho)
        if not self.im_lang:
            if loi:
                QMessageBox.warning(self, TIEU_DE, f'Đã áp {so_dong} dòng ({so_ho} hộ). Không áp được:\n' + '\n'.join(loi[:10]))
            else:
                QMessageBox.information(self, TIEU_DE, f'Đã áp đơn giá {vn(self.kq.don_gia_ap_dung)} đ/m² cho {so_dong} dòng đất của {so_ho} hộ.')
        self.accept()
        return so_dong, so_ho, loi

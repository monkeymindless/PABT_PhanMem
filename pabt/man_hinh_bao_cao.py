"""Báo cáo tiến độ GPMB (Nhóm 6, Bước 16 Mục IV QĐ 18/2026/QĐ-UBND): bảng điều hành trực quan.

Bốn thẻ chỉ số - tỷ lệ giải ngân tiền bồi thường, tỷ lệ diện tích mặt bằng sạch đã bàn giao, số thửa chưa bàn giao mặt bằng (còn vướng mắc), số hộ
đủ điều kiện cưỡng chế - và danh sách thửa còn vướng cần giải tỏa gấp (xếp Gấp / Cao / Theo dõi). Số liệu ở bao_cao_gpmb.py;
trang chỉ vẽ. Dùng chung khung _Khung của man_hinh_theo_doi (im_lang, xuất Excel, hộ đang chọn).
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout

from . import bao_cao_gpmb, thoi_han, van_dong
from .bang_ao import BangAo
from .giao_dien import XepDong, dat_trang_thai
from .man_hinh_theo_doi import DO, VANG, XAM, _chu, _Khung, _nut
from .tien import so_vn, vn

_QSS_THE = '''
QFrame#the_kpi { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }
QLabel#kpi_tieu_de { color: #64748B; font-size: 12px; font-weight: 600; background: transparent; }
QLabel#kpi_so { color: #0F3866; font-size: 28px; font-weight: 700; background: transparent; }
QLabel#kpi_phu { color: #475569; font-size: 12px; background: transparent; }
QProgressBar { background: #E2E8F0; border: 0; border-radius: 5px; }
'''
MAU_THE = dict(giai_ngan='#107C41', mat_bang='#2563EB', con_vuong='#D97706', cuong_che='#DC2626')   # màu thanh / chữ từng thẻ
NEN_MUC = {'gap': DO, 'cao': VANG, 'theo_doi': XAM}


class _TheKPI(QFrame):
    """Một thẻ chỉ số: tiêu đề nhỏ, số lớn, thanh tiến độ (nếu có tỷ lệ), dòng chú thích."""

    def __init__(self, tieu_de: str, mau: str, parent=None):
        super().__init__(parent)
        self.setObjectName('the_kpi')
        self.setStyleSheet(_QSS_THE)
        self.mau = mau
        self.lb_td = QLabel(tieu_de)
        self.lb_td.setObjectName('kpi_tieu_de')
        self.lb_so = QLabel('–')
        self.lb_so.setObjectName('kpi_so')
        self.thanh = QProgressBar()
        self.thanh.setRange(0, 1000)
        self.thanh.setTextVisible(False)
        self.thanh.setFixedHeight(10)
        self.lb_phu = QLabel('')
        self.lb_phu.setObjectName('kpi_phu')
        self.lb_phu.setWordWrap(True)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(14, 10, 14, 10)
        lo.setSpacing(4)
        for w in (self.lb_td, self.lb_so, self.thanh, self.lb_phu):
            lo.addWidget(w)
        lo.addStretch(1)                                    # nội dung canh trên: bốn thẻ cùng cao, tiêu đề / số thẳng hàng
        self.setMinimumWidth(190)

    def dat(self, so: str, ty_le: float | None, phu: str) -> None:
        self.lb_so.setText(so)
        self.lb_phu.setText(phu)
        self.thanh.setVisible(ty_le is not None)
        if ty_le is not None:
            self.thanh.setValue(int(min(100.0, max(0.0, ty_le)) * 10))
            self.thanh.setStyleSheet(f'QProgressBar::chunk {{ background: {self.mau}; border-radius: 5px; }}')


class KhungBaoCaoTienDo(_Khung):
    """Bảng điều hành tiến độ giải phóng mặt bằng."""
    COT = ['Ưu tiên', 'Mã hộ', 'Họ và tên', 'Tờ', 'Thửa', 'DT thu hồi\n(m²)', 'Loại đất', 'Lý do còn vướng',
           'Vận động / cưỡng chế', 'Cùng tờ bản đồ', 'Mốc thu hồi đất']
    mo_theo_doi = Signal()                  # nút "Mở Theo dõi chi trả…": cửa sổ chính chuyển sang trang Theo dõi chi trả & Bàn giao
    xuat_tong_hop = Signal()                # nút "Xuất danh sách đầy đủ các hộ…": cửa sổ chính xuất báo cáo tổng hợp (Excel)

    def __init__(self, con=None, parent=None, chi_doc: bool = False):
        super().__init__(con, parent, chi_doc)
        self.tq = None
        self._can_nap = False
        self.nut = {}
        self.the = dict(giai_ngan=_TheKPI('GIẢI NGÂN TIỀN BỒI THƯỜNG', MAU_THE['giai_ngan'], self),
                        mat_bang=_TheKPI('MẶT BẰNG SẠCH ĐÃ BÀN GIAO', MAU_THE['mat_bang'], self),
                        con_vuong=_TheKPI('THỬA CHƯA BÀN GIAO MẶT BẰNG', MAU_THE['con_vuong'], self),
                        cuong_che=_TheKPI('HỘ ĐỦ ĐIỀU KIỆN CƯỠNG CHẾ', MAU_THE['cuong_che'], self))
        h_the = QHBoxLayout()
        for t in self.the.values():
            h_the.addWidget(t, 1)
        self.lb_tt = QLabel('')
        self.lb_tt.setWordWrap(True)
        self.cb_muc = QComboBox()
        self.cb_muc.addItem('Tất cả mức ưu tiên', '')
        for k in bao_cao_gpmb.MUC:
            self.cb_muc.addItem(bao_cao_gpmb.TEN_MUC[k], k)
        self.cb_muc.currentIndexChanged.connect(lambda *_: self.ve())
        self.lb_dem = QLabel('')
        self.bang = BangAo(self.COT, can_phai=(1, 5), tu_cao=True)
        for c, w in enumerate((80, 60, 190, 50, 60, 90, 90, 340, 300, 170, 330)):
            self.bang.setColumnWidth(c, w)
        self.bang.cellDoubleClicked.connect(self._mo_ho_dong)
        td = QLabel('THỬA CHƯA BÀN GIAO MẶT BẰNG - CẦN GIẢI TỎA GẤP')
        td.setProperty('vai', 'tieu_de')
        h_loc = QHBoxLayout()
        h_loc.addWidget(td)
        h_loc.addStretch(1)
        h_loc.addWidget(self.cb_muc)
        h_loc.addWidget(self.lb_dem)
        h_nut = XepDong(cach=6)
        _nut([('Xuất báo cáo tiến độ…', lambda: self.xuat()), ('Xuất DS đề nghị cưỡng chế…', lambda: self.xuat_cuong_che()),
              ('Xuất danh sách đầy đủ các hộ…', lambda: self.xuat_tong_hop.emit()),
              ('Mở theo dõi chi trả, bàn giao…', lambda: self.mo_theo_doi.emit())], h_nut, self.nut)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addLayout(h_the)
        lo.addWidget(self.lb_tt)
        lo.addLayout(h_loc)
        lo.addWidget(self.bang, 1)
        lo.addLayout(h_nut)

    def nap(self):
        """Tính lại số liệu; trang đang ẩn thì chỉ đánh dấu, nạp khi hiện (showEvent) - lưu một hộ không phải tính lại cả dự án."""
        if not self.isVisible() and not self.im_lang:
            self._can_nap = True
            return
        self._can_nap = False
        self.tq = bao_cao_gpmb.tong_quan(self.con) if self.con is not None else None
        self.ve()

    def showEvent(self, e):
        super().showEvent(e)
        if self._can_nap:
            self.nap()

    def thua_hien(self) -> list:
        muc = self.cb_muc.currentData() or ''
        return [r for r in (self.tq['thua'] if self.tq else []) if not muc or r['muc'] == muc]

    def ve(self):
        tq = self.tq
        for t in self.the.values():
            t.dat('–', None, '')
        if tq is None:
            self.bang.dat_du_lieu([])
            self.lb_tt.setText('')
            self.lb_dem.setText('')
            return
        self.the['giai_ngan'].dat(f'{tq["pt_giai_ngan"]:.1f}%'.replace('.', ','), tq['pt_giai_ngan'],
                                  f'{vn(tq["da_chi"])} / {vn(tq["tong_pd"])} đ đã phê duyệt · còn {vn(tq["con_lai"])} đ · '
                                  f'{tq["so_ho_nhan_du"]}/{tq["so_ho_phe_duyet"]} hộ đã nhận đủ tiền')
        self.the['mat_bang'].dat(f'{tq["pt_mat_bang"]:.1f}%'.replace('.', ','), tq['pt_mat_bang'],
                                 f'{so_vn(tq["dt_ban_giao"])} / {so_vn(tq["dt_tong"])} m² · {tq["so_ho_ban_giao"]}/{tq["so_ho"]} '
                                 'hộ đã bàn giao')
        d = tq['dem']
        self.the['con_vuong'].dat(str(len(tq['thua'])), None, f'Gấp {d["gap"]} · Cao {d["cao"]} · Theo dõi {d["theo_doi"]}')
        self.the['cuong_che'].dat(str(tq['so_ho_cuong_che']), None,
                                  f'Vận động quá {thoi_han.so_ngay(self.con, "van_dong")} ngày chưa thành - {van_dong.CAN_CU_CUONG_CHE}')
        dat_trang_thai(self.lb_tt, 'canh_bao' if d['gap'] or tq['so_ho_cuong_che'] else 'tin',
                       f'Số liệu tính đến {thoi_han.hien_ngay(tq["hom_nay"])}: {tq["so_ho"]} hộ · đã phê duyệt '
                       f'{tq["so_ho_phe_duyet"]} · chưa phê duyệt {tq["so_ho_chua_pd"]} (chưa tính vào danh sách thửa còn vướng).')
        ds = self.thua_hien()
        kieu = {}
        for r, x in enumerate(ds):
            kieu[(r, 0)] = dict(nen=NEN_MUC[x['muc']], dam=x['muc'] == 'gap')
            if x['ma_van_dong'] == 'du_dk_cuong_che':
                kieu[(r, 8)] = dict(nen=DO, dam=True)
        self.bang.dat_du_lieu([_chu([bao_cao_gpmb.TEN_MUC[x['muc']], x['ma_ho'], x['ho_ten'], x['so_to'], x['so_thua'], x['dt'],
                                     x['loai_dat'], x['ly_do'], x['van_dong'], x['cung_to'], x['moc_thu_hoi']], so=(5,))
                               for x in ds], [x['ma_ho'] for x in ds], kieu)
        self.lb_dem.setText(f'{len(ds)}/{len(tq["thua"])} thửa')

    def xuat(self, file=None):
        if self.con is None:
            return None
        return self._xuat(file, 'Lưu báo cáo tiến độ GPMB', 'BaoCaoTienDoGPMB.xlsx', lambda f: bao_cao_gpmb.xuat_excel(self.con, f))

    def xuat_cuong_che(self, file=None):
        """Danh sách đề nghị ban hành quyết định cưỡng chế thu hồi đất (hộ đủ điều kiện theo Điều 89) - cùng danh sách ở Theo dõi."""
        if self.con is None:
            return None
        if not van_dong.ds_cuong_che(self.con):
            self.bao('Chưa có hộ nào đủ điều kiện cưỡng chế (cần vận động quá '
                     f'{thoi_han.so_ngay(self.con, "van_dong")} ngày mà hộ vẫn chưa nhận tiền / chưa bàn giao mặt bằng).', loi=False)
            return None
        return self._xuat(file, 'Lưu danh sách đề nghị cưỡng chế', 'DS_DeNghi_CuongChe.xlsx',
                          lambda f: van_dong.xuat_ds_cuong_che(self.con, f))

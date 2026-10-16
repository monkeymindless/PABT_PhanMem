"""Tiến độ chi trả & Bàn giao - phần TỔNG QUAN (Bước 16 Mục IV QĐ 18/2026/QĐ-UBND).

1.0.00 (người dùng 16/10/2026, Hội đồng chuyên gia UI/UX - nghiệp vụ GPMB - kiến trúc - QA): trang "Báo cáo tiến độ GPMB" GỘP vào
trang "Theo dõi chi trả & Bàn giao" (hai trang trùng ~70% dữ liệu - mốc thu hồi, vận động / cưỡng chế, lý do còn vướng - và 3 nút
trùng lệnh). Module này còn hai thành phần, dùng trong man_hinh_theo_doi.KhungTienDo:
  DaiKPI         4 thẻ chỉ số gọn: giải ngân, mặt bằng sạch, thửa chưa bàn giao, hộ đủ điều kiện cưỡng chế. Bấm thẻ = lọc bảng
                 (tín hiệu bam(khóa)). Chưa có quyết định phê duyệt: "—" kèm lời nhắc (không hiện "0,0%" gây hiểu nhầm).
  BangThuaVuong  chế độ xem "Thửa còn vướng": thửa của hộ ĐÃ có quyết định mà chưa bàn giao, xếp Gấp / Cao / Theo dõi; bảng trống
                 thì nói rõ vì sao.
Số liệu ở bao_cao_gpmb.py (không Qt); module này chỉ vẽ.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QProgressBar, QStackedWidget, QVBoxLayout, QWidget

from . import bao_cao_gpmb, van_dong
from .bang_ao import BangAo
from .giao_dien import NhanRutGon
from .man_hinh_theo_doi import DO, VANG, XAM, _chu
from .tien import so_vn, vn

_QSS_THE = '''
QFrame#the_kpi { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }
QFrame#the_kpi:hover { border-color: #93C5FD; background: #F8FAFC; }
QLabel#kpi_tieu_de { color: #64748B; font-size: 11px; font-weight: 600; background: transparent; }
QLabel#kpi_so { color: #0F3866; font-size: 20px; font-weight: 700; background: transparent; }
QLabel#kpi_phu { color: #475569; font-size: 11px; background: transparent; }
QProgressBar { background: #E2E8F0; border: 0; border-radius: 2px; }
'''
MAU_THE = dict(giai_ngan='#107C41', mat_bang='#2563EB', con_vuong='#D97706', cuong_che='#DC2626')   # màu thanh / chữ từng thẻ
NEN_MUC = {'gap': DO, 'cao': VANG, 'theo_doi': XAM}
TIEU_DE_THE = dict(giai_ngan='GIẢI NGÂN TIỀN BỒI THƯỜNG', mat_bang='MẶT BẰNG SẠCH ĐÃ BÀN GIAO',
                   con_vuong='THỬA CHƯA BÀN GIAO MẶT BẰNG', cuong_che='HỘ ĐỦ ĐIỀU KIỆN CƯỠNG CHẾ')
# bấm thẻ làm gì (chú thích) - KhungTienDo.bam_kpi làm đúng việc này
GOI_Y_THE = dict(giai_ngan='Bấm để lọc các hộ còn quyết định chưa nhận tiền',
                 mat_bang='Bấm để lọc các hộ chưa bàn giao mặt bằng',
                 con_vuong='Bấm để xem danh sách thửa còn vướng (xếp Gấp / Cao / Theo dõi)',
                 cuong_che='Bấm để lọc các hộ đủ điều kiện cưỡng chế thu hồi đất')
KHONG_SO = '—'                          # chưa có cơ sở để tính tỷ lệ (chưa có quyết định / chưa có diện tích)


class _TheKPI(QFrame):
    """Một thẻ chỉ số gọn (~64 px): tiêu đề nhỏ, số lớn + dòng chú thích một dòng (rút gọn "…", đủ chữ ở chú thích khi rê chuột),
    thanh tiến độ mảnh khi có tỷ lệ. Bấm cả thẻ -> bam."""
    bam = Signal()

    def __init__(self, tieu_de: str, mau: str, goi_y: str = '', parent=None):
        super().__init__(parent)
        self.setObjectName('the_kpi')
        self.setStyleSheet(_QSS_THE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.goi_y = goi_y
        self.mau = mau
        self.lb_td = QLabel(tieu_de)
        self.lb_td.setObjectName('kpi_tieu_de')
        self.lb_so = QLabel('–')
        self.lb_so.setObjectName('kpi_so')
        self.lb_phu = NhanRutGon('')
        self.lb_phu.setObjectName('kpi_phu')
        self.thanh = QProgressBar()
        self.thanh.setRange(0, 1000)
        self.thanh.setTextVisible(False)
        self.thanh.setFixedHeight(4)
        h = QHBoxLayout()
        h.setSpacing(8)
        h.addWidget(self.lb_so)
        h.addWidget(self.lb_phu, 1, Qt.AlignmentFlag.AlignVCenter)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(10, 6, 10, 6)
        lo.setSpacing(2)
        lo.addWidget(self.lb_td)
        lo.addLayout(h)
        lo.addWidget(self.thanh)
        self.setMinimumWidth(170)
        self.setToolTip(goi_y)

    def dat(self, so: str, ty_le: float | None, phu: str, chu_thich: str = '') -> None:
        self.lb_so.setText(so)
        self.lb_phu.setText(phu)
        self.setToolTip('\n'.join(x for x in (chu_thich or phu, self.goi_y) if x))
        self.thanh.setVisible(ty_le is not None)
        if ty_le is not None:
            self.thanh.setValue(int(min(100.0, max(0.0, ty_le)) * 10))
            self.thanh.setStyleSheet(f'QProgressBar::chunk {{ background: {self.mau}; border-radius: 2px; }}')

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()
                                                                              if hasattr(e, 'position') else e.pos()):
            self.bam.emit()


class DaiKPI(QWidget):
    """Dải 4 thẻ chỉ số của trang Tiến độ chi trả & Bàn giao. bam(khóa thẻ): giai_ngan / mat_bang / con_vuong / cuong_che."""
    bam = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.the = {}
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        for k, td in TIEU_DE_THE.items():
            t = _TheKPI(td, MAU_THE[k], GOI_Y_THE[k], self)
            t.bam.connect(lambda k=k: self.bam.emit(k))
            self.the[k] = t
            h.addWidget(t, 1)

    def dat(self, tq: dict | None, so_ngay_van_dong: int = 0) -> None:
        if tq is None:
            for t in self.the.values():
                t.dat('–', None, '')
            return
        if tq['tong_pd']:
            self.the['giai_ngan'].dat(f'{tq["pt_giai_ngan"]:.1f}%'.replace('.', ','), tq['pt_giai_ngan'],
                                      f'{tq["so_ho_nhan_du"]}/{tq["so_ho_phe_duyet"]} hộ nhận đủ · còn {vn(tq["con_lai"])} đ',
                                      f'Đã chi {vn(tq["da_chi"])} / {vn(tq["tong_pd"])} đ đã phê duyệt · còn {vn(tq["con_lai"])} đ · '
                                      f'{tq["so_ho_nhan_du"]}/{tq["so_ho_phe_duyet"]} hộ đã nhận đủ tiền')
        else:
            self.the['giai_ngan'].dat(KHONG_SO, None, 'Chưa có quyết định phê duyệt',
                                      'Chưa có quyết định phê duyệt nào: chưa có số tiền để tính tỷ lệ giải ngân.')
        if tq['dt_tong']:
            self.the['mat_bang'].dat(f'{tq["pt_mat_bang"]:.1f}%'.replace('.', ','), tq['pt_mat_bang'],
                                     f'{tq["so_ho_ban_giao"]}/{tq["so_ho"]} hộ · {so_vn(tq["dt_ban_giao"])} m²',
                                     f'{so_vn(tq["dt_ban_giao"])} / {so_vn(tq["dt_tong"])} m² thu hồi đã bàn giao · '
                                     f'{tq["so_ho_ban_giao"]}/{tq["so_ho"]} hộ đã bàn giao')
        else:
            self.the['mat_bang'].dat(KHONG_SO, None, 'Chưa có diện tích thu hồi', 'Các thửa chưa có diện tích thu hồi.')
        d = tq['dem']
        if tq['so_ho_phe_duyet']:
            self.the['con_vuong'].dat(str(len(tq['thua'])), None, f'Gấp {d["gap"]} · Cao {d["cao"]} · Theo dõi {d["theo_doi"]}')
        else:
            self.the['con_vuong'].dat(KHONG_SO, None, 'Chưa có hộ được phê duyệt',
                                      'Chỉ tính thửa của hộ ĐÃ có quyết định phê duyệt mà chưa bàn giao mặt bằng.')
        self.the['cuong_che'].dat(str(tq['so_ho_cuong_che']), None, f'Vận động quá {so_ngay_van_dong} ngày chưa thành',
                                  f'Vận động quá {so_ngay_van_dong} ngày mà hộ vẫn chưa nhận tiền / chưa bàn giao - '
                                  f'{van_dong.CAN_CU_CUONG_CHE}')


class BangThuaVuong(QWidget):
    """Chế độ xem "Thửa còn vướng": mức ưu tiên + bảng thửa (BangAo); bảng trống thì nhãn giải thích thay chỗ bảng."""
    COT = ['Ưu tiên', 'Mã hộ', 'Họ và tên', 'Tờ', 'Thửa', 'DT thu hồi\n(m²)', 'Loại đất', 'Lý do còn vướng',
           'Vận động / cưỡng chế', 'Cùng tờ bản đồ', 'Mốc thu hồi đất']
    mo_ho = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tq = None
        self.cb_muc = QComboBox()
        self.cb_muc.addItem('Tất cả mức ưu tiên', '')
        for k in bao_cao_gpmb.MUC:
            self.cb_muc.addItem(bao_cao_gpmb.TEN_MUC[k], k)
        self.cb_muc.setToolTip('Gấp: đủ điều kiện cưỡng chế, hoặc đã nhận đủ tiền mà chưa bàn giao và cùng tờ bản đồ với thửa đã giải '
                               'tỏa.\nCao: đã nhận đủ tiền chưa bàn giao, hoặc đang vận động.\nTheo dõi: đã phê duyệt, chưa nhận tiền.')
        self.cb_muc.currentIndexChanged.connect(lambda *_: self.ve())
        self.lb_dem = QLabel('')
        self.bang = BangAo(self.COT, can_phai=(1, 5), tu_cao=True)
        for c, w in enumerate((80, 60, 190, 50, 60, 90, 90, 340, 300, 170, 330)):
            self.bang.setColumnWidth(c, w)
        self.bang.cellDoubleClicked.connect(self._mo_ho_dong)
        self.lb_trong = QLabel('')
        self.lb_trong.setWordWrap(True)
        self.lb_trong.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb_trong.setStyleSheet('QLabel { color: #64748B; font-size: 13px; background: #FFFFFF; border: 1px solid #E2E8F0; '
                                    'border-radius: 6px; padding: 24px; }')
        self.ngan = QStackedWidget()
        self.ngan.addWidget(self.bang)
        self.ngan.addWidget(self.lb_trong)
        h = QHBoxLayout()
        h.addWidget(QLabel('Mức ưu tiên:'))
        h.addWidget(self.cb_muc)
        h.addWidget(self.lb_dem)
        h.addStretch(1)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addLayout(h)
        lo.addWidget(self.ngan, 1)

    def dat(self, tq: dict | None) -> None:
        self.tq = tq
        self.ve()

    def thua_hien(self) -> list:
        muc = self.cb_muc.currentData() or ''
        return [r for r in (self.tq['thua'] if self.tq else []) if not muc or r['muc'] == muc]

    def ve(self):
        tq = self.tq
        ds = self.thua_hien()
        kieu = {}
        for r, x in enumerate(ds):
            kieu[(r, 0)] = dict(nen=NEN_MUC[x['muc']], dam=x['muc'] == 'gap')
            if x['ma_van_dong'] == 'du_dk_cuong_che':
                kieu[(r, 8)] = dict(nen=DO, dam=True)
        self.bang.dat_du_lieu([_chu([bao_cao_gpmb.TEN_MUC[x['muc']], x['ma_ho'], x['ho_ten'], x['so_to'], x['so_thua'], x['dt'],
                                     x['loai_dat'], x['ly_do'], x['van_dong'], x['cung_to'], x['moc_thu_hoi']], so=(5,))
                               for x in ds], [x['ma_ho'] for x in ds], kieu)
        tong = len(tq['thua']) if tq else 0
        self.lb_dem.setText(f'{len(ds)}/{tong} thửa' if tq else '')
        self.lb_trong.setText(self.chu_trong())
        self.ngan.setCurrentWidget(self.bang if ds else self.lb_trong)

    def chu_trong(self) -> str:
        """Vì sao bảng trống (thay cho một bảng trắng không lời giải thích)."""
        tq = self.tq
        if tq is None:
            return 'Chưa mở dự án.'
        if not tq['so_ho_phe_duyet']:
            return (f'Chưa có hộ nào được phê duyệt ({tq["so_ho_chua_pd"]} hộ chưa có quyết định).\n'
                    'Danh sách thửa còn vướng chỉ tính thửa của hộ ĐÃ có quyết định phê duyệt mà chưa bàn giao mặt bằng - thêm '
                    'quyết định ở mục "Quyết định phê duyệt".')
        if not tq['thua']:
            return (f'Không còn thửa vướng: {tq["so_ho_phe_duyet"]} hộ đã phê duyệt đều đã bàn giao mặt bằng'
                    + (f' ({tq["so_ho_chua_pd"]} hộ chưa có quyết định chưa tính).' if tq['so_ho_chua_pd'] else '.'))
        return f'Không có thửa ở mức "{self.cb_muc.currentText()}".'

    def _mo_ho_dong(self, r: int, c: int = 0):
        ma = self.bang.ma_dong(r)
        if ma is not None:
            self.mo_ho.emit(int(ma))

    def ma_da_chon(self) -> list:
        """Mã hộ của các thửa đang chọn (một hộ nhiều thửa: một lần, giữ thứ tự)."""
        return list(dict.fromkeys(self.bang.ma_da_chon()))

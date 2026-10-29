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

# 1.0.02 (Hybrid Enterprise Navy, như thẻ số màn hình chính): nền trắng, viền slate, bo 6, vạch trái 3 px màu thẻ; thẻ đang lọc
# (KhungTienDo.KPI_LOC khớp bộ lọc / chế độ đang xem) nền xanh băng viền navy
_QSS_THE = '''
QFrame#the_kpi {{ background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 3px solid {m}; border-radius: 6px; }}
QFrame#the_kpi:hover {{ background: #F8FAFC; border-color: #94A3B8; border-left-color: {m}; }}
QFrame#the_kpi[dang_loc="1"] {{ background: #EFF6FF; border: 1px solid #1E3A5F; border-left: 3px solid {m}; }}
QLabel#kpi_tieu_de {{ color: #475569; font-size: 11px; font-weight: 600; background: transparent; border: 0; }}
QLabel#kpi_so {{ color: #0F172A; font-size: 16px; font-weight: 700; background: transparent; border: 0; }}
QLabel#kpi_phu {{ color: #475569; font-size: 11px; background: transparent; border: 0; }}
QProgressBar {{ background: #E2E8F0; border: 0; border-radius: 2px; }}
'''
CAO_THE_KPI = 58                         # thẻ chỉ số (px): như thẻ số 56 px màn hình chính, thêm thanh tiến độ mảnh
# màu vạch trái / số / thanh từng thẻ: navy (giải ngân), teal (mặt bằng sạch), slate (thửa còn vướng), đỏ trầm (cưỡng chế)
# 20/10/2026 (ảnh mẫu): 6 thẻ - tổng hộ, đã phê duyệt, đã chi trả (giai_ngan), đã bàn giao (mat_bang), đang vận động, đủ ĐK cưỡng chế.
# Thẻ "Thửa còn vướng" bỏ khỏi dải (chế độ xem có nút riêng "Thửa còn vướng")
MAU_THE = dict(tong_ho='#1E3A5F', phe_duyet='#1F76A6', giai_ngan='#2F7D54', mat_bang='#1F6F66', van_dong='#C98A22',
               cuong_che='#B83A3A')
NEN_MUC = {'gap': DO, 'cao': VANG, 'theo_doi': XAM}
# 22/10/2026 (nâng cấp giao diện): tên thẻ chữ thường kiểu câu - cùng kiểu thẻ số liệu các trang khác (trước: chữ HOA)
TIEU_DE_THE = dict(tong_ho='Tổng số hộ dự án', phe_duyet='Đã phê duyệt QĐ', giai_ngan='Đã chi trả tiền',
                   mat_bang='Đã bàn giao MB', van_dong='Đang vận động', cuong_che='Đủ ĐK cưỡng chế (Đ89)')
# bấm thẻ làm gì (chú thích) - KhungTienDo.bam_kpi làm đúng việc này
GOI_Y_THE = dict(tong_ho='Bấm để xem tất cả hộ',
                 phe_duyet='Bấm để lọc các hộ đã có quyết định phê duyệt',
                 giai_ngan='Bấm để lọc các hộ đã nhận tiền đủ các quyết định',
                 mat_bang='Bấm để lọc các hộ đã bàn giao mặt bằng',
                 van_dong='Bấm để lọc các hộ đang trong thời hạn vận động',
                 cuong_che='Bấm để lọc các hộ đủ điều kiện cưỡng chế thu hồi đất')
KHONG_SO = '—'                          # chưa có cơ sở để tính tỷ lệ (chưa có quyết định / chưa có diện tích)


class _TheKPI(QFrame):
    """Một thẻ chỉ số gọn (~64 px): tiêu đề nhỏ, số lớn + dòng chú thích một dòng (rút gọn "…", đủ chữ ở chú thích khi rê chuột),
    thanh tiến độ mảnh khi có tỷ lệ. Bấm cả thẻ -> bam."""
    bam = Signal()

    def __init__(self, tieu_de: str, mau: str, goi_y: str = '', parent=None):
        super().__init__(parent)
        self.setObjectName('the_kpi')
        self.setStyleSheet(_QSS_THE.format(m=mau))
        self.setProperty('dang_loc', '0')
        self.setFixedHeight(CAO_THE_KPI)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.goi_y = goi_y
        self.mau = mau
        self.lb_td = NhanRutGon(tieu_de)              # 6 thẻ ở màn hình 1366 @125%: tiêu đề dài rút "…" (đủ chữ ở chú thích)
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
        lo.setContentsMargins(10, 4, 10, 4)
        lo.setSpacing(1)
        lo.addWidget(self.lb_td)
        lo.addLayout(h)
        lo.addWidget(self.thanh)
        self.setMinimumWidth(118)                       # 20/10/2026: 6 thẻ (trước 4 thẻ x 170) - số "n hộ (x%)" luôn đọc được
        self.setToolTip(goi_y)

    def dat(self, so: str, ty_le: float | None, phu: str, chu_thich: str = '') -> None:
        self.lb_so.setText(so)
        self.lb_phu.setText(phu)
        self.setToolTip('\n'.join(x for x in (chu_thich or phu, self.goi_y) if x))
        self._vua_phu()
        self.thanh.setVisible(ty_le is not None)
        if ty_le is not None:
            self.thanh.setValue(int(min(100.0, max(0.0, ty_le)) * 10))
            self.thanh.setStyleSheet(f'QProgressBar::chunk {{ background: {self.mau}; border-radius: 2px; }}')

    def _vua_phu(self) -> None:
        """Thẻ hẹp (6 thẻ ở màn hình 1366 @125%): ẩn chữ phụ để số "n hộ (x%)" đọc đủ - chữ phụ vẫn ở chú thích thẻ."""
        can = self.lb_so.sizeHint().width() + 40 + (self.lb_phu.fontMetrics().horizontalAdvance('Giải ngân') if self.lb_phu.text() else 0)
        hien = bool(self.lb_phu.text()) and self.width() >= can + 20
        if self.lb_phu.isVisibleTo(self) != hien:
            self.lb_phu.setVisible(hien)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._vua_phu()

    def dat_dang_loc(self, co: bool) -> None:
        """Đánh dấu thẻ đang là bộ lọc / chế độ xem của bảng (nền xanh băng, viền navy)."""
        gt = '1' if co else '0'
        if self.property('dang_loc') != gt:
            self.setProperty('dang_loc', gt)
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()

    def dang_loc(self) -> bool:
        return self.property('dang_loc') == '1'

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()
                                                                              if hasattr(e, 'position') else e.pos()):
            self.bam.emit()


def _pt_chu(n: int, tong: int) -> str:
    return f'{n:,} hộ'.replace(',', '.') + (f' ({n * 100 / tong:.1f}%)'.replace('.', ',') if tong else '')


class DaiKPI(QWidget):
    """Dải 6 thẻ chỉ số của trang Tiến độ chi trả & Bàn giao. bam(khóa thẻ): tong_ho / phe_duyet / giai_ngan / mat_bang /
    van_dong / cuong_che."""
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

    def dat_loc(self, khoa: str | None) -> None:
        """Thẻ khoa (TIEU_DE_THE) đang là bộ lọc của bảng; None = không thẻ nào."""
        for k, t in self.the.items():
            t.dat_dang_loc(k == khoa)

    def dat(self, tq: dict | None, so_ngay_van_dong: int = 0, so_dang_vd: int = 0) -> None:
        """tq: bao_cao_gpmb.tong_quan; so_dang_vd: số hộ đang trong thời hạn vận động (KhungTienDo đếm). Tỷ lệ % trên tổng số hộ."""
        if tq is None:
            for t in self.the.values():
                t.dat('–', None, '')
            return
        n = tq['so_ho']
        ha = tq['dt_tong'] / 10000 if tq['dt_tong'] else None

        def pt(k):
            return k * 100 / n if n else None
        self.the['tong_ho'].dat(f'{n:,} hộ'.replace(',', '.'), None,
                                f'Diện tích thu hồi: {so_vn(round(ha, 2))} ha' if ha is not None else 'Chưa có diện tích thu hồi')
        pd = tq['so_ho_phe_duyet']
        self.the['phe_duyet'].dat(_pt_chu(pd, n), pt(pd), f'{tq["so_ho_chua_pd"]} hộ chưa có quyết định',
                                  f'{pd}/{n} hộ đã có quyết định phê duyệt · tổng phê duyệt {vn(tq["tong_pd"])} đ')
        if tq['tong_pd']:
            k = tq['so_ho_nhan_du']
            self.the['giai_ngan'].dat(_pt_chu(k, n), pt(k), f'Giải ngân {vn(tq["da_chi"])} đ ({tq["pt_giai_ngan"]:.1f}%)'.replace('.', ','),
                                      f'Đã chi {vn(tq["da_chi"])} / {vn(tq["tong_pd"])} đ đã phê duyệt · còn {vn(tq["con_lai"])} đ · '
                                      f'{k}/{tq["so_ho_phe_duyet"]} hộ đã nhận đủ tiền')
        else:
            self.the['giai_ngan'].dat(KHONG_SO, None, 'Chưa có quyết định phê duyệt',
                                      'Chưa có quyết định phê duyệt nào: chưa có số tiền để tính tỷ lệ giải ngân.')
        if tq['dt_tong']:
            k = tq['so_ho_ban_giao']
            self.the['mat_bang'].dat(_pt_chu(k, n), pt(k), f'Bàn giao {so_vn(round(tq["dt_ban_giao"] / 10000, 2))} ha',
                                     f'{so_vn(tq["dt_ban_giao"])} / {so_vn(tq["dt_tong"])} m² thu hồi đã bàn giao · '
                                     f'{k}/{n} hộ đã bàn giao')
        else:
            self.the['mat_bang'].dat(KHONG_SO, None, 'Chưa có diện tích thu hồi', 'Các thửa chưa có diện tích thu hồi.')
        self.the['van_dong'].lb_td.setText(f'Đang vận động ({so_ngay_van_dong} ngày)')
        self.the['van_dong'].dat(_pt_chu(so_dang_vd, n), pt(so_dang_vd), f'Chưa quá hạn {so_ngay_van_dong} ngày',
                                 f'Hộ đang trong thời hạn vận động {so_ngay_van_dong} ngày kể từ buổi vận động đầu tiên')
        k = tq['so_ho_cuong_che']
        self.the['cuong_che'].dat(_pt_chu(k, n), pt(k), f'Quá hạn {so_ngay_van_dong} ngày vận động',
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

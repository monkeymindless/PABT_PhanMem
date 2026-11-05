"""Thanh áp giá nhanh một hàng trên bảng mục 1. Đất của cửa sổ lập phương án (1.0.68): Đoạn đường (theo xã dự án) -> Vị trí -> Mặt đường -> Giá bảng giá -> công thức + kết quả.
Công thức, hệ số, K3 đường đất, khóa 1,00 khi tuyến có quy định riêng đều ở gia_dat_qd03.tinh_don_gia theo gói quy tắc của dự án; nhóm đất lấy theo loại đất của từng dòng.
Yếu tố khác (K2, Phụ lục III, K khác, giá cụ thể): bảng tính đầy đủ. Dữ liệu chỉ nạp khi thanh hiện lần đầu, mở cửa sổ không phải đọc gói quy tắc."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QWidget

from .giao_dien import dat_kieu_theo_tong
from .lap_pa import LoiNhap, doc_so
from .tien import vn


class ThanhApGiaNhanh(QWidget):
    """man: CuaSoLapPA; bm: BangMuc mục 1. nap() đọc gói + đoạn đường (tự gọi khi hiện lần đầu)."""

    def __init__(self, man, bm):
        super().__init__()
        self.setObjectName('thanh_ap_gia_nhanh')
        self.man, self.bm = man, bm
        self.goi = None
        self.kq = None
        self._da_nap = False
        self._dang_nap = False
        self._g_tay = False                   # người dùng tự gõ giá: không tự tra đè
        self.ly_do = ''
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        nhan = QLabel('Áp giá nhanh:')
        nhan.setProperty('vai', 'nhan')
        h.addWidget(nhan)
        self.cb_doan, self.cb_vi_tri, self.cb_ket_cau = QComboBox(), QComboBox(), QComboBox()
        for cb, tip, gian, chu in ((self.cb_doan, 'Đoạn đường của xã, phường dự án', 3, 14), (self.cb_vi_tri, 'Vị trí kết nối', 2, 8), (self.cb_ket_cau, 'Mặt đường', 2, 8)):
            cb.setToolTip(tip)
            cb.setMinimumContentsLength(chu)
            cb.setMaxVisibleItems(18)
            cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            cb.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            cb.view().setMinimumWidth(460)        # ô hẹp, danh sách xổ vẫn đủ chữ
            cb.currentIndexChanged.connect(lambda *_, c=cb: self._doi_cb(c))
            h.addWidget(cb, gian)
        self.o_g = QLineEdit()
        self.o_g.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.o_g.setPlaceholderText('Giá NQ 28')
        self.o_g.setToolTip('Giá bảng giá (đ/m²): tự tra theo đoạn đường, vị trí, loại đất của dòng; gõ số để dùng giá khác')
        self.o_g.setMaximumWidth(self.o_g.fontMetrics().boundingRect('12.345.678').width() + 20)
        self.o_g.textEdited.connect(lambda *_: self._go_gia())
        h.addWidget(self.o_g)
        self.lb_ct = QLabel('')
        dat_kieu_theo_tong(self.lb_ct, 'QLabel { font-weight: 600; }')
        self.lb_ct.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        h.addWidget(self.lb_ct, 3)
        self.b_ap = QPushButton('Áp vào dòng đất đang chọn')
        self.b_ap.clicked.connect(lambda: self.ap_dong_chon())
        self.b_them = QPushButton('Thêm thành dòng đất mới')
        self.b_them.setToolTip('Thêm một dòng cho thửa đang chọn ở ô Thửa, áp luôn đơn giá này')
        self.b_them.clicked.connect(lambda: self.them_dong_moi())
        h.addWidget(self.b_ap)
        h.addWidget(self.b_them)

    def showEvent(self, e):
        super().showEvent(e)
        if not self._da_nap:
            self.nap()

    # ---------------------------------------------------------------- nạp
    def nap(self) -> None:
        from . import gia_dat_qd03 as g
        from . import goi_gia_dat as gg
        self._da_nap = True
        self._dang_nap = True
        try:
            bo = self.man.bo
            xa = bo.bc.ten_dia_ban or ''
            self.goi = gg.goi_du_an(bo.con, xa)
            k = g.dia_ban_theo_ten(xa, self.goi)
            cac_xa = [k] if k else g.ds_dia_ban(self.goi)        # xã dự án không có trong gói: để chọn đoạn của mọi địa bàn trong gói, không để trống
            self.cb_doan.clear()
            for x in cac_xa:
                for r in g.ds_doan(x, self.goi):
                    self.cb_doan.addItem(('' if k else g.ten_ngan(x) + ': ') + g.nhan_doan(r), f'{x}|{r["ma_doan_duong"]}')
            self.cb_vi_tri.clear()
            for x in self.goi['vi_tri']:
                self.cb_vi_tri.addItem(x['ten'], x['ma'])
            self.cb_ket_cau.clear()
            for x in self.goi['ket_cau']:
                self.cb_ket_cau.addItem(x['ten'], x['ma'])
        finally:
            self._dang_nap = False
        self._g_tay = False
        self.tinh()
        self.cap_nhat_khoa()

    def _doi_cb(self, cb) -> None:
        cb.setToolTip(cb.currentText())
        if not self._dang_nap:
            self._g_tay = False
            self.tinh()

    def _go_gia(self) -> None:
        self._g_tay = bool(self.o_g.text().strip())
        self.tinh()

    def _doan(self) -> tuple:
        """(địa bàn, dòng đoạn đường hoặc None)."""
        from . import gia_dat_qd03 as g
        dl = self.cb_doan.currentData() or ''
        x, _, ma = dl.partition('|')
        return x, g.tim_doan(x, ma, self.goi)

    def thong_so(self) -> dict:
        """Thông số đang chọn, đưa sang bảng tính đầy đủ."""
        if not self._da_nap:
            return {}
        x, d = self._doan()
        return dict(dia_ban=x, ma_doan=(d or {}).get('ma_doan_duong'), vi_tri=self.cb_vi_tri.currentData(), ket_cau=self.cb_ket_cau.currentData(), loai_dat=self._loai_dang_chon())

    # ---------------------------------------------------------------- tính
    def _loai_dang_chon(self) -> str:
        bo = self.man.bo
        i = self.bm._bang.currentRow()
        if 0 <= i < len(bo.pa.dat):
            return bo.pa.dat[i].loai_dat
        mt = self.bm.cb_thua.currentData() if self.bm.cb_thua.count() else None
        t = bo.bc.thua.get(mt) if mt is not None else None
        if t is None and bo.pa.dat:
            return bo.pa.dat[0].loai_dat
        return str((t or {}).get('loai_dat') or '')

    def tinh_cho(self, loai_dat: str) -> tuple:
        """(KetQua hoặc None, lý do không tính được) của một loại đất, theo thông số trên thanh."""
        from . import gia_dat_qd03 as g
        if self.goi is None:
            self.nap()
        n = g.nhom_theo_loai_dat(loai_dat, self.goi)
        if n is None:
            return None, f'Loại đất {loai_dat or "(chưa chọn)"} chưa có nhóm giá: dùng bảng tính đầy đủ.'
        x, doan = self._doan()
        if doan is None:
            return None, 'Chọn đoạn đường.'
        vt = self.cb_vi_tri.currentData() or ''
        if self._g_tay:
            try:
                gia = doc_so(self.o_g.text(), 'Giá bảng giá')
            except LoiNhap as e:
                return None, str(e)
        else:
            gia = g.gia_bang_gia(x, doan, n['ma'], vt, n['cot_gia'], self.goi)
        if not gia or gia <= 0:
            return None, 'Bảng giá không có dòng khớp: gõ giá vào ô Giá NQ 28.'
        v = g.DauVao(dia_ban=x, nhom_dat=n['ma'], ma_doan_duong=doan['ma_doan_duong'], loai_ket_noi_vi_tri=vt, ket_cau_mat_duong=self.cb_ket_cau.currentData() or '', don_gia_bang_gia=gia, cot_gia=n['cot_gia'])
        return g.tinh_don_gia(v, doan, self.goi), ''

    def tinh(self):
        """Tính theo loại đất của dòng đang chọn, hiện công thức."""
        from . import gia_dat_qd03 as g
        if not self._da_nap or self._dang_nap:
            return None
        self.kq, self.ly_do = self.tinh_cho(self._loai_dang_chon())
        if not self._g_tay:
            self.o_g.setText(vn(self.kq.don_gia_nq28) if self.kq is not None else '')
        if self.kq is None:
            self.lb_ct.setText(self.ly_do)
            self.lb_ct.setToolTip(self.ly_do)
        else:
            self.lb_ct.setText(g.cong_thuc_gon(self.kq) + (' (!)' if self.kq.canh_bao else ''))      # (!): K3 tự khóa, K1 chưa có... chi tiết ở chú thích
            self.lb_ct.setMinimumWidth(min(self.lb_ct.fontMetrics().boundingRect(self.lb_ct.text()).width() + 8, 300))     # công thức là thứ phải đọc được: ô chọn nhường chỗ
            self.lb_ct.setToolTip('\n'.join(['Công thức: ' + self.kq.cong_thuc] + ['! ' + c for c in self.kq.canh_bao] + self.kq.buoc_lap_luan))
        self.cap_nhat_khoa()
        return self.kq

    def cap_nhat_khoa(self) -> None:
        """Bật / tắt theo bản đang mở. V1 khóa vẫn bật: bấm thì chuyển sang nhánh V2 (CuaSoLapPA.dam_bao_sua_dat), V1 không đổi."""
        man = self.man
        duoc = man.co_the_ap_gia_dat()
        for w in (self.cb_doan, self.cb_vi_tri, self.cb_ket_cau, self.o_g):
            w.setEnabled(duoc)
        self.b_ap.setEnabled(duoc and self.kq is not None and bool(man.bo.pa.dat))
        self.b_them.setEnabled(duoc and self.kq is not None and self.bm.cb_thua.count() > 0)

    # ---------------------------------------------------------------- áp
    def _ghi(self, ds: list) -> list:
        """ds: chỉ số dòng; mỗi dòng tính theo loại đất của nó. Trả [(chỉ số, lý do)] dòng không tính được."""
        from . import gia_dat_qd03 as g
        bo = self.man.bo
        x, doan = self._doan()
        vt = g.mo_ta_vi_tri(doan, self.cb_vi_tri.currentData() or '', self.goi)
        loi = []
        doi = []
        for i in ds:
            kq, ly_do = self.tinh_cho(bo.pa.dat[i].loai_dat)
            if kq is None or kq.don_gia_ap_dung <= 0:
                loi.append((i, ly_do or 'Đơn giá bằng 0.'))
                continue
            bo.ap_don_gia_qd03([i], kq.don_gia_ap_dung, g.ghi_chu_ap_gia(kq, doan, g.ten_ngan(x)), vt)
            doi.extend(bo.ho_tro_doi)
        bo.ho_tro_doi = doi
        return loi

    def _sau_ghi(self, n: int, loi: list, chon=None) -> None:
        from . import ap_gia_dat as ap
        man = self.man
        cb = ap.gop_can_cu(man.bo.con, self.goi) if n else ''
        chu = f'Đã áp đơn giá vào {n} dòng đất.' + (f' Tính lại {len(man.bo.ho_tro_doi)} khoản đào tạo, chuyển đổi nghề.' if man.bo.ho_tro_doi else '')
        if loi:
            chu += ' Chưa áp: ' + '; '.join(f'dòng 1.{i + 1}: {c}' for i, c in loi)
        if cb:
            chu += ' ' + cb
        man.sau_ap_gia_dat(chu, chon)

    def ap_dong_chon(self, ds=None) -> int:
        """Áp vào các dòng đang chọn (không chọn mà chỉ có một dòng: dòng đó). Trả số dòng đã áp."""
        man, bo = self.man, self.man.bo
        if ds is None:
            ds = self.bm.cac_dong_chon() or ([0] if len(bo.pa.dat) == 1 else [])
        ds = [i for i in ds if 0 <= i < len(bo.pa.dat)]
        if not ds:
            man.thong_bao('Chọn dòng đất ở bảng để áp giá.')
            return 0
        if not man.dam_bao_sua_dat():
            return 0
        bo = man.bo
        loi = self._ghi(ds)
        n = len(ds) - len(loi)
        self._sau_ghi(n, loi, ds[0])
        return n

    def them_dong_moi(self, ma_thua=None):
        """Thêm dòng cho thửa ở ô Thửa rồi áp giá. Trả chỉ số dòng hoặc None."""
        man = self.man
        mt = ma_thua if ma_thua is not None else (self.bm.cb_thua.currentData() if self.bm.cb_thua.count() else None)
        if mt is None:
            man.thong_bao('Hộ này chưa có thửa: thêm thửa ở thẻ Thông tin hộ, thửa đất.')
            return None
        if not man.dam_bao_sua_dat():
            return None
        bo = man.bo
        try:
            i, _ = bo.them_thua(mt)
        except LoiNhap as e:
            man.thong_bao(str(e))
            return None
        loi = self._ghi([i])
        if loi:
            bo.xoa(1, i)                     # chưa có giá thì không để lại dòng trống: dùng Thêm thửa nếu muốn nhập tay
            man.thong_bao(f'Chưa thêm dòng: {loi[0][1]}')
            return None
        bo.tinh_lai_ho_tro()                 # diện tích đất đổi: các khoản theo diện tích cũng đổi
        self._sau_ghi(1, [], i)
        return i

"""Hộp thoại NQ 28/2025 (1.0.81) mở từ thẻ "Cập nhật, bổ sung giá đất" (man_hinh_gia_dat.KhungCapNhatGiaDat):
HopPhanTich4LoaiDatNN - giá 4 loại đất nông nghiệp (Điều 5) của một dòng bảng giá + trần / sàn Phụ lục VIII, thử tỷ lệ phạm vi;
HopTinhGiaTaiDinhCuVaDieu8 - giá đất tái định cư và trường hợp cụ thể Điều 8-10 (quy_tac_vi_tri.tinh_gia_tai_dinh_cu_va_truong_hop_cu_the).
Chỉ tính / xem - không ghi bảng giá, không ghi dự án. Mọi tỷ lệ đọc từ gói dữ liệu (gia_dat_qd03.json, khóa quy_tac_nq28)."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import gia_dat_nq28 as nq
from .tien import vn


def _o_so(it: QTableWidgetItem) -> QTableWidgetItem:
    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return it


class HopPhanTich4LoaiDatNN(QDialog):
    """4 cột giá đất nông nghiệp của dòng bảng giá đang chọn: giá bảng (cột riêng hoặc cột dự phòng), tỷ lệ phạm vi thử, giá sau tỷ lệ,
    trần / sàn Phụ lục VIII; giá sau tỷ lệ thấp hơn sàn thì lấy sàn."""
    COT = ['Loại đất', 'Mã đất', 'Cột giá', 'Giá bảng (đ/m²)', 'Tỷ lệ (%)', 'Giá theo tỷ lệ (đ/m²)', 'Sàn PL VIII', 'Trần PL VIII', 'Ghi chú']

    def __init__(self, parent=None, dong: dict | None = None, dia_ban: str = ''):
        super().__init__(parent)
        self.setWindowTitle('Phân tích 4 loại đất nông nghiệp - Điều 5 NQ 28/2025')
        self.dong = dong or {}
        self.dia_ban = dia_ban or self.dong.get('xa', '')
        self.lb = QLabel()
        self.lb.setWordWrap(True)
        self.bang = QTableWidget(0, len(self.COT))
        self.bang.setHorizontalHeaderLabels(self.COT)
        self.bang.verticalHeader().setVisible(False)
        self.bang.horizontalHeader().setStretchLastSection(True)
        for c, w in enumerate((190, 150, 95, 120, 75, 140, 100, 100)):
            self.bang.setColumnWidth(c, w)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed |
                                  QAbstractItemView.EditTrigger.AnyKeyPressed)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        lo.addWidget(self.lb)
        lo.addWidget(self.bang, 1)
        lo.addWidget(nut)
        self.resize(1080, 320)
        self.nap()
        self.bang.itemChanged.connect(self._doi_o)

    def nap(self) -> list:
        r = self.dong
        ds = nq.phan_tich_4_loai_nn(r, self.dia_ban) if r else []
        self.ds = ds
        self.lb.setText((f'{r.get("xa", "")} - {r.get("ten_duong", "")} ({r.get("vi_tri", "")}). ' if r else
                         'Chưa chọn dòng bảng giá. ') +
                        'Bảng giá NQ 28 gộp 2 cột giá nông nghiệp: cây lâu năm / hằng năm dùng chung cột "nn_cay", nuôi trồng thủy sản / '
                        'rừng sản xuất dùng chung cột "nn_rung_nts" (cột dự phòng) khi bảng không có cột riêng. Sửa ô Tỷ lệ để thử '
                        'phạm vi (PV2 80%, PV3 60%, VT2 30%); giá thấp hơn sàn Phụ lục VIII thì lấy sàn.')
        b = self.bang
        b.blockSignals(True)
        try:
            b.setRowCount(len(ds))
            for i, x in enumerate(ds):
                for c, v in enumerate((x['ten'], x['ma_dat'], x['cot_gia'], vn(x['gia']), '100', '',
                                       vn(x['toi_thieu']) if x['toi_thieu'] else '', vn(x['toi_da']) if x['toi_da'] else '',
                                       x['ghi_chu'])):
                    it = QTableWidgetItem(str(v))
                    if c != 4:
                        it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    b.setItem(i, c, _o_so(it) if 3 <= c <= 7 else it)
                self._tinh_dong(i)
        finally:
            b.blockSignals(False)
        return ds

    def _tinh_dong(self, i: int) -> None:
        from .tien import D, doc_so_vn, lam_tron
        x = self.ds[i]
        try:
            tl = doc_so_vn(self.bang.item(i, 4).text().replace('%', '')) / 100
        except (ValueError, ArithmeticError):
            tl = None
        if tl is None or tl <= 0:
            chu = 'Tỷ lệ sai'
        else:
            g = lam_tron(D(x['gia']) * tl, 0)
            if x['toi_thieu'] and g < D(x['toi_thieu']):
                g = D(x['toi_thieu'])
            chu = vn(g)
        self.bang.blockSignals(True)
        self.bang.setItem(i, 5, _o_so(QTableWidgetItem(chu)))
        self.bang.item(i, 5).setFlags(self.bang.item(i, 5).flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.bang.blockSignals(False)

    def _doi_o(self, it) -> None:
        if it.column() == 4 and 0 <= it.row() < len(self.ds):
            self._tinh_dong(it.row())


class HopTinhGiaTaiDinhCuVaDieu8(QDialog):
    """Chọn trường hợp (tái định cư, phạm vi, nhiều mặt tiền, Điều 8 K5-K12, Điều 9, Điều 10), nhập giá gốc + tham số -> giá, hệ số,
    giải trình, căn cứ. Thẻ dưới: quy tắc đã đọc từ toàn văn nghị quyết (nếu đã nạp)."""

    def __init__(self, parent=None, dong: dict | None = None):
        super().__init__(parent)
        from .quy_tac_vi_tri import cac_truong_hop, doc_quy_tac_toan_van_da_luu
        self.setWindowTitle('Giá đất tái định cư và trường hợp cụ thể Điều 8-10 - NQ 28/2025')
        self.cb = QComboBox()
        for ma, ten, cc in cac_truong_hop():
            self.cb.addItem(f'{ten} ({cc})', ma)
        g = nq.gia_dong(dong, 'dat_o') if dong and dong.get('dat_o') else 0
        self.o_gia = QLineEdit(vn(g) if g else '')
        self.o_gia.setPlaceholderText('Giá gốc đồng/m² (giá đường, giá đất ở TĐC, giá 70 năm…)')
        self.o_kc = QLineEdit()
        self.o_kc.setPlaceholderText('m - chỉ cho "KDC cách đường Phụ lục VII"')
        self.ck_do_thi = QCheckBox('Khu vực đô thị')
        self.o_dt = QLineEdit()
        self.o_dt.setPlaceholderText('m² - DT suất tái định cư tối thiểu')
        self.o_bt = QLineEdit()
        self.o_bt.setPlaceholderText('đồng - tiền bồi thường đất ở của hộ')
        self.o_khac = QLineEdit()
        self.o_khac.setPlaceholderText('Giá sàn / giá tỉnh giáp ranh / số năm / giá các đường (cách nhau ";")')
        self.lb_kq = QLabel()
        self.lb_kq.setWordWrap(True)
        self.lb_kq.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form = QFormLayout()
        form.addRow('Trường hợp:', self.cb)
        form.addRow('Giá gốc (đ/m²):', self.o_gia)
        form.addRow('Khoảng cách (m):', self.o_kc)
        form.addRow('', self.ck_do_thi)
        form.addRow('DT suất TĐC (m²):', self.o_dt)
        form.addRow('Tiền BT đất ở (đ):', self.o_bt)
        form.addRow('Tham số khác:', self.o_khac)
        self.bang = QTableWidget(0, 4)
        self.bang.setHorizontalHeaderLabels(['Điều', 'Khoản', 'Tỷ lệ / hệ số / khoảng cách', 'Nội dung'])
        self.bang.verticalHeader().setVisible(False)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for c, w in enumerate((50, 55, 190)):
            self.bang.setColumnWidth(c, w)
        qt = doc_quy_tac_toan_van_da_luu()
        self.bang.setRowCount(len(qt))
        for i, q in enumerate(qt):
            so = '; '.join([f'{x}%' for x in q.get('ty_le') or []] + [f'hệ số {x}' for x in q.get('he_so') or []] +
                           [f'{x} m' for x in q.get('khoang_cach_m') or []])
            for c, v in enumerate((q.get('dieu', ''), q.get('khoan', ''), so, q.get('noi_dung', ''))):
                it = QTableWidgetItem(str(v))
                it.setToolTip(str(v))
                self.bang.setItem(i, c, it)
        lb_qt = QLabel(f'Quy tắc đọc từ toàn văn nghị quyết đã nạp: {len(qt)}' if qt else
                       'Chưa nạp toàn văn nghị quyết: thẻ "Cập nhật, bổ sung giá đất" > Đọc file… chọn file toàn văn NQ 28 (.docx / .pdf).')
        lb_qt.setWordWrap(True)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        nut.rejected.connect(self.reject)
        lo = QVBoxLayout(self)
        lo.addLayout(form)
        lo.addWidget(self.lb_kq)
        lo.addWidget(lb_qt)
        lo.addWidget(self.bang, 1)
        lo.addWidget(nut)
        self.resize(900, 600)
        for w in (self.o_gia, self.o_kc, self.o_dt, self.o_bt, self.o_khac):
            w.textChanged.connect(lambda _=None: self.tinh())
        self.cb.currentIndexChanged.connect(lambda _=None: self.tinh())
        self.ck_do_thi.toggled.connect(lambda _=None: self.tinh())
        self.tinh()

    def tinh(self) -> dict | None:
        from .quy_tac_vi_tri import LoiQuyTac, tinh_gia_tai_dinh_cu_va_truong_hop_cu_the
        th = self.cb.currentData() or ''
        khac = [x.strip() for x in self.o_khac.text().split(';') if x.strip()]
        ts = dict(khoang_cach_m=self.o_kc.text().strip() or None, do_thi=self.ck_do_thi.isChecked(),
                  dt_suat=self.o_dt.text().strip() or None, tien_bt_dat_o=self.o_bt.text().strip() or None)
        if th == 'chenh_lech_suat_tdc':
            ts['gia_tdc'] = self.o_gia.text().strip() or None
        elif th == 'nga_ba':
            ts['gia_cac_duong'] = khac
        elif th == 'giap_ranh':
            ts['gia_tinh_ban'] = khac[0] if khac else None
        elif th == 'thoi_han':
            ts['so_nam'] = khac[0] if khac else None
        elif th.startswith('pham_vi_') and khac:
            ts['san'] = khac[0]
        try:
            kq = tinh_gia_tai_dinh_cu_va_truong_hop_cu_the(th, self.o_gia.text().strip() or None, **ts)
        except LoiQuyTac as e:
            self.lb_kq.setText(f'Chưa tính được: {e}')
            return None
        self.lb_kq.setText(f'Kết quả: {vn(kq["gia"])} {"đồng" if th == "chenh_lech_suat_tdc" else "đồng/m²"}. '
                           f'{kq["giai_trinh"]}. Căn cứ: {kq["can_cu"]} NQ 28/2025/NQ-HĐND.')
        return kq

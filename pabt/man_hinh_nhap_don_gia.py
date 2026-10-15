"""Màn hình xem trước cập nhật đơn giá từ file Excel / Word / PDF / CSV: thông tin văn bản, nhóm từng dòng, bỏ chọn dòng,
áp dụng."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox,
                               QPlainTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import nhap_don_gia as ndg
from .lap_pa import LoiNhap
from .tien import vn
from .thong_bao import TEN_UD

MAU = {'mới': QColor('#E8F5E9'), 'cập nhật': QColor('#FFF8E1'), 'giữ nguyên': QColor('#F5F5F5')}
DONG_TU_CAO_TOI_DA = 1500
TEN_NHOM_NGAN = {2: 'Nhà, công trình', 3: 'Cây trồng', ndg.NHOM_VN: 'Vật nuôi', 4: 'Hỗ trợ'}
C_MA, C_TEN, C_DVT, C_GIA = 1, 2, 3, 4


def mo_ta_van_ban(vb: dict) -> str:
    """'Quyết định 48/2025/QĐ-UBND ngày 23/10/2025 của Ủy ban nhân dân tỉnh Đồng Nai' (rỗng nếu không nhận ra số hiệu)."""
    if not vb or not vb.get('so_hieu'):
        return ''
    return ' '.join(x for x in (vb.get('loai_vb', ''), vb['so_hieu'], f'ngày {vb["ngay"]}' if vb.get('ngay') else '',
                                f'của {vb["co_quan"]}' if vb.get('co_quan') else '') if x)


class HopNhapDonGia(QDialog):
    im_lang = False

    def __init__(self, file, parent=None, nguon: str = '', dong: list | None = None, van_ban: dict | None = None,
                 nhom_uu_tien: int | None = None):
        """dong: các dòng đã đọc sẵn (ndg.doc_bang_ocr, có hộp tiến trình khi phải nhận dạng bản scan; chữ dán từ Clipboard).
        van_ban: ndg.phan_tich_van_ban (không có thì tự phân tích các dòng đầu của file). nhom_uu_tien: nhóm của thẻ đang xem ở Bộ
        đơn giá (2 / 3 / 7 / 4) - dùng khi văn bản không cho biết nhóm (bảng dán, file không có trích yếu)."""
        # đọc file trước khi tạo hộp thoại: file lỗi thì không để lại hộp thoại dở dang
        dong = ndg.doc_bang(file) if dong is None else dong
        vb = van_ban if van_ban is not None else ndg.phan_tich_van_ban(dong)
        nhom_vb = vb.get('nhom', 0) or nhom_uu_tien or 0
        ds = ndg.nhan_muc(dong, nhom_vb)
        xem_van, tu_loi_van = [], False
        if not ds:                                      # không có bảng: đơn giá viết trong điều khoản (QĐ 31/2025 vật nuôi...)
            ds, xem_van = ndg.muc_tu_loi_van(dong, nhom_vb)
            tu_loi_van = bool(ds)
        if not ds:
            raise ndg.LoiKhongCoGia('Không tìm thấy đơn giá nào trong file: không có bảng (cột Tên, ĐVT, Đơn giá) và không có câu '
                                    'ghi giá dạng "<tên> … <số> đồng/<đơn vị>".' +
                                    ('\n\n' + '\n'.join(xem_van[:10]) if xem_van else ''))
        super().__init__(parent)
        self.tu_loi_van = tu_loi_van
        self.ds = ds
        self.van_ban = vb
        self.da_co = ndg.da_co(vb.get('so_hieu', ''))
        self.ket_qua = None
        self.nguon = nguon or Path(str(file or 'Clipboard')).name
        self.setWindowTitle(f'Cập nhật đơn giá từ {self.nguon}')
        self.resize(1300, 760)
        lo = QVBoxLayout(self)
        mt = mo_ta_van_ban(vb)
        if mt:
            l_vb = QLabel(f'<b>{mt}</b><br>{vb.get("trich_yeu", "")}')
            l_vb.setWordWrap(True)
            l_vb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lo.addWidget(l_vb)
        canh = []
        if self.da_co:
            canh.append('Văn bản này ĐÃ CÓ trong danh sách văn bản của bộ đơn giá. Giá có thể đã được văn bản ban hành sau sửa đổi: '
                        'các dòng ĐỔI GIÁ để trống ô "Dùng" (áp dụng lại sẽ ghi đè giá mới bằng giá cũ) - chỉ chọn khi chắc chắn. '
                        'Mục MỚI (chưa có trong danh mục) vẫn được chọn.')
        if mt and not vb.get('dong_nai'):
            canh.append('Không thấy tên Đồng Nai trong văn bản: kiểm tra đây có đúng văn bản áp dụng tại địa phương không.')
        if self.tu_loi_van:
            canh.append(f'Văn bản không có bảng giá: {len(ds)} đơn giá đọc từ LỜI VĂN các điều khoản (tên = chữ trước số tiền, ghép '
                        'tiêu đề khoản). Rê chuột vào tên để xem câu gốc; sửa tên / bỏ chọn dòng chưa đúng trước khi áp dụng.')
        if vb.get('sua_doi'):
            canh.append('Văn bản sửa đổi, bổ sung: chỉ các bảng giá trong văn bản được áp dụng; nội dung bãi bỏ / sửa điều khoản '
                        'ở khung bên dưới cần tự xử lý.')
        if canh:
            l_canh = QLabel('\n'.join('• ' + x for x in canh))
            l_canh.setWordWrap(True)
            l_canh.setStyleSheet('QLabel { color: #B71C1C; background: #FFEBEE; padding: 6px; border-radius: 4px; }')
            lo.addWidget(l_canh)
        self.o_nhom = QComboBox()
        self.o_nhom.addItem('Tự động: theo văn bản, tiêu đề nhóm và từng dòng (tên, ĐVT)', 0)
        for k, t in ndg.NHOM.items():
            self.o_nhom.addItem('Toàn bộ là ' + t, k)
        self.o_nhom.currentIndexChanged.connect(self.khop)
        hang = QHBoxLayout()
        n = QLabel('Nhóm danh mục:')
        n.setProperty('vai', 'nhan')
        hang.addWidget(n)
        hang.addWidget(self.o_nhom)
        self.lb = QLabel()
        hang.addWidget(self.lb, 1)
        lo.addLayout(hang)
        self.bang = QTableWidget(0, 8)
        self.bang.setHorizontalHeaderLabels(['Dùng', 'Mã', 'Tên', 'ĐVT', 'Đơn giá mới (đ)', 'Đơn giá hiện hành (đ)', 'Trạng thái',
                                             'Nhóm'])
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        for c, w in enumerate((50, 80, 520, 110, 120, 140, 150, 130)):          # ĐVT rộng: "m² mặt nước"
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.setWordWrap(True)                     # tên dài (điều kiện "nuôi dưới 50%…" ở cuối) không bị cắt "…"
        lo.addWidget(self.bang, 1)
        self.bang.cellChanged.connect(self._sua_o)
        if xem_van:
            o = QPlainTextEdit('\n'.join(xem_van))
            o.setReadOnly(True)
            o.setMaximumHeight(110)
            lo.addWidget(QLabel('Câu có số tiền / tỷ lệ phần mềm KHÔNG tự lấy (khoảng giá, tỷ lệ %, không rõ tên) - xem và nhập tay nếu cần:'))
            lo.addWidget(o)
        self.xem_van = xem_van
        if vb.get('can_xem'):
            o = QPlainTextEdit('\n'.join(vb['can_xem']))
            o.setReadOnly(True)
            o.setMaximumHeight(110)
            lo.addWidget(QLabel('Nội dung sửa đổi / bãi bỏ trong văn bản (phần mềm không tự áp dụng - xem và xử lý nếu cần):'))
            lo.addWidget(o)
        lo.addWidget(QLabel('Xanh: mục mới (thêm vào danh mục). Vàng: đổi giá ("gần đúng": tên gần giống, xem kỹ). Xám: giá không '
                            'đổi (bỏ qua). Bỏ dấu ở cột "Dùng" với dòng không muốn cập nhật. Bộ đơn giá cũ được giữ; dự án đang '
                            'lập muốn dùng giá mới thì "Áp bộ đơn giá vào dự án".'))
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText('Áp dụng: tạo bộ đơn giá mới')
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        lo.addWidget(nut)
        self.khop()

    def khop(self):
        ndg.so_khop(self.ds, self.o_nhom.currentData() or None)
        nhom_bang = self.o_nhom.currentData() or 0
        self._dang_ve = True
        self.bang.setRowCount(len(self.ds))
        for i, m in enumerate(self.ds):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            # văn bản đã có: chỉ bỏ chọn sẵn dòng ĐỔI GIÁ (có thể ghi đè giá văn bản sau đã sửa); mục mới không ghi đè gì - vẫn chọn
            # (QĐ 31/2025 có tên trong danh sách văn bản nhưng bộ đơn giá chưa có mục vật nuôi nào)
            dung = m.chon and m.trang_thai != 'giữ nguyên' and not (self.da_co and m.trang_thai == 'cập nhật')
            chk.setCheckState(Qt.CheckState.Checked if dung else Qt.CheckState.Unchecked)
            self.bang.setItem(i, 0, chk)
            tt = m.trang_thai + (f' (gần đúng {m.khop_gan:.0%})' if m.khop_gan else '')
            n = nhom_bang or m.nhom or 3
            # mục mới: tiền tố mã sẽ cấp khi áp dụng (số tiếp theo của bộ đơn giá - ma_tai_san.ma_tiep)
            ma = m.ma_khop or m.ma or (f'{ndg.TIEN_TO.get(n, "")}… (mới)' if m.trang_thai == 'mới' else '')
            for c, v in enumerate((ma, m.ten, m.dvt, vn(m.don_gia), vn(m.gia_cu) if m.gia_cu else '', tt,
                                   TEN_NHOM_NGAN.get(n, '')), start=1):
                it = QTableWidgetItem(v)
                if c not in (C_TEN, C_DVT, C_GIA):              # sửa được Tên, ĐVT, Đơn giá mới trước khi áp dụng
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                it.setToolTip(m.nguon_dong)
                it.setBackground(QBrush(MAU[m.trang_thai]))
                if c in (4, 5):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.bang.setItem(i, c, it)
        if len(self.ds) <= DONG_TU_CAO_TOI_DA:          # cao dòng theo chữ: đo từng dòng, bảng vài nghìn dòng thì bỏ qua
            self.bang.resizeRowsToContents()
        self._dang_ve = False
        dem = {k: sum(m.trang_thai == k for m in self.ds) for k in MAU}
        gan = sum(1 for m in self.ds if m.khop_gan)
        self.lb.setText(f'  {len(self.ds)} dòng: {dem["mới"]} mới, {dem["cập nhật"]} đổi giá, {dem["giữ nguyên"]} không đổi'
                        + (f', {gan} khớp tên gần đúng.' if gan else '.'))

    def _sua_o(self, r: int, c: int):
        """Sửa tên / ĐVT / đơn giá mới: ghi vào mục rồi so khớp lại với bộ đơn giá đang dùng (đổi trạng thái mới / đổi giá)."""
        if getattr(self, '_dang_ve', False) or c not in (C_TEN, C_DVT, C_GIA) or not 0 <= r < len(self.ds):
            return
        chu = ' '.join(self.bang.item(r, c).text().split())
        m = self.ds[r]
        if c == C_GIA:
            g = ndg.doc_gia(chu)
            if not g:
                if not self.im_lang:
                    QMessageBox.warning(self, TEN_UD, f'Đơn giá "{chu}" không đọc được: gõ số tiền (ví dụ 1.250.000).')
                self.khop()
                return
            if g == m.don_gia:
                return
            m.don_gia = g
            self.khop()
            return
        if not chu or chu == (m.ten if c == C_TEN else m.dvt):
            return
        if c == C_TEN:
            m.ten = chu
        else:
            m.dvt = chu
        m.ma_khop, m.gia_cu, m.khop_gan = '', None, 0.0
        self.khop()

    def accept(self):
        for i, m in enumerate(self.ds):
            m.chon = self.bang.item(i, 0).checkState() == Qt.CheckState.Checked
        if not any(m.chon and m.trang_thai in ('mới', 'cập nhật') for m in self.ds):
            if not self.im_lang:
                QMessageBox.warning(self, TEN_UD, 'Chưa chọn dòng nào mới hoặc đổi giá để cập nhật.')
            return
        try:
            self.ket_qua = ndg.ap_dung(self.ds, self.o_nhom.currentData() or None, self.nguon, van_ban=self.van_ban)
        except LoiNhap as e:
            if not self.im_lang:
                QMessageBox.warning(self, TEN_UD, str(e))
            return
        if not self.im_lang:
            QMessageBox.information(self, TEN_UD, f'Đã tạo bộ đơn giá phiên bản {self.ket_qua["phien_ban"]}: '
                                                  f'{self.ket_qua["so_moi"]} mục mới, {self.ket_qua["so_cap_nhat"]} mục đổi giá.')
        super().accept()

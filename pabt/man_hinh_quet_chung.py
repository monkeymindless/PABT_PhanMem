"""Nút Quét dùng chung (UnifiedScanTriggerButton) + hộp xem kết quả quét (AI Smart Scan hợp nhất, chạy trên máy - quet_chung.py).

Mọi nơi có nút "Quét / Nạp file" dùng `NutQuetChung(nhan, ngu_canh)` hoặc `chon_va_quet(cha, ngu_canh)`: chọn file -> hộp tiến trình (nhận dạng
chữ từng trang) -> `quet_chung.quet` -> `HopKetQuaQuet` cho người dùng XEM TRƯỚC (văn bản căn cứ đã sắp 13 bậc, thửa đất, tài sản / cây
trồng, thông số) rồi mới ghi / chuyển sang Bảng tính đơn giá đất. Không gửi dữ liệu ra ngoài."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QFileDialog, QLabel, QMessageBox, QPlainTextEdit, QPushButton,
                               QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout)

from . import quet_chung as qc
from . import van_ban_can_cu as vb
from .tien import vn

TIEU_DE = 'LARC - Quét file'
TEN_NGU_CANH = {
    qc.AUTO: 'Quét file (tự nhận dạng loại văn bản)',
    qc.CAN_CU: 'Quét văn bản căn cứ',
    qc.GIA_DAT: 'Quét văn bản / bảng giá đất',
    qc.GIA_TAI_SAN: 'Quét đơn giá nhà, vật kiến trúc, cây trồng',
    qc.HO_SO_HO: 'Quét hồ sơ chi tiết của hộ',
    qc.BANG_TONG_HOP: 'Quét bảng tổng hợp',
}
TEN_NHOM = {'DAT_NONG_NGHIEP': 'Đất nông nghiệp', 'DAT_O': 'Đất ở', 'DAT_TMDV': 'Đất TMDV', 'DAT_SXKD_KHOANGSAN': 'Đất SX-KD, khoáng sản'}
TEN_KET_CAU = {'NHUA_BETONG': 'Đường nhựa, bê tông', 'DAT_SOI_DA_CAPPHOI': 'Đường đất, đá, sỏi, cấp phối'}


def quet_co_tien_do(cha, files, ngu_canh: str = qc.AUTO, doc=None):
    """qc.quet kèm hộp tiến trình (bản scan nhận dạng chữ từng trang, bấm Hủy được). None: người dùng hủy."""
    from . import ocr
    from .man_hinh_quan_ly import doc_co_tien_do
    try:
        return doc_co_tien_do(cha, qc.quet, list(files), ngu_canh, doc=doc)
    except ocr.DaHuy:
        return None


def chon_va_quet(cha, ngu_canh: str = qc.AUTO, files=None, doc=None):
    """Hộp chọn file (hoặc files cho sẵn - kiểm thử) -> kết quả quét; None nếu không chọn / hủy."""
    if files is None:
        files, _ = QFileDialog.getOpenFileNames(cha, TEN_NGU_CANH.get(ngu_canh, 'Quét file'), '', qc.LOC_FILE)
    if not files:
        return None
    kq = quet_co_tien_do(cha, files, ngu_canh, doc)
    if kq is not None and kq.loi and not kq.co_du_lieu() and not getattr(cha, 'im_lang', False):
        QMessageBox.warning(cha, TIEU_DE, 'Không đọc được file:\n' + '\n'.join(kq.loi[:8]))
    return kq


class NutQuetChung(QPushButton):
    """UnifiedScanTriggerButton: một nút, một ngữ cảnh. Bấm -> chọn file -> quét -> phát tín hiệu da_quet(KetQuaQuet)."""
    da_quet = Signal(object)

    def __init__(self, nhan: str, ngu_canh: str = qc.AUTO, cha=None):
        super().__init__(nhan, cha)
        self.ngu_canh = ngu_canh
        self.kq = None
        self.setToolTip('Đọc file (PDF, Word, Excel, ảnh scan) ngay trên máy, không gửi dữ liệu ra ngoài. Kết quả hiện ra để xem trước khi áp dụng.')
        self.clicked.connect(lambda *_: self.quet())

    def quet(self, files=None, doc=None):
        kq = chon_va_quet(self.window(), self.ngu_canh, files, doc)
        if kq is not None:
            self.kq = kq
            self.da_quet.emit(kq)
        return kq


def _bang(cot: list, dong: list) -> QTableWidget:
    b = QTableWidget(len(dong), len(cot))
    b.setHorizontalHeaderLabels(cot)
    b.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    b.verticalHeader().setVisible(False)
    b.horizontalHeader().setStretchLastSection(True)
    for i, r in enumerate(dong):
        for j, v in enumerate(r):
            it = QTableWidgetItem(str(v))
            if isinstance(v, str) and v[:1].isdigit() and j > 1:
                it.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            b.setItem(i, j, it)
    b.resizeColumnsToContents()
    return b


class HopKetQuaQuet(QDialog):
    """Xem trước kết quả quét. self.hanh_dong sau khi đóng: '' | 'ghi_can_cu' | 'tinh_gia'."""
    im_lang = False

    def __init__(self, parent, kq: qc.KetQuaQuet, co_du_an: bool = False, chi_doc: bool = False):
        super().__init__(parent)
        self.kq, self.hanh_dong = kq, ''
        self.setWindowTitle(f'{TIEU_DE} - kết quả')
        self.resize(880, 560)
        lo = QVBoxLayout(self)
        dau = QLabel(f'Đã đọc {kq.so_file} file trong {kq.thoi_gian_ms} ms: {len(kq.can_cu)} văn bản căn cứ, {len(kq.dong_dat)} thửa đất, '
                     f'{len(kq.dong_tai_san)} hạng mục tài sản / cây trồng.' + (f'  Không đọc được {len(kq.loi)} file.' if kq.loi else ''))
        dau.setWordWrap(True)
        lo.addWidget(dau)
        self.tab = QTabWidget()
        lo.addWidget(self.tab, 1)
        self.o_can_cu = QPlainTextEdit()
        self.o_can_cu.setReadOnly(True)
        self.o_can_cu.setPlainText(vb.gop_va_sap_xep(kq.can_cu)[0] if kq.can_cu else '(Không thấy văn bản căn cứ trong file.)')
        self.tab.addTab(self.o_can_cu, f'Văn bản căn cứ ({len(kq.can_cu)})')
        self.b_dat = _bang(['Tờ', 'Thửa', 'Loại đất', 'Nhóm đất', 'Diện tích (m²)', 'Mặt đường'],
                           [(d.to_ban_do, d.so_thua, d.loai_dat, TEN_NHOM.get(d.nhom_dat, d.nhom_dat), vn(d.dien_tich_thu_hoi, 1),
                             TEN_KET_CAU.get(d.ket_cau_mat_duong, '')) for d in kq.dong_dat])
        self.tab.addTab(self.b_dat, f'Thửa đất ({len(kq.dong_dat)})')
        self.b_ts = _bang(['Nhóm', 'Tên tài sản / cây trồng', 'ĐVT', 'Khối lượng', 'Đơn giá', 'Thành tiền'],
                          [('Cây trồng' if t.danh_muc == 'CAY_TRONG_HOA_MAU' else 'Nhà & VKT', t.ten, t.dvt, vn(t.so_luong, 2), vn(t.don_gia),
                            vn(t.thanh_tien)) for t in kq.dong_tai_san])
        self.tab.addTab(self.b_ts, f'Tài sản, cây trồng ({len(kq.dong_tai_san)})')
        self.o_tom_tat = QPlainTextEdit()
        self.o_tom_tat.setReadOnly(True)
        dong = list(kq.tom_tat)
        if kq.tham_so:
            dong.append('Thông số nhận diện: ' + '; '.join(f'{k} = {v}' for k, v in kq.tham_so.items()))
        dong += [f'Không đọc được: {x}' for x in kq.loi]
        self.o_tom_tat.setPlainText('\n'.join(dong) or '(Không nhận dạng được nội dung nào.)')
        self.tab.addTab(self.o_tom_tat, 'Nhật ký quét')
        nut = QDialogButtonBox()
        self.b_ghi = QPushButton('Ghi văn bản căn cứ vào dự án')
        self.b_ghi.setEnabled(bool(kq.can_cu) and co_du_an and not chi_doc)
        self.b_ghi.setToolTip('Gộp vào mục Văn bản căn cứ của dự án, khử trùng lặp và sắp theo 13 bậc hiệu lực pháp lý')
        self.b_ghi.clicked.connect(lambda: self._chon('ghi_can_cu'))
        self.b_tinh = QPushButton('Mở bảng tính đơn giá đất…')
        self.b_tinh.setEnabled(bool(kq.tham_so or kq.dong_dat or kq.can_cu))
        self.b_tinh.clicked.connect(lambda: self._chon('tinh_gia'))
        nut.addButton(self.b_ghi, QDialogButtonBox.ButtonRole.ActionRole)
        nut.addButton(self.b_tinh, QDialogButtonBox.ButtonRole.ActionRole)
        dong_b = nut.addButton('Đóng', QDialogButtonBox.ButtonRole.RejectRole)
        dong_b.clicked.connect(self.reject)
        lo.addWidget(nut)

    def _chon(self, hanh_dong: str) -> None:
        self.hanh_dong = hanh_dong
        self.accept()

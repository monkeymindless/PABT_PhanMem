"""Hộp "Chẩn đoán & sửa lỗi hệ thống" (0.9.87, menu Trợ giúp): kiểm tra máy (thư mục dữ liệu, ổ đĩa, Excel, Tesseract, HTTPS),
kiểm tra / sửa file dự án (chua_benh_csdl) và xuất gói chẩn đoán .zip (dự án đã ẩn danh) gửi tác giả. Hộp báo lỗi không mong muốn
(giao_dien.cai_bat_loi) cũng có nút xuất gói này (xuat_goi_chan_doan)."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QLabel, QMessageBox, QPushButton,
                               QTableWidget, QWidget, QTableWidgetItem, QVBoxLayout)

from . import chua_benh_csdl, csdl

MAU_MUC = {'dat': '#047857', 'canh_bao': '#B45309', 'loi': '#B91C1C'}
CHU_MUC = {'dat': 'Đạt', 'canh_bao': 'Lưu ý', 'loi': 'Lỗi'}
NUT_GOI = 'Xuất gói chẩn đoán gửi tác giả (.zip)…'


def ten_goi_mac_dinh() -> str:
    return f'PABT_ChanDoan_{datetime.now():%Y%m%d_%H%M%S}.zip'


def xuat_goi_chan_doan(cha, file_pabt=None, loi_text: str = '', file_ra=None, im_lang: bool = False):
    """Hỏi nơi lưu rồi đóng gói (chua_benh_csdl.dong_goi_chan_doan). Trả đường dẫn .zip hoặc None (bỏ qua / lỗi)."""
    if file_ra is None:
        if im_lang:
            return None
        goc = str(Path(file_pabt).parent / ten_goi_mac_dinh()) if file_pabt else str(Path.home() / ten_goi_mac_dinh())
        file_ra, _ = QFileDialog.getSaveFileName(cha, 'Lưu gói chẩn đoán', goc, 'Gói ZIP (*.zip)')
        if not file_ra:
            return None
    from .giao_dien import con_tro_cho
    try:
        with con_tro_cho():
            kq = chua_benh_csdl.dong_goi_chan_doan(file_ra, file_pabt=file_pabt, loi_text=loi_text)
    except Exception as e:                              # noqa: BLE001 - báo lỗi, không ném tiếp từ hộp báo lỗi
        if not im_lang:
            from .thong_bao import chu_loi
            QMessageBox.warning(cha, 'Gói chẩn đoán', chu_loi('Không tạo được gói chẩn đoán', e))
        return None
    if not im_lang:
        QMessageBox.information(cha, 'Gói chẩn đoán', f'Đã tạo gói chẩn đoán:\n{kq}\n\nGói gồm thông tin máy, nhật ký lỗi, hồ sơ '
                                'địa phương' + (' và bản sao dự án ĐÃ ẨN DANH (không họ tên, CCCD, điện thoại, địa chỉ, nguồn gốc, '
                                                'ý kiến dân; giữ số liệu để tái hiện lỗi)' if file_pabt else '') + '.')
    return kq


class HopChanDoanHeThong(QDialog):
    """file_pabt: dự án đang mở (None: chưa mở). dong_du_an: hàm đóng dự án đang mở ở phần mềm (trả False nếu người dùng hủy) -
    sửa file phải đóng trước; mo_lai(file): mở lại sau khi sửa."""

    def __init__(self, cha=None, file_pabt=None, dong_du_an=None, mo_lai=None, im_lang: bool = False):
        super().__init__(cha)
        self.file_pabt = str(file_pabt) if file_pabt else None
        self.dong_du_an, self.mo_lai, self.im_lang = dong_du_an, mo_lai, im_lang
        self.ket_qua_sua = None
        self.setWindowTitle('Chẩn đoán & sửa lỗi hệ thống')
        self.resize(900, 520)
        lo = QVBoxLayout(self)
        tieu = QLabel('Kiểm tra máy đang dùng, kiểm tra / sửa file dự án và đóng gói thông tin gửi tác giả khi gặp lỗi.')
        tieu.setWordWrap(True)
        lo.addWidget(tieu)
        self.bang = QTableWidget(0, 4)
        self.bang.setHorizontalHeaderLabels(['Hạng mục', 'Kết quả', 'Chi tiết', 'Cách xử lý'])
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setWordWrap(True)
        for c, w in enumerate((220, 70, 300)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        lo.addWidget(self.bang, 1)
        self.lb_tep = QLabel()
        self.lb_tep.setWordWrap(True)
        self.lb_tep.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lo.addWidget(self.lb_tep)
        from .giao_dien import XepDong
        hang = QWidget()
        h = XepDong(hang, 8)                            # hẹp (màn hình 1366 @125%) thì nút xuống dòng, không ép hộp rộng ra
        h.setContentsMargins(0, 0, 0, 0)
        self.b_lai = QPushButton('Kiểm tra lại')
        self.b_sua = QPushButton('Kiểm tra && sửa file dự án…')
        self.b_goi = QPushButton(NUT_GOI)
        b_dong = QPushButton('Đóng')
        self.b_lai.clicked.connect(lambda: self.nap())
        self.b_sua.clicked.connect(lambda: self.sua_file())
        self.b_goi.clicked.connect(lambda: self.xuat_goi())
        b_dong.clicked.connect(self.reject)
        for b in (self.b_lai, self.b_sua, self.b_goi, b_dong):
            h.addWidget(b)
        lo.addWidget(hang)
        self.nap()

    def nap(self) -> list:
        ds = chua_benh_csdl.kiem_tra_moi_truong()
        self.bang.setRowCount(len(ds))
        for r, m in enumerate(ds):
            for c, chu in enumerate((m['ten'], CHU_MUC.get(m['muc'], m['muc']), m['chi_tiet'], m['cach_xu_ly'])):
                o = QTableWidgetItem(chu)
                o.setToolTip(chu)
                if c == 1:
                    o.setForeground(QColor(MAU_MUC.get(m['muc'], '#202124')))
                self.bang.setItem(r, c, o)
        self.bang.resizeRowsToContents()
        if self.file_pabt and Path(self.file_pabt).is_file():
            self.kiem_tra_file = chua_benh_csdl.kiem_tra_tep_pabt(self.file_pabt)
            self.lb_tep.setText(f'Dự án đang mở ({Path(self.file_pabt).name}): {self.kiem_tra_file["thong_bao"]}')
        else:
            self.kiem_tra_file = None
            self.lb_tep.setText('Chưa mở dự án: "Kiểm tra & sửa file dự án…" sẽ hỏi chọn file dự án (.larc).')
        return ds

    def _bao(self, chu: str, canh_bao: bool = False) -> None:
        if not self.im_lang:
            (QMessageBox.warning if canh_bao else QMessageBox.information)(self, 'Chẩn đoán & sửa lỗi', chu)

    def sua_file(self, duong_dan=None, xac_nhan: bool | None = None):
        """Sao lưu rồi sửa file (đóng dự án nếu đang mở, mở lại sau khi sửa). Trả kết quả chua_benh_csdl.sua_tep_pabt hoặc None."""
        f = duong_dan or self.file_pabt
        if not f:
            if self.im_lang:
                return None
            f, _ = QFileDialog.getOpenFileName(self, 'Chọn file dự án cần kiểm tra và sửa', '', csdl.LOC_MO)
            if not f:
                return None
        dang_mo = bool(self.file_pabt) and Path(f).resolve() == Path(self.file_pabt).resolve()
        if xac_nhan is None:
            if self.im_lang:
                xac_nhan = True
            else:
                xac_nhan = QMessageBox.question(
                    self, 'Sửa file dự án',
                    f'Sao lưu rồi sửa file:\n{f}\n\n' + ('Dự án đang mở sẽ được ĐÓNG trong lúc sửa và mở lại sau đó.\n\n' if dang_mo
                                                       else '') + 'Tiếp tục?') == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        if dang_mo and self.dong_du_an is not None and self.dong_du_an() is False:
            return None
        from .giao_dien import con_tro_cho
        try:
            with con_tro_cho():
                kq = chua_benh_csdl.sua_tep_pabt(f)
        except chua_benh_csdl.LoiSuaTep as e:
            self._bao(str(e), True)
            kq = None
        except Exception as e:                          # noqa: BLE001
            from .thong_bao import chu_loi
            self._bao(chu_loi('Không sửa được file dự án', e), True)
            kq = None
        if dang_mo and self.mo_lai is not None:
            self.mo_lai(f)
        if kq is not None:
            self.ket_qua_sua = kq
            self._bao('\n'.join(kq['hanh_dong'] + ['', kq['kiem_tra_sau']['thong_bao']]), not kq['thanh_cong'])
        self.nap()
        return kq

    def xuat_goi(self, file_ra=None):
        return xuat_goi_chan_doan(self, self.file_pabt, file_ra=file_ra, im_lang=self.im_lang)

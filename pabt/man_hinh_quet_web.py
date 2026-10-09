"""Màn hình "Cập nhật từ trang web": quét trang web / tìm trên Công báo Đồng Nai -> danh sách văn bản (đơn giá, chính sách bồi
thường, hỗ trợ) chấm mức liên quan, đánh dấu văn bản đã có -> tải, đọc (Word cũ qua Word, PDF scan qua OCR), phân tích số /
ngày / nhóm -> xem trước từng văn bản theo thứ tự ngày ban hành (văn bản sửa đổi áp sau văn bản gốc) -> áp dụng."""
from __future__ import annotations
import re
import tempfile

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox,
                               QProgressDialog, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import cap_nhat_web as cw, nhap_don_gia as ndg, ocr
from .lap_pa import LoiNhap
from .giao_dien import con_tro_cho
from .thong_bao import TEN_UD

KHOA_NHO = 'cap_nhat/nguon_web'
_MAY_NOI_BO = re.compile(r'(?i)^https?://(?:127\.|localhost\b|\[?::1\]?|0\.0\.0\.0)')   # máy chạy thử (kiểm thử): không nhớ
COT = ['Chọn', 'Văn bản', 'Số hiệu', 'Nhóm', 'Tình trạng', 'File']


def _ngay_sap_xep(vb: dict) -> tuple:
    m = re.fullmatch(r'(\d{2})/(\d{2})/(\d{4})', vb.get('ngay') or '')
    return (int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else (9999, 0, 0)


class HopQuetWeb(QDialog):
    im_lang = False             # kiểm thử: không hiện hộp thông báo; nội dung ở thong_bao_cuoi

    def __init__(self, parent=None, nguon: str = ''):
        super().__init__(parent)
        self.setWindowTitle('Cập nhật đơn giá, chính sách bồi thường từ trang web')
        self.resize(1250, 680)
        self.ds = []
        self.hop = []              # hộp xem trước đã tạo (cho=False, kiểm thử)
        self.ket_qua = []
        self.thong_bao_cuoi = ''
        lo = QVBoxLayout(self)
        hd = QLabel('Chọn nguồn có sẵn (Công báo Đồng Nai; văn bản Trung ương của Quốc hội, Chính phủ, Bộ ngành trên Cơ sở dữ liệu '
                    'quốc gia về văn bản pháp luật, Cổng văn bản Chính phủ, Công báo Chính phủ; Thư viện pháp luật), dán đường dẫn '
                    'trang web (cổng thông tin, trang văn bản, Google Drive...) hoặc gõ từ khóa rồi chọn nơi tìm. Phần mềm tự tìm '
                    'file văn bản, xếp theo mức liên quan tới đơn giá / bồi thường, hỗ trợ, tái định cư, đánh dấu văn bản đã có '
                    'và tự chọn văn bản mới. Văn bản quy định chính sách (luật, nghị định, thông tư...) không có bảng giá được ghi '
                    'vào danh mục văn bản căn cứ để theo dõi, đối chiếu.')
        hd.setWordWrap(True)
        lo.addWidget(hd)
        hang = QHBoxLayout()
        self.o_nguon = QComboBox()
        self.o_nguon.setEditable(True)
        self.o_nguon.setMinimumWidth(700)
        self.goi_y = cw.nguon_goi_y()
        for ten, tu_khoa in self.goi_y:
            self.o_nguon.addItem(ten, tu_khoa)
        for x in self._doc_nho():
            if self.o_nguon.findText(x) < 0:
                self.o_nguon.addItem(x, x)
        if nguon:
            self.o_nguon.setEditText(nguon)
        hang.addWidget(self.o_nguon, 1)
        hang.addWidget(QLabel('Từ khóa tìm trên:'))
        self.cb_noi = QComboBox()
        for k, (ten, _) in cw.noi_tim().items():
            self.cb_noi.addItem(ten.split(' (')[0].split(' - ')[0], k)
            self.cb_noi.setItemData(self.cb_noi.count() - 1, ten, Qt.ItemDataRole.ToolTipRole)
        self.cb_noi.setToolTip('Nơi tìm khi gõ từ khóa (nguồn có sẵn và đường dẫn trang web không phụ thuộc ô này)')
        hang.addWidget(self.cb_noi)
        self.b_quet = QPushButton('Quét')
        self.b_quet.clicked.connect(lambda: self.quet())
        hang.addWidget(self.b_quet)
        lo.addLayout(hang)
        self.c_loc = QCheckBox('Chỉ hiện văn bản liên quan đơn giá, bồi thường, hỗ trợ')
        self.c_loc.setChecked(True)
        self.c_loc.toggled.connect(self.hien)
        lo.addWidget(self.c_loc)
        self.bang = QTableWidget(0, len(COT))
        self.bang.setHorizontalHeaderLabels(COT)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        for c, w in enumerate((50, 560, 150, 140, 150, 150)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        lo.addWidget(self.bang, 1)
        self.lb = QLabel()
        self.lb.setWordWrap(True)
        lo.addWidget(self.lb)
        nut = QHBoxLayout()
        self.b_tai = QPushButton('Tải và phân tích các văn bản đã chọn')
        self.b_tai.clicked.connect(lambda: self.tai_va_phan_tich())
        self.b_tai.setEnabled(False)
        nut.addWidget(self.b_tai)
        nut.addStretch(1)
        dong = QPushButton('Đóng')
        dong.clicked.connect(self.accept)
        nut.addWidget(dong)
        lo.addLayout(nut)
        self._hien_ds = []

    def _bao(self, ham, chu):
        self.thong_bao_cuoi = chu
        if not self.im_lang:
            ham(self, TEN_UD, chu)

    def _nguon(self) -> str:
        chu = self.o_nguon.currentText().strip()
        i = self.o_nguon.findText(chu)
        return (self.o_nguon.itemData(i) if i >= 0 else None) or chu

    @staticmethod
    def _doc_nho() -> list:
        """Đường dẫn đã quét (QSettings), bỏ địa chỉ máy nội bộ (127.0.0.1... do chạy kiểm thử ghi vào) và dọn luôn."""
        try:
            cai = QSettings('PABT', 'PABT')
            nho = cai.value(KHOA_NHO, []) or []
            nho = [nho] if isinstance(nho, str) else [x for x in list(nho) if isinstance(x, str)]
            sach = [x for x in nho if x and not _MAY_NOI_BO.match(x)]
            if sach != nho:
                cai.setValue(KHOA_NHO, sach)
            return sach
        except Exception:
            return []

    def _nho(self, chu: str):
        if not chu or _MAY_NOI_BO.match(chu) or any(chu == tk for _, tk in self.goi_y):
            return
        try:
            cai = QSettings('PABT', 'PABT')
            cu = self._doc_nho()
            cai.setValue(KHOA_NHO, [chu] + [x for x in cu if x != chu][:9])
        except Exception:
            pass

    def quet(self, nguon: str | None = None) -> list:
        nguon = (nguon or self._nguon()).strip()
        if nguon.lower().split('?')[0].endswith('.json') and hasattr(self.parent(), 'cap_nhat_mang'):
            self.parent().cap_nhat_mang(nguon)          # thông báo cập nhật bộ đơn giá của đơn vị quản lý
            return []
        tien = QProgressDialog('Đang mở trang web…', 'Dừng', 0, 0, self)
        tien.setWindowTitle(TEN_UD)
        tien.setWindowModality(Qt.WindowModality.WindowModal)
        tien.setMinimumDuration(400)

        def bao(i, n, chu):
            tien.setMaximum(n)
            tien.setValue(i - 1)
            tien.setLabelText(f'Đang xem trang {i}/{n}: {chu[:80]}…')
            QApplication.processEvents()
            return tien.wasCanceled()
        try:
            with con_tro_cho():
                self.ds = cw.quet(nguon, bao=bao, noi=self.cb_noi.currentData() or 'dongnai')
        except LoiNhap as e:
            tien.close()
            self._bao(QMessageBox.warning, str(e))
            return []
        tien.close()
        self._nho(nguon if nguon.lower().startswith('http') else '')
        self.hien()
        if not self.ds:
            self._bao(QMessageBox.information, 'Không tìm thấy file văn bản nào. Thử từ khóa khác / nơi tìm khác, hoặc mở trang bằng '
                                               'trình duyệt và dán đường dẫn trang chi tiết văn bản. Một số trang (Thư viện pháp '
                                               'luật...) chỉ cho tải file khi đăng nhập hoặc dựng danh sách bằng JavaScript: tải file '
                                               'về máy rồi dùng "Cập nhật bộ đơn giá từ file…".')
        return self.ds

    def hien(self):
        self._hien_ds = [t for t in self.ds if not self.c_loc.isChecked() or t.diem > 0]
        self.bang.setRowCount(len(self._hien_ds))
        for i, t in enumerate(self._hien_ds):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked if t.chon else Qt.CheckState.Unchecked)
            self.bang.setItem(i, 0, chk)
            tinh_trang = 'Đã có trong bộ đơn giá' if t.da_co else ('MỚI' if t.so_hieu else 'Chưa rõ số hiệu')
            mau = QColor('#F5F5F5') if t.da_co else QColor('#E8F5E9') if t.chon else QColor('#FFFFFF')
            for c, v in enumerate((t.ten, t.so_hieu, cw.TEN_NHOM_VB.get(t.nhom, ''), tinh_trang, t.tep), start=1):
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                it.setToolTip(f'{t.ten}\nFile: {t.url}\nTrang: {t.trang}\nMức liên quan: {t.diem}')
                it.setBackground(QBrush(mau))
                self.bang.setItem(i, c, it)
        an = len(self.ds) - len(self._hien_ds)
        so_chon = sum(1 for t in self._hien_ds if t.chon)
        self.lb.setText(f'{len(self._hien_ds)} văn bản' + (f' (ẩn {an} không liên quan)' if an else '') +
                        f'; tự chọn {so_chon} văn bản mới. Văn bản giá đất cập nhật ở mục giá đất, không qua bộ đơn giá.')
        self.b_tai.setEnabled(bool(self._hien_ds))

    def chon_ds(self) -> list:
        return [t for i, t in enumerate(self._hien_ds) if self.bang.item(i, 0).checkState() == Qt.CheckState.Checked]

    def tai_va_phan_tich(self, cho: bool = True) -> list:
        """Tải các văn bản đã chọn, đọc, phân tích; xem trước từng văn bản theo ngày ban hành rồi áp dụng."""
        from .man_hinh_nhap_don_gia import HopNhapDonGia, mo_ta_van_ban
        from .man_hinh_quan_ly import doc_co_tien_do
        ds = self.chon_ds()
        if not ds:
            self._bao(QMessageBox.information, 'Chọn (đánh dấu cột "Chọn") văn bản cần tải.')
            return []
        td = tempfile.mkdtemp(prefix='pabt_web_')
        goi, loi = [], []
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for t in ds:
                try:
                    kq = cw.tai_ve(t.url, td)
                    if 'lien_ket' in kq:                # đường dẫn là trang: lấy file đầu tiên trên trang
                        kq = cw.tai_ve(kq['lien_ket'][0][1], td)
                    QApplication.restoreOverrideCursor()
                    dong = doc_co_tien_do(self, ndg.doc_bang_ocr, kq['file'])
                    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                    vb = ndg.phan_tich_van_ban(dong, t.ten)
                    goi.append((vb, kq['file'], dong, t))
                except ocr.DaHuy:
                    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                    loi.append(f'{t.ten[:80]}: đã hủy nhận dạng chữ')
                except (LoiNhap, ocr.LoiOCR, OSError, ValueError, KeyError) as e:
                    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                    loi.append(f'{t.ten[:80]}: {e}')
        finally:
            QApplication.restoreOverrideCursor()
        goi.sort(key=lambda x: _ngay_sap_xep(x[0]))      # văn bản sửa đổi (ban hành sau) áp sau văn bản gốc
        xong = []
        for vb, f, dong, t in goi:
            nguon = mo_ta_van_ban(vb) or t.ten
            try:
                d = HopNhapDonGia(f, self, nguon, dong=dong, van_ban=vb)
            except ndg.LoiKhongCoGia:
                # không có đơn giá (không bảng, không câu ghi giá): văn bản quy định chính sách -> ghi vào danh mục văn bản căn
                # cứ để theo dõi
                if vb.get('so_hieu') and not ndg.da_co(vb['so_hieu']) and (self.im_lang or QMessageBox.question(
                        self, TEN_UD, f'{nguon}\n{vb.get("trich_yeu", "")}\n\nVăn bản không ghi đơn giá (văn bản quy định '
                                      'chính sách): phần mềm không tự đổi quy tắc tính. Ghi văn bản vào danh mục văn bản căn cứ '
                                      'của bộ đơn giá để theo dõi, đối chiếu?') == QMessageBox.StandardButton.Yes):
                    try:
                        xong.append(ndg.ap_dung([], None, nguon, van_ban=vb))
                    except LoiNhap as e:
                        loi.append(f'{nguon}: {e}')
                else:
                    loi.append(f'{nguon}: không tìm thấy đơn giá (không có bảng giá, không có câu ghi "… đồng/<đơn vị>")'
                               + (' - văn bản đã có trong danh mục văn bản căn cứ' if ndg.da_co(vb.get('so_hieu', '')) else ''))
                continue
            except LoiNhap as e:                        # lỗi khác (đọc bộ đơn giá, so khớp…): báo đúng lý do
                loi.append(f'{nguon}: {e}')
                continue
            d.im_lang = self.im_lang
            if not cho:
                self.hop.append(d)
                continue
            if d.exec() and d.ket_qua:
                xong.append(d.ket_qua)
        self.ket_qua += xong
        if xong or loi:
            self._bao(QMessageBox.warning if loi else QMessageBox.information,
                      (f'Đã cập nhật {len(xong)} văn bản vào bộ đơn giá.' if xong else 'Chưa cập nhật văn bản nào.') +
                      ('\n\nKhông xử lý được:\n' + '\n'.join('- ' + x for x in loi) if loi else ''))
        if xong and self.ds:                            # đánh dấu lại văn bản đã có
            co = ndg.van_ban_da_co()
            for t in self.ds:
                t.da_co = ndg.da_co(t.so_hieu, co)
                t.chon = t.chon and not t.da_co
            self.hien()
        return goi

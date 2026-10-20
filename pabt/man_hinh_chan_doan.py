"""Hộp "Chẩn đoán & sửa lỗi hệ thống" (0.9.87, menu Trợ giúp): kiểm tra máy (thư mục dữ liệu, ổ đĩa, Excel, Tesseract, HTTPS),
kiểm tra / sửa file dự án (chua_benh_csdl) và xuất gói chẩn đoán .zip (dự án đã ẩn danh) gửi tác giả. Hộp báo lỗi không mong muốn
(giao_dien.cai_bat_loi) cũng có nút xuất gói này (xuat_goi_chan_doan)."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import chua_benh_csdl, csdl

MAU_MUC = {'dat': '#047857', 'canh_bao': '#B45309', 'loi': '#B91C1C'}
CHU_MUC = {'dat': 'Đạt', 'canh_bao': 'Lưu ý', 'loi': 'Lỗi'}
NUT_GOI = 'Xuất gói chẩn đoán ẩn danh gửi tác giả (.zip)…'
# 20/10/2026 (ảnh mẫu người dùng): 5 chỉ số kiểm toán kỹ thuật (khóa, mã chỉ số, nhãn) + 4 nút bảo trì 1-click (việc chua_benh_csdl.
# sua_tep_pabt, chữ nút, biểu tượng Segoe MDL2) - không emoji (Win 7)
CHI_SO = (('khoa', '1. Trạng thái tệp khóa CSDL (.khoa)'), ('toan_ven', '2. Kiểm tra toàn vẹn CSDL (integrity_check)'),
          ('khoa_ngoai', '3. Ràng buộc khóa ngoại (foreign_key_check)'), ('luoc_do', '4. Phiên bản lược đồ CSDL'),
          ('office', '5. Kết nối MS Excel & bộ dựng PDF'))
NUT_BAO_TRI = (('go_khoa', 'Gỡ tệp khóa (.khoa) bị kẹt', 0xE785), ('toi_uu', 'Tối ưu CSDL (VACUUM + REINDEX)', 0xE945),
               ('cuu', 'Cứu hộ CSDL hỏng (chép dữ liệu)', 0xE90F), ('nang_cap', 'Nâng cấp CSDL lên v{v}', 0xE777))
TIEU_DE_BAO_TRI = {'go_khoa': 'Gỡ tệp khóa bị kẹt', 'toi_uu': 'Tối ưu CSDL', 'cuu': 'Cứu hộ CSDL hỏng', 'nang_cap': 'Nâng cấp lược đồ',
                   'tat_ca': 'Kiểm tra & sửa file dự án'}


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
    sửa file phải đóng trước; mo_lai(file): mở lại sau khi sửa.
    20/10/2026 (ảnh mẫu): trái = 5 chỉ số kiểm toán kỹ thuật (thẻ nhỏ màu) + bảng kiểm tra máy trạm; phải = 4 nút bảo trì 1-click
    (bao_tri -> chua_benh_csdl.sua_tep_pabt(viec=)) + hộp đen "Xuất gói chẩn đoán ẩn danh"."""

    def __init__(self, cha=None, file_pabt=None, dong_du_an=None, mo_lai=None, im_lang: bool = False):
        super().__init__(cha)
        self.file_pabt = str(file_pabt) if file_pabt else None
        self.dong_du_an, self.mo_lai, self.im_lang = dong_du_an, mo_lai, im_lang
        self.ket_qua_sua = None
        self.kiem_tra_file = None
        self.setWindowTitle('Bác sĩ kỹ thuật CSDL & chẩn đoán máy trạm')
        self.resize(1000, 620)
        from .giao_dien import icon_ky_hieu, KieuNut, ap_kieu_nut
        lo = QVBoxLayout(self)
        tieu = QLabel('Kiểm toán tình trạng kỹ thuật của file dự án và máy đang dùng, công cụ cứu hộ / bảo trì một lần bấm, đóng gói '
                      'thông tin (đã ẩn danh) gửi tác giả khi gặp lỗi.')
        tieu.setWordWrap(True)
        lo.addWidget(tieu)
        cot = QHBoxLayout()
        cot.setSpacing(10)
        # ---- trái: 5 chỉ số + bảng máy trạm
        trai = QVBoxLayout()
        k_cs = QFrame()
        k_cs.setObjectName('khung_chi_so_cd')
        lcs = QGridLayout(k_cs)
        lcs.setContentsMargins(10, 8, 10, 8)
        lcs.setVerticalSpacing(5)
        td = QLabel('KẾT QUẢ KIỂM TOÁN TÌNH TRẠNG KỸ THUẬT (5 CHỈ SỐ):')
        td.setProperty('vai', 'tieu_de')
        td.setWordWrap(True)
        lcs.addWidget(td, 0, 0, 1, 2)
        self.the_chi_so = {}
        for r, (k, nhan) in enumerate(CHI_SO, start=1):
            lb = QLabel(nhan)
            lb.setWordWrap(True)                        # màn hình hẹp / chữ to: xuống dòng, không ép hộp rộng ra
            lcs.addWidget(lb, r, 0)
            t = QLabel('')
            t.setProperty('the_nho', 'xam')
            lcs.addWidget(t, r, 1, Qt.AlignmentFlag.AlignRight)
            self.the_chi_so[k] = t
        lcs.setColumnStretch(0, 1)
        trai.addWidget(k_cs)
        nhan = QLabel('Kiểm tra máy trạm:')
        nhan.setProperty('vai', 'nhan')
        trai.addWidget(nhan)
        self.bang = QTableWidget(0, 4)
        self.bang.setHorizontalHeaderLabels(['Hạng mục', 'Kết quả', 'Chi tiết', 'Cách xử lý'])
        self.bang.verticalHeader().setVisible(False)
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setWordWrap(True)
        for c, w in enumerate((190, 60, 220)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.setMinimumHeight(120)
        trai.addWidget(self.bang, 1)
        self.lb_tep = QLabel()
        self.lb_tep.setWordWrap(True)
        self.lb_tep.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        trai.addWidget(self.lb_tep)
        # ---- phải: nút bảo trì 1-click + hộp đen
        phai = QVBoxLayout()
        td = QLabel('CÔNG CỤ CỨU HỘ & BẢO TRÌ 1-CLICK:')
        td.setProperty('vai', 'tieu_de')
        td.setWordWrap(True)
        phai.addWidget(td)
        luoi = QGridLayout()
        luoi.setSpacing(6)
        self.nut_bao_tri = {}
        from . import csdl as _csdl
        for i, (viec, chu, ky) in enumerate(NUT_BAO_TRI):
            b = QPushButton(chu.format(v=_csdl.PHIEN_BAN_CSDL))
            b.setProperty('khong_icon', True)
            ic = icon_ky_hieu(ky, '#0F3866', 16)
            if ic is not None:
                b.setIcon(ic)
            b.setMinimumHeight(34)
            b.setMinimumWidth(120)                      # không lấy độ dài chữ làm bề rộng tối thiểu (hộp <= 1024 px)
            b.clicked.connect(lambda _=False, v=viec: self.bao_tri(v))
            luoi.addWidget(b, i, 0)                     # một nút một hàng: cột phải hẹp (1366 @125%) không cắt chữ
            self.nut_bao_tri[viec] = b
        self.nut_bao_tri['go_khoa'].setToolTip('Gỡ tệp khóa còn sót khi máy tắt đột ngột (khóa đang có hiệu lực ở máy khác thì không gỡ).')
        self.nut_bao_tri['toi_uu'].setToolTip('Sao lưu rồi dựng lại chỉ mục (REINDEX) và nén gọn file (VACUUM).')
        self.nut_bao_tri['cuu'].setToolTip('File có trang dữ liệu hỏng: sao lưu rồi chép mọi dòng đọc được của từng bảng sang file mới.')
        self.nut_bao_tri['nang_cap'].setToolTip('Sao lưu rồi mở bằng phần mềm một lần để nâng cấp lược đồ lên bản mới nhất.')
        phai.addLayout(luoi)
        hop = QFrame()
        hop.setObjectName('khung_hop_den')
        lh = QVBoxLayout(hop)
        lh.setContentsMargins(10, 8, 10, 10)
        td = QLabel('HỘP ĐEN CHẨN ĐOÁN LỖI ẨN DANH (GỬI TÁC GIẢ):')
        td.setObjectName('tieu_de_hop_den')
        td.setWordWrap(True)
        lh.addWidget(td)
        mt = QLabel('Khi gặp sự cố kỹ thuật phức tạp, bấm nút dưới đây để tạo gói <b>.zip ẩn danh</b>: tự đổi tên họ, xóa CCCD, điện '
                    'thoại, địa chỉ, nguồn gốc, ý kiến dân nhưng giữ nguyên số liệu để tái hiện lỗi, kèm nhật ký lỗi <b>loi.log</b> '
                    'và thông tin máy.')
        mt.setWordWrap(True)
        mt.setObjectName('mo_ta_hop_den')
        lh.addWidget(mt)
        self.b_goi = QPushButton(NUT_GOI)
        self.b_goi.setObjectName('nut_goi_chan_doan')
        self.b_goi.setProperty('khong_icon', True)
        self.b_goi.setMinimumHeight(34)
        self.b_goi.setMinimumWidth(160)
        self.b_goi.clicked.connect(lambda: self.xuat_goi())
        lh.addWidget(self.b_goi)
        phai.addWidget(hop)
        phai.addStretch(1)
        cot.addLayout(trai, 3)
        cot.addLayout(phai, 2)
        lo.addLayout(cot, 1)
        h = QHBoxLayout()
        self.b_lai = QPushButton('Kiểm tra lại')
        self.b_lai.clicked.connect(lambda: self.nap())
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        ap_kieu_nut(b_dong, KieuNut.PHU)
        h.addWidget(self.b_lai)
        h.addStretch(1)
        h.addWidget(b_dong)
        lo.addLayout(h)
        self.nap()

    def _dat_chi_so(self, k: str, chu: str, loai: str, goi_y: str = '') -> None:
        from .giao_dien import dat_the_nho
        t = self.the_chi_so[k]
        t.setText(chu)
        t.setToolTip(goi_y or chu)
        dat_the_nho(t, loai)

    def chi_so(self) -> dict:
        """{khóa CHI_SO: (chữ, loại thẻ)} - đang hiện."""
        return {k: (t.text(), t.property('the_nho')) for k, t in self.the_chi_so.items()}

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
            self.lb_tep.setText('Chưa mở dự án: các nút bảo trì sẽ hỏi chọn file dự án (.larc).')
        self._ve_chi_so(ds)
        return ds

    def _ve_chi_so(self, moi_truong: list) -> None:
        """5 chỉ số + bật / tắt nút bảo trì theo kết quả kiểm tra file (chưa mở dự án: chỉ số file "Chưa mở dự án", nút vẫn bật -
        bấm thì chọn file)."""
        v = csdl.PHIEN_BAN_CSDL
        f = self.kiem_tra_file
        if f is None:
            for k in ('khoa', 'toan_ven', 'khoa_ngoai', 'luoc_do'):
                self._dat_chi_so(k, 'Chưa mở dự án', 'xam')
            for b in self.nut_bao_tri.values():
                b.setEnabled(True)
        else:
            k = f['khoa']
            if k is None:
                self._dat_chi_so('khoa', 'Không bị kẹt khóa', 'xanh')
            elif k['con_hieu_luc']:
                self._dat_chi_so('khoa', 'Đang mở để sửa', 'vang', f'Đang được mở để sửa ở {k["mo_ta"]}')
            else:
                self._dat_chi_so('khoa', 'Khóa cũ bị kẹt', 'do', 'Còn tệp khóa của lần mở trước bị tắt đột ngột - bấm "Gỡ tệp khóa".')
            n = len(f['loi_toan_ven'])
            self._dat_chi_so('toan_ven', 'OK (0 trang lỗi)' if not n else f'{n} lỗi toàn vẹn', 'xanh' if not n else 'do',
                             '\n'.join(f['loi_toan_ven'][:10]))
            n = len(f['loi_khoa_ngoai'])
            self._dat_chi_so('khoa_ngoai', 'Khớp 100%' if not n else f'{n} dòng lệch', 'xanh' if not n else 'vang',
                             '\n'.join(f['loi_khoa_ngoai'][:10]))
            pv = f['phien_ban']
            if pv == v:
                self._dat_chi_so('luoc_do', f'v{pv} (chuẩn phần mềm)', 'lam')
            elif pv < v:
                self._dat_chi_so('luoc_do', f'v{pv} - cần nâng cấp lên v{v}', 'vang')
            else:
                self._dat_chi_so('luoc_do', f'v{pv} - mới hơn phần mềm (v{v})', 'do', 'File tạo bằng phiên bản mới hơn: cập nhật phần mềm.')
            self.nut_bao_tri['go_khoa'].setEnabled(bool(k) and not k['con_hieu_luc'])
            self.nut_bao_tri['toi_uu'].setEnabled(not f['loi_toan_ven'] and pv <= v)
            self.nut_bao_tri['cuu'].setEnabled(bool(f['loi_toan_ven']))
            self.nut_bao_tri['nang_cap'].setEnabled(pv < v)
        excel = next((m for m in moi_truong if m['ma'] == 'excel'), None)
        from .xem_truoc_tai_lieu import co_qtpdf
        co_ex, co_pdf = bool(excel and excel['muc'] == 'dat'), co_qtpdf()
        if co_ex and co_pdf:
            self._dat_chi_so('office', 'Sẵn sàng (Excel + QtPdf)', 'xanh')
        elif co_ex:
            self._dat_chi_so('office', 'Có Excel (xem trước: mở ngoài)', 'vang', 'Bản Qt 5 không có QtPdf: xem trước A4 mở bằng trình xem PDF.')
        else:
            self._dat_chi_so('office', 'Chỉ bộ dựng PDF dự phòng', 'vang', excel['cach_xu_ly'] if excel else '')

    def _bao(self, chu: str, canh_bao: bool = False) -> None:
        if not self.im_lang:
            (QMessageBox.warning if canh_bao else QMessageBox.information)(self, 'Chẩn đoán & sửa lỗi', chu)

    def sua_file(self, duong_dan=None, xac_nhan: bool | None = None):
        """Sao lưu rồi sửa file - mọi bước (đóng dự án nếu đang mở, mở lại sau khi sửa). Trả kết quả sua_tep_pabt hoặc None."""
        return self.bao_tri('tat_ca', duong_dan, xac_nhan)

    def bao_tri(self, viec: str, duong_dan=None, xac_nhan: bool | None = None):
        """Một việc bảo trì (chua_benh_csdl.VIEC_SUA) trên file dự án đang mở hoặc file chọn. Dự án đang mở: đóng trước, mở lại sau.
        Trả kết quả chua_benh_csdl.sua_tep_pabt hoặc None (hủy / không làm được - đã báo)."""
        f = duong_dan or self.file_pabt
        ten = TIEU_DE_BAO_TRI.get(viec, viec)
        if not f:
            if self.im_lang:
                return None
            f, _ = QFileDialog.getOpenFileName(self, f'{ten}: chọn file dự án', '', csdl.LOC_MO)
            if not f:
                return None
        dang_mo = bool(self.file_pabt) and Path(f).resolve() == Path(self.file_pabt).resolve()
        if xac_nhan is None:
            if self.im_lang:
                xac_nhan = True
            else:
                xac_nhan = QMessageBox.question(
                    self, ten, (f'{ten}:\n{f}\n\n' + ('Sao lưu bản gốc trước khi làm. ' if viec != 'go_khoa' else '') +
                                ('Dự án đang mở sẽ được ĐÓNG trong lúc làm và mở lại sau đó.\n\n' if dang_mo else '\n') +
                                'Tiếp tục?')) == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        if dang_mo and self.dong_du_an is not None and self.dong_du_an() is False:
            return None
        from .giao_dien import con_tro_cho
        try:
            with con_tro_cho():
                kq = chua_benh_csdl.sua_tep_pabt(f, viec=viec)
        except chua_benh_csdl.LoiSuaTep as e:
            self._bao(str(e), True)
            kq = None
        except Exception as e:                          # noqa: BLE001
            from .thong_bao import chu_loi
            self._bao(chu_loi(f'{ten} không thành công', e), True)
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

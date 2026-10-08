"""Màn hình "Bộ đơn giá": xem (chỉ đọc) danh mục đơn giá, chính sách hỗ trợ, tham số - hạn mức, biểu thưởng, văn bản căn cứ;
cập nhật bộ đơn giá từ file hoặc qua Internet; tra cứu văn bản mới; áp bộ đơn giá vào dự án đang mở."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QMenu, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from . import csdl, don_gia
from .lap_pa import LoiNhap, bo_dau
from .tien import vn

TEN_UD = 'PABT - Lập phương án bồi thường, hỗ trợ'
THE = [
    ('Đơn giá tài sản, cây trồng', 'SELECT ma, phan_loai, ten, dvt, don_gia, ghi_chu FROM dm_taisan',
     ['Mã', 'Phân loại', 'Tên', 'ĐVT', 'Đơn giá (đ)', 'Ghi chú'], [70, 240, 420, 70, 110, 300]),
    ('Chính sách hỗ trợ (QĐ 42/2025)', 'SELECT ma, ten, dvt, don_gia, can_cu, cach_tinh FROM dm_hotro',
     ['Mã', 'Khoản hỗ trợ', 'ĐVT', 'Đơn giá / hệ số', 'Căn cứ', 'Cách tính'], [55, 420, 90, 110, 330, 330]),
    ('Tham số, hạn mức đất NN', 'SELECT ma, ten, gia_tri, dvt, can_cu, trang_thai FROM tham_so',
     ['Mã', 'Tham số', 'Giá trị', 'ĐVT', 'Căn cứ', 'Trạng thái'], [120, 430, 90, 90, 330, 160]),
    ('Thưởng bàn giao mặt bằng', 'SELECT tu, muc FROM bieu_thuong ORDER BY CAST(tu AS REAL)',
     ['Tổng bồi thường, hỗ trợ từ (đ)', 'Mức thưởng (đ/hộ)'], [220, 180]),
    ('Quy ước giá tương đương', 'SELECT ten_thuc_te, ten_tuong_duong, dvt, don_gia, can_cu FROM quy_uoc',
     ['Tên thực tế', 'Áp giá tương đương', 'ĐVT', 'Đơn giá', 'Căn cứ'], [260, 300, 70, 110, 330]),
    ('Văn bản căn cứ', 'SELECT so_hieu, co_quan, noi_dung, trang_thai FROM van_ban ORDER BY id',
     ['Văn bản', 'Cơ quan', 'Nội dung áp dụng', 'Trạng thái'], [380, 200, 440, 230]),
]


class HopBoDonGia(QDialog):

    im_lang = False             # True: không hiện hộp thông báo (kiểm thử); nội dung lưu ở thong_bao_cuoi

    def _bao(self, ham, chu):
        self.thong_bao_cuoi = chu
        if not self.im_lang:
            ham(self, TEN_UD, chu)
    def __init__(self, parent=None, con_du_an=None, chi_doc: bool = False):
        super().__init__(parent)
        self.con_du_an = con_du_an
        self.chi_doc = chi_doc
        self.da_ap = False
        self.setWindowTitle('Bộ đơn giá bồi thường, hỗ trợ, tái định cư')
        self.resize(1300, 720)
        self.lb = QLabel()
        self.lb.setProperty('vai', 'bang_ten')
        self.lb.setWordWrap(True)
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Tìm trong thẻ đang xem (không cần dấu): xoai, nha cap 4, HT09…')
        self.o_tim.textChanged.connect(self.loc)
        self.the = QTabWidget()
        nut = QHBoxLayout()
        for ten, ham in (('Cập nhật bộ đơn giá từ file…', lambda: self.cap_nhat_file()),
                         ('Cập nhật từ trang web…', lambda: self.cap_nhat_web()),
                         ('Tra cứu văn bản mới…', lambda: self.tra_cuu()),
                         ('Tra bảng giá đất NQ 28/2025…', lambda: self.xem_gia_dat()),
                         ('Xuất bảng giá đất ra Excel…', lambda: self.xuat_gia_dat()),
                         ('Đơn giá riêng của dự án…', lambda: self.don_gia_rieng()),
                         ('Áp bộ đơn giá vào dự án đang mở', lambda: self.ap_du_an())):
            b = QPushButton(ten)
            b.clicked.connect(ham)
            nut.addWidget(b)
            setattr(self, 'b_' + bo_dau(ten).split()[0], b)
        nut.addStretch(1)
        dong = QPushButton('Đóng')
        dong.clicked.connect(self.accept)
        nut.addWidget(dong)
        self.b_ap.setEnabled(con_du_an is not None and not chi_doc)
        self.b_don.setEnabled(con_du_an is not None)
        self.b_don.setToolTip('Quy ước giá tương đương nhập tay, đơn giá thẩm định giá (tài sản đặc biệt) của dự án đang mở')
        lo = QVBoxLayout(self)
        lo.addWidget(self.lb)
        lo.addWidget(self.o_tim)
        lo.addWidget(self.the, 1)
        lo.addLayout(nut)
        self.nap()

    def nap(self):
        tt = don_gia.thong_tin()
        self.lb.setText(f'<b>{tt["ten"]}</b> – phiên bản <b>{tt["phien_ban"]}</b> (nguồn {tt["nguon"]}, đóng gói {tt["ngay"][:10]})<br>'
                        f'{tt["ghi_chu"]}<br>Danh mục, chính sách, tham số được cố định; chỉ cập nhật bằng các nút bên dưới.')
        self.the.clear()
        con = csdl.mo(tt['file'], chi_doc=True)
        try:
            for ten, sql, cot, rong in THE:
                ds = con.execute(sql).fetchall()
                b = QTableWidget(len(ds), len(cot))
                b.setHorizontalHeaderLabels(cot)
                b.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                b.setAlternatingRowColors(True)
                b.verticalHeader().setVisible(False)
                for c, w in enumerate(rong):
                    b.setColumnWidth(c, w)
                b.horizontalHeader().setStretchLastSection(True)
                for r, dong in enumerate(ds):
                    for c, v in enumerate(dong):
                        s = '' if v is None else str(v)
                        if cot[c].startswith(('Đơn giá', 'Mức thưởng', 'Tổng bồi')) and s.replace('.', '').isdigit() and float(s) >= 100:
                            s = vn(s)
                        it = QTableWidgetItem(s)
                        it.setToolTip(s)
                        b.setItem(r, c, it)
                self.the.addTab(b, f'{ten} ({len(ds)})')
        finally:
            con.close()

    def don_gia_rieng(self, cho: bool = True):
        """Quy ước tương đương / đơn giá thẩm định riêng của dự án đang mở (bộ đơn giá chung vẫn cố định)."""
        from .man_hinh_don_gia_rieng import HopDonGiaRieng
        if self.con_du_an is None:
            return None
        d = HopDonGiaRieng(self.con_du_an, self, chi_doc=self.chi_doc)
        d.im_lang = self.im_lang
        if not cho:
            return d
        d.exec()
        if d.da_luu:
            self.da_ap = True                           # cửa sổ chính dựng lại danh mục của dự án
        return d

    def loc(self, chu: str):
        b = self.the.currentWidget()
        k = bo_dau(chu)
        for r in range(b.rowCount()):
            dong = bo_dau(' '.join(b.item(r, c).text() for c in range(b.columnCount()) if b.item(r, c)))
            b.setRowHidden(r, bool(k) and not all(x in dong for x in k.split()))

    def cap_nhat_file(self, p=None):
        if p is None:
            p, _ = QFileDialog.getOpenFileName(self, 'Chọn file đơn giá', '',
                                               'File đơn giá (*.xlsx *.xlsm *.docx *.pdf *.csv *.sqlite);;Tất cả (*.*)')
            if not p:
                return None
        from .nhap_tho import la_file_pabt
        if Path(p).suffix.lower() != '.sqlite' and not (Path(p).suffix.lower() in ('.xlsx', '.xlsm') and la_file_pabt(p)):
            return self.cap_nhat_file_bat_ky(p)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            tt = don_gia.cap_nhat_tu_file(p)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            self._bao(QMessageBox.warning, f'Không cập nhật được:\n{e}')
            return None
        QApplication.restoreOverrideCursor()
        self.nap()
        self._bao(QMessageBox.information, f'Đã cập nhật bộ đơn giá phiên bản {tt["phien_ban"]}. Dự án mới dùng bộ này; '
                                              'dự án đang lập muốn đổi thì bấm "Áp bộ đơn giá vào dự án đang mở".')
        return tt

    def cap_nhat_file_bat_ky(self, p, nguon: str = '', cho: bool = True):
        """File Excel / Word / PDF / CSV bất kỳ: xem trước các dòng đơn giá rồi áp dụng."""
        from . import nhap_don_gia as ndg, ocr
        from .man_hinh_nhap_don_gia import HopNhapDonGia
        from .man_hinh_quan_ly import doc_co_tien_do
        try:
            dong = doc_co_tien_do(self, ndg.doc_bang_ocr, p)        # PDF scan: nhận dạng chữ từng trang, có nút Hủy
            d = HopNhapDonGia(p, self, nguon, dong=dong)
        except ocr.DaHuy:
            return None
        except (LoiNhap, ocr.LoiOCR, OSError, ValueError) as e:
            self._bao(QMessageBox.warning, str(e))
            return None
        d.im_lang = self.im_lang
        if not cho:
            return d
        if d.exec() and d.ket_qua:
            self.nap()
        return d.ket_qua

    def cap_nhat_web(self, url=None, cho: bool = True):
        """Quét trang web / tìm trên Công báo Đồng Nai, tải và phân tích văn bản đơn giá, chính sách (HopQuetWeb).
        Đường dẫn thông báo cập nhật bộ đơn giá (.json) đi theo cap_nhat_mang."""
        if url and url.strip().lower().split('?')[0].endswith('.json'):
            return self.cap_nhat_mang(url.strip())
        try:
            from .man_hinh_quet_web import HopQuetWeb   # phát hành riêng bằng gói cập nhật, không có trong bộ cài gốc
        except ImportError:
            self._bao(QMessageBox.information,
                      'Tính năng "Cập nhật từ trang web" (tự quét Công báo Đồng Nai, tải và phân tích văn bản đơn giá, chính '
                      'sách) được phát hành riêng bằng gói cập nhật phần mềm (PABT_CapNhat_<phiên bản>.pabtcn), không có sẵn '
                      'trong bộ cài.\n\nCài gói: bấm đúp file .pabtcn, hoặc nút "Cập nhật phần mềm" ở góc dưới bên phải → '
                      '"Cập nhật từ file…", rồi mở lại PABT.\n\nVẫn cập nhật được từ file đã tải về máy: "Cập nhật bộ đơn giá '
                      'từ file…".')
            return None
        d = HopQuetWeb(self, url or '')
        d.im_lang = self.im_lang
        if url:
            d.quet(url)
        if not cho:
            return d
        d.exec()
        if d.ket_qua:
            self.nap()
        return d.ket_qua

    def cap_nhat_mang(self, url=None):
        if url is None:
            return self.cap_nhat_web()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            tb = don_gia.kiem_tra_mang(url.strip())
            if tb is None:
                QApplication.restoreOverrideCursor()
                self._bao(QMessageBox.information, 'Bộ đơn giá đang dùng là mới nhất.')
                return None
            QApplication.restoreOverrideCursor()
            if QMessageBox.question(self, TEN_UD, f'Có bộ đơn giá phiên bản {tb["phien_ban"]}.\n{tb.get("ghi_chu", "")}\n\nTải và cài?') \
                    != QMessageBox.StandardButton.Yes:
                return None
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            tt = don_gia.tai_va_cai(tb)
        except LoiNhap as e:
            QApplication.restoreOverrideCursor()
            self._bao(QMessageBox.warning, str(e))
            return None
        QApplication.restoreOverrideCursor()
        self.nap()
        self._bao(QMessageBox.information, f'Đã cài bộ đơn giá phiên bản {tt["phien_ban"]}.')
        return tt

    def tra_cuu(self):
        m = QMenu(self)
        for ten, url in don_gia.TRA_CUU:
            m.addAction(ten, lambda u=url: QDesktopServices.openUrl(QUrl(u)))
        m.exec(self.cursor().pos())

    def xem_gia_dat(self, cho: bool = True):
        from .man_hinh_gia_dat import HopTraGiaDat
        d = HopTraGiaDat(self, chi_xem=True)
        if cho:
            d.exec()
        return d

    def xuat_gia_dat(self, p=None):
        from . import gia_dat_nq28 as nq
        if p is None:
            p, _ = QFileDialog.getSaveFileName(self, 'Lưu bảng giá đất', 'BANG_GIA_DAT_NQ28_2025.xlsx', 'File Excel (*.xlsx)')
            if not p:
                return None
        try:
            f = nq.xuat_excel(p)
        except OSError as e:
            self._bao(QMessageBox.warning, f'Không ghi được file (đang mở trong Excel?):\n{e}')
            return None
        self._bao(QMessageBox.information, f'Đã lưu bảng giá đất:\n{f}')
        return f

    def ap_du_an(self, xac_nhan=None):
        if self.con_du_an is None or self.chi_doc:
            return None
        if xac_nhan is None:
            xac_nhan = QMessageBox.question(self, TEN_UD, 'Thay danh mục đơn giá, chính sách, tham số của dự án đang mở bằng bộ đơn giá '
                                                          'này? Hồ sơ hộ, thửa, giá đất và phương án đã lập giữ nguyên (dòng đã lập '
                                                          'giữ đơn giá cũ; dùng Rà soát giá để kiểm tra).') == QMessageBox.StandardButton.Yes
        if not xac_nhan:
            return None
        tt = don_gia.ap_vao_du_an(self.con_du_an)
        self.da_ap = True
        self._bao(QMessageBox.information, f'Đã áp bộ đơn giá phiên bản {tt["phien_ban"]} vào dự án.')
        return tt

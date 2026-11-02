"""Hộp "Dán danh sách tài sản": dán / gõ nhiều dòng tài sản thô (Tên, ĐVT, Số lượng, Tỷ lệ, Ghi chú) -> phần mềm tự xếp mỗi dòng
vào Nhà, công trình / Cây trồng / Vật nuôi / Chính sách hỗ trợ (phan_loai_tai_san) và tìm mục đơn giá khớp; người dùng sửa
loại nếu cần rồi thêm vào phương án của hộ đang mở (CuaSoLapPA) hoặc bảng Dự toán & khái toán (KhungDuToan) - 0.9.67: cùng
một hộp, ghi qua "đích" của nhap_tai_san (DichPhuongAn / DichDuToan); màn hình chủ vẽ lại ở `sau_khi_dan_tai_san(n, muc)`."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
                               QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from .giao_dien import TOKEN, qmau_theo_tong
from .lap_pa import LoiNhap
from .phan_loai_tai_san import LOAI, BoPhanLoai, doc_danh_sach
from .thong_bao import TEN_UD

VANG = QColor(TOKEN['canh_bao_nhat'])
COT = ['Thêm', 'Tên tài sản', 'ĐVT', 'Số lượng', 'Tỷ lệ', 'Xếp vào', 'Mục đơn giá khớp', 'Độ tin', 'Căn cứ xếp loại',
       'Quy cách (số đo / tuổi), ghi chú']
C_QUY_CACH = 9
VI_DU = ('Nhà tạm: 46m2\nGác để ở tính bằng Nhà 01 tầng kết cấu loại 4: 35,8m2\nXoài: 16 cây, 17 năm tuổi\n'
         'Tràm: 1453 cây, đường kính 28cm\nAo nuôi cá ghép: 1,5ha, 1 năm 1 vụ\nNhà tạm m2 4*5\nGà ta con 40\nDi dời đồng hồ điện bộ 1')


def _bo_phan_loai(dm) -> BoPhanLoai:
    """Dựng một lần cho mỗi danh mục (DanhMuc dùng chung giữa các lần mở cửa sổ)."""
    bo = dm.__dict__.get('_bo_phan_loai')
    if bo is None:
        bo = dm.__dict__['_bo_phan_loai'] = BoPhanLoai(dm)
    return bo


class HopDanTaiSan(QDialog):
    im_lang = False

    def __init__(self, cua_so, chu: str = '', dich=None):
        """cua_so: màn hình chủ có `sau_khi_dan_tai_san(n, muc_cuoi)` (CuaSoLapPA, KhungDuToan); dich: đích ghi của
        nhap_tai_san (mặc định DichPhuongAn(cua_so.bo))."""
        super().__init__(cua_so)
        self.cua_so = cua_so
        if dich is None:
            from .nhap_tai_san import DichPhuongAn
            dich = DichPhuongAn(cua_so.bo)
        self.dich = dich
        self.ds = []                                    # [(dict dòng thô, KetQua)]
        self._chu_ocr = ''                              # chữ OCR gốc (cả trang) — không đổ vào ô; xem bằng nút Chữ OCR gốc
        self._tu_ocr = False
        self.setWindowTitle('Dán danh sách tài sản - tự xếp vào Nhà, công trình / Cây trồng / Vật nuôi / Hỗ trợ')
        self.resize(1250, 680)
        hd = QLabel('Mỗi dòng một tài sản, viết tự nhiên: <b>Tên: số lượng + đơn vị, quy cách</b> - <b>Xoài: 16 cây, 17 năm tuổi</b>; '
                    '<b>Tràm: 1453 cây, đường kính 28cm</b> (hoặc <b>Tràm cây 1500 d28</b>, chu vi: <b>cv 45</b>); <b>Nhà tạm: 46m2</b>; '
                    '<b>Gác để ở tính bằng Nhà 01 tầng kết cấu loại 4: 35,8m2</b> (áp giá mục sau chữ "tính bằng"); <b>Ao nuôi cá ghép: '
                    '1,5ha, 1 năm 1 vụ</b>. Cách cũ <b>Tên ␣ ĐVT ␣ Số lượng</b> (<b>Nhà tạm m2 4*5</b> = 20 m²) và dán từ Excel (cột Tên, '
                    'ĐVT, Số lượng, Tỷ lệ, Ghi chú) vẫn dùng được. Bấm <b>Phân loại</b>: phần mềm tự xếp vào Nhà / Cây / Vật nuôi / Hỗ trợ, '
                    'chọn mục đơn giá theo năm tuổi / quy cách đường kính; dòng nền vàng nên xem lại. '
                    '<b>Mở file</b> đọc PDF ảnh OCR, Word, Excel: tự lọc dòng tài sản / viết tay — không đưa mẫu in hành chính vào ô. '
                    'Trợ lý AI (nếu bật) viết lại dòng đã lọc, không gửi file.')
        hd.setWordWrap(True)
        self.o_chu = QPlainTextEdit(chu)
        self.o_chu.setPlaceholderText(VI_DU)
        b_pl = QPushButton('Phân loại')
        b_pl.clicked.connect(lambda: self.phan_loai())
        self.b_anh = QPushButton('Mở file…')
        self.b_anh.setToolTip(
            'PDF ảnh OCR, ảnh chụp, Word, Excel: đọc chữ trên máy, tự lọc dòng tài sản / viết tay. '
            'Mẫu in (CỘNG HÒA, tiêu đề biên bản, chữ ký) bị bỏ. Trợ lý AI bật thì viết lại dòng đã lọc — không gửi file. '
            'Chữ viết tay dễ sai: xem dòng vàng trước khi thêm.')
        self.b_anh.clicked.connect(lambda: self.mo_anh_pdf())
        self.b_clip = QPushButton('Dán ảnh clipboard')
        self.b_clip.setToolTip('Ảnh chụp màn hình trong Clipboard: nhận dạng chữ rồi lọc dòng tài sản.')
        self.b_clip.clicked.connect(lambda: self.dan_anh())
        self.b_goc = QPushButton('Chữ OCR gốc…')
        self.b_goc.setToolTip('Xem toàn bộ chữ nhận dạng (kể cả mẫu in đã lọc) — không đổ vào ô Dán tài sản.')
        self.b_goc.setEnabled(False)
        self.b_goc.clicked.connect(lambda: self.hien_chu_ocr_goc())
        self.b_ai = QPushButton('Trợ lý AI viết lại…')
        self.b_ai.setToolTip(
            'Tùy chọn: nhờ Trợ lý trực tuyến viết lại dòng OCR đã lọc thành "Tên: số lượng ĐVT". '
            'Không gửi file ảnh / PDF. Mặc định tắt — bật ở Công cụ → Trợ lý.')
        self.b_ai.clicked.connect(lambda: self.chinh_bang_ai())
        tren = QWidget()
        lt = QVBoxLayout(tren)
        lt.setContentsMargins(0, 0, 0, 0)
        lt.addWidget(hd)
        lt.addWidget(self.o_chu, 1)
        h = QHBoxLayout()
        self.o_viet_tay = QCheckBox('Chữ viết tay (đọc lại cột thưa)')
        self.o_viet_tay.setChecked(True)
        self.o_viet_tay.setToolTip('Biên bản điền tay: đọc thêm kiểu cột thưa khi lần đầu không ra dòng tài sản. '
                                   'Tắt với Giấy chứng nhận (không có tài sản) để khỏi đọc hai lần.')
        h.addWidget(self.o_viet_tay)
        h.addStretch(1)
        h.addWidget(self.b_anh)
        h.addWidget(self.b_clip)
        h.addWidget(self.b_goc)
        h.addWidget(self.b_ai)
        h.addWidget(b_pl)
        lt.addLayout(h)
        self._cap_nut_ai()
        self.bang = QTableWidget(0, len(COT))
        self.bang.setHorizontalHeaderLabels(COT)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        for c, w in enumerate((45, 260, 60, 80, 60, 150, 320, 55, 300, 220)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.lb = QLabel('')
        b_them = QPushButton('Thêm vào phương án')
        b_them.clicked.connect(lambda: self.them())
        b_dong = QPushButton('Đóng')
        b_dong.clicked.connect(self.reject)
        hn = QHBoxLayout()
        hn.addWidget(self.lb, 1)
        hn.addWidget(b_them)
        hn.addWidget(b_dong)
        tach = QSplitter(Qt.Orientation.Vertical)
        tach.addWidget(tren)
        tach.addWidget(self.bang)
        tach.setSizes([220, 420])
        lo = QVBoxLayout(self)
        lo.addWidget(tach, 1)
        lo.addLayout(hn)
        if chu:
            self.phan_loai()

    def bao(self, chu: str, loi: bool = True) -> None:
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TEN_UD, chu)

    def _cap_nut_ai(self) -> None:
        from . import tro_ly
        bat = bool(tro_ly.doc_cai_dat().get('bat'))
        self.b_ai.setEnabled(bat)
        if not bat:
            self.b_ai.setToolTip(
                'Trợ lý trực tuyến đang tắt (mặc định). Bật ở Công cụ → Trợ lý nếu muốn nhờ AI viết lại dòng OCR đã lọc. '
                'Không gửi file ảnh / PDF / CCCD.')

    def hien_chu_ocr_goc(self) -> None:
        from .giao_dien import hop_ket_qua
        dong = [x for x in (self._chu_ocr or '').splitlines() if x.strip()]
        hop_ket_qua(self, 'Chữ nhận dạng gốc (cả trang). Không đưa vào Dán tài sản — chỉ để soát.',
                    dong, tieu_de_ds='Chữ OCR gốc', canh_bao=False, hien=not self.im_lang)

    def chinh_bang_ai(self, khach=None) -> list:
        """Nhờ Trợ lý AI viết lại dòng đã lọc (không gửi ảnh / PDF). khach: client giả lập."""
        from .ocr_ho_so import chinh_dong_ocr_ai, loc_dong_viet_tay
        from .thong_bao import chu_loi
        from . import tro_ly
        chu = self.o_chu.toPlainText().strip() or self._chu_ocr
        dong = loc_dong_viet_tay(chu).giu
        if not dong:
            self.bao('Chưa có dòng tài sản để nhờ AI viết lại. Mở file trước, hoặc gõ tay vào ô.', loi=False)
            return []
        try:
            if self.im_lang or khach is not None:
                ra = chinh_dong_ocr_ai(dong, khach=khach)
            else:
                from .giao_dien import chay_nen_huy
                ra = chay_nen_huy(self, lambda: chinh_dong_ocr_ai(dong),
                                  'Đang nhờ trợ lý viết lại dòng tài sản…', nut_huy='Bỏ qua', gioi_han=45)
                if ra is None:
                    self.bao('Đã bỏ qua trợ lý AI (hết giờ hoặc mất mạng). Giữ nguyên ô hiện tại.', loi=False)
                    return []
        except tro_ly.LoiTroLy as e:
            self.bao(chu_loi('Không nhờ được Trợ lý AI', e))
            return []
        if not ra:
            self.bao('Trợ lý AI không giữ dòng tài sản nào. Giữ nguyên ô hiện tại.', loi=False)
            return []
        self.o_chu.setPlainText('\n'.join(ra))
        return self.phan_loai(tu_ocr=True)

    def _nap_dong_ocr(self, chu_goc: str, loc=None) -> str:
        """Lọc chữ OCR: chỉ dòng tài sản / viết tay vào ô; giữ chữ gốc để xem. loc: LocOcr sẵn (đã AI)."""
        from .ocr_ho_so import dong_dua_vao_dan
        self._chu_ocr = chu_goc or ''
        self.b_goc.setEnabled(bool((chu_goc or '').strip()))
        if loc is None:
            loc = dong_dua_vao_dan(chu_goc)
        self.lb.setText(loc.ly_do)
        return '\n'.join(loc.giu)

    def mo_anh_pdf(self, file=None) -> list:
        """Đọc PDF ảnh OCR / ảnh / Word / Excel -> lọc dòng tài sản rồi Phân loại. file: đường dẫn (kiểm thử)."""
        from pathlib import Path
        from . import ocr, ocr_ho_so
        from .nhap_don_gia import LoiNhap
        from .thong_bao import chu_loi
        if file is None:
            if self.im_lang:
                return []
            file, _ = QFileDialog.getOpenFileName(
                self, 'Chọn PDF ảnh, Word, Excel hoặc ảnh biên bản kiểm đếm', '', ocr_ho_so.LOC_FILE)
            if not file:
                return []
        duoi = Path(file).suffix.lower()
        can_ocr = duoi in ocr.DUOI_ANH or duoi == '.pdf'
        if can_ocr:
            thieu = ocr.san_sang()
            if thieu:
                self.bao(thieu)
                return []
        from PySide6.QtWidgets import QProgressDialog
        from .giao_dien import chay_nen_tien_do, con_tro_cho
        tien = None
        if not self.im_lang:
            tien = QProgressDialog('Đang đọc và phân tích file…', 'Dừng', 0, 0, self)
            tien.setWindowTitle(TEN_UD)
            tien.setWindowModality(Qt.WindowModality.WindowModal)
            tien.setMinimumDuration(0)
            tien.setValue(0)
            tien.show()
        psm_vt = bool(self.o_viet_tay.isChecked()) if hasattr(self, 'o_viet_tay') else True

        def ham(bao, cho):
            return ocr_ho_so.doc_va_phan_tich(
                file, bao_tien_do=bao, cho=cho, psm_viet_tay=psm_vt)

        self.b_anh.setEnabled(False)
        self.b_clip.setEnabled(False)
        try:
            with con_tro_cho():
                loc, chu, _da = chay_nen_tien_do(self, ham, tien)
        except ocr.DaHuy:
            return []
        except (ocr.LoiOCR, LoiNhap, OSError) as e:
            self.bao(chu_loi('Không đọc được file', e) if not isinstance(e, ocr.LoiOCR) else str(e))
            return []
        finally:
            self.b_anh.setEnabled(True)
            self.b_clip.setEnabled(True)
            if tien is not None:
                tien.close()
        if not (chu or '').strip():
            self.bao('Không đọc được chữ trên file. PDF ảnh / chữ viết tay mờ: gõ hoặc dán chữ vào ô.', loi=False)
            return []
        loc_chu = self._nap_dong_ocr(chu, loc)
        if not loc_chu.strip():
            self.bao('Đã đọc file nhưng không thấy dòng tài sản viết tay (mẫu in / tiêu đề form đã lọc). '
                     'Gõ hoặc dán từng dòng tài sản vào ô, hoặc bấm Chữ OCR gốc để soát.', loi=False)
            return []
        cu = self.o_chu.toPlainText().strip()
        self.o_chu.setPlainText((cu + '\n' + loc_chu) if cu else loc_chu)
        QApplication.processEvents()
        return self.phan_loai(tu_ocr=True)

    def dan_anh(self, anh=None) -> list:
        """Clipboard là ảnh thì OCR; là chữ thì đổ vào ô. anh: QImage (kiểm thử)."""
        from pathlib import Path
        import shutil
        import tempfile
        if anh is None:
            cb = QApplication.clipboard()
            chu = (cb.text() or '').strip()
            if chu:
                cu = self.o_chu.toPlainText().strip()
                self.o_chu.setPlainText((cu + '\n' + chu) if cu else chu)
                return self.phan_loai()
            if cb.mimeData() is not None and cb.mimeData().hasImage():
                anh = cb.image()
            else:
                self.bao('Clipboard chưa có ảnh hoặc chữ.', loi=False)
                return []
        td = Path(tempfile.mkdtemp(prefix='PABT_dan_ts_'))
        try:
            f = td / 'anh.png'
            if not anh.save(str(f)):
                self.bao('Không lưu được ảnh trong Clipboard để nhận dạng chữ.')
                return []
            return self.mo_anh_pdf(f)
        finally:
            shutil.rmtree(td, ignore_errors=True)

    # ---------------------------------------------- phân loại
    def phan_loai(self, chu: str | None = None, tu_ocr: bool = False) -> list:
        if chu is not None:
            self.o_chu.setPlainText(chu)
        if tu_ocr:
            self._tu_ocr = True
        dong = doc_danh_sach(self.o_chu.toPlainText())
        if not dong:
            self.bao('Chưa có dòng tài sản nào: dán hoặc gõ danh sách vào ô phía trên.', loi=False)
            return []
        from .hieu_tai_san import bo_sung
        bo = _bo_phan_loai(self.dich.dm)
        # bo_sung: cây theo đường kính / chu vi -> loại cây của bảng quy cách; năm tuổi -> mục đúng năm; khớp theo từ; "… tính bằng …"
        self.ds = [(d, bo_sung(bo, self.dich.dm, d, bo.phan_loai(d['ten'], d['dvt']))) for d in dong]
        b = self.bang
        b.setUpdatesEnabled(False)
        b.setRowCount(len(self.ds))
        for r, (d, k) in enumerate(self.ds):
            o = QTableWidgetItem()
            o.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            # OCR: dòng vàng / chưa có số lượng bỏ chọn sẵn — người dùng tự đánh dấu khi đã soát
            chon = not (self._tu_ocr and (k.can_xem or not (d.get('so_luong') or '').strip()))
            o.setCheckState(Qt.CheckState.Checked if chon else Qt.CheckState.Unchecked)
            b.setItem(r, 0, o)
            for c, v in ((1, d['ten']), (2, k.dvt or d['dvt']), (3, d['so_luong']), (4, d['ty_le'])):
                b.setItem(r, c, QTableWidgetItem(v))
            if d.get('cong_thuc'):                       # "4*5" đã tính thành 20: giữ phép tính gốc ở chú thích
                b.item(r, 3).setToolTip(f'= {d["cong_thuc"]}')
            cb = QComboBox()
            for ma, (_, ten) in LOAI.items():
                cb.addItem(ten, ma)
            cb.setCurrentIndex(cb.findData(k.loai))
            cb.currentIndexChanged.connect(lambda _=0, rr=r: self._doi_loai(rr))
            b.setCellWidget(r, 5, cb)
            if k.kieu:
                khop = f'{k.loai_cay}: chọn quy cách theo {"đường kính" if k.kieu == "dk" else "chu vi"} {k.so_do} cm'
            else:
                khop = k.khop.ten if k.khop is not None else '(ngoài danh mục: nhập đơn giá sau)'
            quy = '; '.join(x for x in ((f'{"Đường kính" if k.kieu == "dk" else "Chu vi"} {k.so_do} cm' if k.kieu else ''),
                                        (f'{d["tuoi"]} năm tuổi' if d.get('tuoi') else ''), d.get('ghi_chu') or '', k.ghi_them) if x)
            for c, v in ((6, khop), (7, f'{k.do_tin:.0%}'), (8, k.ly_do), (C_QUY_CACH, quy)):
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                it.setToolTip(v)
                b.setItem(r, c, it)
            if k.can_xem:
                for c in range(len(COT)):
                    if b.item(r, c) is not None:
                        b.item(r, c).setBackground(QBrush(qmau_theo_tong(TOKEN['canh_bao_nhat'], 'nen')))
        b.setUpdatesEnabled(True)
        dem = {}
        for _, k in self.ds:
            dem[k.ten_loai] = dem.get(k.ten_loai, 0) + 1
        self.lb.setText(f'{len(self.ds)} dòng: ' + ', '.join(f'{t} {n}' for t, n in dem.items()) +
                        f'; khớp đơn giá {sum(1 for _, k in self.ds if k.khop is not None)} dòng; '
                        f'cần xem lại {sum(1 for _, k in self.ds if k.can_xem)} dòng (nền vàng).')
        return self.ds

    def _doi_loai(self, r: int):
        """Người dùng đổi loại: mục danh mục đã khớp khác loại thì bỏ (dòng thành ngoài danh mục)."""
        d, k = self.ds[r]
        loai = self.bang.cellWidget(r, 5).currentData()
        if (k.khop is not None or k.kieu) and loai != k.loai:
            k.khop, k.kieu = None, ''
            self.bang.item(r, 6).setText('(ngoài danh mục: nhập đơn giá sau)')
        k.loai = loai


    # ---------------------------------------------- thêm vào phương án
    def them(self) -> int:
        from .nhap_tai_san import them_dong_tho, them_mot
        n, loi, muc_cuoi = 0, [], None
        for r, (d, k) in enumerate(self.ds):
            if self.bang.item(r, 0).checkState() != Qt.CheckState.Checked:
                continue
            ten, dvt = self.bang.item(r, 1).text().strip(), self.bang.item(r, 2).text().strip()
            sl, tl = self.bang.item(r, 3).text().strip(), self.bang.item(r, 4).text().strip()
            muc = LOAI[k.loai][0]
            gc = '; '.join(x for x in (d.get('ghi_chu') or '', k.ghi_them) if x)
            try:
                if k.kieu in ('dk', 'cv'):              # cây theo số đo: số cây (ô Số lượng) x quy cách đường kính / chu vi
                    them_mot(self.dich, 3, ('nhom', k.loai_cay), ten, sl, tl, k.kieu, gc, k.so_do)
                else:
                    them_dong_tho(self.dich, muc, k.khop, ten, dvt, sl, tl, gc)
                n += 1
                muc_cuoi = muc
                self.bang.item(r, 0).setCheckState(Qt.CheckState.Unchecked)       # đã thêm: bấm lại không thêm trùng
            except LoiNhap as e:
                loi.append(f'Dòng {r + 1} "{ten[:40]}": {e}')
        if muc_cuoi is not None:
            self.cua_so.sau_khi_dan_tai_san(n, muc_cuoi)
        if loi:
            self.bao(f'Đã thêm {n} dòng; {len(loi)} dòng chưa thêm được:\n' + '\n'.join(loi[:15]))
        elif n and not self.im_lang:
            self.accept()
        return n

"""Tiện ích nhập cây trồng, tài sản trong màn hình lập phương án:
- Thêm cây theo chu vi đo được (tự đổi sang đường kính, chọn đúng mục đơn giá theo quy cách đường kính);
- Tính mật độ: tách số cây trong / ngoài mật độ theo diện tích trồng và quy chuẩn mật độ;
- Tách tài sản theo ranh thu hồi: phần xây dựng trong / ngoài diện tích thu hồi;
- Quy chuẩn mật độ cây trồng, tỷ lệ mặc định của dự án.
Các hàm thao tác nhận tham số để kiểm thử không cần bấm (im_lang = True: không hiện hộp thông báo).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QListWidget, QMessageBox, QPlainTextEdit, QTableWidget, QTableWidgetItem,
                               QVBoxLayout)

from . import cay_trong as ct
from . import csdl
from .giao_dien import loc_khi_ngung_go
from .lap_pa import LoiNhap, doc_so, doc_ty_le
from .nghiep_vu import NGUON_DM
from .tien import D, KHONG, so_vn, vn

TIEU_DE = 'Cây trồng, tài sản'


def _o_so(text='', rong=120) -> QLineEdit:
    o = QLineEdit(text)
    o.setMaximumWidth(rong)
    o.setAlignment(Qt.AlignmentFlag.AlignRight)
    return o


class _Hop(QDialog):
    im_lang = False

    def bao(self, chu: str, loi: bool = True) -> None:
        if not self.im_lang:
            (QMessageBox.warning if loi else QMessageBox.information)(self, TIEU_DE, chu)

    def _nut(self, ok_chu: str) -> QDialogButtonBox:
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        nut.button(QDialogButtonBox.StandardButton.Ok).setText(ok_chu)
        nut.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        return nut


# ---------------------------------------------------------------- cây theo chu vi
class HopCayChuVi(_Hop):
    """Chọn loại cây (danh mục ghi theo đường kính), nhập các chu vi đo được -> thêm các dòng mục 3 đúng quy cách."""

    def __init__(self, man, tu_khoa: str = ''):
        super().__init__(man)
        self.man = man
        self.bang_dk = ct.BangCayDK(man.bo.dm.muc[3])
        self.nhom = []
        self.setWindowTitle('Thêm cây trồng theo chu vi đo được')
        self.resize(980, 620)
        self.o_tim = QLineEdit(tu_khoa)
        self.o_tim.setPlaceholderText('Tìm loại cây (không cần dấu), ví dụ: sao den, dau, si canh…')
        self.ds_loai = QListWidget()
        self.ds_loai.setMaximumWidth(300)
        self.o_cv = QPlainTextEdit()
        self.o_cv.setPlaceholderText('Chu vi thân đo được (cm), cách nhau bằng dấu phẩy hoặc xuống dòng.\n'
                                     'Nhiều cây cùng chu vi: 52x3 (3 cây chu vi 52 cm).\nVí dụ: 45, 52x3, 60x2, 130')
        self.o_cv.setMaximumHeight(110)
        self.bang = QTableWidget(0, 7)
        self.bang.setHorizontalHeaderLabels(['Mã', 'Mục đơn giá (quy cách đường kính)', 'Quy cách theo chu vi', 'Số cây',
                                             'Chu vi đo (cm)', 'Đơn giá (đ)', 'Thành tiền (đ)'])
        self.bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.verticalHeader().setVisible(False)
        for c, w in enumerate((60, 260, 180, 60, 100, 100, 110)):
            self.bang.setColumnWidth(c, w)
        self.lb = QLabel(f'Chu vi = π × đường kính (π ≈ {ct.pi_chuoi()}). Mỗi chu vi được đổi sang đường kính để chọn đúng '
                         'mục đơn giá; chu vi và đường kính quy đổi ghi vào cột Quy cách.')
        self.lb.setWordWrap(True)
        trai = QVBoxLayout()
        trai.addWidget(QLabel('Loại cây:'))
        trai.addWidget(self.o_tim)
        trai.addWidget(self.ds_loai)
        phai = QVBoxLayout()
        phai.addWidget(QLabel('Chu vi đo được:'))
        phai.addWidget(self.o_cv)
        phai.addWidget(self.bang)
        h = QHBoxLayout()
        h.addLayout(trai)
        h.addLayout(phai, 1)
        lo = QVBoxLayout(self)
        lo.addLayout(h)
        lo.addWidget(self.lb)
        lo.addWidget(self._nut('Thêm vào mục 3'))
        loc_khi_ngung_go(self.o_tim, self._loc)
        self.ds_loai.currentTextChanged.connect(lambda *_: self.xem())
        self.o_cv.textChanged.connect(lambda: self.xem())
        self._loc()

    def _loc(self, *_):
        self.ds_loai.clear()
        self.ds_loai.addItems(self.bang_dk.ten_loai(self.o_tim.text()))
        if self.ds_loai.count():
            self.ds_loai.setCurrentRow(0)

    def chon_loai(self, ten: str) -> None:
        self.o_tim.setText('')
        ds = [self.ds_loai.item(i).text() for i in range(self.ds_loai.count())]
        if ten in ds:
            self.ds_loai.setCurrentRow(ds.index(ten))

    def xem(self) -> tuple:
        ten = self.ds_loai.currentItem().text() if self.ds_loai.currentItem() else ''
        try:
            ds = ct.doc_ds_chu_vi(self.o_cv.toPlainText())
            self.nhom, loi = ct.gom_theo_chu_vi(self.bang_dk, ten, ds) if ten else ([], [])
            tb = ''
        except ValueError as e:
            self.nhom, loi, tb = [], [], str(e)
        self.bang.setRowCount(len(self.nhom))
        for r, (m, so, a, z) in enumerate(self.nhom):
            cv = so_vn(a) if a == z else f'{so_vn(a)} – {so_vn(z)}'
            for c, v in enumerate((m.ma, m.ten, ct.mo_ta_chu_vi(m.ten), str(so), cv, vn(m.don_gia or 0),
                                   vn((m.don_gia or KHONG) * so))):
                it = QTableWidgetItem(v)
                if c >= 3:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.bang.setItem(r, c, it)
        if loi:
            tb = f'Chu vi không thuộc khoảng nào của {ten}: ' + ', '.join(so_vn(x) for x in loi)
        if tb:
            self.lb.setText(f'<span style="color:#C62828">{tb}</span>')
        else:
            tong = sum(so for _, so, _, _ in self.nhom)
            self.lb.setText(f'{tong} cây, {len(self.nhom)} quy cách. Chu vi = π × đường kính (π ≈ {ct.pi_chuoi()}).')
        return self.nhom, loi

    def them(self) -> list:
        """Thêm các dòng vào mục 3 của hộ; trả chỉ số các dòng mới."""
        bo = self.man.bo
        moi = []
        for m, so, a, z in self.nhom:
            i, _ = bo.them_tu_danh_muc(3, m)
            bo.sua_khoan(3, i, 'so_luong', str(so))
            cv = so_vn(a) if a == z else f'{so_vn(a)}–{so_vn(z)}'
            dk = so_vn(ct.chu_vi_sang_duong_kinh(a)) if a == z else \
                f'{so_vn(ct.chu_vi_sang_duong_kinh(a))}–{so_vn(ct.chu_vi_sang_duong_kinh(z))}'
            bo.sua_khoan(3, i, 'quy_cach', f'Chu vi đo {cv} cm (đường kính quy đổi {dk} cm)')
            moi.append(i)
        return moi

    def accept(self):
        nhom, loi = self.xem()
        if not nhom:
            self.bao('Chọn loại cây và nhập ít nhất một chu vi hợp lệ.')
            return
        if loi and not self.im_lang and QMessageBox.question(
                self, TIEU_DE, self.lb.text().replace('<span style="color:#C62828">', '').replace('</span>', '') +
                '\n\nVẫn thêm các cây còn lại?') != QMessageBox.StandardButton.Yes:
            return
        self.dong_moi = self.them()
        super().accept()


# ---------------------------------------------------------------- mật độ cây trồng
def dt_dat_nn(bo) -> object:
    """Diện tích đất nông nghiệp thu hồi của hộ (mục 1), không có thì tổng DT thu hồi các thửa."""
    nn = sum((d.dien_tich for d in bo.pa.dat if (bo.bc.loai_dat.get(d.loai_dat.upper(), '') or '').lower().startswith('nông')),
             KHONG)
    if nn > 0:
        return nn
    return sum((D(t['dt_thu_hoi'] or 0) for t in bo.bc.thua_cua(bo.ma_ho)), KHONG)


def canh_bao_mat_do(bo, i: int) -> str:
    """Dòng cây trồng i (mục 3) vượt mật độ quy chuẩn trên diện tích đất nông nghiệp của hộ: câu nhắc dùng "Tính mật độ…";
    không vượt / chưa có mật độ / dòng đã tách trong - ngoài mật độ: ''. Không đổi số liệu (người dùng quyết định tách)."""
    try:
        d = bo.pa.khoan[3][i]
    except (IndexError, KeyError):
        return ''
    if 'mật độ' in (d.quy_cach or '').lower() or not d.so_luong:
        return ''
    m = bo.dm.lay(d.ma or d.ma_tuong_duong)
    q = ct.quy_chuan_mat_do(bo.con, d.ten, m.ten if m else d.ten, m.can_cu if m else '')
    dt = dt_dat_nn(bo)
    if q.mat_do is None or dt <= 0:
        return ''
    trong, ngoai = ct.tach_mat_do(d.so_luong, dt, q.mat_do)
    if not ngoai:
        return ''
    return (f'Mật độ: {so_vn(d.so_luong)} cây {ct.ten_goc(d.ten)} trên {so_vn(dt)} m² = {so_vn(ct.mat_do_thuc_te(d.so_luong, dt))} '
            f'cây/ha, vượt mật độ {so_vn(q.mat_do)} cây/ha ({ngoai} cây ngoài mật độ). Bấm "Tính mật độ…" để tách '
            '(sửa được diện tích trồng).')


class HopMatDo(_Hop):
    """Tách số cây của dòng mục 3 đang chọn thành trong mật độ (100%) và ngoài mật độ (theo tỷ lệ quy chuẩn)."""

    def __init__(self, man, i: int):
        super().__init__(man)
        self.man, self.i = man, i
        bo = man.bo
        self.d = d = bo.pa.khoan[3][i]
        m = bo.dm.lay(d.ma or d.ma_tuong_duong)
        self.q = ct.quy_chuan_mat_do(bo.con, d.ten, m.ten if m else d.ten, m.can_cu if m else '')
        self.setWindowTitle('Tính cây trong / ngoài mật độ')
        self.resize(640, 360)
        self.o_dt = _o_so(so_vn(dt_dat_nn(bo)))
        self.o_so = _o_so(so_vn(d.so_luong))
        self.o_md = _o_so(so_vn(self.q.mat_do) if self.q.mat_do else '')
        self.o_tl = _o_so(so_vn(self.q.ty_le_ngoai * 100))
        self.o_luu = QCheckBox(f'Lưu mật độ, tỷ lệ này làm quy chuẩn của dự án cho "{self.q.ten_cay}"')
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        self.lb.setTextFormat(Qt.TextFormat.RichText)
        self.lb.setObjectName('ket_qua_mat_do')
        self.lb.setStyleSheet('QLabel#ket_qua_mat_do { background: #FFFFFF; border: 1px solid #D5DEE7; border-radius: 8px; '
                              'padding: 10px 12px; }')
        self.resize(700, 520)
        form = QFormLayout()
        form.addRow('Cây trồng:', QLabel(f'<b>{d.ten}</b>' + (f'  (mã {d.ma})' if d.ma else '')))
        form.addRow('Diện tích trồng (m²):', self.o_dt)
        form.addRow('Số cây kiểm đếm:', self.o_so)
        form.addRow('Mật độ quy chuẩn (cây/ha):', self.o_md)
        form.addRow('Tỷ lệ bồi thường cây ngoài mật độ (%):', self.o_tl)
        form.addRow('', self.o_luu)
        ghi = QLabel(f'Mật độ: {self.q.can_cu or "chưa có trong danh mục - nhập theo quy định"}'
                     f'{" (quy chuẩn dự án)" if self.q.nguon == "dự án" else ""}. Số cây tối đa = mật độ × diện tích / 10.000. '
                     'Tỷ lệ ngoài mật độ đặt theo quy định áp dụng (mặc định 0% = không bồi thường phần vượt).')
        ghi.setWordWrap(True)
        lo = QVBoxLayout(self)
        lo.addLayout(form)
        lo.addWidget(ghi)
        lo.addWidget(self.lb)
        lo.addWidget(self._nut('Áp dụng'))
        for o in (self.o_dt, self.o_so, self.o_md, self.o_tl):
            o.textChanged.connect(lambda *_: self.tinh())
        self.tinh()

    def _doc(self) -> tuple:
        dt = doc_so(self.o_dt.text(), 'Diện tích trồng')
        so = doc_so(self.o_so.text(), 'Số cây')
        md = doc_so(self.o_md.text(), 'Mật độ', cho_phep_trong=True)
        tl = doc_ty_le(self.o_tl.text() or '0')
        if so != int(so):
            raise LoiNhap('Số cây phải là số nguyên.')
        return dt, int(so), (md if md > 0 else None), tl

    def tinh(self):
        try:
            dt, so, md, tl = self._doc()
        except LoiNhap as e:
            self.lb.setText(f'<span style="color:#C62828">{e}</span>')
            return None
        if md is None:
            self.lb.setText('Chưa có mật độ quy chuẩn: nhập mật độ (cây/ha).')
            return None
        trong, ngoai = ct.tach_mat_do(so, dt, md)
        p = ct.phan_tich_mat_do(so, dt, md)
        do = '#C62828'
        dong = [
            ('Mật độ quy định', f'{so_vn(md)} cây/ha (= {so_vn(p["m2_moi_cay"])} m²/cây)' +
                                (f' - <i>{self.q.can_cu}</i>' if self.q.nguon == 'gần đúng' else '')),
            ('Mật độ thực tế', f'{so} cây / {so_vn(dt)} m² = <b>{so_vn(ct.mat_do_thuc_te(so, dt) or 0)} cây/ha</b>'),
            ('Diện tích trồng', f'{so_vn(dt)} m² → trồng tối đa <b>{p["toi_da"]} cây</b> theo mật độ'),
            ('Số cây kiểm đếm', f'{so} cây → cần diện tích <b>{so_vn(p["dt_can"])} m²</b> theo mật độ'),
            ('Đối chiếu', (f'<span style="color:{do}"><b>VƯỢT mật độ {ngoai} cây</b> '
                           f'(thiếu {so_vn(p["dt_thieu"])} m² diện tích trồng)</span>') if ngoai else
                          '<span style="color:#2E7D32"><b>Không vượt mật độ</b></span>'),
            ('Bồi thường', f'<b>Đảm bảo mật độ {trong} cây</b> (100%)' +
                           (f'; <b>vượt mật độ {ngoai} cây</b> ({so_vn(tl * 100)}%)' if ngoai else '')),
        ]
        self.lb.setText('<table cellspacing="0" cellpadding="3">' + ''.join(
            f'<tr><td style="color:#1F4E79; font-weight:600; padding-right:14px">{a}</td><td>{b}</td></tr>' for a, b in dong) +
            '</table>')
        return trong, ngoai

    def ap_dung(self) -> tuple:
        dt, so, md, tl = self._doc()
        if md is None:
            raise LoiNhap('Nhập mật độ quy chuẩn (cây/ha).')
        trong, ngoai = ct.tach_mat_do(so, dt, md)
        bo = self.man.bo
        if self.o_luu.isChecked():
            ct.luu_quy_chuan_mat_do(bo.con, ct.QuyChuanMatDo(self.q.ten_cay, md, tl, self.q.can_cu or 'Quy chuẩn của dự án'))
        mo_ta = f'Mật độ {so_vn(md)} cây/ha × {so_vn(dt)} m² = tối đa {ct.so_cay_toi_da(md, dt)} cây'
        bo.sua_khoan(3, self.i, 'so_luong', str(trong))
        bo.sua_khoan(3, self.i, 'quy_cach', f'Trong mật độ ({mo_ta})')
        j = None
        if ngoai > 0:
            j = bo.nhan_ban(3, self.i)
            bo.sua_khoan(3, j, 'so_luong', str(ngoai))
            bo.sua_khoan(3, j, 'ty_le', so_vn(tl * 100))
            bo.sua_khoan(3, j, 'quy_cach', f'Ngoài mật độ ({mo_ta}; vượt {ngoai} cây)')
            bo.sua_khoan(3, j, 'ghi_chu', f'Cây ngoài mật độ: tỷ lệ {so_vn(tl * 100)}%')
        return trong, ngoai, j

    def accept(self):
        try:
            self.ket_qua = self.ap_dung()
        except LoiNhap as e:
            self.bao(str(e))
            return
        super().accept()


# ---------------------------------------------------------------- tài sản theo ranh thu hồi
class HopRanh(_Hop):
    """Tách khối lượng tài sản (mục 2) thành phần trong ranh thu hồi và phần vượt ra ngoài ranh."""

    def __init__(self, man, i: int):
        super().__init__(man)
        self.man, self.i = man, i
        bo = man.bo
        self.d = d = bo.pa.khoan[2][i]
        self.setWindowTitle('Tách tài sản theo ranh thu hồi')
        self.resize(640, 380)
        dt_thu_hoi = sum((D(t['dt_thu_hoi'] or 0) for t in bo.bc.thua_cua(bo.ma_ho)), KHONG)
        self.o_tong = _o_so(so_vn(d.so_luong))
        self.o_trong = _o_so('')
        self.o_kc = QCheckBox('Phần ngoài ranh bị ảnh hưởng kết cấu, không sử dụng được (tính toàn bộ)')
        self.o_tl = _o_so(so_vn(D(csdl.doc_cai_dat(bo.con, 'TL_NGOAI_RANH', '0')) * 100))
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        form = QFormLayout()
        form.addRow('Tài sản:', QLabel(f'<b>{d.ten}</b> ({d.dvt or "?"})'))
        form.addRow(f'Tổng khối lượng / diện tích xây dựng ({d.dvt or "đơn vị"}):', self.o_tong)
        form.addRow('Phần nằm trong ranh thu hồi:', self.o_trong)
        form.addRow('', self.o_kc)
        form.addRow('Tỷ lệ bồi thường phần ngoài ranh (%):', self.o_tl)
        ghi = QLabel(f'Diện tích thu hồi của hộ: {so_vn(dt_thu_hoi)} m². Phần trong ranh tính 100%; phần ngoài ranh tính theo tỷ lệ '
                     '(mặc định 0% = không bồi thường) trừ khi bị ảnh hưởng kết cấu. Mô tả trong / ngoài ranh ghi vào cột Quy cách.')
        ghi.setWordWrap(True)
        lo = QVBoxLayout(self)
        lo.addLayout(form)
        lo.addWidget(ghi)
        lo.addWidget(self.lb)
        lo.addWidget(self._nut('Áp dụng'))
        for o in (self.o_tong, self.o_trong, self.o_tl):
            o.textChanged.connect(lambda *_: self.tinh())
        self.o_kc.toggled.connect(lambda *_: self.tinh())
        self.tinh()

    def _doc(self):
        tong = doc_so(self.o_tong.text(), 'Tổng khối lượng')
        trong = doc_so(self.o_trong.text(), 'Phần trong ranh')
        tl = doc_ty_le(self.o_tl.text() or '0')
        return tong, trong, tl

    def tinh(self):
        try:
            tong, trong, tl = self._doc()
            r = ct.tach_ranh(tong, trong, self.o_kc.isChecked(), tl)
        except (LoiNhap, ValueError) as e:
            self.lb.setText(f'<span style="color:#C62828">{e}</span>')
            return None
        s = f'Tính 100%: <b>{so_vn(r["trong"])}</b>'
        if r['ngoai'] > 0:
            s += f'; phần ngoài ranh <b>{so_vn(r["ngoai"])}</b> tính {so_vn(r["ty_le_ngoai"] * 100)}%'
        self.lb.setText(s + '.')
        return r

    def ap_dung(self) -> tuple:
        tong, trong, tl = self._doc()
        kc = self.o_kc.isChecked()
        r = ct.tach_ranh(tong, trong, kc, tl)
        bo = self.man.bo
        bo.sua_khoan(2, self.i, 'so_luong', so_vn(r['trong']))
        bo.sua_khoan(2, self.i, 'quy_cach', ct.mo_ta_ranh(tong, trong, kc))
        j = None
        if r['ngoai'] > 0:
            j = bo.nhan_ban(2, self.i)
            bo.sua_khoan(2, j, 'so_luong', so_vn(r['ngoai']))
            bo.sua_khoan(2, j, 'ty_le', so_vn(r['ty_le_ngoai'] * 100))
            bo.sua_khoan(2, j, 'quy_cach', f'Phần ngoài ranh thu hồi ({so_vn(r["ngoai"])})')
            bo.sua_khoan(2, j, 'ghi_chu', f'Ngoài ranh thu hồi: tỷ lệ {so_vn(r["ty_le_ngoai"] * 100)}%')
        return r, j

    def accept(self):
        try:
            self.ket_qua = self.ap_dung()
        except (LoiNhap, ValueError) as e:
            self.bao(str(e))
            return
        super().accept()


# ---------------------------------------------------------------- tổng diện tích xây dựng so với diện tích thu hồi
class HopDienTichXayDung(_Hop):
    """Cộng dồn diện tích các tài sản (m²) theo thứ tự nhà chính → nhà khác → mái che → công trình phụ → sân, nền và so với
    tổng diện tích thu hồi của hộ, làm cơ sở xét điều kiện bồi thường phần vượt (bỏ dấu "Tính" để loại một dòng)."""
    COT = ['Tính', 'Ưu tiên', 'Nhóm', 'Dòng', 'Tài sản', 'Diện tích (m²)', 'Cộng dồn (m²)', 'So với DT thu hồi']

    def __init__(self, man):
        super().__init__(man)
        self.man = man
        self.bo_qua = set()
        self.setWindowTitle('Kiểm tra diện tích xây dựng so với diện tích thu hồi')
        self.resize(1080, 560)
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        self.lb.setTextFormat(Qt.TextFormat.RichText)
        self.lb.setObjectName('kq_dtxd')
        self.lb.setStyleSheet('QLabel#kq_dtxd { background: #FFFFFF; border: 1px solid #D5DEE7; border-radius: 8px; '
                              'padding: 10px 12px; font-size: 13px; }')
        self.bang = QTableWidget(0, len(self.COT))
        self.bang.setHorizontalHeaderLabels(self.COT)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setWordWrap(True)
        for c, w in enumerate((46, 60, 230, 55, 330, 110, 110, 150)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setStretchLastSection(True)
        self.bang.itemChanged.connect(self._doi_tinh)
        self.lb_lt = QLabel('')
        self.lb_lt.setWordWrap(True)
        ghi = QLabel('Thứ tự ưu tiên: nhà chính → nhà, công trình khác → mái che, mái hiên → công trình phụ → sân, nền. Chỉ tính tài '
                     'sản ĐVT m² chiếm đất (không tính tường, hàng rào, gác lửng, giếng…). Nhà nhiều tầng: kiểm tra số lượng là '
                     'diện tích chiếm đất hay diện tích sàn. Phần vượt diện tích thu hồi: xem xét điều kiện bồi thường (phần ngoài '
                     'ranh thu hồi) theo quy định.')
        ghi.setWordWrap(True)
        ghi.setStyleSheet('QLabel { color: #4A5B6C; }')
        lo = QVBoxLayout(self)
        lo.addWidget(self.lb)
        lo.addWidget(self.bang, 1)
        lo.addWidget(self.lb_lt)
        lo.addWidget(ghi)
        nut = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        nut.button(QDialogButtonBox.StandardButton.Close).setText('Đóng')
        nut.rejected.connect(self.reject)
        lo.addWidget(nut)
        self._dang_ve = False
        self.tinh()

    def tinh(self) -> dict:
        kq = ct.kiem_tra_dt_xay_dung(self.man.bo, self.bo_qua)
        self.kq = kq
        self._dang_ve = True
        try:
            self.bang.setRowCount(len(kq['dong']))
            for r, x in enumerate(kq['dong']):
                ck = QTableWidgetItem('')
                ck.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                ck.setCheckState(Qt.CheckState.Checked if x['tinh'] else Qt.CheckState.Unchecked)
                ck.setData(Qt.ItemDataRole.UserRole, x['i'])
                self.bang.setItem(r, 0, ck)
                for c, v in enumerate((str(x['nhom_so']), x['nhom'], f'2.{x["i"] + 1}', x['ten'], so_vn(x['dien_tich']),
                                       so_vn(x['luy_ke']) if x['tinh'] else '', x['trang_thai']), start=1):
                    it = QTableWidgetItem(v)
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if c in (1, 3, 5, 6):
                        it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    if c == 7 and x['vuot'] > 0:
                        it.setForeground(QColor('#B8433A'))
                        f = it.font()
                        f.setBold(True)
                        it.setFont(f)
                    self.bang.setItem(r, c, it)
            self.bang.resizeRowsToContents()
        finally:
            self._dang_ve = False
        vuot = kq['vuot']
        ket = (f'<span style="color:#B8433A"><b>VƯỢT {so_vn(vuot)} m²</b> so với diện tích thu hồi</span>' if vuot > 0 else
               '<span style="color:#2F7A4F"><b>Không vượt</b> diện tích thu hồi</span>')
        self.lb.setText(f'Tổng diện tích thu hồi của hộ: <b>{so_vn(kq["thu_hoi"])} m²</b> &nbsp;·&nbsp; '
                        f'Tổng diện tích tài sản xây dựng đã lập: <b>{so_vn(kq["tong"])} m²</b> &nbsp;→&nbsp; {ket}')
        lt = kq['loai_tru']
        self.lb_lt.setText(('Không tính: ' + '; '.join(f'2.{x["i"] + 1} {x["ten"][:40]} ({x["ly_do"]})' for x in lt[:8]) +
                            (f'; … ({len(lt)} dòng)' if len(lt) > 8 else '')) if lt else '')
        return kq

    def _doi_tinh(self, it):
        if self._dang_ve or it.column() != 0:
            return
        i = it.data(Qt.ItemDataRole.UserRole)
        (self.bo_qua.discard if it.checkState() == Qt.CheckState.Checked else self.bo_qua.add)(i)
        self.tinh()


# ---------------------------------------------------------------- quy chuẩn
class HopQuyChuan(_Hop):
    """Quy chuẩn mật độ cây trồng và tỷ lệ mặc định của dự án (lưu trong file dự án, không thuộc bộ đơn giá khóa)."""
    COT = ['Loại cây', 'Mật độ (cây/ha)', 'Tỷ lệ BT ngoài mật độ (%)', 'Căn cứ', 'Nguồn']

    def __init__(self, con, parent=None, chi_doc: bool = False):
        super().__init__(parent)
        self.con = con
        self.setWindowTitle('Quy chuẩn cây trồng, tài sản')
        self.resize(1000, 620)
        self.ds = ct.ds_quy_chuan_mat_do(con)
        self.o_tim = QLineEdit()
        self.o_tim.setPlaceholderText('Lọc loại cây…')
        self.bang = QTableWidget(len(self.ds), len(self.COT))
        self.bang.setHorizontalHeaderLabels(self.COT)
        self.bang.verticalHeader().setVisible(False)
        for c, w in enumerate((260, 120, 160, 300, 90)):
            self.bang.setColumnWidth(c, w)
        self.bang.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for r, q in enumerate(self.ds):
            for c, v in enumerate((q.ten_cay, so_vn(q.mat_do) if q.mat_do else '', so_vn(q.ty_le_ngoai * 100), q.can_cu, q.nguon)):
                it = QTableWidgetItem(v)
                if c in (0, 4) or chi_doc:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if c in (1, 2):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.bang.setItem(r, c, it)
        self.o_md = _o_so(so_vn(D(csdl.doc_cai_dat(con, 'TL_NGOAI_MAT_DO', '0')) * 100))
        self.o_ranh = _o_so(so_vn(D(csdl.doc_cai_dat(con, 'TL_NGOAI_RANH', '0')) * 100))
        from .nghiep_vu import NK_CO_BAN
        self.o_nk = _o_so(csdl.doc_cai_dat(con, 'NGUONG_NHAN_KHAU', str(NK_CO_BAN)))
        self.o_nk.setToolTip('QĐ 42/2025: mức hỗ trợ thuê nhà / tự lo chỗ ở cho hộ đến 4 nhân khẩu, cộng thêm từ nhân khẩu thứ 5')
        form = QFormLayout()
        form.addRow('Tỷ lệ mặc định bồi thường cây ngoài mật độ (%):', self.o_md)
        form.addRow('Tỷ lệ mặc định bồi thường tài sản phần ngoài ranh thu hồi (%):', self.o_ranh)
        form.addRow('Thuê nhà, tự lo chỗ ở: mức cơ bản cho hộ đến (nhân khẩu):', self.o_nk)
        ghi = QLabel('Mật độ đọc từ ghi chú bộ đơn giá ("Mật độ N cây/ha"); sửa ô Mật độ / Tỷ lệ / Căn cứ để đặt quy chuẩn riêng của '
                     'dự án (lưu trong file dự án). Tỷ lệ mặc định 0% = không bồi thường phần vượt - điều chỉnh theo quy định '
                     'áp dụng cho dự án.')
        ghi.setWordWrap(True)
        lo = QVBoxLayout(self)
        lo.addWidget(self.o_tim)
        lo.addWidget(self.bang)
        lo.addLayout(form)
        lo.addWidget(ghi)
        nut = self._nut('Lưu')
        nut.button(QDialogButtonBox.StandardButton.Ok).setEnabled(not chi_doc)
        lo.addWidget(nut)
        loc_khi_ngung_go(self.o_tim, self._loc)
        self._goc = [(self.bang.item(r, 1).text(), self.bang.item(r, 2).text(), self.bang.item(r, 3).text())
                     for r in range(len(self.ds))]

    def _loc(self, text):
        from .lap_pa import bo_dau
        k = bo_dau(text).split()
        for r, q in enumerate(self.ds):
            self.bang.setRowHidden(r, not all(x in bo_dau(q.ten_cay) for x in k))

    def luu(self) -> int:
        n = 0
        thay = []
        for r, q in enumerate(self.ds):
            gt = (self.bang.item(r, 1).text(), self.bang.item(r, 2).text(), self.bang.item(r, 3).text())
            if gt == self._goc[r]:
                continue
            md = doc_so(gt[0], f'Mật độ {q.ten_cay}', cho_phep_trong=True)
            tl = doc_ty_le(gt[1] or '0')
            thay.append(ct.QuyChuanMatDo(q.ten_cay, md if md > 0 else None, tl, gt[2].strip()))
        tl_md, tl_ranh = doc_ty_le(self.o_md.text() or '0'), doc_ty_le(self.o_ranh.text() or '0')
        nk = doc_so(self.o_nk.text() or '4', 'Số nhân khẩu mức cơ bản', toi_thieu=D(1), toi_da=D(20))
        if nk != int(nk):
            raise LoiNhap('Số nhân khẩu mức cơ bản phải là số nguyên.')
        for q in thay:
            ct.luu_quy_chuan_mat_do(self.con, q)
            n += 1
        with self.con:
            csdl.ghi_cai_dat(self.con, 'TL_NGOAI_MAT_DO', str(tl_md))
            csdl.ghi_cai_dat(self.con, 'TL_NGOAI_RANH', str(tl_ranh))
            csdl.ghi_cai_dat(self.con, 'NGUONG_NHAN_KHAU', str(int(nk)))
        return n

    def accept(self):
        try:
            self.so_luu = self.luu()
        except LoiNhap as e:
            self.bao(str(e))
            return
        super().accept()


__all__ = ['HopCayChuVi', 'HopMatDo', 'HopRanh', 'HopQuyChuan', 'NGUON_DM']

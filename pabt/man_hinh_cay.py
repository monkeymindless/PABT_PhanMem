"""Tiện ích nhập cây trồng, tài sản trong màn hình lập phương án:
- Thêm cây theo chu vi đo được (tự đổi sang đường kính, chọn đúng mục đơn giá theo quy cách đường kính);
- Tính mật độ: tách số cây trong / ngoài mật độ theo diện tích trồng và quy chuẩn mật độ;
- Tách tài sản theo ranh thu hồi: phần xây dựng trong / ngoài diện tích thu hồi;
- Quy chuẩn mật độ cây trồng, tỷ lệ mặc định của dự án.
Các hàm thao tác nhận tham số để kiểm thử không cần bấm (im_lang = True: không hiện hộp thông báo).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QListWidget, QMessageBox, QPlainTextEdit, QTableWidget, QTableWidgetItem,
                               QVBoxLayout)

from . import cay_trong as ct
from . import csdl
from .giao_dien import loc_khi_ngung_go
from .giao_dien import mau_theo_tong  # noqa: E402  (màu rich text theo tông nền)
from .giao_dien import dat_kieu_theo_tong  # noqa: E402  (kiểu riêng đổi theo tông nền)
from .giao_dien import vua_dong  # noqa: E402
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
            self.lb.setText(f'<span style="color:{mau_theo_tong("#B83A3A", "chu")}">{tb}</span>')
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
                self, TIEU_DE, self.lb.text().replace('<span style="color:#B83A3A">', '').replace('</span>', '') +
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
    if 'mật độ' in (d.quy_cach or '').lower() or la_dong_xen(d) or not d.so_luong:
        return ''
    m = bo.dm.lay(d.ma or d.ma_tuong_duong)
    q = ct.quy_chuan_mat_do(bo.con, d.ten, m.ten if m else d.ten, m.can_cu if m else '')
    dt = dt_dat_nn(bo)
    if q.mat_do is None or dt <= 0:
        return ''
    # 30/10/2026: cùng diện tích chia cho mọi loại cây của hộ, cây đơn giá cao tính trước (phan_bo_mat_do)
    g = next((g for g in phan_bo_cua_ho(bo, dt)[0] if g.i == i), None)
    if g is None or not g.dong.thu_tu:
        trong, ngoai = ct.tach_mat_do(d.so_luong, dt, q.mat_do)
        uu_tien = ''
    else:
        trong, ngoai = g.dong.trong, g.dong.ngoai
        uu_tien = f' (ưu tiên {g.dong.thu_tu} theo đơn giá, còn chỗ cho {trong} cây)'
    if not ngoai:
        return ''
    return (f'Mật độ: {so_vn(d.so_luong)} cây {ct.ten_goc(d.ten)} trên {so_vn(dt)} m² = {so_vn(ct.mat_do_thuc_te(d.so_luong, dt))} '
            f'cây/ha, vượt mật độ {so_vn(q.mat_do)} cây/ha{uu_tien}: {ngoai} cây ngoài mật độ. Bấm "Tính mật độ…" để tách '
            '(tính mọi loại cây của hộ, sửa được diện tích trồng).')


# ---------------------------------------------------------------- mật độ nhiều loại cây trên cùng diện tích (30/10/2026)
# dấu ở đầu quy cách: dòng chính (trong mật độ / cây trồng xen trong 0,5 lần) và dòng vượt (ngoài mật độ / cây xen vượt 0,5 lần)
_RE_DAU_MAT_DO = re.compile(r'^(?:Trong mật độ|Ngoài mật độ|Cây trồng xen|Cây xen vượt [^(]*) \([^)]*\)(?:;\s*)?')
_RE_TL_GOC = re.compile(r'tỷ lệ (?:trong mật độ|gốc) ([\d.,]+)%')
_DVT_CAY = re.compile(r'(?i)^(cây|bụi|khóm|gốc|bụi/khóm|cây/bụi)$')
DAU_VUOT = ('Ngoài mật độ (', 'Cây xen vượt ')
DAU_XEN = ('Cây trồng xen (', 'Cây xen vượt ')
GHI_CHU_VUOT = 'Phần cây trồng vượt mật độ, không tính toán bồi thường, hỗ trợ.'


def ghi_chu_xen(he_so, vuot: bool) -> str:
    """Ghi chú dòng cây trồng xen theo cách ghi của phương án mẫu (người dùng 30/10/2026)."""
    if vuot:
        return f'Phần cây trồng xen vượt quá {so_vn(D(he_so))} lần giá trị cây trồng chính, không tính toán bồi thường, hỗ trợ.'
    return f'Phần cây trồng xen không vượt quá {so_vn(D(he_so))} lần giá trị cây trồng chính.'


def _la_ngoai(d) -> bool:
    return (d.quy_cach or '').startswith(DAU_VUOT)


def la_dong_xen(d) -> bool:
    """Dòng đã xếp là cây trồng xen ở lần tính trước."""
    return (d.quy_cach or '').startswith(DAU_XEN)


def _ghi_chu_tu_dong(gc: str) -> bool:
    gc = gc or ''
    return gc == GHI_CHU_VUOT or gc.startswith(('Cây ngoài mật độ: tỷ lệ', 'Phần cây trồng xen '))


def _cung_dong(a, b) -> bool:
    return (a.ma, a.ma_tuong_duong, a.ten, a.dvt, a.don_gia) == (b.ma, b.ma_tuong_duong, b.ten, b.dvt, b.don_gia)


@dataclass
class NhomMatDo:
    """Một dòng cây trồng (gồm cả dòng vượt đã tách ngay dưới nó ở lần tính trước) của phương án."""
    i: int                          # chỉ số dòng chính trong bo.pa.khoan[3]
    phu: list                       # chỉ số các dòng vượt gộp vào dòng chính
    ty_le_goc: Decimal              # tỷ lệ bồi thường của dòng trước khi tách
    q: object                       # QuyChuanMatDo
    dong: ct.DongMatDo
    xen: bool = False               # cây trồng xen: không xét mật độ, giới hạn theo giá trị cây trồng chính


def nhom_mat_do(bo) -> list:
    """Các dòng cây trồng mục 3 tính theo cây (ĐVT cây / bụi / khóm / gốc, số nguyên) để phân bổ mật độ. Dòng vượt ("Ngoài mật độ" /
    "Cây xen vượt…") ngay dưới dòng cùng cây cùng giá (đã tách ở lần trước) gộp lại thành tổng số cây kiểm đếm - tính lại không cộng
    dồn. Dòng đã xếp cây trồng xen giữ vai trò xen."""
    ds = bo.pa.khoan[3]
    kq, md_nho = [], {}
    for i, d in enumerate(ds):
        if not _DVT_CAY.match((d.dvt or '').strip()) or d.so_luong != int(d.so_luong):
            continue
        if _la_ngoai(d) and kq and kq[-1].i + len(kq[-1].phu) == i - 1 and _cung_dong(ds[kq[-1].i], d):
            kq[-1].phu.append(i)
            kq[-1].dong.so_cay += int(d.so_luong)
            continue
        tl = d.ty_le
        if _la_ngoai(d):                              # cả dòng đã thành dòng vượt: lấy lại tỷ lệ ghi trong quy cách
            m = _RE_TL_GOC.search(d.quy_cach or '')
            tl = doc_ty_le(m.group(1)) if m else D(1)
        m = bo.dm.lay(d.ma or d.ma_tuong_duong)
        khoa = (ct.ten_goc(d.ten), m.ten if m else d.ten, m.can_cu if m else '')
        if khoa not in md_nho:
            md_nho[khoa] = ct.quy_chuan_mat_do(bo.con, d.ten, khoa[1], khoa[2])
        q = md_nho[khoa]
        kq.append(NhomMatDo(i, [], tl, q, ct.DongMatDo(d.ten, int(d.so_luong), q.mat_do, d.don_gia, tl), la_dong_xen(d)))
    return kq


def he_so_cay_xen(con) -> Decimal:
    try:
        v = D(csdl.doc_cai_dat(con, 'HE_SO_CAY_XEN', '') or ct.HE_SO_CAY_XEN)
    except Exception:                                   # noqa: BLE001 - giá trị hỏng: mặc định 0,5
        return ct.HE_SO_CAY_XEN
    return v if v >= 0 else ct.HE_SO_CAY_XEN


def phan_bo_nhom(nhom: list, dt, he_so=ct.HE_SO_CAY_XEN) -> dict:
    """Cây trồng chính: phân bổ diện tích theo mật độ (phan_bo_mat_do); cây trồng xen: giới hạn he_so x giá trị cây trồng chính
    (phan_bo_cay_xen). Trả dict(dt_con, gia_tri_chinh, toi_da_xen, xen_con)."""
    chinh = [g.dong for g in nhom if not g.xen]
    xen = [g.dong for g in nhom if g.xen]
    dt_con = ct.phan_bo_mat_do(chinh, dt)
    gtc = ct.gia_tri_cay(chinh)
    toi_da = gtc * D(he_so)
    xen_con = ct.phan_bo_cay_xen(xen, toi_da)
    return dict(dt_con=dt_con, gia_tri_chinh=gtc, toi_da_xen=toi_da, xen_con=xen_con)


def ap_mat_do(bo, nhom: list, dt, tl_ngoai, he_so=ct.HE_SO_CAY_XEN, kq: dict | None = None) -> tuple:
    """Ghi kết quả phan_bo_nhom vào phương án: dòng chính = số cây trong mật độ / trong giới hạn cây xen (tỷ lệ gốc), phần vượt = dòng
    riêng ngay dưới (vượt mật độ: tỷ lệ tl_ngoai; cây xen vượt: 0%, ghi chú theo mẫu); cả dòng vượt thì chính dòng đó thành dòng vượt.
    Trả (tổng trong, tổng vượt, số dòng vượt)."""
    ds = bo.pa.khoan[3]
    kq = kq or {}
    tong_trong = tong_ngoai = so_dong = 0
    for g in sorted(nhom, key=lambda g: -g.i):          # từ dưới lên: chèn / xóa dòng không làm lệch chỉ số dòng phía trên
        x = g.dong
        for j in sorted(g.phu, reverse=True):
            del ds[j]
        d = ds[g.i]
        goc = _RE_DAU_MAT_DO.sub('', d.quy_cach or '')
        if _ghi_chu_tu_dong(d.ghi_chu):
            d.ghi_chu = ''
        d.ty_le = g.ty_le_goc
        if not x.thu_tu:                                # chưa có mật độ: trả về đủ số cây, bỏ dấu mật độ cũ
            bo.sua_khoan(3, g.i, 'so_luong', str(x.so_cay))
            d.quy_cach = goc
            continue
        tong_trong += x.trong
        tong_ngoai += x.ngoai
        sau = f'; {goc}' if goc else ''
        tl_goc = '' if g.ty_le_goc == 1 else f'; tỷ lệ gốc {so_vn(g.ty_le_goc * 100)}%'
        if g.xen:
            mo_ta = (f'tối đa {so_vn(D(he_so))} lần giá trị cây trồng chính {vn(kq.get("gia_tri_chinh", KHONG))} đ = '
                     f'{vn(kq.get("toi_da_xen", KHONG))} đ, ưu tiên {x.thu_tu} theo đơn giá')
            dau_trong, dau_vuot = 'Cây trồng xen', f'Cây xen vượt {so_vn(D(he_so))} lần'
            tl_vuot, gc_trong, gc_vuot = KHONG, ghi_chu_xen(he_so, False), ghi_chu_xen(he_so, True)
        else:
            mo_ta = (f'Mật độ {so_vn(x.mat_do)} cây/ha, ưu tiên {x.thu_tu} theo đơn giá, '
                     f'dùng {so_vn(x.dt_dung.quantize(D("0.01")))} m² / {so_vn(D(dt))} m²')
            if x.trong == 0:
                mo_ta = (f'Mật độ {so_vn(x.mat_do)} cây/ha, ưu tiên {x.thu_tu} theo đơn giá: {so_vn(D(dt))} m² trồng đã dùng hết '
                         'cho cây đơn giá cao hơn')
            dau_trong, dau_vuot = 'Trong mật độ', 'Ngoài mật độ'
            tl_vuot, gc_trong = D(tl_ngoai), ''
            gc_vuot = GHI_CHU_VUOT if tl_vuot == 0 else f'Cây ngoài mật độ: tỷ lệ {so_vn(tl_vuot * 100)}%'

        def vuot(k):
            ds[k].ty_le = tl_vuot
            ds[k].thanh_tien_excel = None
            ds[k].ghi_chu = gc_vuot
        if x.trong == 0 and x.ngoai:
            bo.sua_khoan(3, g.i, 'so_luong', str(x.ngoai))
            d.quy_cach = f'{dau_vuot} ({mo_ta}; vượt {x.ngoai} cây{tl_goc}){sau}'
            vuot(g.i)
            so_dong += 1
            continue
        bo.sua_khoan(3, g.i, 'so_luong', str(x.trong))
        d.quy_cach = f'{dau_trong} ({mo_ta}){sau}'
        if gc_trong and not d.ghi_chu:
            d.ghi_chu = gc_trong
        if x.ngoai:
            j = bo.nhan_ban(3, g.i)
            bo.sua_khoan(3, j, 'so_luong', str(x.ngoai))
            ds[j].quy_cach = f'{dau_vuot} ({mo_ta}; vượt {x.ngoai} cây){sau}'
            vuot(j)
            so_dong += 1
    return tong_trong, tong_ngoai, so_dong


def phan_bo_cua_ho(bo, dt=None) -> tuple:
    """(nhóm, kết quả phan_bo_nhom) của mọi dòng cây trồng của hộ trên diện tích đất nông nghiệp thu hồi (dt None)."""
    nhom = nhom_mat_do(bo)
    kq = phan_bo_nhom(nhom, dt_dat_nn(bo) if dt is None else dt, he_so_cay_xen(bo.con))
    return nhom, kq


class HopMatDoNhieuCay(_Hop):
    """Tính mật độ MỌI dòng cây trồng của hộ trên cùng diện tích trồng: cây trồng chính đơn giá cao tính trước; phần diện tích còn dư
    tính tiếp cho cây đơn giá thấp hơn; cây không còn chỗ là vượt mật độ (dòng riêng, tỷ lệ ngoài mật độ). Cây trồng xen (đánh dấu ở
    cột "Cây xen"): không xét mật độ, bồi thường tối đa 0,5 lần giá trị cây trồng chính - phần vượt là dòng riêng không tính tiền."""
    COT = ['Ưu tiên', 'Cây trồng', 'Cây xen', 'Số cây', 'Đơn giá', 'Mật độ (cây/ha)', 'm²/cây', 'Được tính', 'Vượt',
           'Dùng (m² / đ)']
    C_XEN, C_MD, C_VUOT = 2, 5, 8

    def __init__(self, man):
        super().__init__(man)
        self.man = man
        bo = man.bo
        self.nhom = nhom_mat_do(bo)
        self.setWindowTitle('Tính mật độ cây trồng, cây trồng xen (nhiều loại cây trên cùng diện tích)')
        self.resize(1120, 620)
        self.o_dt = _o_so(so_vn(dt_dat_nn(bo)))
        self.o_tl = _o_so(so_vn(D(csdl.doc_cai_dat(bo.con, 'TL_NGOAI_MAT_DO', '0')) * 100))
        self.he_so_cu = he_so_cay_xen(bo.con)
        self.o_hs = _o_so(so_vn(self.he_so_cu))
        self.o_luu = QCheckBox('Lưu mật độ đã sửa trong bảng làm quy chuẩn của dự án')
        form = QFormLayout()
        form.addRow('Diện tích trồng (m²):', self.o_dt)
        form.addRow('Tỷ lệ bồi thường cây vượt mật độ (%):', self.o_tl)
        form.addRow('Cây trồng xen tối đa (lần giá trị cây trồng chính):', self.o_hs)
        ghi = QLabel('Cây trồng chính có đơn giá cao hơn được tính trước: trong mật độ tối đa = diện tích còn lại × mật độ / 10.000; '
                     'diện tích còn dư tính tiếp cho cây đơn giá cao thứ hai… tới khi hết; phần còn lại là vượt mật độ - dòng riêng ngay '
                     'dưới (mặc định 0% = không bồi thường). Đánh dấu "Cây xen" cho cây trồng xen: không xét mật độ, được bồi thường tối '
                     'đa 0,5 lần giá trị cây trồng chính (cây xen đơn giá cao tính trước); phần vượt là dòng riêng không tính tiền. Sửa '
                     'được cột Mật độ.')
        ghi.setWordWrap(True)
        self.bang = QTableWidget(0, len(self.COT))
        self.bang.setHorizontalHeaderLabels(self.COT)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        hd = self.bang.horizontalHeader()
        hd.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hd.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.bang.setWordWrap(False)
        self.lb = QLabel('')
        self.lb.setWordWrap(True)
        self.lb.setTextFormat(Qt.TextFormat.RichText)
        self.lb.setObjectName('ket_qua_mat_do')
        dat_kieu_theo_tong(self.lb, 'QLabel#ket_qua_mat_do { background: #FFFFFF; border: 1px solid #D5DEE7; border-radius: 8px; '
                                    'padding: 8px 12px; }')
        lo = QVBoxLayout(self)
        lo.addLayout(form)
        lo.addWidget(ghi)
        lo.addWidget(self.bang, 1)
        lo.addWidget(self.lb)
        lo.addWidget(self.o_luu)
        lo.addWidget(self._nut('Áp dụng vào phương án'))
        # bảng xếp theo đơn giá giảm dần (dòng chưa có mật độ cuối bảng) - đơn giá không sửa ở đây nên thứ tự cố định
        self.thu_tu = sorted(range(len(self.nhom)), key=lambda k: (not self.nhom[k].q.mat_do and not self.nhom[k].xen,
                                                                   -self.nhom[k].dong.don_gia, k))
        self.bang.setRowCount(len(self.thu_tu))
        self.bang.blockSignals(True)
        for r, k in enumerate(self.thu_tu):
            g = self.nhom[k]
            for c in range(len(self.COT)):
                it = QTableWidgetItem('')
                if c != self.C_MD:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if c not in (1, self.C_XEN):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.bang.setItem(r, c, it)
            o = self.bang.item(r, self.C_XEN)
            o.setFlags(o.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            o.setCheckState(Qt.CheckState.Checked if g.xen else Qt.CheckState.Unchecked)
            o.setToolTip('Cây trồng xen: không xét mật độ, bồi thường tối đa 0,5 lần giá trị cây trồng chính')
            self.bang.item(r, 1).setText(g.dong.ten)
            self.bang.item(r, 3).setText(str(g.dong.so_cay))
            self.bang.item(r, 4).setText(vn(g.dong.don_gia))
            self.bang.item(r, self.C_MD).setText(so_vn(g.q.mat_do) if g.q.mat_do else '')
            self.bang.item(r, self.C_MD).setToolTip(g.q.can_cu or 'Chưa có mật độ trong danh mục - nhập mật độ (cây/ha)')
        self.bang.blockSignals(False)
        self.bang.itemChanged.connect(lambda *_: self.tinh())
        for o in (self.o_dt, self.o_tl, self.o_hs):
            o.textChanged.connect(lambda *_: self.tinh())
        self.tinh()

    def dat_xen(self, ten_hoac_chi_so, xen: bool = True) -> None:
        """Đánh dấu / bỏ cây trồng xen cho dòng (chỉ số trong self.nhom, hoặc tên cây) - dùng cho kiểm thử."""
        for r, k in enumerate(self.thu_tu):
            if k == ten_hoac_chi_so or self.nhom[k].dong.ten == ten_hoac_chi_so:
                self.bang.item(r, self.C_XEN).setCheckState(Qt.CheckState.Checked if xen else Qt.CheckState.Unchecked)

    def _doc(self) -> tuple:
        dt = doc_so(self.o_dt.text(), 'Diện tích trồng')
        tl = doc_ty_le(self.o_tl.text() or '0')
        hs = doc_so(self.o_hs.text() or '0', 'Hệ số cây trồng xen')
        for r, k in enumerate(self.thu_tu):
            g = self.nhom[k]
            md = doc_so(self.bang.item(r, self.C_MD).text(), f'Mật độ của {g.dong.ten}', cho_phep_trong=True)
            g.dong.mat_do = md if md > 0 else None
            g.xen = self.bang.item(r, self.C_XEN).checkState() == Qt.CheckState.Checked
        return dt, tl, hs

    def tinh(self):
        try:
            dt, tl, hs = self._doc()
        except LoiNhap as e:
            self.lb.setText(f'<span style="color:{mau_theo_tong("#B83A3A", "chu")}">{e}</span>')
            return None
        kq = phan_bo_nhom(self.nhom, dt, hs)
        self.bang.blockSignals(True)
        do, xanh = QColor('#B83A3A'), QColor('#2E7D32')
        for r, k in enumerate(self.thu_tu):
            g = self.nhom[k]
            x = g.dong
            co = bool(x.thu_tu)
            if g.xen:
                gt = [f'xen {x.thu_tu}', None, None, None, None, None, '-', str(x.trong), str(x.ngoai), vn(x.dt_dung)]
            else:
                gt = [str(x.thu_tu) if co else '-', None, None, None, None, None,
                      so_vn(x.m2_moi_cay.quantize(D('0.01'))) if co else '', str(x.trong) if co else 'chưa có mật độ',
                      str(x.ngoai) if co else '', so_vn(x.dt_dung.quantize(D('0.01'))) if co else '']
            for c, v in enumerate(gt):
                if v is not None:
                    self.bang.item(r, c).setText(v)
            self.bang.item(r, self.C_VUOT).setForeground(do if x.ngoai else xanh)
        self.bang.blockSignals(False)
        chinh = [g.dong for g in self.nhom if not g.xen]
        xen = [g.dong for g in self.nhom if g.xen]
        trong = sum(x.trong for x in chinh if x.thu_tu)
        ngoai = sum(x.ngoai for x in chinh)
        khong = [x.ten for x in chinh if not x.thu_tu]
        dong = [
            ('Diện tích trồng', f'{so_vn(dt)} m²; đã dùng <b>{so_vn((dt - kq["dt_con"]).quantize(D("0.01")))} m²</b>, còn '
                                f'{so_vn(kq["dt_con"].quantize(D("0.01")))} m²'),
            ('Trong mật độ', f'<b>{trong} cây</b> (tỷ lệ của từng dòng) - giá trị cây trồng chính {vn(kq["gia_tri_chinh"])} đ'),
            ('Vượt mật độ', (f'<span style="color:#B83A3A"><b>{ngoai} cây</b></span> - dòng riêng, tỷ lệ {so_vn(tl * 100)}%')
             if ngoai else '<span style="color:#2E7D32"><b>Không có cây vượt mật độ</b></span>'),
        ]
        if xen:
            vuot_xen = sum(x.ngoai for x in xen)
            dong.append(('Cây trồng xen', f'tối đa {so_vn(hs)} × {vn(kq["gia_tri_chinh"])} = <b>{vn(kq["toi_da_xen"])} đ</b>; '
                         f'được tính {sum(x.trong for x in xen)} cây = {vn(ct.gia_tri_cay(xen))} đ' +
                         (f'; <span style="color:#B83A3A"><b>vượt {vuot_xen} cây</b></span> (không bồi thường)' if vuot_xen else '')))
        if khong:
            dong.append(('Chưa có mật độ', ', '.join(khong) + ' - không tính, giữ nguyên số cây (nhập mật độ hoặc đánh dấu cây xen)'))
        if not self.nhom:
            dong = [('Không có dòng', 'Hộ chưa có dòng cây trồng tính theo cây (ĐVT cây / bụi / khóm, số nguyên) ở mục 3.')]
        self.lb.setText('<table cellspacing="0" cellpadding="3">' + ''.join(
            f'<tr><td style="color:{mau_theo_tong("#1F4E79", "chu")}; font-weight:600; padding-right:14px">{a}</td><td>{b}</td></tr>' for a, b in dong) +
            '</table>')
        return trong, ngoai

    def ap_dung(self) -> tuple:
        dt, tl, hs = self._doc()
        if not self.nhom:
            raise LoiNhap('Hộ chưa có dòng cây trồng tính theo cây ở mục 3.')
        bo = self.man.bo
        kq = phan_bo_nhom(self.nhom, dt, hs)
        if self.o_luu.isChecked():
            for g in self.nhom:
                if not g.xen and g.dong.mat_do and g.dong.mat_do != g.q.mat_do:
                    ct.luu_quy_chuan_mat_do(bo.con, ct.QuyChuanMatDo(g.q.ten_cay, g.dong.mat_do, tl, 'Quy chuẩn của dự án'))
        if hs != self.he_so_cu and not getattr(bo, 'chi_doc', False):
            with bo.con:
                csdl.ghi_cai_dat(bo.con, 'HE_SO_CAY_XEN', str(hs))
                csdl.ghi_nhat_ky(bo.con, 'Hệ số cây trồng xen', f'Cây trồng xen tối đa {so_vn(hs)} lần giá trị cây trồng chính')
        return ap_mat_do(bo, self.nhom, dt, tl, hs, kq)

    def accept(self):
        try:
            self.ket_qua = self.ap_dung()
        except LoiNhap as e:
            self.bao(str(e))
            return
        super().accept()


class HopMatDo(_Hop):
    """Tách số cây của dòng mục 3 đang chọn thành trong mật độ (100%) và ngoài mật độ (theo tỷ lệ quy chuẩn). Một dòng - trên màn hình
    lệnh "Tính mật độ…" mở HopMatDoNhieuCay (mọi loại cây của hộ); hộp này còn dùng khi gọi tinh_mat_do(i) cho một dòng."""

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
        dat_kieu_theo_tong(self.lb, 'QLabel#ket_qua_mat_do { background: #FFFFFF; border: 1px solid #D5DEE7; border-radius: 8px; '
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
            self.lb.setText(f'<span style="color:{mau_theo_tong("#B83A3A", "chu")}">{e}</span>')
            return None
        if md is None:
            self.lb.setText('Chưa có mật độ quy chuẩn: nhập mật độ (cây/ha).')
            return None
        trong, ngoai = ct.tach_mat_do(so, dt, md)
        p = ct.phan_tich_mat_do(so, dt, md)
        do = mau_theo_tong('#B83A3A', 'chu')
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
            f'<tr><td style="color:{mau_theo_tong("#1F4E79", "chu")}; font-weight:600; padding-right:14px">{a}</td><td>{b}</td></tr>' for a, b in dong) +
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
            self.lb.setText(f'<span style="color:{mau_theo_tong("#B83A3A", "chu")}">{e}</span>')
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
        dat_kieu_theo_tong(self.lb, 'QLabel#kq_dtxd { background: #FFFFFF; border: 1px solid #D5DEE7; border-radius: 8px; '
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
        dat_kieu_theo_tong(ghi, 'QLabel { color: #4A5B6C; }')
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
            vua_dong(self.bang, None, None)
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


__all__ = ['HopCayChuVi', 'HopMatDo', 'HopMatDoNhieuCay', 'HopRanh', 'HopQuyChuan', 'NGUON_DM']

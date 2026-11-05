"""Áp đơn giá đất (gia_dat_qd03) vào dòng đất của các hộ trong dự án: danh sách dòng cho bảng tính, ghi đúng phiên bản, tự tạo dòng từ thửa. Không Qt.

Quy tắc phiên bản (phien_ban_pa, người dùng 05/11/2026 "tuyệt đối không ghi đè đơn giá niêm yết ở V1"): hộ chưa có V1 ghi vào V0; hộ đã có V1 ghi vào nhánh
V2 mới nhất còn mở, chưa có thì nhân bản V1 thành V2 mới. Hộ đang mở trong cửa sổ lập phương án (bo_mo) ghi vào bộ soạn của cửa sổ, chưa lưu xuống file, để
cửa sổ không ghi đè lại bằng số cũ. Mọi số tiền vẫn do nghiep_vu tính khi đọc kết quả, ở đây không tính tay."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from decimal import Decimal

from . import ho_so
from . import phien_ban_pa as pb
from .lap_pa import BoSoan, DanhMuc, LoiNhap, bo_dau, doc_so_luong
from .nghiep_vu import BoiCanh, doc_tat_ca_phuong_an, he_so
from .tien import KHONG, D

CO_CHUA_DONG = -1                  # chi_so của hàng "hộ chưa có dòng đất": hiện để biết còn hộ cần lập, không tích được
V2_MOI = 'V2 mới'
LY_DO_V2 = 'Áp đơn giá đất mới, V1 đã niêm yết giữ nguyên.'


@dataclass
class DongGia:
    """Một hàng của bảng áp giá. chi_so: vị trí trong pa.dat của phiên bản đích, CO_CHUA_DONG: hộ chưa có dòng đất."""
    ma_ho: int
    ho_ten: str
    chi_so: int
    ma_thua: object = None
    ten_thua: str = ''
    loai_dat: str = ''
    dien_tich: Decimal = KHONG
    ty_le: object = None
    gia_hien_tai: Decimal = KHONG
    dich: str = pb.V0              # phiên bản sẽ ghi: V0 | V2.n | V2 mới | bản đang mở
    so_thua_ho: int = 0
    tim: str = ''                  # chữ không dấu để lọc nhanh

    @property
    def khoa(self) -> tuple:
        return self.ma_ho, self.chi_so, self.ma_thua, self.loai_dat


@dataclass
class KetQuaAp:
    so_dong: int = 0
    so_ho: int = 0
    nhanh: dict = field(default_factory=dict)        # {mã hộ: 'V2.n'} hộ có V1 khóa nên ghi vào nhánh
    bi_chan: list = field(default_factory=list)      # câu báo từng hộ không ghi được
    ho_tro: list = field(default_factory=list)       # câu báo khoản hỗ trợ đã tính lại
    canh_bao: list = field(default_factory=list)


def _phien_ban_ca_du_an(con) -> dict:
    """{mã hộ: {mã phiên bản: khóa}} một câu truy vấn (bỏ dòng V1.goc)."""
    if not pb.co_bang(con):
        return {}
    kq = {}
    for ma, v, k in con.execute('SELECT ma_ho, ma, khoa FROM pa_phien_ban WHERE ma <> ?', (pb.V1_GOC,)):
        kq.setdefault(ma, {})[v] = bool(k)
    return kq


def _ho_nhieu_lan(con) -> set:
    """Hộ không đi được đường tắt (có lần bổ sung / điều chỉnh, quyết định, khóa): dùng chung điều kiện với lap_pa._mot_lan_chua_duyet nhưng cả dự án một câu."""
    try:
        return {r[0] for r in con.execute('''SELECT ma_ho FROM qd_ho
                                             UNION SELECT ma_ho FROM pa_lan WHERE lan > 1 OR khoa = 1 OR trang_thai <> 'dang_lap'
                                             UNION SELECT ma_ho FROM ct_dat WHERE lan > 1
                                             UNION SELECT ma_ho FROM ct_khoan WHERE lan > 1''')}
    except sqlite3.OperationalError:                 # file chỉ xem bản cũ: chưa có pa_lan / cột lan
        return {r[0] for r in con.execute('SELECT ma_ho FROM qd_ho')}


def _dich_cua(ban: dict | None) -> str:
    """Phiên bản sẽ ghi của một hộ theo danh sách phiên bản của hộ."""
    if not ban or pb.V1 not in ban:
        return pb.V0
    v2 = sorted((m for m in ban if m.startswith('V2.')), key=pb._khoa_sap)
    mo = [m for m in v2 if not ban[m]]
    return mo[-1] if mo else V2_MOI


def doc_dong(con, ds_ma_ho=None, bo_mo=None) -> list:
    """Các hàng cho bảng áp giá theo thứ tự hộ. ds_ma_ho None: cả dự án (doc_tat_ca_phuong_an, không đọc từng hộ). bo_mo: bộ soạn đang mở của một hộ, lấy dòng chưa lưu."""
    bc = BoiCanh.tu(con)
    ban = _phien_ban_ca_du_an(con)
    nhieu_lan = _ho_nhieu_lan(con)
    ds_pa = doc_tat_ca_phuong_an(con, ds_ma_ho)
    dm = None
    kq = []
    ten_thua = {}
    for t in bc.thua.values():
        ten_thua[t['ma_thua']] = (f'Thửa {t["so_thua"]} tờ {t["so_to"]}', f'{t["so_to"]} {t["so_thua"]}')
    for ma, pa in ds_pa.items():
        dich = _dich_cua(ban.get(ma))
        if bo_mo is not None and bo_mo.ma_ho == ma:
            dat, dich = bo_mo.pa.dat, getattr(bo_mo, 'phien_ban', None) or pb.V0
        elif dich != pb.V0:
            r = pb.lay(con, ma, pb.V1 if dich == V2_MOI else dich)
            dat = pb.dat_tu_json(r['du_lieu'])
        elif ma in nhieu_lan:
            dm = dm or DanhMuc(con)
            dat = BoSoan(con, ma, dm, bc).pa.dat
        else:
            dat = pa.dat
        ten = pa.ho.ho_ten or ''
        so_thua = len(bc.thua_cua(ma))
        if not dat:
            chu = f'Chưa có dòng đất ({so_thua} thửa)' if so_thua else 'Chưa có thửa'
            kq.append(DongGia(ma, ten, CO_CHUA_DONG, ten_thua=chu, dich=dich, so_thua_ho=so_thua, tim=bo_dau(f'{ma} {ten}')))
            continue
        for i, d in enumerate(dat):
            mo_ta, to_thua = ten_thua.get(d.ma_thua, ('', ''))
            kq.append(DongGia(ma, ten, i, d.ma_thua, mo_ta, d.loai_dat, D(d.dien_tich), d.ty_le, D(d.gia_bang_gia) * he_so(d.he_so_k), dich, so_thua,
                              bo_dau(f'{ma} {ten} {mo_ta} {to_thua} {d.loai_dat}')))
    return kq


def mo_ban_ghi(con, ma_ho: int, dm=None, bc=None) -> tuple:
    """BoSoan mở đúng phiên bản sẽ ghi; hộ có V1 mà chưa có nhánh mở thì tạo V2. Trả (bộ soạn, mã nhánh vừa dùng hoặc ''). Lần đã phê duyệt: LoiNhap, không tạo nhánh thừa."""
    bo = BoSoan(con, ma_ho, dm, bc)
    if bo.khoa:
        raise LoiNhap(f'lần {bo.lan} đã có quyết định phê duyệt, không sửa được.')
    ban = {x['ma']: bool(x['khoa']) for x in pb.ds_phien_ban(con, ma_ho)}
    dich = _dich_cua(ban)
    if dich == pb.V0:
        return bo, ''
    ma = pb.tao_v2(con, ma_ho, LY_DO_V2) if dich == V2_MOI else dich
    bo.mo_phien_ban(ma)
    return bo, ma


def gop_can_cu(con, goi: dict, chu_hien: str | None = None) -> str:
    """Gộp văn bản căn cứ của gói vào mục căn cứ của dự án (13 bậc, khử trùng), dự án nhớ gói đã áp. Trả câu cảnh báo nếu không ghi được."""
    from . import goi_gia_dat as gg
    from . import van_ban_can_cu as vb
    chu = chu_hien if chu_hien is not None else vb.doc_can_cu_du_an(con)
    try:
        vb.ghi_can_cu_du_an(con, vb.gop_va_sap_xep([chu], list(goi.get('van_ban_can_cu') or ()))[0])
        gg.nho_goi_du_an(con, goi['ma'])
    except (LoiNhap, sqlite3.OperationalError) as e:
        return f'Chưa ghi được văn bản căn cứ vào dự án: {e}'
    return ''


def ap_hang_loat(con, dong: list, don_gia, ghi_chu: str, vi_tri: str = '', bo_mo=None, truoc_bo_mo=None, bao_tien_do=None, chi_tiet=None) -> KetQuaAp:
    """Áp một đơn giá vào các hàng DongGia đã chọn, mỗi hộ một lần lưu. Hộ lỗi ghi vào bi_chan, hộ khác vẫn áp. bo_mo: hộ đang mở chỉ đổi trong bộ soạn;
    truoc_bo_mo(): trả False nếu bản đang mở không sửa được (cửa sổ tự chuyển nhánh khi đang xem V1). bao_tien_do(đã xong, tổng): trả True để dừng, hộ đã áp vẫn giữ."""
    kq = KetQuaAp()
    theo_ho = {}
    for x in dong:
        if x.chi_so != CO_CHUA_DONG:
            theo_ho.setdefault(x.ma_ho, []).append(x)
    dm, bc = None, None
    n = len(theo_ho)
    for k, (ma, ds) in enumerate(theo_ho.items(), 1):
        if bao_tien_do is not None and bao_tien_do(k - 1, n):
            kq.canh_bao.append(f'Đã dừng: còn {n - k + 1} hộ chưa áp.')
            break
        ten = ds[0].ho_ten
        try:
            if bo_mo is not None and bo_mo.ma_ho == ma:
                if truoc_bo_mo is not None and not truoc_bo_mo():
                    raise LoiNhap('bản đang mở chỉ xem, không sửa được.')
                if bo_mo.khoa:
                    raise LoiNhap('bản đang mở chỉ xem, không sửa được.')
                bo, nhanh = bo_mo, ''
                luu = False
            else:
                dm, bc = dm or DanhMuc(con), bc or BoiCanh.tu(con)
                bo, nhanh = mo_ban_ghi(con, ma, dm, bc)
                luu = True
            for x in ds:
                if not 0 <= x.chi_so < len(bo.pa.dat) or bo.pa.dat[x.chi_so].ma_thua != x.ma_thua or bo.pa.dat[x.chi_so].loai_dat != x.loai_dat:
                    raise LoiNhap('dòng đất đã đổi so với lúc mở bảng này: nạp lại rồi áp.')
            so = bo.ap_don_gia_qd03([x.chi_so for x in ds], don_gia, ghi_chu, vi_tri, chi_tiet)
            if luu:
                bo.luu(mo_lai=False)
        except LoiNhap as e:
            kq.bi_chan.append(f'Hộ {ma} {ten}: {e}')
            continue
        kq.so_dong += so
        kq.so_ho += 1
        if nhanh:
            kq.nhanh[ma] = nhanh
        kq.ho_tro.extend(f'Hộ {ma} {ten}: {c}' for c in bo.ho_tro_doi)
    return kq


def tao_dong_tu_thua(con, ds_ma_ho, bo_mo=None) -> tuple:
    """Hộ có thửa mà mục 1 của bản sẽ ghi còn rỗng: tạo dòng đất từ thửa (BoSoan.them_dong_tu_thua, cùng cách Dự án mới tự lập), lưu. Trả (số hộ, số dòng, [cảnh báo])."""
    dm, bc = DanhMuc(con), BoiCanh.tu(con)
    ban = _phien_ban_ca_du_an(con)
    so_ho, so_dong, cb = 0, 0, []
    for ma in ds_ma_ho:
        if bo_mo is not None and bo_mo.ma_ho == ma:
            if bo_mo.pa.dat or bo_mo.khoa:
                continue
            n, c = bo_mo.them_dong_tu_thua()
            cb.extend(c)
            if n:
                bo_mo.tinh_lai_ho_tro()
                so_ho, so_dong = so_ho + 1, so_dong + n
            continue
        thua = bc.thua_cua(ma)
        dich = _dich_cua(ban.get(ma))
        if not thua or (dich != pb.V0 and pb.dat_tu_json(pb.lay(con, ma, pb.V1 if dich == V2_MOI else dich)['du_lieu'])):
            continue
        if not any(D(t['dt_thu_hoi']) > 0 for t in thua):      # hộ không có gì để tạo: không sinh nhánh V2 thừa
            cb.append(f'Hộ {ma}: các thửa có DT thu hồi = 0, chưa tạo dòng đất. Nhập DT ở thẻ Thông tin hộ, thửa đất.')
            continue
        try:
            bo, _ = mo_ban_ghi(con, ma, dm, bc)
            if bo.pa.dat:
                continue
            n, c = bo.them_dong_tu_thua()
            cb.extend(c)
            if not n:
                continue
            bo.tinh_lai_ho_tro()
            bo.luu(mo_lai=False)
        except LoiNhap as e:
            cb.append(f'Hộ {ma}: {e}')
            continue
        so_ho, so_dong = so_ho + 1, so_dong + n
    return so_ho, so_dong, cb


def them_dong_dat(con, ma_ho: int, so_to: str, so_thua: str, loai_dat: str, dien_tich, bo_mo=None) -> tuple:
    """Thêm một dòng đất cho hộ từ Tờ, Thửa, Loại đất, DT: thửa chưa có trong hồ sơ thì thêm vào hồ sơ. Lưu ngay, trừ hộ đang mở (bo_mo). Trả (DongGia, mã nhánh hoặc '')."""
    so_to, so_thua = str(so_to or '').strip(), str(so_thua or '').strip()
    if not so_to or not so_thua:
        raise LoiNhap('Nhập số tờ, số thửa.')
    if not str(loai_dat or '').strip():
        raise LoiNhap('Chọn loại đất.')
    dt = doc_so_luong(dien_tich, 'm²', 'Diện tích')
    if dt is None or dt <= 0:
        raise LoiNhap('Diện tích phải lớn hơn 0.')
    r = con.execute('SELECT ma_thua FROM thua WHERE ma_ho = ? AND so_to = ? AND so_thua = ? ORDER BY thu_tu', (ma_ho, so_to, so_thua)).fetchone()
    if bo_mo is not None and bo_mo.ma_ho == ma_ho:
        if bo_mo.khoa:
            raise LoiNhap('Bản đang mở chỉ xem, không thêm dòng được.')
        bo, nhanh, luu = bo_mo, '', False
    else:
        bo, nhanh = mo_ban_ghi(con, ma_ho)
        luu = True
    ma_thua = r[0] if r is not None else ho_so.them_thua(con, ma_ho, dict(so_to=so_to, so_thua=so_thua, loai_dat=loai_dat, dt_thu_hoi=str(dt)))
    if r is None:
        bo.bc = BoiCanh.tu(con)                               # thửa vừa thêm chưa có trong bối cảnh đã đọc
    i, _ = bo.them_thua(ma_thua)
    bo.dat_dong_moi(i, loai_dat, dt)
    bo.tinh_lai_ho_tro()
    if luu:
        bo.luu(mo_lai=False)
    d = bo.pa.dat[i]
    t = bo.bc.thua[ma_thua]
    dong = DongGia(ma_ho, bo.pa.ho.ho_ten or '', i, ma_thua, f'Thửa {t["so_thua"]} tờ {t["so_to"]}', d.loai_dat, D(d.dien_tich), d.ty_le, D(d.gia_bang_gia) * he_so(d.he_so_k))
    return dong, nhanh
